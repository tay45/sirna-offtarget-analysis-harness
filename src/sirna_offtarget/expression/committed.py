from __future__ import annotations

import hashlib
import json
from dataclasses import fields
from pathlib import Path
from typing import Any, NoReturn

from sirna_offtarget.contracts.stage_results import ExpressionAnalysisResultV2
from sirna_offtarget.expression.contracts_v2 import NormalizedGeneEffectRecordV2
from sirna_offtarget.expression.downstream import (
    DownstreamExpressionViewV1,
    IsoformGeneEffectInputViewV1,
    normalized_gene_effect_v2_to_downstream_view,
    normalized_gene_effect_v2_to_isoform_input,
    normalized_gene_effect_v2_to_network_input,
    normalized_gene_effect_v2_to_pathway_input,
)


class CommittedExpressionArtifactNotFoundError(FileNotFoundError):
    pass


class LegacyExpressionArtifactNotSupportedError(RuntimeError):
    pass


def load_committed_normalized_gene_effects_v2(
    run_directory: Path,
) -> list[NormalizedGeneEffectRecordV2]:
    load_committed_expression_analysis_v2(run_directory)
    path = _find_committed_effect_artifact(run_directory, "normalized_gene_effects_v2.jsonl")
    field_names = {field.name for field in fields(NormalizedGeneEffectRecordV2)}
    records: list[NormalizedGeneEffectRecordV2] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        data: dict[str, Any] = json.loads(line)
        records.append(
            NormalizedGeneEffectRecordV2(
                **{key: value for key, value in data.items() if key in field_names}
            )
        )
    return records


def load_committed_expression_effects_v2(
    run_directory: Path,
) -> DownstreamExpressionViewV1:
    return normalized_gene_effect_v2_to_downstream_view(
        load_committed_normalized_gene_effects_v2(run_directory)
    )


def load_isoform_gene_effect_inputs(run_directory: Path) -> IsoformGeneEffectInputViewV1:
    return normalized_gene_effect_v2_to_isoform_input(
        load_committed_normalized_gene_effects_v2(run_directory)
    )


def load_pathway_gene_effect_inputs(run_directory: Path) -> DownstreamExpressionViewV1:
    return normalized_gene_effect_v2_to_pathway_input(
        load_committed_normalized_gene_effects_v2(run_directory)
    )


def load_network_gene_effect_inputs(run_directory: Path) -> DownstreamExpressionViewV1:
    return normalized_gene_effect_v2_to_network_input(
        load_committed_normalized_gene_effects_v2(run_directory)
    )


def load_committed_expression_analysis_v2(run_directory: Path) -> ExpressionAnalysisResultV2:
    path = _find_committed_stage_contract(run_directory)
    data = _load_json(path)
    if data.get("contract_name") != "ExpressionAnalysisResultV2":
        raise CommittedExpressionArtifactNotFoundError(
            "committed expression stage contract is not ExpressionAnalysisResultV2"
        )
    return ExpressionAnalysisResultV2.model_validate(data)


def load_committed_normalized_gene_effects(run_directory: Path) -> NoReturn:
    raise LegacyExpressionArtifactNotSupportedError(
        "normalized_gene_effects_v1.jsonl is not a supported production expression source; "
        "load committed normalized_gene_effects_v2.jsonl instead"
    )


def load_expression_effects_for_downstream(
    run_directory: Path,
) -> DownstreamExpressionViewV1:
    return load_committed_expression_effects_v2(run_directory)


def _find_committed_stage_contract(run_directory: Path) -> Path:
    stage_dir = run_directory / "stages" / "05_expression_analysis"
    manifest_path = _current_manifest_path(stage_dir)
    if manifest_path is None:
        raise CommittedExpressionArtifactNotFoundError(
            "ExpressionAnalysisResultV2 not found: expression stage has no committed manifest"
        )
    manifest = _load_json(manifest_path)
    if manifest.get("status") not in {"completed", "completed_with_warnings", "skipped_reused"}:
        status = manifest.get("status")
        raise CommittedExpressionArtifactNotFoundError(
            f"ExpressionAnalysisResultV2 not found: expression stage status is {status}"
        )
    contract_path = manifest_path.parent / "committed" / "outputs" / "stage_result.json"
    if not contract_path.exists():
        raise CommittedExpressionArtifactNotFoundError("committed expression stage_result missing")
    expected = manifest.get("contract_sha256")
    if expected and _sha256_file(contract_path) != expected:
        raise CommittedExpressionArtifactNotFoundError(
            "committed expression stage_result checksum mismatch"
        )
    return contract_path


def _find_committed_effect_artifact(run_directory: Path, filename: str) -> Path:
    stage_dir = run_directory / "stages" / "05_expression_analysis"
    manifest_path = _current_manifest_path(stage_dir)
    if manifest_path is None:
        raise CommittedExpressionArtifactNotFoundError(
            f"{filename} not found: expression stage has no committed current manifest"
        )
    manifest = _load_json(manifest_path)
    if manifest.get("status") not in {"completed", "completed_with_warnings", "skipped_reused"}:
        raise CommittedExpressionArtifactNotFoundError(
            f"{filename} not found: expression stage status is {manifest.get('status')}"
        )
    for record in manifest.get("output_artifacts", []):
        record_path = str(record.get("path", ""))
        if Path(record_path).name != filename:
            continue
        artifact = manifest_path.parent / record_path
        if not artifact.exists():
            raise CommittedExpressionArtifactNotFoundError(
                f"listed artifact is missing: {artifact}"
            )
        expected = record.get("sha256")
        if expected and _sha256_file(artifact) != expected:
            raise CommittedExpressionArtifactNotFoundError(
                f"listed artifact checksum mismatch: {artifact}"
            )
        if "committed/outputs" not in artifact.as_posix():
            raise CommittedExpressionArtifactNotFoundError(
                f"artifact is not in committed outputs: {artifact}"
            )
        return artifact
    raise CommittedExpressionArtifactNotFoundError(
        f"{filename} not listed in committed expression manifest"
    )


def _current_manifest_path(stage_dir: Path) -> Path | None:
    pointer = stage_dir / "current.json"
    if not pointer.exists():
        return None
    data = _load_json(pointer)
    manifest = data.get("manifest_path")
    if isinstance(manifest, str):
        path = Path(manifest)
        return path if path.is_absolute() else stage_dir / path
    attempt = data.get("attempt_dir")
    if isinstance(attempt, str):
        path = Path(attempt)
        attempt_dir = path if path.is_absolute() else stage_dir / "attempts" / path
        manifest_path = attempt_dir / "stage_manifest.json"
        return manifest_path if manifest_path.exists() else None
    attempt_directory = data.get("attempt_directory")
    if isinstance(attempt_directory, str):
        manifest_path = stage_dir / "attempts" / attempt_directory / "stage_manifest.json"
        return manifest_path if manifest_path.exists() else None
    attempt_number = data.get("attempt_number")
    if isinstance(attempt_number, int):
        manifest_path = (
            stage_dir / "attempts" / f"attempt_{attempt_number:03d}" / "stage_manifest.json"
        )
        return manifest_path if manifest_path.exists() else None
    current_attempt = data.get("current_attempt")
    if isinstance(current_attempt, int):
        manifest_path = (
            stage_dir / "attempts" / f"attempt_{current_attempt:03d}" / "stage_manifest.json"
        )
        return manifest_path if manifest_path.exists() else None
    return None


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise CommittedExpressionArtifactNotFoundError(f"{path} is not a JSON object")
    return data


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
