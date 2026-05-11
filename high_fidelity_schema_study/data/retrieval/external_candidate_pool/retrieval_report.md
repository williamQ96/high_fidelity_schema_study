# Retrieval Report

This report compares lexical retrieval behavior over the current promoted external candidate pool.

## metadata_only

| Metric | Value |
| --- | ---: |
| recall_at_1 | 0.7000 |
| recall_at_3 | 0.7000 |
| precision_at_1 | 0.7000 |
| precision_at_3 | 0.2333 |
| mrr | 0.7617 |
| ndcg_at_3 | 0.7000 |

### Query Cases

#### hailstorm_tracks_geo_time

- Expected: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1 correct: `True`
- Overlap terms: `csv, dataset, hailstorm, storm, tracks`

#### indoor_air_sensor_pollutants

- Expected: `zenodo__record_18195710__ensensia_raw_20230728-20251202_school_5.csv`
- Top 1: `zenodo__record_18195710__ensensia_raw_20230728-20251202_school_5.csv`
- Top 1 correct: `True`
- Overlap terms: `5, school`

#### atmospheric_hdf5_station

- Expected: `zenodo__record_3660832__Data_01_Jan_2019.h5`
- Top 1: `zenodo__record_3660832__Data_01_Jan_2019.h5`
- Top 1 correct: `True`
- Overlap terms: `atmospheric, data, jan, january, meteorological, nitrogen, oxides, ozone, parameters, station`

#### wind_lidar_time_series

- Expected: `zenodo__record_5935524__20211108_ZXLidar_Winds.csv`
- Top 1: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1 correct: `False`
- Overlap terms: none

#### particle_counts_time_series

- Expected: `zenodo__record_5935524__20211108_Sensit.csv`
- Top 1: `zenodo__record_3660832__Data_03_Mar_2019.h5`
- Top 1 correct: `False`
- Overlap terms: `data`

#### tide_water_level_series

- Expected: `zenodo__record_5935524__20211108_Tides.csv`
- Top 1: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1 correct: `False`
- Overlap terms: none

#### greenland_cod_telemetry_positions

- Expected: `dryad__10.5061_dryad.2f2b3__Season_and_site_fidelity_determine_home_range_of_dispersing_and_resident_juvenile_Greenland_cod_(Gadus_ogac)_in_a_Newfoundland_fjord_year1.csv`
- Top 1: `dryad__10.5061_dryad.2f2b3__Season_and_site_fidelity_determine_home_range_of_dispersing_and_resident_juvenile_Greenland_cod_(Gadus_ogac)_in_a_Newfoundland_fjord_year1.csv`
- Top 1 correct: `True`
- Overlap terms: `cod, data, greenland, juvenile, year1`

#### african_mammal_site_locations

- Expected: `dryad__10.5061_dryad.zkh1893nh__African_Mammal_FoodWebs_Locations.csv`
- Top 1: `dryad__10.5061_dryad.zkh1893nh__African_Mammal_FoodWebs_Locations.csv`
- Top 1 correct: `True`
- Overlap terms: `african, food, locations, mammal, web`

#### mammal_functional_traits

- Expected: `dryad__10.5061_dryad.zkh1893nh__functional_traits.csv`
- Top 1: `dryad__10.5061_dryad.zkh1893nh__functional_traits.csv`
- Top 1 correct: `True`
- Overlap terms: `traits`

#### weather_station_meteorology

- Expected: `dryad__10.5061_dryad.dv41ns266__weatherMQ-FP-20261011.csv`
- Top 1: `dryad__10.5061_dryad.dv41ns266__weatherMQ-FP-20261011.csv`
- Top 1 correct: `True`
- Overlap terms: `data, station, weather`

## readme_only

| Metric | Value |
| --- | ---: |
| recall_at_1 | 0.5000 |
| recall_at_3 | 0.8000 |
| precision_at_1 | 0.5000 |
| precision_at_3 | 0.2667 |
| mrr | 0.6610 |
| ndcg_at_3 | 0.6762 |

### Query Cases

#### hailstorm_tracks_geo_time

- Expected: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1 correct: `True`
- Overlap terms: `csv, dataset, hailstorm, intensity, latitude, longitude, storm, tracks`

#### indoor_air_sensor_pollutants

- Expected: `zenodo__record_18195710__ensensia_raw_20230728-20251202_school_5.csv`
- Top 1: `zenodo__record_5935524__20211108_ZXLidar_Winds.csv`
- Top 1 correct: `False`
- Overlap terms: `data, sensor, series, time`

#### atmospheric_hdf5_station

- Expected: `zenodo__record_3660832__Data_01_Jan_2019.h5`
- Top 1: `zenodo__record_3660832__Data_01_Jan_2019.h5`
- Top 1 correct: `True`
- Overlap terms: `atmospheric, data, file, hdf5, january, station`

#### wind_lidar_time_series

- Expected: `zenodo__record_5935524__20211108_ZXLidar_Winds.csv`
- Top 1: `zenodo__record_5935524__20211108_ZXLidar_Winds.csv`
- Top 1 correct: `True`
- Overlap terms: `measurements, series, time, wind`

#### particle_counts_time_series

- Expected: `zenodo__record_5935524__20211108_Sensit.csv`
- Top 1: `zenodo__record_5935524__20211108_ZXLidar_Winds.csv`
- Top 1 correct: `False`
- Overlap terms: `data, field, particle, sensor, series, time`

#### tide_water_level_series

- Expected: `zenodo__record_5935524__20211108_Tides.csv`
- Top 1: `zenodo__record_5935524__20211108_ZXLidar_Winds.csv`
- Top 1 correct: `False`
- Overlap terms: `measurements, series, tidal, time`

#### greenland_cod_telemetry_positions

- Expected: `dryad__10.5061_dryad.2f2b3__Season_and_site_fidelity_determine_home_range_of_dispersing_and_resident_juvenile_Greenland_cod_(Gadus_ogac)_in_a_Newfoundland_fjord_year1.csv`
- Top 1: `dryad__10.5061_dryad.2f2b3__Season_and_site_fidelity_determine_home_range_of_dispersing_and_resident_juvenile_Greenland_cod_(Gadus_ogac)_in_a_Newfoundland_fjord_year1.csv`
- Top 1 correct: `True`
- Overlap terms: `cod, data, greenland, juvenile`

#### african_mammal_site_locations

- Expected: `dryad__10.5061_dryad.zkh1893nh__African_Mammal_FoodWebs_Locations.csv`
- Top 1: `dryad__10.5061_dryad.zkh1893nh__above_500_PA_data.csv`
- Top 1 correct: `False`
- Overlap terms: `food, web`

#### mammal_functional_traits

- Expected: `dryad__10.5061_dryad.zkh1893nh__functional_traits.csv`
- Top 1: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1 correct: `False`
- Overlap terms: `such`

#### weather_station_meteorology

- Expected: `dryad__10.5061_dryad.dv41ns266__weatherMQ-FP-20261011.csv`
- Top 1: `dryad__10.5061_dryad.dv41ns266__weatherMQ-FP-20261011.csv`
- Top 1 correct: `True`
- Overlap terms: `data, station, weather`

## schema_enhanced

| Metric | Value |
| --- | ---: |
| recall_at_1 | 1.0000 |
| recall_at_3 | 1.0000 |
| precision_at_1 | 1.0000 |
| precision_at_3 | 0.3333 |
| mrr | 1.0000 |
| ndcg_at_3 | 1.0000 |

### Query Cases

#### hailstorm_tracks_geo_time

- Expected: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1 correct: `True`
- Overlap terms: `csv, dataset, hailstorm, intensity, latitude, longitude, storm, tracks`

#### indoor_air_sensor_pollutants

- Expected: `zenodo__record_18195710__ensensia_raw_20230728-20251202_school_5.csv`
- Top 1: `zenodo__record_18195710__ensensia_raw_20230728-20251202_school_5.csv`
- Top 1 correct: `True`
- Overlap terms: `5, co2, no2, o3, school, sensor, series, temperature, time`

#### atmospheric_hdf5_station

- Expected: `zenodo__record_3660832__Data_01_Jan_2019.h5`
- Top 1: `zenodo__record_3660832__Data_01_Jan_2019.h5`
- Top 1 correct: `True`
- Overlap terms: `atmospheric, data, file, hdf5, jan, january, meteorological, nitrogen, oxides, ozone`

#### wind_lidar_time_series

- Expected: `zenodo__record_5935524__20211108_ZXLidar_Winds.csv`
- Top 1: `zenodo__record_5935524__20211108_ZXLidar_Winds.csv`
- Top 1 correct: `True`
- Overlap terms: `direction, exponent, measurements, series, shear, speed, time, wind`

#### particle_counts_time_series

- Expected: `zenodo__record_5935524__20211108_Sensit.csv`
- Top 1: `zenodo__record_5935524__20211108_Sensit.csv`
- Top 1 correct: `True`
- Overlap terms: `counts, data, field, particle, second, sensor, series, time`

#### tide_water_level_series

- Expected: `zenodo__record_5935524__20211108_Tides.csv`
- Top 1: `zenodo__record_5935524__20211108_Tides.csv`
- Top 1 correct: `True`
- Overlap terms: `level, measurements, series, still, tidal, time, water`

#### greenland_cod_telemetry_positions

- Expected: `dryad__10.5061_dryad.2f2b3__Season_and_site_fidelity_determine_home_range_of_dispersing_and_resident_juvenile_Greenland_cod_(Gadus_ogac)_in_a_Newfoundland_fjord_year1.csv`
- Top 1: `dryad__10.5061_dryad.2f2b3__Season_and_site_fidelity_determine_home_range_of_dispersing_and_resident_juvenile_Greenland_cod_(Gadus_ogac)_in_a_Newfoundland_fjord_year1.csv`
- Top 1 correct: `True`
- Overlap terms: `cod, cove, data, first, greenland, juvenile, transplant, year, year1`

#### african_mammal_site_locations

- Expected: `dryad__10.5061_dryad.zkh1893nh__African_Mammal_FoodWebs_Locations.csv`
- Top 1: `dryad__10.5061_dryad.zkh1893nh__African_Mammal_FoodWebs_Locations.csv`
- Top 1 correct: `True`
- Overlap terms: `african, code, community, country, food, latitude, locations, mammal, name, web`

#### mammal_functional_traits

- Expected: `dryad__10.5061_dryad.zkh1893nh__functional_traits.csv`
- Top 1: `dryad__10.5061_dryad.zkh1893nh__functional_traits.csv`
- Top 1 correct: `True`
- Overlap terms: `bird, invertebrate, mammal, mass, species, traits, vertebrate`

#### weather_station_meteorology

- Expected: `dryad__10.5061_dryad.dv41ns266__weatherMQ-FP-20261011.csv`
- Top 1: `dryad__10.5061_dryad.dv41ns266__weatherMQ-FP-20261011.csv`
- Top 1 correct: `True`
- Overlap terms: `barometric, data, date, direction, gust, humidity, pressure, rainfall, relative, speed`

## schema_enhanced_deterministic

| Metric | Value |
| --- | ---: |
| recall_at_1 | 1.0000 |
| recall_at_3 | 1.0000 |
| precision_at_1 | 1.0000 |
| precision_at_3 | 0.3333 |
| mrr | 1.0000 |
| ndcg_at_3 | 1.0000 |

### Query Cases

#### hailstorm_tracks_geo_time

- Expected: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1 correct: `True`
- Overlap terms: `csv, dataset, hailstorm, intensity, latitude, longitude, storm, tracks`

#### indoor_air_sensor_pollutants

- Expected: `zenodo__record_18195710__ensensia_raw_20230728-20251202_school_5.csv`
- Top 1: `zenodo__record_18195710__ensensia_raw_20230728-20251202_school_5.csv`
- Top 1 correct: `True`
- Overlap terms: `5, co2, no2, o3, school, sensor, series, temperature, time`

#### atmospheric_hdf5_station

- Expected: `zenodo__record_3660832__Data_01_Jan_2019.h5`
- Top 1: `zenodo__record_3660832__Data_01_Jan_2019.h5`
- Top 1 correct: `True`
- Overlap terms: `atmospheric, data, file, hdf5, jan, january, meteorological, nitrogen, oxides, ozone`

#### wind_lidar_time_series

- Expected: `zenodo__record_5935524__20211108_ZXLidar_Winds.csv`
- Top 1: `zenodo__record_5935524__20211108_ZXLidar_Winds.csv`
- Top 1 correct: `True`
- Overlap terms: `direction, exponent, measurements, series, shear, speed, time, wind`

#### particle_counts_time_series

- Expected: `zenodo__record_5935524__20211108_Sensit.csv`
- Top 1: `zenodo__record_5935524__20211108_Sensit.csv`
- Top 1 correct: `True`
- Overlap terms: `counts, data, field, particle, second, sensor, series, time`

#### tide_water_level_series

- Expected: `zenodo__record_5935524__20211108_Tides.csv`
- Top 1: `zenodo__record_5935524__20211108_Tides.csv`
- Top 1 correct: `True`
- Overlap terms: `level, measurements, series, still, tidal, time, water`

#### greenland_cod_telemetry_positions

- Expected: `dryad__10.5061_dryad.2f2b3__Season_and_site_fidelity_determine_home_range_of_dispersing_and_resident_juvenile_Greenland_cod_(Gadus_ogac)_in_a_Newfoundland_fjord_year1.csv`
- Top 1: `dryad__10.5061_dryad.2f2b3__Season_and_site_fidelity_determine_home_range_of_dispersing_and_resident_juvenile_Greenland_cod_(Gadus_ogac)_in_a_Newfoundland_fjord_year1.csv`
- Top 1 correct: `True`
- Overlap terms: `cod, cove, data, first, greenland, juvenile, transplant, year, year1`

#### african_mammal_site_locations

- Expected: `dryad__10.5061_dryad.zkh1893nh__African_Mammal_FoodWebs_Locations.csv`
- Top 1: `dryad__10.5061_dryad.zkh1893nh__African_Mammal_FoodWebs_Locations.csv`
- Top 1 correct: `True`
- Overlap terms: `african, code, community, country, food, latitude, locations, mammal, name, web`

#### mammal_functional_traits

- Expected: `dryad__10.5061_dryad.zkh1893nh__functional_traits.csv`
- Top 1: `dryad__10.5061_dryad.zkh1893nh__functional_traits.csv`
- Top 1 correct: `True`
- Overlap terms: `bird, invertebrate, mammal, mass, species, traits, vertebrate`

#### weather_station_meteorology

- Expected: `dryad__10.5061_dryad.dv41ns266__weatherMQ-FP-20261011.csv`
- Top 1: `dryad__10.5061_dryad.dv41ns266__weatherMQ-FP-20261011.csv`
- Top 1 correct: `True`
- Overlap terms: `barometric, data, date, direction, gust, humidity, pressure, rainfall, relative, speed`

## schema_enhanced_semantic_merged

| Metric | Value |
| --- | ---: |
| recall_at_1 | 1.0000 |
| recall_at_3 | 1.0000 |
| precision_at_1 | 1.0000 |
| precision_at_3 | 0.3333 |
| mrr | 1.0000 |
| ndcg_at_3 | 1.0000 |

### Query Cases

#### hailstorm_tracks_geo_time

- Expected: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1: `zenodo__record_15008662__unique_tracks_90.csv`
- Top 1 correct: `True`
- Overlap terms: `csv, dataset, hailstorm, intensity, latitude, longitude, storm, tracks`

#### indoor_air_sensor_pollutants

- Expected: `zenodo__record_18195710__ensensia_raw_20230728-20251202_school_5.csv`
- Top 1: `zenodo__record_18195710__ensensia_raw_20230728-20251202_school_5.csv`
- Top 1 correct: `True`
- Overlap terms: `5, co2, humidity, no2, o3, school, sensor, series, temperature, time`

#### atmospheric_hdf5_station

- Expected: `zenodo__record_3660832__Data_01_Jan_2019.h5`
- Top 1: `zenodo__record_3660832__Data_01_Jan_2019.h5`
- Top 1 correct: `True`
- Overlap terms: `atmospheric, data, file, hdf5, jan, january, meteorological, nitrogen, oxides, ozone`

#### wind_lidar_time_series

- Expected: `zenodo__record_5935524__20211108_ZXLidar_Winds.csv`
- Top 1: `zenodo__record_5935524__20211108_ZXLidar_Winds.csv`
- Top 1 correct: `True`
- Overlap terms: `direction, exponent, measurements, series, shear, speed, time, wind`

#### particle_counts_time_series

- Expected: `zenodo__record_5935524__20211108_Sensit.csv`
- Top 1: `zenodo__record_5935524__20211108_Sensit.csv`
- Top 1 correct: `True`
- Overlap terms: `counts, data, field, particle, second, sensor, series, time`

#### tide_water_level_series

- Expected: `zenodo__record_5935524__20211108_Tides.csv`
- Top 1: `zenodo__record_5935524__20211108_Tides.csv`
- Top 1 correct: `True`
- Overlap terms: `level, measurements, series, still, tidal, time, water`

#### greenland_cod_telemetry_positions

- Expected: `dryad__10.5061_dryad.2f2b3__Season_and_site_fidelity_determine_home_range_of_dispersing_and_resident_juvenile_Greenland_cod_(Gadus_ogac)_in_a_Newfoundland_fjord_year1.csv`
- Top 1: `dryad__10.5061_dryad.2f2b3__Season_and_site_fidelity_determine_home_range_of_dispersing_and_resident_juvenile_Greenland_cod_(Gadus_ogac)_in_a_Newfoundland_fjord_year1.csv`
- Top 1 correct: `True`
- Overlap terms: `cod, cove, data, first, greenland, juvenile, time, transplant, year, year1`

#### african_mammal_site_locations

- Expected: `dryad__10.5061_dryad.zkh1893nh__African_Mammal_FoodWebs_Locations.csv`
- Top 1: `dryad__10.5061_dryad.zkh1893nh__African_Mammal_FoodWebs_Locations.csv`
- Top 1 correct: `True`
- Overlap terms: `african, code, community, country, food, latitude, locations, longitude, mammal, name`

#### mammal_functional_traits

- Expected: `dryad__10.5061_dryad.zkh1893nh__functional_traits.csv`
- Top 1: `dryad__10.5061_dryad.zkh1893nh__functional_traits.csv`
- Top 1 correct: `True`
- Overlap terms: `bird, invertebrate, mammal, mass, species, traits, vertebrate`

#### weather_station_meteorology

- Expected: `dryad__10.5061_dryad.dv41ns266__weatherMQ-FP-20261011.csv`
- Top 1: `dryad__10.5061_dryad.dv41ns266__weatherMQ-FP-20261011.csv`
- Top 1 correct: `True`
- Overlap terms: `barometric, data, date, direction, gust, humidity, pressure, rainfall, relative, speed`

