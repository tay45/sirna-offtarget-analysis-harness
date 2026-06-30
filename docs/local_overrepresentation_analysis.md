# Local Overrepresentation Analysis

Local ORA uses cached provider annotation membership with the tested background
universe. It computes Fisher exact greater-tail and hypergeometric upper-tail
p-values, takes the conservative minimum, and applies Benjamini-Hochberg FDR.

Results are labeled `locally_calculated_from_provider_annotations`; provider
native results remain labeled separately and are not mixed.
