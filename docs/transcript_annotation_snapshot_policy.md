# Transcript Annotation Snapshot Policy

Production isoform uncertainty requires an explicit verified transcript annotation snapshot.

Required metadata:

- provider
- release
- organism
- assembly
- transcript identifier namespace
- gene identifier namespace
- source-file checksum
- snapshot ID
- verification status

The system must not download an uncontrolled latest annotation, select the first directory entry, mix assemblies, mix organisms, or silently change transcript releases between runs.
