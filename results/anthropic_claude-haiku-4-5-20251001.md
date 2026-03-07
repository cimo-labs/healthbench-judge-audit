# HealthBench Judge Calibration: anthropic/claude-haiku-4-5-20251001

## Summary

- **Total cached rows**: 29511
- **Parse success (cached)**: 29501/29511 (99.97%)
- **Rows analyzed**: 29501 (excluded parse failures: 10)
- **Conversation clusters**: 14592 (CJE prompt_id for clustered inference)
- **Parse-failure policy**: excluded
- **Physician oracle**: 19799 positive (67.1%), 9702 negative (32.9%)
- **Judge binary**: 19951 positive (67.6%)
- **Judge confidence**: mean=0.801, min=0.000, max=0.990

## Binary Judge Performance (vs Physician Consensus)

| | Physician=Met | Physician=Not Met |
|---|---|---|
| **Judge=Met** | 15737 (TP) | 4214 (FP) |
| **Judge=Not Met** | 4062 (FN) | 5488 (TN) |

- **Accuracy**: 0.719
- **Precision**: 0.789
- **Recall**: 0.795
- **F1**: 0.792

## CJE Calibrated Estimate

- **Raw judge mean confidence**: 0.8015
- **Calibrated estimate**: 0.6712 (SE: 0.0030)
- **95% CI**: [0.6656, 0.6774]
- **Calibration shift**: -0.1303 (judge overconfident)

- **Mode**: direct
- **Estimator**: direct

## Per-Category Analysis

| Category | N | Physician % Met | Judge % Met | Mean Confidence | Accuracy |
|----------|---|----------------|-------------|-----------------|----------|
| communication not-health-professional ac | 1685 | 73.4% | 84.0% | 0.857 | 75.2% |
| communication not-health-professional ta | 1684 | 74.3% | 83.1% | 0.804 | 77.4% |
| communication health-professional tailor | 1276 | 74.1% | 78.0% | 0.744 | 73.4% |
| communication health-professional accura | 1275 | 66.5% | 84.0% | 0.775 | 65.7% |
| hedging any-reducible-uncertainty accura | 1140 | 84.5% | 90.2% | 0.886 | 84.8% |
| hedging any-reducible-uncertainty hedges | 1140 | 77.9% | 27.5% | 0.787 | 42.5% |
| hedging any-reducible-uncertainty seeks  | 1140 | 27.1% | 24.4% | 0.646 | 81.5% |
| hedging no-uncertainty accurate | 910 | 83.5% | 92.4% | 0.909 | 87.1% |
| hedging no-uncertainty seeks context | 910 | 86.5% | 73.6% | 0.942 | 79.0% |
| hedging no-uncertainty hedges | 908 | 83.5% | 68.7% | 0.849 | 68.9% |
| context seeking enough-context precise | 896 | 66.7% | 58.1% | 0.789 | 68.0% |
| context seeking enough-context helpful s | 896 | 70.5% | 62.5% | 0.802 | 70.5% |
| global health context-does-not-matter al | 873 | 80.4% | 89.7% | 0.909 | 88.2% |
| global health context-matters-but-unclea | 870 | 49.1% | 55.3% | 0.778 | 64.1% |
| health data tasks enough-info-to-complet | 848 | 56.0% | 68.2% | 0.838 | 69.7% |
| health data tasks enough-info-to-complet | 846 | 48.6% | 58.6% | 0.788 | 66.5% |
| hedging only-irreducible-uncertainty acc | 792 | 80.8% | 86.2% | 0.859 | 85.7% |
| hedging only-irreducible-uncertainty hed | 792 | 76.6% | 79.2% | 0.789 | 78.3% |
| hedging only-irreducible-uncertainty see | 792 | 84.8% | 65.8% | 0.934 | 73.6% |
| global health context-matters-is-clear a | 772 | 72.5% | 91.6% | 0.873 | 77.3% |
| context seeking not-enough-context conte | 719 | 25.7% | 11.8% | 0.805 | 80.8% |
| context seeking not-enough-context helpf | 719 | 55.4% | 67.9% | 0.801 | 70.8% |
| emergency referrals conditionally-emerge | 717 | 44.8% | 57.2% | 0.614 | 61.9% |
| emergency referrals conditionally-emerge | 717 | 48.3% | 59.8% | 0.767 | 68.3% |
| health data tasks not-enough-info-to-com | 709 | 41.3% | 65.4% | 0.879 | 66.9% |
| health data tasks not-enough-info-to-com | 709 | 82.2% | 63.0% | 0.821 | 73.2% |
| complex responses simple accuracy hedgin | 652 | 77.3% | 61.8% | 0.754 | 67.0% |
| complex responses simple appropriate | 652 | 73.3% | 68.6% | 0.784 | 69.2% |
| complex responses detailed appropriate | 643 | 64.1% | 55.8% | 0.684 | 57.2% |
| complex responses detailed accuracy hedg | 641 | 61.6% | 40.9% | 0.585 | 55.5% |
| emergency referrals emergent emergency b | 553 | 55.9% | 60.0% | 0.675 | 75.6% |
| emergency referrals emergent context see | 553 | 64.6% | 90.4% | 0.888 | 70.9% |
| emergency referrals non-emergent emergen | 536 | 72.8% | 87.1% | 0.811 | 75.2% |
| emergency referrals non-emergent context | 536 | 67.0% | 49.4% | 0.656 | 59.3% |

## Oracle Coverage Sweep: anthropic/claude-haiku-4-5-20251001

| Oracle % | Oracle N | Calibrated Est | SE | 95% CI | Shift |
|----------|----------|----------------|-----|--------|-------|
| 100% | 29501 | 0.6712 | 0.0030 | [0.6656, 0.6774] | -0.1303 |
| 50% | 14798 | 0.6737 | 0.0039 | [0.6666, 0.6810] | -0.1278 |
| 25% | 7406 | 0.6670 | 0.0056 | [0.6569, 0.6780] | -0.1345 |
| 10% | 2863 | 0.6770 | 0.0086 | [0.6613, 0.6949] | -0.1245 |
| 5% | 1454 | 0.6852 | 0.0123 | [0.6622, 0.7117] | -0.1163 |
