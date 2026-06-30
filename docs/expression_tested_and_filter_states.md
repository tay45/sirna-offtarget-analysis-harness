# Expression Tested And Filter States

Imported `tested_column`, `filter_status_column`, `low_count_column`, `model_status_column`, and `exclusion_reason_column` are preserved when configured. Harness thresholds may create separate descriptive flags, but they must not overwrite imported tested or filtering states.

Rows tested by the source analysis are not relabeled untested solely because `baseMean` is below a harness threshold.
