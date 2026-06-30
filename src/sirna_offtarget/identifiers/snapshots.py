from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sirna_offtarget.identifiers.exceptions import IdentifierSnapshotError

SCHEMA_VERSION = "identifier-snapshot-v1"


@dataclass(frozen=True)
class IdentifierSnapshotRecord:
    input_identifier: str
    identifier_type: str
    canonical_gene_id: str | None
    canonical_symbol: str | None
    aliases: tuple[str, ...]
    previous_symbols: tuple[str, ...]
    organism: str
    mapping_source: str
    confidence: str
    ambiguous: bool
    candidate_mappings: tuple[str, ...]
    unmapped_reason: str | None = None


def write_identifier_snapshot(cache_dir: Path, organism: str) -> Path:
    snapshot_dir = cache_dir / f"{organism}_{SCHEMA_VERSION}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    records = _fixture_records(organism)
    records_path = snapshot_dir / "records.jsonl"
    records_path.write_text(
        "\n".join(json.dumps(asdict(record), sort_keys=True) for record in records) + "\n"
    )
    checksum = hashlib.sha256(records_path.read_bytes()).hexdigest()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "organism": organism,
        "snapshot_id": snapshot_dir.name,
        "record_count": len(records),
        "records_sha256": checksum,
        "version_confidence": "retrieval_date_only",
        "warnings": [
            "fixture snapshot; replace with licensed HGNC/Ensembl/UniProt resources for production"
        ],
    }
    (snapshot_dir / "identifier_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    (snapshot_dir / ".verified").write_text("verified\n")
    return snapshot_dir


def build_identifier_snapshot_from_resources(
    cache_dir: Path,
    organism: str,
    input_files: list[Path],
    *,
    snapshot_id: str | None = None,
) -> Path:
    """Build an offline identifier snapshot from user-supplied tabular resources."""
    if not input_files:
        msg = "at least one identifier resource file is required"
        raise IdentifierSnapshotError(msg)
    snapshot_dir = cache_dir / (snapshot_id or f"{organism}_{SCHEMA_VERSION}_custom")
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    records: list[IdentifierSnapshotRecord] = []
    aliases: list[dict[str, str]] = []
    cross_references: list[dict[str, str]] = []
    deprecated: list[dict[str, str]] = []
    ambiguities: list[dict[str, str]] = []
    source_resources: list[dict[str, str]] = []
    for input_file in input_files:
        rows = _read_resource_rows(input_file)
        source_resources.append(
            {
                "path": str(input_file),
                "sha256": hashlib.sha256(input_file.read_bytes()).hexdigest(),
            }
        )
        for row in rows:
            record = _record_from_resource_row(row, organism, input_file.name)
            records.append(record)
            if record.ambiguous:
                ambiguities.append(
                    {
                        "input_identifier": record.input_identifier,
                        "identifier_type": record.identifier_type,
                        "candidate_mappings": ";".join(record.candidate_mappings),
                        "reason": record.unmapped_reason or "ambiguous_mapping",
                    }
                )
            for alias in record.aliases:
                aliases.append(
                    {
                        "alias": alias,
                        "canonical_gene_id": record.canonical_gene_id or "",
                        "canonical_symbol": record.canonical_symbol or "",
                    }
                )
            for previous_symbol in record.previous_symbols:
                deprecated.append(
                    {
                        "deprecated_identifier": previous_symbol,
                        "canonical_gene_id": record.canonical_gene_id or "",
                        "canonical_symbol": record.canonical_symbol or "",
                    }
                )
            if record.canonical_gene_id:
                cross_references.append(
                    {
                        "input_identifier": record.input_identifier,
                        "identifier_type": record.identifier_type,
                        "canonical_gene_id": record.canonical_gene_id,
                        "canonical_symbol": record.canonical_symbol or "",
                    }
                )
    records_path = snapshot_dir / "records.jsonl"
    records_path.write_text(
        "\n".join(json.dumps(asdict(record), sort_keys=True) for record in records) + "\n"
    )
    _write_table(snapshot_dir / "identifier_entities.tsv", [asdict(record) for record in records])
    _write_table(snapshot_dir / "identifier_aliases.tsv", aliases)
    _write_table(snapshot_dir / "identifier_cross_references.tsv", cross_references)
    _write_table(snapshot_dir / "identifier_deprecated.tsv", deprecated)
    _write_table(snapshot_dir / "identifier_ambiguities.tsv", ambiguities)
    normalized_files = [
        "records.jsonl",
        "identifier_entities.tsv",
        "identifier_aliases.tsv",
        "identifier_cross_references.tsv",
        "identifier_deprecated.tsv",
        "identifier_ambiguities.tsv",
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "organism": organism,
        "snapshot_id": snapshot_dir.name,
        "source_resources": source_resources,
        "source_versions": "user_supplied",
        "retrieval_timestamps": "offline_user_supplied",
        "raw_checksums": {item["path"]: item["sha256"] for item in source_resources},
        "normalized_checksums": {
            name: hashlib.sha256((snapshot_dir / name).read_bytes()).hexdigest()
            for name in normalized_files
        },
        "records_sha256": hashlib.sha256(records_path.read_bytes()).hexdigest(),
        "parser_versions": {"identifier_resource_tsv": "identifier-resource-parser-v1"},
        "record_count": len(records),
        "ambiguity_count": len(ambiguities),
        "deprecated_record_count": len(deprecated),
        "version_confidence": "explicit" if source_resources else "unavailable",
        "warnings": [
            "user-supplied offline resources; biological authority depends on supplied files"
        ],
    }
    (snapshot_dir / "identifier_snapshot_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    (snapshot_dir / "identifier_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    (snapshot_dir / ".verified").write_text("verified\n")
    return snapshot_dir


def inspect_identifier_cache(cache_dir: Path) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for path in sorted(cache_dir.glob("*/identifier_manifest.json")):
        manifests.append(json.loads(path.read_text()))
    return manifests


def verify_identifier_cache(cache_dir: Path) -> list[str]:
    errors: list[str] = []
    for manifest_path in sorted(cache_dir.glob("*/identifier_manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"unsupported identifier schema {manifest_path}")
        records_path = manifest_path.parent / "records.jsonl"
        if not records_path.exists():
            errors.append(f"missing records {records_path}")
            continue
        expected = manifest.get("records_sha256")
        actual = hashlib.sha256(records_path.read_bytes()).hexdigest()
        if expected != actual:
            errors.append(f"identifier checksum mismatch {records_path}")
        if not (manifest_path.parent / ".verified").exists():
            errors.append(f"identifier snapshot not marked verified {manifest_path.parent}")
        if (
            manifest.get("source_resources")
            and not (manifest_path.parent / "identifier_entities.tsv").exists()
        ):
            errors.append(f"missing normalized identifier entities {manifest_path.parent}")
    return errors


def require_identifier_cache(cache_dir: Path) -> None:
    errors = verify_identifier_cache(cache_dir)
    if errors:
        raise IdentifierSnapshotError("; ".join(errors))


def _fixture_records(organism: str) -> list[IdentifierSnapshotRecord]:
    records = [
        IdentifierSnapshotRecord(
            "TP53",
            "hgnc_symbol",
            "HGNC:11998",
            "TP53",
            ("P53",),
            ("BCC7",),
            organism,
            "fixture_hgnc",
            "unambiguous",
            False,
            (),
        ),
        IdentifierSnapshotRecord(
            "P04637",
            "uniprot_accession",
            "HGNC:11998",
            "TP53",
            (),
            (),
            organism,
            "fixture_uniprot",
            "unambiguous",
            False,
            (),
        ),
        IdentifierSnapshotRecord(
            "OLD1",
            "hgnc_symbol",
            None,
            None,
            (),
            ("OLD1",),
            organism,
            "fixture_hgnc",
            "ambiguous",
            True,
            ("GENEA", "GENEB"),
            "one_to_many_alias",
        ),
    ]
    for symbol in (
        "TARGET1",
        "DIRECT_NEAR",
        "SEED8_UTR",
        "SEED7",
        "WEAK_PARTIAL",
        "PASSENGER_DIRECT",
        "SIMILAR_NO_EXPR",
        "SECONDARY_DOWN",
        "SECONDARY_UP",
        "MODULE_A",
        "MODULE_B",
        "REGULON_RESP",
        "STRESS_IFN",
        "MIXED_GENE",
        "UNCHANGED1",
        "LOWCOUNT_FC",
        "NOISE_CHANGE",
        "DIRECTION_BAD",
        "INACCESSIBLE_MATCH",
        "GENEA",
        "GENEB",
    ):
        records.append(
            IdentifierSnapshotRecord(
                symbol,
                "synthetic_symbol",
                f"SYNTH:{symbol}",
                symbol,
                (),
                (),
                organism,
                "fixture_synthetic",
                "unambiguous",
                False,
                (),
            )
        )
    return records


def _read_resource_rows(path: Path) -> list[dict[str, str]]:
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","
    with path.open(newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle, delimiter=delimiter)]


def _record_from_resource_row(
    row: dict[str, str], organism: str, mapping_source: str
) -> IdentifierSnapshotRecord:
    input_identifier = _first_present(
        row, "input_identifier", "identifier", "symbol", "alias", "ensembl_gene_id", "uniprot"
    )
    identifier_type = _first_present(row, "identifier_type", "type") or _infer_identifier_type(row)
    candidate_mappings = tuple(
        item.strip()
        for item in _first_present(row, "candidate_mappings", "candidates").split(";")
        if item.strip()
    )
    ambiguous = _truthy(_first_present(row, "ambiguous")) or len(candidate_mappings) > 1
    aliases = tuple(
        item.strip() for item in _first_present(row, "aliases", "alias").split(";") if item.strip()
    )
    previous_symbols = tuple(
        item.strip()
        for item in _first_present(row, "previous_symbols", "deprecated_symbol").split(";")
        if item.strip()
    )
    canonical_gene_id = _first_present(row, "canonical_gene_id", "hgnc_id", "gene_id") or None
    canonical_symbol = _first_present(row, "canonical_symbol", "approved_symbol", "symbol") or None
    return IdentifierSnapshotRecord(
        input_identifier=input_identifier,
        identifier_type=identifier_type,
        canonical_gene_id=canonical_gene_id,
        canonical_symbol=canonical_symbol,
        aliases=aliases,
        previous_symbols=previous_symbols,
        organism=_first_present(row, "organism") or organism,
        mapping_source=mapping_source,
        confidence=_first_present(row, "confidence")
        or ("ambiguous" if ambiguous else "unambiguous"),
        ambiguous=ambiguous,
        candidate_mappings=candidate_mappings,
        unmapped_reason=_first_present(row, "unmapped_reason") or None,
    )


def _first_present(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key, "")
        if value:
            return value.strip()
    return ""


def _infer_identifier_type(row: dict[str, str]) -> str:
    if row.get("ensembl_transcript_id"):
        return "ensembl_transcript_id"
    if row.get("ensembl_gene_id"):
        return "ensembl_gene_id"
    if row.get("entrez_id"):
        return "entrez_gene_id"
    if row.get("uniprot"):
        return "uniprot_accession"
    return "hgnc_symbol"


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _write_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["empty"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: ";".join(value) if isinstance(value, tuple) else value
                    for key, value in row.items()
                }
            )
