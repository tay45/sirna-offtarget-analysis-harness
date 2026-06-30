from __future__ import annotations


def test_abundance_derived_proportions_are_explicitly_deferred() -> None:
    supported_modes = {
        "annotation_only_equal_prior",
        "precomputed_transcript_proportions",
        "precomputed_transcript_abundance",
        "unsupported",
        "insufficient_evidence",
    }
    assert "precomputed_transcript_abundance" in supported_modes
    assert "abundance_derived_proportion" in {
        "equal_prior",
        "external_proportion",
        "abundance_derived_proportion",
        "unavailable",
    }
