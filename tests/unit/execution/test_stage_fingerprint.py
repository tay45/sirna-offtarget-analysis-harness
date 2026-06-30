from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.api import build_context
from sirna_offtarget.execution.stages import build_stages, stage_fingerprint


def test_stage_fingerprint_changes_with_relevant_input_hash(tmp_path: Path) -> None:
    original = Path("examples/synthetic/config.yaml")
    copied = tmp_path / "config.yaml"
    copied.write_text(original.read_text())
    transcript = tmp_path / "transcripts.fasta"
    transcript.write_text(Path("examples/synthetic/transcripts.fasta").read_text())
    text = copied.read_text().replace("transcripts.fasta", str(transcript))
    copied.write_text(text)
    context = build_context(config_path=copied, output_dir=tmp_path / "out", run_id="test")
    stage = build_stages()["sequence_analysis"]
    before = stage_fingerprint(stage, context, {})
    transcript.write_text(transcript.read_text() + "\n>NEW|NEW\nAAAAAA\n")
    after = stage_fingerprint(stage, context, {})
    assert before != after
