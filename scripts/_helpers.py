"""Vendored utility functions for the HealthBench judge audit.

_ensure_ci_scale is extracted from inspect_evals/tools/judge_calibration_diagnostics.py
to avoid requiring a full inspect_evals checkout.
"""

from __future__ import annotations

from typing import Any


def _ensure_ci_scale(
    estimates: Any,
    ci_lower: Any,
    ci_upper: Any,
    results: Any,
) -> tuple[Any, Any]:
    """Defensive guard: denormalize CIs if they appear on a different scale than estimates.

    CJE normalizes scores internally and should denormalize all outputs.
    This catches edge cases where CIs remain on the normalized [0,1] scale
    while estimates are on the original score scale.
    """
    if ci_lower is None or ci_upper is None:
        return ci_lower, ci_upper

    import numpy as np

    est = np.asarray(estimates)
    ci_lo = np.asarray(ci_lower, dtype=float)
    ci_hi = np.asarray(ci_upper, dtype=float)

    if len(est) == 0 or len(ci_lo) == 0 or len(ci_hi) == 0:
        return ci_lower, ci_upper

    # Check: does each CI contain its estimate?  If so, scales match.
    contains = (ci_lo <= est + 1e-9) & (est - 1e-9 <= ci_hi)
    if np.all(contains):
        return ci_lower, ci_upper

    # CIs don't contain estimates — try denormalization if metadata is available.
    meta = getattr(results, "metadata", None) or {}
    norm = meta.get("normalization", {})

    expected_range_len = 2
    candidate_ranges: list[tuple[float, float]] = []

    # Legacy schema: normalization.original_range
    legacy_range = norm.get("original_range")
    if legacy_range and len(legacy_range) == expected_range_len:
        candidate_ranges.append((float(legacy_range[0]), float(legacy_range[1])))

    # Current schema: normalization.{judge_score,oracle_label}.original_range
    # plus normalization.results_scale indicating the intended estimate scale.
    results_scale = str(norm.get("results_scale", "")).lower()
    preferred_keys: list[str] = []
    if results_scale.startswith("oracle"):
        preferred_keys.append("oracle_label")
    elif results_scale.startswith("judge"):
        preferred_keys.append("judge_score")
    # Keep both as fallbacks (in deterministic order) for robustness.
    for key in ("oracle_label", "judge_score"):
        if key not in preferred_keys:
            preferred_keys.append(key)

    for key in preferred_keys:
        entry = norm.get(key)
        if isinstance(entry, dict):
            key_range = entry.get("original_range")
            if key_range and len(key_range) == expected_range_len:
                candidate_ranges.append((float(key_range[0]), float(key_range[1])))

    if not candidate_ranges:
        return ci_lower, ci_upper

    # Deduplicate while preserving order.
    unique_ranges = list(dict.fromkeys(candidate_ranges))

    # Choose the denormalization that maximizes CI containment for estimates.
    best_contained = int(np.sum(contains))
    best_bounds: tuple[Any, Any] | None = None
    for lo, hi in unique_ranges:
        span = hi - lo
        if span <= 0:
            continue
        denorm_lo = ci_lo * span + lo
        denorm_hi = ci_hi * span + lo
        denorm_contains = (denorm_lo <= est + 1e-9) & (est - 1e-9 <= denorm_hi)
        denorm_contained = int(np.sum(denorm_contains))
        if denorm_contained > best_contained:
            best_contained = denorm_contained
            best_bounds = (denorm_lo, denorm_hi)

    # Only apply denormalization if it improves containment.
    if best_bounds is not None:
        return best_bounds

    return ci_lower, ci_upper
