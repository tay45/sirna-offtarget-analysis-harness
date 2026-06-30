from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sirna_offtarget.pathway.providers.base import CachedProviderSnapshot, load_cached_records
from sirna_offtarget.pathway.providers.models import PathwayEnrichmentProviderRecord


class PantherProvider:
    name = "panther"
    provider_name = "panther"
    provider_version = "offline-cache"
    production_provider = True
    supported_organisms = ("human", "mouse", "rat")
    annotation_datasets = (
        "PANTHER_PATHWAY",
        "REACTOME_PATHWAY",
        "GO_BIOLOGICAL_PROCESS",
        "GO_MOLECULAR_FUNCTION",
        "PANTHER_PROTEIN_CLASS",
    )
    required_columns = ("gene", "pathway_id", "pathway_name")

    def parse_raw(
        self,
        payload: dict[str, Any] | list[dict[str, Any]],
        *,
        snapshot_id: str,
        organism: str,
        gene_set_category: str = "changed",
        expression_direction: str = "mixed",
        tested_gene_universe: tuple[str, ...] = (),
    ) -> list[PathwayEnrichmentProviderRecord]:
        rows = _panther_rows(payload)
        checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        records: list[PathwayEnrichmentProviderRecord] = []
        for index, row in enumerate(rows, start=1):
            matched = tuple(sorted(str(gene).upper() for gene in _split(row.get("matched_genes"))))
            observed = int(
                float(row.get("number_in_list") or row.get("observed_count") or len(matched))
            )
            expected = float(row.get("expected") or row.get("expected_count") or 0.0)
            fold = float(
                row.get("fold_enrichment")
                or row.get("foldEnrichment")
                or (observed / expected if expected else 0.0)
            )
            raw_p = float(row.get("pValue") or row.get("raw_p_value") or 1.0)
            adjusted = float(row.get("fdr") or row.get("adjusted_p_value") or raw_p)
            records.append(
                PathwayEnrichmentProviderRecord(
                    provider=self.name,
                    annotation_source=str(
                        row.get("annotation_source") or row.get("dataset") or "PANTHER_PATHWAY"
                    ),
                    term_id=str(row.get("term_id") or row.get("pathway_id") or f"panther:{index}"),
                    term_name=str(row.get("term_name") or row.get("pathway_name") or ""),
                    gene_set_category=gene_set_category,
                    expression_direction=expression_direction,
                    observed_count=observed,
                    expected_count=expected,
                    fold_enrichment=fold,
                    raw_p_value=raw_p,
                    adjusted_p_value=adjusted,
                    matched_genes=matched,
                    submitted_gene_count=int(float(row.get("submitted_gene_count") or observed)),
                    background_gene_count=int(
                        float(
                            row.get("background_gene_count")
                            or max(len(tested_gene_universe), observed, 1)
                        )
                    ),
                    tested_gene_universe=tested_gene_universe,
                    organism=organism,
                    database_version=str(row.get("dataset_version") or self.provider_version),
                    retrieval_snapshot=snapshot_id,
                    request_checksum=checksum[:24],
                    response_checksum=checksum,
                    warnings=(
                        ("PANTHER REACTOME_PATHWAY shares Reactome annotation lineage.",)
                        if str(row.get("dataset")) == "REACTOME_PATHWAY"
                        else ()
                    ),
                )
            )
        return records

    def normalize(
        self, raw: dict[str, Any] | list[dict[str, Any]], snapshot_id: str, organism: str
    ) -> list[PathwayEnrichmentProviderRecord]:
        return self.parse_raw(raw, snapshot_id=snapshot_id, organism=organism)

    def load_cached(self, cache_dir: str | Path) -> CachedProviderSnapshot:
        return load_cached_records(cache_dir, self.name, self.required_columns)


def _panther_rows(payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    results = payload.get("results")
    if isinstance(results, dict):
        result = results.get("result")
        return result if isinstance(result, list) else []
    return results if isinstance(results, list) else []


def _split(value: object) -> tuple[str, ...]:
    return tuple(
        part.strip() for part in str(value or "").replace(",", ";").split(";") if part.strip()
    )
