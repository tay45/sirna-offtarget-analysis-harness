from __future__ import annotations

from pathlib import Path
from typing import Any

from sirna_offtarget.pathway.providers.base import CachedProviderSnapshot, load_cached_records
from sirna_offtarget.pathway.providers.models import ProviderEdgeEvidenceRecord
from sirna_offtarget.pathway.providers.normalization import lineage_key


class ReactomeFIProvider:
    name = "reactome_fi"
    provider_name = "reactome_fi"
    provider_version = "offline-cache"
    production_provider = True
    edge_semantics = "unsigned functional connectivity unless independently supported"
    supported_organisms = ("human",)
    required_columns = ("source", "target")

    def parse_raw(
        self, rows: list[dict[str, Any]], snapshot_id: str, organism: str
    ) -> list[ProviderEdgeEvidenceRecord]:
        records: list[ProviderEdgeEvidenceRecord] = []
        for index, row in enumerate(rows, start=1):
            source = str(row.get("source") or row.get("gene1") or "").upper()
            target = str(row.get("target") or row.get("gene2") or "").upper()
            key = lineage_key(
                source,
                target,
                "functional_interaction",
                "unsigned",
                "reactome_fi",
                str(row.get("id") or index),
            )
            records.append(
                ProviderEdgeEvidenceRecord(
                    evidence_id=f"reactome_fi:{snapshot_id}:{index}",
                    provider=self.name,
                    access_route="reactome_fi",
                    source=source,
                    target=target,
                    source_identifier=str(row.get("source") or source),
                    target_identifier=str(row.get("target") or target),
                    directed=False,
                    sign="unsigned",
                    relation_type="functional_interaction",
                    mechanism="reactome_fi_unsigned_functional_support",
                    functional_only=True,
                    causal_eligible=False,
                    original_sources=("reactome_fi",),
                    references=(),
                    organism=str(row.get("organism") or organism),
                    evidence_level="functional",
                    provider_record_id=str(row.get("id") or index),
                    database_version=str(row.get("database_version") or self.provider_version),
                    retrieval_snapshot=snapshot_id,
                    predicted_only=False,
                    lineage_key=key,
                    warnings=("Reactome FI-only evidence is unsigned and non-causal.",),
                )
            )
        return records

    def normalize(
        self, raw: list[dict[str, Any]], snapshot_id: str, organism: str
    ) -> list[ProviderEdgeEvidenceRecord]:
        return self.parse_raw(raw, snapshot_id, organism)

    def load_cached(self, cache_dir: str | Path) -> CachedProviderSnapshot:
        return load_cached_records(cache_dir, self.name, self.required_columns)
