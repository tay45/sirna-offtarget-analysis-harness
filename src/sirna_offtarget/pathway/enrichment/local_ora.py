from __future__ import annotations

from collections import defaultdict
from typing import Any, cast

from sirna_offtarget.pathway.enrichment.models import (
    BackgroundUniverseV1,
    GeneSetDefinitionV1,
    LocalEnrichmentResultV1,
    PathwayMembershipRecordV1,
)
from sirna_offtarget.pathway.enrichment.policies import (
    CORRECTION_POLICY_VERSION,
    calculate_ora_test_values,
    correction_family_id,
)
from sirna_offtarget.pathway.enrichment.statistics import (
    benjamini_hochberg,
)


def build_memberships_from_provider_results(
    rows: list[dict[str, Any]],
) -> list[PathwayMembershipRecordV1]:
    memberships: list[PathwayMembershipRecordV1] = []
    for row in rows:
        provider = str(row.get("provider", "unknown"))
        annotation_source = str(row.get("annotation_source", provider))
        term_id = str(row.get("term_id") or row.get("pathway_id") or "")
        term_name = str(row.get("term_name") or row.get("pathway_name") or term_id)
        snapshot_id = str(row.get("retrieval_snapshot", "unknown_snapshot"))
        provider_version = str(row.get("database_version", "")) or None
        matched_genes = cast(tuple[str, ...] | list[str], row.get("matched_genes", ()) or ())
        warnings = cast(tuple[str, ...] | list[str], row.get("warnings", ()) or ())
        membership_warnings = tuple(warnings) + (
            "incomplete_membership_from_provider_enrichment_hits_only",
        )
        for gene in matched_genes:
            gene_id = str(gene).upper()
            memberships.append(
                PathwayMembershipRecordV1(
                    provider=provider,
                    annotation_source=annotation_source,
                    term_id=term_id,
                    term_name=term_name,
                    member_entity_id=f"gene:{gene_id}",
                    member_gene_id=gene_id,
                    organism=str(row.get("organism", "")),
                    hierarchy_parent_ids=(),
                    evidence_type="provider_annotation_membership",
                    provider_version=provider_version,
                    snapshot_id=snapshot_id,
                    membership_type="submitted_hit_membership",
                    membership_completeness="submitted_hit_only",
                    warnings=membership_warnings,
                )
            )
    return memberships


def run_local_ora(
    gene_sets: list[GeneSetDefinitionV1],
    background: BackgroundUniverseV1,
    memberships: list[PathwayMembershipRecordV1],
    *,
    primary_test: str = "fisher_exact_greater",
    calculate_diagnostic_alternative: bool = True,
    require_complete_membership: bool = True,
) -> list[LocalEnrichmentResultV1]:
    by_term: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    names: dict[tuple[str, str, str], str] = {}
    snapshots: dict[tuple[str, str, str], str] = {}
    completeness: dict[tuple[str, str, str], str] = {}
    incomplete_terms: set[tuple[str, str, str]] = set()
    for membership in memberships:
        if not membership.member_gene_id:
            continue
        key = (membership.provider, membership.annotation_source, membership.term_id)
        completeness[key] = membership.membership_completeness
        if membership.membership_completeness != "complete":
            incomplete_terms.add(key)
        by_term[key].add(membership.member_gene_id.upper())
        names[key] = membership.term_name
        snapshots[key] = membership.snapshot_id
    raw_results: list[LocalEnrichmentResultV1] = []
    background_genes = set(background.genes)
    background_size = len(background_genes)
    for gene_set in gene_sets:
        test_genes = set(gene_set.genes) & background_genes
        if not test_genes or not background_genes:
            continue
        for key, members in sorted(by_term.items()):
            provider, annotation_source, term_id = key
            if require_complete_membership and key in incomplete_terms:
                continue
            term_members = members & background_genes
            matched = tuple(sorted(test_genes & term_members))
            observed = len(matched)
            if observed == 0:
                continue
            pathway_size = len(term_members)
            test_size = len(test_genes)
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
            family_id = correction_family_id(
                provider=provider,
                annotation_dataset=annotation_source,
                gene_set_id=gene_set.gene_set_id,
                expression_direction=gene_set.direction,
                calculation_mode="locally_calculated_from_provider_annotations",
            )
            raw_results.append(
                LocalEnrichmentResultV1(
                    provider_annotation_source=f"{provider}:{annotation_source}",
                    term_id=term_id,
                    term_name=names[key],
                    gene_set_id=gene_set.gene_set_id,
                    observed_count=observed,
                    expected_count=expected,
                    fold_enrichment=observed / expected if expected else 0.0,
                    raw_p_value=test_values.primary_raw_p_value,
                    adjusted_p_value=test_values.primary_raw_p_value,
                    contingency_table=(a, b, c, d),
                    matched_genes=matched,
                    pathway_size=pathway_size,
                    test_list_size=test_size,
                    background_size=background_size,
                    background_id=background.background_id,
                    annotation_snapshot_id=snapshots[key],
                    statistics_method=test_values.primary_test_method,
                    primary_test_method=test_values.primary_test_method,
                    primary_raw_p_value=test_values.primary_raw_p_value,
                    diagnostic_test_method=test_values.diagnostic_test_method,
                    diagnostic_raw_p_value=test_values.diagnostic_raw_p_value,
                    test_policy_version=test_values.test_policy_version,
                    correction_family_id=family_id,
                    correction_method="benjamini_hochberg",
                    correction_policy_version=CORRECTION_POLICY_VERSION,
                    annotation_membership_completeness=completeness.get(key, "unknown"),
                )
            )
    families: dict[str, list[int]] = defaultdict(list)
    for index, result in enumerate(raw_results):
        families[result.correction_family_id].append(index)
    corrected = list(raw_results)
    for family_id, indexes in families.items():
        adjusted = benjamini_hochberg([raw_results[index].primary_raw_p_value for index in indexes])
        family_size = len(indexes)
        for family_index, result_index in enumerate(indexes):
            result = raw_results[result_index]
            corrected[result_index] = LocalEnrichmentResultV1(
                **{
                    **result.__dict__,
                    "adjusted_p_value": adjusted[family_index],
                    "correction_family_id": family_id,
                    "correction_family_size": family_size,
                }
            )
    return corrected


def consensus_by_annotation_lineage(
    provider_results: list[dict[str, Any]],
    local_results: list[LocalEnrichmentResultV1],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in provider_results:
        key = (str(row.get("annotation_source", "")), str(row.get("term_id", "")))
        current = grouped.setdefault(
            key,
            {
                "annotation_source": key[0],
                "term_id": key[1],
                "provider_specific_results": [],
                "calculation_modes": set(),
                "matched_gene_overlap": set(),
                "annotation_lineage_overlap": "unknown",
                "warnings": [],
            },
        )
        provider_specific_results = cast(list[dict[str, Any]], current["provider_specific_results"])
        calculation_modes = cast(set[str], current["calculation_modes"])
        matched_gene_overlap = cast(set[str], current["matched_gene_overlap"])
        provider_specific_results.append(row)
        calculation_modes.add("provider_calculated")
        matched_gene_overlap.update(
            cast(tuple[str, ...] | list[str], row.get("matched_genes", ()) or ())
        )
    for result in local_results:
        source = result.provider_annotation_source.split(":", maxsplit=1)[-1]
        key = (source, result.term_id)
        current = grouped.setdefault(
            key,
            {
                "annotation_source": key[0],
                "term_id": key[1],
                "provider_specific_results": [],
                "calculation_modes": set(),
                "matched_gene_overlap": set(),
                "annotation_lineage_overlap": "unknown",
                "warnings": [],
            },
        )
        provider_specific_results = cast(list[dict[str, Any]], current["provider_specific_results"])
        calculation_modes = cast(set[str], current["calculation_modes"])
        matched_gene_overlap = cast(set[str], current["matched_gene_overlap"])
        provider_specific_results.append(result.__dict__)
        calculation_modes.add(result.calculation_mode)
        matched_gene_overlap.update(result.matched_genes)
    consensus: list[dict[str, Any]] = []
    for record in grouped.values():
        provider_specific_results = cast(list[dict[str, Any]], record["provider_specific_results"])
        modes = sorted(cast(set[str], record["calculation_modes"]))
        matched = sorted(cast(set[str], record["matched_gene_overlap"]))
        warnings: list[str] = []
        if record["annotation_source"] == "REACTOME_PATHWAY":
            warnings.append(
                "PANTHER Reactome-derived annotations are lineage-related, "
                "not independent Reactome replication."
            )
        consensus.append(
            {
                **record,
                "calculation_modes": modes,
                "matched_gene_overlap": matched,
                "provider_agreement": len(provider_specific_results) > 1,
                "provider_disagreement": False,
                "confidence_category": "contextual_enrichment",
                "warnings": warnings,
            }
        )
    return consensus
