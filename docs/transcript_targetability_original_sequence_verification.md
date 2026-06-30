# Transcript Targetability Original Sequence Verification

The verifier treats the verified transcript-sequence snapshot as the source of
truth. Internal agreement among stored site sequence, alignment rows, mismatch
rows, counts, and evidence class is not sufficient.

For every canonical site, verification reloads
`transcript_sequence_snapshot_records_v1.jsonl`, resolves transcript ID and
version, checks gene assignment, recomputes the transcript checksum, extracts
the 0-based half-open transcript slice, and compares that slice with the stored
site sequence.

The verifier also recomputes guide reverse complement, aligned positions,
mismatch positions, mismatch regions, paired-base counts, evidence class, site
ID, ranking, best-site selection, and evidence aggregation. Coordinated fake
records that remain internally consistent but disagree with the original
transcript sequence are rejected.
