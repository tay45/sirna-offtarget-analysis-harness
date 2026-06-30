# Manual Invalidation

Manual invalidation requests are stored in `invalidation_requests.json`. A request includes an id,
requested stage, downstream policy, timestamp, user, reason, status, and affected stages.

`sirna-offtarget plan` displays the effect of pending requests. The next run applies pending
requests once, reruns the affected stages, preserves old attempts, and marks requests consumed.
