# Artifact Handoff

Downstream stages consume committed upstream artifacts, not raw recomputation of upstream scientific
stages. A successful attempt writes temporary files in `working/outputs/`; only after validation are
those files atomically promoted to `committed/outputs/`.

Failed attempts keep their diagnostics and partial outputs, but downstream stages cannot consume
anything from `working/` or `partial_outputs/`.
