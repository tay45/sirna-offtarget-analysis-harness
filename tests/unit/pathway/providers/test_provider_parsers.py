from __future__ import annotations

from sirna_offtarget.pathway.providers.omnipath import OmniPathProvider
from sirna_offtarget.pathway.providers.panther import PantherProvider
from sirna_offtarget.pathway.providers.reactome_analysis import ReactomeAnalysisProvider
from sirna_offtarget.pathway.providers.reactome_content import ReactomeContentProvider
from sirna_offtarget.pathway.providers.reactome_fi import ReactomeFIProvider
from sirna_offtarget.pathway.providers.signor import SignorProvider


def test_omnipath_preserves_stimulation_inhibition_conflict() -> None:
    records = OmniPathProvider().parse_raw(
        [
            {
                "source": "A",
                "target": "B",
                "is_stimulation": True,
                "is_inhibition": True,
                "sources": "SIGNOR",
                "references": "PMID1",
            }
        ],
        "snap",
        "human",
    )
    assert records[0].sign == "conflicting"
    assert records[0].references == ("PMID1",)


def test_signor_parser_preserves_causal_effect() -> None:
    record = SignorProvider().parse_raw(
        [{"source": "A", "target": "B", "effect": "inhibition", "PMID": "PMID2"}],
        "snap",
        "human",
    )[0]
    assert record.sign == "negative"
    assert record.causal_eligible is True


def test_reactome_fi_forces_unsigned_non_causal() -> None:
    record = ReactomeFIProvider().parse_raw(
        [{"source": "A", "target": "B", "sign": "positive"}],
        "snap",
        "human",
    )[0]
    assert record.sign == "unsigned"
    assert record.functional_only is True
    assert record.causal_eligible is False


def test_reactome_content_membership_is_not_causal() -> None:
    record = ReactomeContentProvider().parse_raw(
        [{"source": "A", "target": "B", "pathway_id": "R-HSA-1"}],
        "snap",
        "human",
    )[0]
    assert record.sign == "unsigned"
    assert record.causal_eligible is False


def test_reactome_and_panther_enrichment_records() -> None:
    reactome = ReactomeAnalysisProvider().parse_raw(
        {
            "pathways": [
                {
                    "stId": "R-HSA-1",
                    "name": "Path",
                    "entities": {"found": ["A"], "fdr": 0.1, "pValue": 0.05},
                    "foundEntities": 1,
                    "expected_count": 0.5,
                }
            ]
        },
        snapshot_id="snap",
        organism="human",
    )[0]
    panther = PantherProvider().parse_raw(
        [
            {
                "term_id": "P1",
                "term_name": "Term",
                "matched_genes": "A;B",
                "number_in_list": 2,
                "expected": 1,
                "fold_enrichment": 2,
                "pValue": 0.01,
                "fdr": 0.02,
                "dataset": "REACTOME_PATHWAY",
            }
        ],
        snapshot_id="snap",
        organism="human",
    )[0]
    assert reactome.adjusted_p_value == 0.1
    assert panther.matched_genes == ("A", "B")
    assert panther.warnings
