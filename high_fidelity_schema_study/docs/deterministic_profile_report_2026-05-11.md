# Deterministic Profile Report

This report records the first richer deterministic profiling pass over the internal pilot derived schemas.

## Scope

- Profile date: `2026-05-11`
- Profiled datasets: `9`
- Profiled derived fields: `53`
- Profile sources: `data/derived/*/*.schema.json`
- Cross-file relationship profile: `data/derived/internal_relationship_profile.json`

## What Was Added

Each internal derived schema now carries a `metadata.deterministic_profile` block with:

- `missingness`: sampled-row missing counts, missing ratios, nullable flags, and total missing cells.
- `identifier_quality`: identifier candidates, unique ratios, duplicate counts, and conservative quality labels.

The internal derived manifest now points to:

- `data/derived/internal_relationship_profile.json`

That profile lists deterministic cross-file relationship candidates based on shared logical and semantic field labels.

## Current Summary

| Profile area | Count |
| --- | ---: |
| Datasets profiled | 9 |
| Derived fields profiled | 53 |
| Fields with missing values | 1 |
| Total missing sampled cells | 2 |
| Identifier candidates | 10 |
| Best identifier fields | 5 |
| Cross-file relationship candidates | 22 |

## Relationship Candidates

| Relationship type | Count |
| --- | ---: |
| shared_identifier_semantic | 6 |
| shared_measurement_semantic | 6 |
| shared_temporal_semantic | 4 |
| shared_time_axis_semantic | 6 |

These are candidates, not asserted joins. They are useful for paper discussion and future corpus hardening because they expose where deterministic labels suggest possible cross-file alignment.

## Convergence Value

This closes the current Phase 4 profiling gap without changing evaluation metrics or expanding the corpus.

The result is intentionally conservative:

- Missingness is sampled-row based for CSV/time-series files and field-metadata based for HDF5 files.
- Identifier quality uses unique ratio and missingness only; it does not assume that a repeated identifier is wrong.
- Multi-file relationships are label-based candidates. Value-level join validation remains future work.

## Remaining Risks

- HDF5 missingness is not yet value-scanned for large external files.
- Relationship candidates are not used as gold labels.
- Multi-file relationships should not be promoted to benchmark claims until value-level overlap or source documentation supports them.
