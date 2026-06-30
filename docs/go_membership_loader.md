# GO Membership Loader

Accepted input is a normalized GO association TSV or CSV with:

- `go_id`
- `namespace`
- `gene`
- `evidence_code`
- `assigned_by`

Optional fields include `term_name`, `qualifier`, `provider_release`, `completeness_status`, and `warnings`.

The loader stores records as annotation membership snapshot V2 with provider `go` and annotation source `GO_ASSOCIATION`. Evidence and assignment columns are preserved through source provenance and normalized membership metadata where available.
