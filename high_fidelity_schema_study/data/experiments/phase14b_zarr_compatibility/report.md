# Phase 14B Zarr Compatibility Validation

This is a realistic compatibility corpus, not a downloaded representative ecosystem sample.

## Metrics

| Metric | Value |
| --- | ---: |
| case_count | 17 |
| supported_case_count | 10 |
| supported_compatibility_rate | 1.0000 |
| unsupported_feature_visibility | 1.0000 |
| malformed_failure_quality | 1.0000 |
| structured_abstention_quality | 1.0000 |
| overall_expectation_match | 1.0000 |
| evidence_coverage | 1.0000 |
| path_portability_accuracy | 1.0000 |
| chunk_payload_non_claim_rate | 1.0000 |
| value_observation_abstention_accuracy | 1.0000 |
| compatibility_gap_count | 2 |
| unsupported_promotion_count | 0 |
| true_bug_count | 0 |

## Classification Summary

| Classification | Cases | Expectations Met |
| --- | ---: | ---: |
| malformed_failure | 2 | 2 |
| structured_abstention | 1 | 1 |
| supported | 10 | 10 |
| unsupported_feature | 4 | 4 |

## Compatibility Gaps

- `dimension_size_conflict`: 1
- `unresolved_coordinate_reference`: 1

## Supported

| Case | Profile | Status | Expectations |
| --- | --- | --- | --- |
| root_array_numpy_style | standalone NumPy-style root array | success | pass |
| xarray_weather_nonconsolidated | Xarray-style non-consolidated multidimensional dataset | success | pass |
| xarray_ocean_consolidated | Xarray-style consolidated ocean dataset | success | pass |
| nested_instrument_groups | Nested grouped station dataset with repeated variable names | success | pass |
| scalar_and_zero_length | Scalar and empty scientific arrays | success | pass |
| structured_dtype_records | NumPy structured-record array | success | pass |
| object_vlen_utf8 | Object array with vlen UTF-8 filter metadata | success | pass |
| slash_separator_tree | Large image array with slash-separated chunk keys | success | pass |
| special_fill_values | Floating arrays with JSON special fill values | success | pass |
| unknown_codec_metadata | Site-defined codec metadata preserved without execution | success | pass |

## Unsupported Feature

| Case | Profile | Status | Expectations |
| --- | --- | --- | --- |
| unresolved_coordinate_reference | Xarray-style dataset with one missing coordinate target | success | pass |
| dimension_conflict_group | Inconsistent Xarray dimension-size declarations | success | pass |
| stale_consolidated_metadata | Direct metadata newer than stale consolidated metadata | partial | pass |
| zarr_v3_reference | Recognized Zarr v3 group | abstained | pass |

## Malformed Failure

| Case | Profile | Status | Expectations |
| --- | --- | --- | --- |
| malformed_optional_attrs | Valid array with malformed optional attributes | partial | pass |
| malformed_only_array | Malformed root array metadata | failed | pass |

## Structured Abstention

| Case | Profile | Status | Expectations |
| --- | --- | --- | --- |
| empty_suffix_only | Directory suffix without spec-backed metadata | abstained | pass |

## Boundaries

- The corpus reconstructs common local Zarr v2 producer layouts; it is not a downloaded representative ecosystem sample.
- Chunk keys contain dummy invalid bytes and are never used to create schema or value-level claims.
- Unsupported features and malformed stores are successful compatibility observations when surfaced as expected.
- Remote stores, Zarr v3 extraction, chunk decoding, and full Xarray reconstruction remain out of scope.
