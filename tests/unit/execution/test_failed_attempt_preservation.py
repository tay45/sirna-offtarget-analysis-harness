from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sirna_offtarget.execution.api import run_staged_analysis
from sirna_offtarget.execution.dag import stage_index


def test_failed_attempt_keeps_partial_outputs_out_of_committed(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    base = Path("examples/synthetic").resolve()
    raw = yaml.safe_load(Path("examples/synthetic/config.yaml").read_text())
    raw["sequence"]["transcript_fasta"] = str(base / raw["sequence"]["transcript_fasta"])
    raw["sequence"]["annotation_gtf"] = str(base / raw["sequence"]["annotation_gtf"])
    raw["expression"]["count_matrix"] = str(base / raw["expression"]["count_matrix"])
    raw["expression"]["sample_metadata"] = str(base / raw["expression"]["sample_metadata"])
    raw["pathway"]["network_file"] = str(base / raw["pathway"]["network_file"])
    raw["pathway"]["regulon_file"] = str(base / raw["pathway"]["regulon_file"])
    raw.setdefault("execution", {})["inject_failure_stage"] = "expression_analysis"
    config_path.write_text(yaml.safe_dump(raw, sort_keys=False))
    with pytest.raises(RuntimeError):
        run_staged_analysis(config_path=config_path, output_dir=tmp_path / "run")
    failed_attempt = (
        tmp_path
        / "run"
        / "stages"
        / f"{stage_index('expression_analysis'):02d}_expression_analysis"
        / "attempts"
        / "attempt_001"
    )
    assert (failed_attempt / "failure_report.json").exists()
    assert not (failed_attempt / "committed" / "outputs").exists()
