from __future__ import annotations

from pathlib import Path
from typing import Any

from sirna_offtarget.execution.hashing import load_json


def list_attempts(run_dir: Path, stage_name: str) -> list[dict[str, Any]]:
    stage_dir = next(run_dir.glob(f"stages/*_{stage_name}"), None)
    if stage_dir is None:
        return []
    rows: list[dict[str, Any]] = []
    for manifest in sorted((stage_dir / "attempts").glob("attempt_*/stage_manifest.json")):
        rows.append(load_json(manifest))
    return rows
