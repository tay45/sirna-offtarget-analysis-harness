from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

import sirna_offtarget.cli as cli


def test_cli_run_deterministic_seed_uses_in_memory_analysis(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("project: {}\n")

    class Project:
        random_seed = 0

    class Config:
        project = Project()

    class State:
        sequence_hits = {"A": object()}
        expression_results = {"A": object(), "B": object()}
        isoform_results = {"A": object()}
        pathway_results = {"B": object()}

    monkeypatch.setattr(cli, "_load", lambda _path: Config())
    monkeypatch.setattr(cli, "execute_workflow", lambda _config: State())
    result = CliRunner().invoke(
        cli.main,
        ["run", "--config", str(config_path), "--deterministic-seed", "7"],
    )
    assert result.exit_code == 0
    assert "expression_gene_count" in result.output


def test_cli_staged_run_plan_resume_status_attempts_and_report(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("project: {}\n")
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    monkeypatch.setattr(cli, "run_staged_analysis", lambda **_kwargs: [{"stage": "validate"}])
    monkeypatch.setattr(cli, "plan_run", lambda **_kwargs: [{"stage": "validate"}])
    monkeypatch.setattr(cli, "resume_run", lambda _run_dir: [{"stage": "resume"}])
    monkeypatch.setattr(cli, "status_run", lambda _run_dir: [{"stage": "status"}])
    monkeypatch.setattr(cli, "stage_attempts", lambda _run_dir, _stage: [{"attempt": "001"}])

    runner = CliRunner()
    assert (
        runner.invoke(cli.main, ["run", "--config", str(config_path), "--dry-run"]).exit_code == 0
    )
    assert runner.invoke(cli.main, ["plan", "--config", str(config_path)]).exit_code == 0
    assert runner.invoke(cli.main, ["resume", "--run-dir", str(run_dir)]).exit_code == 0
    assert runner.invoke(cli.main, ["status", "--run-dir", str(run_dir)]).exit_code == 0
    assert (
        runner.invoke(
            cli.main,
            ["attempts", "--run-dir", str(run_dir), "--stage", "expression_analysis"],
        ).exit_code
        == 0
    )
    assert runner.invoke(cli.main, ["report", "--run-dir", str(run_dir)]).exit_code == 0
    assert (
        runner.invoke(
            cli.main, ["report", "--config", str(config_path), "--output-dir", str(run_dir)]
        ).exit_code
        != 0
    )
    assert runner.invoke(cli.main, ["report"]).exit_code != 0


def test_cli_invalidate_verify_and_validate_results_branches(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("project: {}\n")
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    class Config:
        class Outputs:
            directory = run_dir

        outputs = Outputs()

    monkeypatch.setattr(cli, "list_invalidations", lambda _run_dir: [{"id": "one"}])
    monkeypatch.setattr(cli, "cancel_invalidation", lambda _run_dir, _request: {"cancelled": True})
    monkeypatch.setattr(cli, "invalidate_run", lambda *_args: {"invalidated": True})
    monkeypatch.setattr(cli, "verify_run", lambda _run_dir: [])
    monkeypatch.setattr(cli, "_load", lambda _path: Config())
    monkeypatch.setattr(cli, "validate_output_directory", lambda _path: [])

    runner = CliRunner()
    assert (
        runner.invoke(cli.main, ["invalidate", "--run-dir", str(run_dir), "--list"]).exit_code == 0
    )
    assert (
        runner.invoke(
            cli.main,
            ["invalidate", "--run-dir", str(run_dir), "--cancel", "one"],
        ).exit_code
        == 0
    )
    assert runner.invoke(cli.main, ["invalidate", "--run-dir", str(run_dir)]).exit_code != 0
    assert (
        runner.invoke(
            cli.main,
            ["invalidate", "--run-dir", str(run_dir), "--stage", "expression_analysis"],
        ).exit_code
        == 0
    )
    assert runner.invoke(cli.main, ["verify", "--run-dir", str(run_dir)]).exit_code == 0
    monkeypatch.setattr(cli, "verify_run", lambda _run_dir: ["bad checksum"])
    assert runner.invoke(cli.main, ["verify", "--run-dir", str(run_dir)]).exit_code != 0
    assert (
        runner.invoke(cli.main, ["validate-results", "--config", str(config_path)]).exit_code == 0
    )
    monkeypatch.setattr(cli, "validate_output_directory", lambda _path: ["missing"])
    assert (
        runner.invoke(cli.main, ["validate-results", "--config", str(config_path)]).exit_code != 0
    )
