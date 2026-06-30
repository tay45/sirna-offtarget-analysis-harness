# Coverage Policy

Line coverage must remain at least 92 percent.

Branch coverage is measured with coverage.py branch tracking and checked from `coverage.xml` by:

```bash
python scripts/check_coverage_thresholds.py coverage.xml --min-line-rate 0.92 --min-branch-rate 0.85
```

The XML gate checks line-rate and branch-rate independently so branch coverage cannot be hidden by the aggregate `fail_under` setting.
