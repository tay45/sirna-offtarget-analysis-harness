from __future__ import annotations

from typing import Any

from sirna_offtarget.contracts.exceptions import (
    ArtifactIntegrityError as ContractArtifactIntegrityError,
)
from sirna_offtarget.contracts.exceptions import ContractCompatibilityError as ContractError
from sirna_offtarget.execution.exceptions import (
    ArtifactIntegrityError,
    ConfigurationError,
    ContractCompatibilityError,
    DependencyError,
    ExternalToolError,
    InputSchemaError,
    InterruptedRunError,
    MissingInputError,
    NetworkError,
    OutputValidationError,
    ProviderError,
    ResourceError,
    ScientificValidationError,
    TimeoutExecutionError,
)


def classify_failure(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, KeyboardInterrupt | InterruptedRunError):
        category = "interrupted"
        recoverable = True
    elif isinstance(exc, ConfigurationError | ValueError):
        category = "configuration_error"
        recoverable = True
    elif isinstance(exc, FileNotFoundError | MissingInputError):
        category = "missing_input"
        recoverable = True
    elif isinstance(exc, InputSchemaError):
        category = "schema_error"
        recoverable = True
    elif isinstance(exc, DependencyError | ContractError | ContractCompatibilityError):
        category = "dependency_error"
        recoverable = True
    elif isinstance(exc, ContractArtifactIntegrityError | ArtifactIntegrityError):
        category = "output_validation_error"
        recoverable = True
    elif isinstance(exc, ExternalToolError):
        category = "external_tool_error"
        recoverable = True
    elif isinstance(exc, NetworkError):
        category = "network_error"
        recoverable = True
    elif isinstance(exc, ProviderError):
        category = "provider_error"
        recoverable = True
    elif isinstance(exc, TimeoutExecutionError | TimeoutError):
        category = "timeout"
        recoverable = True
    elif isinstance(exc, ResourceError):
        category = "resource_error"
        recoverable = True
    elif isinstance(exc, ScientificValidationError):
        category = "scientific_validation_error"
        recoverable = True
    elif isinstance(exc, OutputValidationError):
        category = "output_validation_error"
        recoverable = True
    else:
        category = "unknown"
        recoverable = True
    return {"failure_category": category, "recoverable": recoverable}
