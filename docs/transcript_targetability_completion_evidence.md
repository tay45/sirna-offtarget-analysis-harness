# Transcript Targetability Completion Evidence

This pass completes correctness requirements for transcript targetability:

- intended-target transcript validation requires an actual acceptable site;
- guide length limits are enforced before matching;
- active seed-policy fields control runtime;
- unsupported seed-policy options fail validation;
- missing transcript sequence behavior is explicit;
- mismatch artifacts contain only mismatches;
- passenger search is explicitly unsupported;
- N, M, and M/N remain not started.

Final correction evidence:

- verification reloads original transcript sequence records;
- transcript checksums and transcript slices are recomputed independently;
- coordinated internally consistent but false site records are rejected;
- `fail_gene` creates gene-failure records and removes canonical sites for the
  failed gene;
- intended-target policy fields actively control runtime behavior.
