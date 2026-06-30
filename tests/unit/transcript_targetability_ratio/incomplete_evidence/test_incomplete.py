from tests.unit.transcript_targetability_ratio.helpers import compute, evidence, site, weight


def test_unavailable_sequence_does_not_become_zero_m() -> None:
    record = compute(
        [weight("G1", "TX1", 2), weight("G1", "TX2", 2)],
        [evidence("G1", "TX1"), evidence("G1", "TX2", "sequence_unavailable")],
        [site("G1", "TX1", "s1")],
    ).gene_ratios[0]
    assert record.observed_qualifying_transcript_count == 1
    assert record.m_targetable_transcripts is None
    assert record.ratio_status == "unavailable_incomplete_evidence"
    assert record.optional_m_lower_bound == 1
    assert record.optional_m_upper_bound == 2


def test_failed_gene_has_no_definitive_ratio() -> None:
    record = compute(
        [weight("G1", "TX1", 2), weight("G1", "TX2", 2)],
        [evidence("G1", "TX1", "not_evaluated_due_to_gene_failure")],
        [site("G1", "TX1", "s1")],
        gene_failures=[
            {
                "failure_record_id": "fail-G1",
                "canonical_gene_id": "G1",
                "triggering_transcript_ids": ("TX2",),
            }
        ],
    ).gene_ratios[0]
    assert record.m_targetable_transcripts is None
    assert record.ratio_status == "unavailable_gene_failure"
    assert record.gene_failure_record_id == "fail-G1"
