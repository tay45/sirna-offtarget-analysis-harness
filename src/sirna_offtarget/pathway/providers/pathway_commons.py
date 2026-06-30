from __future__ import annotations

from pathlib import Path

from sirna_offtarget.pathway.providers.base import CachedProviderSnapshot, load_cached_records


class PathwayCommonsProvider:
    name = "pathway_commons"
    production_provider = True
    optional_semantic_backend = True

    required_columns = ("source", "target")

    def load_cached(self, cache_dir: str | Path) -> CachedProviderSnapshot:
        return load_cached_records(cache_dir, self.name, self.required_columns)
