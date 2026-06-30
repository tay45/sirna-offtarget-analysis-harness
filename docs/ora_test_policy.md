# ORA Test Policy

Local over-representation analysis uses exactly one configured primary test.

Default policy:

```yaml
pathway:
  enrichment:
    local_ora:
      primary_test: fisher_exact_greater
      calculate_diagnostic_alternative: true
      require_complete_membership: true
```

Supported primary tests are `fisher_exact_greater` and `hypergeometric_upper_tail`.
The non-primary test may be emitted as a diagnostic value, but the pipeline never
selects `min(fisher, hypergeometric)` as the primary p-value.

Every local ORA result records `primary_test_method`, `primary_raw_p_value`,
`diagnostic_test_method`, `diagnostic_raw_p_value`, and `test_policy_version`.
