from __future__ import annotations

from collections import defaultdict

from sirna_offtarget.models import (
    GeneSequenceEvidence,
    TranscriptRecord,
    TranscriptSequenceEvidence,
)
from sirna_offtarget.sequence.complementarity import (
    guide_seed,
    reverse_complement,
    scan_transcript,
    target_seed_query,
)


def map_sequence_hits(
    guide_sequence: str,
    passenger_sequence: str | None,
    transcripts: list[TranscriptRecord],
    seed_lengths: list[int],
    allow_gu_wobble: bool,
) -> dict[str, GeneSequenceEvidence]:
    by_gene: dict[str, list[TranscriptSequenceEvidence]] = defaultdict(list)
    for transcript in transcripts:
        transcript_sites = []
        for strand, sequence in (("guide", guide_sequence), ("passenger", passenger_sequence)):
            if sequence is None:
                continue
            transcript_sites.extend(
                scan_transcript(sequence, strand, transcript, seed_lengths, allow_gu_wobble)
            )
        if transcript_sites:
            by_gene[transcript.gene].append(
                TranscriptSequenceEvidence(
                    gene=transcript.gene,
                    transcript=transcript.transcript_id,
                    binding_sites=tuple(transcript_sites),
                )
            )
    return {
        gene: GeneSequenceEvidence(gene=gene, transcripts=tuple(transcript_evidence))
        for gene, transcript_evidence in by_gene.items()
    }


__all__ = ["guide_seed", "map_sequence_hits", "reverse_complement", "target_seed_query"]
