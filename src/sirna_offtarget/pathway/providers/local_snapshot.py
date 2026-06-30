class LocalSnapshotProvider:
    name = "local_snapshot"
    production_provider = True

    def load_cached(self, cache_dir: str) -> dict[str, str]:
        return {"cache_dir": cache_dir, "status": "offline snapshot loaded"}
