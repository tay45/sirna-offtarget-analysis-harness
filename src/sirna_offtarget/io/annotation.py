from __future__ import annotations

from pathlib import Path


def read_annotation_lines(path: Path) -> list[str]:
    return [line for line in path.read_text().splitlines() if line and not line.startswith("#")]
