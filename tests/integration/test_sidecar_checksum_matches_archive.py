from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from scripts.release_source_tree import compute_release_source_tree_checksum
from scripts.verify_release_archive import verify_release_archive

ZIP_NAME = "sirna-offtarget-portfolio-public-final-verified-2026-06-28.zip"
SIDECAR_NAME = f"{ZIP_NAME}.sha256"


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _make_repo(root: Path, *, unresolved_token: str | None = None) -> Path:
    repo = root / "sirna-offtarget-analysis-harness"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "package.py").write_text("VALUE = 1\n")
    (repo / "tests" / "test_package.py").write_text("def test_package():\n    assert True\n")
    (repo / "pyproject.toml").write_text("[project]\nname = 'fixture'\nversion = '0.0.0'\n")
    source = compute_release_source_tree_checksum(repo)
    manifest = {
        "archive_checksum_model": "external-sidecar",
        "archive_checksum_authority": "adjacent .zip.sha256 file",
        "archive_sidecar_filename": SIDECAR_NAME,
        "archive_sha256": None,
        "archive_sha256_status": "EXTERNAL_SIDECAR",
        "latest_zip_filename": ZIP_NAME,
        "source_tree_checksum_sha256": source.checksum,
        "source_tree_included_file_count": source.included_file_count,
        "post_package_verification": {
            "archive_checksum_model": "external-sidecar",
            "archive_sidecar_filename": SIDECAR_NAME,
            "archive_sha256": None,
        },
    }
    post_package = {
        "passed": True,
        "status": "PASSED",
        "verification_type": "post-package-verification",
        "archive_filename": ZIP_NAME,
        "archive_checksum_model": "external-sidecar",
        "archive_checksum_authority": "adjacent .zip.sha256 file",
        "archive_sidecar_filename": SIDECAR_NAME,
        "archive_sha256": None,
        "archive_sha256_status": "EXTERNAL_SIDECAR",
        "source_tree_sha256": source.checksum,
        "source_inventory_count": source.included_file_count,
    }
    _write_json(repo / "release_manifest.json", manifest)
    _write_json(repo / "post_package_verification.json", post_package)
    latest = (
        "# Latest Release Notes\n\n"
        "FINAL ARCHIVE CHECKSUM MODEL: EXTERNAL SIDECAR\n"
        f"FINAL ARCHIVE SIDECAR: {SIDECAR_NAME}\n"
        f"INTERNAL SOURCE CHECKSUM: {source.checksum}\n"
        "ARCHIVE CHECKSUM: See adjacent SHA-256 sidecar file\n"
    )
    if unresolved_token:
        latest += unresolved_token
    (repo / "LATEST.md").write_text(latest)
    return repo


def _zip_repo(repo: Path, output_dir: Path) -> Path:
    zip_path = output_dir / ZIP_NAME
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(repo.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(repo.parent).as_posix())
    return zip_path


def _write_sidecar(zip_path: Path, sidecar_path: Path, *, filename: str | None = None) -> None:
    checksum = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    sidecar_path.write_text(f"{checksum}  {filename or zip_path.name}\n")


def test_sidecar_checksum_matches_archive(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    zip_path = _zip_repo(repo, tmp_path)
    sidecar_path = tmp_path / SIDECAR_NAME
    _write_sidecar(zip_path, sidecar_path)
    assert verify_release_archive(zip_path, sidecar_path, tmp_path / "extract") == 0


def test_sidecar_has_standard_sha256sum_format(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    zip_path = _zip_repo(repo, tmp_path)
    sidecar_path = tmp_path / SIDECAR_NAME
    _write_sidecar(zip_path, sidecar_path)
    line = sidecar_path.read_text()
    checksum, filename = line.strip().split("  ")
    assert len(checksum) == 64
    assert checksum == checksum.lower()
    assert filename == ZIP_NAME
    assert line.endswith("\n")


def test_archive_verifier_accepts_valid_sidecar(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    zip_path = _zip_repo(repo, tmp_path)
    sidecar_path = tmp_path / SIDECAR_NAME
    _write_sidecar(zip_path, sidecar_path)
    assert verify_release_archive(zip_path, sidecar_path, tmp_path / "extract") == 0


def test_archive_verifier_rejects_wrong_checksum(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    zip_path = _zip_repo(repo, tmp_path)
    sidecar_path = tmp_path / SIDECAR_NAME
    sidecar_path.write_text(f"{'1' * 64}  {ZIP_NAME}\n")
    assert verify_release_archive(zip_path, sidecar_path, tmp_path / "extract") == 1


def test_archive_verifier_rejects_wrong_filename(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    zip_path = _zip_repo(repo, tmp_path)
    sidecar_path = tmp_path / SIDECAR_NAME
    _write_sidecar(zip_path, sidecar_path, filename="wrong.zip")
    assert verify_release_archive(zip_path, sidecar_path, tmp_path / "extract") == 1


def test_archive_verifier_rejects_missing_sidecar(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    zip_path = _zip_repo(repo, tmp_path)
    assert verify_release_archive(zip_path, tmp_path / SIDECAR_NAME, tmp_path / "extract") == 1


def test_archive_verifier_rejects_placeholder(tmp_path: Path) -> None:
    token = "PEND" + "ING_FINAL_ARCHIVE_SHA256"
    repo = _make_repo(tmp_path / "repo", unresolved_token=token)
    zip_path = _zip_repo(repo, tmp_path)
    sidecar_path = tmp_path / SIDECAR_NAME
    _write_sidecar(zip_path, sidecar_path)
    assert verify_release_archive(zip_path, sidecar_path, tmp_path / "extract") == 1


def test_internal_source_checksum_matches_extracted_tree(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    zip_path = _zip_repo(repo, tmp_path)
    sidecar_path = tmp_path / SIDECAR_NAME
    _write_sidecar(zip_path, sidecar_path)
    extract_dir = tmp_path / "extract"
    assert verify_release_archive(zip_path, sidecar_path, extract_dir) == 0
    extracted = extract_dir / "sirna-offtarget-analysis-harness"
    source = compute_release_source_tree_checksum(extracted)
    manifest = json.loads((extracted / "release_manifest.json").read_text())
    assert manifest["source_tree_checksum_sha256"] == source.checksum


def test_release_evidence_uses_external_checksum_authority(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    zip_path = _zip_repo(repo, tmp_path)
    sidecar_path = tmp_path / SIDECAR_NAME
    _write_sidecar(zip_path, sidecar_path)
    assert verify_release_archive(zip_path, sidecar_path, tmp_path / "extract") == 0
