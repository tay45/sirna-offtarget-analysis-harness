from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from sirna_offtarget.expression.contracts_v2 import NormalizedGeneEffectRecordV2
from sirna_offtarget.models import Direction

SHRUNKEN_EFFECT_SOURCES = frozenset(
    {
        "imported_shrunken_log2fc",
        "backend_shrunken_log2fc",
    }
)


@dataclass(frozen=True)
class DownstreamGeneEffectBaseV1:
    schema_version: str
    input_record_id: str
    source_expression_v2_record_id: str
    original_gene_id: str
    canonical_gene_id: str
    approved_symbol: str | None
    contrast_id: str
    canonical_log2_fold_change: float
    canonical_effect_source: str
    numerical_direction: str
    tested_status: str
    filter_status: str
    low_count_status: str
    model_status: str
    statistical_support_status: str
    adjusted_p_value: float | None
    adjusted_pvalue_status: str
    identifier_resolution_id: str
    warnings: tuple[str, ...]

    @property
    def gene(self) -> str:
        return self.approved_symbol or self.original_gene_id

    @property
    def direction(self) -> Direction:
        return _direction_from_view(self.numerical_direction)

    @property
    def low_count_flag(self) -> bool:
        return self.low_count_status == "low_count"


@dataclass(frozen=True)
class PathwayGeneEffectInputV1(DownstreamGeneEffectBaseV1):
    pass


@dataclass(frozen=True)
class NetworkGeneEffectInputV1(DownstreamGeneEffectBaseV1):
    pass


@dataclass(frozen=True)
class DownstreamGeneEffectExclusion:
    source_expression_v2_record_id: str
    original_gene_id: str
    canonical_gene_id: str | None
    consumer_name: str
    exclusion_reason: str
    missing_required_fields: tuple[str, ...]
    warning: str


@dataclass(frozen=True)
class DownstreamExpressionViewV1:
    view_name: str
    records: tuple[DownstreamGeneEffectBaseV1, ...]
    exclusions: tuple[DownstreamGeneEffectExclusion, ...]

    @property
    def by_approved_symbol(self) -> Mapping[str, DownstreamGeneEffectBaseV1]:
        return MappingProxyType({record.gene: record for record in self.records})


@dataclass(frozen=True)
class IsoformGeneEffectInputV1:
    schema_version: str
    input_record_id: str
    source_expression_v2_record_id: str
    canonical_gene_id: str
    approved_symbol: str | None
    original_gene_id: str
    contrast_id: str
    canonical_log2_fold_change: float
    canonical_effect_source: str
    shrunken_log2_fold_change: float | None
    numerical_direction: str
    tested_status: str
    filter_status: str
    low_count_status: str
    model_status: str
    statistical_support_status: str
    adjusted_p_value: float | None
    adjusted_pvalue_status: str
    control_abundance_summary: float | None
    treatment_abundance_summary: float | None
    abundance_status: str
    mean_abundance_summary: float | None
    replicate_consistency: float | None
    replicate_consistency_status: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class IsoformGeneEffectInputExclusionV1:
    source_expression_v2_record_id: str
    original_gene_id: str
    canonical_gene_id: str | None
    exclusion_reason: str
    missing_required_fields: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class IsoformGeneEffectInputViewV1:
    view_name: str
    schema_version: str
    records: tuple[IsoformGeneEffectInputV1, ...]
    exclusions: tuple[IsoformGeneEffectInputExclusionV1, ...]
    summary: dict[str, int]

    @property
    def by_gene(self) -> Mapping[str, IsoformGeneEffectInputV1]:
        return MappingProxyType(
            {record.approved_symbol or record.original_gene_id: record for record in self.records}
        )


def normalized_gene_effect_v2_to_downstream_view(
    records: list[NormalizedGeneEffectRecordV2],
) -> DownstreamExpressionViewV1:
    included: list[DownstreamGeneEffectBaseV1] = []
    excluded: list[DownstreamGeneEffectExclusion] = []
    for record in records:
        reason, missing = _base_exclusion(record)
        if reason is not None:
            excluded.append(
                DownstreamGeneEffectExclusion(
                    source_expression_v2_record_id=record.record_id,
                    original_gene_id=record.original_gene_id,
                    canonical_gene_id=record.canonical_gene_id,
                    consumer_name="shared_base",
                    exclusion_reason=reason,
                    missing_required_fields=missing,
                    warning=f"V2 record excluded from downstream view: {reason}",
                )
            )
            continue
        included.append(_base_input(record))
    return DownstreamExpressionViewV1(
        view_name="DownstreamGeneEffectViewV1",
        records=tuple(included),
        exclusions=tuple(excluded),
    )


def normalized_gene_effect_v2_to_pathway_input(
    records: list[NormalizedGeneEffectRecordV2],
) -> DownstreamExpressionViewV1:
    return _consumer_view(records, "PathwayGeneEffectInputV1", PathwayGeneEffectInputV1)


def normalized_gene_effect_v2_to_network_input(
    records: list[NormalizedGeneEffectRecordV2],
) -> DownstreamExpressionViewV1:
    return _consumer_view(records, "NetworkGeneEffectInputV1", NetworkGeneEffectInputV1)


def normalized_gene_effect_v2_to_isoform_input(
    records: list[NormalizedGeneEffectRecordV2],
) -> IsoformGeneEffectInputViewV1:
    included: list[IsoformGeneEffectInputV1] = []
    excluded: list[IsoformGeneEffectInputExclusionV1] = []
    for record in records:
        reason, missing = _isoform_exclusion(record)
        if reason is not None:
            excluded.append(
                IsoformGeneEffectInputExclusionV1(
                    source_expression_v2_record_id=record.record_id,
                    original_gene_id=record.original_gene_id,
                    canonical_gene_id=record.canonical_gene_id,
                    exclusion_reason=reason,
                    missing_required_fields=missing,
                    warnings=record.warnings,
                )
            )
            continue
        canonical_gene_id, canonical_log2_fold_change = _required_canonical_effect(record)
        warnings = list(record.warnings)
        if record.adjusted_p_value is None:
            warnings.append("adjusted p-value unavailable; preserved as null")
        if record.control_abundance_summary is None or record.treatment_abundance_summary is None:
            warnings.append("condition-specific abundance unavailable; not reconstructed")
        included.append(
            IsoformGeneEffectInputV1(
                schema_version="1",
                input_record_id=f"isoform-input:{record.record_id}",
                source_expression_v2_record_id=record.record_id,
                canonical_gene_id=canonical_gene_id,
                approved_symbol=record.approved_symbol,
                original_gene_id=record.original_gene_id,
                contrast_id=record.contrast_id,
                canonical_log2_fold_change=canonical_log2_fold_change,
                canonical_effect_source=record.canonical_effect_source,
                shrunken_log2_fold_change=_shrunken_value_for_isoform(record),
                numerical_direction=record.numerical_direction,
                tested_status=record.tested_status,
                filter_status=record.filter_status,
                low_count_status=record.low_count_status,
                model_status=record.model_status,
                statistical_support_status=record.statistical_support_status,
                adjusted_p_value=record.adjusted_p_value,
                adjusted_pvalue_status=record.adjusted_pvalue_status,
                control_abundance_summary=record.control_abundance_summary,
                treatment_abundance_summary=record.treatment_abundance_summary,
                abundance_status=_abundance_status(record),
                mean_abundance_summary=record.mean_abundance_summary,
                replicate_consistency=None,
                replicate_consistency_status="unavailable",
                warnings=tuple(warnings),
            )
        )
    return IsoformGeneEffectInputViewV1(
        view_name="IsoformGeneEffectInputV1",
        schema_version="1",
        records=tuple(included),
        exclusions=tuple(excluded),
        summary=_isoform_summary(records, included, excluded),
    )


def _base_exclusion(record: NormalizedGeneEffectRecordV2) -> tuple[str | None, tuple[str, ...]]:
    missing: list[str] = []
    if record.canonical_gene_id is None:
        missing.append("canonical_gene_id")
        return "canonical_gene_id_unavailable", tuple(missing)
    if record.identifier_ambiguity_status == "ambiguous":
        return "ambiguous_identifier_not_allowed", tuple(missing)
    if record.canonical_log2_fold_change is None:
        missing.append("canonical_log2_fold_change")
        return "canonical_effect_unavailable", tuple(missing)
    if record.model_status == "model_not_estimable":
        return "model_not_estimable", tuple(missing)
    if record.model_status == "model_failure":
        return "model_failure", tuple(missing)
    if record.filter_status == "unsupported":
        return "unsupported_expression_state", tuple(missing)
    return None, tuple(missing)


def _base_input(record: NormalizedGeneEffectRecordV2) -> DownstreamGeneEffectBaseV1:
    canonical_gene_id, canonical_log2_fold_change = _required_canonical_effect(record)
    return DownstreamGeneEffectBaseV1(
        schema_version="1",
        input_record_id=f"downstream-input:{record.record_id}",
        source_expression_v2_record_id=record.record_id,
        original_gene_id=record.original_gene_id,
        canonical_gene_id=canonical_gene_id,
        approved_symbol=record.approved_symbol,
        contrast_id=record.contrast_id,
        canonical_log2_fold_change=canonical_log2_fold_change,
        canonical_effect_source=record.canonical_effect_source,
        numerical_direction=record.numerical_direction,
        tested_status=record.tested_status,
        filter_status=record.filter_status,
        low_count_status=record.low_count_status,
        model_status=record.model_status,
        statistical_support_status=record.statistical_support_status,
        adjusted_p_value=record.adjusted_p_value,
        adjusted_pvalue_status=record.adjusted_pvalue_status,
        identifier_resolution_id=record.identifier_resolution_id,
        warnings=record.warnings,
    )


def _required_canonical_effect(record: NormalizedGeneEffectRecordV2) -> tuple[str, float]:
    if record.canonical_gene_id is None or record.canonical_log2_fold_change is None:
        raise ValueError(
            "downstream expression views require canonical_gene_id and canonical_log2_fold_change"
        )
    return record.canonical_gene_id, record.canonical_log2_fold_change


def _consumer_view(
    records: list[NormalizedGeneEffectRecordV2],
    view_name: str,
    view_type: type[PathwayGeneEffectInputV1] | type[NetworkGeneEffectInputV1],
) -> DownstreamExpressionViewV1:
    included: list[DownstreamGeneEffectBaseV1] = []
    excluded: list[DownstreamGeneEffectExclusion] = []
    for record in records:
        reason, missing = _base_exclusion(record)
        if reason is not None:
            excluded.append(_consumer_exclusion(record, view_name, reason, missing))
            continue
        included.append(view_type(**_base_input(record).__dict__))
    return DownstreamExpressionViewV1(
        view_name=view_name,
        records=tuple(included),
        exclusions=tuple(excluded),
    )


def _consumer_exclusion(
    record: NormalizedGeneEffectRecordV2,
    consumer_name: str,
    reason: str,
    missing: tuple[str, ...],
) -> DownstreamGeneEffectExclusion:
    return DownstreamGeneEffectExclusion(
        source_expression_v2_record_id=record.record_id,
        original_gene_id=record.original_gene_id,
        canonical_gene_id=record.canonical_gene_id,
        consumer_name=consumer_name,
        exclusion_reason=reason,
        missing_required_fields=missing,
        warning=f"V2 record excluded from {consumer_name}: {reason}",
    )


def _isoform_exclusion(
    record: NormalizedGeneEffectRecordV2,
) -> tuple[str | None, tuple[str, ...]]:
    missing: list[str] = []
    if record.canonical_gene_id is None:
        missing.append("canonical_gene_id")
        return "canonical_gene_id_unavailable", tuple(missing)
    if record.identifier_ambiguity_status == "ambiguous":
        return "ambiguous_identifier_not_allowed", tuple(missing)
    if record.canonical_log2_fold_change is None:
        missing.append("canonical_log2_fold_change")
        return "canonical_effect_unavailable", tuple(missing)
    if record.model_status == "model_failure":
        return "model_failure", tuple(missing)
    if record.filter_status == "unsupported":
        return "unsupported_expression_state", tuple(missing)
    return None, tuple(missing)


def _shrunken_value_for_isoform(record: NormalizedGeneEffectRecordV2) -> float | None:
    return _shrunken_value_for_record(record)


def _shrunken_value_for_record(record: NormalizedGeneEffectRecordV2) -> float | None:
    if record.canonical_effect_source in SHRUNKEN_EFFECT_SOURCES:
        return record.canonical_log2_fold_change
    return None


def _abundance_status(record: NormalizedGeneEffectRecordV2) -> str:
    if (
        record.control_abundance_summary is not None
        and record.treatment_abundance_summary is not None
    ):
        return "condition_summaries_available"
    return "condition_summaries_unavailable"


def _isoform_summary(
    records: list[NormalizedGeneEffectRecordV2],
    included: list[IsoformGeneEffectInputV1],
    excluded: list[IsoformGeneEffectInputExclusionV1],
) -> dict[str, int]:
    return {
        "total_v2_records_examined": len(records),
        "included_records": len(included),
        "excluded_records": len(excluded),
        "missing_canonical_gene_id": sum(
            1 for record in records if record.canonical_gene_id is None
        ),
        "missing_canonical_effect": sum(
            1 for record in records if record.canonical_log2_fold_change is None
        ),
        "not_estimable_records": sum(
            1 for record in records if record.model_status == "not_estimable"
        ),
        "model_failure_records": sum(
            1 for record in records if record.model_status == "model_failure"
        ),
        "missing_adjusted_p_value_but_included": sum(
            1 for record in included if record.adjusted_p_value is None
        ),
        "missing_condition_summaries_but_included": sum(
            1
            for record in included
            if record.control_abundance_summary is None
            or record.treatment_abundance_summary is None
        ),
        "replicate_consistency_unavailable_but_included": sum(
            1 for record in included if record.replicate_consistency is None
        ),
        "unshrunken_effects_included": sum(
            1 for record in included if record.shrunken_log2_fold_change is None
        ),
        "genuinely_shrunken_effects_included": sum(
            1 for record in included if record.shrunken_log2_fold_change is not None
        ),
    }


def _direction_from_view(direction: str) -> Direction:
    if direction == "decreased":
        return Direction.DOWN
    if direction == "increased":
        return Direction.UP
    return Direction.UNCHANGED
