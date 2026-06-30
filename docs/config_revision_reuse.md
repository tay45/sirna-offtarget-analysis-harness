# Config Revision Reuse

Configuration revisions are created only when original config hash, resolved config hash, or CLI override content changes.

Unchanged resumes reuse the active revision and append a config-history event instead of creating duplicate revision files.

Original YAML snapshots are preserved as submitted; resolved YAML contains normalized paths and defaults.
