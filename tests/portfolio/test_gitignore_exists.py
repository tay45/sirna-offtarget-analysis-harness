from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_gitignore_exists() -> None:
    text = (ROOT / ".gitignore").read_text()
    for entry in (
        ".venv/",
        "__pycache__/",
        ".pytest_cache/",
        ".import_linter_cache/",
        "coverage.xml",
        "build/",
        "dist/",
        "*.zip",
    ):
        assert entry in text
