# Run Verification

`sirna-offtarget verify --run-dir RUN` checks run structure, stage manifests, committed contract integrity, dependency consumption, atomic commit state, attempt history, and invalidation state.

Verification writes `verification_report.json` and `verification_report.html` in the run directory. A valid run exits with status 0; invalid runs exit nonzero.

Runs stopped intentionally with `--until-stage` record a planned terminal stage and verify only the expected completion boundary.
