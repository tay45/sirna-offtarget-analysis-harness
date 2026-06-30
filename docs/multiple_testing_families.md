# Multiple Testing Families

Local ORA applies Benjamini-Hochberg correction within explicit correction
families instead of one global pool.

Default family key:

- provider
- annotation dataset
- gene set ID
- expression direction
- calculation mode

Each result records `correction_family_id`, `correction_family_size`,
`correction_method`, `adjusted_p_value`, and `correction_policy_version`.
This keeps, for example, upregulated Reactome local ORA separate from
downregulated Reactome local ORA and from provider-calculated PANTHER results.
