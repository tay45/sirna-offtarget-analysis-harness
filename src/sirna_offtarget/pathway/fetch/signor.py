from __future__ import annotations

from sirna_offtarget.pathway.fetch.base import ProviderRequest


def build_signor_request(
    endpoint: str = "https://signor.uniroma2.it/getData.php",
) -> ProviderRequest:
    return ProviderRequest(
        provider="signor",
        endpoint=endpoint,
        method="GET",
        query_parameters={"organism": "human", "format": "json"},
        headers={"Accept": "application/json"},
        pagination="single_response",
        release_discovery="export_version_or_retrieval_date",
        timeout_seconds=25.0,
    )
