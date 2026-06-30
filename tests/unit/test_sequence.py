from sirna_offtarget.models import TranscriptRecord
from sirna_offtarget.sequence import (
    map_sequence_hits,
    reverse_complement,
    target_seed_query,
)
from sirna_offtarget.sequence.complementarity import mismatch_positions


def test_reverse_complement_and_seed_orientation() -> None:
    assert reverse_complement("AAGU") == "ACTT"
    assert target_seed_query("ACGTACGTACGT", 6) == reverse_complement("CGTACG")


def test_mismatch_positions_are_guide_coordinates() -> None:
    assert mismatch_positions("AAAA", "TATT") == (3,)


def test_seed_hit_uses_guide_seed_reverse_complement() -> None:
    tx = TranscriptRecord("tx1", "G1", "CCCCCCCCTTTTTTTTAAAA", {"8": "3UTR"})
    hits = map_sequence_hits("AAAAAAAAAAAAAAAAAAAAA", None, [tx], [6, 7, 8], True)
    assert hits["G1"].best_site is not None
    assert hits["G1"].best_site.seed_match_type in {"seed8", "full_length"}


def test_passenger_strand_matching() -> None:
    tx = TranscriptRecord("tx1", "G1", "CCCCCCCCCCCCCCCCCCCCCAAAA", {"0": "CDS"})
    hits = map_sequence_hits(
        "AAAAAAAAAAAAAAAAAAAAA", "GGGGGGGGGGGGGGGGGGGGG", [tx], [6, 7, 8], True
    )
    assert hits["G1"].best_site is not None
    assert hits["G1"].best_site.strand == "passenger"


def test_preserves_overlapping_and_multi_transcript_sites() -> None:
    tx1 = TranscriptRecord("tx1", "G1", "TTTTTTTTT", {"0": "3UTR", "1": "3UTR"})
    tx2 = TranscriptRecord("tx2", "G1", "AAATTTTTTAAA", {"3": "3UTR"})
    hits = map_sequence_hits("AAAAAAAAA", None, [tx1, tx2], [6], False)
    assert hits["G1"].target_containing_transcripts == ("tx1", "tx2")
    assert hits["G1"].total_site_multiplicity > 2
