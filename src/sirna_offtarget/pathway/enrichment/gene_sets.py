from __future__ import annotations

import hashlib
import json
from typing import Any, cast

from sirna_offtarget.models import Direction
from sirna_offtarget.pathway.enrichment.models import GeneSetDefinitionV1


def build_gene_sets(
    expression_results: dict[str, Any],
    *,
    adjusted_p_value_threshold: float = 0.05,
    absolute_log2_fold_change_threshold: float = 0.5,
    use_shrunken_log2_fold_change: bool = True,
    include_low_count: bool = False,
    intended_target_gene: str | None = None,
) -> list[GeneSetDefinitionV1]:
    thresholds: dict[str, float | bool | str] = {
        "adjusted_p_value_threshold": adjusted_p_value_threshold,
        "absolute_log2_fold_change_threshold": absolute_log2_fold_change_threshold,
        "use_shrunken_log2_fold_change": use_shrunken_log2_fold_change,
        "include_low_count": include_low_count,
    }
    excluded: dict[str, str] = {
        gene: "low_count_excluded"
        for gene, result in expression_results.items()
        if result.low_count_flag and not include_low_count
    }
    eligible = {gene: result for gene, result in expression_results.items() if gene not in excluded}
    changed = {
        gene
        for gene, result in eligible.items()
        if result.adjusted_p_value is not None
        and result.adjusted_p_value <= adjusted_p_value_threshold
        and abs(_effect_size(result, use_shrunken_log2_fold_change))
        >= absolute_log2_fold_change_threshold
    }
    up = {
        gene
        for gene in changed
        if _effect_size(eligible[gene], use_shrunken_log2_fold_change) > 0
        and eligible[gene].direction == Direction.UP
    }
    down = {
        gene
        for gene in changed
        if _effect_size(eligible[gene], use_shrunken_log2_fold_change) < 0
        and eligible[gene].direction == Direction.DOWN
    }
    low_count = {gene for gene, result in expression_results.items() if result.low_count_flag}
    intended = {intended_target_gene} & set(expression_results) if intended_target_gene else set()
    return [
        _definition(
            "significant_upregulated",
            "Significant upregulated genes",
            "up",
            up,
            thresholds,
            excluded,
        ),
        _definition(
            "significant_downregulated",
            "Significant downregulated genes",
            "down",
            down,
            thresholds,
            excluded,
        ),
        _definition(
            "all_tested_changed", "All tested changed genes", "mixed", changed, thresholds, excluded
        ),
        _definition(
            "intended_target_related",
            "Intended target related genes",
            "target",
            intended,
            thresholds | {"intended_target_gene": intended_target_gene or ""},
            excluded,
        ),
        _definition(
            "low_count_excluded",
            "Low count excluded genes",
            "excluded",
            low_count,
            thresholds,
            {},
        ),
        _definition(
            "unmapped_excluded", "Unmapped excluded genes", "excluded", set(), thresholds, {}
        ),
    ]


def _effect_size(result: Any, use_shrunken: bool) -> float:
    shrunken = getattr(result, "shrunken_log2_fold_change", None)
    if use_shrunken and shrunken is not None:
        return cast(float, shrunken)
    canonical = getattr(result, "canonical_log2_fold_change", None)
    if canonical is not None:
        return cast(float, canonical)
    return cast(float, result.log2_fold_change)


def _definition(
    gene_set_id: str,
    name: str,
    direction: str,
    genes: set[str],
    thresholds: dict[str, float | bool | str],
    excluded: dict[str, str],
) -> GeneSetDefinitionV1:
    ordered = tuple(sorted(genes))
    payload = {"gene_set_id": gene_set_id, "genes": ordered, "thresholds": thresholds}
    checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return GeneSetDefinitionV1(
        gene_set_id=gene_set_id,
        name=name,
        source_stage="expression_analysis",
        direction=direction,
        genes=ordered,
        selection_rule="expression_direction_and_configured_significance_thresholds",
        thresholds=thresholds,
        excluded_genes=tuple(sorted(excluded)),
        exclusion_reasons=dict(sorted(excluded.items())),
        checksum=checksum,
    )
