from __future__ import annotations

from pathlib import Path

from sirna_offtarget.validation.schema import required_output_files


def validate_output_directory(output_dir: Path) -> list[str]:
    if not output_dir.exists():
        return [f"missing output directory: {output_dir}"]
    errors: list[str] = []
    missing = sorted(required_output_files() - {path.name for path in output_dir.iterdir()})
    errors.extend(f"missing output file: {name}" for name in missing)
    return errors
