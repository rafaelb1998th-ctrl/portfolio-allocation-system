"""Minimal target sanity check before trade generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from core.utils.io import read_json
from infra.state_paths import TARGETS_FILE


def validate_targets_sum(
    tolerance: float = 0.02,
    targets_path: Path | None = None,
) -> Tuple[bool, str]:
    path = targets_path or TARGETS_FILE
    doc: Dict[str, Any] = read_json(str(path))
    weights = doc.get("weights") or {}
    if not weights:
        return False, "targets: empty weights"

    total = sum(float(w) for w in weights.values() if isinstance(w, (int, float)))
    if abs(total - 1.0) <= tolerance:
        return True, f"ok (sum={total:.4f})"
    return False, f"weights sum to {total:.4f}, expected ~1.0 (±{tolerance})"
