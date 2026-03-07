# HealthBench Judge/Oracle Information Ablation

## Summary

- **meta_eval rows**: 29511
- **cached judge rows**: 29511
- **joined rows**: 29501
- **missing joins**: 0
- **parse-ok joined rows**: 29501 (100.00%)
- **conversation clusters**: 14592
- **parse-failure policy**: excluded
- **continuous oracle range**: [0.000, 1.000]

## Full-Coverage Results (100% Oracle)

| Condition | Judge Score | Oracle Label | Estimate | SE | 95% CI | Shift vs Raw |
|---|---|---|---:|---:|---|---:|
| A | judge_continuous | oracle_binary_majority | 0.6712 | 0.0028 | [0.6664, 0.6771] | -0.1303 |
| B | judge_binary | oracle_binary_majority | 0.6711 | 0.0028 | [0.6663, 0.6770] | -0.0052 |
| C | judge_continuous | oracle_continuous_agreement | 0.7717 | 0.0020 | [0.7685, 0.7758] | -0.0298 |
| D | judge_binary | oracle_continuous_agreement | 0.7718 | 0.0020 | [0.7685, 0.7758] | +0.0955 |

## Oracle Coverage Sweep by Condition

### Condition A: judge_continuous + oracle_binary_majority

| Oracle % | Oracle N | Estimate | SE | 95% CI | Shift vs Raw |
|---|---:|---:|---:|---|---:|
| 100% | 29501 | 0.6712 | 0.0028 | [0.6664, 0.6771] | -0.1303 |
| 50% | 14798 | 0.6737 | 0.0037 | [0.6673, 0.6810] | -0.1278 |
| 25% | 7406 | 0.6670 | 0.0054 | [0.6561, 0.6773] | -0.1345 |
| 10% | 2863 | 0.6778 | 0.0094 | [0.6598, 0.6955] | -0.1237 |
| 5% | 1454 | 0.6852 | 0.0126 | [0.6655, 0.7120] | -0.1163 |

### Condition B: judge_binary + oracle_binary_majority

| Oracle % | Oracle N | Estimate | SE | 95% CI | Shift vs Raw |
|---|---:|---:|---:|---|---:|
| 100% | 29501 | 0.6711 | 0.0028 | [0.6663, 0.6770] | -0.0052 |
| 50% | 14798 | 0.6729 | 0.0036 | [0.6670, 0.6793] | -0.0034 |
| 25% | 7406 | 0.6662 | 0.0049 | [0.6570, 0.6757] | -0.0100 |
| 10% | 2863 | 0.6737 | 0.0087 | [0.6561, 0.6896] | -0.0026 |
| 5% | 1454 | 0.6791 | 0.0122 | [0.6592, 0.7038] | +0.0028 |

### Condition C: judge_continuous + oracle_continuous_agreement

| Oracle % | Oracle N | Estimate | SE | 95% CI | Shift vs Raw |
|---|---:|---:|---:|---|---:|
| 100% | 29501 | 0.7717 | 0.0020 | [0.7685, 0.7758] | -0.0298 |
| 50% | 14798 | 0.7738 | 0.0026 | [0.7693, 0.7790] | -0.0277 |
| 25% | 7406 | 0.7700 | 0.0039 | [0.7628, 0.7775] | -0.0315 |
| 10% | 2863 | 0.7752 | 0.0068 | [0.7621, 0.7876] | -0.0263 |
| 5% | 1454 | 0.7787 | 0.0100 | [0.7605, 0.7993] | -0.0228 |

### Condition D: judge_binary + oracle_continuous_agreement

| Oracle % | Oracle N | Estimate | SE | 95% CI | Shift vs Raw |
|---|---:|---:|---:|---|---:|
| 100% | 29501 | 0.7718 | 0.0020 | [0.7685, 0.7758] | +0.0955 |
| 50% | 14798 | 0.7732 | 0.0025 | [0.7689, 0.7776] | +0.0969 |
| 25% | 7406 | 0.7691 | 0.0035 | [0.7622, 0.7755] | +0.0928 |
| 10% | 2863 | 0.7724 | 0.0062 | [0.7608, 0.7841] | +0.0961 |
| 5% | 1454 | 0.7757 | 0.0094 | [0.7583, 0.7936] | +0.0994 |

## Delta vs Baseline (Condition A)

| Oracle % | Baseline A Est | B-A | C-A | D-A |
|---|---:|---:|---:|---:|
| 100% | 0.6712 | -0.0001 | +0.1005 | +0.1006 |
| 50% | 0.6737 | -0.0008 | +0.1001 | +0.0995 |
| 25% | 0.6670 | -0.0007 | +0.1030 | +0.1021 |
| 10% | 0.6778 | -0.0041 | +0.0974 | +0.0946 |
| 5% | 0.6852 | -0.0060 | +0.0935 | +0.0905 |

## Validation Checks

- **Join integrity**: 29501 joined rows (expected 29501)
- **Continuous oracle in [0,1]**: True
- **CI contains estimate (all runs)**: True
