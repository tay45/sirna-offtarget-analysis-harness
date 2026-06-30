from __future__ import annotations

import csv
from pathlib import Path

from sirna_offtarget.pathway.membership.exceptions import AnnotationMembershipError
from sirna_offtarget.pathway.membership.loaders import build_annotation_membership_snapshot

REQUIRED_COLUMNS = {"go_id", "namespace", "gene", "evidence_code", "assigned_by"}


def build_go_membership_snapshot(
    *, cache_dir: Path, input_files: list[Path], organism: str, ontology_release: str
) -> Path:
    _require_columns(input_files, REQUIRED_COLUMNS, "GO")
    return build_annotation_membership_snapshot(
        cache_dir=cache_dir,
        provider="go",
        input_files=input_files,
        organism=organism,
        annotation_source="GO_ASSOCIATION",
        provider_release=ontology_release,
        provider_version=ontology_release,
    )


def _require_columns(input_files: list[Path], required: set[str], provider: str) -> None:
    for path in input_files:
        delimiter = "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","
        with path.open(newline="") as handle:
            fieldnames = set(csv.DictReader(handle, delimiter=delimiter).fieldnames or [])
        missing = sorted(required - fieldnames)
        if missing:
            raise AnnotationMembershipError(
                f"{provider} membership input {path} is missing required columns: {missing}"
            )


__all__ = ["REQUIRED_COLUMNS", "build_go_membership_snapshot"]
