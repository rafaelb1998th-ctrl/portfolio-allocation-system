"""Pick top-N names from momentum scores (deterministic)."""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional


def select_top_symbols(
    scores: Mapping[str, float],
    *,
    top_n: int,
    min_score: Optional[float] = None,
) -> List[str]:
    """
    Return symbols sorted best -> worst, at most `top_n`.
    Tie-break: alphabetical by symbol for stability.
    """
    if top_n <= 0:
        return []
    items = [(str(s), float(v)) for s, v in scores.items()]
    if min_score is not None:
        items = [(s, v) for s, v in items if v >= min_score]
    items.sort(key=lambda x: (-x[1], x[0]))
    return [s for s, _ in items[:top_n]]
