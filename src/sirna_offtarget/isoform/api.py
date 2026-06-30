from __future__ import annotations

from sirna_offtarget.expression.downstream import IsoformGeneEffectInputV1
from sirna_offtarget.isoform.back_calculation import inferred_targetable_fraction
from sirna_offtarget.isoform.equal_prior import equal_transcript_prior
from sirna_offtarget.models import (
    ExpressionResult,
    GeneSequenceEvidence,
    IsoformResult,
    TranscriptRecord,
)


def analyze_isoforms(
    transcripts: list[TranscriptRecord],
    sequence_hits: dict[str, GeneSequenceEvidence],
    expression_results: dict[str, ExpressionResult],
    efficiency_min: float,
    efficiency_max: float,
) -> dict[str, IsoformResult]:
    results: dict[str, IsoformResult] = {}
    genes = sorted({record.gene for record in transcripts})
    for gene in genes:
        seen: set[str] = set()
        eligible: list[str] = []
        excluded: list[tuple[str, str]] = []
        for record in transcripts:
            if record.gene != gene:
                continue
            if not record.sequence:
                excluded.append((record.transcript_id, "missing_sequence"))
            elif record.transcript_id in seen:
                excluded.append((record.transcript_id, "duplicate_transcript_identifier"))
            else:
                eligible.append(record.transcript_id)
                seen.add(record.transcript_id)
        evidence = sequence_hits.get(gene)
        with_site = sorted(
            set(evidence.target_containing_transcripts if evidence else ()) & set(eligible)
        )
        without_site = [item for item in eligible if item not in with_site]
        prior = equal_transcript_prior(len(with_site), len(eligible)) if eligible else 0.0
        expr = expression_results.get(gene)
        f_min = f_max = None
        warning = None
        if expr and with_site:
            f_min, f_max, warning = inferred_targetable_fraction(
                expr.normalized_control_expression,
                expr.normalized_treated_expression,
                efficiency_min,
                efficiency_max,
            )
        results[gene] = IsoformResult(
            gene=gene,
            all_transcripts=tuple(
                record.transcript_id for record in transcripts if record.gene == gene
            ),
            eligible_transcripts=tuple(eligible),
            excluded_transcripts=tuple(excluded),
            transcripts_with_site=tuple(with_site),
            transcripts_without_site=tuple(without_site),
            total_transcript_count=len(eligible),
            target_site_transcript_count=len(with_site),
            equal_transcript_prior=round(prior, 6),
            inferred_fraction_min=f_min,
            inferred_fraction_max=f_max,
            warning=warning,
        )
    return results


def analyze_isoforms_from_gene_effect_inputs(
    transcripts: list[TranscriptRecord],
    sequence_hits: dict[str, GeneSequenceEvidence],
    expression_inputs: dict[str, IsoformGeneEffectInputV1],
    efficiency_min: float,
    efficiency_max: float,
) -> dict[str, IsoformResult]:
    results: dict[str, IsoformResult] = {}
    genes = sorted({record.gene for record in transcripts})
    for gene in genes:
        seen: set[str] = set()
        eligible: list[str] = []
        excluded: list[tuple[str, str]] = []
        for record in transcripts:
            if record.gene != gene:
                continue
            if not record.sequence:
                excluded.append((record.transcript_id, "missing_sequence"))
            elif record.transcript_id in seen:
                excluded.append((record.transcript_id, "duplicate_transcript_identifier"))
            else:
                eligible.append(record.transcript_id)
                seen.add(record.transcript_id)
        evidence = sequence_hits.get(gene)
        with_site = sorted(
            set(evidence.target_containing_transcripts if evidence else ()) & set(eligible)
        )
        without_site = [item for item in eligible if item not in with_site]
        prior = equal_transcript_prior(len(with_site), len(eligible)) if eligible else 0.0
        expr = expression_inputs.get(gene)
        f_min = f_max = None
        warning = None
        if (
            expr
            and with_site
            and expr.control_abundance_summary is not None
            and expr.treatment_abundance_summary is not None
        ):
            f_min, f_max, warning = inferred_targetable_fraction(
                expr.control_abundance_summary,
                expr.treatment_abundance_summary,
                efficiency_min,
                efficiency_max,
            )
        elif expr and with_site:
            warning = "condition-specific abundance unavailable; targetable fraction not inferred"
        results[gene] = IsoformResult(
            gene=gene,
            all_transcripts=tuple(
                record.transcript_id for record in transcripts if record.gene == gene
            ),
            eligible_transcripts=tuple(eligible),
            excluded_transcripts=tuple(excluded),
            transcripts_with_site=tuple(with_site),
            transcripts_without_site=tuple(without_site),
            total_transcript_count=len(eligible),
            target_site_transcript_count=len(with_site),
            equal_transcript_prior=round(prior, 6),
            inferred_fraction_min=f_min,
            inferred_fraction_max=f_max,
            warning=warning,
        )
    return results


__all__ = [
    "analyze_isoforms",
    "analyze_isoforms_from_gene_effect_inputs",
    "equal_transcript_prior",
    "inferred_targetable_fraction",
]
