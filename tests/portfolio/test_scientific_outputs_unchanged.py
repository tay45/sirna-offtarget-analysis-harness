import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_scientific_outputs_unchanged() -> None:
    expected = json.loads((ROOT / "portfolio_scientific_preservation.json").read_text())
    actual = {
        relative_path: hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
        for relative_path in expected
    }
    assert actual == expected
