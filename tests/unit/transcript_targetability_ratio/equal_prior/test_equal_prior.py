from tests.unit.transcript_targetability_ratio.helpers import compute, evidence, site, weight


def test_equal_prior_weight_sum_matches_m_over_n() -> None:
    record = compute(
        [weight("G1", "TX1", 2), weight("G1", "TX2", 2)],
        [evidence("G1", "TX1"), evidence("G1", "TX2")],
        [site("G1", "TX1", "s1")],
    ).gene_ratios[0]
    assert record.equal_prior_weight_per_transcript == 0.5
    assert record.qualifying_equal_prior_weight_sum == record.ratio_m_over_n
    assert record.equal_prior_consistency_status == "passed"
