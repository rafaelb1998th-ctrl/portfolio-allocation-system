"""File existence, non-empty, recency, and ordering checks for production cycles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List


class FreshnessError(Exception):
    pass


@dataclass
class FileCheck:
    path: Path
    max_age_minutes: int


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def file_exists(path: Path) -> None:
    if not path.exists():
        raise FreshnessError(f"Missing required file: {path}")


def file_not_empty(path: Path) -> None:
    file_exists(path)
    if path.stat().st_size == 0:
        raise FreshnessError(f"Empty file: {path}")


def file_recent_enough(path: Path, max_age_minutes: int) -> None:
    file_exists(path)
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    if now - mtime > timedelta(minutes=max_age_minutes):
        raise FreshnessError(
            f"Stale file: {path} (older than {max_age_minutes} minutes)"
        )


def assert_required_symbols(prices_path: Path, required_symbols: List[str]) -> None:
    """Ensure each symbol exists under top-level `prices` in the prices JSON."""
    data = _load_json(prices_path)
    if not isinstance(data, dict):
        raise FreshnessError(f"Invalid prices JSON (not an object): {prices_path}")
    prices = data.get("prices")
    if not isinstance(prices, dict):
        raise FreshnessError(f"Missing or invalid 'prices' object in {prices_path}")
    missing = [
        sym
        for sym in required_symbols
        if sym not in prices or prices.get(sym) in (None, 0, 0.0)
    ]
    if missing:
        raise FreshnessError(
            f"Missing or zero price for required symbols in {prices_path}: {missing}"
        )


def assert_mtime_order(older: Path, newer: Path) -> None:
    file_exists(older)
    file_exists(newer)
    if newer.stat().st_mtime < older.stat().st_mtime:
        raise FreshnessError(f"{newer} is older than {older}")


def validate_raw_state(
    prices_path: Path,
    portfolio_path: Path,
    max_age_minutes: int = 180,
) -> None:
    file_not_empty(prices_path)
    file_not_empty(portfolio_path)
    file_recent_enough(prices_path, max_age_minutes=max_age_minutes)
    file_recent_enough(portfolio_path, max_age_minutes=max_age_minutes)


def validate_signal_state(prices_path: Path, regime_path: Path) -> None:
    file_not_empty(regime_path)
    assert_mtime_order(prices_path, regime_path)


def validate_target_state(regime_path: Path, targets_path: Path) -> None:
    file_not_empty(targets_path)
    assert_mtime_order(regime_path, targets_path)


def validate_trade_state(targets_path: Path, trade_list_path: Path) -> None:
    file_not_empty(trade_list_path)
    assert_mtime_order(targets_path, trade_list_path)
