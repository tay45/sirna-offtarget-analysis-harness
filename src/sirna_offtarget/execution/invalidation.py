from __future__ import annotations

import getpass
import uuid
from pathlib import Path
from typing import Any

from sirna_offtarget.execution.dag import downstream_of
from sirna_offtarget.execution.hashing import dump_json, load_json
from sirna_offtarget.execution.manifests import utc_now


def affected_stages(stage_name: str, include_self: bool = True) -> set[str]:
    affected = downstream_of(stage_name)
    if include_self:
        affected.add(stage_name)
    return affected


def request_store(run_dir: Path) -> Path:
    return run_dir / "invalidation_requests.json"


def load_requests(run_dir: Path) -> list[dict[str, Any]]:
    path = request_store(run_dir)
    if not path.exists():
        return []
    data = load_json(path)
    requests = data.get("requests", [])
    return requests if isinstance(requests, list) else []


def save_requests(run_dir: Path, requests: list[dict[str, Any]]) -> None:
    dump_json(request_store(run_dir), {"requests": requests})


def create_request(run_dir: Path, stage: str, downstream: bool, reason: str) -> dict[str, Any]:
    affected = sorted(affected_stages(stage, include_self=True) if downstream else {stage})
    request = {
        "request_id": str(uuid.uuid4()),
        "requested_stage": stage,
        "include_downstream": downstream,
        "requested_at": utc_now(),
        "requested_by": getpass.getuser(),
        "reason": reason,
        "status": "pending",
        "affected_stages": affected,
    }
    requests = load_requests(run_dir)
    requests.append(request)
    save_requests(run_dir, requests)
    return request


def pending_invalidated_stages(run_dir: Path) -> set[str]:
    pending: set[str] = set()
    for request in load_requests(run_dir):
        if request.get("status") == "pending":
            pending.update(str(stage) for stage in request.get("affected_stages", []))
    return pending


def consume_pending_requests(run_dir: Path) -> None:
    requests = load_requests(run_dir)
    changed = False
    for request in requests:
        if request.get("status") == "pending":
            request["status"] = "consumed"
            changed = True
    if changed:
        save_requests(run_dir, requests)


def cancel_request(run_dir: Path, request_id: str) -> dict[str, Any]:
    requests = load_requests(run_dir)
    for request in requests:
        if request.get("request_id") == request_id:
            if request.get("status") != "pending":
                request["status"] = "rejected"
            else:
                request["status"] = "cancelled"
            save_requests(run_dir, requests)
            return request
    raise ValueError(f"unknown invalidation request {request_id}")
