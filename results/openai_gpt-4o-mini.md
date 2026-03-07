# HealthBench Judge Calibration: openai/gpt-4o-mini

## Summary

- **Total cached rows**: 29511
- **Parse success (cached)**: 29510/29511 (100.00%)
- **Rows analyzed**: 29510 (excluded parse failures: 1)
- **Conversation clusters**: 14592 (CJE prompt_id for clustered inference)
- **Parse-failure policy**: excluded
- **Physician oracle**: 19804 positive (67.1%), 9706 negative (32.9%)
- **Judge binary**: 21414 positive (72.6%)
- **Judge confidence**: mean=0.916, min=0.000, max=1.000

## Binary Judge Performance (vs Physician Consensus)

| | Physician=Met | Physician=Not Met |
|---|---|---|
| **Judge=Met** | 15933 (TP) | 5481 (FP) |
| **Judge=Not Met** | 3871 (FN) | 4225 (TN) |

- **Accuracy**: 0.683
- **Precision**: 0.744
- **Recall**: 0.805
- **F1**: 0.773

## CJE Calibrated Estimate

- **Raw judge mean confidence**: 0.9160
- **Calibrated estimate**: 0.6711 (SE: 0.0030)
- **95% CI**: [0.6656, 0.6776]
- **Calibration shift**: -0.2449 (judge overconfident)

- **Mode**: direct
- **Estimator**: direct

## Per-Category Analysis

| Category | N | Physician % Met | Judge % Met | Mean Confidence | Accuracy |
|----------|---|----------------|-------------|-----------------|----------|
| communication not-health-professional ac | 1685 | 73.4% | 91.3% | 0.977 | 75.1% |
| communication not-health-professional ta | 1685 | 74.3% | 90.6% | 0.968 | 80.2% |
| communication health-professional accura | 1276 | 66.5% | 98.4% | 0.993 | 66.8% |
| communication health-professional tailor | 1276 | 74.1% | 97.5% | 0.990 | 75.6% |
| hedging any-reducible-uncertainty accura | 1140 | 84.5% | 98.0% | 0.996 | 86.0% |
| hedging any-reducible-uncertainty hedges | 1140 | 77.9% | 73.9% | 0.923 | 69.9% |
| hedging any-reducible-uncertainty seeks  | 1140 | 27.1% | 22.7% | 0.817 | 81.4% |
| hedging no-uncertainty accurate | 910 | 83.5% | 96.9% | 0.993 | 85.9% |
| hedging no-uncertainty hedges | 910 | 83.4% | 75.4% | 0.927 | 72.2% |
| hedging no-uncertainty seeks context | 910 | 86.5% | 0.4% | 0.903 | 13.7% |
| context seeking enough-context precise | 896 | 66.7% | 90.1% | 0.958 | 70.2% |
| context seeking enough-context helpful s | 896 | 70.5% | 93.1% | 0.960 | 73.9% |
| global health context-does-not-matter al | 873 | 80.4% | 96.2% | 0.990 | 82.6% |
| global health context-matters-but-unclea | 870 | 49.1% | 64.9% | 0.897 | 61.4% |
| health data tasks enough-info-to-complet | 848 | 48.7% | 66.6% | 0.905 | 59.2% |
| health data tasks enough-info-to-complet | 848 | 56.0% | 78.5% | 0.963 | 71.8% |
| hedging only-irreducible-uncertainty acc | 792 | 80.8% | 95.3% | 0.988 | 84.2% |
| hedging only-irreducible-uncertainty hed | 792 | 76.6% | 80.4% | 0.893 | 78.0% |
| hedging only-irreducible-uncertainty see | 792 | 84.8% | 0.9% | 0.903 | 15.0% |
| global health context-matters-is-clear a | 772 | 72.5% | 97.5% | 0.988 | 73.7% |
| context seeking not-enough-context conte | 719 | 25.7% | 20.7% | 0.722 | 80.5% |
| context seeking not-enough-context helpf | 719 | 55.4% | 71.8% | 0.844 | 66.9% |
| emergency referrals conditionally-emerge | 717 | 44.8% | 75.6% | 0.871 | 61.6% |
| emergency referrals conditionally-emerge | 717 | 48.3% | 73.1% | 0.919 | 62.9% |
| health data tasks not-enough-info-to-com | 709 | 41.3% | 41.2% | 0.837 | 57.8% |
| health data tasks not-enough-info-to-com | 709 | 82.2% | 70.9% | 0.902 | 78.3% |
| complex responses simple accuracy hedgin | 652 | 77.3% | 33.7% | 0.702 | 42.9% |
| complex responses simple appropriate | 652 | 73.3% | 58.3% | 0.825 | 65.0% |
| complex responses detailed appropriate | 644 | 64.1% | 81.8% | 0.921 | 66.8% |
| complex responses detailed accuracy hedg | 643 | 61.4% | 8.7% | 0.531 | 40.4% |
| emergency referrals emergent emergency b | 553 | 55.9% | 74.3% | 0.872 | 71.4% |
| emergency referrals emergent context see | 553 | 64.6% | 95.8% | 0.985 | 66.9% |
| emergency referrals non-emergent emergen | 536 | 72.8% | 84.3% | 0.916 | 70.9% |
| emergency referrals non-emergent context | 536 | 67.0% | 98.1% | 0.989 | 68.5% |

## Oracle Coverage Sweep: openai/gpt-4o-mini

| Oracle % | Oracle N | Calibrated Est | SE | 95% CI | Shift |
|----------|----------|----------------|-----|--------|-------|
| 100% | 29510 | 0.6711 | 0.0030 | [0.6656, 0.6776] | -0.2449 |
| 50% | 14802 | 0.6736 | 0.0039 | [0.6666, 0.6809] | -0.2423 |
| 25% | 7408 | 0.6689 | 0.0054 | [0.6597, 0.6793] | -0.2470 |
| 10% | 2863 | 0.6828 | 0.0085 | [0.6666, 0.6999] | -0.2332 |
| 5% | 1454 | 0.6918 | 0.0121 | [0.6690, 0.7164] | -0.2242 |
