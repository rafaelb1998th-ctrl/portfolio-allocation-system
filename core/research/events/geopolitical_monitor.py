"""Placeholder geopolitical risk label — extend with trusted feeds later."""

from __future__ import annotations

from typing import Literal

GeoRisk = Literal["low", "moderate", "elevated", "high"]


def geopolitical_risk_level() -> GeoRisk:
    """Static default until wired to a curated source."""
    return "moderate"
