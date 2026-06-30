# Network Visual Semantics V2

Mechanistic SVG output now includes non-color semantics:

- positive edges use `activation-arrow`
- negative edges use `inhibition-bar`
- conflicting edges use `conflict-diamond`
- unsigned/unknown edges use dash patterns

GraphML edges include `graph_layer` and `marker_semantics`, including
`activation_arrow`, `inhibition_bar`, `unsigned_dashed`,
`conflicting_double`, and `unknown_dash_dot`.
