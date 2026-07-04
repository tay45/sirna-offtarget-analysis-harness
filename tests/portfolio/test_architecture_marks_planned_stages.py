from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_architecture_marks_planned_stages() -> None:
    dot = (ROOT / "docs/architecture_current_and_planned.dot").read_text()
    assert "Current validated release" in dot
    assert "Future validation and tuning" in dot
    assert 'style="rounded,dashed"' in dot
    assert "Intended-target" in dot
    assert "Final evidence" in dot
    assert "External biological" in dot
    assert (ROOT / "docs/architecture_current_and_planned.png").is_file()
    assert (ROOT / "docs/architecture_current_and_planned.svg").is_file()
