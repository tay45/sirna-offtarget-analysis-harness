from __future__ import annotations

from sirna_offtarget.contracts.base import StageContract
from sirna_offtarget.contracts.stage_results import (
    ExpectedDirectEffectResultV1,
    ExpressionAnalysisResultV1,
    ExpressionAnalysisResultV2,
    IdentifierMappingResultV1,
    IsoformAnalysisResultV1,
    IsoformUncertaintyResultV1,
    MechanisticNetworkResultV1,
    MechanisticNetworkResultV2,
    PathwayEnrichmentResultV1,
    PathwayEnrichmentResultV2,
    PreparedInputsResultV1,
    SequenceAnalysisResultV1,
    TranscriptTargetabilityRatioResultV1,
    TranscriptTargetabilityResultV1,
    ValidationResultV1,
)

CONTRACT_REGISTRY: dict[str, type[StageContract]] = {
    cls.expected_contract_name: cls
    for cls in (
        ValidationResultV1,
        PreparedInputsResultV1,
        IdentifierMappingResultV1,
        SequenceAnalysisResultV1,
        ExpressionAnalysisResultV1,
        ExpressionAnalysisResultV2,
        ExpectedDirectEffectResultV1,
        IsoformAnalysisResultV1,
        IsoformUncertaintyResultV1,
        TranscriptTargetabilityResultV1,
        TranscriptTargetabilityRatioResultV1,
        PathwayEnrichmentResultV1,
        PathwayEnrichmentResultV2,
        MechanisticNetworkResultV1,
        MechanisticNetworkResultV2,
    )
}

STAGE_CONTRACTS: dict[str, type[StageContract]] = {
    "validate": ValidationResultV1,
    "prepare_inputs": PreparedInputsResultV1,
    "map_identifiers": IdentifierMappingResultV1,
    "sequence_analysis": SequenceAnalysisResultV1,
    "expression_analysis": ExpressionAnalysisResultV2,
    "isoform_uncertainty": IsoformUncertaintyResultV1,
    "transcript_targetability": TranscriptTargetabilityResultV1,
    "transcript_targetability_ratio": TranscriptTargetabilityRatioResultV1,
    "expected_direct_effect": ExpectedDirectEffectResultV1,
}
