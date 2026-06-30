from __future__ import annotations

from typing import Any

import pandas as pd

from sirna_offtarget.models import Direction, PathwayResult
from sirna_offtarget.pathway.enrichment.models import EnrichmentTerm
from sirna_offtarget.pathway.enrichment.policies import (
    CORRECTION_POLICY_VERSION,
    calculate_ora_test_values,
    correction_family_id,
)
from sirna_offtarget.pathway.enrichment.statistics import benjamini_hochberg


def analyze_pathway_enrichment(
    expression_results: dict[str, Any],
    regulons: pd.DataFrame,
) -> dict[str, PathwayResult]:
    regulon_rows = regulons.to_dict("records")
    regulon_targets = {str(row.get("target", "")) for row in regulon_rows}
    stress_targets = {
        str(row.get("target", ""))
        for row in regulon_rows
        if str(row.get("regulon", "")) == "stress_signature"
    }
    changed_genes = {
        gene
        for gene, result in expression_results.items()
        if result.direction in {Direction.UP, Direction.DOWN}
    }
    results: dict[str, PathwayResult] = {}
    for gene, _expression in expression_results.items():
        pathway_coherence = 0.0
        if gene in regulon_targets:
            pathway_coherence = round(
                len(changed_genes & regulon_targets) / max(len(regulon_targets), 1),
                6,
            )
        results[gene] = PathwayResult(
            gene=gene,
            target_pathway_distance=None,
            direction_consistency=None,
            pathway_coherence=pathway_coherence,
            regulon_evidence=_regulon_coherence(gene, regulons, expression_results),
            stress_signature_evidence=1.0 if gene in stress_targets else 0.0,
            paths=(),
            shortest_signed_path=(),
            shortest_unsigned_supported_path=(),
            composed_path_sign=None,
            expected_candidate_direction=None,
            conflicting_paths=False,
            supporting_path_count=0,
            contradictory_path_count=0,
            provider_sources=("enrichment_summary",),
            evidence_limitations=(
                "Pathway enrichment/coherence is contextual and not causal path evidence.",
            ),
        )
    return results


def overrepresentation_analysis(
    *,
    provider: str,
    annotation_source: str,
    gene_set_category: str,
    expression_direction: str,
    test_genes: set[str],
    pathway_members: dict[str, set[str]],
    pathway_names: dict[str, str],
    background_genes: set[str],
    database_release: str,
    primary_test: str = "fisher_exact_greater",
    calculate_diagnostic_alternative: bool = True,
) -> list[EnrichmentTerm]:
    normalized_test = {gene.upper() for gene in test_genes} & {
        gene.upper() for gene in background_genes
    }
    normalized_background = {gene.upper() for gene in background_genes}
    raw_terms: list[EnrichmentTerm] = []
    raw_p_values: list[float] = []
    for pathway_id, members in sorted(pathway_members.items()):
        normalized_members = {gene.upper() for gene in members} & normalized_background
        matched = tuple(sorted(normalized_test & normalized_members))
        observed = len(matched)
        if observed == 0:
            continue
        background_size = len(normalized_background)
        test_size = len(normalized_test)
        pathway_size = len(normalized_members)
        a = observed
        b = test_size - observed
        c = pathway_size - observed
        d = background_size - a - b - c
        test_values = calculate_ora_test_values(
            observed=observed,
            pathway_size=pathway_size,
            test_size=test_size,
            background_size=background_size,
            contingency_table=(a, b, c, d),
            primary_test=primary_test,
            calculate_diagnostic_alternative=calculate_diagnostic_alternative,
        )
        expected = test_size * pathway_size / background_size if background_size else 0.0
        raw_p_values.append(test_values.primary_raw_p_value)
        family_id = correction_family_id(
            provider=provider,
            annotation_dataset=annotation_source,
            gene_set_id=gene_set_category,
            expression_direction=expression_direction,
            calculation_mode="local_ora",
        )
        raw_terms.append(
            EnrichmentTerm(
                provider=provider,
                pathway_id=pathway_id,
                pathway_name=pathway_names.get(pathway_id, pathway_id),
                expression_direction=expression_direction,
                observed_count=observed,
                expected_count=expected,
                enrichment_ratio=observed / expected if expected else 0.0,
                raw_p_value=test_values.primary_raw_p_value,
                fdr=test_values.primary_raw_p_value,
                matched_genes=matched,
                background_size=background_size,
                test_list_size=test_size,
                database_release=database_release,
                contingency_table=(a, b, c, d),
                adjusted_p_value=None,
                primary_test_method=test_values.primary_test_method,
                primary_raw_p_value=test_values.primary_raw_p_value,
                diagnostic_test_method=test_values.diagnostic_test_method,
                diagnostic_raw_p_value=test_values.diagnostic_raw_p_value,
                test_policy_version=test_values.test_policy_version,
                correction_family_id=family_id,
                correction_method="benjamini_hochberg",
                correction_policy_version=CORRECTION_POLICY_VERSION,
            )
        )
    families: dict[str, list[int]] = {}
    for index, term in enumerate(raw_terms):
        families.setdefault(term.correction_family_id, []).append(index)
    corrected = list(raw_terms)
    for family_id, indexes in families.items():
        adjusted = benjamini_hochberg(
            [raw_terms[index].primary_raw_p_value or 1.0 for index in indexes]
        )
        for family_index, result_index in enumerate(indexes):
            term = raw_terms[result_index]
            corrected[result_index] = EnrichmentTerm(
                **{
                    **term.__dict__,
                    "fdr": adjusted[family_index],
                    "adjusted_p_value": adjusted[family_index],
                    "correction_family_size": len(indexes),
                    "correction_family_id": family_id,
                }
            )
    return corrected


def _regulon_coherence(
    gene: str,
    regulons: pd.DataFrame,
    expression_results: dict[str, Any],
) -> float:
    memberships = [row for row in regulons.to_dict("records") if str(row.get("target", "")) == gene]
    if not memberships:
        return 0.0
    regulon = str(memberships[0].get("regulon", ""))
    targets = [
        str(row.get("target", ""))
        for row in regulons.to_dict("records")
        if str(row.get("regulon", "")) == regulon
    ]
    changed = [
        target
        for target in targets
        if target in expression_results
        and expression_results[target].direction.value in {"up", "down"}
    ]
    return round(len(changed) / len(targets), 6) if targets else 0.0
