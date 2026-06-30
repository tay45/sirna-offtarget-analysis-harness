# Self-Referential Checksum Policy

A file cannot safely contain the checksum of its own complete final bytes unless a special canonicalization scheme excludes the checksum field. This project does not use such a scheme for isoform uncertainty metadata.

Policy:

- `isoform_uncertainty_run_v1.json` does not store its own final-file checksum.
- `isoform_uncertainty_result_v1.json` does not store its own final-file checksum.
- Both records use `self_checksum_status = recorded_in_outer_manifest`.
- Both may reference immutable scientific artifacts by checksum.
- The committed stage manifest is the authority for final byte checksums of metadata files.

The deprecated `output_checksums` field remains accepted for older records, but new isoform uncertainty metadata uses `referenced_artifact_checksums`.
