from __future__ import annotations

import json
from pathlib import Path

from sirna_offtarget.isoform_uncertainty.artifacts import (
    IMMUTABLE_SCIENTIFIC_ARTIFACTS,
    artifact_paths,
    sha256_file,
    verify_isoform_uncertainty_final_outputs,
    write_final_isoform_uncertainty_metadata,
    write_immutable_isoform_uncertainty_artifacts,
)
from sirna_offtarget.isoform_uncertainty.contracts import (
    IsoformUncertaintyPayloadV1,
    IsoformUncertaintyRunRecordV1,
)
from sirna_offtarget.isoform_uncertainty.core import assign_isoform_uncertainty_for_gene
from tests.unit.isoform_uncertainty.conftest import tx


def _finalize(
    tmp_path: Path, snapshot, policy
) -> tuple[IsoformUncertaintyRunRecordV1, dict[str, str]]:
    gene, weights, exclusions = assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=[tx("ENST1"), tx("ENST2")],
        policy=policy,
    )
    immutable = write_immutable_isoform_uncertainty_artifacts(
        output_dir=tmp_path,
        gene_records=[gene],
        weight_records=weights,
        exclusion_records=exclusions,
        annotation_validation={"schema_version": "1", "status": "passed"},
        method_selection={"schema_version": "1", "stage_enabled": True},
        input_validation={"schema_version": "1", "status": "passed"},
        summary={"gene_isoform_uncertainty_records": 1},
    )
    run = IsoformUncertaintyRunRecordV1(
        run_id="run",
        expression_stage_contract="ExpressionAnalysisResultV2",
        expression_artifact_checksum="sha256:expr",
        annotation_snapshot_id=snapshot.snapshot_id,
        annotation_checksum=snapshot.source_file_checksum,
        transcript_set_policy_id=policy.policy_id,
        isoform_evidence_mode="annotation_only_equal_prior",
        weight_policy="equal_prior",
        numerical_tolerance=1e-6,
        organism="human",
        assembly="GRCh38",
        identifier_snapshot_id="ids",
        identifier_snapshot_checksum="sha256:ids",
        software_version="0.1.0",
        started_at="2026-06-26T00:00:00Z",
        completed_at="2026-06-26T00:00:01Z",
        status="completed",
        record_counts={
            "gene_isoform_uncertainty_records": 1,
            "transcript_prior_weight_records": len(weights),
            "transcript_set_exclusion_records": len(exclusions),
        },
        referenced_artifact_checksums={
            key: immutable[key] for key in IMMUTABLE_SCIENTIFIC_ARTIFACTS
        },
    )
    payload = IsoformUncertaintyPayloadV1(
        run_record=run, counts=run.record_counts, artifacts=immutable
    )
    metadata = write_final_isoform_uncertainty_metadata(
        output_dir=tmp_path,
        run_record=run,
        result_payload=payload.model_dump(mode="json"),
    )
    return run, {**immutable, **metadata}


def test_scientific_artifacts_written_once(tmp_path, snapshot, policy) -> None:
    _finalize(tmp_path, snapshot, policy)
    paths = artifact_paths(tmp_path)
    assert all(paths[key].exists() for key in IMMUTABLE_SCIENTIFIC_ARTIFACTS)


def test_scientific_checksums_computed_after_final_write(tmp_path, snapshot, policy) -> None:
    _run, checksums = _finalize(tmp_path, snapshot, policy)
    assert checksums["genes"] == sha256_file(tmp_path / "gene_isoform_uncertainty_v1.jsonl")


def test_run_record_written_once_after_artifact_checksums(tmp_path, snapshot, policy) -> None:
    run, _checksums = _finalize(tmp_path, snapshot, policy)
    written = json.loads((tmp_path / "isoform_uncertainty_run_v1.json").read_text())
    assert written["referenced_artifact_checksums"] == run.referenced_artifact_checksums


def test_result_record_written_once_after_run_finalization(tmp_path, snapshot, policy) -> None:
    run, _checksums = _finalize(tmp_path, snapshot, policy)
    result = json.loads((tmp_path / "isoform_uncertainty_result_v1.json").read_text())
    assert result["run_record"]["run_id"] == run.run_id
    assert result["run_record_file_sha256"] == sha256_file(
        tmp_path / "isoform_uncertainty_run_v1.json"
    )


def test_run_record_not_rewritten_after_checksum_reference(tmp_path, snapshot, policy) -> None:
    _run, _checksums = _finalize(tmp_path, snapshot, policy)
    before = sha256_file(tmp_path / "isoform_uncertainty_run_v1.json")
    assert verify_isoform_uncertainty_final_outputs(tmp_path).passed
    assert sha256_file(tmp_path / "isoform_uncertainty_run_v1.json") == before


def test_result_record_not_rewritten_after_manifest_checksum(tmp_path, snapshot, policy) -> None:
    _run, _checksums = _finalize(tmp_path, snapshot, policy)
    before = sha256_file(tmp_path / "isoform_uncertainty_result_v1.json")
    assert verify_isoform_uncertainty_final_outputs(tmp_path).passed
    assert sha256_file(tmp_path / "isoform_uncertainty_result_v1.json") == before


def test_no_circular_checksum_reference(tmp_path, snapshot, policy) -> None:
    _run, _checksums = _finalize(tmp_path, snapshot, policy)
    run = json.loads((tmp_path / "isoform_uncertainty_run_v1.json").read_text())
    result = json.loads((tmp_path / "isoform_uncertainty_result_v1.json").read_text())
    assert "run" not in run["referenced_artifact_checksums"]
    assert "result" not in result["artifacts"]


def test_written_run_matches_finalized_run_object(tmp_path, snapshot, policy) -> None:
    run, _checksums = _finalize(tmp_path, snapshot, policy)
    written = json.loads((tmp_path / "isoform_uncertainty_run_v1.json").read_text())
    assert written == run.model_dump(mode="json")


def test_written_result_matches_finalized_result_object(tmp_path, snapshot, policy) -> None:
    run, checksums = _finalize(tmp_path, snapshot, policy)
    result = json.loads((tmp_path / "isoform_uncertainty_result_v1.json").read_text())
    assert result["run_record"] == run.model_dump(mode="json")
    assert result["run_record_file_sha256"] == checksums["run"]


def test_finalization_order_is_deterministic(tmp_path, snapshot, policy) -> None:
    _run, first = _finalize(tmp_path / "a", snapshot, policy)
    _run, second = _finalize(tmp_path / "b", snapshot, policy)
    assert first["genes"] == second["genes"]


def test_run_record_does_not_claim_unverifiable_self_checksum(tmp_path, snapshot, policy) -> None:
    _run, _checksums = _finalize(tmp_path, snapshot, policy)
    run = json.loads((tmp_path / "isoform_uncertainty_run_v1.json").read_text())
    assert run["self_checksum_status"] == "recorded_in_outer_manifest"
    assert "output_checksums" not in run


def test_result_record_does_not_claim_unverifiable_self_checksum(
    tmp_path, snapshot, policy
) -> None:
    _run, _checksums = _finalize(tmp_path, snapshot, policy)
    result = json.loads((tmp_path / "isoform_uncertainty_result_v1.json").read_text())
    assert result["self_checksum_status"] == "recorded_in_outer_manifest"
    assert "result_file_sha256" not in result


def test_run_record_references_immutable_artifact_checksums(tmp_path, snapshot, policy) -> None:
    run, _checksums = _finalize(tmp_path, snapshot, policy)
    assert set(run.referenced_artifact_checksums) == set(IMMUTABLE_SCIENTIFIC_ARTIFACTS)


def test_self_checksum_status_is_explicit(tmp_path, snapshot, policy) -> None:
    run, _checksums = _finalize(tmp_path, snapshot, policy)
    assert run.self_checksum_status == "recorded_in_outer_manifest"


def test_metadata_checksum_policy_is_documented_in_contract() -> None:
    field = IsoformUncertaintyRunRecordV1.model_fields["output_checksums"]
    assert "Deprecated compatibility alias" in str(field.description)
    assert field.exclude is True
