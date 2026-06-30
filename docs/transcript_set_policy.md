# Transcript Set Policy

The annotated transcript set is the set present in the configured annotation snapshot.

The eligible transcript set is the subset that passes `TranscriptSetPolicyV1`. The conservative default:

- requires the transcript to belong to the canonical resolved gene,
- requires organism and assembly match,
- requires a valid transcript identifier,
- requires a sequence reference for future sequence analysis,
- preserves transcript biotype and transcript version,
- excludes deprecated transcripts and alternative contigs by default,
- preserves every exclusion reason.

This is not the expressed transcript set and not the future siRNA-targetable transcript set.
