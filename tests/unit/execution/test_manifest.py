from __future__ import annotations

from sirna_offtarget.execution.manifests import build_base_manifest


def test_stage_manifest_contains_required_provenance_fields() -> None:
    manifest = build_base_manifest(
        run_id="r1",
        stage_name="validate",
        stage_version="1",
        attempt_number=1,
        status="running",
        started_at="2026-01-01T00:00:00+00:00",
        original_config_hash="a",
        resolved_config_hash="b",
        relevant_config_hash="c",
        stage_fingerprint="d",
        dependencies=[],
        command_invocation=("sirna-offtarget", "run"),
        offline=True,
    )
    assert manifest["manifest_schema_version"] == "1"
    assert manifest["stage_name"] == "validate"
    assert manifest["offline"] is True
    assert "output_sha256_checksums" in manifest
