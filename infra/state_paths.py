"""Canonical paths: nested state layout + legacy flat files (until modules migrate)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "state"

RAW = STATE / "raw"
SIGNALS = STATE / "signals"
TARGETS = STATE / "targets"
TRADES = STATE / "trades"
PERFORMANCE = STATE / "performance"
OPS = STATE / "ops"

PRICES = RAW / "prices.json"
PORTFOLIO = RAW / "portfolio.json"
# Optional daily closes for momentum stock sleeve (symbol -> [float, ...] oldest first)
STOCK_CLOSES = RAW / "stock_closes.json"
# Optional local snapshot for dry-run / sandbox (see core/services/quote_fallback.py)
CACHED_QUOTES = RAW / "cached_quotes.json"
# Committed fixture for CI and restricted API plans
REGIME_QUOTES_FIXTURE = ROOT / "tests" / "fixtures" / "regime_quotes.json"

REGIME = SIGNALS / "regime.json"

TARGETS_FILE = TARGETS / "targets.json"

TRADE_LIST = TRADES / "trade_list.json"
EXECUTIONS_LOG = TRADES / "executions.log.jsonl"

SLEEVE_PERFORMANCE = PERFORMANCE / "sleeve_performance.json"
NAV_HISTORY = PERFORMANCE / "nav_history.jsonl"
PREV_SLEEVE_SCORES = PERFORMANCE / "prev_sleeve_scores.json"
SLEEVE_ATTRIBUTION_HISTORY = PERFORMANCE / "sleeve_attribution_history.jsonl"
HEALTH_STATUS = OPS / "health_status.json"
LAST_REGIME = OPS / "last_regime.json"
LAST_DRIFT_STATE = OPS / "last_drift_state.json"
RUN_LOCK = OPS / "run.lock"
CYCLE_AUDIT = OPS / "cycle_audit.jsonl"

# Flat paths still written/read by unmigrated services
LEGACY_PRICES = STATE / "prices.json"
LEGACY_PORTFOLIO = STATE / "portfolio.json"
LEGACY_REGIME = STATE / "regime.json"
LEGACY_TARGETS = STATE / "targets.json"
LEGACY_TRADE_LIST = STATE / "trade_list.json"
LEGACY_EXECUTIONS_LOG = STATE / "executions.log.jsonl"


def ensure_state_dirs() -> None:
    for path in (RAW, SIGNALS, TARGETS, TRADES, PERFORMANCE, OPS):
        path.mkdir(parents=True, exist_ok=True)
