from __future__ import annotations

from pathlib import Path
from typing import Any

from sirna_offtarget.execution.hashing import dump_json, hash_data, load_json, write_yaml
from sirna_offtarget.execution.manifests import utc_now


def write_config_revision(
    *,
    run_dir: Path,
    original: dict[str, Any],
    resolved: dict[str, Any],
    reason: str,
    cli_overrides: dict[str, Any],
) -> int:
    history = run_dir / "config_history"
    history.mkdir(parents=True, exist_ok=True)
    original_hash = hash_data(original)
    resolved_hash = hash_data(resolved)
    existing = sorted(history.glob("revision_*.metadata.json"))
    if existing:
        latest = load_json(existing[-1])
        if (
            latest.get("original_sha256") == original_hash
            and latest.get("resolved_sha256") == resolved_hash
            and latest.get("cli_overrides") == cli_overrides
        ):
            event_path = history / "events.jsonl"
            with event_path.open("a") as handle:
                handle.write(
                    f'{{"timestamp":"{utc_now()}","event":"config_revision_reused",'
                    f'"revision_number":{latest["revision_number"]},"reason":"unchanged"}}\n'
                )
            return int(latest["revision_number"])
    revision = len(existing) + 1
    prefix = history / f"revision_{revision:03d}"
    write_yaml(prefix.with_suffix(".original.yaml"), original)
    write_yaml(prefix.with_suffix(".resolved.yaml"), resolved)
    dump_json(
        prefix.with_suffix(".metadata.json"),
        {
            "revision_number": revision,
            "timestamp": utc_now(),
            "original_sha256": original_hash,
            "resolved_sha256": resolved_hash,
            "parent_revision": revision - 1 if revision > 1 else None,
            "reason": reason,
            "cli_overrides": cli_overrides,
            "affected_stage_plan": [],
            "status": "created",
            "creation_reason": reason,
        },
    )
    return revision
