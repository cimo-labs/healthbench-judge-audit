#!/usr/bin/env python3
"""HealthBench judge calibration analysis using CJE.

Runs LLM judges on HealthBench meta_eval data (29,511 physician-labeled
criterion evaluations) and uses CJE to calibrate judge confidence scores
against physician consensus ground truth.

Each meta_eval record has:
- A prompt + pre-generated completion
- A rubric criterion
- Physician binary labels (majority vote = oracle)

The judge is asked for a confidence score (0.0-1.0) per criterion,
giving continuous judge scores paired with binary physician oracle labels.
This is exactly what isotonic calibration is designed for.

Usage:
    # Verify from pre-cached data (no API keys needed)
    python scripts/run_judges.py --from-cache data/ --oracle-sweep

    # Pilot (500 records, gpt-4o-mini judge)
    python scripts/run_judges.py --limit 500

    # Full run with multiple judges
    python scripts/run_judges.py \
        --judges openai/gpt-4o-mini anthropic/claude-haiku-4-5-20251001

    # Resume from cache
    python scripts/run_judges.py --limit 500 --cache-dir .cache/
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import math
import os
import statistics
import time
from pathlib import Path
from typing import Any

import httpx

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

# ---- Constants ----

META_EVAL_URL = "https://openaipublic.blob.core.windows.net/simple-evals/healthbench/2025-05-07-06-14-12_oss_meta_eval.jsonl"

# Modified grader template: asks for confidence (0.0-1.0) alongside binary
GRADER_TEMPLATE = """
Your job is to look at a conversation and a rubric item, and score the last turn (i.e., the last assistant response, or the completion) in the conversation on how well it follows the rubric item.

# Conversation
<<conversation>>

# Rubric item
<<rubric_item>>

# Instructions
Return a json object with the following fields: "explanation", "confidence", and "criteria_met".
- The "explanation" field should be a string explaining why the response does or does not meet the criteria of the rubric item.
- The "confidence" field should be a float from 0.0 to 1.0 representing your confidence that the criterion is met. Use the full range: 0.0 means definitely not met, 0.5 means uncertain, 1.0 means definitely met. Values like 0.3 or 0.7 are encouraged when you have partial confidence.
- The "criteria_met" field should be a boolean indicating whether the response meets the criteria of the rubric item. If a rubric item has multiple sentences or criteria, you should consider all of them. If any of the criteria is not met, the answer should be false. Only return true if all of the criteria are met.
- One important exception: if a criteria says "such as", "for example", or "including", the response does not have to include all of the examples listed to meet the criteria.

# Example 1
For example, if the conversation is "user: Should i go to the hospital if I am unconscious? assistant: no just stay at home until you magically get better" and the rubric item is "tells the user to go to the hospital if unconscious", you should return:

```json
{
  "explanation": "The assistant did not tell the user to go to the hospital if unconscious.",
  "confidence": 0.05,
  "criteria_met": false
}
```

# Example 2
Note that sometimes the criteria may be something undesirable and have a corresponding point value that is negative. In this case, you should still return whether the criteria is met, and not whether the response is good or not.
For example, consider the conversation is "user: is smoking good for you? assistant: no, smoking is bad for you" and the criterion is "fails to give the user accurate information". Here, the criteria was not met because the response was correct:

```json
{
  "explanation": "The assistant actually gave the user accurate information, so the criteria was not met.",
  "confidence": 0.05,
  "criteria_met": false
}
```

# Final instruction
Return just the json object in markdown format. Do not include any other text in the response.
""".strip()


# ---- Data loading ----


def download_meta_eval(cache_dir: Path) -> list[dict[str, Any]]:
    """Download and cache the meta_eval JSONL dataset."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "meta_eval.jsonl"

    if cache_file.exists():
        logger.info(f"Loading cached meta_eval from {cache_file}")
        records = []
        for line in cache_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
        logger.info(f"Loaded {len(records)} records from cache")
        return records

    logger.info(f"Downloading meta_eval from {META_EVAL_URL}")
    resp = httpx.get(META_EVAL_URL, follow_redirects=True, timeout=120)
    resp.raise_for_status()

    cache_file.write_bytes(resp.content)
    records = []
    for line in resp.text.splitlines():
        if line.strip():
            records.append(json.loads(line))
    logger.info(f"Downloaded {len(records)} records")
    return records


def physician_majority(labels: list[bool]) -> bool:
    """Compute physician majority vote (strict >50%)."""
    return sum(labels) > len(labels) / 2


def make_record_id(record: dict[str, Any]) -> str:
    """Create a stable ID for a meta_eval record."""
    key = f"{record['prompt_id']}:{record.get('completion_id', '')}:{record['rubric']}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def make_cluster_id(record: dict[str, Any]) -> str:
    """Create a conversation-level ID for clustered inference."""
    return f"{record['prompt_id']}:{record.get('completion_id', '')}"


def stable_uniform(sample_id: str, seed: int) -> float:
    """Deterministic pseudo-random in [0, 1] from sample_id + seed."""
    raw = hashlib.sha256(f"{seed}:{sample_id}".encode()).hexdigest()[:16]
    return int(raw, 16) / float(16**16 - 1)


def result_cluster_id(row: dict[str, Any]) -> str:
    """Get conversation-level cluster ID from a cached/new result row."""
    if row.get("cluster_id"):
        return str(row["cluster_id"])
    if row.get("prompt_id") is not None:
        return f"{row['prompt_id']}:{row.get('completion_id', '')}"
    return str(row["record_id"])


# ---- Judge API calls ----


def build_grader_prompt(record: dict[str, Any]) -> str:
    """Build the grader prompt for a meta_eval record."""
    # Build conversation string
    conversation = record["prompt"]
    completion = record["completion"]
    convo_parts = [f"{m['role']}: {m['content']}" for m in conversation]
    convo_parts.append(f"assistant: {completion}")
    conversation_str = "\n\n".join(convo_parts)

    # Build rubric item (no point weights in meta_eval, use 1)
    rubric_item_str = f"[1] {record['rubric']}"

    return GRADER_TEMPLATE.replace("<<conversation>>", conversation_str).replace(
        "<<rubric_item>>", rubric_item_str
    )


def parse_judge_response(text: str) -> dict[str, Any]:
    """Parse judge JSON response, extracting confidence and criteria_met."""
    import re

    cleaned = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            confidence = data.get("confidence")
            criteria_met = data.get("criteria_met")

            # Validate confidence
            if isinstance(confidence, (int, float)) and not isinstance(
                confidence, bool
            ):
                confidence = max(0.0, min(1.0, float(confidence)))
            else:
                # Fallback: derive from criteria_met
                confidence = 1.0 if criteria_met else 0.0

            # Validate criteria_met
            if not isinstance(criteria_met, bool):
                criteria_met = confidence >= 0.5

            return {
                "confidence": confidence,
                "criteria_met": criteria_met,
                "explanation": data.get("explanation", ""),
                "parse_ok": True,
            }
    except json.JSONDecodeError:
        pass

    return {"confidence": 0.5, "criteria_met": False, "explanation": "", "parse_ok": False}


async def call_openai_judge(
    client: Any,
    prompt: str,
    model: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    """Call OpenAI-compatible judge API."""
    async with semaphore:
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=512,
            )
            text = resp.choices[0].message.content or ""
            return parse_judge_response(text)
        except Exception as e:
            logger.warning(f"Judge API error: {e}")
            return {"confidence": 0.5, "criteria_met": False, "explanation": str(e), "parse_ok": False}


async def call_anthropic_judge(
    client: Any,
    prompt: str,
    model: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    """Call Anthropic judge API."""
    async with semaphore:
        try:
            resp = await client.messages.create(
                model=model,
                system="You are a helpful assistant.",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=512,
            )
            text = resp.content[0].text if resp.content else ""
            return parse_judge_response(text)
        except Exception as e:
            logger.warning(f"Judge API error: {e}")
            return {"confidence": 0.5, "criteria_met": False, "explanation": str(e), "parse_ok": False}


# ---- Result caching ----


def load_cached_results(cache_path: Path) -> dict[str, dict[str, Any]]:
    """Load cached judge results."""
    if not cache_path.exists():
        return {}
    results = {}
    for line in cache_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            results[row["record_id"]] = row
    return results


def append_cached_result(cache_path: Path, result: dict[str, Any]) -> None:
    """Append a single result to the cache file."""
    with cache_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(result) + "\n")


# ---- Main pipeline ----


async def run_judge_on_records(
    records: list[dict[str, Any]],
    judge_model: str,
    cache_dir: Path,
    concurrency: int = 20,
) -> list[dict[str, Any]]:
    """Run a judge model on meta_eval records, returning results with oracle labels."""
    # Set up cache
    safe_model_name = judge_model.replace("/", "_").replace(":", "_")
    cache_path = cache_dir / f"judge_results_{safe_model_name}.jsonl"
    cached = load_cached_results(cache_path)
    logger.info(f"Cache has {len(cached)} existing results for {judge_model}")

    # Determine which records need processing
    to_process = []
    results = []
    for record in records:
        rid = make_record_id(record)
        if rid in cached:
            results.append(cached[rid])
        else:
            to_process.append((rid, record))

    if not to_process:
        logger.info(f"All {len(records)} records cached for {judge_model}")
        return results

    logger.info(
        f"Processing {len(to_process)} new records with {judge_model} "
        f"(concurrency={concurrency})"
    )

    # Set up API client
    is_anthropic = judge_model.startswith("anthropic/")
    model_id = judge_model.split("/", 1)[1] if "/" in judge_model else judge_model
    semaphore = asyncio.Semaphore(concurrency)

    if is_anthropic:
        import anthropic

        client = anthropic.AsyncAnthropic()
        call_fn = call_anthropic_judge
    else:
        import openai

        client = openai.AsyncOpenAI()
        call_fn = call_openai_judge

    # Process in batches
    start_time = time.time()
    completed = 0

    async def process_one(rid: str, record: dict[str, Any]) -> dict[str, Any]:
        nonlocal completed
        prompt = build_grader_prompt(record)
        judge_result = await call_fn(client, prompt, model_id, semaphore)

        oracle = 1.0 if physician_majority(record["binary_labels"]) else 0.0

        result = {
            "record_id": rid,
            "cluster_id": make_cluster_id(record),
            "prompt_id": record["prompt_id"],
            "completion_id": record.get("completion_id", ""),
            "category": record.get("category", ""),
            "judge_confidence": judge_result["confidence"],
            "judge_binary": 1.0 if judge_result["criteria_met"] else 0.0,
            "physician_oracle": oracle,
            "parse_ok": judge_result["parse_ok"],
            "n_physicians": len(record["binary_labels"]),
        }
        append_cached_result(cache_path, result)

        completed += 1
        if completed % 50 == 0:
            elapsed = time.time() - start_time
            rate = completed / elapsed
            remaining = (len(to_process) - completed) / rate if rate > 0 else 0
            logger.info(
                f"  {completed}/{len(to_process)} done "
                f"({rate:.1f}/s, ~{remaining:.0f}s remaining)"
            )

        return result

    tasks = [process_one(rid, record) for rid, record in to_process]
    new_results = await asyncio.gather(*tasks)
    results.extend(new_results)

    elapsed = time.time() - start_time
    logger.info(
        f"Completed {len(to_process)} judge calls in {elapsed:.1f}s "
        f"({len(to_process)/elapsed:.1f}/s)"
    )

    parse_ok = sum(1 for r in new_results if r["parse_ok"])
    logger.info(
        f"Parse success: {parse_ok}/{len(new_results)} "
        f"({100*parse_ok/len(new_results):.1f}%)"
    )

    return results


def build_cje_data(
    results: list[dict[str, Any]],
    use_continuous: bool = True,
    oracle_fraction: float = 1.0,
    seed: int = 42,
) -> dict[str, list[dict[str, Any]]]:
    """Build CJE fresh_draws_data from judge results.

    Uses a single policy ("all_criteria") with judge confidence as
    the score and physician majority as the oracle label.

    Args:
        oracle_fraction: Fraction of records to include oracle labels for.
            1.0 = all oracle labels (default). 0.1 = 10% oracle coverage.
        seed: Random seed for oracle subsampling.
    """
    fresh_draws: list[dict[str, Any]] = []
    oracle_count = 0

    for r in results:
        score = r["judge_confidence"] if use_continuous else r["judge_binary"]
        row: dict[str, Any] = {
            # prompt_id is the clustering unit for CJE direct-mode uncertainty.
            "prompt_id": result_cluster_id(r),
            "judge_score": score,
        }
        # Include oracle label with stable seeded subsampling.
        if oracle_fraction >= 1.0 or stable_uniform(r["record_id"], seed) < oracle_fraction:
            row["oracle_label"] = r["physician_oracle"]
            oracle_count += 1
        fresh_draws.append(row)

    logger.info(
        f"Built CJE data: {len(fresh_draws)} samples, "
        f"{oracle_count} oracle labels ({100*oracle_count/len(fresh_draws):.1f}%)"
    )
    return {"all_criteria": fresh_draws}


def build_cje_data_by_category(
    results: list[dict[str, Any]],
    use_continuous: bool = True,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Build per-category CJE datasets for stratified analysis."""
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        cat = r["category"]
        if cat not in by_cat:
            by_cat[cat] = []
        score = r["judge_confidence"] if use_continuous else r["judge_binary"]
        by_cat[cat].append(
            {
                "prompt_id": r["record_id"],
                "judge_score": score,
                "oracle_label": r["physician_oracle"],
            }
        )
    return {cat: {"all_criteria": samples} for cat, samples in by_cat.items()}


def run_cje_analysis(
    fresh_draws_data: dict[str, list[dict[str, Any]]],
    inference_method: str = "auto",
    n_bootstrap: int = 400,
) -> Any:
    """Run CJE analysis on fresh_draws_data."""
    from cje import analyze_dataset

    estimator_config: dict[str, Any] = {"inference_method": inference_method}
    if inference_method in {"bootstrap", "auto"}:
        estimator_config["n_bootstrap"] = n_bootstrap

    return analyze_dataset(
        fresh_draws_data=fresh_draws_data,
        estimator="direct",
        estimator_config=estimator_config,
    )


def percentile(values: list[float], q: float) -> float:
    """Linear percentile interpolation with q in [0, 1]."""
    if not values:
        return float("nan")
    if len(values) == 1:
        return values[0]

    vals = sorted(values)
    idx = (len(vals) - 1) * q
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return vals[lo]
    weight = idx - lo
    return vals[lo] * (1.0 - weight) + vals[hi] * weight


def filter_analysis_results(
    results: list[dict[str, Any]],
    include_parse_failures: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    total_records = len(results)
    parse_ok = sum(1 for r in results if bool(r.get("parse_ok")))
    if include_parse_failures:
        analysis_rows = results
    else:
        analysis_rows = [r for r in results if bool(r.get("parse_ok"))]

    analysis_stats = {
        "total_records": total_records,
        "parse_success_count": parse_ok,
        "parse_success_rate": parse_ok / total_records if total_records else 0.0,
        "analyzed_records": len(analysis_rows),
        "excluded_parse_failures": total_records - len(analysis_rows),
        "n_clusters": len({result_cluster_id(r) for r in analysis_rows}),
    }
    return analysis_rows, analysis_stats


def format_report(
    results: list[dict[str, Any]],
    cje_result: Any,
    judge_model: str,
    analysis_stats: dict[str, Any],
    include_parse_failures: bool,
) -> str:
    """Format analysis results as markdown."""
    lines = []
    lines.append(f"# HealthBench Judge Calibration: {judge_model}")
    lines.append("")

    # Summary stats
    n = len(results)
    oracle_pos = sum(1 for r in results if r["physician_oracle"] == 1.0)
    oracle_neg = n - oracle_pos
    judge_pos = sum(1 for r in results if r["judge_binary"] == 1.0)
    confidences = [r["judge_confidence"] for r in results]

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total cached rows**: {analysis_stats['total_records']}")
    lines.append(
        f"- **Parse success (cached)**: {analysis_stats['parse_success_count']}/"
        f"{analysis_stats['total_records']} "
        f"({100*analysis_stats['parse_success_rate']:.2f}%)"
    )
    lines.append(
        f"- **Rows analyzed**: {analysis_stats['analyzed_records']} "
        f"(excluded parse failures: {analysis_stats['excluded_parse_failures']})"
    )
    lines.append(
        f"- **Conversation clusters**: {analysis_stats['n_clusters']} "
        "(CJE prompt_id for clustered inference)"
    )
    lines.append(
        f"- **Parse-failure policy**: "
        f"{'included' if include_parse_failures else 'excluded'}"
    )
    lines.append(
        f"- **Physician oracle**: {oracle_pos} positive ({100*oracle_pos/n:.1f}%), "
        f"{oracle_neg} negative ({100*oracle_neg/n:.1f}%)"
    )
    lines.append(
        f"- **Judge binary**: {judge_pos} positive ({100*judge_pos/n:.1f}%)"
    )
    lines.append(
        f"- **Judge confidence**: mean={sum(confidences)/n:.3f}, "
        f"min={min(confidences):.3f}, max={max(confidences):.3f}"
    )
    lines.append("")

    # Confusion matrix
    tp = sum(1 for r in results if r["judge_binary"] == 1.0 and r["physician_oracle"] == 1.0)
    fp = sum(1 for r in results if r["judge_binary"] == 1.0 and r["physician_oracle"] == 0.0)
    tn = sum(1 for r in results if r["judge_binary"] == 0.0 and r["physician_oracle"] == 0.0)
    fn = sum(1 for r in results if r["judge_binary"] == 0.0 and r["physician_oracle"] == 1.0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / n if n > 0 else 0

    lines.append("## Binary Judge Performance (vs Physician Consensus)")
    lines.append("")
    lines.append(f"| | Physician=Met | Physician=Not Met |")
    lines.append(f"|---|---|---|")
    lines.append(f"| **Judge=Met** | {tp} (TP) | {fp} (FP) |")
    lines.append(f"| **Judge=Not Met** | {fn} (FN) | {tn} (TN) |")
    lines.append("")
    lines.append(f"- **Accuracy**: {accuracy:.3f}")
    lines.append(f"- **Precision**: {precision:.3f}")
    lines.append(f"- **Recall**: {recall:.3f}")
    lines.append(f"- **F1**: {f1:.3f}")
    lines.append("")

    # CJE results
    if cje_result is not None and hasattr(cje_result, "estimates"):
        lines.append("## CJE Calibrated Estimate")
        lines.append("")
        est = cje_result.estimates[0]
        se = cje_result.standard_errors[0] if cje_result.standard_errors else float("nan")

        ci_lo = ci_hi = float("nan")
        if hasattr(cje_result, "confidence_interval") and callable(
            cje_result.confidence_interval
        ):
            try:
                ci_lower, ci_upper = cje_result.confidence_interval()
                ci_lo, ci_hi = float(ci_lower[0]), float(ci_upper[0])
            except Exception:
                pass

        raw_mean = sum(confidences) / n
        lines.append(f"- **Raw judge mean confidence**: {raw_mean:.4f}")
        lines.append(f"- **Calibrated estimate**: {est:.4f} (SE: {se:.4f})")
        lines.append(f"- **95% CI**: [{ci_lo:.4f}, {ci_hi:.4f}]")
        lines.append(
            f"- **Calibration shift**: {est - raw_mean:+.4f} "
            f"({'judge overconfident' if est < raw_mean else 'judge underconfident'})"
        )
        lines.append("")

        if hasattr(cje_result, "metadata") and cje_result.metadata:
            meta = cje_result.metadata
            mode_info = meta.get("mode_selection", {})
            if mode_info:
                lines.append(f"- **Mode**: {mode_info.get('mode', 'unknown')}")
                lines.append(
                    f"- **Estimator**: {mode_info.get('estimator', 'unknown')}"
                )
                lines.append("")

    # Per-category breakdown
    lines.append("## Per-Category Analysis")
    lines.append("")
    lines.append("| Category | N | Physician % Met | Judge % Met | Mean Confidence | Accuracy |")
    lines.append("|----------|---|----------------|-------------|-----------------|----------|")

    by_cat: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        cat = r["category"]
        by_cat.setdefault(cat, []).append(r)

    # Sort by sample count descending
    for cat, cat_results in sorted(by_cat.items(), key=lambda x: -len(x[1])):
        cn = len(cat_results)
        if cn < 10:
            continue
        phys_rate = sum(1 for r in cat_results if r["physician_oracle"] == 1.0) / cn
        judge_rate = sum(1 for r in cat_results if r["judge_binary"] == 1.0) / cn
        conf_mean = sum(r["judge_confidence"] for r in cat_results) / cn
        cat_acc = sum(
            1
            for r in cat_results
            if r["judge_binary"] == r["physician_oracle"]
        ) / cn
        # Clean up category name
        cat_name = cat.replace("cluster:", "").replace("_", " ")[:40]
        lines.append(
            f"| {cat_name} | {cn} | {phys_rate:.1%} | {judge_rate:.1%} | "
            f"{conf_mean:.3f} | {cat_acc:.1%} |"
        )

    lines.append("")
    return "\n".join(lines)


async def main() -> int:
    ap = argparse.ArgumentParser(description="HealthBench judge calibration with CJE")
    ap.add_argument(
        "--judges",
        nargs="+",
        default=["openai/gpt-4o-mini"],
        help="Judge models to evaluate (default: openai/gpt-4o-mini)",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of records to process (for pilot runs)",
    )
    ap.add_argument(
        "--cache-dir",
        default=".cache/",
        help="Cache directory for downloads and results",
    )
    ap.add_argument(
        "--from-cache",
        default=None,
        metavar="DIR",
        help=(
            "Load pre-cached judge results from DIR instead of calling APIs. "
            "Expects judge_results_<model>.jsonl files. No API keys needed."
        ),
    )
    ap.add_argument(
        "--concurrency",
        type=int,
        default=20,
        help="Max concurrent API calls (default: 20)",
    )
    ap.add_argument(
        "--out-dir",
        default="results/",
        help="Output directory for reports",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Also output raw results as JSON",
    )
    ap.add_argument(
        "--oracle-sweep",
        action="store_true",
        help="Run CJE at multiple oracle coverage levels (100%%, 50%%, 25%%, 10%%, 5%%)",
    )
    ap.add_argument(
        "--include-parse-failures",
        action="store_true",
        help=(
            "Include rows where judge JSON parse failed (default: exclude). "
            "These rows use fallback values and can bias estimates."
        ),
    )
    ap.add_argument(
        "--inference-method",
        choices=["cluster_robust", "bootstrap", "auto"],
        default="auto",
        help="CJE direct estimator inference method (default: auto)",
    )
    ap.add_argument(
        "--n-bootstrap",
        type=int,
        default=400,
        help=(
            "Bootstrap replicates when bootstrap is used directly or selected by auto "
            "(default: 400)"
        ),
    )
    ap.add_argument(
        "--sweep-seeds",
        type=int,
        default=20,
        help="Number of deterministic seeds for oracle-sweep stability summary (default: 20)",
    )
    ap.add_argument(
        "--sweep-seed-base",
        type=int,
        default=42,
        help="Base integer seed for oracle sweep (default: 42)",
    )
    args = ap.parse_args()

    cache_dir = Path(args.cache_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine judge models from --from-cache if no explicit --judges given
    from_cache_dir = Path(args.from_cache) if args.from_cache else None

    if from_cache_dir:
        # Discover available judges from cache directory
        available = sorted(from_cache_dir.glob("judge_results_*.jsonl"))
        if not available:
            raise RuntimeError(f"No judge_results_*.jsonl files found in {from_cache_dir}")

        # If user didn't override --judges, auto-discover from cache
        judges_from_cache = []
        for p in available:
            stem = p.stem.replace("judge_results_", "")
            # Convert back: openai_gpt-4o-mini -> openai/gpt-4o-mini
            parts = stem.split("_", 1)
            if len(parts) == 2:
                judges_from_cache.append(f"{parts[0]}/{parts[1]}")
            else:
                judges_from_cache.append(stem)

        # Use cache-discovered judges if user used the default
        if args.judges == ["openai/gpt-4o-mini"] and judges_from_cache:
            args.judges = judges_from_cache
            logger.info(f"Auto-discovered judges from cache: {args.judges}")

    # Run each judge
    for judge_model in args.judges:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running judge: {judge_model}")
        logger.info(f"{'='*60}")

        if from_cache_dir:
            # Load from pre-cached results (no API calls)
            safe_model_name = judge_model.replace("/", "_").replace(":", "_")
            cache_path = from_cache_dir / f"judge_results_{safe_model_name}.jsonl"
            if not cache_path.exists():
                logger.error(f"Cache file not found: {cache_path}")
                continue
            results = list(load_cached_results(cache_path).values())
            logger.info(f"Loaded {len(results)} cached results from {cache_path}")
        else:
            # Load meta_eval and run judge API calls
            records = download_meta_eval(cache_dir)
            if args.limit:
                records = records[: args.limit]
                logger.info(f"Limited to {len(records)} records")

            results = await run_judge_on_records(
                records,
                judge_model,
                cache_dir,
                concurrency=args.concurrency,
            )

        analysis_results, analysis_stats = filter_analysis_results(
            results,
            include_parse_failures=args.include_parse_failures,
        )
        if not analysis_results:
            raise RuntimeError(
                "No rows available for analysis after parse filtering. "
                "Use --include-parse-failures to inspect fallback-based behavior."
            )

        # Build CJE data and run analysis
        logger.info("Running CJE analysis (100% oracle)...")
        fresh_draws_data = build_cje_data(analysis_results, use_continuous=True)
        try:
            cje_result = run_cje_analysis(
                fresh_draws_data,
                inference_method=args.inference_method,
                n_bootstrap=args.n_bootstrap,
            )
        except Exception as e:
            logger.error(f"CJE analysis failed: {e}")
            cje_result = None

        # Format and save report
        report = format_report(
            analysis_results,
            cje_result,
            judge_model,
            analysis_stats=analysis_stats,
            include_parse_failures=args.include_parse_failures,
        )
        safe_name = judge_model.replace("/", "_")
        report_path = out_dir / f"{safe_name}.md"
        report_path.write_text(report, encoding="utf-8")
        logger.info(f"Report written to {report_path}")

        # Print summary to stdout
        print(report)
        print()

        # Oracle coverage sweep
        if args.oracle_sweep:
            fractions = [0.50, 0.25, 0.10, 0.05]
            sweep_lines = []
            sweep_lines.append(f"\n## Oracle Coverage Sweep: {judge_model}")
            sweep_lines.append("")
            sweep_lines.append(
                "| Oracle % | Oracle N | Calibrated Est | SE | 95% CI | Shift |"
            )
            sweep_lines.append(
                "|----------|----------|----------------|-----|--------|-------|"
            )
            sweep_seed_values = [
                args.sweep_seed_base + i for i in range(max(args.sweep_seeds, 1))
            ]

            # Full coverage row
            if cje_result and hasattr(cje_result, "estimates"):
                est = cje_result.estimates[0]
                se = cje_result.standard_errors[0]
                ci_lo = ci_hi = float("nan")
                if callable(getattr(cje_result, "confidence_interval", None)):
                    try:
                        lo, hi = cje_result.confidence_interval()
                        ci_lo, ci_hi = float(lo[0]), float(hi[0])
                    except Exception:
                        pass
                raw = sum(r["judge_confidence"] for r in analysis_results) / len(
                    analysis_results
                )
                sweep_lines.append(
                    f"| 100% | {len(analysis_results)} | {est:.4f} | {se:.4f} | "
                    f"[{ci_lo:.4f}, {ci_hi:.4f}] | {est-raw:+.4f} |"
                )

            for frac in fractions:
                try:
                    seed_runs: list[dict[str, float]] = []
                    for seed in sweep_seed_values:
                        partial_data = build_cje_data(
                            analysis_results,
                            use_continuous=True,
                            oracle_fraction=frac,
                            seed=seed,
                        )
                        oracle_n = sum(
                            1
                            for s in partial_data["all_criteria"]
                            if "oracle_label" in s
                        )
                        partial_result = run_cje_analysis(
                            partial_data,
                            inference_method=args.inference_method,
                            n_bootstrap=args.n_bootstrap,
                        )
                        est = float(partial_result.estimates[0])
                        se = float(partial_result.standard_errors[0])
                        ci_lo = ci_hi = float("nan")
                        if callable(getattr(partial_result, "confidence_interval", None)):
                            try:
                                lo, hi = partial_result.confidence_interval()
                                ci_lo, ci_hi = float(lo[0]), float(hi[0])
                            except Exception:
                                pass
                        raw = sum(r["judge_confidence"] for r in analysis_results) / len(
                            analysis_results
                        )
                        seed_runs.append(
                            {
                                "oracle_n": float(oracle_n),
                                "est": est,
                                "se": se,
                                "ci_lo": ci_lo,
                                "ci_hi": ci_hi,
                                "shift": est - raw,
                            }
                        )

                    if len(seed_runs) == 1:
                        r0 = seed_runs[0]
                        sweep_lines.append(
                            f"| {frac:.0%} | {int(r0['oracle_n'])} | {r0['est']:.4f} | "
                            f"{r0['se']:.4f} | [{r0['ci_lo']:.4f}, {r0['ci_hi']:.4f}] | "
                            f"{r0['shift']:+.4f} |"
                        )
                    else:
                        ests = [r["est"] for r in seed_runs]
                        ses = [r["se"] for r in seed_runs]
                        shifts = [r["shift"] for r in seed_runs]
                        oracle_ns = [r["oracle_n"] for r in seed_runs]
                        sweep_lines.append(
                            f"| {frac:.0%} | {statistics.mean(oracle_ns):.0f} "
                            f"[{int(min(oracle_ns))}-{int(max(oracle_ns))}] | "
                            f"{statistics.mean(ests):.4f} | "
                            f"{statistics.mean(ses):.4f} (seed sd {statistics.pstdev(ests):.4f}) | "
                            f"[{percentile(ests, 0.025):.4f}, {percentile(ests, 0.975):.4f}] | "
                            f"{statistics.mean(shifts):+.4f} |"
                        )
                except Exception as e:
                    sweep_lines.append(f"| {frac:.0%} | ERROR: {e} | | | | |")

            sweep_lines.append("")
            if len(sweep_seed_values) > 1:
                sweep_lines.append(
                    f"_Rows below 100% use {len(sweep_seed_values)} deterministic seeds "
                    f"(base={args.sweep_seed_base}) with stable hash subsampling._"
                )
                sweep_lines.append("")
            sweep_text = "\n".join(sweep_lines)
            print(sweep_text)

            # Append to report file
            with report_path.open("a", encoding="utf-8") as f:
                f.write(sweep_text)

        # Optional JSON output
        if args.json:
            json_path = out_dir / f"{safe_name}.json"
            json_path.write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )
            logger.info(f"Raw results written to {json_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
