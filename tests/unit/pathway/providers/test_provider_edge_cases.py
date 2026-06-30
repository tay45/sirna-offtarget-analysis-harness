from __future__ import annotations

from sirna_offtarget.pathway.providers.omnipath import OmniPathProvider
from sirna_offtarget.pathway.providers.panther import PantherProvider
from sirna_offtarget.pathway.providers.reactome_analysis import ReactomeAnalysisProvider
from sirna_offtarget.pathway.providers.reactome_content import ReactomeContentProvider
from sirna_offtarget.pathway.providers.reactome_fi import ReactomeFIProvider
from sirna_offtarget.pathway.providers.signor import SignorProvider


def test_provider_load_cached_methods(tmp_path) -> None:
    (tmp_path / "omnipath.tsv").write_text("source\ttarget\nA\tB\n")
    (tmp_path / "signor.tsv").write_text("source\ttarget\teffect\nA\tB\tactivation\n")
    (tmp_path / "reactome_fi.tsv").write_text("source\ttarget\nA\tB\n")
    (tmp_path / "reactome_content.tsv").write_text("source\ttarget\tpathway_id\nA\tB\tR\n")
    (tmp_path / "reactome_analysis.tsv").write_text("gene\tpathway_id\tpathway_name\nA\tR\tP\n")
    (tmp_path / "panther.tsv").write_text("gene\tpathway_id\tpathway_name\nA\tP\tP\n")
    assert OmniPathProvider().load_cached(tmp_path).record_count == 1
    assert SignorProvider().load_cached(tmp_path).record_count == 1
    assert ReactomeFIProvider().load_cached(tmp_path).record_count == 1
    assert ReactomeContentProvider().load_cached(tmp_path).record_count == 1
    assert ReactomeAnalysisProvider().load_cached(tmp_path).record_count == 1
    assert PantherProvider().load_cached(tmp_path).record_count == 1


def test_reactome_analysis_result_list_and_empty_panther() -> None:
    records = ReactomeAnalysisProvider().parse_raw(
        [
            {
                "pathway_id": "R",
                "pathway_name": "Path",
                "entities": {"found": ["A"]},
                "observed_count": 1,
                "expected_count": 1,
                "adjusted_p_value": 0.5,
            }
        ],
        snapshot_id="snap",
        organism="human",
    )
    assert records[0].term_id == "R"
    assert (
        PantherProvider().parse_raw({"results": {"result": {}}}, snapshot_id="s", organism="h")
        == []
    )
