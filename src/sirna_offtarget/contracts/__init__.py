from __future__ import annotations

from sirna_offtarget.contracts.artifacts import ArtifactReference
from sirna_offtarget.contracts.base import StageContract, make_contract
from sirna_offtarget.contracts.registry import CONTRACT_REGISTRY, STAGE_CONTRACTS
from sirna_offtarget.contracts.stage_results import (
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
from sirna_offtarget.contracts.validation import (
    validate_contract_artifacts,
    validate_contract_file,
)

__all__ = [
    "ArtifactReference",
    "CONTRACT_REGISTRY",
    "STAGE_CONTRACTS",
    "ExpressionAnalysisResultV1",
    "ExpressionAnalysisResultV2",
    "IdentifierMappingResultV1",
    "IsoformAnalysisResultV1",
    "IsoformUncertaintyResultV1",
    "MechanisticNetworkResultV1",
    "MechanisticNetworkResultV2",
    "PathwayEnrichmentResultV1",
    "PathwayEnrichmentResultV2",
    "PreparedInputsResultV1",
    "SequenceAnalysisResultV1",
    "StageContract",
    "TranscriptTargetabilityRatioResultV1",
    "TranscriptTargetabilityResultV1",
    "ValidationResultV1",
    "make_contract",
    "validate_contract_artifacts",
    "validate_contract_file",
]
