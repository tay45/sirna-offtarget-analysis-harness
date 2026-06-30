# Provider Evidence Runtime

`build_provider_edge_evidence_v2` converts normalized provider/local edge rows into `ProviderEdgeEvidenceRecordV2`.

The builder records directedness, sign, mechanism, directness, functional-only status, causal eligibility, provider/database provenance, references, organism, context fields where present, prediction status, identifier snapshot ID, provider snapshot ID, and provider version.

Evidence quality is calculated after evidence construction; parsers do not assign quality.
