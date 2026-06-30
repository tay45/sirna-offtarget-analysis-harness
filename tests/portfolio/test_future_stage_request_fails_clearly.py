from pathlib import Path

import pytest

from sirna_offtarget.execution.api import run_staged_analysis
from sirna_offtarget.execution.exceptions import InvalidStageError
from tests.portfolio.integrity_helpers import CONFIG


def test_future_stage_request_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(InvalidStageError):
        run_staged_analysis(
            config_path=CONFIG,
            output_dir=tmp_path / "run",
            until_stage="expected_direct_effect",
        )
