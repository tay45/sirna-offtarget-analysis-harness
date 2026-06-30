from __future__ import annotations

from dataclasses import asdict, dataclass

from sirna_offtarget.config import ExpressionConfig


@dataclass(frozen=True)
class ExpressionExecutionSupportRecord:
    input_mode: str
    backend: str
    execution_support_level: str
    validation_supported: bool
    execution_supported: bool
    production_supported: bool
    inferential_statistics_supported: bool
    descriptive_effect_supported: bool
    required_backend: str
    backend_bundled_or_external: str
    limitations: tuple[str, ...]
    failure_behavior: str


def expression_execution_support(config: ExpressionConfig) -> ExpressionExecutionSupportRecord:
    backend = (config.backend or "unset").lower().replace("-", "_")
    if config.input_mode == "normalized_matrix":
        return ExpressionExecutionSupportRecord(
            input_mode=config.input_mode,
            backend=backend,
            execution_support_level="validation_only",
            validation_supported=True,
            execution_supported=False,
            production_supported=False,
            inferential_statistics_supported=False,
            descriptive_effect_supported=False,
            required_backend="not_implemented",
            backend_bundled_or_external="none",
            limitations=("normalized-matrix execution is not implemented in this pass",),
            failure_behavior="normalized_matrix_execution_not_supported",
        )
    if backend in {"synthetic", "synthetic_demo"}:
        return ExpressionExecutionSupportRecord(
            input_mode=config.input_mode,
            backend=backend,
            execution_support_level="demonstration_only",
            validation_supported=True,
            execution_supported=True,
            production_supported=False,
            inferential_statistics_supported=False,
            descriptive_effect_supported=True,
            required_backend="synthetic_demo",
            backend_bundled_or_external="bundled_demo",
            limitations=("heuristic effect scores are not production p-values",),
            failure_behavior="executes only as demonstration output",
        )
    if backend == "precomputed":
        return ExpressionExecutionSupportRecord(
            input_mode="precomputed_de",
            backend=backend,
            execution_support_level="validated_import",
            validation_supported=True,
            execution_supported=True,
            production_supported=True,
            inferential_statistics_supported=True,
            descriptive_effect_supported=True,
            required_backend="precomputed",
            backend_bundled_or_external="external_results_imported",
            limitations=("external normalization and model fitting are trusted, not rerun",),
            failure_behavior="fails on schema or value validation errors",
        )
    if backend in {"pydeseq2", "deseq2_r"}:
        return ExpressionExecutionSupportRecord(
            input_mode=config.input_mode,
            backend=backend,
            execution_support_level="unsupported",
            validation_supported=True,
            execution_supported=False,
            production_supported=False,
            inferential_statistics_supported=False,
            descriptive_effect_supported=False,
            required_backend=backend,
            backend_bundled_or_external="external_unavailable",
            limitations=("raw-count production adapter is not bundled or executable",),
            failure_behavior="raw_count_production_backend_unavailable",
        )
    return ExpressionExecutionSupportRecord(
        input_mode=config.input_mode,
        backend=backend,
        execution_support_level="unsupported",
        validation_supported=False,
        execution_supported=False,
        production_supported=False,
        inferential_statistics_supported=False,
        descriptive_effect_supported=False,
        required_backend="unsupported",
        backend_bundled_or_external="none",
        limitations=("unsupported expression backend",),
        failure_behavior="unsupported_expression_backend",
    )


def support_matrix_as_dict(config: ExpressionConfig) -> dict[str, object]:
    return asdict(expression_execution_support(config))
