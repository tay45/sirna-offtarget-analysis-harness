from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.atomic import read_current_pointer, write_current_pointer


def test_current_pointer_is_json_and_cross_platform(tmp_path: Path) -> None:
    attempt = tmp_path / "attempts" / "attempt_001"
    attempt.mkdir(parents=True)
    write_current_pointer(tmp_path, 1, attempt)
    assert read_current_pointer(tmp_path) == {
        "attempt_number": 1,
        "attempt_directory": "attempt_001",
    }
