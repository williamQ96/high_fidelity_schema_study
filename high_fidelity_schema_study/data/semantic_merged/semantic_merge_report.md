# Semantic Merge Report

This report compares baseline deterministic schemas against semantic-merged schemas for internal tasks that have both gold references and semantic merge outputs.

## Aggregate Summary

- Dataset count: `3`
- Datasets with any metric gain: `2`
- Total accepted semantic merges: `3`
- Total conflicts: `1`
- Mean logical accuracy delta: `+0.1667`

## hdf5_hard_ocean_profile

| Metric | Baseline | Merged | Delta |
| --- | ---: | ---: | ---: |
| physical_accuracy | 1.0000 | 1.0000 | +0.0000 |
| logical_accuracy | 1.0000 | 1.0000 | +0.0000 |
| semantic_accuracy | 1.0000 | 1.0000 | +0.0000 |
| unit_accuracy | 1.0000 | 1.0000 | +0.0000 |

- Accepted semantic merges: `0`
- Conflict count: `1`

## csv_hard_field_campaign

| Metric | Baseline | Merged | Delta |
| --- | ---: | ---: | ---: |
| physical_accuracy | 1.0000 | 1.0000 | +0.0000 |
| logical_accuracy | 0.6667 | 1.0000 | +0.3333 |
| semantic_accuracy | 1.0000 | 1.0000 | +0.0000 |
| unit_accuracy | 0.0000 | 0.0000 | +0.0000 |

- Accepted semantic merges: `2`
- Conflict count: `0`

## csv_easy_weather_stations

| Metric | Baseline | Merged | Delta |
| --- | ---: | ---: | ---: |
| physical_accuracy | 0.8333 | 0.8333 | +0.0000 |
| logical_accuracy | 0.8333 | 1.0000 | +0.1667 |
| semantic_accuracy | 1.0000 | 1.0000 | +0.0000 |
| unit_accuracy | 1.0000 | 1.0000 | +0.0000 |

- Accepted semantic merges: `1`
- Conflict count: `0`

