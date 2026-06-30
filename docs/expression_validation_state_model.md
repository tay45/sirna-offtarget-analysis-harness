# Expression Validation State Model

Expression validation reports use explicit states: `passed`, `failed`,
`not_run`, `not_applicable`, and `warning`.

Precomputed imports mark sample-level model execution checks as
`not_applicable` because the external differential-expression model has already
run outside the harness.
