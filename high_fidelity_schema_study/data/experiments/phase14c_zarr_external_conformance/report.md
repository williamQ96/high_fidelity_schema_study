# Phase 14C External/Library Zarr Conformance

This corpus combines one public-source metadata subset with pinned library-produced metadata-only stores; it is not representative of the full Zarr ecosystem.

## Metrics

| Metric | Value |
| --- | ---: |
| case_count | 12 |
| external_public_case_count | 2 |
| library_produced_case_count | 8 |
| library_derived_edge_count | 2 |
| supported_compatibility_rate | 1.0000 |
| structured_abstention_quality | 1.0000 |
| unsupported_feature_visibility | 1.0000 |
| malformed_edge_quality | 1.0000 |
| source_documentation_completeness | 1.0000 |
| evidence_coverage | 1.0000 |
| path_portability_accuracy | 1.0000 |
| chunk_payload_non_claim_rate | 1.0000 |
| unsupported_promotion_count | 0 |
| true_bug_count | 0 |
| zarr_conformance_assessed_count | 12 |
| zarr_physical_conformance_rate | 0.8333 |
| xarray_conformance_assessed_count | 4 |
| xarray_structure_conformance_rate | 1.0000 |
| conformance_difference_count | 5 |
| unexplained_conformance_difference_count | 0 |

## Sources

- `external_public_sdist`: 2
- `library_derived_edge`: 2
- `library_produced`: 8

## Conformance Differences

- `encoded_fill_value_interpretation`: 1
- `parser_default_materialization`: 4

## Supported

| Case | Source | Status | Canonical | Differences |
| --- | --- | --- | --- | ---: |
| official_zarr_python_fixture_subset | external_public_sdist | success | pass | 4 |
| zarr_library_root_array | library_produced | success | pass | 0 |
| zarr_library_group_hierarchy | library_produced | success | pass | 0 |
| zarr_library_structured_records | library_produced | success | pass | 1 |
| zarr_library_nested_separator | library_produced | success | pass | 0 |
| zarr_library_vlen_utf8 | library_produced | success | pass | 0 |
| xarray_library_nonconsolidated | library_produced | success | pass | 0 |
| xarray_library_consolidated | library_produced | success | pass | 0 |
| xarray_library_nested_group | library_produced | success | pass | 0 |

## Structured Abstention

| Case | Source | Status | Canonical | Differences |
| --- | --- | --- | --- | ---: |
| official_zarr_python_utf8attrs_orphan | external_public_sdist | abstained | pass | 0 |

## Unsupported Feature

| Case | Source | Status | Canonical | Differences |
| --- | --- | --- | --- | ---: |
| xarray_library_dangling_coordinate | library_derived_edge | success | pass | 0 |

## Malformed Edge

| Case | Source | Status | Canonical | Differences |
| --- | --- | --- | --- | ---: |
| zarr_library_malformed_optional_attrs | library_derived_edge | partial | pass | 0 |

## Boundaries

- Cross-parser results are dev-only supporting evidence and do not override canonical extraction outcomes.
- No canonical or cross-parser path reads array values.
- The public-source subset retains metadata documents only; official fixture chunk payloads are excluded.
- Library-produced stores are generated with pinned versions and stripped of any eagerly written non-metadata objects.
- Zarr v3, remote stores, full Xarray reconstruction, and value-level profiling remain out of scope.
