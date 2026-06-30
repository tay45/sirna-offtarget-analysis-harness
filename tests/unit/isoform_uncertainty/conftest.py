from __future__ import annotations

import pytest

from sirna_offtarget.isoform_uncertainty.contracts import (
    TranscriptAnnotationRecordV1,
    TranscriptAnnotationSnapshotV1,
    TranscriptSetPolicyV1,
)


@pytest.fixture
def snapshot() -> TranscriptAnnotationSnapshotV1:
    return TranscriptAnnotationSnapshotV1(
        provider="GENCODE",
        release="v44",
        organism="human",
        assembly="GRCh38",
        transcript_identifier_namespace="ensembl_transcript",
        gene_identifier_namespace="hgnc",
        source_file_checksum="sha256:annotation",
        snapshot_id="gencode-v44-GRCh38-human",
        verification_status="verified",
    )


@pytest.fixture
def policy() -> TranscriptSetPolicyV1:
    return TranscriptSetPolicyV1()


def tx(
    transcript_id: str,
    *,
    gene: str = "HGNC:11998",
    original_gene: str = "TP53",
    biotype: str = "protein_coding",
    sequence: str | None = "ENST.fa:TP53",
    organism: str = "human",
    assembly: str = "GRCh38",
    release: str = "v44",
    version: str | None = "1",
    deprecated: bool = False,
    alternative_contig: bool = False,
    canonical_transcript_id: str | None = None,
    ambiguous: bool = False,
) -> TranscriptAnnotationRecordV1:
    return TranscriptAnnotationRecordV1(
        original_gene_id=original_gene,
        canonical_gene_id=gene,
        original_transcript_id=f"{transcript_id}.{version}" if version else transcript_id,
        canonical_transcript_id=canonical_transcript_id or transcript_id,
        transcript_version=version,
        transcript_biotype=biotype,
        organism=organism,
        assembly=assembly,
        annotation_release=release,
        sequence_reference=sequence,
        deprecated=deprecated,
        alternative_contig=alternative_contig,
        ambiguous_transcript_mapping=ambiguous,
    )
