from __future__ import annotations

from sirna_offtarget.pathway.fetch.base import ProviderRequest


def build_panther_enrichment_request(
    genes: list[str],
    *,
    organism: str = "HUMAN",
    annotation_dataset: str = "PANTHER_PATHWAY",
    reference_genes: list[str] | None = None,
    endpoint: str = "https://pantherdb.org/services/oai/pantherdb/enrich/overrep",
) -> ProviderRequest:
    params = {
        "geneInputList": ",".join(genes),
        "organism": organism,
        "annotDataSet": annotation_dataset,
        "enrichmentTestType": "FISHER",
        "correction": "FDR",
    }
    if reference_genes:
        params["refInputList"] = ",".join(reference_genes)
    return ProviderRequest(
        provider="panther",
        endpoint=endpoint,
        method="GET",
        query_parameters=params,
        headers={"Accept": "application/json"},
        pagination="single_response",
        release_discovery="dataset_release_field_or_null",
        timeout_seconds=25.0,
    )
