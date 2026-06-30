from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = (
    "/" + "Users" + "/",
    "/" + "home" + "/",
    "C:" + "\\" + "Users" + "\\",
    "th" + "kang",
    "Desk" + "top",
    "Docu" + "ments",
)
SKIP_PARTS = {
    ".venv",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".import_linter_cache",
    "__pycache__",
    "output",
    "work",
    "build",
    "dist",
}
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
    ".tsv",
    ".csv",
    ".dot",
    ".svg",
}


def test_no_personal_absolute_paths() -> None:
    offenders: list[str] = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if any(part in SKIP_PARTS for part in rel.parts) or path.suffix not in TEXT_SUFFIXES:
            continue
        text = path.read_text(errors="ignore")
        if any(token in text for token in FORBIDDEN):
            offenders.append(rel.as_posix())
    assert offenders == []
