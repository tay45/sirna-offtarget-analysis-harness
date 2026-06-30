from __future__ import annotations

from dataclasses import dataclass

from sirna_offtarget.config import HarnessConfig
from sirna_offtarget.expression import analyze_expression
from sirna_offtarget.io import (
    read_counts,
    read_network,
    read_regulons,
    read_sample_metadata,
    read_transcripts,
)
from sirna_offtarget.isoform import analyze_isoforms
from sirna_offtarget.models import (
    ExpressionResult,
    GeneSequenceEvidence,
    IsoformResult,
    PathwayResult,
)
from sirna_offtarget.pathway import analyze_pathways
from sirna_offtarget.sequence import map_sequence_hits


@dataclass(frozen=True)
class WorkflowState:
    sequence_hits: dict[str, GeneSequenceEvidence]
    expression_results: dict[str, ExpressionResult]
    isoform_results: dict[str, IsoformResult]
    pathway_results: dict[str, PathwayResult]


def execute_workflow(config: HarnessConfig) -> WorkflowState:
    transcripts = read_transcripts(config.sequence.transcript_fasta)
    counts = read_counts(config.expression.count_matrix)
    metadata = read_sample_metadata(config.expression.sample_metadata)
    network = read_network(config.pathway.network_file)
    regulons = read_regulons(config.pathway.regulon_file)
    sequence_hits = map_sequence_hits(
        config.sirna.guide_sequence,
        config.sirna.passenger_sequence if config.sequence.search_passenger_strand else None,
        transcripts,
        config.sequence.seed_lengths,
        config.sequence.allow_gu_wobble,
    )
    expression_results = analyze_expression(
        counts,
        metadata,
        config.expression.min_baseline_count,
        config.expression.min_expressed_replicates,
    )
    isoform_results = analyze_isoforms(
        transcripts,
        sequence_hits,
        expression_results,
        config.isoform.knockdown_efficiency_min,
        config.isoform.knockdown_efficiency_max,
    )
    pathway_results = analyze_pathways(
        config.sirna.intended_target_gene,
        expression_results,
        network,
        regulons,
        config.pathway.max_path_length,
    )
    return WorkflowState(sequence_hits, expression_results, isoform_results, pathway_results)
