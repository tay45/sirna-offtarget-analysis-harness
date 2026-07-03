from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_readme_distinguishes_implemented_and_planned() -> None:
    readme = (ROOT / "README.md").read_text()
    assert "## Implemented and Validated" in readme
    assert "## Planned, Not Yet Implemented" in readme
    assert "| Expression normalization | Implemented |" in readme
    assert "| Intended-target calibration | Implemented |" in readme
    assert "| Expected direct effect | Implemented |" in readme
    assert "| Final classification | Planned |" in readme
