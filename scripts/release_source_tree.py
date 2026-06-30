from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

POLICY_VERSION = "release-source-tree-checksum-v2"
ROOT_MARKERS = ("pyproject.toml", "src", "tests")
EXCLUDED_DIR_NAMES = {
    ".git",
    ".import_linter_cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "work",
}
EXCLUDED_FILE_NAMES = {
    ".coverage",
    "archive_checksum_placeholder_scan_report.json",
    "LATEST.md",
    "post_package_verification.json",
    "release_coverage_evidence.json",
    "release_manifest.json",
    "release_source_tree_inventory.json",
}
EXCLUDED_SUFFIXES = (".zip", ".pyc", ".pyo")
EXCLUDED_PREFIX_PARTS = (
    ("examples", "portfolio", "output"),
    ("examples", "synthetic", "output"),
)


@dataclass(frozen=True)
class SourceTreeChecksum:
    checksum: str
    included_file_count: int
    included_paths: tuple[str, ...]
    algorithm: str = (
        "sha256(relative-posix-path NUL file-bytes) over lexicographically sorted files"
    )
    policy_version: str = POLICY_VERSION


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _is_excluded(rel: Path) -> bool:
    if any(part in EXCLUDED_DIR_NAMES for part in rel.parts):
        return True
    if rel.name in EXCLUDED_FILE_NAMES:
        return True
    if rel.name == "coverage.xml":
        return True
    if rel.name.endswith(EXCLUDED_SUFFIXES):
        return True
    return any(rel.parts[: len(prefix)] == prefix for prefix in EXCLUDED_PREFIX_PARTS)


def included_source_paths(root_path: Path) -> tuple[Path, ...]:
    root = root_path.resolve()
    if not all((root / marker).exists() for marker in ROOT_MARKERS):
        raise ValueError(f"{root} is not a release repository root")
    paths: list[Path] = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if _is_excluded(rel):
            continue
        if path.is_symlink():
            target = path.resolve()
            if not _is_relative_to(target, root):
                raise ValueError(f"symbolic link leaves repository: {rel.as_posix()}")
            continue
        if path.is_file():
            paths.append(path)
    return tuple(sorted(paths, key=lambda p: p.relative_to(root).as_posix()))


def compute_release_source_tree_checksum(root_path: str | Path) -> SourceTreeChecksum:
    root = Path(root_path).resolve()
    digest = hashlib.sha256()
    included: list[str] = []
    for path in included_source_paths(root):
        rel = path.relative_to(root).as_posix()
        included.append(rel)
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return SourceTreeChecksum(
        checksum=digest.hexdigest(),
        included_file_count=len(included),
        included_paths=tuple(included),
    )


def excluded_pattern_summary() -> dict[str, object]:
    return {
        "directory_names": sorted(EXCLUDED_DIR_NAMES),
        "file_names": sorted(EXCLUDED_FILE_NAMES | {"coverage.xml"}),
        "suffixes": list(EXCLUDED_SUFFIXES),
        "prefix_paths": ["/".join(prefix) for prefix in EXCLUDED_PREFIX_PARTS],
    }


def build_source_tree_inventory(root_path: str | Path) -> dict[str, object]:
    result = compute_release_source_tree_checksum(root_path)
    return {
        "algorithm": result.algorithm,
        "checksum_policy_version": result.policy_version,
        "repository_root_marker": list(ROOT_MARKERS),
        "included_file_count": result.included_file_count,
        "included_relative_paths": list(result.included_paths),
        "excluded_pattern_summary": excluded_pattern_summary(),
        "source_tree_checksum": result.checksum,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--inventory", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = compute_release_source_tree_checksum(args.root)
    if args.inventory:
        write_json(args.inventory, build_source_tree_inventory(args.root))
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
