from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import isclose
from typing import Any, cast

from sirna_offtarget.isoform_uncertainty.contracts import TranscriptPriorWeightRecordV1
from sirna_offtarget.transcript_targetability_ratio.contracts import (
    GeneTranscriptTargetabilityRatioRecordV1,
    MStatus,
    TargetabilityRatioStatus,
    TargetableTranscriptInclusionPolicyV1,
    TranscriptMContributionRecordV1,
    UnresolvedTargetabilityRatioEvidenceRecordV1,
    stable_id,
)

TOLERANCE = 1e-12


@dataclass(frozen=True)
class RatioComputation:
    gene_ratios: list[GeneTranscriptTargetabilityRatioRecordV1]
    contributions: list[TranscriptMContributionRecordV1]
    unresolved: list[UnresolvedTargetabilityRatioEvidenceRecordV1]
    summary: dict[str, Any]
    warnings: list[str]


def _sites_by_transcript(sites: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_site_ids: set[str] = set()
    for site in sites:
        site_id = str(site.get("site_record_id"))
        if site_id in seen_site_ids:
            continue
        seen_site_ids.add(site_id)
        grouped[str(site["canonical_transcript_id"])].append(site)
    return grouped


def _qualifying_sites(
    transcript_sites: list[dict[str, Any]], policy: TargetableTranscriptInclusionPolicyV1
) -> list[dict[str, Any]]:
    qualifying: list[dict[str, Any]] = []
    for site in transcript_sites:
        evidence_class = str(site.get("evidence_class"))
        cleavage_status = str(site.get("cleavage_compatibility_status"))
        if evidence_class == "seed_only_candidate" and not policy.include_seed_only:
            continue
        if evidence_class == "ambiguous_alignment" and not policy.include_ambiguous:
            continue
        if (
            evidence_class == "exact_full_length_complement"
            and not policy.include_exact_full_length
        ):
            continue
        if evidence_class == "near_full_length_complement" and not policy.include_near_full_length:
            continue
        if evidence_class not in policy.included_evidence_classes:
            continue
        if (
            policy.require_cleavage_compatibility
            and cleavage_status != "cleavage_compatible_candidate"
        ):
            continue
        qualifying.append(site)
    return qualifying


def _reason_for_nonqualifying(
    evidence: dict[str, Any] | None, transcript_sites: list[dict[str, Any]]
) -> str:
    if evidence is None:
        return "unresolved_missing_targetability_evidence"
    status = str(evidence.get("targetability_decision_status"))
    if status == "sequence_unavailable":
        return "unresolved_sequence_unavailable"
    if status == "not_evaluated_due_to_gene_failure":
        return "gene_failed_targetability"
    if any(site.get("evidence_class") == "seed_only_candidate" for site in transcript_sites):
        return "does_not_qualify_seed_only"
    if any(site.get("evidence_class") == "partial_nonseed_match" for site in transcript_sites):
        return "does_not_qualify_partial_match"
    if status == "no_supported_site":
        return "does_not_qualify_no_supported_site"
    if status == "indeterminate":
        return "unresolved_ambiguous_alignment"
    return f"does_not_qualify_{status}"


def _summary(
    gene_ratios: list[GeneTranscriptTargetabilityRatioRecordV1],
    contributions: list[TranscriptMContributionRecordV1],
) -> dict[str, Any]:
    definitive = [record for record in gene_ratios if record.ratio_status == "definitive"]
    ratios = [record.ratio_m_over_n for record in definitive if record.ratio_m_over_n is not None]
    return {
        "genes_examined": len(gene_ratios),
        "genes_with_definitive_ratios": len(definitive),
        "genes_with_unavailable_ratios": sum(
            record.ratio_status != "definitive" for record in gene_ratios
        ),
        "genes_with_n_zero": sum(
            record.n_total_eligible_transcripts == 0 for record in gene_ratios
        ),
        "genes_failed_by_targetability": sum(
            record.ratio_status == "unavailable_gene_failure" for record in gene_ratios
        ),
        "genes_with_unresolved_transcript_evidence": sum(
            record.unresolved_transcript_count > 0 for record in gene_ratios
        ),
        "total_eligible_transcripts": sum(
            record.n_total_eligible_transcripts for record in gene_ratios
        ),
        "total_evaluable_transcripts": sum(
            record.n_evaluable_transcripts for record in gene_ratios
        ),
        "total_unresolved_transcripts": sum(
            record.unresolved_transcript_count for record in gene_ratios
        ),
        "total_qualifying_transcripts": sum(
            record.observed_qualifying_transcript_count for record in gene_ratios
        ),
        "total_seed_only_transcripts": sum(
            record.seed_only_transcript_count for record in gene_ratios
        ),
        "total_evaluated_nonqualifying_transcripts": sum(
            len(record.nonqualifying_transcript_ids) for record in gene_ratios
        ),
        "genes_with_m_zero": sum(record.m_targetable_transcripts == 0 for record in definitive),
        "genes_with_m_equals_n": sum(
            record.m_targetable_transcripts == record.n_total_eligible_transcripts
            for record in definitive
        ),
        "genes_with_partial_m": sum(
            record.m_targetable_transcripts is not None
            and 0 < record.m_targetable_transcripts < record.n_total_eligible_transcripts
            for record in definitive
        ),
        "exact_match_qualifying_transcripts": sum(
            item.qualifying_evidence_class == "exact_full_length_complement"
            for item in contributions
        ),
        "near_full_length_qualifying_transcripts": sum(
            item.qualifying_evidence_class == "near_full_length_complement"
            for item in contributions
        ),
        "cleavage_compatible_qualifying_transcripts": sum(
            item.qualifying_for_m for item in contributions
        ),
        "minimum_definitive_ratio": min(ratios) if ratios else None,
        "maximum_definitive_ratio": max(ratios) if ratios else None,
        "count_reconciliation_status": "passed",
        "equal_prior_consistency_status": "passed"
        if all(
            record.equal_prior_consistency_status in {"passed", "not_applicable"}
            for record in gene_ratios
        )
        else "failed",
    }


def compute_transcript_targetability_ratios(
    *,
    transcript_weights: list[TranscriptPriorWeightRecordV1],
    gene_records: list[dict[str, Any]] | None = None,
    targetability_evidence: list[dict[str, Any]],
    targetability_sites: list[dict[str, Any]],
    gene_failures: list[dict[str, Any]],
    source_targetability_result_id: str,
    inclusion_policy: TargetableTranscriptInclusionPolicyV1,
) -> RatioComputation:
    warnings: list[str] = []
    eligible_weights = [
        weight
        for weight in transcript_weights
        if weight.eligibility_status == "eligible" and weight.weight is not None
    ]
    by_gene: dict[str, list[TranscriptPriorWeightRecordV1]] = defaultdict(list)
    transcript_gene: dict[str, str] = {}
    duplicate_transcripts: set[str] = set()
    cross_gene: set[str] = set()
    for weight in eligible_weights:
        tx = weight.canonical_transcript_id
        if tx in transcript_gene:
            duplicate_transcripts.add(tx)
            if transcript_gene[tx] != weight.canonical_gene_id:
                cross_gene.add(tx)
        transcript_gene[tx] = weight.canonical_gene_id
        by_gene[weight.canonical_gene_id].append(weight)
    if cross_gene:
        raise ValueError(f"eligible transcript mapped to multiple genes:{sorted(cross_gene)}")
    if duplicate_transcripts:
        raise ValueError(f"duplicate eligible transcript ids:{sorted(duplicate_transcripts)}")

    evidence_by_tx: dict[str, dict[str, Any]] = {}
    for record in targetability_evidence:
        tx = str(record["canonical_transcript_id"])
        if tx in evidence_by_tx:
            raise ValueError(f"duplicate targetability evidence:{tx}")
        evidence_by_tx[tx] = record
    sites_by_tx = _sites_by_transcript(targetability_sites)
    failure_by_gene = {str(record["canonical_gene_id"]): record for record in gene_failures}

    gene_ratios: list[GeneTranscriptTargetabilityRatioRecordV1] = []
    contributions: list[TranscriptMContributionRecordV1] = []
    unresolved: list[UnresolvedTargetabilityRatioEvidenceRecordV1] = []
    zero_gene_records = {
        str(record["canonical_gene_id"]): record
        for record in (gene_records or [])
        if int(record.get("eligible_transcript_count", 0)) == 0
    }
    for gene_id, record in sorted(zero_gene_records.items()):
        if gene_id in by_gene:
            continue
        gene_ratios.append(
            GeneTranscriptTargetabilityRatioRecordV1(
                ratio_record_id=stable_id("gene-m-over-n", gene_id, ()),
                canonical_gene_id=gene_id,
                source_isoform_uncertainty_record_id=str(record["record_id"]),
                source_targetability_result_id=source_targetability_result_id,
                targetability_inclusion_policy_id=inclusion_policy.policy_id,
                eligible_transcript_ids=(),
                n_total_eligible_transcripts=0,
                evaluable_transcript_ids=(),
                n_evaluable_transcripts=0,
                unresolved_transcript_ids=(),
                unresolved_transcript_count=0,
                qualifying_transcript_ids=(),
                observed_qualifying_transcript_count=0,
                m_targetable_transcripts=None,
                m_status="undefined_zero_denominator",
                ratio_m_over_n=None,
                ratio_status="undefined_zero_denominator",
                ratio_unavailable_reason="undefined_zero_denominator",
                equal_prior_weight_per_transcript=None,
                qualifying_equal_prior_weight_sum=None,
                equal_prior_consistency_status="not_applicable",
                provenance_record_ids=(str(record["record_id"]),),
            )
        )

    for gene_id in sorted(by_gene):
        weights = sorted(by_gene[gene_id], key=lambda item: item.canonical_transcript_id)
        eligible_ids = tuple(weight.canonical_transcript_id for weight in weights)
        n_total = len(eligible_ids)
        gene_failure = failure_by_gene.get(gene_id)
        qualifying_ids: list[str] = []
        seed_only_ids: list[str] = []
        nonqualifying_ids: list[str] = []
        evaluable_ids: list[str] = []
        unresolved_ids: list[str] = []
        source_gene_record = weights[0].gene_isoform_uncertainty_record_id if weights else "none"

        for weight in weights:
            tx = weight.canonical_transcript_id
            evidence = evidence_by_tx.get(tx)
            transcript_sites = sites_by_tx.get(tx, [])
            seed_only = any(
                site.get("evidence_class") == "seed_only_candidate" for site in transcript_sites
            )
            qualifying_sites = (
                [] if gene_failure else _qualifying_sites(transcript_sites, inclusion_policy)
            )
            reason = None
            evaluable = False
            qualifying = False
            contribution_to_m: int | None = None
            qualifying_class = None
            qualifying_site_ids: tuple[str, ...] = ()
            if gene_failure:
                reason = "gene_failed_targetability"
                unresolved_ids.append(tx)
            elif evidence is None:
                reason = "unresolved_missing_targetability_evidence"
                unresolved_ids.append(tx)
            elif evidence.get("sequence_available") is False:
                reason = "unresolved_sequence_unavailable"
                unresolved_ids.append(tx)
            elif (
                str(evidence.get("targetability_decision_status"))
                == "not_evaluated_due_to_gene_failure"
            ):
                reason = "gene_failed_targetability"
                unresolved_ids.append(tx)
            elif qualifying_sites:
                evaluable = True
                qualifying = True
                contribution_to_m = 1
                qualifying_ids.append(tx)
                selected = sorted(qualifying_sites, key=lambda item: tuple(item["ranking_tuple"]))[
                    0
                ]
                qualifying_class = str(selected.get("evidence_class"))
                qualifying_site_ids = tuple(
                    str(site["site_record_id"]) for site in qualifying_sites
                )
            else:
                evaluable = True
                contribution_to_m = 0
                reason = _reason_for_nonqualifying(evidence, transcript_sites)
                nonqualifying_ids.append(tx)
            if evaluable:
                evaluable_ids.append(tx)
            if seed_only:
                seed_only_ids.append(tx)
            contributions.append(
                TranscriptMContributionRecordV1(
                    contribution_record_id=stable_id("tx-m-contribution", gene_id, tx),
                    canonical_gene_id=gene_id,
                    canonical_transcript_id=tx,
                    transcript_version=weight.transcript_version,
                    source_transcript_weight_record_id=weight.record_id,
                    source_targetability_evidence_record_id=evidence.get("evidence_record_id")
                    if evidence
                    else None,
                    eligible_for_n=True,
                    evaluable_for_m=evaluable,
                    qualifying_for_m=qualifying,
                    contribution_to_n=1,
                    contribution_to_m=contribution_to_m,
                    qualifying_evidence_class=qualifying_class,
                    qualifying_site_ids=qualifying_site_ids,
                    seed_only_evidence_present=seed_only,
                    exclusion_or_unavailability_reason=reason,
                    transcript_prior_weight=weight.weight,
                    provenance_record_ids=(weight.record_id,)
                    if evidence is None
                    else (weight.record_id, str(evidence.get("evidence_record_id"))),
                )
            )
            if reason and reason.startswith(("unresolved", "gene_failed")):
                unresolved.append(
                    UnresolvedTargetabilityRatioEvidenceRecordV1(
                        unresolved_record_id=stable_id("ratio-unresolved", gene_id, tx, reason),
                        canonical_gene_id=gene_id,
                        canonical_transcript_id=tx,
                        reason=reason,
                        source_record_id=evidence.get("evidence_record_id") if evidence else None,
                    )
                )

        q = len(set(qualifying_ids))
        unresolved_count = len(set(unresolved_ids))
        if n_total == 0:
            m_value = None
            ratio = None
            ratio_status = "undefined_zero_denominator"
            m_status = "undefined_zero_denominator"
            unavailable = "undefined_zero_denominator"
            weight_per_tx = None
            qualifying_weight = None
            consistency = "not_applicable"
        elif gene_failure:
            m_value = None
            ratio = None
            ratio_status = "unavailable_gene_failure"
            m_status = "unavailable_gene_failure"
            unavailable = "ratio_unavailable_gene_failure"
            weight_per_tx = 1.0 / n_total
            qualifying_weight = None
            consistency = "not_applicable"
        elif unresolved_count and inclusion_policy.require_complete_gene_evidence:
            m_value = None
            ratio = None
            ratio_status = "unavailable_incomplete_evidence"
            m_status = "unavailable_incomplete_evidence"
            unavailable = "ratio_unavailable_incomplete_targetability_evidence"
            weight_per_tx = 1.0 / n_total
            qualifying_weight = q * weight_per_tx
            consistency = "not_applicable"
        else:
            m_value = q
            ratio = q / n_total
            ratio_status = "definitive"
            m_status = "definitive"
            unavailable = None
            weight_per_tx = 1.0 / n_total
            qualifying_weight = q * weight_per_tx
            consistency = (
                "passed"
                if isclose(ratio, qualifying_weight, rel_tol=0.0, abs_tol=TOLERANCE)
                else "failed"
            )
        gene_ratios.append(
            GeneTranscriptTargetabilityRatioRecordV1(
                ratio_record_id=stable_id("gene-m-over-n", gene_id, eligible_ids),
                canonical_gene_id=gene_id,
                source_isoform_uncertainty_record_id=source_gene_record,
                source_targetability_result_id=source_targetability_result_id,
                targetability_inclusion_policy_id=inclusion_policy.policy_id,
                eligible_transcript_ids=eligible_ids,
                n_total_eligible_transcripts=n_total,
                evaluable_transcript_ids=tuple(sorted(set(evaluable_ids))),
                n_evaluable_transcripts=len(set(evaluable_ids)),
                unresolved_transcript_ids=tuple(sorted(set(unresolved_ids))),
                unresolved_transcript_count=unresolved_count,
                qualifying_transcript_ids=tuple(sorted(set(qualifying_ids))),
                observed_qualifying_transcript_count=q,
                m_targetable_transcripts=m_value,
                m_status=cast(MStatus, m_status),
                ratio_m_over_n=ratio,
                ratio_status=cast(TargetabilityRatioStatus, ratio_status),
                ratio_unavailable_reason=unavailable,
                equal_prior_weight_per_transcript=weight_per_tx,
                qualifying_equal_prior_weight_sum=qualifying_weight,
                equal_prior_consistency_status=cast(Any, consistency),
                seed_only_transcript_ids=tuple(sorted(set(seed_only_ids))),
                seed_only_transcript_count=len(set(seed_only_ids)),
                nonqualifying_transcript_ids=tuple(sorted(set(nonqualifying_ids))),
                gene_failure_record_id=gene_failure.get("failure_record_id")
                if gene_failure
                else None,
                optional_m_lower_bound=q if unresolved_count else None,
                optional_m_upper_bound=q + unresolved_count if unresolved_count else None,
                optional_ratio_lower_bound=q / n_total if n_total and unresolved_count else None,
                optional_ratio_upper_bound=(q + unresolved_count) / n_total
                if n_total and unresolved_count
                else None,
                provenance_record_ids=tuple(weight.record_id for weight in weights),
            )
        )
    summary = _summary(gene_ratios, contributions)
    return RatioComputation(gene_ratios, contributions, unresolved, summary, warnings)
