from __future__ import annotations

from sirna_offtarget.pathway.fetch.base import ProviderRequest


def build_reactome_content_request(
    stable_id: str,
    endpoint: str = "https://reactome.org/ContentService/data/query",
) -> ProviderRequest:
    return ProviderRequest(
        provider="reactome_content",
        endpoint=f"{endpoint}/{stable_id}",
        method="GET",
        headers={"Accept": "application/json"},
        pagination="nested_event_traversal",
        release_discovery="content_service_release",
        validation=("non_empty_body", "status_2xx", "preserve_reactions_complexes_entity_sets"),
    )
