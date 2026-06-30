from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sirna_offtarget.expression.committed import (
    CommittedExpressionArtifactNotFoundError,
    LegacyExpressionArtifactNotSupportedError,
    load_committed_normalized_gene_effects,
    load_committed_normalized_gene_effects_v2,
    load_expression_effects_for_downstream,
    load_isoform_gene_effect_inputs,
    load_network_gene_effect_inputs,
    load_pathway_gene_effect_inputs,
)


def _v2_record() -> dict[str, object]:
    return {
        "schema_version": "2",
        "record_id": "r1",
        "original_gene_id": "TP53",
        "original_gene_namespace": "hgnc_symbol",
        "canonical_gene_id": "HGNC:11998",
        "approved_symbol": "TP53",
        "identifier_resolution_id": "ids:TP53",
        "identifier_mapping_confidence": 1.0,
        "identifier_ambiguity_status": "unambiguous",
        "identifier_organism_match": True,
        "organism": "human",
        "contrast_id": "treated_vs_control",
        "normalization_run_id": "run1",
        "input_mode": "precomputed_de",
        "input_value_scale": "raw_count",
        "normalization_method": "imported",
        "differential_method": "imported",
        "effect_scale": "log2_fold_change",
        "raw_effect_estimate": -1.0,
        "reported_log2_fold_change": -1.0,
        "shrunken_log2_fold_change": None,
        "canonical_log2_fold_change": -1.0,
        "canonical_effect_source": "reported_unshrunken_log2fc",
        "standard_error": None,
        "confidence_interval_lower": None,
        "confidence_interval_upper": None,
        "test_statistic": None,
        "raw_p_value": None,
        "adjusted_p_value": None,
        "adjusted_pvalue_status": "adjusted_pvalue_unavailable",
        "multiple_testing_method": "benjamini_hochberg",
        "tested_status": "tested",
        "filter_status": "not_filtered",
        "low_count_status": "not_imported",
        "model_status": "estimated",
        "exclusion_reason": None,
        "numerical_direction": "decreased",
        "statistical_support_status": "adjusted_pvalue_unavailable",
        "biological_threshold_status": "exceeds_decrease_threshold",
        "direction_basis": "canonical_log2_fold_change",
        "control_abundance_summary": None,
        "treatment_abundance_summary": None,
        "mean_abundance_summary": 10.0,
        "replicate_count_control": None,
        "replicate_count_treatment": None,
        "design_formula": "~ condition",
        "covariates": [],
        "batch_terms": [],
        "analysis_software": "external",
        "analysis_software_version": "unknown",
        "provenance_record_ids": [],
        "source_row_identifier": "row:0:TP53",
        "warnings": [],
    }


def _v1_record() -> dict[str, object]:
    return {
        "gene": "TP53",
        "gene_id_namespace": "symbol",
        "organism": "human",
        "contrast_id": "treated_vs_control",
        "normalization_run_id": "run1",
        "canonical_log2_fold_change": -1.0,
        "effect_scale": "log2_fold_change",
        "direction": "decreased",
        "threshold_status": "above_threshold",
        "tested_status": "tested",
        "low_count_status": "passes_count_filter",
        "raw_p_value": 0.01,
        "adjusted_p_value": 0.02,
        "significance_status": "significant",
        "backend_name": "v2_compatibility_view",
        "backend_version": "deprecated-loss-aware",
        "demonstration_only": False,
        "provenance": {"source": "compatibility"},
    }


def _write_committed_run(
    tmp_path: Path, *, status: str = "completed", include_v1: bool = False
) -> Path:
    stage_dir = tmp_path / "stages" / "05_expression_analysis"
    attempt_dir = stage_dir / "attempts" / "attempt_001"
    output = attempt_dir / "committed" / "outputs" / "normalized_gene_effects_v2.jsonl"
    output.parent.mkdir(parents=True)
    output.write_text("\n" + json.dumps(_v2_record()) + "\n")

    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    contract_path = output.parent / "stage_result.json"
    contract_path.write_text(
        json.dumps(
            {
                "contract_name": "ExpressionAnalysisResultV2",
                "schema_version": "2",
                "stage_name": "expression_analysis",
                "stage_version": "1",
                "run_id": "run1",
                "attempt_number": 1,
                "payload": {
                    "canonical": True,
                    "normalization_run_artifact": "expression_normalization_run_v2.json",
                    "contrasts_artifact": "expression_contrasts_v2.json",
                    "normalized_gene_effects_artifact": "normalized_gene_effects_v2.jsonl",
                    "identifier_resolutions_artifact": (
                        "expression_identifier_resolutions_v2.jsonl"
                    ),
                    "input_validation_artifact": "expression_input_validation.json",
                    "filtering_summary_artifact": "expression_filtering_summary.tsv",
                    "warnings_artifact": "expression_warnings.tsv",
                    "execution_support_artifact": "expression_execution_support.json",
                    "downstream_compatibility_artifact": (
                        "expression_downstream_compatibility_view_v1.json"
                    ),
                    "artifact_checksums": {
                        "normalized_gene_effects_v2.jsonl": checksum,
                    },
                    "record_counts": {"normalized_gene_effects_v2": 1},
                    "compatibility_metadata": {},
                },
                "artifacts": [],
                "warnings": [],
            }
        )
    )
    output_artifacts = [
        {
            "path": "committed/outputs/normalized_gene_effects_v2.jsonl",
            "sha256": checksum,
        }
    ]
    if include_v1:
        v1_output = output.parent / "normalized_gene_effects_v1.jsonl"
        v1_output.write_text(json.dumps(_v1_record()) + "\n")
        output_artifacts.append(
            {
                "path": "committed/outputs/normalized_gene_effects_v1.jsonl",
                "sha256": hashlib.sha256(v1_output.read_bytes()).hexdigest(),
            }
        )
    manifest = {
        "status": status,
        "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "output_artifacts": output_artifacts,
    }
    (attempt_dir / "stage_manifest.json").write_text(json.dumps(manifest))
    stage_dir.mkdir(parents=True, exist_ok=True)
    (stage_dir / "current.json").write_text(
        json.dumps({"attempt_number": 1, "attempt_directory": "attempt_001"})
    )
    return output


def _stage_paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    stage_dir = tmp_path / "stages" / "05_expression_analysis"
    attempt_dir = stage_dir / "attempts" / "attempt_001"
    manifest = attempt_dir / "stage_manifest.json"
    output = attempt_dir / "committed" / "outputs" / "normalized_gene_effects_v2.jsonl"
    contract = output.parent / "stage_result.json"
    return stage_dir, attempt_dir, manifest, contract


def test_committed_loader_reads_manifest_listed_committed_output(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    records = load_committed_normalized_gene_effects_v2(tmp_path)
    assert records[0].original_gene_id == "TP53"
    assert records[0].canonical_gene_id == "HGNC:11998"


@pytest.mark.parametrize("status", ["completed_with_warnings", "skipped_reused"])
def test_committed_loader_accepts_successful_terminal_statuses(tmp_path: Path, status: str) -> None:
    _write_committed_run(tmp_path, status=status)
    assert load_committed_normalized_gene_effects_v2(tmp_path)[0].record_id == "r1"


def test_downstream_accessor_defaults_to_v2(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    view = load_expression_effects_for_downstream(tmp_path)
    assert len(view.records) == 1
    assert view.records[0].source_expression_v2_record_id == "r1"


def test_compatibility_option_removed_and_v1_is_ignored(tmp_path: Path) -> None:
    _write_committed_run(tmp_path, include_v1=True)
    view = load_expression_effects_for_downstream(tmp_path)

    assert len(view.records) == 1
    assert view.records[0].source_expression_v2_record_id == "r1"


def test_compatibility_keyword_is_not_public_api(tmp_path: Path) -> None:
    _write_committed_run(tmp_path, include_v1=True)
    with pytest.raises(TypeError):
        load_expression_effects_for_downstream(tmp_path, compatibility=True)  # type: ignore[call-arg]


def test_legacy_v1_loader_raises_typed_error_without_reading_files(tmp_path: Path) -> None:
    _write_committed_run(tmp_path, include_v1=True)
    with pytest.raises(LegacyExpressionArtifactNotSupportedError, match="v1.jsonl"):
        load_committed_normalized_gene_effects(tmp_path)


def test_isoform_input_loader_reads_committed_v2(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    view = load_isoform_gene_effect_inputs(tmp_path)

    assert view.records[0].source_expression_v2_record_id == "r1"
    assert view.records[0].canonical_log2_fold_change == -1.0


def test_isoform_input_loader_does_not_read_v1(tmp_path: Path) -> None:
    _write_committed_run(tmp_path, include_v1=True)
    view = load_isoform_gene_effect_inputs(tmp_path)

    assert view.records[0].original_gene_id == "TP53"
    assert view.records[0].adjusted_p_value is None


def test_all_consumer_loaders_preserve_committed_v2_identity(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    views = [
        load_expression_effects_for_downstream(tmp_path),
        load_pathway_gene_effect_inputs(tmp_path),
        load_network_gene_effect_inputs(tmp_path),
    ]
    assert {view.records[0].source_expression_v2_record_id for view in views} == {"r1"}


def test_committed_loader_rejects_uncommitted_attempt(tmp_path: Path) -> None:
    artifact = (
        tmp_path
        / "stages/05_expression_analysis/attempts/attempt_001/outputs"
        / "normalized_gene_effects_v2.jsonl"
    )
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n")
    with pytest.raises(CommittedExpressionArtifactNotFoundError):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_committed_loader_rejects_failed_attempt(tmp_path: Path) -> None:
    _write_committed_run(tmp_path, status="failed")
    with pytest.raises(CommittedExpressionArtifactNotFoundError, match="status is failed"):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_committed_loader_rejects_partial_attempt(tmp_path: Path) -> None:
    _write_committed_run(tmp_path, status="running")
    with pytest.raises(CommittedExpressionArtifactNotFoundError, match="status is running"):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_committed_loader_requires_manifest_entry(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    manifest = (
        tmp_path
        / "stages"
        / "05_expression_analysis"
        / "attempts"
        / "attempt_001"
        / "stage_manifest.json"
    )
    manifest.write_text(json.dumps({"status": "completed", "output_artifacts": []}))
    with pytest.raises(CommittedExpressionArtifactNotFoundError, match="not listed"):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_committed_loader_rejects_missing_listed_artifact(tmp_path: Path) -> None:
    output = _write_committed_run(tmp_path)
    output.unlink()
    with pytest.raises(
        CommittedExpressionArtifactNotFoundError,
        match="listed artifact is missing",
    ):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_committed_loader_rejects_uncommitted_listed_artifact(tmp_path: Path) -> None:
    output = _write_committed_run(tmp_path)
    _, attempt_dir, manifest, _ = _stage_paths(tmp_path)
    uncommitted = attempt_dir / "outputs" / "normalized_gene_effects_v2.jsonl"
    uncommitted.parent.mkdir()
    uncommitted.write_text(output.read_text())
    checksum = hashlib.sha256(uncommitted.read_bytes()).hexdigest()
    data = json.loads(manifest.read_text())
    data["output_artifacts"] = [
        {"path": "outputs/normalized_gene_effects_v2.jsonl", "sha256": checksum}
    ]
    manifest.write_text(json.dumps(data))

    with pytest.raises(CommittedExpressionArtifactNotFoundError, match="not in committed outputs"):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_committed_loader_rejects_checksum_mismatch(tmp_path: Path) -> None:
    output = _write_committed_run(tmp_path)
    output.write_text(json.dumps(_v2_record()) + "\n")
    with pytest.raises(CommittedExpressionArtifactNotFoundError, match="checksum mismatch"):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_committed_loader_rejects_missing_stage_result(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    _, _, _, contract = _stage_paths(tmp_path)
    contract.unlink()
    with pytest.raises(CommittedExpressionArtifactNotFoundError, match="stage_result missing"):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_committed_loader_rejects_stage_result_checksum_mismatch(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    _, _, _, contract = _stage_paths(tmp_path)
    payload = json.loads(contract.read_text())
    payload["warnings"] = ["mutated after manifest"]
    contract.write_text(json.dumps(payload))
    with pytest.raises(CommittedExpressionArtifactNotFoundError, match="stage_result checksum"):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_committed_loader_rejects_non_v2_stage_result(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    _, _, manifest, contract = _stage_paths(tmp_path)
    payload = json.loads(contract.read_text())
    payload["contract_name"] = "ExpressionAnalysisResultV1"
    contract.write_text(json.dumps(payload))
    data = json.loads(manifest.read_text())
    data["contract_sha256"] = hashlib.sha256(contract.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(data))

    with pytest.raises(
        CommittedExpressionArtifactNotFoundError,
        match="not ExpressionAnalysisResultV2",
    ):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_committed_loader_rejects_non_object_stage_result_json(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    _, _, manifest, contract = _stage_paths(tmp_path)
    contract.write_text("[]")
    data = json.loads(manifest.read_text())
    data["contract_sha256"] = hashlib.sha256(contract.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(data))

    with pytest.raises(CommittedExpressionArtifactNotFoundError, match="not a JSON object"):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_committed_loader_rejects_non_object_current_pointer(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    stage_dir, _, _, _ = _stage_paths(tmp_path)
    (stage_dir / "current.json").write_text("[]")

    with pytest.raises(CommittedExpressionArtifactNotFoundError, match="not a JSON object"):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_current_manifest_path_accepts_manifest_path_pointer(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    stage_dir, _, _, _ = _stage_paths(tmp_path)
    (stage_dir / "current.json").write_text(
        json.dumps({"manifest_path": "attempts/attempt_001/stage_manifest.json"})
    )
    assert load_committed_normalized_gene_effects_v2(tmp_path)[0].record_id == "r1"


def test_current_manifest_path_accepts_attempt_dir_pointer(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    stage_dir, _, _, _ = _stage_paths(tmp_path)
    (stage_dir / "current.json").write_text(json.dumps({"attempt_dir": "attempt_001"}))
    assert load_committed_normalized_gene_effects_v2(tmp_path)[0].record_id == "r1"


def test_current_manifest_path_accepts_current_attempt_pointer(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    stage_dir, _, _, _ = _stage_paths(tmp_path)
    (stage_dir / "current.json").write_text(json.dumps({"current_attempt": 1}))
    assert load_committed_normalized_gene_effects_v2(tmp_path)[0].record_id == "r1"


def test_current_manifest_path_missing_attempt_manifest_fails(tmp_path: Path) -> None:
    _write_committed_run(tmp_path)
    stage_dir, _, _, _ = _stage_paths(tmp_path)
    (stage_dir / "current.json").write_text(json.dumps({"attempt_directory": "missing"}))
    with pytest.raises(CommittedExpressionArtifactNotFoundError, match="no committed manifest"):
        load_committed_normalized_gene_effects_v2(tmp_path)


def test_committed_loader_preserves_deterministic_record_order(tmp_path: Path) -> None:
    output = _write_committed_run(tmp_path)
    second = _v2_record() | {
        "record_id": "r2",
        "original_gene_id": "BRCA1",
        "approved_symbol": "BRCA1",
        "canonical_gene_id": "HGNC:1100",
        "identifier_resolution_id": "ids:BRCA1",
        "source_row_identifier": "row:1:BRCA1",
    }
    output.write_text("\n" + json.dumps(_v2_record()) + "\n" + json.dumps(second) + "\n")
    _, _, manifest, contract = _stage_paths(tmp_path)
    data = json.loads(manifest.read_text())
    data["output_artifacts"][0]["sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(data))

    records = load_committed_normalized_gene_effects_v2(tmp_path)
    assert [record.record_id for record in records] == ["r1", "r2"]


def test_missing_v2_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(CommittedExpressionArtifactNotFoundError, match="no committed manifest"):
        load_isoform_gene_effect_inputs(tmp_path)
