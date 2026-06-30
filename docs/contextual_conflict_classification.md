# Contextual Conflict Classification

`ContextualConflictSummaryV1` distinguishes global, context-specific, and
unresolved context conflicts.

- Overlapping known contexts can produce `global_sign_conflict`.
- Non-overlapping known contexts produce `context_specific_conflict`.
- Missing contexts produce `unresolved_context_conflict`.

This prevents non-overlapping biological contexts from being reported as a
universal contradiction.
