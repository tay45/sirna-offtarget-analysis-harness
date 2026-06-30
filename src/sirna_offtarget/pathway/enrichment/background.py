from __future__ import annotations

import hashlib
import json
from typing import Any

from sirna_offtarget.identifiers import detect_identifier_type
from sirna_offtarget.pathway.enrichment.models import (
    BackgroundUniverseV1,
    PathwayMembershipRecordV1,
)


def build_background_universe(
    expression_results: dict[str, Any],
    memberships: list[PathwayMembershipRecordV1],
    *,
    mode: str = "tested_detectable_annotatable_genes",
    min_baseline_expression: float = 0.0,
    include_low_count: bool = False,
    explicit_genes: set[str] | None = None,
) -> BackgroundUniverseV1:
    annotation_genes = {
        str(record.member_gene_id).upper() for record in memberships if record.member_gene_id
    }
    exclusion_records: list[dict[str, str]] = []
    selected: set[str] = set()
    initial = explicit_genes or set(expression_results)
    for gene in sorted(initial):
        result = expression_results.get(gene)
        normalized_gene = gene.upper()
        reason = ""
        if mode == "explicit_file" and explicit_genes is not None:
            selected.add(normalized_gene)
            continue
        if result is None:
            reason = "not_expression_tested"
            exclusion_records.append({"gene": gene, "reason": reason})
            continue
        baseline_expression = getattr(result, "baseline_expression", None)
        if (
            not reason
            and mode != "all_tested_genes"
            and baseline_expression is not None
            and baseline_expression < min_baseline_expression
        ):
            reason = "below_detectability_threshold"
        elif not include_low_count and result.low_count_flag:
            reason = "low_count"
        elif detect_identifier_type(gene) == "invalid":
            reason = "invalid_identifier"
        elif (
            mode == "tested_detectable_annotatable_genes"
            and annotation_genes
            and normalized_gene not in annotation_genes
        ):
            reason = "not_provider_annotation_eligible"
        if reason:
            exclusion_records.append({"gene": gene, "reason": reason})
        else:
            selected.add(normalized_gene)
    exclusion_counts: dict[str, int] = {}
    for record in exclusion_records:
        reason = record["reason"]
        exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1
    genes = tuple(sorted(selected))
    thresholds: dict[str, float | bool | str] = {
        "min_baseline_expression": min_baseline_expression,
        "include_low_count": include_low_count,
    }
    checksum = hashlib.sha256(
        json.dumps(
            {"mode": mode, "genes": genes, "thresholds": thresholds}, sort_keys=True
        ).encode()
    ).hexdigest()
    detectable_count = len(expression_results) - exclusion_counts.get(
        "below_detectability_threshold", 0
    )
    return BackgroundUniverseV1(
        background_id=f"{mode}_{checksum[:12]}",
        mode=mode,
        genes=genes,
        initial_gene_count=len(initial),
        final_gene_count=len(genes),
        expression_tested_count=len(expression_results),
        detectability_pass_count=detectable_count,
        valid_identifier_count=len(expression_results)
        - exclusion_counts.get("invalid_identifier", 0),
        provider_annotation_eligible_count=len(set(genes) & annotation_genes)
        if annotation_genes
        else len(genes),
        exclusion_counts=exclusion_counts,
        exclusion_records=tuple(exclusion_records),
        thresholds=thresholds,
        checksum=checksum,
        warnings=(() if annotation_genes else ("no provider annotation membership available",)),
    )
