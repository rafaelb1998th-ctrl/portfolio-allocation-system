"""Build individual-stock sleeve from momentum + holding manager (pilot sleeve)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from core.allocation.individual_stocks import get_weights as static_individual_stocks_weights
from core.allocation.stock_selector import select_top_symbols
from core.research.holding_manager import resolve_holdings
from core.research.momentum import momentum_scores
from infra.state_paths import ROOT, STOCK_CLOSES


def _research_cfg(policy: Dict[str, Any]) -> Dict[str, Any]:
    return (policy.get("research") or {}).get("momentum_stocks") or {}


def _universe(policy: Dict[str, Any], whitelist: Dict[str, Any]) -> List[str]:
    u = policy.get("research", {}).get("individual_stock_universe")
    if isinstance(u, list) and u:
        return [str(s) for s in u]
    buckets = whitelist.get("buckets") or {}
    b = buckets.get("individual_stocks")
    if isinstance(b, list) and b:
        return [str(s) for s in b]
    return [
        "AAPL",
        "MSFT",
        "GOOGL",
        "NVDA",
        "AMZN",
        "META",
        "JPM",
        "BAC",
        "V",
        "MA",
        "GS",
        "UNH",
        "JNJ",
        "PFE",
        "ABT",
        "TMO",
        "WMT",
        "HD",
        "COST",
        "NKE",
        "CAT",
        "HON",
    ]


def _load_closes_file(path: Path) -> Dict[str, List[float]]:
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        return {}
    raw = doc.get("closes") if isinstance(doc, dict) and "closes" in doc else doc
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, List[float]] = {}
    for k, v in raw.items():
        if isinstance(v, list) and len(v) >= 2:
            try:
                out[str(k)] = [float(x) for x in v]
            except (TypeError, ValueError):
                continue
    return out


def _fetch_yfinance_closes(symbols: List[str], period: str = "6mo") -> Dict[str, List[float]]:
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        return {}
    out: Dict[str, List[float]] = {}
    for s in symbols:
        try:
            hist = yf.Ticker(s).history(period=period, auto_adjust=True)
            if hist is None or hist.empty:
                continue
            closes = hist["Close"].astype(float).tolist()
            if len(closes) >= 21:
                out[s] = closes
        except Exception:
            continue
    return out


def _current_holdings_in_universe(portfolio: Dict[str, Any], universe: Set[str]) -> List[str]:
    found: List[str] = []
    for p in portfolio.get("positions", []) or []:
        sym = p.get("symbol")
        if not sym or str(sym) not in universe:
            continue
        try:
            v = float(p.get("value", 0) or 0)
        except (TypeError, ValueError):
            v = 0.0
        if v > 0:
            found.append(str(sym))
    return found


def build_momentum_individual_stocks_sleeve(
    *,
    portfolio: Dict[str, Any],
    regime: str,
    confidence: float,
    policy: Dict[str, Any],
    whitelist: Dict[str, Any],
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Returns (weights summing to 1.0 within sleeve, meta for targets.json).
    Falls back to static individual_stocks if disabled or insufficient data.
    """
    rcfg = _research_cfg(policy)
    if rcfg.get("enabled") is False:
        w = static_individual_stocks_weights(regime, confidence)
        return w, {"mode": "static", "reason": "research.momentum_stocks.enabled=false"}

    top_n = int(rcfg.get("top_n", 5))
    min_score = float(rcfg.get("min_score", 0.55))
    max_turn = float(rcfg.get("max_turnover_fraction", 0.25))
    try_yf = bool(rcfg.get("try_yfinance", True))

    universe = _universe(policy, whitelist)
    universe_set = set(universe)

    cp = rcfg.get("closes_path")
    if cp:
        primary = Path(str(cp))
        if not primary.is_absolute():
            primary = ROOT / primary
    else:
        primary = STOCK_CLOSES
    closes = _load_closes_file(primary)

    fb = rcfg.get("fallback_closes_path")
    if fb:
        p2 = ROOT / str(fb)
        if not p2.is_absolute():
            p2 = ROOT / p2
        if not closes:
            closes = _load_closes_file(p2)
        else:
            extra = _load_closes_file(p2)
            for k, v in extra.items():
                closes.setdefault(k, v)

    missing = [s for s in universe if s not in closes or len(closes[s]) < 21]
    if try_yf and missing:
        yf_data = _fetch_yfinance_closes(missing)
        for k, v in yf_data.items():
            closes[k] = v

    scoped = {s: closes[s] for s in universe if s in closes and len(closes[s]) >= 2}
    scores = momentum_scores(scoped)

    ranked_elite = select_top_symbols(
        scores, top_n=max(50, len(universe)), min_score=min_score
    )
    if not ranked_elite:
        w = static_individual_stocks_weights(regime, confidence)
        return w, {
            "mode": "static_fallback",
            "reason": "no_symbols_passed_momentum_min_score_or_no_price_history",
            "min_score": min_score,
            "top_n": top_n,
        }

    current = _current_holdings_in_universe(portfolio, universe_set)
    final_syms = resolve_holdings(
        current,
        ranked_elite,
        portfolio_slots=top_n,
        max_turnover_fraction=max_turn,
    )
    if not final_syms:
        w = static_individual_stocks_weights(regime, confidence)
        return w, {
            "mode": "static_fallback",
            "reason": "holding_manager_returned_empty",
            "ranked_elite": ranked_elite,
            "current_holdings": current,
        }

    ew = 1.0 / len(final_syms)
    weights = {s: ew for s in final_syms}

    meta = {
        "mode": "momentum_equal_weight",
        "top_n": top_n,
        "min_score": min_score,
        "max_turnover_fraction": max_turn,
        "selected": list(final_syms),
        "scores": {s: round(float(scores.get(s, 0.0)), 4) for s in final_syms},
        "ranked_elite": ranked_elite,
        "current_holdings_before": current,
        "holding_manager_applied": True,
        "closes_source": "file+yfinance" if try_yf else "file",
    }
    return weights, meta
