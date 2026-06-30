from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Direction(StrEnum):
    DOWN = "down"
    UP = "up"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class TranscriptRecord:
    transcript_id: str
    gene: str
    sequence: str
    regions: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceMetric:
    value: float | None
    backend: str
    backend_version: str
    calculation_status: str
    is_heuristic: bool
    missing_value_reason: str | None = None


@dataclass(frozen=True)
class BindingSiteEvidence:
    gene: str
    transcript: str
    strand_source: str
    match_type: str
    seed_class: str
    mismatch_count: int
    mismatch_positions: tuple[int, ...]
    transcript_start: int
    transcript_end: int
    region: str
    site_sequence: str
    guide_coordinates: tuple[int, int]
    target_window_coordinates: tuple[int, int]
    genomic_coordinates: tuple[str, int, int] | None
    complementarity_score: float
    full_length_complementarity: bool
    central_pairing: bool
    cleavage_compatible: bool
    supplementary_pairing: bool
    gu_wobble_count: int
    accessibility_evidence: EvidenceMetric
    opening_energy_evidence: EvidenceMetric
    duplex_energy_evidence: EvidenceMetric
    provenance: dict[str, str] = field(default_factory=dict)

    @property
    def strand(self) -> str:
        return self.strand_source

    @property
    def seed_match_type(self) -> str:
        return self.seed_class if self.seed_class != "none" else self.match_type

    @property
    def site_start(self) -> int:
        return self.transcript_start

    @property
    def site_multiplicity(self) -> int:
        return 1

    @property
    def accessibility(self) -> float | None:
        return self.accessibility_evidence.value

    @property
    def opening_energy(self) -> float | None:
        return self.opening_energy_evidence.value

    @property
    def duplex_energy(self) -> float | None:
        return self.duplex_energy_evidence.value


@dataclass(frozen=True)
class TranscriptSequenceEvidence:
    gene: str
    transcript: str
    binding_sites: tuple[BindingSiteEvidence, ...]

    @property
    def best_site(self) -> BindingSiteEvidence | None:
        return max(self.binding_sites, key=lambda site: site.complementarity_score, default=None)

    @property
    def site_multiplicity(self) -> int:
        return len(self.binding_sites)


@dataclass(frozen=True)
class GeneSequenceEvidence:
    gene: str
    transcripts: tuple[TranscriptSequenceEvidence, ...]

    @property
    def all_sites(self) -> tuple[BindingSiteEvidence, ...]:
        return tuple(site for tx in self.transcripts for site in tx.binding_sites)

    @property
    def best_site(self) -> BindingSiteEvidence | None:
        return max(self.all_sites, key=lambda site: site.complementarity_score, default=None)

    @property
    def target_containing_transcripts(self) -> tuple[str, ...]:
        return tuple(sorted({site.transcript for site in self.all_sites}))

    @property
    def guide_supported_transcripts(self) -> tuple[str, ...]:
        return tuple(
            sorted({site.transcript for site in self.all_sites if site.strand_source == "guide"})
        )

    @property
    def passenger_supported_transcripts(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {site.transcript for site in self.all_sites if site.strand_source == "passenger"}
            )
        )

    @property
    def total_site_multiplicity(self) -> int:
        return len(self.all_sites)


SequenceHit = BindingSiteEvidence


@dataclass(frozen=True)
class ExpressionResult:
    gene: str
    baseline_expression: float
    normalized_control_expression: float
    normalized_treated_expression: float
    log2_fold_change: float
    shrunken_log2_fold_change: float
    adjusted_p_value: float
    replicate_consistency: float
    direction: Direction
    low_count_flag: bool
    backend_name: str = "synthetic_demo"
    backend_version: str = "internal"
    design_formula: str = "~ condition"
    shrinkage_status: str = "heuristic"
    standard_error: float | None = None
    raw_p_value: float | None = None
    p_value_status: str = "synthetic_effect_score_not_statistical_p_value"
    demonstration_only: bool = True


@dataclass(frozen=True)
class IsoformResult:
    gene: str
    all_transcripts: tuple[str, ...]
    eligible_transcripts: tuple[str, ...]
    excluded_transcripts: tuple[tuple[str, str], ...]
    transcripts_with_site: tuple[str, ...]
    transcripts_without_site: tuple[str, ...]
    total_transcript_count: int
    target_site_transcript_count: int
    equal_transcript_prior: float
    inferred_fraction_min: float | None
    inferred_fraction_max: float | None
    warning: str | None


@dataclass(frozen=True)
class PathwayResult:
    gene: str
    target_pathway_distance: int | None
    direction_consistency: bool | None
    pathway_coherence: float
    regulon_evidence: float
    stress_signature_evidence: float
    paths: tuple[str, ...] = ()
    shortest_signed_path: tuple[str, ...] = ()
    shortest_unsigned_supported_path: tuple[str, ...] = ()
    composed_path_sign: int | None = None
    expected_candidate_direction: Direction | None = None
    conflicting_paths: bool = False
    supporting_path_count: int = 0
    contradictory_path_count: int = 0
    provider_sources: tuple[str, ...] = ()
    evidence_limitations: tuple[str, ...] = ()
