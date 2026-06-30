from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class Window(ConfigModel):
    min: float | None = None
    max: float | None = None


class ProjectConfig(ConfigModel):
    name: str
    organism: str
    genome_build: str
    random_seed: int = 42


class SirnaConfig(ConfigModel):
    guide_sequence: str
    passenger_sequence: str | None = None
    intended_target_gene: str
    intended_target_transcript: str | None = None


class ExperimentConfig(ConfigModel):
    cell_type: str
    delivery_method: str
    concentration_nM: float
    sampling_time_hours: float
    early_window_hours: Window
    intermediate_window_hours: Window
    late_window_hours: Window


class ExpressionConfig(ConfigModel):
    backend: str | None = None
    count_matrix: Path
    sample_metadata: Path
    precomputed_table: Path | None = None
    input_mode: str = "raw_counts"
    value_scale: str = "raw_count"
    normalization_method: str = "median_ratio"
    differential_method: str = "backend_default"
    effect_scale: str = "log2_fold_change"
    tested_column: str | None = None
    filter_status_column: str | None = None
    low_count_column: str | None = None
    model_status_column: str | None = None
    exclusion_reason_column: str | None = None
    test_statistic_column: str | None = None
    confidence_interval_lower_column: str | None = None
    confidence_interval_upper_column: str | None = None
    control_abundance_column: str | None = None
    treatment_abundance_column: str | None = None
    source_row_id_column: str | None = None
    analysis_software: str = "unspecified"
    analysis_software_version: str = "unspecified"
    shrinkage_method: str = "unspecified"
    shrinkage_status: str = "unspecified"
    identifier_cache_dir: Path | None = None
    identifier_snapshot_id: str | None = None
    require_verified_identifier_snapshot: bool = False
    invalid_row_policy: str = "preserve_with_status"
    identifier_ambiguity_policy: str = "exclude"
    gene_id_namespace: str = "symbol"
    condition_column: str = "condition"
    sample_column: str = "sample"
    control_condition: str = "control"
    treatment_condition: str = "treated"
    contrast_id: str = "treated_vs_control"
    multiple_testing_method: str = "benjamini_hochberg"
    duplicate_gene_policy: str = "reject"
    gene_column: str = "gene"
    base_mean_column: str = "baseMean"
    log2_fold_change_column: str = "log2FoldChange"
    shrunken_log2_fold_change_column: str = "lfcShrink"
    standard_error_column: str = "lfcSE"
    p_value_column: str = "pvalue"
    adjusted_p_value_column: str = "padj"
    design_formula: str = "~ condition"
    min_baseline_count: float = 10
    min_expressed_replicates: int = 2
    padj_threshold: float = 0.05
    absolute_log2_fold_change: float = 0.5
    lfc_shrinkage: bool = True


class SequenceConfig(ConfigModel):
    transcript_fasta: Path
    annotation_gtf: Path
    search_passenger_strand: bool = True
    seed_lengths: list[int] = Field(default_factory=lambda: [6, 7, 8])
    allow_gu_wobble: bool = True


class IsoformConfig(ConfigModel):
    equal_transcript_prior: bool = True
    knockdown_efficiency_min: float = 0.50
    knockdown_efficiency_max: float = 1.00
    knockdown_efficiency_step: float = 0.05

    @model_validator(mode="after")
    def validate_interval(self) -> IsoformConfig:
        if self.knockdown_efficiency_min <= 0:
            raise ValueError("knockdown_efficiency_min must be positive")
        if self.knockdown_efficiency_max < self.knockdown_efficiency_min:
            raise ValueError("knockdown_efficiency_max must be >= min")
        return self


class IsoformUncertaintyConfig(ConfigModel):
    enabled: bool = False
    annotation_cache_dir: Path | None = None
    annotation_snapshot_id: str | None = None
    require_verified_annotation_snapshot: bool = True
    require_verified_identifier_snapshot: bool = True
    identifier_snapshot_id: str | None = None
    identifier_snapshot_checksum: str | None = None
    transcript_records_artifact: str = "transcripts.jsonl"
    manifest_artifact: str = "manifest.json"
    external_proportions_file: Path | None = None
    invalid_proportion_behavior: str = "fail_gene"
    missing_transcript_behavior: str = "require_complete_coverage"
    duplicate_row_behavior: str = "fail_gene"
    unknown_transcript_behavior: str = "fail_gene"
    wrong_gene_mapping_behavior: str = "fail_gene"
    small_rounding_tolerance: float = 1e-6
    material_sum_tolerance: float = 0.05
    allow_renormalization: bool = False
    include_protein_coding: bool = True
    include_retained_intron: bool = True
    include_nonsense_mediated_decay: bool = True
    include_processed_transcript: bool = True
    include_noncoding: bool = True
    include_pseudogene: bool = False
    include_readthrough: bool = False
    allow_alternative_contigs: bool = False
    allow_deprecated_transcripts: bool = False
    require_sequence_reference: bool = True
    allow_unresolved_gene_mapping: bool = False
    allowed_transcript_support_levels: list[str] | None = None


class TranscriptTargetabilityConfig(ConfigModel):
    enabled: bool = False
    transcript_sequence_cache_dir: Path | None = None
    transcript_sequence_snapshot_id: str | None = None
    require_verified_transcript_sequence_snapshot: bool = True
    manifest_artifact: str = "manifest.json"
    sirna_id: str = "configured_sirna"
    reagent_name: str = "configured_sirna"
    guide_orientation: str = "guide_5p_to_3p"
    search_passenger: bool = False
    intended_target_missing_policy: str = "fail_stage"
    intended_target_required: bool = True
    intended_target_transcript_ids_required: bool = False
    intended_target_failure_behavior: str = "fail_stage"
    intended_target_gene_only_behavior: str = "preserve_uncertainty"
    intended_target_accepted_evidence_classes: list[str] = Field(
        default_factory=lambda: ["exact_full_length_complement", "near_full_length_complement"]
    )
    missing_transcript_sequence_mode: str = "record_unavailable_and_continue"
    guide_length_min: int = 19
    guide_length_max: int = 23
    maximum_total_mismatches: int = 2
    maximum_seed_mismatches: int = 0
    maximum_central_mismatches: int = 0
    maximum_nonseed_mismatches: int = 2
    seed_start: int = 2
    seed_end: int = 8
    exact_seed_required: bool = True
    allowed_seed_mismatches: int = 0
    minimum_total_paired_bases: int = 7
    seed_maximum_total_mismatches: int = 14
    supplementary_pairing_requirement: str = "record_only"
    transcript_region_restrictions: list[str] = Field(default_factory=list)


class TranscriptTargetabilityRatioConfig(ConfigModel):
    enabled: bool = True
    policy_id: str = "targetable-transcript-inclusion-v1-cleavage-compatible"
    include_seed_only: bool = False
    include_ambiguous: bool = False
    require_complete_gene_evidence: bool = True
    require_cleavage_compatibility: bool = True
    require_verified_sequence: bool = True
    require_verified_site: bool = True


class PathwayConfig(ConfigModel):
    network_file: Path
    regulon_file: Path
    mode: str = "local_snapshot"
    cache_dir: Path | None = Field(default=None, alias="cache_directory")
    offline: bool = True
    providers: list[str] = Field(default_factory=lambda: ["synthetic"])
    synthetic_mode: bool = True
    max_path_length: int = 4
    maximum_paths_per_candidate: int = 25
    maximum_total_paths: int | None = None
    shortest_paths_only: bool = False
    require_directed_for_causal_claim: bool = True
    require_signed_for_direction_claim: bool = True
    trace_signed_paths: bool = True
    trace_unsigned_paths: bool = True
    trace_contextual_paths: bool = True
    allow_unsigned_context_paths: bool = True
    require_direction_consistency: bool = True
    enable_legacy_path_comparison: bool = False


class ProviderSelectionConfig(ConfigModel):
    mode: str = "disabled"
    required: bool = False
    snapshot_id: str = "latest_verified"
    endpoint: str | None = None
    timeout_seconds: float = 20.0
    retry_count: int = 2
    expected_content_type: str | None = None


class OutputConfig(ConfigModel):
    directory: Path
    html_report: bool = True
    json_report: bool = True
    csv_tables: bool = True
    save_intermediate_results: bool = True


class ExecutionConfig(ConfigModel):
    resume: bool = True
    fail_fast: bool = True
    preserve_failed_attempts: bool = True
    verify_output_checksums: bool = True
    verify_dependency_hashes: bool = True
    atomic_stage_commit: bool = True
    max_stage_attempts: int = 3
    lock_timeout_seconds: int = 300
    stale_lock_timeout_seconds: int = 3600
    inject_failure_stage: str | None = None
    inject_interrupt_stage: str | None = None


class ReportingConfig(ConfigModel):
    stage_reports: bool = True
    run_dashboard: bool = True


class HarnessConfig(ConfigModel):
    schema_version: str = "1"
    project: ProjectConfig
    sirna: SirnaConfig
    experiment: ExperimentConfig
    expression: ExpressionConfig
    sequence: SequenceConfig
    isoform: IsoformConfig
    isoform_uncertainty: IsoformUncertaintyConfig = Field(default_factory=IsoformUncertaintyConfig)
    transcript_targetability: TranscriptTargetabilityConfig = Field(
        default_factory=TranscriptTargetabilityConfig
    )
    transcript_targetability_ratio: TranscriptTargetabilityRatioConfig = Field(
        default_factory=TranscriptTargetabilityRatioConfig
    )
    pathway: PathwayConfig
    providers: dict[str, ProviderSelectionConfig] = Field(default_factory=dict)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    outputs: OutputConfig
    config_path: Path | None = None

    def resolve_paths(self, base_dir: Path) -> HarnessConfig:
        data = self.model_copy(deep=True)
        for section_name in (
            "expression",
            "sequence",
            "pathway",
            "isoform_uncertainty",
            "transcript_targetability",
            "transcript_targetability_ratio",
        ):
            section = getattr(data, section_name)
            for key, value in section:
                if isinstance(value, Path) and not value.is_absolute():
                    setattr(section, key, (base_dir / value).resolve())
                elif isinstance(value, Path):
                    setattr(section, key, value.resolve())
        if not data.outputs.directory.is_absolute():
            data.outputs.directory = (base_dir / data.outputs.directory).resolve()
        else:
            data.outputs.directory = data.outputs.directory.resolve()
        data.config_path = base_dir
        return data


def load_config(path: Path) -> HarnessConfig:
    raw = yaml.safe_load(path.read_text()) or {}
    return HarnessConfig.model_validate(raw).resolve_paths(path.parent)
