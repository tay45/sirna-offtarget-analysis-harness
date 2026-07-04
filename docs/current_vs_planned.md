# Current vs Planned

| Component | Status | Purpose |
| --- | --- | --- |
| Expression normalization | Implemented | Establish comparable gene-expression changes |
| Isoform uncertainty | Implemented | Define eligible transcript set and equal prior |
| Transcript targetability | Implemented | Identify sequence-compatible direct targets |
| N/M/M/N | Implemented | Estimate targetable transcript fraction |
| Pathway evidence architecture | Implemented | Preserve mechanistic relationships |
| Intended-target calibration | Implemented | Estimate targetable-transcript knockdown from intended target expression and M/N |
| Expected direct effect | Implemented | Predict direct expression decrease from calibration and candidate M/N |
| Unresolved residual value | Implemented | Store observed minus expected log2 change without attribution |
| Residual support characterization | Implemented | Summarize residual direction, magnitude, and optional pathway support without final attribution |
| Secondary evidence integration | Implemented | Integrate sequence, expected direct-effect, unresolved residual, and pathway-support evidence into classification-ready records |
| Final evidence classification | Implemented | Emit conservative evidence labels, not definitive biological or regulatory conclusions |
| External benchmark validation | Planned | Validate and tune evidence labels against real perturbation datasets |
