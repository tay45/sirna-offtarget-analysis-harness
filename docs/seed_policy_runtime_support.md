# Seed Policy Runtime Support

| Field | Runtime support | Behavior |
| --- | --- | --- |
| `seed_start` | Implemented | Defines inclusive guide seed start coordinate. |
| `seed_end` | Implemented | Defines inclusive guide seed end coordinate. |
| `seed_length` | Implemented | Must equal `seed_end - seed_start + 1`. |
| `exact_seed_required` | Implemented | When true, allowed seed mismatches must be zero. |
| `allowed_seed_mismatches` | Implemented | Controls seed-only eligibility when exact seed is not contradictory. |
| `supplementary_pairing_requirement` | Validated | Only `record_only` and `not_required` are accepted. |
| `minimum_total_paired_bases` | Implemented | Seed-only sites must satisfy this paired-base minimum. |
| `maximum_total_mismatches` | Implemented | Seed-only sites must not exceed this total mismatch limit. |
| `allowed_bulges` | Unsupported | Any true value fails policy validation. |
| `allowed_indels` | Unsupported | Any true value fails policy validation. |
| `transcript_region_restrictions` | Unsupported | Any nonempty restriction fails policy validation. |

Unsupported options fail early instead of being silently ignored.
