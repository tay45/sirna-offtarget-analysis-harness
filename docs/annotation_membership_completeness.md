# Annotation Membership Completeness

Allowed completeness values are `complete`, `partial`, `submitted_hit_only`,
and `unknown`.

Production local ORA accepts only `complete` memberships unless an explicit
research override disables complete-membership enforcement. `submitted_hit_only`
records are never treated as full pathway membership because they do not define
the denominator for a valid contingency table.

When `pathway.enrichment.annotation_cache_dir` is configured, the pathway stage
loads verified annotation snapshots and calculates local ORA from:

```text
background genes ∩ complete term membership
```
