from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.hashing import load_json


def current_manifest_path(stage_dir: Path) -> Path | None:
    current = stage_dir / "current.json"
    if not current.exists():
        return None
    pointer = load_json(current)
    attempt = stage_dir / "attempts" / str(pointer["attempt_directory"])
    manifest = attempt / "stage_manifest.json"
    return manifest if manifest.exists() else None


def current_attempt_dir(stage_dir: Path) -> Path | None:
    current = stage_dir / "current.json"
    if not current.exists():
        return None
    pointer = load_json(current)
    attempt = stage_dir / "attempts" / str(pointer["attempt_directory"])
    return attempt if attempt.exists() else None


def next_attempt_number(stage_dir: Path) -> int:
    attempts = stage_dir / "attempts"
    attempts.mkdir(parents=True, exist_ok=True)
    numbers = []
    for path in attempts.glob("attempt_*"):
        try:
            numbers.append(int(path.name.split("_", 1)[1]))
        except (IndexError, ValueError):
            continue
    return max(numbers, default=0) + 1
