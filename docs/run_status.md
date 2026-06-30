# Run Status

`run_status.json` records run-level lifecycle state, active config revision, planned boundary, current and last successful stages, failed or interrupted stage, verification state, warning/error counts, attempt counts, reuse counts, and resume guidance.

Partial runs use `partially_completed` when the requested terminal stage completed successfully.
