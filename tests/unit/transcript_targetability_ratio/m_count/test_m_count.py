from tests.unit.transcript_targetability_ratio.helpers import compute, evidence, site, weight


def test_exact_full_length_counts_once_even_with_multiple_sites() -> None:
    result = compute(
        [weight("G1", "TX1", 1)],
        [evidence("G1", "TX1")],
        [site("G1", "TX1", "s1"), site("G1", "TX1", "s2")],
    )
    record = result.gene_ratios[0]
    contribution = result.contributions[0]
    assert record.m_targetable_transcripts == 1
    assert contribution.contribution_to_m == 1
    assert len(contribution.qualifying_site_ids) == 2


def test_near_full_length_requires_cleavage_compatibility() -> None:
    result = compute(
        [weight("G1", "TX1", 1)],
        [evidence("G1", "TX1", "indeterminate")],
        [
            site(
                "G1",
                "TX1",
                "s1",
                evidence_class="near_full_length_complement",
                cleavage_status="not_cleavage_compatible",
            )
        ],
    )
    record = result.gene_ratios[0]
    assert record.m_targetable_transcripts == 0
    assert record.ratio_m_over_n == 0


def test_seed_only_is_preserved_but_excluded_from_default_m() -> None:
    result = compute(
        [weight("G1", "TX1", 1)],
        [evidence("G1", "TX1", "seed_only_candidate_present")],
        [
            site(
                "G1",
                "TX1",
                "seed",
                evidence_class="seed_only_candidate",
                cleavage_status="not_cleavage_compatible",
            )
        ],
    )
    record = result.gene_ratios[0]
    assert record.m_targetable_transcripts == 0
    assert record.seed_only_transcript_ids == ("TX1",)
    assert (
        result.contributions[0].exclusion_or_unavailability_reason == "does_not_qualify_seed_only"
    )


def test_partial_and_ambiguous_sites_are_excluded() -> None:
    result = compute(
        [weight("G1", "TX1", 2), weight("G1", "TX2", 2)],
        [evidence("G1", "TX1", "indeterminate"), evidence("G1", "TX2", "indeterminate")],
        [
            site(
                "G1",
                "TX1",
                "partial",
                evidence_class="partial_nonseed_match",
                cleavage_status="not_cleavage_compatible",
            ),
            site(
                "G1",
                "TX2",
                "ambiguous",
                evidence_class="ambiguous_alignment",
                cleavage_status="not_cleavage_compatible",
            ),
        ],
    )
    reasons = {item.exclusion_or_unavailability_reason for item in result.contributions}
    assert "does_not_qualify_partial_match" in reasons
    assert "unresolved_ambiguous_alignment" in reasons
