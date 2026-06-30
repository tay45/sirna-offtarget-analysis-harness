# Portfolio Integrity Repair Report

Status: COMPLETE

Baseline archive: sirna-offtarget-portfolio-ready-2026-06-27.zip

Baseline archive SHA256:
3cc5856888a6373e525e5dd984c1743b62445a972c58e7ad7e186875a819bab7

Baseline source checksum:
c3b15fc715582207b3e4bf49b0f62da4c849b4ed6deeb241b9efb449393348b1

Candidate-scoring diagnosis: candidate scoring was a legacy prototype stage that
exceeded the current validated scope. It generated direct-effect and
classification-like payloads even when the documented public quick-start stopped
at transcript_targetability_ratio.

Repair action:

- Removed candidate_scoring and downstream classification/reporting stages from
  the official stage DAG and official stage contract registry.
- Changed until-stage execution to use the requested stage's transitive
  prerequisites instead of slicing a global topological order.
- Made the official default pipeline stop at transcript_targetability_ratio.
- Made the score-candidates CLI command reject the legacy prototype path.
- Regenerated the public portfolio summary from canonical ratio and
  targetability artifacts using evidence-only language.

Official current stage registry:

1. validate
2. prepare_inputs
3. map_identifiers
4. sequence_analysis
5. expression_analysis
6. isoform_uncertainty
7. transcript_targetability
8. transcript_targetability_ratio

Current terminal stage: transcript_targetability_ratio.

Portfolio quick-start stage list:

validate, prepare_inputs, map_identifiers, sequence_analysis,
expression_analysis, isoform_uncertainty, transcript_targetability,
transcript_targetability_ratio.

Prohibited-field scan: current public portfolio outputs contain no
direct_effect_score, direct_effect_tier, final_classification, risk, or
classification-like fields.

Scientific regression: current validated expression, isoform uncertainty,
transcript targetability, N, M, and M/N artifacts were preserved.

Remaining limitations:

- Intended-target calibration is not implemented.
- Expected direct effect is not implemented.
- Residual attribution is not implemented.
- Secondary-effect integration is not implemented.
- Final classification remains planned.
