"""
Production daily cycle: orchestration only. Domain logic in core.data / signals / allocation / execution.

Reads and writes canonical paths under state/ via infra.state_paths (no legacy mirroring).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Dict, List

from core.allocation.meta_allocator import main as allocator_main
from core.data.collector_t212 import main as collect_data_main
from core.execution.position_checker import main as checker_main
from core.execution.trade_executor import main as executor_main
from core.monitoring.state_freshness import (
    FreshnessError,
    assert_required_symbols,
    file_not_empty,
    validate_raw_state,
    validate_signal_state,
    validate_target_state,
    validate_trade_state,
)
from core.risk.gate import validate_targets_sum
from core.risk.policy_engine import run_target_policy_check
from core.risk.pretrade_checks import run_pretrade_checks
from core.services.quote_fallback import REQUIRED_REGIME_PRICE_SYMBOLS
from core.signals.regime_from_market import main as regime_main
from infra.locks import FileLock, LockError
from infra.state_paths import (
    CYCLE_AUDIT,
    PORTFOLIO,
    PRICES,
    REGIME,
    ROOT,
    RUN_LOCK,
    TARGETS_FILE,
    TRADE_LIST,
    ensure_state_dirs,
)

REQUIRED_SYMBOLS = list(REQUIRED_REGIME_PRICE_SYMBOLS)


def write_audit(event: dict) -> None:
    CYCLE_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with CYCLE_AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")


def stage_result(name: str, status: str, detail: str = "") -> dict:
    return {
        "stage": name,
        "status": status,
        "detail": detail,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def run_cycle(*, dry_run: bool, raw_max_age_minutes: int) -> None:
    cycle_ts = datetime.now(timezone.utc).isoformat()
    stages: List[dict] = []

    with FileLock(RUN_LOCK, stale_after_seconds=60 * 60):
        ensure_state_dirs()
        stages.append(stage_result("bootstrap", "ok", "State directories ensured"))

        collect_meta = collect_data_main(dry_run=dry_run)
        src = collect_meta.get("quote_data_source", "unknown")
        stages.append(
            stage_result("collect", "ok", f"Collected prices and portfolio (quotes={src})")
        )

        validate_raw_state(PRICES, PORTFOLIO, max_age_minutes=raw_max_age_minutes)
        assert_required_symbols(PRICES, REQUIRED_SYMBOLS)
        stages.append(stage_result("raw_validation", "ok", "Raw state validated"))

        regime_main()
        validate_signal_state(PRICES, REGIME)
        stages.append(stage_result("signals", "ok", "Regime computed and validated"))

        allocator_main()
        validate_target_state(REGIME, TARGETS_FILE)
        stages.append(stage_result("allocator", "ok", "Targets built and validated"))

        ok, msg = validate_targets_sum()
        if not ok:
            raise RuntimeError(f"target_gate: {msg}")
        stages.append(stage_result("target_gate", "ok", msg))

        run_target_policy_check()
        stages.append(stage_result("policy", "ok", "Target risk policy OK"))

        checker_main()
        validate_trade_state(TARGETS_FILE, TRADE_LIST)
        stages.append(stage_result("trade_generation", "ok", "Trade list generated"))

        run_pretrade_checks(
            targets_path=TARGETS_FILE,
            trade_list_path=TRADE_LIST,
            prices_path=PRICES,
            allow_empty_trade_list=True,
        )
        stages.append(stage_result("pretrade_checks", "ok", "Pre-trade checks passed"))

        if dry_run:
            stages.append(
                stage_result("execution", "skipped", "dry_run: no broker orders")
            )
            write_audit(
                {
                    "ts": cycle_ts,
                    "status": "success",
                    "stages": stages,
                    "dry_run": True,
                    "quote_data_source": collect_meta.get("quote_data_source"),
                    "quote_fallback_paths": collect_meta.get("quote_fallback_paths") or [],
                }
            )
            return

        rc = executor_main()
        if rc != 0:
            raise RuntimeError(f"trade_executor exited {rc}")

        stages.append(stage_result("execution", "ok", "Execution completed"))

        write_audit(
            {
                "ts": cycle_ts,
                "status": "success",
                "stages": stages,
                "dry_run": False,
                "quote_data_source": collect_meta.get("quote_data_source"),
                "quote_fallback_paths": collect_meta.get("quote_fallback_paths") or [],
            }
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="HEDGE daily production cycle")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run through trade generation only; skip broker execution.",
    )
    parser.add_argument(
        "--freshness-minutes",
        type=int,
        default=int(os.environ.get("HEDGE_FRESHNESS_MINUTES", "180")),
        help="Max age for mirrored raw prices/portfolio files (default 180, env HEDGE_FRESHNESS_MINUTES).",
    )
    parser.epilog = (
        "Quote fallback: with --dry-run, missing regime prices may be filled from "
        "state/raw/cached_quotes.json then tests/fixtures/regime_quotes.json. "
        "Without --dry-run, fallback requires HEDGE_ALLOW_CACHED_QUOTES=1 (non-production)."
    )
    args = parser.parse_args()

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    try:
        run_cycle(dry_run=args.dry_run, raw_max_age_minutes=args.freshness_minutes)
        print("✅ Daily cycle finished.")
        return 0
    except LockError as exc:
        write_audit(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "status": "skipped",
                "reason": f"lock_error: {exc}",
            }
        )
        print(str(exc), file=sys.stderr)
        return 2
    except FreshnessError as exc:
        write_audit(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "reason": f"freshness_error: {exc}",
                "traceback": traceback.format_exc(),
            }
        )
        print(f"❌ {exc}", file=sys.stderr)
        return 3
    except RuntimeError as exc:
        write_audit(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "reason": str(exc),
                "traceback": traceback.format_exc(),
            }
        )
        print(str(exc), file=sys.stderr)
        return 4
    except Exception as exc:  # noqa: BLE001
        write_audit(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
                "reason": f"unhandled_error: {exc}",
                "traceback": traceback.format_exc(),
            }
        )
        print(str(exc), file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
