from __future__ import annotations

from sirna_offtarget.pathway.fetch.base import ProviderRequest


def build_omnipath_interactions_request(
    *,
    organism: int = 9606,
    endpoint: str = "https://omnipathdb.org/interactions",
) -> ProviderRequest:
    return ProviderRequest(
        provider="omnipath",
        endpoint=endpoint,
        method="GET",
        query_parameters={
            "organisms": str(organism),
            "format": "json",
            "fields": "sources,references",
        },
        headers={"Accept": "application/json"},
        pagination="single_response",
        release_discovery="resource_date_or_response_headers",
    )
