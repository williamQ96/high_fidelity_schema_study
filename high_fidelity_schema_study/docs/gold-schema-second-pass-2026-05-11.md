# Gold Schema Second-Pass Review

- Review ID: `gold-schema-second-pass-2026-05-11`
- Review date: `2026-05-11`
- Scope: internal pilot gold schemas
- Status: `pass`
- Datasets reviewed: `9`
- Fields reviewed: `50`
- High-necessity fields reviewed: `37`

## Finding Summary

- error: `0`
- warning: `9`
- note: `4`

## Dataset Coverage

| Dataset | Format | Modality | Difficulty | Fields | High necessity | Time-axis fields | Top-level time_axis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| csv_easy_weather_stations | csv | tabular | easy | 6 | 4 | 0 | no |
| csv_hard_field_campaign | csv | tabular | hard | 6 | 3 | 0 | no |
| csv_medium_water_quality | csv | tabular | medium | 7 | 5 | 0 | no |
| hdf5_easy_climate_cube | hdf5 | hierarchical | easy | 4 | 4 | 1 | no |
| hdf5_hard_ocean_profile | hdf5 | hierarchical | hard | 7 | 5 | 0 | no |
| hdf5_medium_station_hierarchy | hdf5 | hierarchical | medium | 5 | 5 | 1 | no |
| ts_easy_hourly_weather | csv | time_series | easy | 5 | 4 | 1 | yes |
| ts_hard_irregular_buoy | csv | time_series | hard | 5 | 4 | 1 | yes |
| ts_medium_power_meter | csv | time_series | medium | 5 | 3 | 1 | yes |

## Blocking Findings

No blocking consistency errors were found.

## Non-Blocking Observations

- warning / `csv_easy_weather_stations`: 6 field gold_evidence arrays are empty; consistency reviewed, evidence enrichment remains future work.
- warning / `csv_hard_field_campaign`: 6 field gold_evidence arrays are empty; consistency reviewed, evidence enrichment remains future work.
- warning / `csv_medium_water_quality`: 7 field gold_evidence arrays are empty; consistency reviewed, evidence enrichment remains future work.
- note / `hdf5_easy_climate_cube`: Contains field-level time_axis labels but no top-level time-series profile; acceptable for non-time-series modality.
- warning / `hdf5_easy_climate_cube`: 4 field gold_evidence arrays are empty; consistency reviewed, evidence enrichment remains future work.
- warning / `hdf5_hard_ocean_profile`: 7 field gold_evidence arrays are empty; consistency reviewed, evidence enrichment remains future work.
- note / `hdf5_hard_ocean_profile`: Semantic type 'water_temperature' has both explicit units and null units; null means unit not evidence-backed in that field.
- note / `hdf5_medium_station_hierarchy`: Contains field-level time_axis labels but no top-level time-series profile; acceptable for non-time-series modality.
- warning / `hdf5_medium_station_hierarchy`: 5 field gold_evidence arrays are empty; consistency reviewed, evidence enrichment remains future work.
- note / `hdf5_medium_station_hierarchy`: Semantic type 'surface_pressure' has both explicit units and null units; null means unit not evidence-backed in that field.
- warning / `ts_easy_hourly_weather`: 5 field gold_evidence arrays are empty; consistency reviewed, evidence enrichment remains future work.
- warning / `ts_hard_irregular_buoy`: 5 field gold_evidence arrays are empty; consistency reviewed, evidence enrichment remains future work.
- warning / `ts_medium_power_meter`: 5 field gold_evidence arrays are empty; consistency reviewed, evidence enrichment remains future work.

## Review Policy Locked By This Pass

- Top-level time_axis is required for data_modality=time_series only.
- Non-time-series HDF5/tabular files may contain field-level time_axis labels without a top-level time-series profile.
- Gold unit values represent evidence-backed units. Null units are allowed when a field's unit is not explicitly supported.
- Empty gold_evidence arrays are warnings, not consistency failures, because this pass reviews label consistency rather than full evidence enrichment.
- semantic_type='unknown' is allowed for intentionally underdetermined fields.

## Result

The internal pilot gold schemas pass the second-pass consistency review.
The remaining warnings are documentation/evidence-enrichment gaps, not label-consistency blockers.
