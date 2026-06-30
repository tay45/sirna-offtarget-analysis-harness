def test_cli_imports_cleanly() -> None:
    import sirna_offtarget.cli as cli

    assert cli.main
