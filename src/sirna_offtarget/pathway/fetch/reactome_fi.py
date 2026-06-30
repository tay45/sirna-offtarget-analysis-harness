from __future__ import annotations

from sirna_offtarget.pathway.fetch.base import ProviderRequest


def build_reactome_fi_request(
    endpoint: str = "https://reactome.org/ContentService/data/interactors/static/molecule",
) -> ProviderRequest:
    return ProviderRequest(
        provider="reactome_fi",
        endpoint=endpoint,
        method="GET",
        query_parameters={"species": "Homo sapiens"},
        headers={"Accept": "application/json"},
        pagination="single_response",
        release_discovery="reactome_release_or_null",
        validation=("non_empty_body", "status_2xx", "force_unsigned_semantics"),
    )
