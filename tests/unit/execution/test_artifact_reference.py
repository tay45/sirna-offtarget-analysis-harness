from __future__ import annotations

from pathlib import Path

from sirna_offtarget.contracts.artifacts import build_artifact_reference


def test_artifact_reference_is_relative_and_checksummed(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    artifact = run_dir / "stages" / "x.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"ok": true}\n')
    ref = build_artifact_reference(
        run_dir=run_dir,
        path=artifact,
        logical_name="x",
        media_type="application/json",
        created_by_stage="test",
        created_by_attempt=1,
    )
    assert not ref.relative_path.startswith("/")
    assert ref.sha256
    assert ref.size_bytes == artifact.stat().st_size
