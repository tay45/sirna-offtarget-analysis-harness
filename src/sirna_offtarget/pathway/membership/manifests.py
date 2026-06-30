from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from sirna_offtarget.pathway.membership.models import AnnotationMembershipSnapshotV2


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(snapshot_dir: Path, manifest: AnnotationMembershipSnapshotV2) -> Path:
    path = snapshot_dir / "annotation_membership_manifest.json"
    path.write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n")
    return path


def read_manifest(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text()))
