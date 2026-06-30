# Expression Committed Artifact Boundary

Committed expression loaders may read only artifacts listed in the current expression stage manifest and located under committed outputs. They must not fall back to arbitrary attempt outputs, failed attempt outputs, working directories, or temporary files.
