from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from sirna_offtarget.identifiers.exceptions import IdentifierSnapshotError
from sirna_offtarget.identifiers.snapshots import IdentifierSnapshotRecord, verify_identifier_cache


@dataclass(frozen=True)
class IdentifierResolutionRecordV2:
    resolution_id: str
    input_identifier: str
    input_namespace: str
    detected_type: str
    normalized_input: str
    expected_entity_type: str | None
    resolved_entity_id: str | None
    canonical_gene_ids: tuple[str, ...]
    approved_symbol: str | None
    organism: str
    mapping_source: str
    mapping_record_ids: tuple[str, ...]
    identifier_snapshot_id: str
    mapping_confidence: float
    ambiguity_status: str
    ambiguity_group_id: str | None
    candidate_mappings: tuple[str, ...]
    deprecated_status: str
    organism_match: bool
    exclusion_status: str
    exclusion_reason: str | None
    warnings: tuple[str, ...]

    def asdict(self) -> dict[str, object]:
        return asdict(self)


class IdentifierResolverV2:
    def __init__(
        self,
        verified_identifier_snapshot_path: Path,
        organism: str,
        ambiguity_policy: str = "exclude",
        provider_id_namespace_map: dict[str, str] | None = None,
        transcript_collapse_policy: str | None = None,
    ) -> None:
        self.snapshot_path = verified_identifier_snapshot_path
        self.organism = organism
        self.ambiguity_policy = ambiguity_policy
        self.provider_id_namespace_map = provider_id_namespace_map or {}
        self.transcript_collapse_policy = transcript_collapse_policy
        errors = verify_identifier_cache(self.snapshot_path.parent)
        if errors:
            raise IdentifierSnapshotError("; ".join(errors))
        self.manifest = self._read_manifest()
        if self.manifest.get("organism") != organism:
            raise IdentifierSnapshotError(
                "identifier snapshot organism mismatch: "
                f"{self.manifest.get('organism')} != {organism}"
            )
        self.snapshot_id = str(self.manifest.get("snapshot_id", self.snapshot_path.name))
        self.records = self._read_records()
        self.index: dict[str, list[IdentifierSnapshotRecord]] = {}
        for record in self.records:
            keys = [
                record.input_identifier,
                record.canonical_symbol or "",
                *(record.aliases or ()),
                *(record.previous_symbols or ()),
            ]
            for key in keys:
                if key:
                    self.index.setdefault(key.upper(), []).append(record)

    def resolve_one(
        self, identifier: str, expected_entity_type: str | None = None
    ) -> IdentifierResolutionRecordV2:
        normalized = identifier.strip().upper()
        matches = self.index.get(normalized, [])
        if not matches:
            return self._unresolved(identifier, expected_entity_type, "not_in_snapshot")
        canonical = {record.canonical_gene_id for record in matches if record.canonical_gene_id}
        ambiguous = len(canonical) > 1 or any(record.ambiguous for record in matches)
        if ambiguous and self.ambiguity_policy != "expand":
            candidates = tuple(sorted(item for item in canonical if item))
            return IdentifierResolutionRecordV2(
                resolution_id=f"{self.snapshot_id}:{normalized}:ambiguous",
                input_identifier=identifier,
                input_namespace=matches[0].identifier_type,
                detected_type=matches[0].identifier_type,
                normalized_input=normalized,
                expected_entity_type=expected_entity_type,
                resolved_entity_id=None,
                canonical_gene_ids=(),
                approved_symbol=None,
                organism=self.organism,
                mapping_source=matches[0].mapping_source,
                mapping_record_ids=tuple(record.input_identifier for record in matches),
                identifier_snapshot_id=self.snapshot_id,
                mapping_confidence=0.0,
                ambiguity_status="ambiguous",
                ambiguity_group_id=f"{self.snapshot_id}:{normalized}",
                candidate_mappings=candidates,
                deprecated_status="deprecated"
                if normalized in {item for record in matches for item in record.previous_symbols}
                else "current",
                organism_match=True,
                exclusion_status="excluded",
                exclusion_reason="ambiguous_identifier",
                warnings=("ambiguous identifier excluded by policy",),
            )
        record = matches[0]
        canonical_gene = record.canonical_gene_id
        if not canonical_gene:
            return self._unresolved(
                identifier, expected_entity_type, record.unmapped_reason or "unmapped"
            )
        deprecated = normalized in {item.upper() for item in record.previous_symbols}
        return IdentifierResolutionRecordV2(
            resolution_id=f"{self.snapshot_id}:{normalized}",
            input_identifier=identifier,
            input_namespace=record.identifier_type,
            detected_type=record.identifier_type,
            normalized_input=normalized,
            expected_entity_type=expected_entity_type,
            resolved_entity_id=f"gene:{canonical_gene}",
            canonical_gene_ids=(canonical_gene,),
            approved_symbol=record.canonical_symbol,
            organism=self.organism,
            mapping_source=record.mapping_source,
            mapping_record_ids=(record.input_identifier,),
            identifier_snapshot_id=self.snapshot_id,
            mapping_confidence=1.0 if record.confidence == "unambiguous" else 0.5,
            ambiguity_status="expanded" if ambiguous else "unambiguous",
            ambiguity_group_id=None,
            candidate_mappings=record.candidate_mappings,
            deprecated_status="deprecated" if deprecated else "current",
            organism_match=True,
            exclusion_status="included",
            exclusion_reason=None,
            warnings=("deprecated identifier resolved",) if deprecated else (),
        )

    def resolve_many(self, identifiers: list[str]) -> list[IdentifierResolutionRecordV2]:
        return [self.resolve_one(identifier) for identifier in identifiers]

    def resolve_provider_entity(
        self, provider: str, raw_identifier: str, raw_entity_type: str | None = None
    ) -> IdentifierResolutionRecordV2:
        expected = raw_entity_type or self.provider_id_namespace_map.get(provider)
        return self.resolve_one(raw_identifier, expected_entity_type=expected)

    def resolve_annotation_member(
        self, provider: str, raw_identifier: str
    ) -> IdentifierResolutionRecordV2:
        return self.resolve_provider_entity(provider, raw_identifier, "gene")

    def resolve_expression_gene(self, raw_identifier: str) -> IdentifierResolutionRecordV2:
        return self.resolve_one(raw_identifier, expected_entity_type="gene")

    def _read_manifest(self) -> dict[str, object]:
        for name in ("identifier_manifest.json", "identifier_snapshot_manifest.json"):
            path = self.snapshot_path / name
            if path.exists():
                data = json.loads(path.read_text())
                if isinstance(data, dict):
                    return data
                raise IdentifierSnapshotError(f"identifier manifest is not an object {path}")
        raise IdentifierSnapshotError(f"missing identifier manifest {self.snapshot_path}")

    def _read_records(self) -> list[IdentifierSnapshotRecord]:
        records_path = self.snapshot_path / "records.jsonl"
        records: list[IdentifierSnapshotRecord] = []
        for line in records_path.read_text().splitlines():
            data = json.loads(line)
            records.append(
                IdentifierSnapshotRecord(
                    input_identifier=data["input_identifier"],
                    identifier_type=data["identifier_type"],
                    canonical_gene_id=data.get("canonical_gene_id"),
                    canonical_symbol=data.get("canonical_symbol"),
                    aliases=tuple(data.get("aliases", ())),
                    previous_symbols=tuple(data.get("previous_symbols", ())),
                    organism=data["organism"],
                    mapping_source=data["mapping_source"],
                    confidence=data["confidence"],
                    ambiguous=bool(data["ambiguous"]),
                    candidate_mappings=tuple(data.get("candidate_mappings", ())),
                    unmapped_reason=data.get("unmapped_reason"),
                )
            )
        return records

    def _unresolved(
        self, identifier: str, expected_entity_type: str | None, reason: str
    ) -> IdentifierResolutionRecordV2:
        normalized = identifier.strip().upper()
        return IdentifierResolutionRecordV2(
            resolution_id=f"{self.snapshot_id}:{normalized}:unresolved",
            input_identifier=identifier,
            input_namespace="unknown",
            detected_type="unknown",
            normalized_input=normalized,
            expected_entity_type=expected_entity_type,
            resolved_entity_id=None,
            canonical_gene_ids=(),
            approved_symbol=None,
            organism=self.organism,
            mapping_source="identifier-snapshot-v2",
            mapping_record_ids=(),
            identifier_snapshot_id=self.snapshot_id,
            mapping_confidence=0.0,
            ambiguity_status="unresolved",
            ambiguity_group_id=None,
            candidate_mappings=(),
            deprecated_status="unknown",
            organism_match=True,
            exclusion_status="excluded",
            exclusion_reason=reason,
            warnings=("unresolved identifier was not mapped to a gene",),
        )
