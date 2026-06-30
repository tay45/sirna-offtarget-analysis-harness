from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sirna_offtarget.config import HarnessConfig


@dataclass(frozen=True)
class ConsumedDependencyRecord:
    dependency_stage: str
    dependency_type: str
    contract_name: str
    contract_version: str
    contract_sha256: str
    artifacts_consumed: list[str]
    payload_fields_consumed: list[str]


@dataclass(frozen=True)
class RunContext:
    config: HarnessConfig
    original_config: dict[str, Any]
    resolved_config: dict[str, Any]
    config_path: Path
    run_dir: Path
    run_id: str
    invocation: tuple[str, ...]
    offline: bool = False
    dependency_consumption: list[ConsumedDependencyRecord] = field(default_factory=list)

    @property
    def stages_dir(self) -> Path:
        return self.run_dir / "stages"

    def record_dependency_consumption(
        self,
        *,
        dependency_stage: str,
        dependency_type: str,
        contract_name: str,
        contract_version: str,
        contract_sha256: str,
        artifacts: list[str] | None = None,
        payload_fields: list[str] | None = None,
    ) -> None:
        self.dependency_consumption.append(
            ConsumedDependencyRecord(
                dependency_stage=dependency_stage,
                dependency_type=dependency_type,
                contract_name=contract_name,
                contract_version=contract_version,
                contract_sha256=contract_sha256,
                artifacts_consumed=artifacts or [],
                payload_fields_consumed=payload_fields or [],
            )
        )


@dataclass(frozen=True)
class StageExecutionResult:
    output_artifacts: list[Path]
    metrics: dict[str, Any]
    warnings: list[str]
    contract_name: str
    contract_version: str = "1"
    payload: Any | None = None


@dataclass(frozen=True)
class ReuseDecision:
    action: str
    explanation: str
    current_fingerprint: str
    previous_fingerprint: str | None
    dependency_status: str
