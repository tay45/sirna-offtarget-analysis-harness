# Expression Imported Status Policy

Imported tested, filtering, low-count, and model statuses are normalized through
`normalize_imported_status`. Known values map to canonical states such as
`tested`, `not_filtered`, `low_count`, `model_not_estimable`, and
`model_failure`.

Unknown imported labels become `imported_unknown` with a row warning, preserving
the fact that the source status was not one of the supported canonical states.
