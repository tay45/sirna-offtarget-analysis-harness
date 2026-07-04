from __future__ import annotations

from pathlib import Path

from sirna_offtarget.execution.dag import STAGE_NODES
from sirna_offtarget.final_evidence_classification.contracts import (
    FORBIDDEN_CERTAINTY_LABELS,
    GeneFinalEvidenceClassificationRecordV1,
)

ROOT = Path(__file__).resolve().parents[2]
FINAL_STAGE_SRC = ROOT / "src/sirna_offtarget/final_evidence_classification"
UPSTREAM_STAGES = (
    "expected_direct_effect",
    "residual_attribution",
    "secondary_evidence_integration",
)


def test_final_stage_depends_only_on_secondary_evidence_integration() -> None:
    assert STAGE_NODES["final_evidence_classification"].data_dependencies == (
        "secondary_evidence_integration",
    )


def test_final_labels_are_emitted_only_by_final_evidence_classification() -> None:
    allowed_labels = {
        "direct_compatible",
        "secondary_supported",
        "mixed_supported",
        "no_evidence_for_effect",
    }
    for stage in UPSTREAM_STAGES:
        source = "\n".join(
            path.read_text() for path in (ROOT / f"src/sirna_offtarget/{stage}").glob("*.py")
        )
        assert not {label for label in allowed_labels if label in source}


def test_previous_stages_do_not_emit_final_classification_fields() -> None:
    forbidden_fields = {
        "final_evidence_classification",
        "classification_confidence",
        "classification_reason",
    }
    for stage in UPSTREAM_STAGES:
        source = "\n".join(
            path.read_text() for path in (ROOT / f"src/sirna_offtarget/{stage}").glob("*.py")
        )
        assert not {field for field in forbidden_fields if field in source}


def test_no_forbidden_certainty_labels_are_emitted_by_final_contract_fields() -> None:
    fields = set(GeneFinalEvidenceClassificationRecordV1.model_fields)
    assert not set(FORBIDDEN_CERTAINTY_LABELS).intersection(fields)


def test_final_stage_does_not_import_raw_upstream_domains() -> None:
    text = "\n".join(path.read_text() for path in FINAL_STAGE_SRC.glob("*.py"))
    assert "normalized_gene_effects_v2" not in text
    assert "gene_transcript_targetability_ratios_v1" not in text
    assert "GeneResidualAttributionEvidenceRecordV1" not in text
    assert "GeneExpectedDirectEffectRecordV1" not in text


def test_missing_evidence_and_seed_only_guardrails_are_present() -> None:
    text = (FINAL_STAGE_SRC / "contracts.py").read_text()
    assert "missing_evidence_as_negative_allowed" in text
    assert "seed_only_upgrade_allowed" in text
