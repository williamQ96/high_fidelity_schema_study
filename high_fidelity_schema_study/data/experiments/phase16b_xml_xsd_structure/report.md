# Phase 16B XML / XSD Structure Evaluation

Controlled XML/XSD challenge pack; observed XML paths are sample-bounded and external schemas are not loaded.

## Metrics

| Metric | Value |
| --- | ---: |
| case_count | 5 |
| format_detection_accuracy | 1.0000 |
| extractor_routing_accuracy | 1.0000 |
| mode_accuracy | 1.0000 |
| path_accuracy | 1.0000 |
| repeated_path_accuracy | 1.0000 |
| namespace_accuracy | 1.0000 |
| declared_xsd_accuracy | 1.0000 |
| declared_observed_conflict_accuracy | 1.0000 |
| sampling_issue_accuracy | 1.0000 |
| evidence_coverage | 1.0000 |
| unsupported_promotion_count | 0 |

## Boundaries

- Observed XML paths and repeat counts are bounded by the configured element sample.
- XSD and xsi:type declarations remain separate from observed instance structure.
- External schemas and entities are not loaded.
