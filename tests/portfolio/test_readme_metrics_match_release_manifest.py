import json

from tests.portfolio.integrity_helpers import ROOT


def test_readme_metrics_match_release_manifest() -> None:
    readme = (ROOT / "README.md").read_text()
    manifest = json.loads((ROOT / "release_manifest.json").read_text())
    metrics = manifest["readme_quality_metrics"]
    assert f"{metrics['full_suite_passed']} passed" in readme
    assert f"{metrics['portfolio_tests_passed']} portfolio tests passed" in readme
    assert str(metrics["line_coverage"]) in readme
    assert str(metrics["branch_coverage"]) in readme
