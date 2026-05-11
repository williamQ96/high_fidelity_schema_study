from __future__ import annotations

import csv
import json
from pathlib import Path

import h5py
import numpy as np


ROOT = Path(__file__).resolve().parent / "data"
RAW_ROOT = ROOT / "raw"
GOLD_ROOT = ROOT / "gold"
DERIVED_ROOT = ROOT / "derived"
RETRIEVAL_ROOT = ROOT / "retrieval"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def write_json(path: Path, payload: object) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_csv_dataset(base_dir: Path, filename: str, header: list[str], rows: list[list[object]], readme: str) -> None:
    ensure_dir(base_dir)
    with (base_dir / filename).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    write_text(base_dir / "README.md", readme)


def write_hdf5_dataset(base_dir: Path, filename: str, builder, readme: str) -> None:
    ensure_dir(base_dir)
    path = base_dir / filename
    with h5py.File(path, "w") as handle:
        builder(handle)
    write_text(base_dir / "README.md", readme)


def gold_field(
    field_name: str,
    field_path: str,
    physical_type: str,
    logical_type: str,
    semantic_type: str,
    necessity: str,
    unit: str | None = None,
    notes: str | None = None,
    evidence: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "field_name": field_name,
        "field_path": field_path,
        "correct_physical_type": physical_type,
        "correct_logical_type": logical_type,
        "correct_semantic_type": semantic_type,
        "unit": unit,
        "necessity": necessity,
        "notes": notes,
        "gold_evidence": evidence or [],
    }


def gold_dataset(
    dataset_id: str,
    file_format: str,
    difficulty: str,
    data_modality: str,
    source_file: str,
    fields: list[dict[str, object]],
    notes: list[str],
    time_axis: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "dataset_id": dataset_id,
        "file_format": file_format,
        "difficulty": difficulty,
        "data_modality": data_modality,
        "source_file": source_file,
        "time_axis": time_axis,
        "fields": fields,
        "notes": notes,
    }


def build_hdf5_easy(handle: h5py.File) -> None:
    handle.attrs["title"] = "Easy climate cube"
    coords = handle.create_group("coords")
    observations = handle.create_group("observations")

    time_ds = coords.create_dataset("time", data=np.array([0, 1, 2, 3], dtype=np.int32))
    time_ds.attrs["units"] = "hours since 2026-01-01 00:00:00 UTC"
    time_ds.attrs["long_name"] = "forecast lead hour"

    station_dtype = h5py.string_dtype(encoding="utf-8")
    station_ds = coords.create_dataset("station_id", data=np.array(["ST001", "ST002"], dtype=object), dtype=station_dtype)
    station_ds.attrs["long_name"] = "weather station identifier"

    temp_ds = observations.create_dataset(
        "temperature",
        data=np.array(
            [
                [12.5, 13.1],
                [12.1, 12.8],
                [11.7, 12.2],
                [11.2, 11.9],
            ],
            dtype=np.float32,
        ),
    )
    temp_ds.attrs["unit"] = "C"
    temp_ds.attrs["long_name"] = "air temperature"

    humidity_ds = observations.create_dataset(
        "humidity",
        data=np.array(
            [
                [61.0, 58.0],
                [64.0, 60.0],
                [66.0, 62.0],
                [68.0, 63.0],
            ],
            dtype=np.float32,
        ),
    )
    humidity_ds.attrs["unit"] = "%"
    humidity_ds.attrs["long_name"] = "relative humidity"


def build_hdf5_medium(handle: h5py.File) -> None:
    weather = handle.create_group("weather")
    weather.attrs["description"] = "Nested station hierarchy with partial metadata"

    ts_dtype = h5py.string_dtype(encoding="utf-8")
    timestamps = weather.create_dataset(
        "timestamp",
        data=np.array(
            [
                "2026-02-01T00:00:00",
                "2026-02-01T01:00:00",
                "2026-02-01T02:00:00",
            ],
            dtype=object,
        ),
        dtype=ts_dtype,
    )
    timestamps.attrs["long_name"] = "observation timestamp"

    for station_id, station_name, temp_values, pressure_values, include_pressure_attrs in [
        ("station_001", "North Ridge", [12.0, 11.8, 11.4], [1012.0, 1011.5, 1011.0], True),
        ("station_002", "Coastal Bay", [13.2, 13.0, 12.7], [1009.0, 1008.8, 1008.3], False),
    ]:
        group = weather.create_group(station_id)
        group.attrs["station_name"] = station_name
        group.attrs["station_id"] = station_id

        temp_ds = group.create_dataset("temp", data=np.array(temp_values, dtype=np.float32))
        temp_ds.attrs["unit"] = "C"
        temp_ds.attrs["long_name"] = "air temperature"

        pressure_ds = group.create_dataset("pressure", data=np.array(pressure_values, dtype=np.float32))
        if include_pressure_attrs:
            pressure_ds.attrs["unit"] = "hPa"
            pressure_ds.attrs["long_name"] = "surface pressure"


def build_hdf5_hard(handle: h5py.File) -> None:
    campaign = handle.create_group("campaign")
    meta = campaign.create_group("meta")
    run_group = campaign.create_group("run_01")
    cast_dtype = h5py.string_dtype(encoding="utf-8")

    meta.create_dataset("station_code", data=np.array("NP-ALPHA", dtype=object), dtype=cast_dtype)
    meta.create_dataset("platform", data=np.array("research_vessel", dtype=object), dtype=cast_dtype)

    for cast_name, temp_values, salinity_values in [
        ("cast_0001", [14.1, 13.7, 13.2, 12.8], [33.1, 33.4, 33.8, 34.0]),
        ("cast_0002", [14.4, 14.0, 13.5, 13.0], [32.9, 33.2, 33.7, 33.9]),
    ]:
        cast = run_group.create_group(cast_name)
        depth_ds = cast.create_dataset("depth_m", data=np.array([0, 10, 20, 30], dtype=np.int32))
        depth_ds.attrs["unit"] = "m"
        depth_ds.attrs["long_name"] = "depth below sea surface"

        temp_ds = cast.create_dataset("temp", data=np.array(temp_values, dtype=np.float32))
        if cast_name == "cast_0002":
            temp_ds.attrs["unit"] = "C"
        temp_ds.attrs["long_name"] = "seawater temperature"

        salinity_ds = cast.create_dataset("salinity_psu", data=np.array(salinity_values, dtype=np.float32))
        salinity_ds.attrs["long_name"] = "practical salinity"

        qc_ds = cast.create_dataset(
            "qc_flag",
            data=np.array(["A", "A", "B", "A"], dtype=object),
            dtype=cast_dtype,
        )
        qc_ds.attrs["long_name"] = "quality control flag"


def create_csv_and_time_series() -> list[dict[str, object]]:
    manifest_entries: list[dict[str, object]] = []

    datasets = [
        {
            "category": "csv",
            "dataset_id": "csv_easy_weather_stations",
            "difficulty": "easy",
            "filename": "stations_precip.csv",
            "header": ["station_id", "station_name", "latitude_deg", "longitude_deg", "elevation_m", "precip_mm"],
            "rows": [
                ["USC0001", "North Ridge", 34.200, -118.520, 312, 0.0],
                ["USC0002", "River Bend", 34.145, -118.310, 128, 4.6],
                ["USC0003", "Coastal Bay", 33.912, -118.442, 15, 1.2],
            ],
            "readme": """
# csv_easy_weather_stations

Small station registry with explicit unit-bearing column names.

- `latitude_deg` and `longitude_deg` are decimal degrees
- `elevation_m` is meters above sea level
- `precip_mm` is daily precipitation in millimeters
""",
            "gold": gold_dataset(
                dataset_id="csv_easy_weather_stations",
                file_format="csv",
                difficulty="easy",
                data_modality="tabular",
                source_file="stations_precip.csv",
                fields=[
                    gold_field("station_id", "station_id", "string", "identifier", "station_identifier", "high"),
                    gold_field("station_name", "station_name", "string", "label", "station_name", "medium"),
                    gold_field("latitude_deg", "latitude_deg", "float", "coordinate", "latitude", "high", unit="degree"),
                    gold_field("longitude_deg", "longitude_deg", "float", "coordinate", "longitude", "high", unit="degree"),
                    gold_field("elevation_m", "elevation_m", "float", "measurement", "elevation", "medium", unit="meter"),
                    gold_field("precip_mm", "precip_mm", "float", "measurement", "precipitation", "high", unit="millimeter"),
                ],
                notes=["Clean header names and explicit unit suffixes should make this an easy physical and semantic extraction case."],
            ),
        },
        {
            "category": "csv",
            "dataset_id": "csv_medium_water_quality",
            "difficulty": "medium",
            "filename": "water_quality.csv",
            "header": ["sample_id", "site_code", "collection_date", "ph", "do_mg_l", "turbidity_ntu", "notes"],
            "rows": [
                ["00017", "UP_A", "2026-04-11", 7.2, 8.9, 3.2, ""],
                ["00018", "UP_A", "2026-04-12", 7.1, 8.7, 3.9, "duplicate bottle"],
                ["00019", "DN_B", "2026-04-12", 6.8, 7.6, 9.8, ""],
                ["00020", "DN_B", "2026-04-13", 6.9, 7.8, 8.4, "rain event"],
            ],
            "readme": """
# csv_medium_water_quality

Discrete water-quality samples collected at multiple sites.

- `sample_id` preserves leading zeros
- `do_mg_l` is dissolved oxygen in milligrams per liter
- `turbidity_ntu` is turbidity in nephelometric turbidity units
- notes may be empty
""",
            "gold": gold_dataset(
                dataset_id="csv_medium_water_quality",
                file_format="csv",
                difficulty="medium",
                data_modality="tabular",
                source_file="water_quality.csv",
                fields=[
                    gold_field("sample_id", "sample_id", "string", "identifier", "sample_identifier", "high", notes="Leading zeros are significant."),
                    gold_field("site_code", "site_code", "string", "identifier", "site_identifier", "high"),
                    gold_field("collection_date", "collection_date", "datetime", "attribute", "collection_date", "high"),
                    gold_field("ph", "ph", "float", "measurement", "acidity_ph", "high"),
                    gold_field("do_mg_l", "do_mg_l", "float", "measurement", "dissolved_oxygen", "high", unit="milligram_per_liter"),
                    gold_field("turbidity_ntu", "turbidity_ntu", "float", "measurement", "turbidity", "medium", unit="NTU"),
                    gold_field("notes", "notes", "string", "label", "free_text_note", "low"),
                ],
                notes=["Mixed explicit metadata quality. Semantic meaning is partially recoverable from names and README."],
            ),
        },
        {
            "category": "csv",
            "dataset_id": "csv_hard_field_campaign",
            "difficulty": "hard",
            "filename": "field_campaign.csv",
            "header": ["rec", "dt_obs", "zc", "val", "flag", "device"],
            "rows": [
                ["0001", "2026-03-01 12:00:00", "94107", "17.2", "A", "SN-01"],
                ["0002", "2026-03-01 12:05:00", "02139", "ND", "C", "SN-01"],
                ["0003", "2026-03-01 12:10:00", "10001", "18.4", "A", "SN-02"],
                ["0004", "2026-03-01 12:15:00", "30301", "ERR", "B", "SN-02"],
            ],
            "readme": """
# csv_hard_field_campaign

Messy field campaign export with overloaded abbreviations.

- `rec` is the row-level record identifier
- `dt_obs` is the observation timestamp
- `zc` is a postal zone code, not a numeric quantity
- `val` mixes numeric observations with non-detect and error markers
- `flag` is a quality-control code
""",
            "gold": gold_dataset(
                dataset_id="csv_hard_field_campaign",
                file_format="csv",
                difficulty="hard",
                data_modality="tabular",
                source_file="field_campaign.csv",
                fields=[
                    gold_field("rec", "rec", "string", "identifier", "record_identifier", "high", notes="Leading zeros are significant."),
                    gold_field("dt_obs", "dt_obs", "datetime", "attribute", "observation_time", "high"),
                    gold_field("zc", "zc", "string", "identifier", "postal_zone_code", "medium", notes="Should remain string because leading zeros are meaningful."),
                    gold_field("val", "val", "string", "measurement", "unknown", "high", notes="Physical type should remain string because values mix numerics, ND, and ERR."),
                    gold_field("flag", "flag", "string", "label", "quality_flag", "medium"),
                    gold_field("device", "device", "string", "identifier", "device_identifier", "medium"),
                ],
                notes=["This dataset is intentionally ambiguous. Marking `val` unknown is preferable to over-claiming a numeric type."],
            ),
        },
        {
            "category": "time_series",
            "dataset_id": "ts_easy_hourly_weather",
            "difficulty": "easy",
            "filename": "hourly_weather.csv",
            "header": ["station_id", "timestamp", "temp_C", "humidity_pct", "wind_speed_m_s"],
            "rows": [
                ["ST001", "2026-01-01 00:00:00", 12.5, 61.0, 3.1],
                ["ST001", "2026-01-01 01:00:00", 12.1, 64.0, 3.4],
                ["ST001", "2026-01-01 02:00:00", 11.7, 66.0, 3.2],
                ["ST001", "2026-01-01 03:00:00", 11.2, 68.0, 2.8],
                ["ST001", "2026-01-01 04:00:00", 10.9, 70.0, 2.5],
            ],
            "readme": """
# ts_easy_hourly_weather

Regular hourly weather observations from a single station.

- `timestamp` is local standard time with no daylight-saving transitions in this excerpt
- `temp_C` is air temperature in Celsius
- `humidity_pct` is relative humidity in percent
- `wind_speed_m_s` is wind speed in meters per second
""",
            "gold": gold_dataset(
                dataset_id="ts_easy_hourly_weather",
                file_format="csv",
                difficulty="easy",
                data_modality="time_series",
                source_file="hourly_weather.csv",
                time_axis={
                    "field": "timestamp",
                    "type": "datetime",
                    "timezone": "local_standard_time",
                    "frequency": "1 hour",
                    "regularity": "regular",
                    "missing_intervals": 0,
                },
                fields=[
                    gold_field("station_id", "station_id", "string", "identifier", "station_identifier", "high"),
                    gold_field("timestamp", "timestamp", "datetime", "time_axis", "observation_time", "high"),
                    gold_field("temp_C", "temp_C", "float", "measurement", "air_temperature", "high", unit="Celsius"),
                    gold_field("humidity_pct", "humidity_pct", "float", "measurement", "relative_humidity", "high", unit="percent"),
                    gold_field("wind_speed_m_s", "wind_speed_m_s", "float", "measurement", "wind_speed", "medium", unit="meter_per_second"),
                ],
                notes=["Clean time axis and explicit unit-bearing names make this a canonical easy time-series case."],
            ),
        },
        {
            "category": "time_series",
            "dataset_id": "ts_medium_power_meter",
            "difficulty": "medium",
            "filename": "power_meter.csv",
            "header": ["sensor_id", "ts_utc", "power_kw", "voltage_v", "status"],
            "rows": [
                ["MTR-9", "2026-05-02T00:00:00Z", 4.2, 231.0, "ok"],
                ["MTR-9", "2026-05-02T00:15:00Z", 4.1, 230.8, "ok"],
                ["MTR-9", "2026-05-02T00:30:00Z", 4.0, 230.6, "ok"],
                ["MTR-9", "2026-05-02T01:00:00Z", 4.4, 231.2, "recovered"],
                ["MTR-9", "2026-05-02T01:15:00Z", 4.3, 231.1, "ok"],
                ["MTR-9", "2026-05-02T01:30:00Z", 4.2, 230.9, "ok"],
            ],
            "readme": """
# ts_medium_power_meter

Power-meter telemetry sampled every 15 minutes, with one missing observation in the excerpt.

- `ts_utc` is UTC time
- `power_kw` is real power in kilowatts
- `voltage_v` is line voltage in volts
- `status` records operational state changes
""",
            "gold": gold_dataset(
                dataset_id="ts_medium_power_meter",
                file_format="csv",
                difficulty="medium",
                data_modality="time_series",
                source_file="power_meter.csv",
                time_axis={
                    "field": "ts_utc",
                    "type": "datetime",
                    "timezone": "UTC",
                    "frequency": "15 minutes",
                    "regularity": "mostly_regular",
                    "missing_intervals": 1,
                },
                fields=[
                    gold_field("sensor_id", "sensor_id", "string", "identifier", "sensor_identifier", "high"),
                    gold_field("ts_utc", "ts_utc", "datetime", "time_axis", "observation_time", "high"),
                    gold_field("power_kw", "power_kw", "float", "measurement", "power", "high", unit="kilowatt"),
                    gold_field("voltage_v", "voltage_v", "float", "measurement", "voltage", "medium", unit="volt"),
                    gold_field("status", "status", "string", "label", "operational_status", "medium"),
                ],
                notes=["The time series is mostly regular and should expose one missing interval rather than collapsing to irregular noise."],
            ),
        },
        {
            "category": "time_series",
            "dataset_id": "ts_hard_irregular_buoy",
            "difficulty": "hard",
            "filename": "buoy_irregular.csv",
            "header": ["buoy_id", "event_time", "temp_C", "salinity_psu", "qc_flag"],
            "rows": [
                ["B-17", "2026-08-01T00:07:00", 17.4, 33.2, "A"],
                ["B-17", "2026-08-01T00:26:00", 17.2, 33.3, "A"],
                ["B-17", "2026-08-01T01:12:00", 16.8, 33.5, "B"],
                ["B-17", "2026-08-01T03:47:00", 16.1, 33.9, "A"],
                ["B-17", "2026-08-01T03:55:00", 16.0, 33.9, "A"],
            ],
            "readme": """
# ts_hard_irregular_buoy

Irregular buoy telemetry excerpt.

- `event_time` is emitted by the onboard controller and is not expected to be evenly spaced
- `temp_C` is water temperature in Celsius
- `salinity_psu` is practical salinity
- `qc_flag` is a quality-control code
""",
            "gold": gold_dataset(
                dataset_id="ts_hard_irregular_buoy",
                file_format="csv",
                difficulty="hard",
                data_modality="time_series",
                source_file="buoy_irregular.csv",
                time_axis={
                    "field": "event_time",
                    "type": "datetime",
                    "timezone": "unknown",
                    "frequency": "mixed",
                    "regularity": "irregular",
                    "missing_intervals": None,
                },
                fields=[
                    gold_field("buoy_id", "buoy_id", "string", "identifier", "buoy_identifier", "high"),
                    gold_field("event_time", "event_time", "datetime", "time_axis", "observation_time", "high"),
                    gold_field("temp_C", "temp_C", "float", "measurement", "water_temperature", "high", unit="Celsius"),
                    gold_field("salinity_psu", "salinity_psu", "float", "measurement", "salinity", "high", unit="PSU"),
                    gold_field("qc_flag", "qc_flag", "string", "label", "quality_flag", "medium"),
                ],
                notes=["A correct extractor should identify the time axis but avoid over-claiming a regular sampling frequency."],
            ),
        },
    ]

    for dataset in datasets:
        base_dir = RAW_ROOT / dataset["category"] / dataset["dataset_id"]
        write_csv_dataset(base_dir, dataset["filename"], dataset["header"], dataset["rows"], dataset["readme"])
        write_json(GOLD_ROOT / dataset["category"] / f"{dataset['dataset_id']}.gold.json", dataset["gold"])
        manifest_entries.append(
            {
                "dataset_id": dataset["dataset_id"],
                "category": dataset["category"],
                "difficulty": dataset["difficulty"],
                "file_format": "csv",
                "data_modality": dataset["gold"]["data_modality"],
                "source_file": f"raw/{dataset['category']}/{dataset['dataset_id']}/{dataset['filename']}",
                "gold_file": f"gold/{dataset['category']}/{dataset['dataset_id']}.gold.json",
            }
        )

    return manifest_entries


def create_hdf5() -> list[dict[str, object]]:
    manifest_entries: list[dict[str, object]] = []
    datasets = [
        {
            "dataset_id": "hdf5_easy_climate_cube",
            "difficulty": "easy",
            "filename": "climate_cube.h5",
            "builder": build_hdf5_easy,
            "readme": """
# hdf5_easy_climate_cube

Two-dimensional climate data cube with explicit coordinate datasets and field-level attributes.

- `/coords/time` defines time offsets
- `/coords/station_id` identifies stations
- `/observations/temperature` is air temperature in Celsius
- `/observations/humidity` is relative humidity in percent
""",
            "gold": gold_dataset(
                dataset_id="hdf5_easy_climate_cube",
                file_format="hdf5",
                difficulty="easy",
                data_modality="hierarchical",
                source_file="climate_cube.h5",
                fields=[
                    gold_field("time", "/coords/time", "int32", "time_axis", "forecast_hour", "high", unit="hours since 2026-01-01 00:00:00 UTC"),
                    gold_field("station_id", "/coords/station_id", "string", "identifier", "station_identifier", "high"),
                    gold_field("temperature", "/observations/temperature", "float32", "measurement", "air_temperature", "high", unit="C"),
                    gold_field("humidity", "/observations/humidity", "float32", "measurement", "relative_humidity", "high", unit="%"),
                ],
                notes=["This HDF5 file is intended to be the clean reference case for path-preserving hierarchical extraction."],
            ),
        },
        {
            "dataset_id": "hdf5_medium_station_hierarchy",
            "difficulty": "medium",
            "filename": "station_hierarchy.h5",
            "builder": build_hdf5_medium,
            "readme": """
# hdf5_medium_station_hierarchy

Nested per-station hierarchy with partial metadata.

- `/weather/timestamp` is the shared hourly time axis
- each station group stores `temp` and `pressure`
- `station_002/pressure` intentionally lacks unit metadata
""",
            "gold": gold_dataset(
                dataset_id="hdf5_medium_station_hierarchy",
                file_format="hdf5",
                difficulty="medium",
                data_modality="hierarchical",
                source_file="station_hierarchy.h5",
                fields=[
                    gold_field("timestamp", "/weather/timestamp", "string", "time_axis", "observation_time", "high"),
                    gold_field("temp", "/weather/station_001/temp", "float32", "measurement", "air_temperature", "high", unit="C"),
                    gold_field("pressure", "/weather/station_001/pressure", "float32", "measurement", "surface_pressure", "high", unit="hPa"),
                    gold_field("temp", "/weather/station_002/temp", "float32", "measurement", "air_temperature", "high", unit="C"),
                    gold_field("pressure", "/weather/station_002/pressure", "float32", "measurement", "surface_pressure", "high", unit=None, notes="Unit should remain unknown because metadata is absent."),
                ],
                notes=["The hierarchy itself is part of the schema. Flattening away station groups would lose field identity."],
            ),
        },
        {
            "dataset_id": "hdf5_hard_ocean_profile",
            "difficulty": "hard",
            "filename": "ocean_profile_nested.h5",
            "builder": build_hdf5_hard,
            "readme": """
# hdf5_hard_ocean_profile

Deeply nested ocean-profile hierarchy with repeated casts and partial field metadata.

- `/campaign/run_01/cast_000*/depth_m` is the vertical coordinate
- `/campaign/run_01/cast_000*/temp` stores seawater temperature
- only one cast includes an explicit temperature unit attribute
- salinity is named structurally but not fully attributed
""",
            "gold": gold_dataset(
                dataset_id="hdf5_hard_ocean_profile",
                file_format="hdf5",
                difficulty="hard",
                data_modality="hierarchical",
                source_file="ocean_profile_nested.h5",
                fields=[
                    gold_field("station_code", "/campaign/meta/station_code", "string", "identifier", "station_identifier", "medium"),
                    gold_field("depth_m", "/campaign/run_01/cast_0001/depth_m", "int32", "coordinate", "depth", "high", unit="m"),
                    gold_field("temp", "/campaign/run_01/cast_0001/temp", "float32", "measurement", "water_temperature", "high", unit=None, notes="Unit is not explicit on this path."),
                    gold_field("salinity_psu", "/campaign/run_01/cast_0001/salinity_psu", "float32", "measurement", "salinity", "high", unit=None, notes="PSU is part of the name but not an explicit attribute."),
                    gold_field("qc_flag", "/campaign/run_01/cast_0001/qc_flag", "string", "label", "quality_flag", "medium"),
                    gold_field("depth_m", "/campaign/run_01/cast_0002/depth_m", "int32", "coordinate", "depth", "high", unit="m"),
                    gold_field("temp", "/campaign/run_01/cast_0002/temp", "float32", "measurement", "water_temperature", "high", unit="C"),
                ],
                notes=["The hard case tests whether extraction preserves repeated nested structure and surfaces metadata asymmetry between similar paths."],
            ),
        },
    ]

    for dataset in datasets:
        base_dir = RAW_ROOT / "hdf5" / dataset["dataset_id"]
        write_hdf5_dataset(base_dir, dataset["filename"], dataset["builder"], dataset["readme"])
        write_json(GOLD_ROOT / "hdf5" / f"{dataset['dataset_id']}.gold.json", dataset["gold"])
        manifest_entries.append(
            {
                "dataset_id": dataset["dataset_id"],
                "category": "hdf5",
                "difficulty": dataset["difficulty"],
                "file_format": "hdf5",
                "data_modality": dataset["gold"]["data_modality"],
                "source_file": f"raw/hdf5/{dataset['dataset_id']}/{dataset['filename']}",
                "gold_file": f"gold/hdf5/{dataset['dataset_id']}.gold.json",
            }
        )

    return manifest_entries


def write_root_readme() -> None:
    content = """
# Data Layout

This directory now contains a reproducible 9-dataset pilot corpus for the high-fidelity schema extraction study.

## Structure

- `raw/csv/` contains three tabular CSV pilot datasets
- `raw/time_series/` contains three time-series CSV pilot datasets
- `raw/hdf5/` contains three hierarchical HDF5 pilot datasets
- `gold/` contains one gold schema JSON per dataset
- `derived/` is reserved for deterministic extractor outputs
- `retrieval/` is reserved for retrieval indices and query artifacts
- `pilot_corpus_manifest.json` is the corpus index

All files in `raw/` are deliberately small and human-readable so the study can start with interpretable field-level evaluation before scaling.
"""
    write_text(ROOT / "README.md", content)


def main() -> None:
    for path in [RAW_ROOT, GOLD_ROOT, DERIVED_ROOT, RETRIEVAL_ROOT]:
        ensure_dir(path)

    manifest = create_csv_and_time_series()
    manifest.extend(create_hdf5())
    manifest.sort(key=lambda item: item["dataset_id"])

    write_root_readme()
    write_json(ROOT / "pilot_corpus_manifest.json", {"datasets": manifest})


if __name__ == "__main__":
    main()
