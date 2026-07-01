from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from sirna_offtarget.config import HarnessConfig
from sirna_offtarget.io.pathways import read_network, read_regulons
from sirna_offtarget.pathway.providers.cache import mark_verified, write_jsonl
from sirna_offtarget.pathway.providers.http import fetch_bytes
from sirna_offtarget.pathway.providers.manifest import (
    build_provider_manifest,
    snapshot_id,
    write_manifest,
)
from sirna_offtarget.pathway.providers.omnipath import OmniPathProvider
from sirna_offtarget.pathway.providers.panther import PantherProvider
from sirna_offtarget.pathway.providers.reactome_analysis import ReactomeAnalysisProvider
from sirna_offtarget.pathway.providers.reactome_content import ReactomeContentProvider
from sirna_offtarget.pathway.providers.reactome_fi import ReactomeFIProvider
from sirna_offtarget.pathway.providers.registry import get_provider
from sirna_offtarget.pathway.providers.signor import SignorProvider


def fetch_pathway_cache(
    config: HarnessConfig,
    providers: list[str],
    cache_dir: Path,
) -> dict[str, object]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    provider_summaries: list[dict[str, object]] = []
    for provider_name in providers:
        provider = get_provider(provider_name)
        provider_key = provider_name.replace("-", "_")
        selection = config.providers.get(provider_key)
        raw_payload: object
        response_headers: dict[str, str] = {}
        endpoint = "recorded_response_or_configured_local_snapshot"
        if selection and selection.mode == "public_fetch":
            if selection.endpoint is None:
                raise ValueError(f"providers.{provider_key}.endpoint is required for public_fetch")
            fetched = fetch_bytes(
                url=selection.endpoint,
                timeout_seconds=selection.timeout_seconds,
                retry_count=selection.retry_count,
                expected_content_type=selection.expected_content_type,
            )
            response_headers = fetched.headers
            endpoint = fetched.url
            raw_payload = json.loads(fetched.body.decode())
        else:
            raw_payload = _recorded_payload(config, provider_name)
        normalized = _normalize(provider, raw_payload, config.project.organism)
        snapshot = snapshot_id(
            provider_name.replace("-", "_"), config.project.organism, raw_payload
        )
        root = cache_dir / provider_name.replace("-", "_") / snapshot
        raw_dir = root / "raw"
        normalized_dir = root / "normalized"
        raw_dir.mkdir(parents=True, exist_ok=True)
        normalized_dir.mkdir(parents=True, exist_ok=True)
        raw_file = raw_dir / "response.json"
        raw_file.write_text(json.dumps(raw_payload, indent=2, sort_keys=True) + "\n")
        normalized_file = normalized_dir / "records.jsonl"
        write_jsonl(normalized_file, normalized)
        manifest = build_provider_manifest(
            provider=provider_name.replace("-", "_"),
            snapshot=snapshot,
            organism=config.project.organism,
            endpoint=endpoint,
            request_parameters={
                "config_project": config.project.name,
                "provider_mode": selection.mode if selection else "local_snapshot",
                "response_header_count": str(len(response_headers)),
            },
            database_version=getattr(provider, "provider_version", "offline-cache"),
            raw_files=[raw_file],
            normalized_files=[normalized_file],
            record_counts={"records": len(normalized)},
            warnings=[],
            license_notes="User is responsible for upstream provider license compliance.",
        )
        write_manifest(root / "provider_manifest.json", manifest)
        mark_verified(root)
        provider_summaries.append(
            {
                "provider": provider_name,
                "snapshot_id": snapshot,
                "record_count": len(normalized),
            }
        )
    top_manifest: dict[str, object] = {
        "mode": "explicit_fetch",
        "providers": provider_summaries,
        "normal_analysis_network_access": "disabled",
    }
    (cache_dir / "manifest.json").write_text(json.dumps(top_manifest, indent=2) + "\n")
    (cache_dir / "pathway_database_manifest.json").write_text(
        json.dumps(top_manifest, indent=2) + "\n"
    )
    return top_manifest


def _normalize(provider: object, payload: object, organism: str) -> list[object]:
    snapshot = "fetch_snapshot"
    if isinstance(
        provider, (OmniPathProvider, SignorProvider, ReactomeFIProvider, ReactomeContentProvider)
    ):
        if not isinstance(payload, list):
            raise ValueError("provider payload must be a list for network providers")
        return list(cast(list[object], provider.normalize(payload, snapshot, organism)))
    if isinstance(provider, (PantherProvider, ReactomeAnalysisProvider)):
        if not isinstance(payload, (list, dict)):
            raise ValueError("provider payload must be a list or object for enrichment providers")
        return list(cast(list[object], provider.normalize(payload, snapshot, organism)))
    return []


def _recorded_payload(
    config: HarnessConfig, provider_name: str
) -> list[dict[str, object]] | dict[str, object]:
    normalized = provider_name.strip().lower().replace("-", "_")
    if normalized in {"omnipath", "signor", "reactome_fi", "reactome_content"}:
        rows = read_network(config.pathway.network_file).to_dict("records")
        payload: list[dict[str, object]] = []
        for index, row in enumerate(rows, start=1):
            source = str(row.get("source", ""))
            target = str(row.get("target", ""))
            sign = str(row.get("sign", "unsigned"))
            if normalized == "reactome_fi":
                payload.append({"id": index, "source": source, "target": target})
            elif normalized == "reactome_content":
                relation = (
                    "positive_regulator"
                    if sign == "positive"
                    else "negative_regulator"
                    if sign == "negative"
                    else "pathway_membership"
                )
                payload.append(
                    {
                        "event_id": index,
                        "source": source,
                        "target": target,
                        "pathway_id": "R-HSA-SYN",
                        "relation_type": relation,
                    }
                )
            elif normalized == "signor":
                payload.append(
                    {
                        "SIGNOR_ID": index,
                        "source": source,
                        "target": target,
                        "effect": sign,
                        "PMID": f"PMID{index}",
                    }
                )
            else:
                payload.append(
                    {
                        "id": index,
                        "source": source,
                        "target": target,
                        "sign": sign,
                        "sources": "SIGNOR" if index == 1 else "OmniPath",
                        "references": f"PMID{index}",
                        "is_directed": True,
                    }
                )
        return payload
    regulons = read_regulons(config.pathway.regulon_file).to_dict("records")
    pathway_rows = [
        {
            "pathway_id": f"SYN-{index}",
            "pathway_name": str(row.get("regulon", "Synthetic pathway")),
            "gene": str(row.get("target", "")),
            "matched_genes": str(row.get("target", "")),
            "number_in_list": 1,
            "expected": 0.5,
            "fold_enrichment": 2.0,
            "pValue": 1.0,
            "fdr": 1.0,
            "dataset": "PANTHER_PATHWAY",
        }
        for index, row in enumerate(regulons, start=1)
    ]
    if normalized == "reactome":
        return {
            "pathways": [
                {
                    "stId": row["pathway_id"],
                    "name": row["pathway_name"],
                    "entities": {"found": [row["gene"]], "fdr": 1.0, "pValue": 1.0},
                    "foundEntities": 1,
                    "expected_count": 0.5,
                }
                for row in pathway_rows
            ]
        }
    return pathway_rows
