from __future__ import annotations

from sirna_offtarget.pathway.models import IdentifierMappingResult


def normalize_identifier(identifier: str, organism: str = "human") -> IdentifierMappingResult:
    normalized = identifier.strip()
    inferred = "ensembl_transcript_id" if normalized.startswith("ENST") else "hgnc_symbol"
    return IdentifierMappingResult(
        input_identifier=identifier,
        inferred_input_type=inferred,
        normalized_identifier=normalized,
        mapped_identifier=normalized,
        organism=organism,
        mapping_status="mapped",
        ambiguity=False,
        candidate_mappings=(normalized,),
        mapping_provider="local_synthetic_mapping",
        mapping_database_version="synthetic_snapshot_v1",
    )
