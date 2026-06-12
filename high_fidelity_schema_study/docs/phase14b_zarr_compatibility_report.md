# Phase 14B: Realistic Local Zarr v2 Compatibility Validation

Date: 2026-06-11

## Scope And Corpus Boundary

Phase 14B validates the registry-backed Zarr metadata extractor against a separate 17-case local compatibility corpus under `testdata/zarr_phase14b_compatibility/`.

The corpus reconstructs common producer-shaped Zarr v2 layouts, including standalone NumPy-style arrays, grouped stores, Xarray-style datasets, consolidated and non-consolidated metadata, coordinate arrays, structured dtypes, scalar and empty arrays, compressed/chunked metadata, special fill values, missing optional attributes, stale metadata, malformed stores, and unsupported variants.

This is a realistic compatibility corpus, not a downloaded representative ecosystem sample. It measures known layout compatibility and failure quality; it does not establish broad ecosystem coverage.

## Compatibility Fixes

The corpus exposed three narrow compatibility issues, which were fixed without expanding the support boundary:

1. Structured NumPy dtype descriptors serialized as JSON list-of-lists are normalized for validation while their original metadata representation is preserved.
2. Metadata discovery now uses an array-boundary-aware walk. Once an array node is found, slash-separated chunk directories are pruned instead of recursively traversed.
3. Xarray-style `coordinates` references are resolved relative to their owning group and only promote existing arrays. Cross-group same-name arrays and unresolved references are not promoted.

The extractor also records explicit `unresolved_coordinate_reference` and `dimension_size_conflict` compatibility gaps, aggregates evidence from all arrays declaring a dimension, and reports store-walk inventory with `payload_bytes_read = 0`.

## Results

The generated compatibility report is under `data/experiments/phase14b_zarr_compatibility/`.

| Classification | Cases | Result |
| --- | ---: | --- |
| Supported and correctly extracted | 10 | 10 met all expectations |
| Unsupported features | 4 | 4 surfaced as expected |
| Malformed-store failures | 2 | 2 produced the expected structured outcomes |
| Structured abstentions | 1 | 1 abstained with the expected reason |

Key metrics:

- supported compatibility rate: `1.0000`;
- unsupported-feature visibility: `1.0000`;
- malformed-failure quality: `1.0000`;
- structured-abstention quality: `1.0000`;
- evidence coverage: `1.0000`;
- chunk-payload non-claim rate: `1.0000`;
- value-observation abstention accuracy: `1.0000`;
- path portability: `1.0000`;
- compatibility gaps surfaced: `2`;
- unsupported promotion count: `0`;
- true bug count after fixes: `0`.
- regression suite: `117 passed`.

The two surfaced compatibility gaps are one unresolved coordinate reference and one conflicting dimension size. Both remain explicit rather than becoming invented fields or silently accepted semantics.

## Boundaries

- Dummy chunk keys contain invalid bytes and are not decoded or used for schema claims.
- Unknown codec metadata is preserved but never executed.
- Zarr v3 remains a structured abstention.
- Remote/object stores, authentication, full Xarray reconstruction, and value-level profiling remain out of scope.
- Frozen benchmark, manuscript, paper tables, figures, and headline metrics remain unchanged.

## Recommendation

The next Zarr step should be an externally sourced local Zarr v2 validation corpus plus optional library-backed cross-parser conformance checks. That work should measure mismatches between this metadata reader and a standards implementation before considering Zarr v3, remote-store intake, or bounded chunk sampling.
