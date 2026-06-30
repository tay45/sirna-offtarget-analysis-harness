class SyntheticPathwayProvider:
    name = "synthetic"
    production_provider = False
    test_only = True

    def load_cached(self, cache_dir: str) -> dict[str, str]:
        return {"cache_dir": cache_dir, "status": "synthetic fixture only"}
