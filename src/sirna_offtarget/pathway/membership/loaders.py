from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path

from sirna_offtarget.pathway.enrichment.models import PathwayMembershipRecordV1
from sirna_offtarget.pathway.membership.exceptions import AnnotationMembershipError
from sirna_offtarget.pathway.membership.manifests import sha256_file, write_manifest
from sirna_offtarget.pathway.membership.models import (
    MEMBERSHIP_PARSER_VERSION,
    MEMBERSHIP_SCHEMA_VERSION,
    AnnotationMembershipSnapshotV2,
    PathwayMembershipRecordV2,
)

ALLOWED_COMPLETENESS = {"complete", "partial", "submitted_hit_only", "unknown"}


def build_annotation_membership_snapshot(
    *,
    cache_dir: Path,
    provider: str,
    input_files: list[Path],
    organism: str,
    annotation_source: str | None = None,
    snapshot_id: str | None = None,
    provider_release: str = "user_supplied",
    provider_version: str = "user_supplied",
) -> Path:
    if not input_files:
        msg = "at least one annotation membership input file is required"
        raise AnnotationMembershipError(msg)
    snapshot_name = snapshot_id or f"{provider}_{organism}_{MEMBERSHIP_SCHEMA_VERSION}_custom"
    snapshot_dir = cache_dir / provider / snapshot_name
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    records = _read_records(
        input_files,
        provider=provider,
        organism=organism,
        snapshot_id=snapshot_name,
        annotation_source=annotation_source,
        provider_release=provider_release,
    )
    records = _deduplicate(records)
    memberships_path = snapshot_dir / "annotation_memberships.tsv"
    _write_records(memberships_path, records)
    incomplete_terms = {
        record.term_id for record in records if record.completeness_status != "complete"
    }
    mapped_genes = {gene for record in records for gene in record.canonical_gene_ids}
    unmapped = [record for record in records if not record.canonical_gene_ids]
    manifest = AnnotationMembershipSnapshotV2(
        snapshot_id=snapshot_name,
        provider=provider,
        annotation_source=annotation_source or provider,
        organism=organism,
        provider_release=provider_release,
        provider_version=provider_version,
        source_files=tuple(str(path) for path in input_files),
        source_checksums={str(path): sha256_file(path) for path in input_files},
        normalized_checksums={"annotation_memberships.tsv": sha256_file(memberships_path)},
        parser_version=MEMBERSHIP_PARSER_VERSION,
        schema_version=MEMBERSHIP_SCHEMA_VERSION,
        term_count=len({record.term_id for record in records}),
        membership_record_count=len(records),
        mapped_gene_count=len(mapped_genes),
        unmapped_entity_count=len(unmapped),
        incomplete_term_count=len(incomplete_terms),
        completeness_status="complete" if not incomplete_terms else "partial",
        warnings=(
            "user-supplied offline annotation resources; biological authority depends on inputs",
        ),
    )
    write_manifest(snapshot_dir, manifest)
    _write_coverage(snapshot_dir / "annotation_membership_coverage.tsv", records)
    _write_incomplete(snapshot_dir / "incomplete_annotation_terms.tsv", records)
    (snapshot_dir / ".verified").write_text("verified\n")
    return snapshot_dir


def load_verified_memberships(
    cache_dir: Path, provider: str | None = None
) -> list[PathwayMembershipRecordV2]:
    records: list[PathwayMembershipRecordV2] = []
    pattern = (
        "*/*/annotation_membership_manifest.json"
        if provider is None
        else f"{provider}/*/annotation_membership_manifest.json"
    )
    for manifest_path in sorted(cache_dir.glob(pattern)):
        errors = verify_snapshot_dir(manifest_path.parent)
        if errors:
            raise AnnotationMembershipError("; ".join(errors))
        records.extend(read_membership_records(manifest_path.parent / "annotation_memberships.tsv"))
    return records


def read_membership_records(path: Path) -> list[PathwayMembershipRecordV2]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return [_record_from_row(row) for row in reader]


def to_enrichment_memberships(
    records: list[PathwayMembershipRecordV2],
) -> list[PathwayMembershipRecordV1]:
    memberships: list[PathwayMembershipRecordV1] = []
    for record in records:
        for gene_id in record.canonical_gene_ids:
            memberships.append(
                PathwayMembershipRecordV1(
                    provider=record.provider,
                    annotation_source=record.annotation_source,
                    term_id=record.term_id,
                    term_name=record.term_name,
                    member_entity_id=record.member_entity_id,
                    member_gene_id=gene_id,
                    organism=record.organism,
                    hierarchy_parent_ids=record.hierarchy_parent_ids,
                    evidence_type="complete_annotation_membership",
                    provider_version=record.provider_release,
                    snapshot_id=record.snapshot_id,
                    membership_type=record.membership_type,
                    membership_completeness=record.completeness_status,
                    warnings=record.warnings,
                )
            )
    return memberships


def inspect_membership_cache(cache_dir: Path) -> list[dict[str, object]]:
    manifests = []
    for path in sorted(cache_dir.glob("*/*/annotation_membership_manifest.json")):
        manifests.append(json.loads(path.read_text()))
    return manifests


def verify_membership_cache(cache_dir: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(cache_dir.glob("*/*/annotation_membership_manifest.json")):
        errors.extend(verify_snapshot_dir(path.parent))
    return errors


def verify_snapshot_dir(snapshot_dir: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = snapshot_dir / "annotation_membership_manifest.json"
    if not manifest_path.exists():
        return [f"missing annotation membership manifest {snapshot_dir}"]
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != MEMBERSHIP_SCHEMA_VERSION:
        errors.append(f"unsupported annotation membership schema {manifest_path}")
    records_path = snapshot_dir / "annotation_memberships.tsv"
    if not records_path.exists():
        errors.append(f"missing annotation memberships {records_path}")
    else:
        expected = manifest.get("normalized_checksums", {}).get("annotation_memberships.tsv")
        actual = sha256_file(records_path)
        if expected != actual:
            errors.append(f"annotation membership checksum mismatch {records_path}")
    if not (snapshot_dir / ".verified").exists():
        errors.append(f"annotation membership snapshot not verified {snapshot_dir}")
    if manifest.get("completeness_status") not in ALLOWED_COMPLETENESS:
        errors.append(f"invalid completeness status {manifest_path}")
    return errors


def _read_records(
    input_files: list[Path],
    *,
    provider: str,
    organism: str,
    snapshot_id: str,
    annotation_source: str | None,
    provider_release: str,
) -> list[PathwayMembershipRecordV2]:
    records: list[PathwayMembershipRecordV2] = []
    for input_file in input_files:
        with input_file.open(newline="") as handle:
            delimiter = "\t" if input_file.suffix.lower() in {".tsv", ".txt"} else ","
            for index, row in enumerate(csv.DictReader(handle, delimiter=delimiter), start=1):
                records.append(
                    _record_from_resource_row(
                        row,
                        provider=provider,
                        organism=organism,
                        snapshot_id=snapshot_id,
                        annotation_source=annotation_source,
                        provider_release=provider_release,
                        source_file=str(input_file),
                        index=index,
                    )
                )
    return records


def _record_from_resource_row(
    row: dict[str, str],
    *,
    provider: str,
    organism: str,
    snapshot_id: str,
    annotation_source: str | None,
    provider_release: str,
    source_file: str,
    index: int,
) -> PathwayMembershipRecordV2:
    source = _first(row, "annotation_source") or annotation_source or provider
    term_id = _first(row, "term_id", "pathway_id", "go_id", "class_id")
    member_entity_id = _first(
        row,
        "member_entity_id",
        "entity_id",
        "reference_entity_id",
        "mapped_gene_id",
        "gene",
        "gene_id",
    )
    canonical_gene_ids = tuple(
        item.strip().upper()
        for item in _first(
            row, "canonical_gene_ids", "member_gene_id", "mapped_gene_id", "gene"
        ).split(";")
        if item.strip()
    )
    completeness = _first(row, "completeness_status") or "complete"
    if completeness not in ALLOWED_COMPLETENESS:
        completeness = "unknown"
    return PathwayMembershipRecordV2(
        membership_record_id=_first(row, "membership_record_id")
        or f"{snapshot_id}:{term_id}:{member_entity_id}:{index}",
        provider=provider,
        annotation_source=source,
        term_id=term_id,
        term_name=_first(row, "term_name", "pathway_name", "name") or term_id,
        member_entity_id=member_entity_id,
        member_entity_type=_first(row, "member_entity_type", "entity_type") or "gene",
        canonical_gene_ids=canonical_gene_ids,
        membership_type=_first(row, "membership_type", "annotation_dataset", "namespace")
        or "curated_annotation_membership",
        organism=_first(row, "organism", "taxon") or organism,
        hierarchy_parent_ids=tuple(
            item.strip() for item in _first(row, "hierarchy_parent_ids").split(";") if item.strip()
        ),
        provider_release=_first(row, "provider_release") or provider_release,
        snapshot_id=snapshot_id,
        completeness_status=completeness,
        provenance=(source_file,),
        warnings=tuple(item.strip() for item in _first(row, "warnings").split(";") if item.strip()),
    )


def _deduplicate(records: list[PathwayMembershipRecordV2]) -> list[PathwayMembershipRecordV2]:
    by_key: dict[tuple[str, str, str, tuple[str, ...]], PathwayMembershipRecordV2] = {}
    for record in records:
        key = (
            record.provider,
            record.term_id,
            record.member_entity_id,
            record.canonical_gene_ids,
        )
        by_key.setdefault(key, record)
    return list(by_key.values())


def _write_records(path: Path, records: list[PathwayMembershipRecordV2]) -> None:
    rows = [asdict(record) for record in records]
    _write_rows(path, rows)


def _write_coverage(path: Path, records: list[PathwayMembershipRecordV2]) -> None:
    rows = []
    by_term: dict[str, list[PathwayMembershipRecordV2]] = {}
    for record in records:
        by_term.setdefault(record.term_id, []).append(record)
    for term_id, term_records in sorted(by_term.items()):
        rows.append(
            {
                "term_id": term_id,
                "term_name": term_records[0].term_name,
                "provider": term_records[0].provider,
                "annotation_source": term_records[0].annotation_source,
                "membership_record_count": len(term_records),
                "mapped_gene_count": len(
                    {gene for record in term_records for gene in record.canonical_gene_ids}
                ),
                "completeness_status": (
                    "complete"
                    if all(record.completeness_status == "complete" for record in term_records)
                    else "partial"
                ),
            }
        )
    _write_rows(path, rows)


def _write_incomplete(path: Path, records: list[PathwayMembershipRecordV2]) -> None:
    rows = [
        {
            "term_id": record.term_id,
            "term_name": record.term_name,
            "member_entity_id": record.member_entity_id,
            "completeness_status": record.completeness_status,
            "warnings": ";".join(record.warnings),
        }
        for record in records
        if record.completeness_status != "complete"
    ]
    _write_rows(path, rows)


def _write_rows(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["empty"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: ";".join(value) if isinstance(value, tuple) else value
                    for key, value in row.items()
                }
            )


def _record_from_row(row: dict[str, str]) -> PathwayMembershipRecordV2:
    return PathwayMembershipRecordV2(
        membership_record_id=row["membership_record_id"],
        provider=row["provider"],
        annotation_source=row["annotation_source"],
        term_id=row["term_id"],
        term_name=row["term_name"],
        member_entity_id=row["member_entity_id"],
        member_entity_type=row["member_entity_type"],
        canonical_gene_ids=tuple(item for item in row["canonical_gene_ids"].split(";") if item),
        membership_type=row["membership_type"],
        organism=row["organism"],
        hierarchy_parent_ids=tuple(item for item in row["hierarchy_parent_ids"].split(";") if item),
        provider_release=row["provider_release"],
        snapshot_id=row["snapshot_id"],
        completeness_status=row["completeness_status"],
        provenance=tuple(item for item in row["provenance"].split(";") if item),
        warnings=tuple(item for item in row["warnings"].split(";") if item),
    )


def _first(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key, "")
        if value:
            return value.strip()
    return ""
