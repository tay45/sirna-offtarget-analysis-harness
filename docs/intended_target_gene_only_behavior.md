# Intended Target Gene-Only Behavior

Gene-only intended-target input does not prove isoform identity. The default
runtime behavior preserves uncertainty rather than marking validation passed.

Supported modes:

- `preserve_uncertainty`: record an uncertain validation status.
- `warning`: record a warning validation status.
- `fail_stage`: reject gene-only input.
- `accept_any_gene_transcript_site`: accept gene-level validation only if at
  least one eligible transcript from the intended gene has an acceptable site.

If the intended gene failed under `fail_gene`, intended-target validation cannot
pass using partial evidence from that gene.
