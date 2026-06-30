import importlib


def test_clean_package_imports() -> None:
    for name in [
        "sirna_offtarget",
        "sirna_offtarget.sequence",
        "sirna_offtarget.expression",
        "sirna_offtarget.isoform",
        "sirna_offtarget.pathway",
    ]:
        assert importlib.import_module(name)
