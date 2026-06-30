from __future__ import annotations

from sirna_offtarget.models import GeneSequenceEvidence, TranscriptRecord


def site_coverage(
    gene: str, transcripts: list[TranscriptRecord], hits: dict[str, GeneSequenceEvidence]
) -> tuple[list[str], list[str]]:
    gene_transcripts = [item.transcript_id for item in transcripts if item.gene == gene]
    evidence = hits.get(gene)
    with_site = list(evidence.target_containing_transcripts) if evidence else []
    without_site = [item for item in gene_transcripts if item not in with_site]
    return with_site, without_site
