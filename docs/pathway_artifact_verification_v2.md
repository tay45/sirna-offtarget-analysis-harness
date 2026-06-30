# Pathway Artifact Verification V2

The pathway stage now emits policy and membership artifacts that can be checked
for scientific provenance:

- `pathway_scientific_policy_manifest.json`
- `annotation_membership_manifest.json`
- `incomplete_annotation_terms.tsv`
- `enrichment_correction_families.tsv`

Current verification coverage proves the primary ORA test policy, correction
family separation, and incomplete membership exclusion in unit tests. Full
semantic verification of every V2 artifact relationship remains future work.
