from __future__ import annotations

from pathlib import Path
from typing import Any

from sirna_offtarget.pathway.providers.base import CachedProviderSnapshot, load_cached_records
from sirna_offtarget.pathway.providers.models import ProviderEdgeEvidenceRecord
from sirna_offtarget.pathway.providers.normalization import lineage_key, normalize_sign


class OmniPathProvider:
    name = "omnipath"
    provider_name = "omnipath"
    provider_version = "offline-cache"
    production_provider = True
    explicit_fetch_required = True
    supported_organisms = ("human", "mouse", "rat")
    required_columns = ("source", "target")

    def parse_raw(
        self, rows: list[dict[str, Any]], snapshot_id: str, organism: str
    ) -> list[ProviderEdgeEvidenceRecord]:
        records: list[ProviderEdgeEvidenceRecord] = []
        for index, row in enumerate(rows, start=1):
            source = str(row.get("source") or row.get("source_genesymbol") or "").upper()
            target = str(row.get("target") or row.get("target_genesymbol") or "").upper()
            stimulation = _bool(row.get("is_stimulation") or row.get("stimulation"))
            inhibition = _bool(row.get("is_inhibition") or row.get("inhibition"))
            sign = (
                normalize_sign(row.get("sign"), inhibition)
                if row.get("sign")
                else normalize_sign(stimulation, inhibition)
            )
            references = _split(row.get("references") or row.get("pmids"))
            original_sources = _split(
                row.get("sources") or row.get("source_databases") or "omnipath"
            )
            primary = references[0] if references else str(row.get("id") or index)
            key = lineage_key(source, target, "interaction", sign, original_sources[0], primary)
            records.append(
                ProviderEdgeEvidenceRecord(
                    evidence_id=f"omnipath:{snapshot_id}:{index}",
                    provider=self.name,
                    access_route="omnipath",
                    source=source,
                    target=target,
                    source_identifier=str(row.get("source") or source),
                    target_identifier=str(row.get("target") or target),
                    directed=_bool(row.get("is_directed") or row.get("directed"), default=True),
                    sign=sign,
                    relation_type=str(row.get("type") or "interaction"),
                    mechanism=str(row.get("mechanism") or "omnipath_interaction"),
                    functional_only=False,
                    causal_eligible=sign in {"positive", "negative"},
                    original_sources=original_sources,
                    references=references,
                    organism=str(row.get("organism") or organism),
                    evidence_level="curated" if references else "provider",
                    provider_record_id=str(row.get("id") or index),
                    database_version=str(row.get("database_version") or self.provider_version),
                    retrieval_snapshot=snapshot_id,
                    predicted_only=_bool(row.get("predicted") or row.get("predicted_only")),
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
    text = str(value or "")
    return tuple(part.strip() for part in text.replace(",", ";").split(";") if part.strip())


def _bool(value: object, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
