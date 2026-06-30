# Expression Downstream Transition

`NormalizedGeneEffectRecordV2` is the future canonical downstream expression input. Current `ExpressionAnalysisResultV1.expression_results` consumption remains transitional and deprecated. Downstream modules must not consume raw expression rows directly or renormalize expression.

This pass does not modify isoform scientific logic.
