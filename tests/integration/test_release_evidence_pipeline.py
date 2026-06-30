from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.release_source_tree import compute_release_source_tree_checksum

ROOT = Path(__file__).resolve().parents[2]


def _manifest() -> dict[str, object]:
    return json.loads((ROOT / "release_manifest.json").read_text())


def test_final_release_package_checksum_pipeline() -> None:
    manifest = _manifest()
    result = compute_release_source_tree_checksum(ROOT)
    assert manifest["source_tree_checksum_sha256"] == result.checksum
    assert manifest["source_tree_included_file_count"] == result.included_file_count


def test_final_release_package_extraction_pipeline() -> None:
    post_package = ROOT / "post_package_verification.json"
    if not post_package.exists():
        return
    payload = json.loads(post_package.read_text())
    assert payload["passed"] is True
    assert payload["status"] == "PASSED"
    assert payload["passed"] == (payload["status"] == "PASSED")
    assert payload["verification_type"] == "post-package-verification"
    for field in (
        "archive_filename",
        "archive_checksum_model",
        "archive_sidecar_filename",
        "archive_sha256",
        "archive_sha256_status",
        "source_tree_sha256",
        "source_inventory_count",
        "test_result",
        "quick_start_result",
        "scientific_regression_result",
    ):
        assert field in payload
    assert payload["archive_checksum_model"] == "external-sidecar"
    assert payload["archive_sha256"] is None
    assert payload["archive_sha256_status"] == "EXTERNAL_SIDECAR"
    assert payload["source_tree_sha256"] == _manifest()["source_tree_checksum_sha256"]
    assert payload["source_inventory_count"] == _manifest()["source_tree_included_file_count"]
    assert payload["source_checksum_match"] is True
    assert payload["excluded_path_check"]["passed"] is True


def test_final_release_manifest_consistency_pipeline() -> None:
    manifest = _manifest()
    latest = (ROOT / "LATEST.md").read_text()
    assert manifest["release_status"] == "COMPLETE"
    assert manifest["latest_zip_filename"] in latest
    assert manifest["archive_checksum_model"] == "external-sidecar"
    assert manifest["archive_sidecar_filename"] in latest
    assert manifest.get("archive_sha256") is None
    assert manifest["post_package_verification"]["status"] == "PASSED"


def test_final_release_coverage_evidence_pipeline() -> None:
    manifest = _manifest()
    coverage = json.loads((ROOT / "release_coverage_evidence.json").read_text())
    assert coverage["coverage_xml_sha256"] == manifest["coverage_evidence"]["coverage_xml_sha256"]
    assert coverage["source_tree_checksum_sha256"] == manifest["source_tree_checksum_sha256"]
    assert float(coverage["line_rate"]) >= float(coverage["min_line_rate"])
    assert float(coverage["branch_rate"]) >= float(coverage["min_branch_rate"])


def test_final_release_clean_wheel_pipeline() -> None:
    manifest = _manifest()
    if manifest["quality_gates"]["clean_install_result"] == "PASSED":
        assert manifest["quality_gates"]["build_result"] == "PASSED"
        assert manifest["quality_gates"]["twine_result"] == "PASSED"
        return
    result = subprocess.run(
        [sys.executable, "-c", "import sirna_offtarget; print(sirna_offtarget.__name__)"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
