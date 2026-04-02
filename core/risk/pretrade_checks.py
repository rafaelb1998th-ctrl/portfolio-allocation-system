"""Pre-execution validation: trade list freshness, whitelist, ordering, notionals, prices."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Set

import yaml

from core.monitoring.state_freshness import FreshnessError, assert_mtime_order
from infra.state_paths import ROOT


class PretradeCheckError(FreshnessError):
    """Raised when trade list fails pre-execution controls."""


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_execution_min_ticket_gbp(policy_path: Path | None = None) -> float:
    path = policy_path or (ROOT / "core" / "policy.yaml")
    try:
        with path.open("r", encoding="utf-8") as f:
            pol = yaml.safe_load(f) or {}
        return float(pol.get("execution", {}).get("min_ticket_gbp", 1.0))
    except Exception:
        return float(os.environ.get("HEDGE_MIN_TICKET_GBP", "1.0"))


def load_whitelisted_symbols() -> Set[str]:
    path = ROOT / "core" / "universe" / "whitelist.yaml"
    out: Set[str] = set()
    try:
        with path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        for _bucket, symbols in (doc.get("buckets") or {}).items():
            if isinstance(symbols, list):
                out.update(str(s) for s in symbols)
    except Exception:
        pass
    return out


def assert_trade_list_fresh(targets_path: Path, trade_list_path: Path) -> None:
    assert_mtime_order(targets_path, trade_list_path)


def assert_no_duplicate_symbols(trades: List[MutableMapping[str, Any]]) -> None:
    symbols = [str(t["symbol"]) for t in trades if t.get("symbol")]
    dupes = [sym for sym, count in Counter(symbols).items() if count > 1]
    if dupes:
        raise PretradeCheckError(f"Duplicate trade symbols: {dupes}")


def assert_sell_before_buy_allocation(trades: List[MutableMapping[str, Any]]) -> None:
    seen_buy = False
    for trade in trades:
        alloc = float(trade.get("allocation", 0) or 0)
        if alloc > 0:
            seen_buy = True
        elif alloc < 0 and seen_buy:
            raise PretradeCheckError("SELL (negative allocation) after BUY in trade list")


def assert_min_ticket(trades: List[MutableMapping[str, Any]], min_ticket_gbp: float) -> None:
    small: List[tuple[Any, float]] = []
    for trade in trades:
        notional = abs(float(trade.get("allocation", 0) or 0))
        if 0 < notional < min_ticket_gbp:
            small.append((trade.get("symbol"), notional))
    if small:
        raise PretradeCheckError(f"Trades below min ticket (£{min_ticket_gbp}): {small}")


def assert_nonzero_allocations(trades: List[MutableMapping[str, Any]]) -> None:
    bad = [t.get("symbol") for t in trades if float(t.get("allocation", 0) or 0) == 0]
    if bad:
        raise PretradeCheckError(f"Zero allocation trades: {bad}")


def assert_symbols_whitelisted(
    trades: List[MutableMapping[str, Any]], allowed: Set[str]
) -> None:
    if not allowed:
        return
    bad: List[Any] = []
    for t in trades:
        sym = t.get("symbol")
        if sym and str(sym) not in allowed:
            bad.append(sym)
    if bad:
        raise PretradeCheckError(f"Symbols not in whitelist: {bad}")


def assert_trade_prices_present(
    trades: List[MutableMapping[str, Any]], prices: Mapping[str, Any]
) -> None:
    missing: List[Any] = []
    for t in trades:
        sym = t.get("symbol")
        if not sym:
            continue
        p = prices.get(str(sym))
        try:
            ok = p is not None and float(p) > 0
        except (TypeError, ValueError):
            ok = False
        if not ok:
            missing.append(sym)
    if missing:
        raise PretradeCheckError(f"Missing or non-positive price for: {missing}")


def run_pretrade_checks(
    *,
    targets_path: Path,
    trade_list_path: Path,
    prices_path: Path,
    allow_empty_trade_list,
    policy_path: Path | None = None,
) -> None:
    payload = load_json(trade_list_path)
    trades: List[MutableMapping[str, Any]] = (
        payload if isinstance(payload, list) else payload.get("trades", []) or []
    )
    if not trades:
        if allow_empty_trade_list:
            return
        raise PretradeCheckError("Trade list is empty (not allowed for this run)")

    assert_trade_list_fresh(targets_path, trade_list_path)
    assert_no_duplicate_symbols(trades)
    assert_nonzero_allocations(trades)
    assert_sell_before_buy_allocation(trades)
    assert_min_ticket(trades, load_execution_min_ticket_gbp(policy_path))
    assert_symbols_whitelisted(trades, load_whitelisted_symbols())

    prices_doc = load_json(prices_path)
    inner = prices_doc.get("prices", {}) if isinstance(prices_doc, dict) else {}
    assert_trade_prices_present(trades, inner if isinstance(inner, dict) else {})
