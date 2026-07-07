from __future__ import annotations

from typing import Any

from sirna_offtarget.contracts.stage_results import MechanisticNetworkResultV2
from sirna_offtarget.residual_attribution.core import PathwaySupportEvidence


SIGNED_PATH_KIND = "signed_mechanistic_path"
UNSIGNED_CONTEXT_KIND = "unsigned_context_path"


def pathway_support_from_mechanistic_network_v2(
    contract: MechanisticNetworkResultV2,
) -> dict[str, list[PathwaySupportEvidence]]:
    """Convert mechanistic V2 paths into candidate-level residual support records.

    Signed paths can carry causal-direction context. Unsigned/context paths are
    preserved as mechanistic context but are explicitly marked as not causal
    direction support.
    """

    support_by_gene: dict[str, list[PathwaySupportEvidence]] = {}
    for path in contract.payload.signed_paths:
        _append_support(
            support_by_gene,
            path,
            evidence_kind=SIGNED_PATH_KIND,
            causal_direction_support=bool(path.get("fully_signed")),
        )
    for path in contract.payload.unsigned_context_paths:
        _append_support(
            support_by_gene,
            path,
            evidence_kind=UNSIGNED_CONTEXT_KIND,
            causal_direction_support=False,
        )
    return support_by_gene


def _append_support(
    support_by_gene: dict[str, list[PathwaySupportEvidence]],
    path: dict[str, Any],
    *,
    evidence_kind: str,
    causal_direction_support: bool,
) -> None:
    candidate = str(path.get("candidate") or path.get("target_symbol") or "")
    if not candidate:
        return
    record_id = str(path.get("path_id") or path.get("path_search_result_id") or "")
    if not record_id:
        record_id = f"{evidence_kind}:{candidate}:{len(support_by_gene.get(candidate, [])) + 1}"
    support_by_gene.setdefault(candidate, []).append(
        PathwaySupportEvidence(
            record_id=record_id,
            evidence_kind=evidence_kind,
            support_strength=_support_strength(path, causal_direction_support),
            summary=_support_summary(path, evidence_kind, causal_direction_support),
        )
    )


def _support_strength(path: dict[str, Any], causal_direction_support: bool) -> str:
    if not causal_direction_support:
        return "supporting_context"
    if path.get("direction_consistent") is True:
        return "direction_consistent_signed_path"
    if path.get("direction_consistent") is False:
        return "conflicting_signed_path"
    return "signed_path"


def _support_summary(
    path: dict[str, Any],
    evidence_kind: str,
    causal_direction_support: bool,
) -> dict[str, object]:
    return {
        "source": "mechanistic_network",
        "evidence_kind": evidence_kind,
        "path_id": path.get("path_id"),
        "search_result_id": path.get("search_result_id"),
        "candidate": path.get("candidate"),
        "ordered_nodes": tuple(path.get("ordered_nodes", ()) or ()),
        "ordered_entity_ids": tuple(path.get("ordered_entity_ids", ()) or ()),
        "ordered_consensus_edge_ids": tuple(path.get("ordered_consensus_edge_ids", ()) or ()),
        "path_length": path.get("path_length"),
        "fully_signed": bool(path.get("fully_signed")),
        "causal_direction_support": causal_direction_support,
        "direction_consistent": path.get("direction_consistent"),
        "composed_sign": path.get("composed_sign"),
        "expected_candidate_direction_after_target_decrease": path.get(
            "expected_candidate_direction_after_target_decrease"
        ),
        "provider_sources": tuple(path.get("provider_sources", ()) or ()),
        "provider_evidence_ids": tuple(path.get("provider_evidence_ids", ()) or ()),
        "references": tuple(path.get("references", ()) or ()),
        "database_versions": tuple(path.get("database_versions", ()) or ()),
        "retrieval_snapshots": tuple(path.get("retrieval_snapshots", ()) or ()),
        "path_confidence_id": path.get("path_confidence_id"),
        "confidence_score": path.get("confidence_score"),
        "conflicting_with_other_paths": bool(path.get("conflicting_with_other_paths")),
        "warnings": tuple(path.get("warnings", ()) or ()),
        "interpretation": (
            "signed_path_supporting_context"
            if causal_direction_support
            else "unsigned_or_context_path_not_causal_direction_support"
        ),
    }
