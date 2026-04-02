"""Regime quote fallback for dry-run, CI, and environments without /equity/quotes.

Never used for live cycles unless HEDGE_ALLOW_CACHED_QUOTES=1 (sandbox / restricted keys).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping

from core.monitoring.state_freshness import FreshnessError

# Same set as production gate in app.run_daily_cycle
REQUIRED_REGIME_PRICE_SYMBOLS: tuple[str, ...] = (
    "XLP",
    "XLY",
    "XLU",
    "XLI",
    "GLD",
    "SPY",
    "XLF",
)


def quote_fallback_allowed(*, dry_run: bool) -> bool:
    return dry_run or os.environ.get("HEDGE_ALLOW_CACHED_QUOTES", "").strip() == "1"


def _valid_price(v: Any) -> bool:
    try:
        return v is not None and float(v) > 0
    except (TypeError, ValueError):
        return False


def missing_required_prices(
    prices: Mapping[str, Any], required: tuple[str, ...] | List[str]
) -> List[str]:
    return [s for s in required if not _valid_price(prices.get(s))]


def load_prices_from_fallback_file(path: Path) -> Dict[str, float]:
    """Read JSON: either {\"prices\": {\"XLP\": 1.0}} or a flat numeric object."""
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        return {}
    raw: Dict[str, Any]
    if "prices" in data and isinstance(data["prices"], dict):
        raw = data["prices"]
    else:
        raw = data
    out: Dict[str, float] = {}
    for k, v in raw.items():
        if str(k).startswith("_"):
            continue
        if isinstance(v, dict):
            continue
        try:
            f = float(v)
            if f > 0:
                out[str(k)] = f
        except (TypeError, ValueError):
            continue
    return out


def merge_fallback_files(
    prices: Dict[str, float],
    paths: List[Path],
    required: tuple[str, ...],
) -> tuple[List[str], List[str]]:
    """Merge missing required keys from the first files that exist. Returns (paths_read, still_missing)."""
    read_paths: List[str] = []
    working = dict(prices)
    miss = missing_required_prices(working, required)

    for path in paths:
        if not miss:
            break
        if not path.is_file():
            continue
        extra = load_prices_from_fallback_file(path)
        if not extra:
            continue
        read_paths.append(str(path.resolve()))
        for k, v in extra.items():
            if not _valid_price(working.get(k)):
                working[k] = float(v)
        miss = missing_required_prices(working, required)

    for k, v in working.items():
        prices[k] = v
    return read_paths, miss


def classify_quote_source(
    snap_after_live: Mapping[str, Any],
    final_prices: Mapping[str, Any],
    used_fallback: bool,
) -> str:
    if not used_fallback:
        return "live"
    had_any_live = any(_valid_price(snap_after_live.get(s)) for s in REQUIRED_REGIME_PRICE_SYMBOLS)
    if not had_any_live:
        return "cached"
    return "mixed"


def ensure_regime_prices_or_raise(
    *,
    prices: Dict[str, float],
    snap_after_live: Mapping[str, Any],
    dry_run: bool,
    fallback_paths: List[Path],
) -> tuple[str, List[str]]:
    """Validate required symbols; optionally merge cache/fixture. Returns (quote_data_source, paths_used)."""
    miss = missing_required_prices(prices, REQUIRED_REGIME_PRICE_SYMBOLS)
    if not miss:
        return classify_quote_source(snap_after_live, prices, False), []

    if not quote_fallback_allowed(dry_run=dry_run):
        raise FreshnessError(
            "Live regime quotes incomplete: missing "
            f"{miss}. "
            "Use --dry-run with tests/fixtures/regime_quotes.json or state/raw/cached_quotes.json, "
            "or set HEDGE_ALLOW_CACHED_QUOTES=1 only in non-production/sandbox."
        )

    paths_used, still = merge_fallback_files(
        prices, fallback_paths, REQUIRED_REGIME_PRICE_SYMBOLS
    )
    if still:
        tried = paths_used or [str(p) for p in fallback_paths]
        raise FreshnessError(
            f"Quote fallback enabled but still missing required symbols {still}. "
            f"Files read or candidates: {tried}."
        )

    src = classify_quote_source(snap_after_live, prices, True)
    return src, paths_used
