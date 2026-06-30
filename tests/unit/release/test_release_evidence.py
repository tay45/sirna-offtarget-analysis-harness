from __future__ import annotations

import json
from pathlib import Path

from scripts.release_source_tree import (
    POLICY_VERSION,
    build_source_tree_inventory,
    compute_release_source_tree_checksum,
    excluded_pattern_summary,
    sha256_file,
)

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_ZIP = "sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip"


def _manifest() -> dict[str, object]:
    return json.loads((ROOT / "release_manifest.json").read_text())


def _latest() -> str:
    return (ROOT / "LATEST.md").read_text()


def _inventory() -> dict[str, object]:
    return json.loads((ROOT / "release_source_tree_inventory.json").read_text())


def _coverage_evidence() -> dict[str, object]:
    return json.loads((ROOT / "release_coverage_evidence.json").read_text())


def _post_package() -> dict[str, object] | None:
    path = ROOT / "post_package_verification.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    if payload.get("archive_filename") != _manifest()["latest_zip_filename"]:
        return None
    return payload


def test_shared_source_checksum_function() -> None:
    result = compute_release_source_tree_checksum(ROOT)
    assert result.policy_version == POLICY_VERSION
    assert result.included_file_count > 0
    assert "src/sirna_offtarget/isoform_uncertainty/core.py" in result.included_paths
    assert "src/sirna_offtarget/transcript_targetability/core.py" in result.included_paths


def test_source_checksum_scope_is_deterministic() -> None:
    first = compute_release_source_tree_checksum(ROOT)
    second = compute_release_source_tree_checksum(ROOT)
    assert first == second
    summary = excluded_pattern_summary()
    assert "coverage.xml" in summary["file_names"]
    assert "release_manifest.json" in summary["file_names"]


def test_release_manifest_checksum_matches_repository() -> None:
    manifest = _manifest()
    result = compute_release_source_tree_checksum(ROOT)
    assert manifest["source_tree_checksum_sha256"] == result.checksum
    assert manifest["source_tree_included_file_count"] == result.included_file_count


def test_source_inventory_matches_repository() -> None:
    expected = build_source_tree_inventory(ROOT)
    inventory = _inventory()
    assert inventory["checksum_policy_version"] == expected["checksum_policy_version"]
    assert inventory["source_tree_checksum"] == expected["source_tree_checksum"]
    assert inventory["included_file_count"] == expected["included_file_count"]
    assert inventory["included_relative_paths"] == expected["included_relative_paths"]
    assert _manifest()["source_inventory_artifact_sha256"] == sha256_file(
        ROOT / "release_source_tree_inventory.json"
    )


def test_latest_md_and_manifest_agree() -> None:
    manifest = _manifest()
    latest = _latest()
    assert manifest["latest_zip_filename"] in latest
    assert f"Overall status: {manifest['release_status']}" in latest
    assert f"Line coverage: {manifest['coverage_evidence']['line_rate']}" in latest
    assert f"Branch coverage: {manifest['coverage_evidence']['branch_rate']}" in latest


def test_coverage_source_checksum_matches_repository() -> None:
    manifest = _manifest()
    evidence = _coverage_evidence()
    result = compute_release_source_tree_checksum(ROOT)
    assert evidence["source_tree_checksum_sha256"] == result.checksum
    assert manifest["coverage_evidence"]["source_tree_checksum_sha256"] == result.checksum
    assert manifest["coverage_evidence_artifact_sha256"] == sha256_file(
        ROOT / "release_coverage_evidence.json"
    )


def test_manifest_test_counts_match_evidence() -> None:
    manifest = _manifest()
    full_suite = manifest["test_results"]["full_suite"]
    assert full_suite["status"] == "PASSED"
    assert full_suite["passed"] == full_suite["collected"]
    assert full_suite["failed"] == 0


def test_manifest_zip_filename_matches_expected_status() -> None:
    manifest = _manifest()
    assert manifest["release_status"] == "COMPLETE"
    assert manifest["latest_zip_filename"] == EXPECTED_ZIP
    assert manifest["required_baseline_zip_for_next_pass"] == EXPECTED_ZIP


def test_clean_package_excludes_coverage_xml() -> None:
    manifest = _manifest()
    post_package = _post_package()
    assert manifest["clean_package_policy"]["coverage_xml_included"] is False
    if post_package is not None:
        assert not (ROOT / "coverage.xml").exists()
        assert post_package["excluded_path_check"]["coverage_xml_absent"] is True


def test_clean_package_excludes_cache_and_work_paths() -> None:
    post_package = _post_package()
    if post_package is None:
        assert _manifest()["clean_package_policy"]["cache_paths_included"] is False
        assert _manifest()["clean_package_policy"]["import_linter_cache_included"] is False
        return
    assert post_package["excluded_path_check"]["cache_paths_absent"] is True
    assert post_package["excluded_path_check"]["import_linter_cache_absent"] is True
    assert post_package["excluded_path_check"]["work_paths_absent"] is True


def test_manifest_does_not_require_excluded_coverage_xml() -> None:
    manifest = _manifest()
    assert manifest["clean_package_policy"]["coverage_xml_included"] is False
    assert manifest["coverage_evidence_artifact"] == "release_coverage_evidence.json"
    assert "coverage.xml" not in manifest["source_inventory_artifact"]


def test_release_files_excluded_from_source_checksum(tmp_path: Path) -> None:
    for dirname in ("src", "tests"):
        (tmp_path / dirname).mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    (tmp_path / "src" / "module.py").write_text("VALUE = 1\n")
    before = compute_release_source_tree_checksum(tmp_path)
    (tmp_path / "release_manifest.json").write_text("{}\n")
    (tmp_path / "LATEST.md").write_text("later\n")
    (tmp_path / "coverage.xml").write_text("<coverage />\n")
    assert compute_release_source_tree_checksum(tmp_path) == before


def test_extracted_zip_source_checksum_matches_manifest() -> None:
    post_package = _post_package()
    if post_package is None:
        return
    assert post_package["passed"] is True
    assert post_package["status"] == "PASSED"
    assert post_package["passed"] == (post_package["status"] == "PASSED")
    assert post_package["source_checksum_match"] is True
    assert post_package["source_tree_sha256"] == _manifest()["source_tree_checksum_sha256"]
    assert post_package["recomputed_source_checksum"] == _manifest()["source_tree_checksum_sha256"]


def test_extracted_zip_inventory_matches() -> None:
    post_package = _post_package()
    if post_package is None:
        return
    assert post_package["inventory_verification"]["passed"] is True
    assert post_package["included_file_count_match"] is True
    assert post_package["source_inventory_count"] == _manifest()["source_tree_included_file_count"]


def test_extracted_zip_contains_required_files() -> None:
    assert (ROOT / "src").is_dir()
    assert (ROOT / "tests").is_dir()
    assert (ROOT / "docs").is_dir()
    assert (ROOT / "scripts").is_dir()
    assert (ROOT / "release_manifest.json").is_file()
    assert (ROOT / "release_source_tree_inventory.json").is_file()


def test_extracted_zip_excludes_generated_junk() -> None:
    post_package = _post_package()
    if post_package is None:
        return
    assert post_package["excluded_path_check"]["passed"] is True


def test_extracted_zip_latest_and_manifest_agree() -> None:
    post_package = _post_package()
    if post_package is None:
        return
    assert post_package["latest_manifest_agreement"] is True
    assert f"Post-package verification passed: {str(post_package['passed']).lower()}" in _latest()
    assert f"Post-package verification status: {post_package['status']}" in _latest()


def test_release_manifest_matches_post_package_verification() -> None:
    post_package = _post_package()
    if post_package is None:
        return
    manifest = _manifest()
    assert manifest["post_package_verification"]["passed"] is post_package["passed"]
    assert manifest["post_package_verification"]["status"] == post_package["status"]
    assert manifest["archive_checksum_model"] == "external-sidecar"
    assert manifest["archive_sidecar_filename"] == post_package["archive_sidecar_filename"]
    assert manifest.get("archive_sha256") is None
    assert manifest["post_package_verification"].get("archive_sha256") is None
    assert post_package.get("archive_sha256") is None
    assert post_package["archive_sha256_status"] == "EXTERNAL_SIDECAR"
    assert manifest["post_package_verification"]["evidence_filename"] == (
        "post_package_verification.json"
    )


def test_extracted_zip_release_status_is_honest() -> None:
    manifest = _manifest()
    if manifest["release_status"] == "COMPLETE":
        expected_status = "PASSED" if _post_package() is not None else "INCOMPLETE"
        assert manifest["post_package_verification"]["status"] == expected_status


def test_extracted_zip_is_only_required_next_baseline() -> None:
    manifest = _manifest()
    assert manifest["required_baseline_zip_for_next_pass"] == manifest["latest_zip_filename"]


def test_license_file_matches_mit_metadata() -> None:
    license_text = (ROOT / "LICENSE").read_text()
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert "MIT License" in license_text
    assert 'license = {text = "MIT"}' in pyproject
