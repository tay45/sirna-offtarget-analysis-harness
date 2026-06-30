from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

from sirna_offtarget.config import HarnessConfig, load_config
from sirna_offtarget.execution.attempts import list_attempts
from sirna_offtarget.execution.hashing import read_yaml
from sirna_offtarget.execution.invalidation import (
    cancel_request,
    create_request,
    load_requests,
)
from sirna_offtarget.execution.runner import plan, run, status, verify
from sirna_offtarget.execution.state import RunContext


def _resolved_dict(config: HarnessConfig, base_dir: Path) -> dict[str, Any]:
    data = config.model_dump(mode="json")
    data["_base_dir"] = str(base_dir.resolve())
    data.setdefault("schema_version", "1")
    data.setdefault(
        "execution",
        {
            "resume": True,
            "fail_fast": True,
            "preserve_failed_attempts": True,
            "verify_output_checksums": True,
            "verify_dependency_hashes": True,
            "atomic_stage_commit": True,
            "max_stage_attempts": 3,
            "lock_timeout_seconds": 300,
            "stale_lock_timeout_seconds": 3600,
        },
    )
    return data


def build_context(
    *,
    config_path: Path,
    output_dir: Path | None,
    run_id: str | None,
    invocation: tuple[str, ...] | None = None,
    offline: bool = False,
) -> RunContext:
    config = load_config(config_path)
    if output_dir is not None:
        config.outputs.directory = output_dir
    original = read_yaml(config_path)
    resolved = _resolved_dict(config, config_path.parent)
    rid = run_id or "latest"
    return RunContext(
        config=config,
        original_config=original,
        resolved_config=resolved,
        config_path=config_path,
        run_dir=config.outputs.directory,
        run_id=rid,
        invocation=invocation or tuple(sys.argv),
        offline=offline,
    )


def run_staged_analysis(
    *,
    config_path: Path,
    output_dir: Path | None = None,
    resume: bool = True,
    from_stage: str | None = None,
    until_stage: str | None = None,
    force_stage: str | None = None,
    force_downstream: str | None = None,
    offline: bool = False,
    dry_run: bool = False,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    if not resume:
        if output_dir is not None and output_dir.exists():
            raise RuntimeError(
                "--no-resume cannot target an existing run directory without a destructive override"
            )
        if output_dir is None:
            base_config = load_config(config_path)
            suffix = run_id or uuid.uuid4().hex[:8]
            output_dir = (
                base_config.outputs.directory.parent
                / f"{base_config.outputs.directory.name}_{suffix}"
            )
    context = build_context(
        config_path=config_path,
        output_dir=output_dir,
        run_id=run_id,
        offline=offline,
    )
    _ = resume
    return run(
        context,
        from_stage=from_stage,
        until_stage=until_stage,
        force_stage=force_stage,
        force_downstream=force_downstream,
        dry_run=dry_run,
    )


def plan_run(
    *,
    config_path: Path,
    output_dir: Path | None = None,
    resume: bool = True,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    _ = resume
    context = build_context(config_path=config_path, output_dir=output_dir, run_id=run_id)
    context.run_dir.mkdir(parents=True, exist_ok=True)
    return plan(context)


def resume_run(run_dir: Path) -> list[dict[str, Any]]:
    resolved = read_yaml(run_dir / "run_config.resolved.yaml")
    config = HarnessConfig.model_validate(resolved)
    context = RunContext(
        config=config,
        original_config=read_yaml(run_dir / "run_config.original.yaml"),
        resolved_config=resolved,
        config_path=run_dir / "run_config.original.yaml",
        run_dir=run_dir,
        run_id=run_dir.name,
        invocation=("sirna-offtarget", "resume", "--run-dir", str(run_dir)),
    )
    return run(context)


def status_run(run_dir: Path) -> list[dict[str, Any]]:
    return status(run_dir)


def stage_attempts(run_dir: Path, stage: str) -> list[dict[str, Any]]:
    return list_attempts(run_dir, stage)


def verify_run(run_dir: Path) -> list[str]:
    return verify(run_dir)


def invalidate_run(
    run_dir: Path, stage: str, downstream: bool, reason: str = "manual invalidation"
) -> dict[str, Any]:
    return create_request(run_dir, stage, downstream, reason=reason)


def list_invalidations(run_dir: Path) -> list[dict[str, Any]]:
    return load_requests(run_dir)


def cancel_invalidation(run_dir: Path, request_id: str) -> dict[str, Any]:
    return cancel_request(run_dir, request_id)
