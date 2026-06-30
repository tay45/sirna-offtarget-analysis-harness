# Release Coverage Evidence Policy

Release coverage evidence must come from a fresh `coverage.xml` generated after the final source changes.

Required command:

```bash
pytest --cov=src/sirna_offtarget --cov-branch --cov-report=term-missing --cov-report=xml --cov-fail-under=92
python scripts/check_coverage_thresholds.py coverage.xml --min-line-rate 0.92 --min-branch-rate 0.85
```

`release_manifest.json` and `LATEST.md` record exact line rate, branch rate, statement counts, branch counts, coverage XML checksum, generation timestamp, and the source-tree checksum associated with that coverage report.
