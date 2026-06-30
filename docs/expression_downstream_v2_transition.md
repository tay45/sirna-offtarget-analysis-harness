# Expression Downstream V2 Transition

`load_expression_effects_for_downstream` defaults to committed V2
`NormalizedGeneEffectRecordV2` records. V1 loading remains available only through
an explicit compatibility request.

This transition allows downstream consumers to preserve nullable effect,
identifier, filtering, and provenance states without relying on lossy V1
contracts.
