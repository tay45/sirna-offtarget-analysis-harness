from pathlib import Path

from tests.portfolio.integrity_helpers import EXPECTED_RATIO_STAGES, run_portfolio


def test_public_example_emits_only_current_scope(tmp_path: Path) -> None:
    out = tmp_path / "run"
    assert run_portfolio(out, until_stage="transcript_targetability_ratio") == EXPECTED_RATIO_STAGES
    stage_names = {path.name.split("_", 1)[1] for path in (out / "stages").iterdir()}
    assert stage_names == set(EXPECTED_RATIO_STAGES)
