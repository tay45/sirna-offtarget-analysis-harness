from __future__ import annotations


class ContractError(RuntimeError):
    """Base class for typed stage contract failures."""


class ContractCompatibilityError(ContractError):
    """Raised when a dependency contract has the wrong name or schema version."""


class ArtifactIntegrityError(ContractError):
    """Raised when a referenced artifact is missing or has the wrong checksum."""


class ContractValidationError(ContractError):
    """Raised when a contract payload does not validate."""
