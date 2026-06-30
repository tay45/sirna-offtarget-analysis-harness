from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnrichmentTerm:
    provider: str
    pathway_id: str
    pathway_name: str
    expression_direction: str
    observed_count: int
    expected_count: float
    enrichment_ratio: float
    raw_p_value: float
    fdr: float
    matched_genes: tuple[str, ...]
    background_size: int
    test_list_size: int
    database_release: str
    contingency_table: tuple[int, int, int, int] = (0, 0, 0, 0)
    adjusted_p_value: float | None = None
    primary_test_method: str = "fisher_exact_greater"
    primary_raw_p_value: float | None = None
    diagnostic_test_method: str | None = None
    diagnostic_raw_p_value: float | None = None
    test_policy_version: str = "ora-test-policy-v2"
    correction_family_id: str = ""
    correction_family_size: int = 0
    correction_method: str = "benjamini_hochberg"
    correction_policy_version: str = "correction-family-policy-v2"


@dataclass(frozen=True)
class GeneSetDefinitionV1:
    gene_set_id: str
    name: str
    source_stage: str
    direction: str
    genes: tuple[str, ...]
    selection_rule: str
    thresholds: dict[str, float | bool | str]
    excluded_genes: tuple[str, ...]
    exclusion_reasons: dict[str, str]
    checksum: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class BackgroundUniverseV1:
    background_id: str
    mode: str
    genes: tuple[str, ...]
    initial_gene_count: int
    final_gene_count: int
    expression_tested_count: int
    detectability_pass_count: int
    valid_identifier_count: int
    provider_annotation_eligible_count: int
    exclusion_counts: dict[str, int]
    exclusion_records: tuple[dict[str, str], ...]
    thresholds: dict[str, float | bool | str]
    checksum: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class PathwayMembershipRecordV1:
    provider: str
    annotation_source: str
    term_id: str
    term_name: str
    member_entity_id: str
    member_gene_id: str | None
    organism: str
    hierarchy_parent_ids: tuple[str, ...]
    evidence_type: str
    provider_version: str | None
    snapshot_id: str
    membership_type: str = "complete_annotation_membership"
    membership_completeness: str = "complete"
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocalEnrichmentResultV1:
    provider_annotation_source: str
    term_id: str
    term_name: str
    gene_set_id: str
    observed_count: int
    expected_count: float
    fold_enrichment: float
    raw_p_value: float
    adjusted_p_value: float
    contingency_table: tuple[int, int, int, int]
    matched_genes: tuple[str, ...]
    pathway_size: int
    test_list_size: int
    background_size: int
    background_id: str
    annotation_snapshot_id: str
    statistics_method: str
    primary_test_method: str = "fisher_exact_greater"
    primary_raw_p_value: float = 1.0
    diagnostic_test_method: str | None = "hypergeometric_upper_tail"
    diagnostic_raw_p_value: float | None = None
    test_policy_version: str = "ora-test-policy-v2"
    correction_family_id: str = ""
    correction_family_size: int = 0
    correction_method: str = "benjamini_hochberg"
    correction_policy_version: str = "correction-family-policy-v2"
    annotation_membership_completeness: str = "complete"
    calculation_mode: str = "locally_calculated_from_provider_annotations"
    warnings: tuple[str, ...] = ()
