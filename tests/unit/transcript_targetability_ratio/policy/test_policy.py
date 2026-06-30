import pytest

from sirna_offtarget.transcript_targetability_ratio.contracts import (
    TargetableTranscriptInclusionPolicyV1,
)


def test_unsupported_seed_only_policy_fails_validation() -> None:
    with pytest.raises(ValueError, match="seed-only"):
        TargetableTranscriptInclusionPolicyV1(include_seed_only=True)


def test_unsupported_incomplete_gene_policy_fails_validation() -> None:
    with pytest.raises(ValueError, match="complete gene"):
        TargetableTranscriptInclusionPolicyV1(require_complete_gene_evidence=False)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"strand_role": "passenger"}, "guide"),
        ({"include_ambiguous": True}, "ambiguous"),
        ({"require_cleavage_compatibility": False}, "cleavage-compatible"),
        ({"require_verified_sequence": False}, "verified sequence"),
        ({"require_verified_site": False}, "verified sequence"),
        ({"multiple_site_counting_rule": "count_site"}, "count_transcript_once"),
        ({"transcript_counting_rule": "alias"}, "unique_canonical_transcript"),
    ],
)
def test_unsupported_policy_fields_fail_validation(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        TargetableTranscriptInclusionPolicyV1(**kwargs)
