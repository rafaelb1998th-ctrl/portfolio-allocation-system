"""Load scheduled risk context from manual_events.json (no external APIs)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class EventContext:
    risk_level: str
    events_today: List[str]
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "events_today": list(self.events_today),
            "notes": self.notes,
        }


def _events_dir() -> Path:
    return Path(__file__).resolve().parent


def load_manual_events(path: Path | None = None) -> Dict[str, Any]:
    p = path or (_events_dir() / "manual_events.json")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_event_context(path: Path | None = None) -> EventContext:
    doc = load_manual_events(path)
    return EventContext(
        risk_level=str(doc.get("risk_level", "normal")),
        events_today=list(doc.get("events_today") or []),
        notes=str(doc.get("notes", "")),
    )
