#!/usr/bin/env python3
"""HealthBench judge/oracle information ablation using cached results.

This script runs CJE on cached gpt-4o-mini meta-eval judgments with a 2x2 matrix:
- Judge score: continuous confidence vs binary criteria_met
- Oracle label: binary physician majority vs continuous physician agreement

No new API calls are made.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from time import perf_counter
from pathlib import Path
from typing import Any

from cje import analyze_dataset

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _helpers import _ensure_ci_scale

FRACTIONS = [1.0, 0.50, 0.25, 0.10, 0.05]
FLOAT_EPSILON = 1e-12

CONDITIONS: list[dict[str, str]] = [
    {
        "id": "A",
        "name": "judge_continuous + oracle_binary_majority",
        "judge_key": "judge_continuous",
        "oracle_key": "oracle_binary_majority",
    },
    {
        "id": "B",
        "name": "judge_binary + oracle_binary_majority",
        "judge_key": "judge_binary",
        "oracle_key": "oracle_binary_majority",
    },
    {
        "id": "C",
        "name": "judge_continuous + oracle_continuous_agreement",
        "judge_key": "judge_continuous",
        "oracle_key": "oracle_continuous_agreement",
    },
    {
        "id": "D",
        "name": "judge_binary + oracle_continuous_agreement",
        "judge_key": "judge_binary",
        "oracle_key": "oracle_continuous_agreement",
    },
]
CONDITION_ORDER = {condition["id"]: idx for idx, condition in enumerate(CONDITIONS)}


def make_record_id(record: dict[str, Any]) -> str:
    key = f"{record['prompt_id']}:{record.get('completion_id', '')}:{record['rubric']}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def physician_majority(labels: list[bool]) -> float:
    return 1.0 if sum(labels) > len(labels) / 2 else 0.0


def stable_uniform(record_id: str, seed: int) -> float:
    raw = hashlib.sha256(f"{seed}:{record_id}".encode()).hexdigest()[:16]
    return int(raw, 16) / float(16**16 - 1)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_joined_rows(cache_dir: Path, model: str = "openai_gpt-4o-mini") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta_path = cache_dir / "meta_eval.jsonl"
    judge_path = cache_dir / f"judge_results_{model}.jsonl"

    meta_rows = load_jsonl(meta_path)
    judge_rows = load_jsonl(judge_path)

    meta_by_id: dict[str, dict[str, Any]] = {make_record_id(row): row for row in meta_rows}

    joined: list[dict[str, Any]] = []
    missing_meta = 0
    parse_ok_rows = 0
    cont_oracle_values: list[float] = []

    for row in judge_rows:
        rid = row["record_id"]
        meta = meta_by_id.get(rid)
        if meta is None:
            missing_meta += 1
            continue

        labels = [bool(x) for x in meta.get("binary_labels", [])]
        if not labels:
            continue

        parse_ok = bool(row.get("parse_ok", True))
        if parse_ok:
            parse_ok_rows += 1

        oracle_cont = sum(labels) / len(labels)
        cont_oracle_values.append(oracle_cont)

        joined.append(
            {
                "record_id": rid,
                "cluster_id": f"{row['prompt_id']}:{row.get('completion_id', '')}",
                "judge_continuous": float(row["judge_confidence"]),
                "judge_binary": float(row["judge_binary"]),
                "oracle_binary_majority": physician_majority(labels),
                "oracle_continuous_agreement": float(oracle_cont),
                "parse_ok": parse_ok,
            }
        )

    stats = {
        "meta_rows": len(meta_rows),
        "judge_rows": len(judge_rows),
        "joined_rows": len(joined),
        "missing_meta_rows": missing_meta,
        "parse_ok_rows": parse_ok_rows,
        "oracle_cont_min": min(cont_oracle_values) if cont_oracle_values else float("nan"),
        "oracle_cont_max": max(cont_oracle_values) if cont_oracle_values else float("nan"),
    }
    return joined, stats


def selected_ids(rows: list[dict[str, Any]], fraction: float, seed: int) -> set[str]:
    if fraction >= 1.0:
        return {row["record_id"] for row in rows}

    picked = set()
    for row in rows:
        u = stable_uniform(row["record_id"], seed)
        if u < fraction:
            picked.add(row["record_id"])
    return picked


def run_condition(
    rows: list[dict[str, Any]],
    condition: dict[str, str],
    fraction: float,
    seed: int,
    n_bootstrap: int,
    inference_method: str,
) -> dict[str, Any]:
    pick = selected_ids(rows, fraction=fraction, seed=seed)
    oracle_n = len(pick)

    judge_key = condition["judge_key"]
    oracle_key = condition["oracle_key"]

    fresh_draws = []
    for row in rows:
        sample: dict[str, Any] = {
            # prompt_id defines clustering unit for CJE direct mode.
            "prompt_id": row["cluster_id"],
            "judge_score": row[judge_key],
        }
        if row["record_id"] in pick:
            sample["oracle_label"] = row[oracle_key]
        fresh_draws.append(sample)

    estimator_config: dict[str, Any] = {"inference_method": inference_method}
    if inference_method in {"bootstrap", "auto"}:
        estimator_config["n_bootstrap"] = n_bootstrap

    results = analyze_dataset(
        fresh_draws_data={"all_criteria": fresh_draws},
        estimator="direct",
        estimator_config=estimator_config,
    )
    estimate = float(results.estimates[0])
    standard_error = float(results.standard_errors[0])
    ci_lo = ci_hi = float("nan")

    if callable(getattr(results, "confidence_interval", None)):
        lower, upper = results.confidence_interval()
        lower, upper = _ensure_ci_scale(results.estimates, lower, upper, results)
        ci_lo, ci_hi = float(lower[0]), float(upper[0])

    raw_mean = sum(float(row[judge_key]) for row in rows) / len(rows)
    ci_contains = ci_lo <= estimate <= ci_hi

    return {
        "condition_id": condition["id"],
        "condition_name": condition["name"],
        "judge_key": judge_key,
        "oracle_key": oracle_key,
        "oracle_fraction": fraction,
        "oracle_n": oracle_n,
        "estimate": estimate,
        "standard_error": standard_error,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "raw_mean": raw_mean,
        "shift_vs_raw": estimate - raw_mean,
        "ci_contains_estimate": ci_contains,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "condition_id",
        "condition_name",
        "judge_key",
        "oracle_key",
        "oracle_fraction",
        "oracle_n",
        "estimate",
        "standard_error",
        "ci_lo",
        "ci_hi",
        "raw_mean",
        "shift_vs_raw",
        "ci_contains_estimate",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def sorted_runs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic ordering for checkpoint and final outputs."""
    return sorted(
        rows,
        key=lambda row: (CONDITION_ORDER.get(row["condition_id"], 999), -float(row["oracle_fraction"])),
    )


def fmt_pct(frac: float) -> str:
    return f"{int(frac * 100)}%"


def write_markdown(path: Path, stats: dict[str, Any], runs: list[dict[str, Any]]) -> None:
    by_cond: dict[str, list[dict[str, Any]]] = {}
    for row in runs:
        by_cond.setdefault(row["condition_id"], []).append(row)

    full_rows = [row for row in runs if abs(row["oracle_fraction"] - 1.0) < FLOAT_EPSILON]
    full_rows.sort(key=lambda row: row["condition_id"])

    baseline_by_fraction = {
        row["oracle_fraction"]: row
        for row in by_cond.get("A", [])
    }

    lines: list[str] = []
    lines.append("# HealthBench Judge/Oracle Information Ablation")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **meta_eval rows**: {stats['meta_rows']}")
    lines.append(f"- **cached judge rows**: {stats['judge_rows']}")
    lines.append(f"- **joined rows**: {stats['joined_rows']}")
    lines.append(f"- **missing joins**: {stats['missing_meta_rows']}")
    lines.append(
        f"- **parse-ok joined rows**: {stats['parse_ok_rows']} "
        f"({(100*stats['parse_ok_rows']/stats['joined_rows']) if stats['joined_rows'] else 0.0:.2f}%)"
    )
    lines.append(f"- **conversation clusters**: {stats['cluster_rows']}")
    lines.append(
        f"- **parse-failure policy**: "
        f"{'included' if stats['include_parse_failures'] else 'excluded'}"
    )
    lines.append(
        f"- **continuous oracle range**: [{stats['oracle_cont_min']:.3f}, {stats['oracle_cont_max']:.3f}]"
    )
    lines.append(f"- **run progress**: {len(runs)}/{len(CONDITIONS) * len(FRACTIONS)} completed")
    lines.append("")

    lines.append("## Full-Coverage Results (100% Oracle)")
    lines.append("")
    lines.append("| Condition | Judge Score | Oracle Label | Estimate | SE | 95% CI | Shift vs Raw |")
    lines.append("|---|---|---|---:|---:|---|---:|")
    for row in full_rows:
        lines.append(
            f"| {row['condition_id']} | {row['judge_key']} | {row['oracle_key']} | "
            f"{row['estimate']:.4f} | {row['standard_error']:.4f} | "
            f"[{row['ci_lo']:.4f}, {row['ci_hi']:.4f}] | {row['shift_vs_raw']:+.4f} |"
        )
    lines.append("")

    lines.append("## Oracle Coverage Sweep by Condition")
    lines.append("")
    for condition in CONDITIONS:
        condition_runs = sorted(by_cond.get(condition["id"], []), key=lambda row: -row["oracle_fraction"])
        lines.append(f"### Condition {condition['id']}: {condition['name']}")
        lines.append("")
        lines.append("| Oracle % | Oracle N | Estimate | SE | 95% CI | Shift vs Raw |")
        lines.append("|---|---:|---:|---:|---|---:|")
        for row in condition_runs:
            lines.append(
                f"| {fmt_pct(row['oracle_fraction'])} | {row['oracle_n']} | {row['estimate']:.4f} | "
                f"{row['standard_error']:.4f} | [{row['ci_lo']:.4f}, {row['ci_hi']:.4f}] | "
                f"{row['shift_vs_raw']:+.4f} |"
            )
        lines.append("")

    lines.append("## Delta vs Baseline (Condition A)")
    lines.append("")
    lines.append("| Oracle % | Baseline A Est | B-A | C-A | D-A |")
    lines.append("|---|---:|---:|---:|---:|")
    for frac in sorted(FRACTIONS, reverse=True):
        base_row = baseline_by_fraction.get(frac)
        if base_row is None:
            lines.append(f"| {fmt_pct(frac)} | pending | pending | pending | pending |")
            continue

        base = base_row["estimate"]
        deltas: dict[str, str] = {}
        for cid in ("B", "C", "D"):
            row = next(
                (
                    item
                    for item in by_cond.get(cid, [])
                    if abs(item["oracle_fraction"] - frac) < FLOAT_EPSILON
                ),
                None,
            )
            deltas[cid] = "pending" if row is None else f"{row['estimate'] - base:+.4f}"
        lines.append(
            f"| {fmt_pct(frac)} | {base:.4f} | {deltas['B']} | {deltas['C']} | {deltas['D']} |"
        )
    lines.append("")

    bad_ci = [row for row in runs if not row["ci_contains_estimate"]]
    lines.append("## Validation Checks")
    lines.append("")
    expected_join_rows = (
        stats["judge_rows"] if stats["include_parse_failures"] else stats["parse_ok_rows"]
    )
    lines.append(
        f"- **Join integrity**: {stats['joined_rows']} joined rows "
        f"(expected {expected_join_rows})"
    )
    lines.append(
        f"- **Continuous oracle in [0,1]**: "
        f"{0.0 <= stats['oracle_cont_min'] <= 1.0 and 0.0 <= stats['oracle_cont_max'] <= 1.0}"
    )
    lines.append(f"- **CI contains estimate (all runs)**: {len(bad_ci) == 0}")
    if bad_ci:
        lines.append(f"- **Non-containing CI rows**: {len(bad_ci)}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="HealthBench judge/oracle ablation from cached data")
    parser.add_argument("--cache-dir", default=".cache/")
    parser.add_argument("--model", default="openai_gpt-4o-mini",
                        help="Judge model cache filename stem (default: openai_gpt-4o-mini)")
    parser.add_argument(
        "--out-md",
        default="results/ablation_judge_oracle_information.md",
    )
    parser.add_argument(
        "--out-csv",
        default="results/ablation_judge_oracle_information.csv",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--n-bootstrap",
        type=int,
        default=400,
        help=(
            "Bootstrap replicates when bootstrap is used directly or selected by auto "
            "(default: 400)"
        ),
    )
    parser.add_argument(
        "--inference-method",
        choices=["cluster_robust", "bootstrap", "auto"],
        default="auto",
        help="CJE direct estimator inference mode (default: auto)",
    )
    parser.add_argument(
        "--include-parse-failures",
        action="store_true",
        help="Include parse-failure rows from cached judge outputs (default: exclude)",
    )
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    out_md = Path(args.out_md)
    out_csv = Path(args.out_csv)
    out_md.parent.mkdir(parents=True, exist_ok=True)

    rows, stats = build_joined_rows(cache_dir, model=args.model)
    if not args.include_parse_failures:
        rows = [row for row in rows if row.get("parse_ok", False)]

    stats["include_parse_failures"] = args.include_parse_failures
    stats["joined_rows"] = len(rows)
    stats["cluster_rows"] = len({row["cluster_id"] for row in rows})
    if stats["joined_rows"] == 0:
        raise RuntimeError("No joined rows found; check cache paths.")

    write_csv(out_csv, [])
    write_markdown(out_md, stats, [])
    print(
        f"[0/{len(CONDITIONS) * len(FRACTIONS)}] initialized checkpoints: "
        f"{out_md} and {out_csv}",
        flush=True,
    )

    all_runs: list[dict[str, Any]] = []
    total_runs = len(CONDITIONS) * len(FRACTIONS)
    for condition_idx, condition in enumerate(CONDITIONS, start=1):
        for fraction_idx, fraction in enumerate(FRACTIONS, start=1):
            run_idx = (condition_idx - 1) * len(FRACTIONS) + fraction_idx
            label = (
                f"condition {condition['id']} "
                f"({condition['judge_key']} vs {condition['oracle_key']}), "
                f"oracle={fmt_pct(fraction)}"
            )
            print(f"[{run_idx}/{total_runs}] starting {label}", flush=True)
            start = perf_counter()
            run = run_condition(
                rows,
                condition,
                fraction=fraction,
                seed=args.seed,
                n_bootstrap=args.n_bootstrap,
                inference_method=args.inference_method,
            )
            all_runs.append(run)
            elapsed = perf_counter() - start

            ordered_runs = sorted_runs(all_runs)
            write_csv(out_csv, ordered_runs)
            write_markdown(out_md, stats, ordered_runs)
            print(
                f"[{run_idx}/{total_runs}] done {label}: "
                f"est={run['estimate']:.4f}, se={run['standard_error']:.4f}, "
                f"ci=[{run['ci_lo']:.4f}, {run['ci_hi']:.4f}], "
                f"elapsed={elapsed:.1f}s (checkpoint written)",
                flush=True,
            )

    ordered_runs = sorted_runs(all_runs)
    write_csv(out_csv, ordered_runs)
    write_markdown(out_md, stats, ordered_runs)

    print(f"Wrote {out_md}")
    print(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
