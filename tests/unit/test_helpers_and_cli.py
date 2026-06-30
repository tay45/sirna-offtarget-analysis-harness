from pathlib import Path

from click.testing import CliRunner

from sirna_offtarget.cli import main
from sirna_offtarget.expression.low_count_filter import is_low_count
from sirna_offtarget.expression.replicate_consistency import consistency
from sirna_offtarget.expression.shrinkage import shrink_lfc
from sirna_offtarget.io.annotation import read_annotation_lines
from sirna_offtarget.io.serialization import to_jsonable
from sirna_offtarget.isoform.sensitivity import efficiency_grid
from sirna_offtarget.isoform.site_coverage import site_coverage
from sirna_offtarget.models import (
    BindingSiteEvidence,
    EvidenceMetric,
    GeneSequenceEvidence,
    TranscriptRecord,
    TranscriptSequenceEvidence,
)
from sirna_offtarget.pathway.direction_consistency import is_direction_consistent
from sirna_offtarget.pathway.enrichment import simple_enrichment_score
from sirna_offtarget.pathway.modules import module_coherence
from sirna_offtarget.pathway.regulons import regulon_score
from sirna_offtarget.pathway.signatures import signature_evidence
from sirna_offtarget.plugins import AccessibilityBackend, EnergyBackend, PathwayBackend
from sirna_offtarget.reporting.plots import plot_manifest
from sirna_offtarget.sequence.accessibility import default_accessibility
from sirna_offtarget.sequence.binding_context import local_context
from sirna_offtarget.sequence.energy import default_duplex_energy

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "examples/synthetic/config.yaml"


def test_small_helper_modules(tmp_path: Path) -> None:
    assert is_low_count(5, 10, 2, 2)
    assert consistency([1, 1, -1]) == 1 / 3
    assert shrink_lfc(-1) < 0
    assert efficiency_grid(0.5, 0.6, 0.05) == [0.5, 0.55, 0.6]
    assert local_context("ABCDEFG", 3, 2) == "BCDE"
    assert default_accessibility("3UTR") == 0.75
    assert default_duplex_energy(2) == -20.0
    assert simple_enrichment_score(2, 4) == 0.5
    assert module_coherence([True, False]) == 0.5
    assert regulon_score(True) == 1.0
    assert signature_evidence(False) == 0.0
    assert is_direction_consistent("unknown", "down") is False
    assert plot_manifest()["status"]
    assert to_jsonable({"path": tmp_path}) == {"path": str(tmp_path)}


def test_annotation_site_coverage_and_protocol_imports(tmp_path: Path) -> None:
    annotation = tmp_path / "annotation.gtf"
    annotation.write_text('# comment\nchr\tsrc\tgene\t1\t2\t.\t+\t.\tgene_id "A";\n')
    assert len(read_annotation_lines(annotation)) == 1
    metric = EvidenceMetric(None, "none", "none", "not_calculated", True, "test")
    hit = BindingSiteEvidence(
        "G",
        "tx1",
        "guide",
        "seed",
        "seed8",
        0,
        (),
        0,
        8,
        "CDS",
        "AAAAAAAA",
        (2, 9),
        (0, 8),
        None,
        10.0,
        False,
        True,
        False,
        False,
        0,
        metric,
        metric,
        metric,
    )
    evidence = GeneSequenceEvidence("G", (TranscriptSequenceEvidence("G", "tx1", (hit,)),))
    with_site, without_site = site_coverage(
        "G",
        [TranscriptRecord("tx1", "G", "AAA"), TranscriptRecord("tx2", "G", "CCC")],
        {"G": evidence},
    )
    assert with_site == ["tx1"]
    assert without_site == ["tx2"]
    assert AccessibilityBackend and EnergyBackend and PathwayBackend


def test_remaining_cli_commands() -> None:
    runner = CliRunner()
    for args in (
        ["map-sequence", "--config", str(CONFIG)],
        ["analyze-expression", "--config", str(CONFIG)],
        ["analyze-isoforms", "--config", str(CONFIG)],
        ["analyze-pathways", "--config", str(CONFIG)],
        ["analyze-pathways", "--config", str(CONFIG), "--offline"],
        ["pathway-db", "inspect", "--cache-dir", str(ROOT / "resources/pathway_cache")],
        ["run", "--config", str(CONFIG), "--dry-run"],
        ["show-version"],
    ):
        result = runner.invoke(main, args)
        assert result.exit_code == 0, result.output

    removed = "-".join(("score", "candidates"))
    result = runner.invoke(main, [removed, "--config", str(CONFIG)])
    assert result.exit_code != 0
    assert "No such command" in result.output
