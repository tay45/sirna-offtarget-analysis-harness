from __future__ import annotations

from sirna_offtarget.pathway.enrichment.policies import calculate_ora_test_values


def test_primary_test_policy_never_selects_smaller_diagnostic_value() -> None:
    values = calculate_ora_test_values(
        observed=1,
        pathway_size=7,
        test_size=1,
        background_size=20,
        contingency_table=(1, 0, 6, 13),
        primary_test="fisher_exact_greater",
        calculate_diagnostic_alternative=True,
    )
    assert values.primary_test_method == "fisher_exact_greater"
    assert values.diagnostic_test_method == "hypergeometric_upper_tail"
    assert values.primary_raw_p_value == values.diagnostic_raw_p_value


def test_hypergeometric_can_be_configured_as_primary() -> None:
    values = calculate_ora_test_values(
        observed=2,
        pathway_size=3,
        test_size=3,
        background_size=10,
        contingency_table=(2, 1, 1, 6),
        primary_test="hypergeometric_upper_tail",
        calculate_diagnostic_alternative=True,
    )
    assert values.primary_test_method == "hypergeometric_upper_tail"
    assert values.diagnostic_test_method == "fisher_exact_greater"
