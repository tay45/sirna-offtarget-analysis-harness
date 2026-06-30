from __future__ import annotations

from pathlib import Path

from sirna_offtarget.contracts.stage_results import SequenceAnalysisResultV1
from sirna_offtarget.execution.api import build_context, run_staged_analysis
from sirna_offtarget.execution.contracts import load_dependency_contract


def test_dependency_loader_consumes_only_committed_contract(tmp_path: Path) -> None:
    out = tmp_path / "run"
    config = Path("examples/synthetic/config.yaml")
    run_staged_analysis(config_path=config, output_dir=out, until_stage="sequence_analysis")
    context = build_context(config_path=config, output_dir=out, run_id="test")
    contract = load_dependency_contract(
        context,
        dependency_stage="sequence_analysis",
        expected_contract=SequenceAnalysisResultV1,
    )
    assert contract.stage_name == "sequence_analysis"
