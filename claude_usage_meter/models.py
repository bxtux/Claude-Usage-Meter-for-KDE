from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class UsageSnapshot:
    percent_used: int
    reset_text: str
    fetched_at: datetime
    source_ok: bool


class AlertState:
    """Tracks threshold crossings to avoid repeated alerts while above threshold."""

    def __init__(self) -> None:
        self._was_above_threshold = False

    def should_fire(self, value: int, threshold: int) -> bool:
        is_above = value >= threshold
        fire = is_above and not self._was_above_threshold
        self._was_above_threshold = is_above
        return fire
