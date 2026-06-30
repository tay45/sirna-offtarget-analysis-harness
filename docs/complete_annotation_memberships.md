# Complete Annotation Memberships

Production local ORA requires complete annotation membership snapshots. A term
membership reconstructed only from submitted enrichment hits is marked
`submitted_hit_only` and is excluded from production local ORA by default.

The pathway stage writes:

- `annotation_memberships.tsv`
- `annotation_membership_manifest.json`
- `annotation_membership_coverage.tsv`
- `incomplete_annotation_terms.tsv`

This prevents pathway size and contingency tables from being derived from only
the submitted significant genes.
