from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ZIP_NAME = "sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip"
SIDECAR_NAME = f"{ZIP_NAME}.sha256"


def _manifest() -> dict[str, object]:
    return json.loads((ROOT / "release_manifest.json").read_text())


def _post_package() -> dict[str, object]:
    return json.loads((ROOT / "post_package_verification.json").read_text())


def test_final_archive_uses_external_sidecar_model() -> None:
    manifest = _manifest()
    post_package = _post_package()
    assert manifest["archive_checksum_model"] == "external-sidecar"
    assert manifest["archive_checksum_authority"] == "adjacent .zip.sha256 file"
    assert manifest["archive_sidecar_filename"] == SIDECAR_NAME
    assert manifest.get("archive_sha256") is None
    assert manifest["archive_sha256_status"] == "EXTERNAL_SIDECAR"
    assert post_package["archive_checksum_model"] == manifest["archive_checksum_model"]
    assert post_package["archive_sidecar_filename"] == manifest["archive_sidecar_filename"]
    assert post_package.get("archive_sha256") is None


def test_internal_manifest_does_not_require_self_checksum() -> None:
    manifest = _manifest()
    assert "final_archive_sha256" not in manifest
    assert manifest["latest_zip_filename"] == ZIP_NAME
    assert manifest["final_zip_filename"] == ZIP_NAME
    assert manifest["required_baseline_zip_for_next_pass"] == ZIP_NAME
