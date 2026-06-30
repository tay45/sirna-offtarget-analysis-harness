# PANTHER Membership Loader

Accepted input is a normalized PANTHER membership TSV or CSV with:

- `annotation_dataset`
- `term_id`
- `term_name`
- `mapped_gene_id`
- `taxon`

Optional fields include `provider_release`, `completeness_status`, `membership_type`, and `warnings`.

The loader stores records as annotation membership snapshot V2 with provider `panther` and annotation source `PANTHER_PATHWAY`.
