from tests.unit.transcript_targetability_ratio.helpers import compute, evidence, site, weight


def test_ratio_values_zero_one_half_and_two_thirds() -> None:
    zero = compute([weight("G0", "TX0", 1)], [evidence("G0", "TX0")], []).gene_ratios[0]
    one = compute(
        [weight("G1", "TX1", 1)], [evidence("G1", "TX1")], [site("G1", "TX1", "s1")]
    ).gene_ratios[0]
    half = compute(
        [weight("G2", "TX1", 2), weight("G2", "TX2", 2)],
        [evidence("G2", "TX1"), evidence("G2", "TX2")],
        [site("G2", "TX1", "s1")],
    ).gene_ratios[0]
    two_thirds = compute(
        [weight("G3", "TX1", 3), weight("G3", "TX2", 3), weight("G3", "TX3", 3)],
        [evidence("G3", "TX1"), evidence("G3", "TX2"), evidence("G3", "TX3")],
        [site("G3", "TX1", "s1"), site("G3", "TX2", "s2")],
    ).gene_ratios[0]
    assert zero.ratio_m_over_n == 0
    assert one.ratio_m_over_n == 1
    assert half.ratio_m_over_n == 0.5
    assert two_thirds.ratio_m_over_n == 2 / 3
