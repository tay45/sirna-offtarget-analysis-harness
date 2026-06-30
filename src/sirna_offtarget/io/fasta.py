from __future__ import annotations

from pathlib import Path

from sirna_offtarget.models import TranscriptRecord


def read_transcripts(path: Path) -> list[TranscriptRecord]:
    records: list[TranscriptRecord] = []
    header: str | None = None
    parts: list[str] = []
    for line in path.read_text().splitlines():
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                records.append(_record_from_header(header, "".join(parts)))
            header = line[1:]
            parts = []
        else:
            parts.append(line.strip().upper())
    if header is not None:
        records.append(_record_from_header(header, "".join(parts)))
    return records


def _record_from_header(header: str, sequence: str) -> TranscriptRecord:
    fields = dict(item.split("=", 1) for item in header.split() if "=" in item)
    transcript_id = fields.get("transcript_id", header.split()[0])
    gene = fields.get("gene", transcript_id.split(".")[0])
    regions = {
        key.removeprefix("region_"): value
        for key, value in fields.items()
        if key.startswith("region_")
    }
    return TranscriptRecord(
        transcript_id=transcript_id, gene=gene, sequence=sequence, regions=regions
    )
