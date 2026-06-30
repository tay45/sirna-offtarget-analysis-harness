from __future__ import annotations

from sirna_offtarget.isoform_uncertainty.artifacts import write_isoform_uncertainty_artifacts
from sirna_offtarget.isoform_uncertainty.contracts import IsoformUncertaintyRunRecordV1
from sirna_offtarget.isoform_uncertainty.core import (
    assign_isoform_uncertainty_for_gene,
    validate_annotation_snapshot,
)
from tests.unit.isoform_uncertainty.conftest import tx


def test_canonical_json_artifacts_and_report_tsvs_are_written(tmp_path, snapshot, policy) -> None:
    gene, weights, exclusions = assign_isoform_uncertainty_for_gene(
        source_expression_v2_record_id="expr-r1",
        original_gene_id="TP53",
        canonical_gene_id="HGNC:11998",
        approved_symbol="TP53",
        organism="human",
        assembly="GRCh38",
        annotation_snapshot=snapshot,
        annotation_records=[tx("ENST1"), tx("ENST2", deprecated=True)],
        policy=policy,
    )
    validation = validate_annotation_snapshot(snapshot, [tx("ENST1")])
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
        record_counts={"genes": 1},
        output_checksums={"placeholder": "sha256:pending"},
    )
    checksums = write_isoform_uncertainty_artifacts(
        output_dir=tmp_path,
        run_record=run,
        gene_records=[gene],
        weight_records=weights,
        exclusion_records=exclusions,
        annotation_validation=validation,
        method_selection={"default": "annotation_only_equal_prior"},
        input_validation={"expression_contract": "ExpressionAnalysisResultV2"},
        summary={"genes_using_equal_prior": 1},
    )
    assert (tmp_path / "gene_isoform_uncertainty_v1.jsonl").exists()
    assert (tmp_path / "gene_isoform_uncertainty_v1.tsv").exists()
    assert checksums["genes"]
    assert checksums["weights_tsv"]
