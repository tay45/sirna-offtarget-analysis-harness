# Equal-Transcript Prior

When no valid transcript-proportion evidence is available, each eligible transcript receives weight `1 / K`, where `K` is the eligible transcript count.

This is a neutral uncertainty allocation rule. It is not a claim that transcripts are equally expressed.

Required states:

- `K = 0`: no weights, `no_eligible_transcripts`.
- `K = 1`: one weight of `1.0`, `single_eligible_transcript`.
- `K > 1`: equal weights summing to 1, `multiple_transcripts_equal_prior`.

Equal-prior weights are not multiplied by gene-level fold change and are not siRNA targetability metrics.
