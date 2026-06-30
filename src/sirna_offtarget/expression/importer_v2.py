from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from sirna_offtarget.config import ExpressionConfig
from sirna_offtarget.expression.contracts_v2 import (
    ExpressionContrastRecordV2,
    ExpressionNormalizationRunRecordV2,
    NormalizedGeneEffectRecordV2,
    build_expression_contrast_record_v2,
    build_expression_normalization_run_record_v2,
    build_precomputed_gene_effect_records_v2,
)
from sirna_offtarget.expression.support import (
    ExpressionExecutionSupportRecord,
    expression_execution_support,
)
from sirna_offtarget.expression.validation import validate_precomputed_table
from sirna_offtarget.identifiers.resolver_v2 import (
    IdentifierResolutionRecordV2,
    IdentifierResolverV2,
)


@dataclass(frozen=True)
class PrecomputedExpressionImportV2:
    table: pd.DataFrame
    support: ExpressionExecutionSupportRecord
    contrast: ExpressionContrastRecordV2
    normalization_run: ExpressionNormalizationRunRecordV2
    records: list[NormalizedGeneEffectRecordV2]
    identifier_resolutions: list[IdentifierResolutionRecordV2]
    validation_payload: dict[str, Any]
    filtering_summary_rows: list[dict[str, Any]]
    warning_rows: list[dict[str, Any]]


def import_precomputed_expression_v2(
    *,
    config: ExpressionConfig,
    organism: str,
    metadata: pd.DataFrame,
    resolver: IdentifierResolverV2,
    counts_path: Path,
    metadata_path: Path,
) -> PrecomputedExpressionImportV2:
    if config.precomputed_table is None:
        raise ValueError("precomputed V2 import requires expression.precomputed_table")
    table = pd.read_csv(config.precomputed_table, sep="\t")
    validate_precomputed_table(table, config)
    support = expression_execution_support(config)
    contrast = build_expression_contrast_record_v2(config)
    normalization_run = build_expression_normalization_run_record_v2(
        config=config,
        organism=organism,
        support=support,
        counts_path=counts_path,
        metadata_path=metadata_path,
        source_result_path=config.precomputed_table,
        metadata=metadata,
        identifier_snapshot_id=resolver.snapshot_id,
        started_at=None,
        completed_at=None,
        warnings=tuple(support.limitations),
    )
    source_checksum = _sha256_file(config.precomputed_table)
    resolutions_by_gene = {
        str(gene): resolver.resolve_expression_gene(str(gene))
        for gene in table[config.gene_column].astype(str)
    }
    records = build_precomputed_gene_effect_records_v2(
        table=table,
        config=config,
        organism=organism,
        contrast_id=contrast.contrast_id,
        normalization_run_id=normalization_run.normalization_run_id,
        source_checksum=source_checksum,
        resolutions=resolutions_by_gene,
    )
    warning_rows = [
        {"record_id": record.record_id, "warning": warning}
        for record in records
        for warning in record.warnings
    ]
    return PrecomputedExpressionImportV2(
        table=table,
        support=support,
        contrast=contrast,
        normalization_run=normalization_run,
        records=records,
        identifier_resolutions=list(resolutions_by_gene.values()),
        validation_payload={
            "input_mode": "precomputed_de",
            "schema_validation": "passed",
            "sample_validation": "not_applicable",
            "contrast_validation": "passed",
            "numeric_validation": "passed",
            "duplicate_gene_handling": config.duplicate_gene_policy,
            "missing_value_handling": "row-level nullable fields preserved in V2",
            "p_value_validation": "nonmissing p-values must be within [0,1]",
            "execution_support_level": support.execution_support_level,
            "fatal_errors": [],
            "warnings": list(support.limitations),
            "source_checksums": {str(config.precomputed_table): source_checksum},
        },
        filtering_summary_rows=[],
        warning_rows=warning_rows,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
