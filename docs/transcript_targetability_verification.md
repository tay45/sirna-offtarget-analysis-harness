# Transcript Targetability Verification

Canonical verification reloads the original transcript snapshot artifact and
does not trust stored site-derived values as source truth.

The verifier checks snapshot verification status, transcript lookup by ID and
version, gene assignment, transcript sequence checksum recomputation, coordinate
bounds, transcript slice extraction, guide reverse-complement search sequence,
aligned-position rows, mismatch rows, mismatch-region counts, paired-base
counts, evidence class, cleavage status, seed-only status, site ID, ranking,
evidence counts, best site, failed-gene states, and intended-target validation
references.

Verification failure marks outputs failed and reports typed error strings with
the transcript, site, or field where possible.
