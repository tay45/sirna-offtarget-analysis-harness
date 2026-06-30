# Evidence Quality Components V2

`calculate_evidence_quality_v2` computes transparent component scores and caps.

Mandatory caps currently represented:

- unsigned functional-only evidence cannot become high causal evidence
- missing direction or sign caps causal confidence
- predicted-only support cannot be high
- unknown entities cap causal use as insufficient

The score is deterministic software provenance, not biological validation.
