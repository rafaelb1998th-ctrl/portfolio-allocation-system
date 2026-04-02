"""Multi-horizon momentum scores from price history (deterministic)."""

from __future__ import annotations

from typing import Dict, Mapping, Sequence


# Trading-day lookbacks (approx 1M / 3M / 6M)
LB_1M = 20
LB_3M = 60
LB_6M = 120

W_1M = 0.5
W_3M = 0.3
W_6M = 0.2


def _segment_return(closes: Sequence[float], lookback: int) -> float:
    if len(closes) < 2 or lookback < 1:
        return 0.0
    window = closes[-lookback:] if len(closes) >= lookback else closes
    a, b = float(window[0]), float(window[-1])
    if a <= 0:
        return 0.0
    return (b / a) - 1.0


def raw_momentum_score(closes: Sequence[float]) -> float:
    """Weighted sum of horizon returns; needs enough history for longer legs."""
    r1 = _segment_return(closes, LB_1M)
    r3 = _segment_return(closes, LB_3M)
    r6 = _segment_return(closes, LB_6M)
    return W_1M * r1 + W_3M * r3 + W_6M * r6


def momentum_scores(
    closes_by_symbol: Mapping[str, Sequence[float]],
) -> Dict[str, float]:
    """
    Map symbol -> momentum score in [0, 1] via min-max over raw scores.

    `closes` per symbol: oldest -> newest daily (or consistent bar) closes.
    """
    raw: Dict[str, float] = {}
    for sym, series in closes_by_symbol.items():
        if not series:
            continue
        raw[str(sym)] = raw_momentum_score(series)

    if not raw:
        return {}

    vals = list(raw.values())
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-12:
        return {s: 0.5 for s in raw}

    out: Dict[str, float] = {}
    for s, v in raw.items():
        out[s] = (v - lo) / (hi - lo)
    return out
