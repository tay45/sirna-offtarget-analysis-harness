from __future__ import annotations

from pathlib import Path

import pytest

from sirna_offtarget.execution.api import run_staged_analysis


def test_no_resume_refuses_existing_run_directory(tmp_path: Path) -> None:
    out = tmp_path / "run"
    run_staged_analysis(config_path=Path("examples/synthetic/config.yaml"), output_dir=out)
    with pytest.raises(RuntimeError, match="--no-resume"):
        run_staged_analysis(
            config_path=Path("examples/synthetic/config.yaml"),
            output_dir=out,
            resume=False,
        )
