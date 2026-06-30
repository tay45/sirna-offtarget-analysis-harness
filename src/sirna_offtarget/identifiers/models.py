from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityRecord:
    entity_id: str
    canonical_identifier: str
    display_name: str
    entity_type: str
    organism: str
    source_identifiers: tuple[str, ...]
    member_entities: tuple[str, ...] = ()
    mapping_confidence: str = "unambiguous"
    provenance: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
