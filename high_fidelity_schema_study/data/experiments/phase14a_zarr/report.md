# Phase 14A Zarr Directory-Store Experiment

This generated report evaluates the isolated local Zarr v2 metadata challenge pack.

## Metrics

| Metric | Value |
| --- | ---: |
| case_count | 14 |
| store_detection_accuracy | 1.0000 |
| extractor_routing_accuracy | 1.0000 |
| outcome_status_accuracy | 1.0000 |
| group_discovery_accuracy | 1.0000 |
| array_discovery_accuracy | 1.0000 |
| physical_metadata_accuracy | 1.0000 |
| attribute_extraction_accuracy | 1.0000 |
| xarray_dimension_accuracy | 1.0000 |
| coordinate_role_accuracy | 1.0000 |
| calendar_handling_accuracy | 1.0000 |
| unit_mapping_accuracy | 1.0000 |
| reason_code_coverage | 1.0000 |
| partial_extraction_accuracy | 1.0000 |
| temporal_abstention_precision | 1.0000 |
| temporal_abstention_recall | 1.0000 |
| value_observation_abstention_accuracy | 1.0000 |
| evidence_coverage | 1.0000 |
| unsupported_promotion_count | 0 |
| path_portability_accuracy | 1.0000 |

## Cases

| Case | Status | Detection | Routing | Expected Status | Portable |
| --- | --- | --- | --- | --- | --- |
| minimal_group | success | pass | pass | pass | pass |
| basic_array | success | pass | pass | pass | pass |
| nested_hierarchy | success | pass | pass | pass | pass |
| physical_metadata | success | pass | pass | pass | pass |
| xarray_coordinates | success | pass | pass | pass | pass |
| coordinate_conflict | success | pass | pass | pass | pass |
| name_only_unknown | success | pass | pass | pass | pass |
| partial_malformed | partial | pass | pass | pass | pass |
| malformed_root | failed | pass | pass | pass | pass |
| missing_metadata | abstained | pass | pass | pass | pass |
| zarr_v3 | abstained | pass | pass | pass | pass |
| consolidated_only | success | pass | pass | pass | pass |
| consolidated_conflict | partial | pass | pass | pass | pass |
| unknown_codec | success | pass | pass | pass | pass |

## Boundaries

- Phase 14A evaluates local directory-store Zarr v2 metadata extraction only.
- Chunk payloads, remote stores, Zarr v3, and full Xarray semantic reconstruction are out of scope.
- All temporal candidates abstain because Phase 14A does not read chunk payload samples.
- Value-level statistics remain unknown because Phase 14A does not read chunk payload samples.
