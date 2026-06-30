from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (ROOT / path).read_text()


def test_immutable_artifacts_are_finalized_before_metadata_records() -> None:
    source = _read("src/sirna_offtarget/execution/stages.py")
    body = source[source.index("    def _execute_isoform_uncertainty") :]
    assert body.index("write_immutable_isoform_uncertainty_artifacts") < body.index(
        "write_final_isoform_uncertainty_metadata"
    )


def test_no_unverifiable_self_checksum_exists() -> None:
    source = _read("src/sirna_offtarget/isoform_uncertainty/artifacts.py")
    assert "result_file_sha256" not in source
    assert "self_checksum_status" in source


def test_outer_manifest_owns_final_metadata_checksums() -> None:
    source = _read("src/sirna_offtarget/execution/runner.py")
    assert "attach_artifacts(" in source
    assert "verify_committed_isoform_uncertainty_result" in source


def test_commit_occurs_only_after_final_verification() -> None:
    source = _read("src/sirna_offtarget/execution/runner.py")
    assert source.index("verify_isoform_uncertainty_final_outputs") < source.index(
        "committed_outputs"
    )


def test_resume_verifies_isoform_checksums() -> None:
    source = _read("src/sirna_offtarget/execution/runner.py")
    assert "isoform uncertainty committed verification failed" in source


def test_no_targetability_or_nm_logic_introduced_in_isoform_uncertainty() -> None:
    source = _read("src/sirna_offtarget/isoform_uncertainty/core.py") + _read(
        "src/sirna_offtarget/isoform_uncertainty/artifacts.py"
    )
    forbidden = [
        "targetability",
        "targetable_transcript_count",
        "formal_transcript_count",
        "M/N",
        "intended-target",
        "residual",
        "secondary-effect",
    ]
    assert not any(term in source for term in forbidden)
