# Path Resolution

Relative input paths are resolved relative to the YAML configuration file, not the current shell working directory.

Resolved paths are normalized before hashing and are written to resolved config history. Original YAML content remains unchanged.

Contracts prefer run-relative artifact paths for portability.
