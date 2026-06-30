from __future__ import annotations

from sirna_offtarget.pathway.fetch.omnipath import build_omnipath_interactions_request
from sirna_offtarget.pathway.fetch.panther import build_panther_enrichment_request
from sirna_offtarget.pathway.fetch.reactome_analysis import build_reactome_analysis_request
from sirna_offtarget.pathway.fetch.reactome_content import build_reactome_content_request
from sirna_offtarget.pathway.fetch.reactome_fi import build_reactome_fi_request
from sirna_offtarget.pathway.fetch.retry import backoff_seconds
from sirna_offtarget.pathway.fetch.signor import build_signor_request
from sirna_offtarget.pathway.fetch.validation import validate_response_metadata


def test_provider_specific_request_builders_encode_provider_semantics() -> None:
    reactome = build_reactome_analysis_request(["TP53"], species="Homo sapiens")
    assert reactome.method == "POST"
    assert reactome.pagination == "token_then_pathway_pages"
    panther = build_panther_enrichment_request(
        ["TP53"],
        reference_genes=["TP53", "MDM2"],
        annotation_dataset="GO_BIOLOGICAL_PROCESS",
    )
    assert panther.query_parameters["refInputList"] == "TP53,MDM2"
    assert panther.query_parameters["correction"] == "FDR"
    assert build_omnipath_interactions_request().query_parameters["organisms"] == "9606"
    assert build_signor_request().release_discovery == "export_version_or_retrieval_date"
    assert "force_unsigned_semantics" in build_reactome_fi_request().validation
    assert (
        "preserve_reactions_complexes_entity_sets"
        in build_reactome_content_request("R-HSA-1").validation
    )
    assert backoff_seconds(3) == 8.0
    assert (
        validate_response_metadata(
            status_code=200,
            content_length=10,
            max_response_size=100,
            content_type="application/json",
            expected_content_type="json",
        )
        == []
    )


def test_response_metadata_validation_accumulates_all_provider_fetch_errors() -> None:
    assert validate_response_metadata(
        status_code=503,
        content_length=0,
        max_response_size=10,
        content_type="text/html",
        expected_content_type="json",
    ) == [
        "unexpected status 503",
        "empty response",
        "unexpected content type 'text/html'",
    ]
    assert validate_response_metadata(
        status_code=200,
        content_length=11,
        max_response_size=10,
        content_type="application/json",
        expected_content_type=None,
    ) == ["response exceeds maximum configured size"]
