# Selective Invalidation

Invalidation follows the DAG. A changed input, relevant configuration section, checksum mismatch,
schema mismatch, or forced stage invalidates the affected stage and its downstream dependents while
preserving unaffected upstream stages.

Examples:

- Pathway configuration changes affect pathway, mechanistic, scoring, classification,
  visualization, reporting, and validation stages.
- Guide sequence changes affect sequence-dependent stages and downstream reporting.
- Expression count changes affect expression, isoform, pathway, mechanistic, scoring,
  classification, visualization, reporting, and validation stages.

Use `sirna-offtarget plan --config project.yaml --resume` to inspect the proposed action and
explanation for each stage before executing.
