# Transcript Targetability Ratio Workflow Stage

`transcript_targetability_ratio` depends on committed Isoform Uncertainty and
committed Transcript Targetability. It does not depend on pathway, expression
magnitude, scoring, secondary effects, or classification.

The stage consumes committed artifacts, writes immutable ratio artifacts, verifies
them, and supports resume through normal stage fingerprints and dependency checks.
