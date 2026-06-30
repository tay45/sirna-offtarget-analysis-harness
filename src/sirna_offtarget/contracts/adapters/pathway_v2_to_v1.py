from __future__ import annotations

import warnings
from typing import Any

from sirna_offtarget.contracts.stage_results import PathwayEnrichmentResultV2


def pathway_v2_to_v1_payload(contract: PathwayEnrichmentResultV2) -> dict[str, Any]:
    """Return a deprecated compatibility view for external V1 consumers only."""
    warnings.warn(
        "PathwayEnrichmentResultV1 compatibility views are deprecated; "
        "runtime stages consume PathwayEnrichmentResultV2.",
        DeprecationWarning,
        stacklevel=2,
    )
    payload = contract.payload
    return {
        "deprecated_compatibility_payload": True,
        "pathway_results": {},
        "pathway_gene_count": 0,
        "provider_results": payload.provider_calculated_enrichment,
        "locally_calculated_results": payload.locally_calculated_enrichment,
        "consensus_results": payload.enrichment_consensus,
        "regulon_context_results": payload.regulon_context,
        "gene_sets": payload.gene_sets,
        "background_universe": payload.background_universe,
        "annotation_membership_summary": payload.annotation_membership_summary,
        "identifier_mapping_summary": payload.identifier_mapping_summary,
        "provider_snapshot_manifest": payload.provider_snapshot_manifest,
        "warnings": [
            *payload.warnings,
            "regulon_context_results are context only and are not enrichment records",
        ],
    }
