# Missing Transcript Sequence Policy

Missing transcript sequence behavior is explicit.

Supported modes:

- `record_unavailable_and_continue`: write sequence-unavailable transcript evidence and continue.
- `fail_stage`: fail the stage when any eligible transcript sequence is missing.
- `fail_gene`: currently treated as unavailable evidence for the transcript set and preserved for future aggregate policy.

An explicitly supplied intended-target transcript with unavailable sequence fails validation.
