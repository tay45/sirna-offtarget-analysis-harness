# Public Release Limitations

- The current release calculates an expected direct-effect estimate from normalized expression, intended-target calibration, and M/N.
- The current release stores observed-minus-expected log2 residuals as unresolved values before residual support characterization.
- The current release emits conservative evidence classification labels using deterministic, rule-based, evidence-preserving logic.
- The current release does not make definitive biological, clinical, toxicological, or regulatory conclusions.
- No production-scale biological benchmark has yet been completed.
- Optional ML-assisted evidence weighting, confidence calibration, and statistical/ML model comparison remain future work that requires external biological benchmark validation.
- The equal-transcript prior is deliberate under short-read isoform uncertainty.
- Seed-only evidence is preserved but excluded from default cleavage-compatible M.
- Passenger-strand analysis is not currently supported.
- Bulge and indel alignment are not currently supported.
- Pathway architecture and secondary evidence integration are implemented; external benchmark validation remains planned.
