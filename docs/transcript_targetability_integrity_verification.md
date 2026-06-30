# Transcript Targetability Integrity Verification

The verifier recomputes site-level sequence evidence from the guide search sequence and
stored transcript site slice. It checks coordinates, alignment length, mismatch positions,
matched-base count, seed and central mismatch counts, evidence class, cleavage status,
seed-only status, ranking tuple, artifact references, and summary counts.

Stored classes are not trusted without recomputation.
