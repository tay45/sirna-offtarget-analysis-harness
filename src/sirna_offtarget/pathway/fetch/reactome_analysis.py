from __future__ import annotations

import json

from sirna_offtarget.pathway.fetch.base import ProviderRequest


def build_reactome_analysis_request(
    identifiers: list[str],
    *,
    species: str = "Homo sapiens",
    endpoint: str = "https://reactome.org/AnalysisService/identifiers/projection",
    include_interactors: bool = False,
) -> ProviderRequest:
    body = "\n".join(identifiers).encode()
    return ProviderRequest(
        provider="reactome_analysis",
        endpoint=endpoint,
        method="POST",
        query_parameters={
            "species": species,
            "includeInteractors": json.dumps(include_interactors),
        },
        body=body,
        headers={"Accept": "application/json"},
        content_type="text/plain",
        pagination="token_then_pathway_pages",
        release_discovery="analysis_service_payload",
        timeout_seconds=30.0,
    )
