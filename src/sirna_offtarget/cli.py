from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast

import click

from sirna_offtarget import __version__
from sirna_offtarget.application import execute_workflow
from sirna_offtarget.config import HarnessConfig, load_config
from sirna_offtarget.execution import (
    cancel_invalidation,
    invalidate_run,
    list_invalidations,
    plan_run,
    resume_run,
    run_staged_analysis,
    stage_attempts,
    status_run,
    verify_run,
)
from sirna_offtarget.execution.hashing import dump_json
from sirna_offtarget.identifiers.snapshots import (
    build_identifier_snapshot_from_resources,
    inspect_identifier_cache,
    verify_identifier_cache,
    write_identifier_snapshot,
)
from sirna_offtarget.pathway.membership import (
    build_annotation_membership_snapshot,
    inspect_membership_cache,
    verify_membership_cache,
)
from sirna_offtarget.pathway.providers.cache import mark_verified, verify_cache
from sirna_offtarget.pathway.providers.fetch import fetch_pathway_cache
from sirna_offtarget.pathway.providers.manifest import read_manifest
from sirna_offtarget.validation import validate_output_directory


def _load(path: str) -> HarnessConfig:
    return load_config(Path(path))


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--log-level", default="INFO", show_default=True)
def main(log_level: str) -> None:
    """Mechanistic, validation-ready siRNA off-target analysis harness."""
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))


@main.command("validate-config")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def validate_config(config_path: str) -> None:
    """Validate a YAML analysis configuration."""
    config = _load(config_path)
    click.echo({"status": "ok", "project": config.project.name})


@main.command("map-sequence")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def map_sequence(config_path: str) -> None:
    """Run sequence complementarity mapping."""
    state = execute_workflow(_load(config_path))
    click.echo({"sequence_hit_count": len(state.sequence_hits)})


@main.command("analyze-expression")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def analyze_expression(config_path: str) -> None:
    """Run normalized expression analysis."""
    state = execute_workflow(_load(config_path))
    click.echo({"gene_count": len(state.expression_results)})


@main.command("analyze-isoforms")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
def analyze_isoforms(config_path: str) -> None:
    """Run isoform dilution and equal-prior analysis."""
    state = execute_workflow(_load(config_path))
    click.echo({"isoform_gene_count": len(state.isoform_results)})


@main.command("analyze-pathways")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option("--offline", is_flag=True, help="Require cached/offline pathway resources.")
def analyze_pathways(config_path: str, offline: bool) -> None:
    """Run directed pathway analysis."""
    state = execute_workflow(_load(config_path))
    click.echo({"pathway_gene_count": len(state.pathway_results), "offline": offline})


@main.group("pathway-db")
def pathway_db() -> None:
    """Manage explicit pathway database cache operations."""


@main.group("identifier-db")
def identifier_db() -> None:
    """Manage offline identifier resolution snapshots."""


@main.group("annotation-db")
def annotation_db() -> None:
    """Manage offline complete annotation membership snapshots."""


@annotation_db.command("build")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option("--provider", required=True)
@click.option(
    "--inputs",
    "input_paths",
    required=True,
    multiple=True,
    type=click.Path(path_type=Path, exists=True),
)
@click.option("--cache-dir", required=True, type=click.Path(path_type=Path))
@click.option("--annotation-source", default=None)
@click.option("--snapshot-id", default=None)
@click.option("--provider-release", default="user_supplied", show_default=True)
@click.option("--provider-version", default="user_supplied", show_default=True)
def annotation_db_build(
    config_path: str,
    provider: str,
    input_paths: tuple[Path, ...],
    cache_dir: Path,
    annotation_source: str | None,
    snapshot_id: str | None,
    provider_release: str,
    provider_version: str,
) -> None:
    """Build a verified complete annotation-membership snapshot from local files."""
    config = _load(config_path)
    snapshot = build_annotation_membership_snapshot(
        cache_dir=cache_dir,
        provider=provider,
        input_files=list(input_paths),
        organism=config.project.organism,
        annotation_source=annotation_source,
        snapshot_id=snapshot_id,
        provider_release=provider_release,
        provider_version=provider_version,
    )
    click.echo({"status": "ok", "snapshot_dir": str(snapshot)})


@annotation_db.command("inspect")
@click.option("--cache-dir", required=True, type=click.Path(path_type=Path))
def annotation_db_inspect(cache_dir: Path) -> None:
    """Inspect offline annotation membership snapshots."""
    click.echo({"cache_dir": str(cache_dir), "snapshots": inspect_membership_cache(cache_dir)})


@annotation_db.command("verify")
@click.option("--cache-dir", required=True, type=click.Path(path_type=Path))
def annotation_db_verify(cache_dir: Path) -> None:
    """Verify offline annotation membership snapshots."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    errors = verify_membership_cache(cache_dir)
    payload = {"cache_dir": str(cache_dir), "valid": not errors, "errors": errors}
    dump_json(cache_dir / "annotation_membership_verification.json", payload)
    if errors:
        raise click.ClickException("; ".join(errors))
    click.echo({"status": "ok", "cache_dir": str(cache_dir)})


@annotation_db.command("renormalize")
@click.option("--snapshot-id", required=True)
@click.option("--cache-dir", required=True, type=click.Path(path_type=Path))
def annotation_db_renormalize(snapshot_id: str, cache_dir: Path) -> None:
    """Validate an existing normalized snapshot without mutating raw resources."""
    matches = list(cache_dir.glob(f"*/{snapshot_id}/annotation_membership_manifest.json"))
    if not matches:
        raise click.ClickException(f"snapshot not found: {snapshot_id}")
    errors = verify_membership_cache(cache_dir)
    if errors:
        raise click.ClickException("; ".join(errors))
    click.echo({"status": "ok", "snapshot_id": snapshot_id, "renormalized": False})


@identifier_db.command("fetch")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option("--cache-dir", required=True, type=click.Path(path_type=Path))
def identifier_db_fetch(config_path: str, cache_dir: Path) -> None:
    """Create a versioned local identifier snapshot."""
    config = _load(config_path)
    snapshot = write_identifier_snapshot(cache_dir, config.project.organism)
    click.echo({"status": "ok", "snapshot_dir": str(snapshot)})


@identifier_db.command("build")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option(
    "--inputs",
    "input_paths",
    required=True,
    multiple=True,
    type=click.Path(path_type=Path, exists=True),
)
@click.option("--cache-dir", required=True, type=click.Path(path_type=Path))
@click.option("--snapshot-id", default=None)
def identifier_db_build(
    config_path: str, input_paths: tuple[Path, ...], cache_dir: Path, snapshot_id: str | None
) -> None:
    """Build a normalized offline identifier snapshot from local resource files."""
    config = _load(config_path)
    snapshot = build_identifier_snapshot_from_resources(
        cache_dir,
        config.project.organism,
        list(input_paths),
        snapshot_id=snapshot_id,
    )
    click.echo({"status": "ok", "snapshot_dir": str(snapshot)})


@identifier_db.command("inspect")
@click.option("--cache-dir", required=True, type=click.Path(path_type=Path))
def identifier_db_inspect(cache_dir: Path) -> None:
    """Inspect offline identifier snapshots."""
    click.echo({"cache_dir": str(cache_dir), "snapshots": inspect_identifier_cache(cache_dir)})


@identifier_db.command("verify")
@click.option("--cache-dir", required=True, type=click.Path(path_type=Path))
def identifier_db_verify(cache_dir: Path) -> None:
    """Verify offline identifier snapshots."""
    errors = verify_identifier_cache(cache_dir)
    payload = {"cache_dir": str(cache_dir), "valid": not errors, "errors": errors}
    dump_json(cache_dir / "identifier_cache_verification.json", payload)
    if errors:
        raise click.ClickException("; ".join(errors))
    click.echo({"status": "ok", "cache_dir": str(cache_dir)})


@pathway_db.command("fetch")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option("--providers", required=True)
@click.option("--cache-dir", required=True, type=click.Path(path_type=Path))
def pathway_db_fetch(config_path: str, providers: str, cache_dir: Path) -> None:
    """Explicitly fetch pathway resources into a cache directory."""
    config = _load(config_path)
    requested = [provider.strip() for provider in providers.split(",") if provider.strip()]
    manifest = fetch_pathway_cache(config, requested, cache_dir)
    click.echo(
        {
            "status": "ok",
            "cache_dir": str(cache_dir),
            "providers": [
                item["provider"] for item in cast(list[dict[str, Any]], manifest["providers"])
            ],
        }
    )


@pathway_db.command("inspect")
@click.option("--cache-dir", required=True, type=click.Path(path_type=Path))
def pathway_db_inspect(cache_dir: Path) -> None:
    """Inspect an offline pathway cache directory."""
    manifests = []
    for manifest_path in sorted(cache_dir.glob("*/*/provider_manifest.json")):
        manifest = read_manifest(manifest_path)
        manifests.append(
            {
                "provider": manifest.provider,
                "snapshot_id": manifest.snapshot_id,
                "organism": manifest.organism,
                "retrieval_timestamp": manifest.retrieval_timestamp,
                "database_version": manifest.database_version,
                "record_counts": manifest.record_counts,
                "status": manifest.completeness_status,
                "warnings": manifest.warning_count,
            }
        )
    click.echo({"cache_dir": str(cache_dir), "providers": manifests})


@pathway_db.command("verify")
@click.option("--cache-dir", required=True, type=click.Path(path_type=Path))
def pathway_db_verify(cache_dir: Path) -> None:
    """Verify an offline pathway cache directory."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    errors = verify_cache(cache_dir)
    payload = {"cache_dir": str(cache_dir), "valid": not errors, "errors": errors}
    dump_json(cache_dir / "pathway_cache_verification.json", payload)
    (cache_dir / "pathway_cache_verification.html").write_text(
        f"<html><body><h1>Pathway cache verification</h1><pre>{payload}</pre></body></html>"
    )
    if errors:
        raise click.ClickException("; ".join(errors))
    click.echo({"status": "ok", "cache_dir": str(cache_dir)})


@pathway_db.command("renormalize")
@click.option("--provider", required=True)
@click.option("--snapshot-id", required=True)
@click.option("--normalization-schema-version", required=True)
@click.option("--cache-dir", required=True, type=click.Path(path_type=Path))
def pathway_db_renormalize(
    provider: str,
    snapshot_id: str,
    normalization_schema_version: str,
    cache_dir: Path,
) -> None:
    """Create a new normalized snapshot from existing raw provider data."""
    source = cache_dir / provider.replace("-", "_") / snapshot_id
    if not source.exists():
        raise click.ClickException(f"snapshot not found: {source}")
    target = (
        cache_dir / provider.replace("-", "_") / f"{snapshot_id}_{normalization_schema_version}"
    )
    if target.exists():
        raise click.ClickException(f"target snapshot already exists: {target}")
    target.mkdir(parents=True)
    (target / "raw").mkdir()
    (target / "normalized").mkdir()
    for raw_file in (source / "raw").glob("*"):
        (target / "raw" / raw_file.name).write_bytes(raw_file.read_bytes())
    (target / "normalized" / "records.jsonl").write_text(
        (source / "normalized" / "records.jsonl").read_text()
    )
    manifest = read_manifest(source / "provider_manifest.json")
    manifest_payload = manifest.__dict__ | {
        "snapshot_id": target.name,
        "normalization_schema_version": normalization_schema_version,
        "request_parameters": manifest.request_parameters | {"renormalized_from": snapshot_id},
    }
    dump_json(target / "provider_manifest.json", manifest_payload)
    errors = verify_cache(cache_dir)
    if not errors:
        mark_verified(target)
    click.echo(
        {
            "status": "ok",
            "snapshot_id": target.name,
            "verified": not errors,
            "errors": errors,
        }
    )


@main.command("run")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option("--output-dir", type=click.Path(path_type=Path), default=None)
@click.option("--resume/--no-resume", default=True, show_default=True)
@click.option("--from-stage", default=None)
@click.option("--until-stage", default=None)
@click.option("--force-stage", default=None)
@click.option("--force-downstream", default=None)
@click.option("--offline", is_flag=True)
@click.option("--deterministic-seed", type=int, default=None)
@click.option("--dry-run", is_flag=True)
@click.option("--run-id", default=None)
def run(
    config_path: str,
    output_dir: Path | None,
    resume: bool,
    from_stage: str | None,
    until_stage: str | None,
    force_stage: str | None,
    force_downstream: str | None,
    offline: bool,
    deterministic_seed: int | None,
    dry_run: bool,
    run_id: str | None,
) -> None:
    """Execute the complete workflow and write outputs."""
    if deterministic_seed is not None:
        config = _load(config_path)
        config.project.random_seed = deterministic_seed
        state = execute_workflow(config)
        click.echo(
            {
                "status": "ok",
                "sequence_hit_count": len(state.sequence_hits),
                "expression_gene_count": len(state.expression_results),
                "isoform_gene_count": len(state.isoform_results),
                "pathway_gene_count": len(state.pathway_results),
            }
        )
        return
    rows = run_staged_analysis(
        config_path=Path(config_path),
        output_dir=output_dir,
        resume=resume,
        from_stage=from_stage,
        until_stage=until_stage,
        force_stage=force_stage,
        force_downstream=force_downstream,
        offline=offline,
        dry_run=dry_run,
        run_id=run_id,
    )
    click.echo({"status": "dry-run" if dry_run else "ok", "stages": rows})


@main.command("plan")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option("--output-dir", type=click.Path(path_type=Path), default=None)
@click.option("--resume/--no-resume", default=True, show_default=True)
@click.option("--run-id", default=None)
def plan(config_path: str, output_dir: Path | None, resume: bool, run_id: str | None) -> None:
    """Show dependency-aware run, reuse, invalidation, and blocked decisions."""
    click.echo(
        {
            "stages": plan_run(
                config_path=Path(config_path),
                output_dir=output_dir,
                resume=resume,
                run_id=run_id,
            )
        }
    )


@main.command("resume")
@click.option("--run-dir", required=True, type=click.Path(path_type=Path, exists=True))
def resume_command(run_dir: Path) -> None:
    """Resume a previously initialized staged run directory."""
    click.echo({"status": "ok", "stages": resume_run(run_dir)})


@main.command("status")
@click.option("--run-dir", required=True, type=click.Path(path_type=Path, exists=True))
def status_command(run_dir: Path) -> None:
    """Show stage status, attempts, dependencies, fingerprints, and reports."""
    click.echo({"stages": status_run(run_dir)})


@main.command("attempts")
@click.option("--run-dir", required=True, type=click.Path(path_type=Path, exists=True))
@click.option("--stage", required=True)
def attempts_command(run_dir: Path, stage: str) -> None:
    """List preserved attempts for a stage."""
    click.echo({"attempts": stage_attempts(run_dir, stage)})


@main.command("report")
@click.option("--run-dir", type=click.Path(path_type=Path, exists=True), default=None)
@click.option("--config", "config_path", type=click.Path(exists=True), default=None)
@click.option("--output-dir", type=click.Path(path_type=Path), default=None)
def report(run_dir: Path | None, config_path: str | None, output_dir: Path | None) -> None:
    """Open staged report metadata or regenerate staged final reports from config."""
    if run_dir is not None:
        dashboard = run_dir / "run_dashboard.html"
        click.echo({"status": "ok", "run_dashboard": str(dashboard), "exists": dashboard.exists()})
        return
    if config_path is None:
        raise click.ClickException("provide either --run-dir or --config")
    raise click.ClickException(
        "regenerating final reports from config is not part of the current validated "
        "pipeline; inspect the staged run dashboard or ratio artifacts instead"
    )


@main.command("invalidate")
@click.option("--run-dir", required=True, type=click.Path(path_type=Path, exists=True))
@click.option("--stage", default=None)
@click.option("--downstream", is_flag=True)
@click.option("--reason", default="manual invalidation")
@click.option("--list", "list_requests", is_flag=True)
@click.option("--cancel", "cancel_request_id", default=None)
def invalidate_command(
    run_dir: Path,
    stage: str | None,
    downstream: bool,
    reason: str,
    list_requests: bool,
    cancel_request_id: str | None,
) -> None:
    """Record a manual invalidation request for a stage and optionally its dependents."""
    if list_requests:
        click.echo({"requests": list_invalidations(run_dir)})
        return
    if cancel_request_id:
        click.echo(cancel_invalidation(run_dir, cancel_request_id))
        return
    if stage is None:
        raise click.ClickException("--stage is required unless --list or --cancel is used")
    click.echo(invalidate_run(run_dir, stage, downstream, reason))


@main.command("verify")
@click.option("--run-dir", required=True, type=click.Path(path_type=Path, exists=True))
def verify_command(run_dir: Path) -> None:
    """Verify current stage manifests and output checksums."""
    errors = verify_run(run_dir)
    if errors:
        raise click.ClickException("; ".join(errors))
    click.echo({"status": "ok"})


@main.command("validate-results")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option("--output-dir", type=click.Path(path_type=Path), default=None)
def validate_results(config_path: str, output_dir: Path | None) -> None:
    """Validate result files and category schemas."""
    config = _load(config_path)
    errors = validate_output_directory(output_dir or config.outputs.directory)
    if errors:
        raise click.ClickException("; ".join(errors))
    click.echo({"status": "ok"})


@main.command("show-version")
def show_version() -> None:
    """Show package version."""
    click.echo(__version__)


if __name__ == "__main__":
    main()
