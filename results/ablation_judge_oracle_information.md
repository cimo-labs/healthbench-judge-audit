# HealthBench Judge/Oracle Information Ablation

## Summary

- **meta_eval rows**: 29511
- **cached judge rows**: 29511
- **joined rows**: 29510
- **missing joins**: 0
- **parse-ok joined rows**: 29510 (100.00%)
- **conversation clusters**: 14592
- **parse-failure policy**: excluded
- **continuous oracle range**: [0.000, 1.000]

## Full-Coverage Results (100% Oracle)

| Condition | Judge Score | Oracle Label | Estimate | SE | 95% CI | Shift vs Raw |
|---|---|---|---:|---:|---|---:|
| A | judge_continuous | oracle_binary_majority | 0.6711 | 0.0028 | [0.6650, 0.6760] | -0.2449 |
| B | judge_binary | oracle_binary_majority | 0.6711 | 0.0028 | [0.6650, 0.6760] | -0.0546 |
| C | judge_continuous | oracle_continuous_agreement | 0.7717 | 0.0021 | [0.7676, 0.7750] | -0.1442 |
| D | judge_binary | oracle_continuous_agreement | 0.7717 | 0.0021 | [0.7676, 0.7750] | +0.0461 |

## Oracle Coverage Sweep by Condition

### Condition A: judge_continuous + oracle_binary_majority

| Oracle % | Oracle N | Estimate | SE | 95% CI | Shift vs Raw |
|---|---:|---:|---:|---|---:|
| 100% | 29510 | 0.6711 | 0.0028 | [0.6650, 0.6760] | -0.2449 |
| 50% | 14802 | 0.6736 | 0.0042 | [0.6672, 0.6803] | -0.2423 |
| 25% | 7408 | 0.6689 | 0.0049 | [0.6611, 0.6791] | -0.2470 |
| 10% | 2863 | 0.6828 | 0.0087 | [0.6644, 0.6965] | -0.2332 |
| 5% | 1454 | 0.6918 | 0.0126 | [0.6663, 0.7135] | -0.2242 |

### Condition B: judge_binary + oracle_binary_majority

| Oracle % | Oracle N | Estimate | SE | 95% CI | Shift vs Raw |
|---|---:|---:|---:|---|---:|
| 100% | 29510 | 0.6711 | 0.0028 | [0.6650, 0.6760] | -0.0546 |
| 50% | 14802 | 0.6734 | 0.0041 | [0.6669, 0.6803] | -0.0523 |
| 25% | 7408 | 0.6680 | 0.0049 | [0.6599, 0.6775] | -0.0576 |
| 10% | 2863 | 0.6812 | 0.0086 | [0.6628, 0.6964] | -0.0445 |
| 5% | 1454 | 0.6897 | 0.0126 | [0.6639, 0.7126] | -0.0360 |

### Condition C: judge_continuous + oracle_continuous_agreement

| Oracle % | Oracle N | Estimate | SE | 95% CI | Shift vs Raw |
|---|---:|---:|---:|---|---:|
| 100% | 29510 | 0.7717 | 0.0021 | [0.7676, 0.7750] | -0.1442 |
| 50% | 14802 | 0.7738 | 0.0030 | [0.7684, 0.7790] | -0.1422 |
| 25% | 7408 | 0.7714 | 0.0037 | [0.7647, 0.7791] | -0.1446 |
| 10% | 2863 | 0.7800 | 0.0062 | [0.7682, 0.7906] | -0.1360 |
| 5% | 1454 | 0.7853 | 0.0088 | [0.7662, 0.8009] | -0.1306 |

### Condition D: judge_binary + oracle_continuous_agreement

| Oracle % | Oracle N | Estimate | SE | 95% CI | Shift vs Raw |
|---|---:|---:|---:|---|---:|
| 100% | 29510 | 0.7717 | 0.0021 | [0.7676, 0.7750] | +0.0461 |
| 50% | 14802 | 0.7736 | 0.0030 | [0.7679, 0.7783] | +0.0479 |
| 25% | 7408 | 0.7706 | 0.0037 | [0.7642, 0.7776] | +0.0450 |
| 10% | 2863 | 0.7788 | 0.0061 | [0.7665, 0.7902] | +0.0531 |
| 5% | 1454 | 0.7845 | 0.0088 | [0.7645, 0.8009] | +0.0588 |

## Delta vs Baseline (Condition A)

| Oracle % | Baseline A Est | B-A | C-A | D-A |
|---|---:|---:|---:|---:|
| 100% | 0.6711 | -0.0000 | +0.1006 | +0.1006 |
| 50% | 0.6736 | -0.0003 | +0.1002 | +0.0999 |
| 25% | 0.6689 | -0.0009 | +0.1025 | +0.1017 |
| 10% | 0.6828 | -0.0016 | +0.0972 | +0.0960 |
| 5% | 0.6918 | -0.0021 | +0.0936 | +0.0927 |

## Validation Checks

- **Join integrity**: 29510 joined rows (expected 29510)
- **Continuous oracle in [0,1]**: True
- **CI contains estimate (all runs)**: True
