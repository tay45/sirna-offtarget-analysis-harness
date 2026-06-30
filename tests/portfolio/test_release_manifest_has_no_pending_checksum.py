from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKEN = "PEND" + "ING_FINAL_ARCHIVE_SHA256"


def test_release_manifest_has_no_pending_checksum() -> None:
    path = ROOT / "release_manifest.json"
    text = path.read_text()
    manifest = json.loads(text)
    assert TOKEN not in text
    assert "final_archive_sha256" not in manifest
    assert manifest["archive_checksum_model"] == "external-sidecar"
    assert manifest["archive_sidecar_filename"].endswith(".zip.sha256")
    assert manifest["archive_sha256"] is None
    assert manifest["post_package_verification"]["archive_sha256"] is None
