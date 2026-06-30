# Guide Length Policy

Guide length is enforced before transcript matching.

The production cleavage policy defines `guide_length_min` and `guide_length_max`. Guides
below or above the configured interval fail validation and do not proceed to matching.
Accepted boundary lengths are recorded in `sirna_sequence_validation_v1.json` together with
the configured limits.
