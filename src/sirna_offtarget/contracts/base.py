from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from pydantic import BaseModel, Field, model_validator

from sirna_offtarget import __version__
from sirna_offtarget.contracts.artifacts import ArtifactReference, ContractProvenance


class StageContract(BaseModel):
    expected_contract_name: ClassVar[str] = "StageContract"
    expected_schema_version: ClassVar[str] = "1"

    contract_name: str
    schema_version: str = "1"
    stage_name: str
    stage_version: str
    run_id: str
    attempt_number: int
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    software_version: str = __version__
    payload: Any
    artifacts: list[ArtifactReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    provenance: ContractProvenance = Field(default_factory=ContractProvenance)

    @model_validator(mode="after")
    def validate_contract_identity(self) -> StageContract:
        if self.contract_name != self.expected_contract_name:
            raise ValueError(f"expected {self.expected_contract_name}, got {self.contract_name}")
        if self.schema_version != self.expected_schema_version:
            raise ValueError(
                f"expected schema {self.expected_schema_version}, got {self.schema_version}"
            )
        if self.payload in ({}, [], None):
            raise ValueError("contract payload must not be empty")
        return self


def make_contract(
    contract_type: type[StageContract],
    *,
    stage_name: str,
    stage_version: str,
    run_id: str,
    attempt_number: int,
    payload: Any,
    artifacts: list[ArtifactReference],
    warnings: list[str],
    provenance: ContractProvenance | None = None,
) -> StageContract:
    return contract_type(
        contract_name=contract_type.expected_contract_name,
        schema_version=contract_type.expected_schema_version,
        stage_name=stage_name,
        stage_version=stage_version,
        run_id=run_id,
        attempt_number=attempt_number,
        payload=payload,
        artifacts=artifacts,
        warnings=warnings,
        provenance=provenance or ContractProvenance(),
    )
