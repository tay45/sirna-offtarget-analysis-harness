from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from sirna_offtarget.execution.api import run_staged_analysis, status_run
from sirna_offtarget.execution.hashing import load_json

ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC = ROOT / "examples/synthetic"


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_annotation_cache(tmp_path: Path) -> Path:
    cache_dir = tmp_path / "annotation_cache"
    snapshot_dir = cache_dir / "synthetic-verified"
    snapshot_dir.mkdir(parents=True)
    genes = [
        line.split("\t", 1)[0]
        for line in (SYNTHETIC / "counts.tsv").read_text().splitlines()[1:]
        if line.strip()
    ]
    rows: list[dict[str, object]] = []
    for gene in genes:
        transcript_count = 3 if gene == "TARGET1" else 1
        for index in range(1, transcript_count + 1):
            rows.append(
                {
                    "original_gene_id": gene,
                    "canonical_gene_id": f"SYNTH:{gene}",
                    "original_transcript_id": f"{gene.lower()}_tx{index}.1",
                    "canonical_transcript_id": f"{gene.lower()}_tx{index}",
                    "transcript_version": "1",
                    "transcript_biotype": "protein_coding",
                    "organism": "human",
                    "assembly": "GRCh38",
                    "annotation_release": "synthetic-v1",
                    "sequence_reference": "synthetic-transcripts.fasta",
                }
            )
    records_path = snapshot_dir / "transcripts.jsonl"
    _write_jsonl(records_path, rows)
    manifest = {
        "provider": "synthetic",
        "release": "synthetic-v1",
        "organism": "human",
        "assembly": "GRCh38",
        "transcript_identifier_namespace": "synthetic_transcript",
        "gene_identifier_namespace": "symbol",
        "source_file_checksum": _sha256(records_path),
        "snapshot_id": "synthetic-verified",
        "verification_status": "verified",
    }
    (snapshot_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return cache_dir


def _read_fasta(path: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    current: str | None = None
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            current = line[1:].split()[0]
            records[current] = ""
        elif current is not None:
            records[current] += line.strip()
    return records


def _write_transcript_sequence_cache(tmp_path: Path) -> Path:
    cache_dir = tmp_path / "sequence_cache"
    snapshot_dir = cache_dir / "synthetic-v1"
    snapshot_dir.mkdir(parents=True)
    fasta = _read_fasta(SYNTHETIC / "transcripts.fasta")
    annotation_rows = [
        json.loads(line)
        for line in (tmp_path / "annotation_cache" / "synthetic-verified" / "transcripts.jsonl")
        .read_text()
        .splitlines()
        if line.strip()
    ]
    rows: list[dict[str, object]] = []
    for annotation in annotation_rows:
        transcript_id = str(annotation["canonical_transcript_id"])
        sequence = fasta.get(transcript_id, "ACACACACACACACACACACACACACACAC")
        rows.append(
            {
                "canonical_gene_id": annotation["canonical_gene_id"],
                "canonical_transcript_id": transcript_id,
                "transcript_version": annotation["transcript_version"],
                "sequence": sequence,
                "sequence_checksum": hashlib.sha256(sequence.encode()).hexdigest(),
            }
        )
    records_path = snapshot_dir / "transcript_sequences.jsonl"
    _write_jsonl(records_path, rows)
    manifest = {
        "schema_version": "1",
        "snapshot_id": "synthetic-v1",
        "provider": "synthetic",
        "release": "synthetic-v1",
        "organism": "human",
        "assembly": "GRCh38",
        "transcript_identifier_namespace": "synthetic_transcript",
        "sequence_alphabet": "DNA",
        "transcript_count": len(rows),
        "sequence_file_checksum": _sha256(records_path),
        "verification_status": "verified",
        "generation_method": "integration_test",
    }
    (snapshot_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return cache_dir


def _write_config(tmp_path: Path, annotation_cache: Path) -> Path:
    config = yaml.safe_load((SYNTHETIC / "config.yaml").read_text())
    config["expression"]["count_matrix"] = str(SYNTHETIC / "counts.tsv")
    config["expression"]["sample_metadata"] = str(SYNTHETIC / "sample_metadata.tsv")
    config["sequence"]["transcript_fasta"] = str(SYNTHETIC / "transcripts.fasta")
    config["sequence"]["annotation_gtf"] = str(SYNTHETIC / "annotation.gtf")
    config["pathway"]["network_file"] = str(SYNTHETIC / "pathway_network.tsv")
    config["pathway"]["regulon_file"] = str(SYNTHETIC / "regulons.tsv")
    config["outputs"]["directory"] = str(tmp_path / "run")
    config["isoform_uncertainty"] = {
        "enabled": True,
        "annotation_cache_dir": str(annotation_cache),
        "annotation_snapshot_id": "synthetic-verified",
        "identifier_snapshot_id": "synthetic-id-snapshot",
        "identifier_snapshot_checksum": "verified-synthetic-id-checksum",
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    return path


def _write_targetability_config(
    tmp_path: Path, annotation_cache: Path, sequence_cache: Path
) -> Path:
    path = _write_config(tmp_path, annotation_cache)
    config = yaml.safe_load(path.read_text())
    config["transcript_targetability"] = {
        "enabled": True,
        "transcript_sequence_cache_dir": str(sequence_cache),
        "transcript_sequence_snapshot_id": "synthetic-v1",
    }
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    return path


def test_isoform_uncertainty_runs_as_committed_workflow_stage(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, _write_annotation_cache(tmp_path))
    out = tmp_path / "run"

    first = run_staged_analysis(
        config_path=config_path,
        output_dir=out,
        until_stage="isoform_uncertainty",
    )
    second = run_staged_analysis(
        config_path=config_path,
        output_dir=out,
        until_stage="isoform_uncertainty",
    )

    assert first[-1]["stage"] == "isoform_uncertainty"
    assert first[-1]["status"] == "completed_with_warnings"
    assert second[-1]["stage"] == "isoform_uncertainty"
    assert second[-1]["action"] == "reuse"
    assert any(item["stage"] == "isoform_uncertainty" for item in status_run(out))
    stage_dir = out / "stages" / "06_isoform_uncertainty" / "attempts" / "attempt_001"
    manifest = load_json(stage_dir / "stage_manifest.json")
    assert manifest["status"] == "completed_with_warnings"
    assert manifest["data_dependencies"] == ["expression_analysis"]
    assert manifest["completion_dependencies"] == ["map_identifiers"]
    assert manifest["consumed_dependencies"][0]["dependency_stage"] == "expression_analysis"
    committed = stage_dir / "committed" / "outputs"
    assert (committed / "stage_result.json").exists()
    assert (committed / "isoform_uncertainty_result_v1.json").exists()
    assert (committed / "external_transcript_evidence_validation_v1.json").exists()
    payload = load_json(committed / "stage_result.json")["payload"]
    assert payload["run_record"]["verification_status"] == "verified"
    assert payload["counts"]["gene_isoform_uncertainty_records"] == 19
    assert payload["counts"]["transcript_prior_weight_records"] == 21


def test_transcript_targetability_runs_after_isoform_uncertainty(tmp_path: Path) -> None:
    config_path = _write_targetability_config(
        tmp_path,
        _write_annotation_cache(tmp_path),
        _write_transcript_sequence_cache(tmp_path),
    )
    out = tmp_path / "run"

    result = run_staged_analysis(
        config_path=config_path,
        output_dir=out,
        until_stage="transcript_targetability",
    )

    assert result[-1]["stage"] == "transcript_targetability"
    stage_dir = out / "stages" / "07_transcript_targetability" / "attempts" / "attempt_001"
    committed = stage_dir / "committed" / "outputs"
    payload = load_json(committed / "stage_result.json")["payload"]
    assert payload["run_record"]["verification_status"] == "verified"
    assert payload["counts"]["eligible_transcripts_examined"] == 21
    assert payload["counts"]["transcripts_with_cleavage_compatible_candidate_sites"] >= 1
    assert (committed / "transcript_targetability_evidence_v1.jsonl").exists()
    assert (committed / "transcript_targetability_mismatches_v1.jsonl").exists()
