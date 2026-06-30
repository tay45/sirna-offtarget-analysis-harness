from tests.portfolio.test_portfolio_result_table_matches_outputs import (
    test_portfolio_result_table_matches_outputs,
)


def test_public_example_result_table_matches_canonical_outputs(tmp_path):
    test_portfolio_result_table_matches_outputs(tmp_path)
