from __future__ import annotations

from dataclasses import dataclass

MEMBERSHIP_SCHEMA_VERSION = "annotation-membership-snapshot-v2"
MEMBERSHIP_PARSER_VERSION = "annotation-membership-tsv-parser-v1"


@dataclass(frozen=True)
class AnnotationMembershipSnapshotV2:
    snapshot_id: str
    provider: str
    annotation_source: str
    organism: str
    provider_release: str
    provider_version: str
    source_files: tuple[str, ...]
    source_checksums: dict[str, str]
    normalized_checksums: dict[str, str]
    parser_version: str
    schema_version: str
    term_count: int
    membership_record_count: int
    mapped_gene_count: int
    unmapped_entity_count: int
    incomplete_term_count: int
    completeness_status: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PathwayMembershipRecordV2:
    membership_record_id: str
    provider: str
    annotation_source: str
    term_id: str
    term_name: str
    member_entity_id: str
    member_entity_type: str
    canonical_gene_ids: tuple[str, ...]
    membership_type: str
    organism: str
    hierarchy_parent_ids: tuple[str, ...]
    provider_release: str
    snapshot_id: str
    completeness_status: str
    provenance: tuple[str, ...]
    warnings: tuple[str, ...] = ()
