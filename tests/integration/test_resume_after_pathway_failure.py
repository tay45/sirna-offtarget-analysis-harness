from __future__ import annotations

from pathlib import Path

import yaml

from sirna_offtarget.execution.api import run_staged_analysis, stage_attempts, status_run
from sirna_offtarget.execution.dag import stage_index


def test_resume_after_pathway_failure_preserves_attempt_and_reuses_upstream(
    tmp_path: Path,
) -> None:
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

    out = tmp_path / "run"
    try:
        run_staged_analysis(config_path=config_path, output_dir=out)
    except RuntimeError as exc:
        assert "controlled injected failure" in str(exc)
    else:
        raise AssertionError("expected controlled pathway failure")

    failed_attempts = stage_attempts(out, "expression_analysis")
    assert failed_attempts[-1]["status"] == "failed"
    assert (
        out
        / "stages"
        / f"{stage_index('expression_analysis'):02d}_expression_analysis"
        / "attempts"
        / "attempt_001"
        / "failure_report.json"
    ).exists()

    rows = run_staged_analysis(config_path=config_path, output_dir=out)
    assert any(row["stage"] == "sequence_analysis" and row["action"] == "reuse" for row in rows)
    assert any(row["stage"] == "expression_analysis" and row["action"] == "run" for row in rows)
    attempts = stage_attempts(out, "expression_analysis")
    assert [attempt["status"] for attempt in attempts] == ["failed", "completed_with_warnings"]
    assert status_run(out)[-1]["status"] == "completed"
