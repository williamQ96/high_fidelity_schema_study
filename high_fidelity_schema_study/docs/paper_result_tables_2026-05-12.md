# Paper-Ready Result Tables

These tables are generated from frozen study artifacts rather than hand-edited numbers.

## Source Artifacts

| Source | Path |
| --- | --- |
| benchmark_freeze | `docs/benchmark_freeze_2026-05-04.json` |
| internal_baseline | `data/derived/internal_baseline_report.json` |
| retrieval_report | `data/retrieval/external_candidate_pool/retrieval_report.json` |
| semantic_merge_report | `data/semantic_merged/semantic_merge_report.json` |
| derived_manifest | `data/derived/derived_manifest.json` |
| relationship_profile | `data/derived/internal_relationship_profile.json` |

## Table 1. Frozen Benchmark Slice

| measure | value | source |
| --- | --- | --- |
| Internal pilot datasets | 9 | data/pilot_corpus_manifest.json |
| External retrieval candidate files | 16 | data/retrieval/external_candidate_pool/pool_manifest.json |
| Promoted external target files | 10 | data/retrieval/external_candidate_pool/pool_manifest.json |
| External distractor files | 6 | data/retrieval/external_candidate_pool/pool_manifest.json |
| Current retrieval systems | 4 | data/retrieval/external_candidate_pool/artifact_manifest.json |
| Locked external field-subset regression groups | 3 | docs/benchmark_freeze_2026-05-04.json |

## Table 2. Deterministic Extraction Baseline

| metric | value |
| --- | --- |
| physical_completeness | 1.0000 |
| physical_accuracy | 0.9815 |
| logical_completeness | 0.9630 |
| logical_accuracy | 0.9444 |
| semantic_completeness | 0.9815 |
| semantic_accuracy | 1.0000 |
| unit_accuracy | 0.8889 |
| high_necessity_coverage | 1.0000 |
| high_necessity_physical_accuracy | 1.0000 |
| time_axis_accuracy | 0.6667 |

## Table 3. Deterministic Baseline By Data Family

| category | physical_completeness | physical_accuracy | logical_accuracy | semantic_accuracy | unit_accuracy | time_axis_accuracy |
| --- | --- | --- | --- | --- | --- | --- |
| csv | 1.0000 | 0.9444 | 0.8333 | 1.0000 | 0.6667 | 1.0000 |
| hdf5 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| time_series | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |

## Table 4. Deterministic Baseline Error Modes

| error_mode | count |
| --- | --- |
| time_axis_mismatch | 3 |
| unexpected_field | 3 |
| logical_unknown | 2 |
| logical_mismatch | 1 |
| physical_type_mismatch | 1 |

## Table 5. External Retrieval Metrics

| system | schema_source | query_count | recall_at_1 | recall_at_3 | precision_at_1 | precision_at_3 | mrr | ndcg_at_3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| metadata_only | metadata only | 10 | 0.7000 | 0.7000 | 0.7000 | 0.2333 | 0.7617 | 0.7000 |
| readme_only | README text only | 10 | 0.5000 | 0.8000 | 0.5000 | 0.2667 | 0.6610 | 0.6762 |
| schema_enhanced | deterministic schema, compatibility alias | 10 | 1.0000 | 1.0000 | 1.0000 | 0.3333 | 1.0000 | 1.0000 |
| schema_enhanced_deterministic | deterministic schema | 10 | 1.0000 | 1.0000 | 1.0000 | 0.3333 | 1.0000 | 1.0000 |
| schema_enhanced_semantic_merged | semantic-merged schema | 10 | 1.0000 | 1.0000 | 1.0000 | 0.3333 | 1.0000 | 1.0000 |

## Table 6. Retrieval Gain Vs Metadata-Only

| system | recall_at_1_delta | recall_at_3_delta | precision_at_1_delta | mrr_delta | ndcg_at_3_delta |
| --- | --- | --- | --- | --- | --- |
| readme_only | -0.2000 | 0.1000 | -0.2000 | -0.1007 | -0.0238 |
| schema_enhanced | 0.3000 | 0.3000 | 0.3000 | 0.2383 | 0.3000 |
| schema_enhanced_deterministic | 0.3000 | 0.3000 | 0.3000 | 0.2383 | 0.3000 |
| schema_enhanced_semantic_merged | 0.3000 | 0.3000 | 0.3000 | 0.2383 | 0.3000 |

## Table 7. Semantic Merge Aggregate

| dataset_count | improved_dataset_count | accepted_for_merge_count | conflict_count | mean_logical_accuracy_delta |
| --- | --- | --- | --- | --- |
| 3 | 2 | 3 | 1 | 0.1667 |

## Table 8. Semantic Merge Dataset Deltas

| dataset_id | accepted_merges | conflicts | baseline_logical_accuracy | merged_logical_accuracy | logical_accuracy_delta | baseline_semantic_accuracy | merged_semantic_accuracy | semantic_accuracy_delta | baseline_unit_accuracy | merged_unit_accuracy | unit_accuracy_delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hdf5_hard_ocean_profile | 0 | 1 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0000 |
| csv_hard_field_campaign | 2 | 0 | 0.6667 | 1.0000 | 0.3333 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| csv_easy_weather_stations | 1 | 0 | 0.8333 | 1.0000 | 0.1667 | 1.0000 | 1.0000 | 0.0000 | 1.0000 | 1.0000 | 0.0000 |

## Table 9. Deterministic Profile Summary

| metric | value | interpretation |
| --- | --- | --- |
| Internal datasets with deterministic profile | 9 | All frozen internal pilot datasets have profile metadata. |
| Derived fields profiled | 53 | Field-level missingness and identifier checks are attached to schemas. |
| Fields with sampled missing values | 1 | Missingness is rare in the current synthetic internal slice. |
| Total sampled missing cells | 2 | Counted from deterministic file scans where rows are sampled. |
| Identifier candidates | 10 | Fields that look like identifiers by logical or semantic labels. |
| Best identifier fields | 5 | Identifier candidates with unique or group-identifier quality. |
| Cross-file relationship candidates | 22 | Deterministic candidates only; not asserted joins. |

## Table 10. Deterministic Cross-File Relationship Candidates

| relationship_type | count |
| --- | --- |
| shared_identifier_semantic | 6 |
| shared_measurement_semantic | 6 |
| shared_temporal_semantic | 4 |
| shared_time_axis_semantic | 6 |

## Table 11. Locked External Field-Subset Regression Groups

| subset | field_count | fields |
| --- | --- | --- |
| greenland_cod_year1 | 6 | Hourbin, COA_Lat, COA_Lon, Tag, Transplant, Cove |
| functional_traits | 2 | Species, Mass.g |
| weatherMQ_FP | 6 | dateTime, temperature, relativeHumidity, barometricPressure, rainfall, windSpeed |

## Table 12. Remaining Non-Final Items

| limitation |
| --- |
| Semantic-merged external fields are protected as high-confidence working annotations, not final gold references. |
| Perfect planted-query retrieval is not broad retrieval robustness; harder non-planted queries remain future work. |
| Remaining time-axis accuracy gaps should be resolved separately through deterministic profiling or evaluation logic. |

## Paper Claims Supported By These Tables

- The frozen reproducible slice contains 9 internal pilot datasets and 16 external retrieval candidates.
- Deterministic extraction has high field-level accuracy on the internal slice, while time-axis handling remains the clearest open gap.
- Schema-enhanced retrieval reaches Recall@1 = 1.0000 on the current planted-query external slice.
- Evidence-constrained semantic merge improves logical accuracy on 2 of 3 reviewed internal datasets without measured metric regression.
- Deterministic profiles add missingness, identifier quality, and relationship-candidate diagnostics without changing evaluation labels.
