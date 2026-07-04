from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.dag import STAGE_NODES
from sirna_offtarget.secondary_evidence_integration.contracts import (
    GeneSecondaryEvidenceIntegrationRecordV1,
    SecondaryEvidenceIntegrationResultV1,
    SecondaryEvidenceIntegrationUnresolvedRecordV1,
)

ROOT = Path(__file__).resolve().parents[2]
STAGE_SRC = ROOT / "src/sirna_offtarget/secondary_evidence_integration"


def test_secondary_evidence_integration_does_not_emit_final_call_fields() -> None:
    forbidden = (
        "_".join(("final", "classification")),
        "_".join(("final", "call")),
        "_".join(("gene", "class")),
        "_".join(("off", "target", "call")),
        "_".join(("secondary", "effect", "call")),
        "_".join(("direct", "effect", "call")),
        "_".join(("mixed", "call")),
    )
    emitted_fields = (
        set(GeneSecondaryEvidenceIntegrationRecordV1.model_fields)
        | set(SecondaryEvidenceIntegrationUnresolvedRecordV1.model_fields)
        | set(SecondaryEvidenceIntegrationResultV1.model_fields)
    )
    for token in forbidden:
        assert token not in emitted_fields


def test_secondary_evidence_integration_depends_on_residual_attribution() -> None:
    assert STAGE_NODES["secondary_evidence_integration"].data_dependencies == (
        "residual_attribution",
    )


def test_secondary_evidence_integration_keeps_missing_pathway_unresolved() -> None:
    core = (STAGE_SRC / "core.py").read_text()
    assert "ready_with_unresolved_pathway_context" in core
    assert "unresolved_not_negative" in core


def test_secondary_evidence_integration_does_not_import_raw_upstream_domains() -> None:
    text = "\n".join(path.read_text() for path in STAGE_SRC.glob("*.py"))
    assert "normalized_gene_effects_v2" not in text
    assert "gene_transcript_targetability_ratios_v1" not in text
    assert "GeneExpectedDirectEffectRecordV1" not in text


def test_expected_direct_effect_and_residual_logic_do_not_import_integration() -> None:
    for stage in ("expected_direct_effect", "residual_attribution"):
        stage_src = ROOT / f"src/sirna_offtarget/{stage}"
        text = "\n".join(path.read_text() for path in stage_src.glob("*.py"))
        assert "secondary_evidence_integration" not in text
