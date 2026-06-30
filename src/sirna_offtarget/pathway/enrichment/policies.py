from __future__ import annotations

from dataclasses import dataclass

from sirna_offtarget.pathway.enrichment.statistics import (
    fisher_exact_greater,
    hypergeometric_tail,
)

ORA_TEST_POLICY_VERSION = "ora-test-policy-v2"
CORRECTION_POLICY_VERSION = "correction-family-policy-v2"
DEFAULT_CORRECTION_SCOPE = (
    "provider",
    "annotation_dataset",
    "gene_set_id",
    "expression_direction",
    "calculation_mode",
)


@dataclass(frozen=True)
class OraTestValues:
    primary_test_method: str
    primary_raw_p_value: float
    diagnostic_test_method: str | None
    diagnostic_raw_p_value: float | None
    test_policy_version: str = ORA_TEST_POLICY_VERSION


def calculate_ora_test_values(
    *,
    observed: int,
    pathway_size: int,
    test_size: int,
    background_size: int,
    contingency_table: tuple[int, int, int, int],
    primary_test: str = "fisher_exact_greater",
    calculate_diagnostic_alternative: bool = True,
) -> OraTestValues:
    """Calculate the configured primary ORA p-value without automatic minimum selection."""
    a, b, c, d = contingency_table
    fisher = fisher_exact_greater(a, b, c, d)
    hyper = hypergeometric_tail(observed, pathway_size, test_size, background_size)
    if primary_test == "fisher_exact_greater":
        primary = fisher
        diagnostic_method = "hypergeometric_upper_tail"
        diagnostic = hyper
    elif primary_test == "hypergeometric_upper_tail":
        primary = hyper
        diagnostic_method = "fisher_exact_greater"
        diagnostic = fisher
    else:
        msg = f"unsupported local ORA primary_test: {primary_test}"
        raise ValueError(msg)
    return OraTestValues(
        primary_test_method=primary_test,
        primary_raw_p_value=primary,
        diagnostic_test_method=diagnostic_method if calculate_diagnostic_alternative else None,
        diagnostic_raw_p_value=diagnostic if calculate_diagnostic_alternative else None,
    )


def correction_family_id(
    *,
    provider: str,
    annotation_dataset: str,
    gene_set_id: str,
    expression_direction: str,
    calculation_mode: str,
) -> str:
    parts = {
        "provider": provider,
        "annotation_dataset": annotation_dataset,
        "gene_set_id": gene_set_id,
        "expression_direction": expression_direction,
        "calculation_mode": calculation_mode,
    }
    return "|".join(f"{key}={parts[key]}" for key in DEFAULT_CORRECTION_SCOPE)
