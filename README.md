# HealthBench Judge Calibration Audit

Reproducibility artifact for [*When the Judge is Wrong: Calibrating LLM Evaluators with CJE*](https://cimolabs.com/blog/judge-calibration-docs).

**Key finding:** Two LLM judges (GPT-4o-mini and Claude Haiku 4.5) both produce overconfident criterion-met scores on HealthBench's 29,511 physician-labeled medical evaluations. After isotonic calibration with [CJE](https://github.com/cimo-labs/cje), both converge to the same calibrated estimate (0.6711 vs 0.6712) despite a 73 percentage-point gap in raw confidence (0.916 vs 0.802). With only 5% oracle labels (~1,475 physician judgments), the calibrated estimates remain within 1 pp of the full-oracle result.

## Quick Verification (No API Keys)

Re-run CJE calibration on pre-cached judge outputs to reproduce the exact numbers in `results/`:

```bash
pip install cje-eval
python scripts/run_judges.py --from-cache data/ --oracle-sweep
```

This loads the cached judge results from `data/` and runs CJE calibration locally. You should see:
- GPT-4o-mini: calibrated estimate **0.6711**, raw confidence 0.916, shift **-0.2449**
- Claude Haiku 4.5: calibrated estimate **0.6712**, raw confidence 0.802, shift **-0.1303**

## Full Reproduction (API Keys Required)

Run the complete pipeline from scratch (~$150-200 in API costs for two judges on 29,511 records):

```bash
pip install -e .
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...

# Main calibration analysis
python scripts/run_judges.py \
    --judges openai/gpt-4o-mini anthropic/claude-haiku-4-5-20251001 \
    --oracle-sweep

# 2x2 ablation: judge score type x oracle label type
python scripts/run_ablation.py

# Prompt A/B confound check (does adding "confidence" to the prompt change binary judgments?)
python scripts/run_prompt_ab.py
```

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
  judge_results_openai_gpt-4o-mini.jsonl
  judge_results_anthropic_claude-haiku-4-5-20251001.jsonl
```

The 130 MB `meta_eval.jsonl` dataset is **not** included — it's publicly available from OpenAI and downloaded automatically on first run.

## Links

- **Blog post**: [When the Judge is Wrong](https://cimolabs.com/blog/judge-calibration-docs)
- **CJE paper**: [arXiv:2512.11150](https://arxiv.org/abs/2512.11150)
- **CJE library**: [github.com/cimo-labs/cje](https://github.com/cimo-labs/cje) / `pip install cje-eval`
- **inspect_evals PR**: [#1206](https://github.com/UKGovernmentBEIS/inspect_evals/pull/1206) (generic judge calibration tool)
- **HealthBench**: [OpenAI HealthBench](https://github.com/openai/healthbench)

## License

MIT
