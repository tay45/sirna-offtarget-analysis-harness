from __future__ import annotations

import json
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from sirna_offtarget.contracts.artifacts import build_artifact_reference
from sirna_offtarget.contracts.base import make_contract
from sirna_offtarget.contracts.registry import STAGE_CONTRACTS
from sirna_offtarget.contracts.validation import validate_contract_file
from sirna_offtarget.execution.atomic import write_current_pointer
from sirna_offtarget.execution.checkpoints import current_manifest_path, next_attempt_number
from sirna_offtarget.execution.config_history import write_config_revision
from sirna_offtarget.execution.dag import (
    STAGE_NODES,
    STAGE_ORDER,
    execution_plan,
    stage_index,
    topological_sort,
)
from sirna_offtarget.execution.exceptions import ExecutionError
from sirna_offtarget.execution.failure import classify_failure
from sirna_offtarget.execution.hashing import (
    dump_json,
    hash_data,
    load_json,
    sha256_file,
    write_yaml,
)
from sirna_offtarget.execution.locking import FileLock
from sirna_offtarget.execution.manifests import (
    attach_artifacts,
    build_base_manifest,
    manifest_hash,
    utc_now,
    write_stage_manifest,
)
from sirna_offtarget.execution.stages import (
    PipelineStage,
    build_stages,
    relevant_config_hash,
    stage_fingerprint,
    write_stage_report,
)
from sirna_offtarget.execution.state import ReuseDecision, RunContext
from sirna_offtarget.expected_direct_effect.artifacts import (
    verify_expected_direct_effect_outputs,
)
from sirna_offtarget.isoform_uncertainty.artifacts import (
    verify_committed_isoform_uncertainty_result,
    verify_isoform_uncertainty_final_outputs,
)
from sirna_offtarget.transcript_targetability.artifacts import (
    verify_transcript_targetability_outputs,
)
from sirna_offtarget.transcript_targetability_ratio.artifacts import (
    verify_transcript_targetability_ratio_outputs,
)


def stage_dir(run_dir: Path, name: str) -> Path:
    return run_dir / "stages" / f"{stage_index(name):02d}_{name}"


def _dependency_data(
    context: RunContext, stage: PipelineStage, *, dependency_type: str = "all"
) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if dependency_type == "data":
        dependencies = stage.data_dependencies()
    elif dependency_type == "completion":
        dependencies = stage.completion_dependencies()
    else:
        dependencies = stage.dependencies()
    for dependency in dependencies:
        manifest = current_manifest_path(stage_dir(context.run_dir, dependency))
        if manifest is None:
            data[dependency] = {"status": "missing"}
            continue
        loaded = load_json(manifest)
        data[dependency] = {
            "status": loaded.get("status"),
            "manifest_hash": manifest_hash(manifest),
            "output_sha256_checksums": loaded.get("output_sha256_checksums", {}),
        }
    return data


def _completed_manifest_valid(manifest_path: Path) -> tuple[bool, str]:
    manifest = load_json(manifest_path)
    if manifest.get("status") not in {"completed", "completed_with_warnings", "skipped_reused"}:
        return False, f"current attempt status is {manifest.get('status')}"
    for record in manifest.get("output_artifacts", []):
        path = manifest_path.parent / record["path"]
        if not path.exists():
            return False, f"missing output {record['path']}"
        if record.get("sha256"):
            from sirna_offtarget.execution.hashing import sha256_file

            if sha256_file(path) != record["sha256"]:
                return False, f"checksum mismatch for {record['path']}"
    contract_path = manifest_path.parent / "committed" / "outputs" / "stage_result.json"
    if not contract_path.exists():
        return False, "missing committed contract"
    if (
        manifest.get("contract_sha256")
        and sha256_file(contract_path) != manifest["contract_sha256"]
    ):
        return False, "contract checksum mismatch"
    if manifest.get("stage_name") == "isoform_uncertainty":
        verification = verify_committed_isoform_uncertainty_result(manifest_path.parent)
        if not verification.passed:
            return False, "isoform uncertainty committed verification failed: " + ", ".join(
                verification.errors
            )
    if manifest.get("stage_name") == "expected_direct_effect":
        direct_effect_verification = verify_expected_direct_effect_outputs(
            manifest_path.parent / "committed" / "outputs"
        )
        if not direct_effect_verification["passed"]:
            return False, "expected direct-effect committed verification failed: " + ", ".join(
                direct_effect_verification["errors"]
            )
    return True, "completed attempt and output checksums are valid"


def plan_stage(
    context: RunContext,
    stage: PipelineStage,
    *,
    forced: set[str],
    invalidated: set[str],
) -> ReuseDecision:
    dependency_data = _dependency_data(context, stage)
    blocked = [
        name
        for name, data in dependency_data.items()
        if data.get("status") not in {"completed", "completed_with_warnings", "skipped_reused"}
    ]
    current = stage_fingerprint(
        stage, context, _dependency_data(context, stage, dependency_type="data")
    )
    manifest_path = current_manifest_path(stage_dir(context.run_dir, stage.name))
    previous = None
    if manifest_path:
        previous_manifest = load_json(manifest_path)
        previous = str(previous_manifest.get("stage_fingerprint"))
    if stage.name in forced:
        return ReuseDecision("forced", "stage explicitly forced", current, previous, "ok")
    if blocked:
        return ReuseDecision(
            "blocked",
            f"waiting for valid dependencies: {', '.join(blocked)}",
            current,
            previous,
            "blocked",
        )
    if stage.name in invalidated:
        return ReuseDecision(
            "invalidate",
            "stage is downstream of a forced or changed stage",
            current,
            previous,
            "ok",
        )
    if manifest_path is None:
        return ReuseDecision("run", "no previous completed attempt", current, previous, "ok")
    valid, reason = _completed_manifest_valid(manifest_path)
    if not valid:
        return ReuseDecision("run", reason, current, previous, "ok")
    if previous != current:
        return ReuseDecision("invalidate", "fingerprint changed", current, previous, "ok")
    return ReuseDecision("reuse", reason, current, previous, "ok")


def write_run_files(context: RunContext) -> None:
    context.run_dir.mkdir(parents=True, exist_ok=True)
    (context.run_dir / "logs").mkdir(exist_ok=True)
    original_path = context.run_dir / "run_config.original.yaml"
    if not original_path.exists():
        write_yaml(original_path, context.original_config)
    write_yaml(context.run_dir / "run_config.resolved.yaml", context.resolved_config)
    revision = write_config_revision(
        run_dir=context.run_dir,
        original=context.original_config,
        resolved=context.resolved_config,
        reason="run invocation",
        cli_overrides={},
    )
    manifest_path = context.run_dir / "run_manifest.json"
    existing_created_at = None
    if manifest_path.exists():
        existing_created_at = load_json(manifest_path).get("created_at")
    dump_json(
        manifest_path,
        {
            "run_id": context.run_id,
            "stage_dag_version": "1",
            "stages": topological_sort(),
            "created_at": existing_created_at or utc_now(),
            "updated_at": utc_now(),
            "active_config_revision": revision,
        },
    )


def execute_stage(
    context: RunContext,
    stage: PipelineStage,
    decision: ReuseDecision,
) -> dict[str, Any]:
    sdir = stage_dir(context.run_dir, stage.name)
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / "attempts").mkdir(exist_ok=True)
    if decision.action == "reuse":
        manifest_path = current_manifest_path(sdir)
        if manifest_path is None:
            raise RuntimeError(f"cannot reuse stage {stage.name}: current manifest is missing")
        manifest = load_json(manifest_path)
        event = {
            "timestamp": utc_now(),
            "reused_attempt": manifest.get("attempt_number"),
            "fingerprint": decision.current_fingerprint,
            "verification_result": decision.explanation,
            "dependency_status": decision.dependency_status,
            "config_revision": load_json(context.run_dir / "run_manifest.json").get(
                "active_config_revision"
            ),
            "reason": decision.explanation,
        }
        with (sdir / "reuse_events.jsonl").open("a") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        return {
            "stage": stage.name,
            "action": "reuse",
            "reused_attempt": manifest.get("attempt_number"),
        }

    attempt_number = next_attempt_number(sdir)
    max_attempts = int(context.resolved_config.get("execution", {}).get("max_stage_attempts", 3))
    if attempt_number > max_attempts:
        raise ExecutionError(
            f"{stage.name} exhausted max_stage_attempts={max_attempts}; "
            "inspect attempts and rerun with a fresh run directory or adjusted policy"
        )
    attempt_dir = sdir / "attempts" / f"attempt_{attempt_number:03d}"
    attempt_dir.mkdir(parents=True)
    for child in ("logs", "inputs", "working", "temporary", "partial_outputs"):
        (attempt_dir / child).mkdir(exist_ok=True)
    (attempt_dir / "working" / "outputs").mkdir(exist_ok=True)
    (attempt_dir / "logs" / "stage.log").write_text("")
    (attempt_dir / "logs" / "events.jsonl").write_text("")
    started = utc_now()
    started_dt = datetime.fromisoformat(started)
    dependency_data = _dependency_data(context, stage)
    data_dependency_data = _dependency_data(context, stage, dependency_type="data")
    completion_dependency_data = _dependency_data(context, stage, dependency_type="completion")
    manifest = build_base_manifest(
        run_id=context.run_id,
        stage_name=stage.name,
        stage_version=stage.version,
        attempt_number=attempt_number,
        status="running",
        started_at=started,
        original_config_hash=hash_data(context.original_config),
        resolved_config_hash=hash_data(context.resolved_config),
        relevant_config_hash=relevant_config_hash(context, stage.relevant_config_paths()),
        stage_fingerprint=decision.current_fingerprint,
        dependencies=list(stage.dependencies()),
        command_invocation=context.invocation,
        offline=context.offline,
    )
    manifest["dependency_manifest_hashes"] = {
        name: data.get("manifest_hash") for name, data in dependency_data.items()
    }
    manifest["dependency_output_hashes"] = {
        name: data.get("output_sha256_checksums") for name, data in dependency_data.items()
    }
    manifest["data_dependencies"] = list(stage.data_dependencies())
    manifest["completion_dependencies"] = list(stage.completion_dependencies())
    manifest["data_dependency_manifest_hashes"] = {
        name: data.get("manifest_hash") for name, data in data_dependency_data.items()
    }
    manifest["completion_dependency_manifest_hashes"] = {
        name: data.get("manifest_hash") for name, data in completion_dependency_data.items()
    }
    write_stage_manifest(attempt_dir, manifest)
    dump_json(attempt_dir / "status.json", {"status": "running", "started_at": started})
    write_yaml(
        attempt_dir / "resolved_stage_config.yaml",
        {path: context.resolved_config.get(path) for path in stage.relevant_config_paths()},
    )
    dump_json(
        attempt_dir / "input_manifest.json",
        {"inputs": [str(p) for p in stage.required_inputs(context)]},
    )
    dump_json(attempt_dir / "dependency_manifest.json", dependency_data)
    (attempt_dir / "command.txt").write_text(" ".join(context.invocation) + "\n")
    dump_json(attempt_dir / "environment.json", {"offline": context.offline})
    try:
        injected_failure_stage = context.resolved_config.get("execution", {}).get(
            "inject_failure_stage"
        )
        previous_failures = [
            path
            for path in (sdir / "attempts").glob("attempt_*/stage_manifest.json")
            if load_json(path).get("status") == "failed"
        ]
        if injected_failure_stage == stage.name and not previous_failures:
            raise RuntimeError(f"controlled injected failure for {stage.name}")
        injected_interrupt_stage = context.resolved_config.get("execution", {}).get(
            "inject_interrupt_stage"
        )
        previous_interrupts = [
            path
            for path in (sdir / "attempts").glob("attempt_*/stage_manifest.json")
            if load_json(path).get("status") == "interrupted"
        ]
        if injected_interrupt_stage == stage.name and not previous_interrupts:
            raise KeyboardInterrupt(f"controlled injected interrupt for {stage.name}")
        working_dir = attempt_dir / "working"
        result = stage.execute(context, working_dir)
        if stage.name == "isoform_uncertainty":
            verification = verify_isoform_uncertainty_final_outputs(working_dir / "outputs")
            if not verification.passed:
                raise RuntimeError(
                    "isoform uncertainty pre-commit verification failed: "
                    + ", ".join(verification.errors)
                )
        committed_dir = attempt_dir / "committed"
        committed_outputs = committed_dir / "outputs"
        if committed_outputs.exists():
            shutil.rmtree(committed_outputs)
        committed_dir.mkdir(exist_ok=True)
        (attempt_dir / "working" / "outputs").replace(committed_outputs)
        committed_artifacts = [
            committed_outputs / path.relative_to(working_dir / "outputs")
            for path in result.output_artifacts
        ]
        artifact_refs = [
            build_artifact_reference(
                run_dir=context.run_dir,
                path=path,
                logical_name=path.stem,
                media_type="application/json"
                if path.suffix == ".json"
                else "text/tab-separated-values"
                if path.suffix == ".tsv"
                else "application/octet-stream",
                created_by_stage=stage.name,
                created_by_attempt=attempt_number,
                schema_name=result.contract_name if path.name.endswith(".json") else None,
                schema_version=result.contract_version if path.name.endswith(".json") else None,
                description=f"{stage.name} output artifact",
            )
            for path in committed_artifacts
            if path.exists()
        ]
        contract_type = STAGE_CONTRACTS[stage.name]
        contract = make_contract(
            contract_type,
            stage_name=stage.name,
            stage_version=stage.version,
            run_id=context.run_id,
            attempt_number=attempt_number,
            payload=result.payload or result.metrics,
            artifacts=artifact_refs,
            warnings=result.warnings,
        )
        contract_path = committed_outputs / "stage_result.json"
        dump_json(contract_path, contract.model_dump(mode="json"))
        validate_contract_file(contract_path, contract_type)
        committed_artifacts.append(contract_path)
        reports = write_stage_report(
            attempt_dir,
            stage_name=stage.name,
            status="completed_with_warnings" if result.warnings else "completed",
            purpose=getattr(stage, "purpose", "Execute stage."),
            metrics=result.metrics,
            warnings=result.warnings,
            outputs=committed_artifacts,
            explanation=decision.explanation,
        )
        completed = utc_now()
        elapsed = (datetime.fromisoformat(completed) - started_dt).total_seconds()
        manifest["status"] = "completed_with_warnings" if result.warnings else "completed"
        manifest["completed_at"] = completed
        manifest["elapsed_seconds"] = elapsed
        manifest["warning_count"] = len(result.warnings)
        manifest["report_paths"] = reports
        manifest["consumed_dependencies"] = [
            {
                "dependency_stage": record.dependency_stage,
                "dependency_type": record.dependency_type,
                "contract_name": record.contract_name,
                "contract_version": record.contract_version,
                "contract_sha256": record.contract_sha256,
                "artifacts_consumed": record.artifacts_consumed,
                "payload_fields_consumed": record.payload_fields_consumed,
            }
            for record in context.dependency_consumption
        ]
        manifest["output_schema_versions"] = {result.contract_name: result.contract_version}
        manifest["contract_sha256"] = sha256_file(committed_outputs / "stage_result.json")
        attach_artifacts(
            manifest,
            inputs=stage.required_inputs(context),
            outputs=committed_artifacts,
            base=attempt_dir,
        )
        write_stage_manifest(attempt_dir, manifest)
        if stage.name == "isoform_uncertainty":
            verification = verify_committed_isoform_uncertainty_result(attempt_dir)
            if not verification.passed:
                raise RuntimeError(
                    "isoform uncertainty post-commit verification failed: "
                    + ", ".join(verification.errors)
                )
        if stage.name == "transcript_targetability":
            targetability_verification = verify_transcript_targetability_outputs(
                attempt_dir / "committed" / "outputs"
            )
            if not targetability_verification["passed"]:
                raise RuntimeError(
                    "transcript targetability post-commit verification failed: "
                    + ", ".join(targetability_verification["errors"])
                )
        if stage.name == "transcript_targetability_ratio":
            ratio_verification = verify_transcript_targetability_ratio_outputs(
                attempt_dir / "committed" / "outputs"
            )
            if not ratio_verification["passed"]:
                raise RuntimeError(
                    "transcript targetability ratio post-commit verification failed: "
                    + ", ".join(ratio_verification["errors"])
                )
        if stage.name == "expected_direct_effect":
            direct_effect_verification = verify_expected_direct_effect_outputs(
                attempt_dir / "committed" / "outputs"
            )
            if not direct_effect_verification["passed"]:
                raise RuntimeError(
                    "expected direct-effect post-commit verification failed: "
                    + ", ".join(direct_effect_verification["errors"])
                )
        dump_json(
            attempt_dir / "status.json", {"status": manifest["status"], "completed_at": completed}
        )
        write_current_pointer(sdir, attempt_number, attempt_dir)
        return {"stage": stage.name, "action": "run", "status": manifest["status"]}
    except BaseException as exc:
        completed = utc_now()
        elapsed = (datetime.fromisoformat(completed) - started_dt).total_seconds()
        classified = classify_failure(exc)
        category = str(classified["failure_category"])
        status = "interrupted" if category == "interrupted" else "failed"
        error = {
            "error_type": exc.__class__.__name__,
            "exception_class": exc.__class__.__name__,
            "message": str(exc),
            "exception_message": str(exc),
            "failure_category": category,
            "failed_operation": "stage.execute",
            "stage": stage.name,
            "attempt_number": attempt_number,
            "attempt": attempt_number,
            "timestamp": completed,
            "recoverable": classified["recoverable"],
            "suggested_action": f"Resume after correcting {category}",
            "suggested_recovery": f"sirna-offtarget resume --run-dir {context.run_dir}",
            "retry_command": f"sirna-offtarget resume --run-dir {context.run_dir}",
            "exception_chain": traceback.format_exception_only(exc.__class__, exc),
            "upstream_dependency_status": dependency_data,
            "relevant_provider_backend": None,
            "provider_backend": None,
            "exit_code": None,
        }
        dump_json(attempt_dir / "error.json", error)
        (attempt_dir / "traceback.txt").write_text(traceback.format_exc())
        working_outputs = attempt_dir / "working" / "outputs"
        if working_outputs.exists():
            destination = attempt_dir / "partial_outputs" / "outputs"
            if destination.exists():
                shutil.rmtree(destination)
            shutil.move(str(working_outputs), str(destination))
        reports = write_stage_report(
            attempt_dir,
            stage_name=stage.name,
            status=status,
            purpose=getattr(stage, "purpose", "Execute stage."),
            metrics={},
            warnings=[],
            outputs=[],
            explanation=str(exc),
        )
        shutil.copy2(attempt_dir / "report.html", attempt_dir / "failure_report.html")
        shutil.copy2(attempt_dir / "report.json", attempt_dir / "failure_report.json")
        manifest["status"] = status
        manifest["completed_at"] = completed
        manifest["elapsed_seconds"] = elapsed
        manifest["error_count"] = 1
        manifest["report_paths"] = reports
        write_stage_manifest(attempt_dir, manifest)
        dump_json(attempt_dir / "status.json", {"status": status, "completed_at": completed})
        raise


def plan(
    context: RunContext,
    *,
    force_stage: str | None = None,
    force_downstream: str | None = None,
) -> list[dict[str, Any]]:
    stages = build_stages()
    forced = {force_stage} if force_stage else set()
    invalidated: set[str] = set()
    from sirna_offtarget.execution.invalidation import pending_invalidated_stages

    invalidated.update(pending_invalidated_stages(context.run_dir))
    if force_stage:
        from sirna_offtarget.execution.invalidation import affected_stages

        invalidated.update(affected_stages(force_stage))
    if force_downstream:
        from sirna_offtarget.execution.dag import downstream_of

        invalidated.update(downstream_of(force_downstream))
    rows: list[dict[str, Any]] = []
    for name in topological_sort():
        stage = stages[name]
        decision = plan_stage(context, stage, forced=forced, invalidated=invalidated)
        rows.append(
            {
                "stage": name,
                "dependency_status": decision.dependency_status,
                "current_fingerprint": decision.current_fingerprint,
                "previous_fingerprint": decision.previous_fingerprint,
                "action": decision.action,
                "explanation": decision.explanation,
            }
        )
        if decision.action in {"run", "forced", "invalidate"}:
            from sirna_offtarget.execution.dag import downstream_of

            invalidated.update(downstream_of(name))
    return rows


def run(
    context: RunContext,
    *,
    from_stage: str | None = None,
    until_stage: str | None = None,
    force_stage: str | None = None,
    force_downstream: str | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    write_run_files(context)
    if until_stage is not None and until_stage not in STAGE_NODES:
        from sirna_offtarget.execution.exceptions import InvalidStageError

        raise InvalidStageError(until_stage)
    if from_stage is not None and from_stage not in STAGE_NODES:
        from sirna_offtarget.execution.exceptions import InvalidStageError

        raise InvalidStageError(from_stage)
    if until_stage:
        manifest_path = context.run_dir / "run_manifest.json"
        manifest = load_json(manifest_path)
        manifest["planned_terminal_stage"] = until_stage
        manifest["expected_completion_boundary"] = until_stage
        dump_json(manifest_path, manifest)
    if dry_run:
        return plan(context, force_stage=force_stage, force_downstream=force_downstream)
    execution_config = context.resolved_config.get("execution", {})
    lock_timeout = int(execution_config.get("lock_timeout_seconds", 300))
    stale_timeout = int(execution_config.get("stale_lock_timeout_seconds", 3600))
    with FileLock(context.run_dir / ".run.lock", lock_timeout, stale_timeout):
        stages = build_stages()
        ordered = execution_plan(until_stage=until_stage)
        if from_stage:
            ordered = ordered[ordered.index(from_stage) :]
        forced = {force_stage} if force_stage else set()
        invalidated: set[str] = set()
        from sirna_offtarget.execution.invalidation import pending_invalidated_stages

        invalidated.update(pending_invalidated_stages(context.run_dir))
        if force_stage:
            from sirna_offtarget.execution.invalidation import affected_stages

            invalidated.update(affected_stages(force_stage))
        if force_downstream:
            from sirna_offtarget.execution.dag import downstream_of

            invalidated.update(downstream_of(force_downstream))
        results: list[dict[str, Any]] = []
        for name in ordered:
            stage = stages[name]
            decision = plan_stage(context, stage, forced=forced, invalidated=invalidated)
            if decision.action == "blocked":
                results.append(
                    {"stage": name, "action": "blocked", "explanation": decision.explanation}
                )
                break
            results.append(execute_stage(context, stage, decision))
            write_run_status(context.run_dir, planned_terminal_stage=until_stage)
            if decision.action in {"run", "forced", "invalidate"}:
                from sirna_offtarget.execution.dag import downstream_of

                invalidated.update(downstream_of(name))
        write_dashboard(context)
        write_run_status(context.run_dir, planned_terminal_stage=until_stage)
        from sirna_offtarget.execution.invalidation import consume_pending_requests

        consume_pending_requests(context.run_dir)
        return results


def status(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in topological_sort():
        sdir = stage_dir(run_dir, name)
        current = current_manifest_path(sdir)
        if current:
            manifest = load_json(current)
            reuse_event_count = (
                sum(1 for _ in (sdir / "reuse_events.jsonl").open())
                if (sdir / "reuse_events.jsonl").exists()
                else 0
            )
            rows.append(
                {
                    "stage": name,
                    "status": manifest.get("status"),
                    "attempt_number": manifest.get("attempt_number"),
                    "execution_attempt_count": len(list((sdir / "attempts").glob("attempt_*"))),
                    "reuse_event_count": reuse_event_count,
                    "current_successful_attempt": str(current.parent.name),
                    "data_dependencies": STAGE_NODES[name].data_dependencies,
                    "completion_dependencies": STAGE_NODES[name].completion_dependencies,
                    "dependencies": STAGE_NODES[name].dependencies,
                    "consumed_dependencies": manifest.get("consumed_dependencies", []),
                    "elapsed_seconds": manifest.get("elapsed_seconds"),
                    "report_location": manifest.get("report_paths", {}),
                    "fingerprint_validity": "recorded",
                }
            )
        else:
            rows.append(
                {
                    "stage": name,
                    "status": "pending",
                    "attempt_number": None,
                    "execution_attempt_count": len(list((sdir / "attempts").glob("attempt_*")))
                    if (sdir / "attempts").exists()
                    else 0,
                    "reuse_event_count": sum(1 for _ in (sdir / "reuse_events.jsonl").open())
                    if (sdir / "reuse_events.jsonl").exists()
                    else 0,
                    "current_successful_attempt": None,
                    "data_dependencies": STAGE_NODES[name].data_dependencies,
                    "completion_dependencies": STAGE_NODES[name].completion_dependencies,
                    "dependencies": STAGE_NODES[name].dependencies,
                    "consumed_dependencies": [],
                    "elapsed_seconds": None,
                    "report_location": {},
                    "fingerprint_validity": "none",
                }
            )
    return rows


def write_run_status(run_dir: Path, *, planned_terminal_stage: str | None = None) -> dict[str, Any]:
    rows = status(run_dir)
    manifest = (
        load_json(run_dir / "run_manifest.json") if (run_dir / "run_manifest.json").exists() else {}
    )
    terminal = planned_terminal_stage or manifest.get("planned_terminal_stage") or STAGE_ORDER[-1]
    expected_stage_names = set(execution_plan(until_stage=terminal))
    expected_rows = [row for row in rows if row["stage"] in expected_stage_names]
    completed = [
        row for row in expected_rows if row["status"] in {"completed", "completed_with_warnings"}
    ]
    failed = next((row for row in rows if row["status"] == "failed"), None)
    interrupted = next((row for row in rows if row["status"] == "interrupted"), None)
    blocked = next((row for row in rows if row["status"] == "blocked"), None)
    pending_invalidations = 0
    invalidation_path = run_dir / "invalidation_requests.json"
    if invalidation_path.exists():
        from sirna_offtarget.execution.invalidation import load_requests

        invalidation_items = load_requests(run_dir)
        pending_invalidations = sum(
            1 for item in invalidation_items if item.get("status") == "pending"
        )
    if failed:
        run_status = "failed"
    elif interrupted:
        run_status = "interrupted"
    elif blocked:
        run_status = "blocked"
    elif len(completed) == len(expected_rows) and terminal != STAGE_ORDER[-1]:
        run_status = "partially_completed"
    elif len(completed) == len(STAGE_ORDER):
        run_status = (
            "completed_with_warnings"
            if any(row["status"] == "completed_with_warnings" for row in rows)
            else "completed"
        )
    else:
        run_status = "running"
    payload = {
        "run_id": manifest.get("run_id", run_dir.name),
        "run_status_schema_version": "1",
        "status": run_status,
        "active_config_revision": manifest.get("active_config_revision"),
        "planned_first_stage": STAGE_ORDER[0],
        "planned_terminal_stage": terminal,
        "current_stage": next((row["stage"] for row in rows if row["status"] == "running"), None),
        "current_attempt": next(
            (row["attempt_number"] for row in rows if row["status"] == "running"), None
        ),
        "last_successful_stage": completed[-1]["stage"] if completed else None,
        "failed_stage": failed["stage"] if failed else None,
        "interrupted_stage": interrupted["stage"] if interrupted else None,
        "blocked_stage": blocked["stage"] if blocked else None,
        "created_at": manifest.get("created_at"),
        "started_at": manifest.get("created_at"),
        "updated_at": utc_now(),
        "completed_at": utc_now()
        if run_status in {"completed", "completed_with_warnings", "partially_completed"}
        else None,
        "warning_count": sum(1 for row in rows if row["status"] == "completed_with_warnings"),
        "error_count": 1 if failed else 0,
        "completed_stage_count": len(completed),
        "reused_stage_count": sum(1 for row in rows if row["reuse_event_count"]),
        "failed_attempt_count": sum(
            1
            for stage_name in STAGE_ORDER
            for path in (
                run_dir / "stages" / f"{stage_index(stage_name):02d}_{stage_name}" / "attempts"
            ).glob("attempt_*/stage_manifest.json")
            if path.exists() and load_json(path).get("status") in {"failed", "interrupted"}
        ),
        "verification_status": "unknown",
        "verification_timestamp": None,
        "resume_recommendation": f"sirna-offtarget resume --run-dir {run_dir}"
        if failed or interrupted
        else None,
        "next_runnable_stage": next(
            (row["stage"] for row in expected_rows if row["status"] == "pending"), None
        ),
        "pending_invalidation_count": pending_invalidations,
        "stages": rows,
    }
    dump_json(run_dir / "run_status.json", payload)
    return payload


def verify(run_dir: Path) -> list[str]:
    errors: list[str] = []
    warnings: list[str] = []
    run_manifest = run_dir / "run_manifest.json"
    run_status_path = run_dir / "run_status.json"
    if not run_manifest.exists():
        errors.append("run: missing run_manifest.json")
    if not run_status_path.exists():
        warnings.append("run: missing run_status.json")
    manifest = load_json(run_manifest) if run_manifest.exists() else {}
    terminal = manifest.get("planned_terminal_stage") or STAGE_ORDER[-1]
    expected = set(execution_plan(until_stage=terminal))
    if manifest.get("active_config_revision"):
        revision_path = (
            run_dir
            / "config_history"
            / f"revision_{int(manifest['active_config_revision']):03d}.metadata.json"
        )
        if not revision_path.exists():
            errors.append("run: active config revision metadata is missing")
    rows = status(run_dir)
    for row in rows:
        if row["stage"] not in expected and terminal != STAGE_ORDER[-1]:
            continue
        current = current_manifest_path(stage_dir(run_dir, row["stage"]))
        if current is None:
            errors.append(f"{row['stage']}: missing current manifest")
            continue
        valid, reason = _completed_manifest_valid(current)
        if not valid:
            errors.append(f"{row['stage']}: {reason}")
        manifest_payload = load_json(current)
        attempt_dir = current.parent
        if (attempt_dir / "working" / "outputs").exists() and manifest_payload.get("status") in {
            "completed",
            "completed_with_warnings",
        }:
            errors.append(f"{row['stage']}: completed attempt has leftover working outputs")
        if not (attempt_dir / "committed" / "outputs").exists() and manifest_payload.get(
            "status"
        ) in {
            "completed",
            "completed_with_warnings",
        }:
            errors.append(f"{row['stage']}: completed attempt lacks committed outputs")
        if row["stage"] == "mechanistic_network" and manifest_payload.get("status") in {
            "completed",
            "completed_with_warnings",
        }:
            errors.extend(_verify_mechanistic_v2_payload(attempt_dir))
        declared_data = set(manifest_payload.get("data_dependencies", []))
        consumed_data = {
            item["dependency_stage"]
            for item in manifest_payload.get("consumed_dependencies", [])
            if item.get("dependency_type") == "data"
        }
        missing_consumption = declared_data - consumed_data
        if missing_consumption:
            missing = sorted(missing_consumption)
            errors.append(
                f"{row['stage']}: data dependencies missing consumption records: {missing}"
            )
        for item in manifest_payload.get("consumed_dependencies", []):
            declared_dependencies = set(manifest_payload.get("data_dependencies", [])) | set(
                manifest_payload.get("completion_dependencies", [])
            )
            if item.get("dependency_stage") not in declared_dependencies:
                errors.append(
                    f"{row['stage']}: consumed undeclared dependency {item.get('dependency_stage')}"
                )
        attempts_dir = stage_dir(run_dir, row["stage"]) / "attempts"
        seen_attempts: set[int] = set()
        for attempt_path in attempts_dir.glob("attempt_*"):
            stage_manifest = attempt_path / "stage_manifest.json"
            if not stage_manifest.exists():
                errors.append(f"{row['stage']}: orphan attempt {attempt_path.name}")
                continue
            attempt_manifest = load_json(stage_manifest)
            attempt_number = int(attempt_manifest.get("attempt_number", -1))
            if attempt_number in seen_attempts:
                errors.append(f"{row['stage']}: duplicate attempt number {attempt_number}")
            seen_attempts.add(attempt_number)
            if attempt_manifest.get("status") == "running":
                errors.append(f"{row['stage']}: stale running attempt {attempt_path.name}")
            if (
                attempt_manifest.get("status") in {"failed", "interrupted"}
                and not (attempt_path / "error.json").exists()
            ):
                errors.append(f"{row['stage']}: failed/interrupted attempt lacks error.json")
    report = {
        "status": "invalid" if errors else "ok",
        "errors": errors,
        "warnings": warnings,
        "checked_at": utc_now(),
    }
    dump_json(run_dir / "verification_report.json", report)
    (run_dir / "verification_report.html").write_text(
        "<html><body><h1>Verification report</h1>"
        f"<pre>{json.dumps(report, indent=2)}</pre></body></html>"
    )
    if run_status_path.exists():
        status_payload = load_json(run_status_path)
        status_payload["verification_status"] = report["status"]
        status_payload["verification_timestamp"] = report["checked_at"]
        dump_json(run_status_path, status_payload)
    return errors


def _verify_mechanistic_v2_payload(attempt_dir: Path) -> list[str]:
    path = attempt_dir / "committed" / "outputs" / "stage_result.payload.json"
    if not path.exists():
        return ["mechanistic_network: missing committed V2 payload"]
    wrapper = load_json(path)
    payload = wrapper.get("payload", wrapper)
    paths = [*payload.get("signed_paths", []), *payload.get("unsigned_context_paths", [])]
    search_results = payload.get("path_search_results", [])
    results_by_id = {item.get("search_result_id"): item for item in search_results}
    errors: list[str] = []
    if len(results_by_id) != len(search_results):
        errors.append("mechanistic_network: duplicate path search result IDs")
    for path_row in paths:
        path_id = path_row.get("path_id")
        result = results_by_id.get(path_row.get("search_result_id"))
        if result is None:
            errors.append(f"mechanistic_network: path {path_id} references missing search result")
            continue
        for key in ("source_entity_id", "target_entity_id", "graph_layer"):
            if path_row.get(key) != result.get(key):
                errors.append(f"mechanistic_network: path {path_id} search {key} mismatch")
        if path_id not in set(result.get("retained_path_ids", [])):
            errors.append(f"mechanistic_network: search result omits child path {path_id}")
        if "truncation_status" in path_row:
            errors.append(f"mechanistic_network: path {path_id} carries path-level truncation")
    path_ids = {path_row.get("path_id") for path_row in paths}
    for result in search_results:
        for child_id in result.get("retained_path_ids", []):
            if child_id not in path_ids:
                errors.append(
                    f"mechanistic_network: search result {result.get('search_result_id')} "
                    f"references missing child path {child_id}"
                )
    metrics = payload.get("metrics", {})
    expected_counts = {
        "signed_path_count": len(payload.get("signed_paths", [])),
        "unsigned_context_path_count": len(payload.get("unsigned_context_paths", [])),
        "total_canonical_path_count": len(paths),
        "path_search_result_count": len(search_results),
        "consensus_edge_count": len(payload.get("consensus_edges", [])),
        "provider_evidence_count": len(payload.get("provider_evidence", [])),
    }
    for key, expected in expected_counts.items():
        if metrics.get(key) != expected:
            errors.append(
                f"mechanistic_network: metric {key}={metrics.get(key)} expected {expected}"
            )
    return errors


def write_dashboard(context: RunContext) -> Path:
    rows = status(context.run_dir)
    html_rows = "\n".join(
        f"<tr><td>{row['stage']}</td><td>{row['status']}</td><td>{row['attempt_number']}</td>"
        f"<td>{row['elapsed_seconds']}</td><td>{row['report_location']}</td></tr>"
        for row in rows
    )
    path = context.run_dir / "run_dashboard.html"
    path.write_text(
        "<html><body><h1>Run dashboard</h1><table>"
        "<tr><th>Stage</th><th>Status</th><th>Attempt</th><th>Elapsed</th><th>Reports</th></tr>"
        f"{html_rows}</table></body></html>"
    )
    return path
