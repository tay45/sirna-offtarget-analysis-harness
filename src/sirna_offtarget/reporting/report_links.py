from __future__ import annotations

from pathlib import Path


def relative_link(from_dir: Path, target: Path) -> str:
    return (
        str(target.resolve().relative_to(from_dir.resolve()))
        if target.is_relative_to(from_dir)
        else str(target)
    )
