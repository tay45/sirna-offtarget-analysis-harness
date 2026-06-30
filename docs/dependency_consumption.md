# Dependency Consumption

Stage code explicitly records consumed dependency payload sections and artifact logical names through the run context.

Each record includes dependency stage, dependency type, contract name/version, contract checksum, consumed artifacts, and consumed payload fields.

Verification fails when a declared data dependency lacks a consumption record or when a stage consumes an undeclared dependency.
