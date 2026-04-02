"""Bond sleeve buckets — institutional-style split (deterministic stub)."""

from __future__ import annotations

from typing import Any, Dict


def fixed_income_bucket_weights(
    regime: str,
    policy: Dict[str, Any] | None = None,
) -> Dict[str, float]:
    """
    Return weights over bond *buckets* (sum to 1.0 within fixed income).

    Not merged into full NAV here — meta_allocator / policy should scale.
    """
    _ = policy
    r = (regime or "").upper()
    if r == "SLOWDOWN":
        return {
            "short_duration": 0.45,
            "long_duration": 0.25,
            "credit": 0.30,
        }
    return {
        "short_duration": 0.30,
        "long_duration": 0.40,
        "credit": 0.30,
    }
