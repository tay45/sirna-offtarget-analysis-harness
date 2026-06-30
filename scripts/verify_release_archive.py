from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from scripts.release_source_tree import compute_release_source_tree_checksum

ARCHIVE_CHECKSUM_MODEL = "external-sidecar"
ARCHIVE_SHA256_STATUS = "EXTERNAL_SIDECAR"
HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TEXT_SUFFIXES = {
    ".cfg",
    ".csv",
    ".dot",
    ".gtf",
    ".ini",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}
UNRESOLVED_CHECKSUM_TOKENS = (
    "PEND" + "ING_FINAL_ARCHIVE_SHA256",
    "TO_BE" + "_FILLED",
    "UNKNOWN" + "_CHECKSUM",
    "PLACE" + "HOLDER",
    "0" * 64,
)


def _fail(message: str) -> int:
    print(f"release archive verification failed: {message}", file=sys.stderr)
    return 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_sidecar(path: Path) -> tuple[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) != 1:
        raise ValueError("sidecar must contain exactly one entry")
    parts = lines[0].split("  ")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("sidecar must use '<sha256>  <filename>' format")
    checksum, filename = parts
    if not HEX_SHA256_RE.fullmatch(checksum):
        raise ValueError("sidecar checksum must be 64 lowercase hexadecimal characters")
    return checksum, filename


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_repo_root(extract_dir: Path) -> Path:
    candidates = [path for path in extract_dir.iterdir() if path.is_dir()]
    if len(candidates) == 1 and (candidates[0] / "pyproject.toml").is_file():
        return candidates[0]
    if (extract_dir / "pyproject.toml").is_file():
        return extract_dir
    raise ValueError("could not locate extracted repository root")


def _scan_for_unresolved_tokens(root: Path) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in UNRESOLVED_CHECKSUM_TOKENS:
            if token in text:
                findings.append(f"{rel}: contains unresolved checksum token")
                break
    return findings


def verify_release_archive(
    zip_path: Path, sidecar_path: Path, extract_dir: Path | None = None
) -> int:
    zip_path = zip_path.resolve()
    sidecar_path = sidecar_path.resolve()
    if not zip_path.is_file():
        return _fail(f"missing ZIP: {zip_path}")
    if not sidecar_path.is_file():
        return _fail(f"missing sidecar: {sidecar_path}")
    try:
        sidecar_checksum, sidecar_filename = _parse_sidecar(sidecar_path)
    except ValueError as exc:
        return _fail(str(exc))
    if sidecar_filename != zip_path.name:
        return _fail("sidecar filename does not match ZIP filename")
    actual_checksum = _sha256(zip_path)
    if actual_checksum != sidecar_checksum:
        return _fail("sidecar checksum does not match ZIP checksum")

    cleanup = False
    if extract_dir is None:
        extract_dir = Path(tempfile.mkdtemp(prefix="sirna_release_verify_"))
        cleanup = True
    else:
        extract_dir = extract_dir.resolve()
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True)
    try:
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)
        repo_root = _find_repo_root(extract_dir)
        manifest = _load_json(repo_root / "release_manifest.json")
        post_package = _load_json(repo_root / "post_package_verification.json")
        latest = (repo_root / "LATEST.md").read_text(encoding="utf-8")

        for payload_name, payload in (("manifest", manifest), ("post-package", post_package)):
            if payload.get("archive_checksum_model") != ARCHIVE_CHECKSUM_MODEL:
                return _fail(f"{payload_name} checksum model is not external-sidecar")
            if payload.get("archive_sidecar_filename") != sidecar_path.name:
                return _fail(f"{payload_name} sidecar filename does not match supplied sidecar")
            if payload.get("archive_sha256") is not None:
                return _fail(f"{payload_name} archive_sha256 must be null or absent")
            if payload.get("archive_sha256_status") != ARCHIVE_SHA256_STATUS:
                return _fail(f"{payload_name} archive_sha256_status is not EXTERNAL_SIDECAR")

        embedded_post = manifest.get("post_package_verification", {})
        if isinstance(embedded_post, dict):
            if embedded_post.get("archive_checksum_model") != ARCHIVE_CHECKSUM_MODEL:
                return _fail("manifest embedded post-package checksum model is incorrect")
            if embedded_post.get("archive_sha256") is not None:
                return _fail("manifest embedded post-package archive_sha256 must be null or absent")

        source = compute_release_source_tree_checksum(repo_root)
        if manifest.get("source_tree_checksum_sha256") != source.checksum:
            return _fail("manifest source checksum does not match extracted source")
        if manifest.get("source_tree_included_file_count") != source.included_file_count:
            return _fail("manifest source inventory count does not match extracted source")
        if post_package.get("source_tree_sha256") != source.checksum:
            return _fail("post-package source checksum does not match extracted source")
        if post_package.get("source_inventory_count") != source.included_file_count:
            return _fail("post-package source inventory count does not match extracted source")
        if "FINAL ARCHIVE CHECKSUM MODEL: EXTERNAL SIDECAR" not in latest:
            return _fail("LATEST.md does not document the external sidecar checksum model")

        findings = _scan_for_unresolved_tokens(repo_root)
        if findings:
            return _fail("; ".join(findings[:5]))
    finally:
        if cleanup:
            shutil.rmtree(extract_dir, ignore_errors=True)
    print("release archive verification passed")
    return 0


def _main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("sidecar_path", type=Path)
    parser.add_argument("--extract-dir", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    return verify_release_archive(args.zip_path, args.sidecar_path, args.extract_dir)


if __name__ == "__main__":
    raise SystemExit(_main())
