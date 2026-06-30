# Expression to Isoform Required Fields

This document records the expression fields read by the current isoform stage.
It is intentionally limited to the existing isoform implementation and does not
define new transcript-level, direct-effect, secondary-effect, or classification logic.

## Current Reads

| Field | Where read | Why needed | V2 always provides it | May be null | Safe behavior when unavailable | Scientific input or display metadata |
| --- | --- | --- | --- | --- | --- | --- |
| Gene key | `analyze_isoforms_from_gene_effect_inputs`, expression input lookup by transcript gene | Joins a transcript gene to a V2-derived expression input record | Yes for included records, using approved symbol or original gene ID as the read-only view key | No for included records | Exclude from isoform input when canonical gene ID is unresolved | Scientific input boundary |
| `control_abundance_summary` | `analyze_isoforms_from_gene_effect_inputs`, before `inferred_targetable_fraction` | Existing inferred targetable fraction calculation needs control abundance when it is available | No | Yes | Preserve null, do not reconstruct, keep gene included, leave inferred fraction null with a warning | Scientific input when available |
| `treatment_abundance_summary` | `analyze_isoforms_from_gene_effect_inputs`, before `inferred_targetable_fraction` | Existing inferred targetable fraction calculation needs treatment abundance when it is available | No | Yes | Preserve null, do not reconstruct, keep gene included, leave inferred fraction null with a warning | Scientific input when available |

## Values Preserved But Not Required By The Current Isoform Calculation

| Field | Where read | Why needed | V2 always provides it | May be null | Safe behavior when unavailable | Scientific input or display metadata |
| --- | --- | --- | --- | --- | --- | --- |
| `canonical_log2_fold_change` | Adapter inclusion check and typed input artifact | Required to make the gene-level expression effect usable and auditable at the boundary | No | Yes | Exclude with `canonical_effect_unavailable` because numeric gene effect is unavailable | Scientific input boundary |
| `canonical_effect_source` | Adapter and typed input artifact | Distinguishes reported unshrunken effects from real shrunken effects | Yes | No | Preserve exactly; do not relabel unshrunken effects as shrunken | Scientific provenance |
| `shrunken_log2_fold_change` | Adapter and typed input artifact | Only populated when V2 says the canonical value came from shrinkage | No | Yes | Leave null for unshrunken canonical effects | Scientific provenance |
| `adjusted_p_value` | Adapter and typed input artifact | Current isoform logic does not use it, but downstream audit needs to know whether it was present | No | Yes | Preserve null and include the gene if other required fields are present | Display and provenance for this boundary |
| `replicate_consistency` | Typed input artifact only | V2 does not currently carry a validated replicate-consistency value | No | Yes | Keep null with `replicate_consistency_status = unavailable`; never use `1.0` as a placeholder | Display and provenance for this boundary |
| `tested_status`, `filter_status`, `low_count_status`, `model_status`, `statistical_support_status` | Adapter and typed input artifact | Preserve expression state and determine true exclusion reasons | Yes | No | Exclude only for states incompatible with a numeric gene-level effect, such as model failure or unsupported records | Scientific provenance |
| `warnings` | Input and exclusion artifacts | Preserve row-level caveats from Expression V2 | Yes | No | Carry forward unchanged, with adapter warnings appended for unavailable optional values | Display and provenance |

## Verified Non-Requirements

- The current isoform code does not read adjusted p-value for any calculation.
- The current isoform code does not read replicate consistency.
- The current isoform code does not require a shrunken fold change.
- Missing control or treatment abundance prevents only the inferred targetable fraction calculation; it does not make the gene unusable for the isoform stage.
- The adapter must not parse the original expression table and must not load a separate V1 expression artifact.
