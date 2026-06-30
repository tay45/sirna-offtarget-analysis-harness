from __future__ import annotations

from sirna_offtarget.models import BindingSiteEvidence, EvidenceMetric, TranscriptRecord

_RC = str.maketrans("ACGTUacgtu", "TGCAAtgcaa")


def reverse_complement(sequence: str) -> str:
    return sequence.translate(_RC)[::-1].upper().replace("U", "T")


def guide_seed(strand_sequence: str, length: int) -> str:
    """Return guide-coordinate seed positions 2..length+1 from the 5' guide."""
    return strand_sequence.upper().replace("U", "T")[1 : 1 + length]


def target_seed_query(strand_sequence: str, length: int) -> str:
    return reverse_complement(guide_seed(strand_sequence, length))


def mismatch_positions(
    guide_sequence: str,
    target_window: str,
    allow_gu_wobble: bool = False,
) -> tuple[int, ...]:
    """Return mismatch positions in 1-based guide coordinates."""
    target_as_guide_orientation = reverse_complement(target_window)
    mismatches: list[int] = []
    for idx, (guide_base, target_base) in enumerate(
        zip(
            guide_sequence.upper().replace("U", "T"),
            target_as_guide_orientation,
            strict=False,
        ),
        start=1,
    ):
        wobble = allow_gu_wobble and {
            guide_base.replace("T", "U"),
            target_base.replace("T", "U"),
        } == {"G", "U"}
        if guide_base != target_base and not wobble:
            mismatches.append(idx)
    return tuple(mismatches)


def gu_wobble_count(guide_sequence: str, target_window: str) -> int:
    target_as_guide_orientation = reverse_complement(target_window)
    return sum(
        1
        for guide_base, target_base in zip(
            guide_sequence.upper().replace("U", "T"),
            target_as_guide_orientation,
            strict=False,
        )
        if guide_base != target_base
        and {guide_base.replace("T", "U"), target_base.replace("T", "U")} == {"G", "U"}
    )


def scan_transcript(
    strand_sequence: str,
    strand_name: str,
    transcript: TranscriptRecord,
    seed_lengths: list[int],
    allow_gu_wobble: bool,
) -> list[BindingSiteEvidence]:
    sequence = transcript.sequence.upper().replace("U", "T")
    hits: list[BindingSiteEvidence] = []
    hits.extend(
        _scan_full_or_partial(strand_sequence, strand_name, transcript, sequence, allow_gu_wobble)
    )
    for length in sorted(seed_lengths, reverse=True):
        hits.extend(_scan_seed(strand_sequence, strand_name, transcript, sequence, length))
    return hits


def _scan_full_or_partial(
    strand_sequence: str,
    strand_name: str,
    transcript: TranscriptRecord,
    sequence: str,
    allow_gu_wobble: bool,
) -> list[BindingSiteEvidence]:
    hits: list[BindingSiteEvidence] = []
    window = len(strand_sequence)
    for start in range(0, max(len(sequence) - window + 1, 0)):
        target_window = sequence[start : start + window]
        mismatches = mismatch_positions(strand_sequence, target_window, allow_gu_wobble)
        if len(mismatches) <= 4:
            hits.append(
                _make_site(
                    transcript=transcript,
                    strand=strand_name,
                    start=start,
                    end=start + window,
                    guide_start=1,
                    guide_end=window,
                    mismatches=mismatches,
                    strand_sequence=strand_sequence,
                    target_window=target_window,
                    match_type="full_length" if not mismatches else "partial_full_length",
                    seed_class="none",
                )
            )
    return hits


def _scan_seed(
    strand_sequence: str,
    strand_name: str,
    transcript: TranscriptRecord,
    sequence: str,
    length: int,
) -> list[BindingSiteEvidence]:
    seed_query = target_seed_query(strand_sequence, length)
    hits: list[BindingSiteEvidence] = []
    for start in range(0, max(len(sequence) - length + 1, 0)):
        target_window = sequence[start : start + length]
        if target_window == seed_query:
            hits.append(
                _make_site(
                    transcript=transcript,
                    strand=strand_name,
                    start=start,
                    end=start + length,
                    guide_start=2,
                    guide_end=1 + length,
                    mismatches=(),
                    strand_sequence=strand_sequence,
                    target_window=target_window,
                    match_type="seed",
                    seed_class=f"seed{length}",
                )
            )
    return hits


def _make_site(
    transcript: TranscriptRecord,
    strand: str,
    start: int,
    end: int,
    guide_start: int,
    guide_end: int,
    mismatches: tuple[int, ...],
    strand_sequence: str,
    target_window: str,
    match_type: str,
    seed_class: str,
) -> BindingSiteEvidence:
    central = not any(9 <= pos <= 12 for pos in mismatches)
    full_length = match_type == "full_length"
    region = transcript.regions.get(str(start), "unknown")
    score = _complementarity_score(match_type, seed_class, len(mismatches), central)
    return BindingSiteEvidence(
        gene=transcript.gene,
        transcript=transcript.transcript_id,
        strand_source=strand,
        match_type=match_type,
        seed_class=seed_class,
        mismatch_count=len(mismatches),
        mismatch_positions=mismatches,
        transcript_start=start,
        transcript_end=end,
        region=region,
        site_sequence=target_window,
        guide_coordinates=(guide_start, guide_end),
        target_window_coordinates=(0, end - start),
        genomic_coordinates=None,
        complementarity_score=score,
        full_length_complementarity=full_length,
        central_pairing=central,
        cleavage_compatible=len(mismatches) <= 2 and central and match_type != "seed",
        supplementary_pairing=_has_supplementary_pairing(strand_sequence, target_window),
        gu_wobble_count=gu_wobble_count(strand_sequence[: len(target_window)], target_window),
        accessibility_evidence=_heuristic_metric(
            0.75 if region == "3UTR" else 0.55, "accessibility_proxy"
        ),
        opening_energy_evidence=_heuristic_metric(None, "heuristic_opening_score"),
        duplex_energy_evidence=_heuristic_metric(None, "heuristic_duplex_score"),
        provenance={"coordinate_system": "guide_5p_to_3p,target_transcript_5p_to_3p"},
    )


def _has_supplementary_pairing(strand_sequence: str, target_window: str) -> bool:
    if len(strand_sequence) < 17:
        return False
    supplementary = reverse_complement(strand_sequence[12:17])
    return supplementary in target_window


def _heuristic_metric(value: float | None, name: str) -> EvidenceMetric:
    return EvidenceMetric(
        value=value,
        backend=name,
        backend_version="internal-heuristic-v1",
        calculation_status="heuristic_proxy" if value is not None else "not_calculated",
        is_heuristic=True,
        missing_value_reason=None if value is not None else "no physical-model backend configured",
    )


def _complementarity_score(
    match_type: str, seed_class: str, mismatch_count: int, central_pairing: bool
) -> float:
    seed_score = {"seed8": 38.0, "seed7": 28.0, "seed6": 18.0, "none": 0.0}.get(seed_class, 0.0)
    full_score = (
        60.0 if match_type == "full_length" else 42.0 if "full_length" in match_type else 0.0
    )
    central_bonus = 8.0 if central_pairing else -12.0
    return max(0.0, full_score + seed_score + central_bonus - mismatch_count * 6.0)


def choose_best_site(sites: tuple[BindingSiteEvidence, ...]) -> BindingSiteEvidence | None:
    return max(sites, key=lambda site: site.complementarity_score, default=None)
