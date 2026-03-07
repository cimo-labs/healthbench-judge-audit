# Data Provenance

## Meta-eval Dataset (not included)

- **Source**: OpenAI HealthBench public release
- **URL**: `https://openaipublic.blob.core.windows.net/simple-evals/healthbench/2025-05-07-06-14-12_oss_meta_eval.jsonl`
- **Size**: ~130 MB, 29,511 records
- **Download**: Automatic on first run of `run_judges.py` (cached to `.cache/meta_eval.jsonl`)

Each meta_eval record contains:
- A multi-turn conversation (`prompt`) with a model-generated response (`completion`)
- A rubric criterion (`rubric`) for evaluation
- Physician binary labels (`binary_labels`) indicating whether the criterion is met
- Category metadata (`category`)

## Judge Results (included)

### `judge_results_openai_gpt-4o-mini.jsonl`

- **Model**: `gpt-4o-mini` via OpenAI API
- **Temperature**: 0.0
- **Prompt variant**: Confidence-augmented (asks for 0.0-1.0 confidence alongside binary)
- **Date run**: March 2025
- **Records**: 29,511 (29,510 parsed successfully)

### `judge_results_anthropic_claude-haiku-4-5-20251001.jsonl`

- **Model**: `claude-haiku-4-5-20251001` via Anthropic API
- **Temperature**: 0.0
- **Prompt variant**: Confidence-augmented (same prompt as GPT-4o-mini)
- **Date run**: March 2025
- **Records**: 29,511 (29,501 parsed successfully)

## JSONL Row Format

Each line is a JSON object with these fields:

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | string | SHA-256 hash (first 16 chars) of `prompt_id:completion_id:rubric` |
| `prompt_id` | string | UUID from meta_eval dataset |
| `completion_id` | string | UUID from meta_eval dataset |
| `category` | string | HealthBench category (e.g., `cluster:emergency_referrals_emergent_emergency_behavior`) |
| `judge_confidence` | float | Judge's confidence score (0.0-1.0) that the criterion is met |
| `judge_binary` | float | Judge's binary determination (1.0 = met, 0.0 = not met) |
| `physician_oracle` | float | Physician majority vote (1.0 = met, 0.0 = not met) |
| `parse_ok` | bool | Whether the judge's JSON response parsed successfully |
| `n_physicians` | int | Number of physician labels for this record |
