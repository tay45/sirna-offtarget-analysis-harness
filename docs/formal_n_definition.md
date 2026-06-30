# Formal N Definition

N is the number of unique eligible transcripts for a gene from the committed
Isoform Uncertainty stage. It is derived from committed
`TranscriptPriorWeightRecordV1` records with eligible status and never from FASTA,
expression rows, targetability site counts, or unfiltered annotation records.

Genes with no eligible transcripts have `N = 0` and no definitive ratio.
