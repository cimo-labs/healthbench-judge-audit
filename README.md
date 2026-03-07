# HealthBench Judge Calibration Audit

Reproducibility artifact for [*When the Judge is Wrong: Calibrating LLM Evaluators with CJE*](https://cimolabs.com/blog/judge-calibration-docs).

**Key finding:** Two LLM judges (GPT-4o-mini and Claude Haiku 4.5) both produce overconfident criterion-met scores on HealthBench's 29,511 physician-labeled medical evaluations. After isotonic calibration with [CJE](https://github.com/cimo-labs/cje), both converge to the same calibrated estimate (0.6711 vs 0.6712) despite an 11.5 pp gap in raw confidence (0.916 vs 0.801) and up to 73 pp cross-judge disagreement at the category level. With only 5% oracle labels (~1,450 physician judgments), the calibrated estimates remain within about 1.4-2.1 pp of the full-oracle result.

## Quick Verification (No API Keys)

Re-run CJE calibration on pre-cached judge outputs to reproduce the exact numbers in `results/`:

```bash
pip install cje-eval
python scripts/run_judges.py --from-cache data/ --oracle-sweep
```

This loads the cached judge results from `data/` and runs CJE calibration locally. You should see:
- GPT-4o-mini: calibrated estimate **0.6711**, raw confidence 0.916, shift **-0.2449**
- Claude Haiku 4.5: calibrated estimate **0.6712**, raw confidence 0.801, shift **-0.1303**

## Full Reproduction (API Keys Required)

Run the complete pipeline from scratch:

```bash
pip install -e .
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...

# Step 1: Main calibration analysis (~$150-200 in API costs for two judges on 29,511 records)
# This also downloads meta_eval.jsonl (~130 MB) to .cache/ on first run.
python scripts/run_judges.py \
    --judges openai/gpt-4o-mini anthropic/claude-haiku-4-5-20251001 \
    --oracle-sweep

# Step 2: 2x2 ablation: judge score type x oracle label type (no API calls, uses .cache/)
python scripts/run_ablation.py

# Step 3: Prompt A/B confound check (requires OPENAI_API_KEY, uses .cache/)
python scripts/run_prompt_ab.py
```

**Note:** Steps 2 and 3 require `meta_eval.jsonl` in `.cache/`, which is downloaded automatically by Step 1. Run Step 1 first (even a `--limit 1` run will trigger the download). The prompt A/B check (Step 3) also makes ~29,511 additional OpenAI API calls.

## Extending to New Judges

Evaluate additional judge models:

```bash
python scripts/run_judges.py --judges openai/gpt-4.1 --oracle-sweep
python scripts/run_judges.py --judges anthropic/claude-sonnet-4-5-20250929 --oracle-sweep
```

Judge results are cached to `.cache/` so you can resume interrupted runs.

## Repository Structure

```
scripts/
  run_judges.py       # Main judge calibration analysis
  run_ablation.py     # 2x2 judge/oracle information ablation
  run_prompt_ab.py    # Prompt A/B confound check
  _helpers.py         # Vendored utility (CI scale guard)

results/              # Pre-computed outputs (committed for verification)
  openai_gpt-4o-mini.md
  anthropic_claude-haiku-4-5-20251001.md
  ablation_judge_oracle_information.md
  ablation_judge_oracle_information.csv
  ablation_judge_oracle_information_haiku.md
  ablation_judge_oracle_information_haiku.csv
  prompt_ab_confound_openai_gpt-4o-mini.md

data/                 # Pre-cached judge outputs (~18 MB, committed)
  README.md             # Data provenance and JSONL schema
  judge_results_openai_gpt-4o-mini.jsonl
  judge_results_anthropic_claude-haiku-4-5-20251001.jsonl
```

The 130 MB `meta_eval.jsonl` dataset is **not** included — it's publicly available from OpenAI and downloaded automatically by `run_judges.py` on first run (to `.cache/meta_eval.jsonl`). The ablation and prompt A/B scripts also need this file; run `run_judges.py` first to fetch it.

## Links

- **Blog post**: [When the Judge is Wrong](https://cimolabs.com/blog/judge-calibration-docs)
- **CJE paper**: [arXiv:2512.11150](https://arxiv.org/abs/2512.11150)
- **CJE library**: [github.com/cimo-labs/cje](https://github.com/cimo-labs/cje) / `pip install cje-eval`
- **inspect_evals PR**: [#1178](https://github.com/UKGovernmentBEIS/inspect_evals/pull/1178) (generic judge calibration tool, merged)
- **HealthBench**: [OpenAI HealthBench](https://github.com/openai/healthbench)

## License

MIT
