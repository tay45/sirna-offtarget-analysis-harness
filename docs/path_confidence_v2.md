# Path Confidence V2

`PathConfidenceRecordV2` records path length, edge IDs, average edge quality,
minimum edge quality, bottleneck edge ID, bottleneck cap, raw score, capped
score, confidence level, and policy version.

The core invariant is:

```text
capped_score <= minimum_edge_quality_score
```

One weak edge therefore caps the whole path.
