from __future__ import annotations

from typing import Protocol


class EnergyBackend(Protocol):
    def predict_duplex_energy(self, guide: str, target: str) -> float: ...
