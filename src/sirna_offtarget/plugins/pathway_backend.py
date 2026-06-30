from __future__ import annotations

from typing import Protocol


class PathwayBackend(Protocol):
    def directed_neighbors(self, gene: str) -> list[tuple[str, str]]: ...
