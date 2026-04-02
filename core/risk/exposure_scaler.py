"""Scale gross exposure from realized vs target volatility (deterministic)."""

from __future__ import annotations


def exposure_multiplier(
    *,
    realized_vol_annual: float,
    target_vol_annual: float,
    min_mult: float = 0.5,
    max_mult: float = 1.0,
) -> float:
    """
    When realized vol exceeds target, scale exposure down; when below, up (capped).

    multiplier ≈ target_vol / realized_vol, clamped to [min_mult, max_mult].
    """
    if target_vol_annual <= 0 or realized_vol_annual <= 0:
        return max_mult
    raw = target_vol_annual / realized_vol_annual
    return max(min_mult, min(max_mult, raw))
