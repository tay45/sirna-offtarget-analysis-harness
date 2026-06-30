from __future__ import annotations

from pathlib import Path
from typing import Any

from sirna_offtarget.pathway.providers.base import CachedProviderSnapshot, load_cached_records
from sirna_offtarget.pathway.providers.models import ProviderEdgeEvidenceRecord
from sirna_offtarget.pathway.providers.normalization import lineage_key, normalize_sign


class ReactomeContentProvider:
    name = "reactome_content"
    provider_name = "reactome_content"
    provider_version = "offline-cache"
    production_provider = True
    explicit_fetch_required = True
    supported_organisms = ("human", "mouse", "rat")
    required_columns = ("source", "target", "pathway_id")

    def parse_raw(
        self, rows: list[dict[str, Any]], snapshot_id: str, organism: str
    ) -> list[ProviderEdgeEvidenceRecord]:
        records: list[ProviderEdgeEvidenceRecord] = []
        for index, row in enumerate(rows, start=1):
            relation = str(row.get("relation_type") or row.get("role") or "pathway_membership")
            explicit = relation in {
                "positive_regulator",
                "negative_regulator",
                "explicit_regulation",
            }
            sign = normalize_sign(
                "positive"
                if relation == "positive_regulator"
                else "negative"
                if relation == "negative_regulator"
                else "unsigned"
            )
            source = str(row.get("source") or "").upper()
            target = str(row.get("target") or "").upper()
            key = lineage_key(
                source,
                target,
                relation,
                sign,
                "reactome_content",
                str(row.get("event_id") or index),
            )
            records.append(
                ProviderEdgeEvidenceRecord(
                    evidence_id=f"reactome_content:{snapshot_id}:{index}",
                    provider=self.name,
                    access_route="reactome_content",
                    source=source,
                    target=target,
                    source_identifier=source,
                    target_identifier=target,
                    directed=explicit,
                    sign=sign if explicit else "unsigned",
                    relation_type=relation,
                    mechanism=str(row.get("mechanism") or "reactome_event"),
                    functional_only=not explicit,
                    causal_eligible=explicit and sign in {"positive", "negative"},
                    original_sources=("reactome_content",),
                    references=(),
                    organism=str(row.get("organism") or organism),
                    evidence_level="curated_context",
                    provider_record_id=str(row.get("event_id") or row.get("id") or index),
                    database_version=str(row.get("database_version") or self.provider_version),
                    retrieval_snapshot=snapshot_id,
                    predicted_only=False,
                    lineage_key=key,
                    warnings=(
                        () if explicit else ("Reactome participation/membership is not causal.",)
                    ),
                )
            )
        return records

    def normalize(
        self, raw: list[dict[str, Any]], snapshot_id: str, organism: str
    ) -> list[ProviderEdgeEvidenceRecord]:
        return self.parse_raw(raw, snapshot_id, organism)

    def load_cached(self, cache_dir: str | Path) -> CachedProviderSnapshot:
        return load_cached_records(cache_dir, self.name, self.required_columns)
