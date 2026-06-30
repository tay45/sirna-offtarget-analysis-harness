from __future__ import annotations

from sirna_offtarget.execution.stages import build_stages


def test_data_and_completion_dependencies_are_separate() -> None:
    stages = build_stages()
    assert stages["transcript_targetability"].data_dependencies() == ("isoform_uncertainty",)
    assert "sequence_analysis" in stages["transcript_targetability"].completion_dependencies()
