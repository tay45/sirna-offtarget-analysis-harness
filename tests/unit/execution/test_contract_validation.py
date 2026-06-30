from __future__ import annotations

from pathlib import Path

from sirna_offtarget.contracts.stage_results import SequenceAnalysisResultV1
from sirna_offtarget.contracts.validation import validate_contract_file
from sirna_offtarget.execution.api import run_staged_analysis


def test_committed_stage_contract_validates(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_staged_analysis(
        config_path=Path("examples/synthetic/config.yaml"),
        output_dir=out,
        until_stage="sequence_analysis",
    )
    contract = validate_contract_file(
        out
        / "stages"
        / "04_sequence_analysis"
        / "attempts"
        / "attempt_001"
        / "committed"
        / "outputs"
        / "stage_result.json",
        SequenceAnalysisResultV1,
    )
    assert contract.payload.total_sites > 0
