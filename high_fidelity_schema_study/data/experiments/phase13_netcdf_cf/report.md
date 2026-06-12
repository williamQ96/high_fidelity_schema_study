# Phase 13 NetCDF/CF Experiment

This generated report evaluates the isolated NetCDF/CF challenge pack.

## Metrics

| Metric | Value |
| --- | ---: |
| case_count | 14 |
| format_detection_accuracy | 1.0000 |
| extractor_routing_accuracy | 1.0000 |
| physical_extraction_accuracy | 1.0000 |
| coordinate_role_accuracy | 1.0000 |
| time_axis_accuracy | 1.0000 |
| calendar_handling_accuracy | 1.0000 |
| unit_mapping_accuracy | 1.0000 |
| temporal_abstention_precision | 1.0000 |
| temporal_abstention_recall | 1.0000 |
| unsupported_promotion_count | 0 |
| evidence_coverage | 1.0000 |

## Cases

| Case | Status | Format | Routing | Physical | Coordinate | Time | Calendar | Units | Abstention |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| standard_coordinates | success | pass | pass | pass | pass | pass | pass | pass | pass |
| auxiliary_coordinates | success | pass | pass | pass | pass | pass | pass | pass | pass |
| days_since | success | pass | pass | pass | pass | pass | pass | pass | pass |
| calendar_360_day | success | pass | pass | pass | pass | pass | pass | pass | pass |
| multiple_time_variables | success | pass | pass | pass | pass | pass | pass | pass | pass |
| irregular_sampling | success | pass | pass | pass | pass | pass | pass | pass | pass |
| bounds_variable | success | pass | pass | pass | pass | pass | pass | pass | pass |
| missing_metadata | success | pass | pass | pass | pass | pass | pass | pass | pass |
| name_only_coordinate | success | pass | pass | pass | pass | pass | pass | pass | pass |
| coordinate_conflict | success | pass | pass | pass | pass | pass | pass | pass | pass |
| malformed_cf_time | success | pass | pass | pass | pass | pass | pass | pass | pass |
| unmapped_unit | success | pass | pass | pass | pass | pass | pass | pass | pass |
| missing_markers | success | pass | pass | pass | pass | pass | pass | pass | pass |
| grouped_netcdf4 | success | pass | pass | pass | pass | pass | pass | pass | pass |

## Boundaries

- Phase 13 is isolated from the frozen Artifact Paper benchmark.
- NetCDF/CF semantic claims are promoted only from explicit attributes or deterministic structure.
- Non-standard calendars are preserved but not decoded by the standard-calendar temporal path.
