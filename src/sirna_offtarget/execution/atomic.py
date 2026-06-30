from __future__ import annotations

import json
import os
from pathlib import Path


def write_current_pointer(stage_dir: Path, attempt_number: int, attempt_dir: Path) -> None:
    tmp = stage_dir / "current.json.tmp"
    current = stage_dir / "current.json"
    tmp.write_text(
        json.dumps(
            {"attempt_number": attempt_number, "attempt_directory": str(attempt_dir.name)},
            indent=2,
        )
        + "\n"
    )
    os.replace(tmp, current)


def read_current_pointer(stage_dir: Path) -> dict[str, object] | None:
    current = stage_dir / "current.json"
    if not current.exists():
        return None
    data = json.loads(current.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{current} must contain a JSON object")
    return data
