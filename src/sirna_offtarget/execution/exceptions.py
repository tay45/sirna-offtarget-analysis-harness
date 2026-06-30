from __future__ import annotations


class ExecutionError(RuntimeError):
    """Base class for staged execution failures."""


class ConfigurationError(ExecutionError):
    """Raised for invalid execution or project configuration."""


class MissingInputError(ExecutionError):
    """Raised when a required raw input is absent."""


class InputSchemaError(ExecutionError):
    """Raised when an input file does not satisfy its expected schema."""


class DependencyError(ExecutionError):
    """Raised when a stage dependency is missing, invalid, or circular."""


class ContractCompatibilityError(DependencyError):
    """Raised when an upstream contract is incompatible."""


class ArtifactIntegrityError(ExecutionError):
    """Raised when an artifact checksum or existence check fails."""


class ExternalToolError(ExecutionError):
    """Raised when an external tool returns an error."""


class ProviderError(ExecutionError):
    """Raised when a configured provider fails."""


class NetworkError(ProviderError):
    """Raised when a network operation fails."""


class TimeoutExecutionError(ExecutionError):
    """Raised when a stage exceeds its timeout."""


class ResourceError(ExecutionError):
    """Raised when memory, disk, or similar resources are unavailable."""


class ScientificValidationError(ExecutionError):
    """Raised when scientific output validation fails."""


class OutputValidationError(ExecutionError):
    """Raised when stage outputs fail validation."""


class StageValidationError(ExecutionError):
    """Raised when stage inputs or outputs do not satisfy their contract."""


class LockError(ExecutionError):
    """Raised when a run or stage lock cannot be acquired safely."""


class InvalidStageError(ExecutionError):
    """Raised when a requested stage name is unknown."""


class InterruptedRunError(ExecutionError):
    """Raised when a stage is interrupted."""


class UnknownExecutionError(ExecutionError):
    """Raised when a failure cannot be classified more specifically."""
