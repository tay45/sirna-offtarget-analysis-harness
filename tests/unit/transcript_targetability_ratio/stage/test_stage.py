import pytest

from sirna_offtarget.contracts.registry import STAGE_CONTRACTS
from sirna_offtarget.execution.dag import STAGE_NODES, STAGE_ORDER, downstream_of
from sirna_offtarget.execution.exceptions import InvalidStageError
from sirna_offtarget.execution.stages import build_stages


def test_ratio_stage_is_registered_after_transcript_targetability() -> None:
    assert "transcript_targetability_ratio" in build_stages()
    assert "transcript_targetability_ratio" in STAGE_CONTRACTS
    assert STAGE_ORDER.index("transcript_targetability_ratio") > STAGE_ORDER.index(
        "transcript_targetability"
    )
    assert STAGE_NODES["transcript_targetability_ratio"].data_dependencies == (
        "isoform_uncertainty",
        "transcript_targetability",
    )


def test_pathway_changes_are_not_upstream_of_ratio_stage() -> None:
    with pytest.raises(InvalidStageError):
        downstream_of("pathway_enrichment")
