from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def test_transcript_targetability_does_not_feed_final_classifier_or_scoring() -> None:
    dag = _read("src/sirna_offtarget/execution/dag.py")
    removed_stage = "_".join(("candidate", "scoring"))
    assert f'"{removed_stage}"' not in dag
    assert '"classification"' not in dag


def test_transcript_targetability_scope_excludes_downstream_effect_models() -> None:
    source = _read("src/sirna_offtarget/transcript_targetability/core.py") + _read(
        "src/sirna_offtarget/transcript_targetability/artifacts.py"
    )
    forbidden_terms = [
        "weighted targetable fraction",
        "knockdown calibration",
        "expected direct decrease",
        "residual",
        "secondary effect",
        "source eligibility",
        "direct off-target classification",
    ]
    lowered = source.lower()
    for term in forbidden_terms:
        assert term not in lowered


def test_transcript_targetability_requires_verified_sequence_snapshot_for_enabled_stage() -> None:
    source = _read("src/sirna_offtarget/execution/stages.py")
    body = source[source.index("    def _execute_transcript_targetability") :]
    assert "require_verified_transcript_sequence_snapshot" in body
    assert "verified sequence snapshot" in body
    assert "transcript_sequence_cache_dir" in body


def test_transcript_targetability_verifier_uses_original_sequence_source() -> None:
    source = _read("src/sirna_offtarget/transcript_targetability/artifacts.py")
    assert "transcript_sequence_snapshot_records_v1.jsonl" in source
    assert "transcript_slice = transcript_sequence[start:end]" in source
    assert "site_sequence_mismatch" in source
    assert "build_targetability_site_id" in source


def test_fail_gene_and_intended_policy_are_runtime_boundaries() -> None:
    stages = _read("src/sirna_offtarget/execution/stages.py")
    contracts = _read("src/sirna_offtarget/transcript_targetability/contracts.py")
    assert 'missing_policy.mode == "fail_gene"' in stages
    assert "gene_failed_evidence" in stages
    assert "TranscriptTargetabilityGeneFailureRecordV1" in contracts
    assert "IntendedTargetValidationRecordV1" in contracts
