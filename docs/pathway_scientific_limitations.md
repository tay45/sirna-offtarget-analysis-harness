# Pathway scientific limitations

The harness separates observed/provider-supported evidence from inference, but pathway conclusions
remain limited by database coverage, identifier ambiguity, cell-context mismatch, missing temporal
measurements, unsigned functional interactions, and provider-specific curation choices.

Current implementation limitations:

- Public fetch is explicit and testable, but official production endpoint variation is not
  exhaustively fixture-covered.
- Identifier resolution is centralized, but no full licensed HGNC/Ensembl/UniProt alias snapshot is
  bundled.
- Evidence quality scores are rule-based transparency signals, not calibrated posterior
  probabilities.
- Enrichment results are contextual and should not be read as causal mechanism evidence.
- Reactome FI and other functional-only edges are unsigned/contextual unless another provider
  supplies signed mechanistic evidence.
- Topology SVG/GraphML shows normalized provider consensus but does not prove biological causality.
