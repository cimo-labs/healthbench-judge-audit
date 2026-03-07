# HealthBench Prompt A/B Confound Check (gpt-4o-mini)

## Summary

- **Joined records**: 29511
- **Missing in A (confidence prompt cache)**: 0
- **Missing in B (original prompt cache)**: 0
- **B parse success**: 29508/29511 (100.0%)
- **A/B binary agreement**: 0.9493
- **A met rate (confidence prompt)**: 0.7256
- **B met rate (original prompt)**: 0.7023
- **Positive-rate delta (B - A)**: -0.0233

## Binary Metrics vs Physician Majority

| Variant | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| A (confidence prompt) | 0.6831 | 0.7440 | 0.8045 | 0.7731 |
| B (original prompt) | 0.6827 | 0.7519 | 0.7869 | 0.7690 |

| Delta (B - A) | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| B-A | -0.0004 | +0.0078 | -0.0177 | -0.0041 |

## Categories with Highest A/B Flip Rates

| Category | N | Flip Rate | A Met % | B Met % |
|---|---:|---:|---:|---:|
| health_data_tasks_not-enough-info-to-complete-task_safety | 709 | 20.59% | 41.18% | 29.34% |
| complex_responses_detailed_appropriate | 644 | 16.77% | 81.83% | 68.48% |
| emergency_referrals_emergent_emergency_behavior | 553 | 16.46% | 74.32% | 60.04% |
| context_seeking_not-enough-context_helpful_safe | 719 | 13.21% | 71.77% | 61.61% |
| complex_responses_simple_accuracy_hedging | 652 | 11.04% | 33.74% | 36.50% |
| emergency_referrals_conditionally-emergent_context_seeking | 717 | 10.18% | 73.08% | 70.99% |
| health_data_tasks_not-enough-info-to-complete-task_helpfulness | 709 | 9.03% | 70.94% | 68.12% |
| complex_responses_simple_appropriate | 652 | 7.98% | 58.28% | 51.53% |
| emergency_referrals_conditionally-emergent_emergency_behavior | 717 | 7.67% | 75.59% | 69.32% |
| complex_responses_detailed_accuracy_hedging | 644 | 6.83% | 8.70% | 9.01% |
| global_health_context-matters-but-unclear_aligned_accurate | 870 | 6.55% | 64.94% | 65.06% |
| hedging_any-reducible-uncertainty_hedges | 1140 | 6.40% | 73.95% | 70.00% |
| emergency_referrals_non-emergent_emergency_behavior | 536 | 6.34% | 84.33% | 82.46% |
| communication_not-health-professional_accuracy_completeness | 1685 | 5.64% | 91.34% | 88.90% |
| hedging_only-irreducible-uncertainty_hedges | 792 | 5.43% | 80.43% | 81.06% |
