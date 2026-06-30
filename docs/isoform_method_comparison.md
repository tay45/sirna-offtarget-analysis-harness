# Isoform Method Comparison

Short-read RNA-seq methods differ in what they estimate and how much transcript ambiguity they can resolve.

| Method | Role | Limitations for this pass |
| --- | --- | --- |
| Salmon | Transcript quantification from read compatibility and annotation | Estimates depend on annotation, equivalence classes, and model assumptions; outputs can be optional external evidence, not transcript truth. |
| kallisto | Transcript abundance from pseudoalignment | Shared exons and multimapping reads remain model-resolved; suitable only as provenance-rich external evidence. |
| RSEM | Transcript/gene abundance estimation | Requires annotation and alignment/model assumptions; not an observed transcript-specific fold change. |
| StringTie | Transcript assembly and quantification | Can introduce assembled transcript models; release/provenance must be explicit. |
| featureCounts/gene-level counting | Gene-level summarization | Does not identify transcript proportions and cannot split gene-level effects among transcripts. |
| tximport-style summarization | Transcript-to-gene aggregation | Useful for gene-level summaries; reverse splitting from gene to transcript is not valid. |
| Annotation-only enumeration | Lists candidate transcripts | Provides eligible transcript sets but no abundance. |
| Precomputed transcript proportions | External evidence | Accepted only when annotation, organism, assembly, checksum, and sums validate. |

Default policy: consume validated precomputed transcript proportions when supplied; otherwise use equal-transcript prior. This pass does not run a transcript quantifier.
