from __future__ import annotations

from pathlib import Path
from typing import Any

from sirna_offtarget.pathway.providers.base import CachedProviderSnapshot, load_cached_records
from sirna_offtarget.pathway.providers.models import ProviderEdgeEvidenceRecord
from sirna_offtarget.pathway.providers.normalization import lineage_key, normalize_sign


class SignorProvider:
    name = "signor"
    provider_name = "signor"
    provider_version = "offline-cache"
    production_provider = True
    explicit_fetch_required = True
    supported_organisms = ("human", "mouse", "rat")
    required_columns = ("source", "target", "effect")

    def parse_raw(
        self, rows: list[dict[str, Any]], snapshot_id: str, organism: str
    ) -> list[ProviderEdgeEvidenceRecord]:
        records: list[ProviderEdgeEvidenceRecord] = []
        for index, row in enumerate(rows, start=1):
            source = str(row.get("source") or row.get("ENTITYA") or "").upper()
            target = str(row.get("target") or row.get("ENTITYB") or "").upper()
            effect = str(row.get("effect") or row.get("EFFECT") or "")
            sign = normalize_sign(effect)
            references = _split(row.get("references") or row.get("PMID"))
            primary = references[0] if references else str(row.get("SIGNOR_ID") or index)
            key = lineage_key(source, target, "signor_effect", sign, "signor", primary)
            records.append(
                ProviderEdgeEvidenceRecord(
                    evidence_id=f"signor:{snapshot_id}:{index}",
                    provider=self.name,
                    access_route="signor",
                    source=source,
                    target=target,
                    source_identifier=str(row.get("source") or source),
                    target_identifier=str(row.get("target") or target),
                    directed=True,
                    sign=sign,
                    relation_type="signor_effect",
                    mechanism=str(row.get("mechanism") or row.get("MECHANISM") or effect),
                    functional_only=False,
                    causal_eligible=sign in {"positive", "negative"},
                    original_sources=("signor",),
                    references=references,
                    organism=str(row.get("organism") or organism),
                    evidence_level="curated",
                    provider_record_id=str(row.get("SIGNOR_ID") or row.get("id") or index),
                    database_version=str(row.get("database_version") or self.provider_version),
                    retrieval_snapshot=snapshot_id,
                    predicted_only=False,
                    lineage_key=key,
                    warnings=(),
                )
            )
        return records

    def normalize(
        self, raw: list[dict[str, Any]], snapshot_id: str, organism: str
    ) -> list[ProviderEdgeEvidenceRecord]:
        return self.parse_raw(raw, snapshot_id, organism)

    def load_cached(self, cache_dir: str | Path) -> CachedProviderSnapshot:
        return load_cached_records(cache_dir, self.name, self.required_columns)


def _split(value: object) -> tuple[str, ...]:
    return tuple(
        part.strip() for part in str(value or "").replace(",", ";").split(";") if part.strip()
    )
