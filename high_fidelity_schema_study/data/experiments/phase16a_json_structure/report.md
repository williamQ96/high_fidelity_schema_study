# Phase 16A JSON Structure Evaluation

Controlled JSON challenge pack; observed structures are sample-bounded and not universal schema truth.

## Metrics

| Metric | Value |
| --- | ---: |
| case_count | 6 |
| format_detection_accuracy | 1.0000 |
| extractor_routing_accuracy | 1.0000 |
| mode_accuracy | 1.0000 |
| path_accuracy | 1.0000 |
| missingness_accuracy | 1.0000 |
| nullability_accuracy | 1.0000 |
| heterogeneous_array_accuracy | 1.0000 |
| declared_schema_accuracy | 1.0000 |
| declared_observed_conflict_accuracy | 1.0000 |
| sampling_issue_accuracy | 1.0000 |
| evidence_coverage | 1.0000 |
| unsupported_promotion_count | 0 |

## Boundaries

- Observed paths and type sets are bounded by the configured record sample.
- JSON Schema documents produce declared claims, not observed-data claims.
- Semantic roles are not inferred from names.
