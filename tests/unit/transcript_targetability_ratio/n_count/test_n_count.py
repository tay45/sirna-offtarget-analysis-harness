from tests.unit.transcript_targetability_ratio.helpers import compute, evidence, site, weight


def test_n_counts_only_committed_eligible_weights() -> None:
    result = compute(
        [weight("G1", "TX1", 2), weight("G1", "TX2", 2)],
        [evidence("G1", "TX1"), evidence("G1", "TX2")],
        [site("G1", "TX1", "s1")],
    )
    record = result.gene_ratios[0]
    assert record.n_total_eligible_transcripts == 2
    assert record.eligible_transcript_ids == ("TX1", "TX2")


def test_zero_eligible_gene_has_undefined_ratio() -> None:
    result = compute(
        [],
        [],
        [],
        gene_records=[
            {
                "record_id": "giso-G0",
                "canonical_gene_id": "G0",
                "eligible_transcript_count": 0,
            }
        ],
    )
    record = result.gene_ratios[0]
    assert record.n_total_eligible_transcripts == 0
    assert record.ratio_status == "undefined_zero_denominator"
    assert record.ratio_m_over_n is None


def test_duplicate_eligible_transcript_is_rejected() -> None:
    duplicate = [weight("G1", "TX1", 1), weight("G1", "TX1", 1)]
    try:
        compute(duplicate, [evidence("G1", "TX1")], [site("G1", "TX1", "s1")])
    except ValueError as exc:
        assert "duplicate eligible transcript" in str(exc)
    else:
        raise AssertionError("expected duplicate eligible transcript rejection")


def test_cross_gene_transcript_is_rejected() -> None:
    left = weight("G1", "TX1", 1)
    right = weight("G2", "TX1", 1)
    try:
        compute([left, right], [evidence("G1", "TX1")], [site("G1", "TX1", "s1")])
    except ValueError as exc:
        assert "multiple genes" in str(exc)
    else:
        raise AssertionError("expected cross-gene transcript rejection")
