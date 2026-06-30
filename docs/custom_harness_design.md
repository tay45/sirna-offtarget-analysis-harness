# Custom Harness Design

This repository intentionally uses a custom domain-specific Python harness for siRNA off-target
analysis. It does not depend on Nextflow, Snakemake, CWL, WDL, Airflow, Luigi, cluster scheduling,
or cloud orchestration.

The execution layer is deliberately narrow: it checkpoints the existing scientific APIs, validates
typed stage contracts, preserves attempts, and resumes from the earliest invalid stage. Scientific
calculations remain isolated in the scientific packages.
