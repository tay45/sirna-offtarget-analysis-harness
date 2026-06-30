from pathlib import Path


def test_import_does_not_create_files(tmp_path: Path, monkeypatch) -> None:
    before = set(tmp_path.iterdir())
    monkeypatch.chdir(tmp_path)
    __import__("sirna_offtarget")
    assert set(tmp_path.iterdir()) == before
