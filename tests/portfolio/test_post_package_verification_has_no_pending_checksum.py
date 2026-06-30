from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKEN = "PEND" + "ING_FINAL_ARCHIVE_SHA256"


def test_post_package_verification_has_no_pending_checksum() -> None:
    path = ROOT / "post_package_verification.json"
    text = path.read_text()
    payload = json.loads(text)
    assert TOKEN not in text
    assert payload["archive_checksum_model"] == "external-sidecar"
    assert payload["archive_sha256"] is None
    assert payload["archive_sha256_status"] == "EXTERNAL_SIDECAR"
    assert payload["passed"] is True
    assert payload["status"] == "PASSED"
