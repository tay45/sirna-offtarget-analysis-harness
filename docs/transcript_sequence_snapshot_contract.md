# Transcript Sequence Snapshot Contract

A production transcript sequence snapshot is a local directory containing a manifest and a
JSONL records artifact. The manifest must declare:

- `snapshot_id`
- `provider`
- `release`
- `organism`
- `assembly`
- `transcript_identifier_namespace`
- `transcript_count`
- `sequence_file_checksum`
- `verification_status`
- `generation_method`

The stage requires `verification_status: verified` when
`transcript_targetability.require_verified_transcript_sequence_snapshot` is true. Every
eligible transcript from the committed isoform-uncertainty weights must have exactly one
matching sequence record assigned to the same canonical gene.
