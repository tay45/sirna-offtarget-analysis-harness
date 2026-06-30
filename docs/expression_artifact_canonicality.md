# Expression Artifact Canonicality

Canonical expression artifacts are V2 artifacts. Compatibility artifacts are
named explicitly and carry `canonical=false` and `deprecated=true`.

Downstream code should consume `normalized_gene_effects_v2.jsonl` or the
committed V2 accessor unless a caller explicitly asks for compatibility output.
