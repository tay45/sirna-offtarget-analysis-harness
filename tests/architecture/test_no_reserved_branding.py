from pathlib import Path


def test_removed_branding_is_not_reintroduced() -> None:
    root = Path(__file__).resolve().parents[2]
    removed = "".join(("n", "2", "n"))
    reserved = [removed, "_".join((removed, "sirna"))]
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        parts = path.relative_to(root).parts
        if any(part.startswith(".") for part in parts):
            continue
        if "__pycache__" in parts:
            continue
        if "dist" in parts:
            continue
        if path.suffix.lower() in {".png", ".zip"}:
            continue
        if path.name == "test_no_reserved_branding.py":
            continue
        text = path.read_text(errors="ignore").lower()
        assert not any(token in text for token in reserved), path
