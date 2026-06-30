# Output Verification

`sirna-offtarget verify --run-dir RUN_DIRECTORY` checks current pointers, stage manifests, committed
contracts, output existence, output checksums, dependency consistency, and atomic commit completeness.

If a committed artifact is corrupted, verify returns nonzero. A subsequent resume starts from the
corrupted stage and invalidates downstream dependents while preserving unaffected upstream attempts.
