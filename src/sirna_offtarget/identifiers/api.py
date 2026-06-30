from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from sirna_offtarget.identifiers.models import EntityRecord

_ENSEMBL_GENE = re.compile(r"^ENS[A-Z]*G\d+(?:\.\d+)?$")
_ENSEMBL_TX = re.compile(r"^ENS[A-Z]*T\d+(?:\.\d+)?$")
_UNIPROT = re.compile(r"^(?:[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9][A-Z][A-Z0-9]{2}[0-9])$")
_REACTOME = re.compile(r"^R-[A-Z]{3}-\d+(?:\.\d+)?$")
_SIGNOR = re.compile(r"^SIGNOR-[A-Z0-9_-]+$")


@dataclass(frozen=True)
class IdentifierResolution:
    input_identifier: str
    input_identifier_type: str
    normalized_identifier: str
    mapped_identifier: str | None
    output_identifier_type: str
    status: str
    ambiguity_status: str
    candidate_mappings: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def detect_identifier_type(identifier: str) -> str:
    value = identifier.strip()
    upper = value.upper()
    if not value:
        return "invalid"
    if _ENSEMBL_GENE.match(value):
        return "ensembl_gene_id"
    if _ENSEMBL_TX.match(value):
        return "ensembl_transcript_id"
    if _REACTOME.match(upper):
        return "reactome_stable_id"
    if _SIGNOR.match(upper):
        return "signor_entity_id"
    if value.isdigit():
        return "entrez_gene_id"
    if _UNIPROT.match(upper):
        return "uniprot_accession"
    if upper.startswith(("COMPLEX:", "FAMILY:", "SET:")):
        return "pathway_entity_set"
    return "hgnc_symbol"


def normalize_identifier_value(identifier: str, identifier_type: str | None = None) -> str:
    value = identifier.strip()
    inferred = identifier_type or detect_identifier_type(value)
    if inferred in {"hgnc_symbol", "uniprot_accession", "reactome_stable_id", "signor_entity_id"}:
        return value.upper()
    if inferred in {"ensembl_gene_id", "ensembl_transcript_id"}:
        return value.split(".", maxsplit=1)[0]
    return value


def resolve_identifier(
    identifier: str,
    *,
    aliases: dict[str, tuple[str, ...]] | None = None,
) -> IdentifierResolution:
    identifier_type = detect_identifier_type(identifier)
    if identifier_type == "invalid":
        return IdentifierResolution(
            input_identifier=identifier,
            input_identifier_type="invalid",
            normalized_identifier="",
            mapped_identifier=None,
            output_identifier_type="hgnc_symbol",
            status="invalid",
            ambiguity_status="none",
            candidate_mappings=(),
            warnings=("empty identifier",),
        )
    normalized = normalize_identifier_value(identifier, identifier_type)
    alias_index = aliases or {}
    matches = tuple(sorted(alias_index.get(normalized, alias_index.get(identifier.strip(), ()))))
    if len(matches) > 1:
        return IdentifierResolution(
            identifier.strip(),
            identifier_type,
            normalized,
            None,
            "hgnc_symbol",
            "ambiguous",
            "ambiguous",
            matches,
            ("multiple candidate mappings",),
        )
    mapped = matches[0] if matches else normalized
    output_type = (
        "hgnc_symbol"
        if identifier_type in {"hgnc_symbol", "pathway_entity_set"}
        else identifier_type
    )
    return IdentifierResolution(
        identifier.strip(),
        identifier_type,
        normalized,
        mapped,
        output_type,
        "mapped",
        "unambiguous",
        matches,
    )


def resolve_entity(
    identifier: str,
    *,
    organism: str,
    aliases: dict[str, tuple[str, ...]] | None = None,
) -> EntityRecord:
    resolution = resolve_identifier(identifier, aliases=aliases)
    canonical = (
        resolution.mapped_identifier or resolution.normalized_identifier or identifier.strip()
    )
    entity_type = (
        "complex_or_family"
        if resolution.input_identifier_type == "pathway_entity_set"
        else "gene_or_gene_product"
    )
    digest = hashlib.sha256(f"{organism}|{canonical}|{entity_type}".encode()).hexdigest()[:16]
    return EntityRecord(
        entity_id=f"entity_{digest}",
        canonical_identifier=canonical,
        display_name=canonical,
        entity_type=entity_type,
        organism=organism,
        source_identifiers=(identifier.strip(),),
        mapping_confidence=resolution.ambiguity_status,
        provenance=("central_identifier_resolution",),
        warnings=resolution.warnings,
    )
