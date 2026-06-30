from __future__ import annotations

from sirna_offtarget.contracts.exceptions import ArtifactIntegrityError, ContractCompatibilityError
from sirna_offtarget.execution.exceptions import (
    ConfigurationError,
    ExternalToolError,
    NetworkError,
    OutputValidationError,
    ResourceError,
    ScientificValidationError,
    TimeoutExecutionError,
)
from sirna_offtarget.execution.failure import classify_failure


def test_failure_classification_categories() -> None:
    cases = [
        (ConfigurationError("bad"), "configuration_error"),
        (FileNotFoundError("missing"), "missing_input"),
        (ContractCompatibilityError("contract"), "dependency_error"),
        (ArtifactIntegrityError("artifact"), "output_validation_error"),
        (ExternalToolError("tool"), "external_tool_error"),
        (NetworkError("network"), "network_error"),
        (TimeoutExecutionError("timeout"), "timeout"),
        (ResourceError("resource"), "resource_error"),
        (ScientificValidationError("science"), "scientific_validation_error"),
        (OutputValidationError("output"), "output_validation_error"),
        (RuntimeError("unknown"), "unknown"),
    ]
    for exc, category in cases:
        assert classify_failure(exc)["failure_category"] == category
