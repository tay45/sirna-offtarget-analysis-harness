import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_license_exists_and_matches_metadata() -> None:
    license_text = (ROOT / "LICENSE").read_text()
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert "MIT License" in license_text
    assert metadata["project"]["license"]["text"] == "MIT"
