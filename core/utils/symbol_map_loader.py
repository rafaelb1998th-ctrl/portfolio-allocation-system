"""Load brokers/symbol_map.json and derive regime-quote candidate tickers (T212 IDs)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_symbol_map() -> Dict[str, Any]:
    path = _project_root() / "brokers" / "symbol_map.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Keys used by core.signals.regime_from_market ratio() logic
REGIME_INTERNAL_SYMBOLS: List[str] = [
    "XLP",
    "XLY",
    "XLU",
    "XLI",
    "XLV",
    "XLK",
    "XLF",
    "GLD",
    "SPY",
]


def regime_signal_t212_candidates() -> Dict[str, List[str]]:
    """Internal regime symbol -> ordered list of T212 tickers to request quotes for."""
    m = load_symbol_map()
    out: Dict[str, List[str]] = {}
    for key in REGIME_INTERNAL_SYMBOLS:
        info = m.get(key)
        if not info:
            continue
        primary = info.get("t212")
        alts = info.get("t212_alt") or []
        cands = [primary] + (list(alts) if isinstance(alts, list) else [])
        out[key] = [c for c in cands if c]
    return out


def t212_to_internal_map() -> Dict[str, str]:
    """Resolve T212 ticker -> internal symbol for portfolio naming."""
    m = load_symbol_map()
    rev: Dict[str, str] = {}
    for internal, info in m.items():
        t = info.get("t212")
        if t:
            rev[str(t)] = internal
        for alt in info.get("t212_alt") or []:
            if alt:
                rev[str(alt)] = internal
    return rev
