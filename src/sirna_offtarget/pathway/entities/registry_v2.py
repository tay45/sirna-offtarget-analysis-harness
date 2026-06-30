from __future__ import annotations

import hashlib
from dataclasses import asdict, replace
from typing import Any

from sirna_offtarget.identifiers.resolver_v2 import IdentifierResolutionRecordV2
from sirna_offtarget.pathway.semantics import BiologicalEntityRecordV2


class BiologicalEntityRegistryV2:
    def __init__(self, organism: str, identifier_snapshot_id: str) -> None:
        self.organism = organism
        self.identifier_snapshot_id = identifier_snapshot_id
        self._entities: dict[str, BiologicalEntityRecordV2] = {}
        self._memberships: dict[str, set[str]] = {}
        self._unsupported: dict[str, BiologicalEntityRecordV2] = {}

    def register_from_resolution(
        self,
        resolution: IdentifierResolutionRecordV2,
        *,
        provider: str,
        provider_record_id: str = "",
        raw_entity_type: str | None = None,
    ) -> BiologicalEntityRecordV2:
        entity_type = _normalize_entity_type(raw_entity_type or resolution.expected_entity_type)
        if entity_type != "gene" and not (
            entity_type == "unknown"
            and resolution.resolved_entity_id
            and resolution.canonical_gene_ids
        ):
            return self._register_non_gene(
                entity_type,
                resolution.input_identifier,
                provider=provider,
                provider_record_id=provider_record_id,
                mapping_confidence=resolution.mapping_confidence,
                ambiguity_status=resolution.ambiguity_status,
                identifier_snapshot_id=resolution.identifier_snapshot_id,
                warnings=resolution.warnings,
            )
        if resolution.resolved_entity_id and resolution.canonical_gene_ids:
            return self.register_gene(
                resolution.canonical_gene_ids[0],
                display_name=resolution.approved_symbol or resolution.canonical_gene_ids[0],
                source_identifier=resolution.input_identifier,
                provider=provider,
                provider_record_id=provider_record_id,
                mapping_confidence=resolution.mapping_confidence,
                ambiguity_status=resolution.ambiguity_status,
                identifier_snapshot_id=resolution.identifier_snapshot_id,
            )
        return self.register_unknown(
            resolution.input_identifier,
            provider=provider,
            provider_record_id=provider_record_id,
            warnings=resolution.warnings or ("unresolved identifier preserved as unknown entity",),
        )

    def register_gene(
        self,
        canonical_gene_id: str,
        *,
        display_name: str | None = None,
        source_identifier: str | None = None,
        provider: str = "",
        provider_record_id: str = "",
        mapping_confidence: float = 1.0,
        ambiguity_status: str = "unambiguous",
        identifier_snapshot_id: str | None = None,
    ) -> BiologicalEntityRecordV2:
        return self._upsert(
            BiologicalEntityRecordV2(
                entity_id=_entity_id("gene", self.organism, canonical_gene_id),
                entity_type="gene",
                display_name=display_name or canonical_gene_id,
                canonical_identifier=canonical_gene_id,
                organism=self.organism,
                source_identifiers=tuple(item for item in (source_identifier,) if item),
                canonical_gene_ids=(canonical_gene_id,),
                member_entity_ids=(),
                entity_set_semantics="single_gene",
                identifier_snapshot_id=identifier_snapshot_id or self.identifier_snapshot_id,
                mapping_confidence=mapping_confidence,
                ambiguity_status=ambiguity_status,
                provider_sources=tuple(item for item in (provider,) if item),
                provider_record_ids=tuple(item for item in (provider_record_id,) if item),
                compartments=(),
                contexts=(),
            )
        )

    def register_protein(self, identifier: str, **kwargs: object) -> BiologicalEntityRecordV2:
        return self._register_non_gene("protein", identifier, **kwargs)

    def register_transcript(self, identifier: str, **kwargs: object) -> BiologicalEntityRecordV2:
        return self._register_non_gene("transcript", identifier, **kwargs)

    def register_complex(self, identifier: str, **kwargs: object) -> BiologicalEntityRecordV2:
        return self._register_non_gene("complex", identifier, **kwargs)

    def register_protein_family(
        self, identifier: str, **kwargs: object
    ) -> BiologicalEntityRecordV2:
        return self._register_non_gene("protein_family", identifier, **kwargs)

    def register_entity_set(self, identifier: str, **kwargs: object) -> BiologicalEntityRecordV2:
        return self._register_non_gene("entity_set", identifier, **kwargs)

    def register_reaction(self, identifier: str, **kwargs: object) -> BiologicalEntityRecordV2:
        return self._register_non_gene("reaction", identifier, **kwargs)

    def register_pathway(self, identifier: str, **kwargs: object) -> BiologicalEntityRecordV2:
        return self._register_non_gene("pathway", identifier, **kwargs)

    def register_small_molecule(
        self, identifier: str, **kwargs: object
    ) -> BiologicalEntityRecordV2:
        return self._register_non_gene("small_molecule", identifier, **kwargs)

    def register_phenotype(self, identifier: str, **kwargs: object) -> BiologicalEntityRecordV2:
        return self._register_non_gene("phenotype", identifier, **kwargs)

    def register_unknown(
        self,
        identifier: str,
        *,
        provider: str = "",
        provider_record_id: str = "",
        warnings: tuple[str, ...] = (),
    ) -> BiologicalEntityRecordV2:
        entity = self._register_non_gene(
            "unknown",
            identifier,
            provider=provider,
            provider_record_id=provider_record_id,
            mapping_confidence=0.0,
            ambiguity_status="unresolved",
            warnings=warnings,
        )
        self._unsupported[entity.entity_id] = entity
        return entity

    def add_membership(self, parent_entity_id: str, member_entity_id: str) -> None:
        self._memberships.setdefault(parent_entity_id, set()).add(member_entity_id)
        if parent_entity_id in self._entities:
            entity = self._entities[parent_entity_id]
            self._entities[parent_entity_id] = replace(
                entity,
                member_entity_ids=tuple(sorted(self._memberships[parent_entity_id])),
            )

    def get(self, entity_id: str) -> BiologicalEntityRecordV2 | None:
        return self._entities.get(entity_id)

    def all_entities(self) -> tuple[BiologicalEntityRecordV2, ...]:
        return tuple(self._entities[key] for key in sorted(self._entities))

    def unsupported_entities(self) -> tuple[BiologicalEntityRecordV2, ...]:
        return tuple(self._unsupported[key] for key in sorted(self._unsupported))

    def expand_for_policy(self, entity_id: str, policy: str) -> tuple[str, ...]:
        if policy == "no_expansion":
            return (entity_id,)
        if policy in {
            "expand_resolvable_members",
            "expand_for_expression_join_only",
            "expand_for_visualization_only",
        }:
            return tuple(sorted(self._memberships.get(entity_id, {entity_id})))
        msg = f"unsupported entity expansion policy: {policy}"
        raise ValueError(msg)

    def to_rows(self) -> list[dict[str, object]]:
        return [asdict(entity) for entity in self.all_entities()]

    def unsupported_rows(self) -> list[dict[str, object]]:
        return [asdict(entity) for entity in self.unsupported_entities()]

    def _register_non_gene(
        self,
        entity_type: str,
        identifier: str,
        **kwargs: object,
    ) -> BiologicalEntityRecordV2:
        provider = str(kwargs.get("provider", ""))
        provider_record_id = str(kwargs.get("provider_record_id", ""))
        warnings = _as_tuple(kwargs.get("warnings"))
        return self._upsert(
            BiologicalEntityRecordV2(
                entity_id=_entity_id(entity_type, self.organism, identifier),
                entity_type=entity_type,
                display_name=str(kwargs.get("display_name") or identifier),
                canonical_identifier=identifier,
                organism=self.organism,
                source_identifiers=(identifier,),
                canonical_gene_ids=(),
                member_entity_ids=(),
                entity_set_semantics=str(kwargs.get("entity_set_semantics") or "not_expanded"),
                identifier_snapshot_id=str(
                    kwargs.get("identifier_snapshot_id") or self.identifier_snapshot_id
                ),
                mapping_confidence=_as_float(kwargs.get("mapping_confidence"), 0.0),
                ambiguity_status=str(kwargs.get("ambiguity_status") or "unresolved"),
                provider_sources=tuple(item for item in (provider,) if item),
                provider_record_ids=tuple(item for item in (provider_record_id,) if item),
                compartments=_as_tuple(kwargs.get("compartments")),
                contexts=_as_tuple(kwargs.get("contexts")),
                warnings=warnings,
            )
        )

    def _upsert(self, entity: BiologicalEntityRecordV2) -> BiologicalEntityRecordV2:
        existing = self._entities.get(entity.entity_id)
        if existing is None:
            self._entities[entity.entity_id] = entity
            return entity
        merged = replace(
            existing,
            source_identifiers=tuple(
                sorted(set(existing.source_identifiers) | set(entity.source_identifiers))
            ),
            provider_sources=tuple(
                sorted(set(existing.provider_sources) | set(entity.provider_sources))
            ),
            provider_record_ids=tuple(
                sorted(set(existing.provider_record_ids) | set(entity.provider_record_ids))
            ),
            warnings=tuple(sorted(set(existing.warnings) | set(entity.warnings))),
        )
        self._entities[entity.entity_id] = merged
        return merged


def _as_tuple(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, tuple | list | set):
        return tuple(str(item) for item in value)
    return (str(value),)


def _as_float(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _entity_id(entity_type: str, organism: str, identifier: str) -> str:
    stable = hashlib.sha256(f"{entity_type}|{organism}|{identifier}".encode()).hexdigest()[:12]
    return f"{entity_type}:{stable}"


def _normalize_entity_type(value: str | None) -> str:
    normalized = str(value or "unknown").strip().lower()
    aliases = {
        "family": "protein_family",
        "proteinfamily": "protein_family",
        "set": "entity_set",
        "definedset": "entity_set",
        "candidateset": "entity_set",
        "openset": "entity_set",
        "simpleentity": "small_molecule",
        "reactionlikeevent": "reaction",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized in {
        "gene",
        "protein",
        "transcript",
        "complex",
        "protein_family",
        "entity_set",
        "pathway",
        "reaction",
        "small_molecule",
        "phenotype",
        "unknown",
    }:
        return normalized
    return "unknown"
