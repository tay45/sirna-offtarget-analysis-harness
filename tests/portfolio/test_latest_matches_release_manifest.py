import json

from tests.portfolio.integrity_helpers import ROOT


def test_latest_matches_release_manifest() -> None:
    manifest = json.loads((ROOT / "release_manifest.json").read_text())
    latest = (ROOT / "LATEST.md").read_text()
    assert manifest["official_terminal_stage"] in latest
    assert manifest["final_zip_filename"] in latest
    assert str(manifest["coverage"]["line_rate"]) in latest
    assert str(manifest["coverage"]["branch_rate"]) in latest
