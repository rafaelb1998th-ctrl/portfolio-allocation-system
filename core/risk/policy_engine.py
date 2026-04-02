"""Target-level policy checks (max position, etc.). Extend for turnover and drawdown gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

from core.monitoring.state_freshness import FreshnessError
from core.utils.io import read_json
from infra.state_paths import ROOT, TARGETS_FILE


def load_policy(policy_path: Path | None = None) -> Dict[str, Any]:
    path = policy_path or (ROOT / "core" / "policy.yaml")
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as exc:
        raise FreshnessError(f"Could not load policy: {path}: {exc}") from exc


def assert_targets_cash_floor(
    weights: Dict[str, Any],
    cash_floor: float,
    tolerance: float,
) -> None:
    """Fail if CASH target weight is below policy floor (after tolerance)."""
    try:
        c = float(weights.get("CASH", 0) or 0)
    except (TypeError, ValueError):
        c = 0.0
    if c + tolerance < cash_floor:
        raise FreshnessError(
            f"Target CASH weight {c:.4f} below risk.cash_floor {cash_floor:.4f} "
            f"(tolerance {tolerance:.4f})"
        )


def assert_targets_within_max_pos(
    weights: Dict[str, Any],
    max_pos: float,
    tolerance: float,
) -> None:
    """Fail if any single-symbol weight (excl. CASH) exceeds max_pos + tolerance (rounding)."""
    cap = max_pos + tolerance
    violations = []
    for sym, raw in weights.items():
        if str(sym).upper() == "CASH":
            continue
        try:
            w = float(raw)
        except (TypeError, ValueError):
            continue
        if w > cap + 1e-9:
            violations.append((sym, w, max_pos))
    if violations:
        raise FreshnessError(
            "Target weights exceed risk.max_pos: "
            + ", ".join(f"{s}={v:.4f} (cap {c:.4f})" for s, v, c in violations)
        )


def run_target_policy_check(
    *,
    targets_path: Path | None = None,
    policy_path: Path | None = None,
) -> None:
    """Validate persisted targets against static risk caps from policy."""
    pol = load_policy(policy_path)
    risk = pol.get("risk", {}) or {}
    max_pos = float(risk.get("max_pos", 1.0))
    tol = float(risk.get("max_pos_rounding_tolerance", 0.01))
    cash_floor = float(risk.get("cash_floor", 0.0))
    cash_tol = float(risk.get("cash_floor_rounding_tolerance", 0.02))
    path = targets_path or TARGETS_FILE
    doc = read_json(str(path))
    weights = doc.get("weights") or {}
    if not isinstance(weights, dict):
        raise FreshnessError("targets.json missing weights object")
    assert_targets_within_max_pos(weights, max_pos, tol)
    if cash_floor > 0:
        assert_targets_cash_floor(weights, cash_floor, cash_tol)
