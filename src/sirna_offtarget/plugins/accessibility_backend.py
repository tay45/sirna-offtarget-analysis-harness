from __future__ import annotations

from typing import Protocol


class AccessibilityBackend(Protocol):
    def predict_accessibility(self, transcript_id: str, start: int, end: int) -> float: ...
