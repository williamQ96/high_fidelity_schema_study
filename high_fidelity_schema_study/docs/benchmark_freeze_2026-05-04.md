# Benchmark Freeze 2026-05-04

This document freezes the current reproducible benchmark slice for the high-fidelity schema extraction study. It is a working freeze, not a final paper corpus.

Machine-readable freeze: [benchmark_freeze_2026-05-04.json](benchmark_freeze_2026-05-04.json)

## Frozen Scope

- Internal pilot datasets: 9
- External retrieval-pool files: 16
- Promoted external retrieval targets: 10
- Hard distractors: 6
- Retrieval query set: current 10 planted queries in `data/retrieval/external_candidate_pool/queries.json`
- Retrieval qrels: current planted single-positive judgments in `data/retrieval/external_candidate_pool/qrels.json`

## Internal Pilot

The internal pilot is frozen to the 9 datasets listed in `data/pilot_corpus_manifest.json`:

- `csv_easy_weather_stations`
- `csv_hard_field_campaign`
- `csv_medium_water_quality`
- `hdf5_easy_climate_cube`
- `hdf5_hard_ocean_profile`
- `hdf5_medium_station_hierarchy`
- `ts_easy_hourly_weather`
- `ts_hard_irregular_buoy`
- `ts_medium_power_meter`

These retain their existing gold references under `data/gold`.

## External Retrieval Pool

The external pool is frozen to `data/retrieval/external_candidate_pool/pool_manifest.json`.

Promoted targets:

- `zenodo/record_15008662/unique_tracks_90.csv`
- `zenodo/record_18195710/ensensia_raw_20230728-20251202_school_5.csv`
- `zenodo/record_3660832/Data 01 Jan 2019.h5`
- `zenodo/record_5935524/20211108_ZXLidar_Winds.csv`
- `zenodo/record_5935524/20211108_Sensit.csv`
- `zenodo/record_5935524/20211108_Tides.csv`
- `dryad/10.5061_dryad.2f2b3/...fjord_year1.csv`
- `dryad/10.5061_dryad.zkh1893nh/African_Mammal_FoodWebs_Locations.csv`
- `dryad/10.5061_dryad.zkh1893nh/functional_traits.csv`
- `dryad/10.5061_dryad.dv41ns266/weatherMQ-FP-20261011.csv`

Hard distractors:

- Greenland cod year2
- `above_500_PA_data.csv`
- `20181108_HoloParticles.csv`
- ENSENSIA school 6
- ATLASM5 February HDF5
- ATLASM5 March HDF5

## Retrieval Protocol

The frozen retrieval comparison systems are:

- `metadata_only`
- `readme_only`
- `schema_enhanced_deterministic`
- `schema_enhanced_semantic_merged`

`schema_enhanced` remains a backward-compatible alias for deterministic schema-enhanced retrieval.

The qrels file records one highly relevant planted target per query. It is included to make relevance judgments explicit, not to imply broad real-world dataset-search coverage.

Schema-enhanced artifacts include explicit slice-disambiguation terms:

- year/file-slice terms such as `year1`, `year2`, `first-year`
- school-slice terms such as `school5`
- month/time-slice terms such as `jan`

These terms are part of the current protocol because same-family files cannot always be separated by generic schema types alone.

## Regression Subsets

The external field-subset regression tests lock high-value fields rather than full external gold schemas.

Covered subsets:

- Greenland cod year1: `Hourbin`, `COA_Lat`, `COA_Lon`, `Tag`, `Transplant`, `Cove`
- `functional_traits.csv`: `Species`, `Mass.g`
- `weatherMQ-FP-20261011.csv`: `dateTime`, `temperature`, `relativeHumidity`, `barometricPressure`, `rainfall`, `windSpeed`

## Deferred

- Semantic-merged external fields are not final gold references.
- Perfect planted-query retrieval is not broad retrieval robustness.
- Remaining time-axis accuracy gaps are not part of this freeze and should be resolved through deterministic profiling or evaluation logic.
