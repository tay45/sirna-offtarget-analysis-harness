# Reactome Membership Loader

Accepted input is a normalized Reactome membership TSV or CSV with:

- `pathway_id`
- `pathway_name`
- `reference_entity_id`
- `gene`

Optional fields include `hierarchy_parent_ids`, `provider_release`, `completeness_status`, `membership_type`, and `warnings`.

The loader stores records as annotation membership snapshot V2 with provider `reactome` and annotation source `REACTOME_PATHWAY`. Missing required columns raise a validation error.
