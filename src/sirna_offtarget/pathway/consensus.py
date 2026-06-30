def consensus_sources(sources: list[str]) -> tuple[str, ...]:
    return tuple(sorted(set(sources)))
