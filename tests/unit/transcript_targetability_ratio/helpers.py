from __future__ import annotations

from sirna_offtarget.isoform_uncertainty.contracts import TranscriptPriorWeightRecordV1
from sirna_offtarget.transcript_targetability_ratio.contracts import (
    TargetableTranscriptInclusionPolicyV1,
)
from sirna_offtarget.transcript_targetability_ratio.core import (
    compute_transcript_targetability_ratios,
)


def weight(gene: str, tx: str, n: int, version: str | None = None) -> TranscriptPriorWeightRecordV1:
    return TranscriptPriorWeightRecordV1(
        record_id=f"w-{gene}-{tx}",
        gene_isoform_uncertainty_record_id=f"giso-{gene}",
        original_gene_id=gene,
        canonical_gene_id=gene,
        original_transcript_id=tx,
        canonical_transcript_id=tx,
        transcript_version=version,
        transcript_biotype="protein_coding",
        annotation_status="annotation_eligible",
        eligibility_status="eligible",
        exclusion_reason=None,
        weight=1 / n,
        weight_type="equal_prior",
        weight_source="equal_transcript_prior",
        weight_evidence_status="assumption_due_to_unresolved_isoform_abundance",
        source_annotation_release="synthetic",
    )


def evidence(gene: str, tx: str, status: str = "cleavage_candidate_present") -> dict[str, object]:
    return {
        "evidence_record_id": f"ev-{gene}-{tx}",
        "sirna_id": "sirna",
        "canonical_gene_id": gene,
        "canonical_transcript_id": tx,
        "source_isoform_uncertainty_record_id": f"giso-{gene}",
        "source_transcript_weight_record_id": f"w-{gene}-{tx}",
        "transcript_prior_weight": 1.0,
        "sequence_available": status != "sequence_unavailable",
        "targetability_decision_status": status,
        "evidence_status": status,
        "site_record_ids": (),
    }


def site(
    gene: str,
    tx: str,
    site_id: str,
    evidence_class: str = "exact_full_length_complement",
    cleavage_status: str = "cleavage_compatible_candidate",
) -> dict[str, object]:
    return {
        "site_record_id": site_id,
        "canonical_gene_id": gene,
        "canonical_transcript_id": tx,
        "evidence_class": evidence_class,
        "cleavage_compatibility_status": cleavage_status,
        "ranking_tuple": (0, 0, 0, 0, 0),
    }


def compute(
    weights: list[TranscriptPriorWeightRecordV1],
    evidence_records: list[dict[str, object]],
    sites: list[dict[str, object]],
    gene_failures: list[dict[str, object]] | None = None,
    gene_records: list[dict[str, object]] | None = None,
):
    return compute_transcript_targetability_ratios(
        transcript_weights=weights,
        gene_records=gene_records,
        targetability_evidence=evidence_records,
        targetability_sites=sites,
        gene_failures=gene_failures or [],
        source_targetability_result_id="tt-result",
        inclusion_policy=TargetableTranscriptInclusionPolicyV1(),
    )
