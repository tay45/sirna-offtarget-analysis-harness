def pathway_snapshot_manifest() -> dict[str, str]:
    return {
        "mode": "offline",
        "snapshot": "synthetic_snapshot_v1",
        "network_access": "disabled during analysis",
    }
