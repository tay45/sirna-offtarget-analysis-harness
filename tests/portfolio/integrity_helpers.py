from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml

from sirna_offtarget.execution.api import run_staged_analysis

ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO = ROOT / "examples" / "portfolio"
CONFIG = ROOT / "examples/portfolio/config.yaml"
EXPECTED_RATIO_STAGES = [
    "validate",
    "prepare_inputs",
    "map_identifiers",
    "sequence_analysis",
    "expression_analysis",
    "isoform_uncertainty",
    "transcript_targetability",
    "transcript_targetability_ratio",
]


def _snake(*parts: str) -> str:
    return "_".join(parts)


PROHIBITED_FIELDS = {
    _snake("direct", "effect", "score"),
    _snake("direct", "effect", "tier"),
    _snake("secondary", "effect", "score"),
    _snake("secondary", "effect", "tier"),
    _snake("mixed", "effect", "score"),
    _snake("mixed", "mechanism", "score"),
    _snake("risk", "score"),
    _snake("risk", "tier"),
    _snake("final", "classification"),
    _snake("mechanism", "classification"),
    _snake("direct", "classification"),
    _snake("secondary", "classification"),
    _snake("mixed", "classification"),
    _snake("supported", "intended", "target"),
    _snake("supported", "direct", "target"),
    _snake("likely", "secondary", "effect"),
    _snake("mixed", "mechanism"),
    _snake("regulatory", "risk"),
    _snake("safety", "risk"),
}
PROHIBITED_TEXT = {
    " ".join(("direct", "effect", "confirmed")),
    " ".join(("secondary", "effect", "likely")),
    " ".join(("mixed", "mechanism")),
    " ".join(("supported", "intended", "target")),
    "high-confidence " + "direct",
    "safety concern",
    " ".join(("regulatory", "risk")),
    " ".join(("final", "classification")),
}


def run_portfolio(
    out: Path, until_stage: str | None = "transcript_targetability_ratio"
) -> list[str]:
    rows = run_staged_analysis(
        config_path=CONFIG,
        output_dir=out,
        until_stage=until_stage,
    )
    return [row["stage"] for row in rows]


def serialized_field_hits(root: Path) -> list[str]:
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {
            ".json",
            ".jsonl",
            ".yaml",
            ".yml",
            ".tsv",
            ".csv",
            ".md",
        }:
            continue
        if path.suffix.lower() == ".json":
            _collect_json_hits(path, json.loads(path.read_text()), hits)
        elif path.suffix.lower() == ".jsonl":
            for line_number, line in enumerate(path.read_text().splitlines(), start=1):
                if line.strip():
                    _collect_json_hits(path, json.loads(line), hits, suffix=f":{line_number}")
        elif path.suffix.lower() in {".yaml", ".yml"}:
            loaded = yaml.safe_load(path.read_text())
            _collect_json_hits(path, loaded, hits)
        elif path.suffix.lower() in {".tsv", ".csv"}:
            delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
            with path.open(newline="") as handle:
                reader = csv.reader(handle, delimiter=delimiter)
                headers = next(reader, [])
            hits.extend(f"{path}:{field}" for field in headers if field in PROHIBITED_FIELDS)
        elif path.suffix.lower() == ".md":
            text = path.read_text().lower()
            for field in PROHIBITED_FIELDS:
                if field in text:
                    hits.append(f"{path}:{field}")

    return hits


def _collect_json_hits(path: Path, value: Any, hits: list[str], *, suffix: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in PROHIBITED_FIELDS:
                hits.append(f"{path}{suffix}:{key}")
            _collect_json_hits(path, child, hits, suffix=suffix)
    elif isinstance(value, list):
        for child in value:
            _collect_json_hits(path, child, hits, suffix=suffix)
