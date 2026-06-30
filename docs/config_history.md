# Config History

Each run records immutable configuration revisions under `config_history/`. The first submitted YAML
is preserved as `run_config.original.yaml`; resolved configuration is written for the active
revision. Revision metadata stores hashes, parent revision, timestamp, reason, CLI overrides, and the
affected stage plan placeholder.
