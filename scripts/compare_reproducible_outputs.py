from __future__ import annotations

import argparse
import json
from pathlib import Path

DETERMINISTIC_FILES = [
    "stages/08_transcript_targetability_ratio/attempts/attempt_001/committed/outputs/gene_transcript_targetability_ratios_v1.tsv",
    "stages/08_transcript_targetability_ratio/attempts/attempt_001/committed/outputs/transcript_m_contributions_v1.tsv",
    "stages/08_transcript_targetability_ratio/attempts/attempt_001/committed/outputs/transcript_targetability_ratio_unresolved_v1.tsv",
    "stages/08_transcript_targetability_ratio/attempts/attempt_001/committed/outputs/transcript_targetability_ratio_summary_v1.json",
]
IGNORED_JSON_FIELDS = {
    "generated_at_utc",
    "outputs",
    "created_at",
    "started_at",
    "updated_at",
    "completed_at",
}


def normalize_json(path: Path) -> object:
    def scrub(value: object) -> object:
        if isinstance(value, dict):
            return {k: scrub(v) for k, v in value.items() if k not in IGNORED_JSON_FIELDS}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    return scrub(json.loads(path.read_text()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    args = parser.parse_args()
    failures: list[str] = []
    for filename in DETERMINISTIC_FILES:
        left = args.left / filename
        right = args.right / filename
        if not left.exists() or not right.exists():
            failures.append(f"missing {filename}")
            continue
        if filename.endswith(".json"):
            if normalize_json(left) != normalize_json(right):
                failures.append(f"different JSON payload: {filename}")
        elif left.read_text() != right.read_text():
            failures.append(f"different text payload: {filename}")
    if failures:
        print("\n".join(failures))
        return 1
    print("reproducible deterministic outputs match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
