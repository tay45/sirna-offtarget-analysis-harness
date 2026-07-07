# Residual Attribution Pathway Support

Residual attribution can consume candidate-level mechanistic/pathway support when the staged run includes a committed `MechanisticNetworkResultV2` payload.

## Data Flow

```text
mechanistic_network
  -> MechanisticNetworkResultV2
  -> candidate-level PathwaySupportEvidence records
  -> residual_attribution
  -> secondary_evidence_integration
  -> final_evidence_classification
```

The residual attribution stage converts signed and unsigned/context paths from the mechanistic network payload into candidate-level support records before calling `compute_residual_attribution`.

## Configuration

```yaml
residual_attribution:
  use_mechanistic_pathway_support: true
  pathway_support_source: mechanistic_network
```

When `use_mechanistic_pathway_support` is true, residual attribution loads the committed mechanistic-network result and sets `pathway_evidence_available=True` only after that payload is available. This prevents missing pathway evidence from being interpreted as negative evidence.

## Interpretation Rules

- Missing pathway evidence remains unresolved, not negative.
- Available pathway evidence with no candidate support is recorded as residual without pathway support.
- Signed mechanistic paths can contribute causal-direction context when the path is fully signed.
- Unsigned and context-only paths are preserved as supporting context but are not treated as causal direction support.
- Mechanistic support may contribute to downstream `secondary_supported` and `mixed_supported` labels after secondary evidence integration and final classification.

## Boundaries

Residual attribution does not make final direct, secondary, or mixed calls. It preserves residual magnitude, support status, provenance, and uncertainty for downstream evidence integration.

