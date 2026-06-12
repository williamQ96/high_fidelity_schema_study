# Phase 12 Deterministic Substrate Experiment

This report is generated from the isolated Phase 12 challenge pack. It does not replace frozen paper metrics.

## Metrics

| Metric | Value |
| --- | ---: |
| case_count | 13 |
| temporal_case_count | 9 |
| format_detection_accuracy | 1.0000 |
| extractor_routing_accuracy | 1.0000 |
| structured_failure_artifact_completeness | 1.0000 |
| time_axis_selection_accuracy | 1.0000 |
| per_property_temporal_accuracy | 1.0000 |
| exact_temporal_profile_accuracy | 1.0000 |
| abstention_precision | 1.0000 |
| abstention_recall | 1.0000 |
| reason_code_coverage | 1.0000 |
| evidence_coverage | 1.0000 |
| unsupported_promotion_count | 0 |

## Cases

| Case | Type | Status | Format | Routing | Abstention | Temporal exact |
| --- | --- | --- | --- | --- | --- | --- |
| utc_z_regular | temporal | success | pass | pass | pass | pass |
| positive_offset | temporal | success | pass | pass | pass | pass |
| naive_timezone_unknown | temporal | success | pass | pass | pass | pass |
| mixed_offsets_conflicted | temporal | success | pass | pass | pass | pass |
| missing_interval | temporal | success | pass | pass | pass | pass |
| irregular_series | temporal | success | pass | pass | pass | pass |
| split_date_parts | temporal | success | pass | pass | pass | pass |
| ambiguous_time_candidates | temporal | success | pass | pass | pass | pass |
| date_attribute_only | temporal | success | pass | pass | pass | pass |
| opaque_binary | format | abstained | pass | pass | pass | n/a |
| malformed_parquet_after_registry_extension | format | failed | pass | pass | pass | n/a |
| registered_hdf5 | format | success | pass | pass | pass | n/a |
| conflicting_hdf5_hint | format | abstained | pass | pass | pass | n/a |

## Boundaries

- This Phase 12 experiment is separate from the frozen Artifact Paper benchmark.
- Support scores are deterministic rule strengths, not calibrated probabilities.
- Sidecar documentation is not used to promote canonical temporal claims.
