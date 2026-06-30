# Expression Normalization Original Requirements

Date: 2026-06-24

## Captured Requirements

The requested recovery pass is limited to expression normalization and normalized gene-level effects. It must not reopen pathway/mechanistic architecture except for a minimal typed input interface that can consume committed normalized-expression records.

The pass must add comparison, decision, and limitation documentation before implementation. It must support explicit expression input modes, normalization provenance, a gene-level normalized-effect contract, a contrast contract, input validation, low-count and untested states, a downstream read-only interface, verification, and tests.

## Deferred By Requirement

This pass explicitly defers isoform allocation, N/M/MN logic, intended-target calibration, expected direct effect, residual effect, direct/secondary scoring, integration, and final classification.
