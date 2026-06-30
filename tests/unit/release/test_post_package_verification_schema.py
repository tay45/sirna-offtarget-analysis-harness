from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.release_evidence import (
    build_post_package_verification,
    write_post_package_verification,
)

REQUIRED_CHECKS = {
    "extraction": True,
    "installation": True,
    "test": True,
    "quick_start": True,
    "prohibited_field_scan": True,
    "personal_path_scan": True,
    "confidentiality_scan": True,
    "scientific_regression": True,
}


def _payload(required_checks: dict[str, bool] | None = None) -> dict[str, object]:
    return build_post_package_verification(
        archive_filename="release.zip",
        archive_sidecar_filename="release.zip.sha256",
        source_tree_sha256="b" * 64,
        source_inventory_count=10,
        required_checks=required_checks or REQUIRED_CHECKS,
        verified_at="2026-06-28T00:00:00Z",
        details={"note": "unit-test"},
    )


def test_post_package_verification_contains_passed_boolean() -> None:
    payload = _payload()
    assert payload["passed"] is True
    assert isinstance(payload["passed"], bool)
    assert payload["status"] == "PASSED"


def test_post_package_verification_status_matches_passed() -> None:
    success = _payload()
    failure = _payload({**REQUIRED_CHECKS, "quick_start": False})
    assert success["passed"] == (success["status"] == "PASSED")
    assert failure["passed"] == (failure["status"] == "PASSED")
    assert failure["passed"] is False
    assert failure["status"] == "FAILED"
    assert failure["quick_start_result"] == "FAILED"


def test_post_package_verification_required_fields() -> None:
    payload = _payload()
    for field in (
        "passed",
        "status",
        "verification_type",
        "archive_filename",
        "archive_checksum_model",
        "archive_checksum_authority",
        "archive_sidecar_filename",
        "archive_sha256",
        "archive_sha256_status",
        "source_tree_sha256",
        "source_inventory_count",
        "extraction_result",
        "installation_result",
        "test_result",
        "quick_start_result",
        "prohibited_field_scan_result",
        "personal_path_scan_result",
        "confidentiality_scan_result",
        "scientific_regression_result",
        "verified_at",
        "details",
    ):
        assert field in payload
    assert payload["verification_type"] == "post-package-verification"
    assert payload["archive_checksum_model"] == "external-sidecar"
    assert payload["archive_sidecar_filename"] == "release.zip.sha256"
    assert payload["archive_sha256"] is None
    assert payload["archive_sha256_status"] == "EXTERNAL_SIDECAR"


def test_post_package_verification_success_exit_code(tmp_path: Path) -> None:
    path = tmp_path / "post_package_verification.json"
    exit_code = write_post_package_verification(path, _payload())
    assert exit_code == 0
    assert json.loads(path.read_text())["passed"] is True


def test_post_package_verification_success_command_exit_code(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.release_evidence",
            str(tmp_path),
            "--release-date",
            "2026-06-28",
            "--write-post-package-verification",
            "--archive-filename",
            "release.zip",
            "--archive-sidecar-filename",
            "release.zip.sha256",
            "--source-tree-sha256",
            "b" * 64,
            "--source-inventory-count",
            "10",
        ],
        cwd=Path(__file__).resolve().parents[3],
        check=False,
    )
    assert result.returncode == 0
    assert json.loads((tmp_path / "post_package_verification.json").read_text())["passed"] is True


def test_post_package_verification_failure_exit_code(tmp_path: Path) -> None:
    path = tmp_path / "post_package_verification.json"
    exit_code = write_post_package_verification(
        path,
        _payload({**REQUIRED_CHECKS, "scientific_regression": False}),
    )
    assert exit_code == 1
    assert json.loads(path.read_text())["status"] == "FAILED"


def test_post_package_verification_failure_command_exit_code(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.release_evidence",
            str(tmp_path),
            "--release-date",
            "2026-06-28",
            "--write-post-package-verification",
            "--archive-filename",
            "release.zip",
            "--archive-sidecar-filename",
            "release.zip.sha256",
            "--source-tree-sha256",
            "b" * 64,
            "--source-inventory-count",
            "10",
            "--failed-check",
            "test",
        ],
        cwd=Path(__file__).resolve().parents[3],
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads((tmp_path / "post_package_verification.json").read_text())
    assert payload["passed"] is False
    assert payload["status"] == "FAILED"


def test_post_package_verification_rejects_contradictory_status(tmp_path: Path) -> None:
    payload = _payload()
    payload["passed"] = False
    with pytest.raises(ValueError, match="passed/status"):
        write_post_package_verification(tmp_path / "bad.json", payload)
