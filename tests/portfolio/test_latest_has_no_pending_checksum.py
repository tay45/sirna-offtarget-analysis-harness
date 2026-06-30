from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOKEN = "PEND" + "ING_FINAL_ARCHIVE_SHA256"


def test_latest_has_no_pending_checksum() -> None:
    text = (ROOT / "LATEST.md").read_text()
    assert TOKEN not in text
    assert "FINAL ARCHIVE CHECKSUM MODEL: EXTERNAL SIDECAR" in text
    assert (
        "FINAL ARCHIVE SIDECAR: "
        "sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip.sha256"
    ) in text
    assert "ARCHIVE CHECKSUM: See adjacent SHA-256 sidecar file" in text
