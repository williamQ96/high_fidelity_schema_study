# Internal Baseline Report

This report compares deterministic derived schemas against the internal gold references.

## Aggregate Metrics

| Metric | Value |
| --- | ---: |
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

## Metrics By Category

| Category | physical_completeness | physical_accuracy | logical_completeness | logical_accuracy | semantic_completeness | semantic_accuracy | high_necessity_coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| csv | 1.0000 | 0.9444 | 0.8889 | 0.8333 | 0.9444 | 1.0000 | 1.0000 |
| hdf5 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| time_series | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

## Uncertainty Analysis

| Confidence Bucket | Count | Physical Accuracy | Logical Accuracy | Semantic Accuracy |
| --- | ---: | ---: | ---: | ---: |
| 0.85-0.95 | 15 | 1.0000 | 0.8667 | 1.0000 |
| 0.95-1.00 | 35 | 0.9714 | 0.9714 | 1.0000 |

- Logical unknown rate: `0.0400`
- Semantic unknown rate: `0.0200`

## Error Modes

| Error Mode | Count |
| --- | ---: |
| time_axis_mismatch | 3 |
| unexpected_field | 3 |
| logical_unknown | 2 |
| logical_mismatch | 1 |
| physical_type_mismatch | 1 |

## Dataset Results

### csv_easy_weather_stations

- Category: `csv`
- Difficulty: `easy`
- Physical completeness: `1.0000`
- Physical accuracy: `0.8333`
- Logical completeness: `1.0000`
- Logical accuracy: `0.8333`
- Semantic completeness: `1.0000`
- Semantic accuracy: `1.0000`
- High necessity coverage: `1.0000`

### csv_hard_field_campaign

- Category: `csv`
- Difficulty: `hard`
- Physical completeness: `1.0000`
- Physical accuracy: `1.0000`
- Logical completeness: `0.6667`
- Logical accuracy: `0.6667`
- Semantic completeness: `0.8333`
- Semantic accuracy: `1.0000`
- High necessity coverage: `1.0000`

### csv_medium_water_quality

- Category: `csv`
- Difficulty: `medium`
- Physical completeness: `1.0000`
- Physical accuracy: `1.0000`
- Logical completeness: `1.0000`
- Logical accuracy: `1.0000`
- Semantic completeness: `1.0000`
- Semantic accuracy: `1.0000`
- High necessity coverage: `1.0000`

### hdf5_easy_climate_cube

- Category: `hdf5`
- Difficulty: `easy`
- Physical completeness: `1.0000`
- Physical accuracy: `1.0000`
- Logical completeness: `1.0000`
- Logical accuracy: `1.0000`
- Semantic completeness: `1.0000`
- Semantic accuracy: `1.0000`
- High necessity coverage: `1.0000`

### hdf5_hard_ocean_profile

- Category: `hdf5`
- Difficulty: `hard`
- Physical completeness: `1.0000`
- Physical accuracy: `1.0000`
- Logical completeness: `1.0000`
- Logical accuracy: `1.0000`
- Semantic completeness: `1.0000`
- Semantic accuracy: `1.0000`
- High necessity coverage: `1.0000`
- Unexpected fields: `/campaign/meta/platform, /campaign/run_01/cast_0002/qc_flag, /campaign/run_01/cast_0002/salinity_psu`

### hdf5_medium_station_hierarchy

- Category: `hdf5`
- Difficulty: `medium`
- Physical completeness: `1.0000`
- Physical accuracy: `1.0000`
- Logical completeness: `1.0000`
- Logical accuracy: `1.0000`
- Semantic completeness: `1.0000`
- Semantic accuracy: `1.0000`
- High necessity coverage: `1.0000`

### ts_easy_hourly_weather

- Category: `time_series`
- Difficulty: `easy`
- Physical completeness: `1.0000`
- Physical accuracy: `1.0000`
- Logical completeness: `1.0000`
- Logical accuracy: `1.0000`
- Semantic completeness: `1.0000`
- Semantic accuracy: `1.0000`
- High necessity coverage: `1.0000`

### ts_hard_irregular_buoy

- Category: `time_series`
- Difficulty: `hard`
- Physical completeness: `1.0000`
- Physical accuracy: `1.0000`
- Logical completeness: `1.0000`
- Logical accuracy: `1.0000`
- Semantic completeness: `1.0000`
- Semantic accuracy: `1.0000`
- High necessity coverage: `1.0000`

### ts_medium_power_meter

- Category: `time_series`
- Difficulty: `medium`
- Physical completeness: `1.0000`
- Physical accuracy: `1.0000`
- Logical completeness: `1.0000`
- Logical accuracy: `1.0000`
- Semantic completeness: `1.0000`
- Semantic accuracy: `1.0000`
- High necessity coverage: `1.0000`

