from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sirna_offtarget.pathway.providers.base import CachedProviderSnapshot, load_cached_records
from sirna_offtarget.pathway.providers.models import PathwayEnrichmentProviderRecord


class ReactomeAnalysisProvider:
    name = "reactome_analysis"
    provider_name = "reactome_analysis"
    provider_version = "offline-cache"
    production_provider = True
    explicit_fetch_required = True
    supported_organisms = ("human", "mouse", "rat")
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
        rows = _reactome_rows(payload)
        response_checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        records: list[PathwayEnrichmentProviderRecord] = []
        for index, row in enumerate(rows, start=1):
            matched = tuple(
                sorted(
                    str(gene).upper() for gene in row.get("entities", {}).get("found", ()) if gene
                )
            )
            submitted = int(row.get("submitted_gene_count") or len(matched))
            background = int(
                row.get("background_gene_count") or max(len(tested_gene_universe), submitted, 1)
            )
            observed = int(row.get("observed_count") or row.get("foundEntities") or len(matched))
            expected = float(
                row.get("expected_count") or row.get("entities", {}).get("ratio", 0.0) or 0.0
            )
            adjusted = float(
                row.get("entities", {}).get("fdr") or row.get("adjusted_p_value") or 1.0
            )
            raw_p = float(
                row.get("entities", {}).get("pValue") or row.get("raw_p_value") or adjusted
            )
            records.append(
                PathwayEnrichmentProviderRecord(
                    provider=self.name,
                    annotation_source="reactome",
                    term_id=str(row.get("stId") or row.get("pathway_id") or f"reactome:{index}"),
                    term_name=str(row.get("name") or row.get("pathway_name") or ""),
                    gene_set_category=gene_set_category,
                    expression_direction=expression_direction,
                    observed_count=observed,
                    expected_count=expected,
                    fold_enrichment=observed / expected if expected else 0.0,
                    raw_p_value=raw_p,
                    adjusted_p_value=adjusted,
                    matched_genes=matched,
                    submitted_gene_count=submitted,
                    background_gene_count=background,
                    tested_gene_universe=tested_gene_universe,
                    organism=organism,
                    database_version=str(row.get("release") or self.provider_version),
                    retrieval_snapshot=snapshot_id,
                    request_checksum=response_checksum[:24],
                    response_checksum=response_checksum,
                    warnings=(),
                )
            )
        return records

    def normalize(
        self, raw: dict[str, Any] | list[dict[str, Any]], snapshot_id: str, organism: str
    ) -> list[PathwayEnrichmentProviderRecord]:
        return self.parse_raw(raw, snapshot_id=snapshot_id, organism=organism)

    def load_cached(self, cache_dir: str | Path) -> CachedProviderSnapshot:
        return load_cached_records(
            cache_dir,
            self.name,
            self.required_columns,
            ("reactome_analysis.tsv", "reactome.tsv", "reactome_analysis.json"),
        )


def _reactome_rows(payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    rows = payload.get("pathways")
    if isinstance(rows, list):
        return rows
    token = payload.get("results")
    if isinstance(token, list):
        return token
    return []
