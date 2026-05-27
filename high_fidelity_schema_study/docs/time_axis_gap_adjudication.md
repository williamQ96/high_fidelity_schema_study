# Time-Axis Gap Adjudication

Status: adjudicated as a known evaluation/extraction boundary for the current Artifact Paper convergence round.

## Observed Facts

Source: `docs/paper_result_tables_2026-05-15.json` and `data/derived/internal_baseline_report.json`.

| Measure | Value |
| --- | ---: |
| Aggregate `time_axis_accuracy` | `0.6667` |
| CSV family `time_axis_accuracy` | `1.0000` |
| HDF5 family `time_axis_accuracy` | `1.0000` |
| Time-series family `time_axis_accuracy` | `0.0000` |
| Error-mode count for `time_axis_mismatch` | `3` |

Affected internal datasets in the baseline report:

- `ts_easy_hourly_weather`
- `ts_hard_irregular_buoy`
- `ts_medium_power_meter`

## Decision

Do not force a metric change in the current convergence round. Treat the gap as a known limitation and evaluation boundary in the paper and GUI.

Rationale:

- The frozen slice already reports the gap explicitly.
- Correctly resolving the gap may require deciding whether the time axis should be scored at dataset organization level, field level, or both.
- Changing the metric now would alter headline paper numbers and requires a separate evaluation-policy update.

## Paper Wording

Allowed:

- "Time-axis evaluation remains the clearest non-final gap in the frozen internal slice."
- "The time-series family currently scores `0.0000` on the time-axis metric despite otherwise strong physical, logical, semantic, and unit metrics."
- "Future work should adjudicate whether time-axis evidence is represented as a field-level claim, an organization-level profile, or both."

Avoid:

- "The deterministic extractor has fully solved time-series schema extraction."
- Any claim that hides `time_axis_accuracy = 0.6667` behind aggregate physical/logical/semantic metrics.

## Follow-Up If This Becomes A Paper Blocker

1. Define whether time-axis scoring is field-level, dataset-level, or both.
2. Add an explicit time-axis gold policy for time-series modality.
3. Rebuild derived schemas and internal baseline reports only after the policy is documented.
4. Regenerate paper tables and figures, then update this adjudication.

