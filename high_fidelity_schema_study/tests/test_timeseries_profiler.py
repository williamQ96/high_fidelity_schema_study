from __future__ import annotations

import unittest

from high_fidelity_schema_study.extractors.timeseries_profiler import infer_time_series_metadata
from high_fidelity_schema_study.models import FieldSchema


class TimeSeriesProfilerTests(unittest.TestCase):
    def test_infers_regular_hourly_series(self) -> None:
        fields = [
            FieldSchema(field_name="timestamp", field_path="timestamp", physical_type="datetime"),
            FieldSchema(
                field_name="station_id",
                field_path="station_id",
                physical_type="string",
                logical_type="identifier",
                semantic_type="identifier",
            ),
            FieldSchema(field_name="temperature", field_path="temperature", physical_type="float"),
        ]
        samples = {
            "timestamp": [
                "2026-01-01 00:00:00",
                "2026-01-01 01:00:00",
                "2026-01-01 02:00:00",
            ],
            "station_id": ["A", "A", "A"],
            "temperature": ["1.2", "1.4", "1.3"],
        }

        metadata = infer_time_series_metadata(samples, fields)

        self.assertEqual(metadata["time_axis"]["field"], "timestamp")
        self.assertEqual(metadata["time_axis"]["frequency"], "1 hour")
        self.assertEqual(metadata["time_axis"]["regularity"], "regular")
        self.assertEqual(metadata["series_identifier"], "station_id")
        self.assertIn("temperature", metadata["measurements"])

    def test_infers_mostly_regular_series_with_one_gap(self) -> None:
        fields = [
            FieldSchema(field_name="ts_utc", field_path="ts_utc", physical_type="datetime"),
            FieldSchema(
                field_name="sensor_id",
                field_path="sensor_id",
                physical_type="string",
                logical_type="identifier",
                semantic_type="identifier",
            ),
            FieldSchema(field_name="power_kw", field_path="power_kw", physical_type="float"),
        ]
        samples = {
            "ts_utc": [
                "2026-05-02T00:00:00Z",
                "2026-05-02T00:15:00Z",
                "2026-05-02T00:30:00Z",
                "2026-05-02T01:00:00Z",
                "2026-05-02T01:15:00Z",
                "2026-05-02T01:30:00Z",
            ],
            "sensor_id": ["MTR-9"] * 6,
            "power_kw": ["4.2", "4.1", "4.0", "4.4", "4.3", "4.2"],
        }

        metadata = infer_time_series_metadata(samples, fields)

        self.assertEqual(metadata["time_axis"]["frequency"], "15 minutes")
        self.assertEqual(metadata["time_axis"]["regularity"], "mostly_regular")
        self.assertEqual(metadata["time_axis"]["missing_intervals"], 1)

    def test_requires_strong_time_field_name(self) -> None:
        fields = [
            FieldSchema(field_name="collection_date", field_path="collection_date", physical_type="datetime"),
            FieldSchema(
                field_name="site_code",
                field_path="site_code",
                physical_type="string",
                logical_type="identifier",
                semantic_type="identifier",
            ),
            FieldSchema(field_name="ph", field_path="ph", physical_type="float"),
        ]
        samples = {
            "collection_date": ["2026-04-11", "2026-04-12", "2026-04-13"],
            "site_code": ["UP_A", "UP_A", "DN_B"],
            "ph": ["7.2", "7.1", "6.8"],
        }

        metadata = infer_time_series_metadata(samples, fields)

        self.assertEqual(metadata, {})

    def test_requires_numeric_measurements(self) -> None:
        fields = [
            FieldSchema(field_name="dt_obs", field_path="dt_obs", physical_type="datetime"),
            FieldSchema(field_name="flag", field_path="flag", physical_type="string"),
        ]
        samples = {
            "dt_obs": [
                "2026-03-01 12:00:00",
                "2026-03-01 12:05:00",
                "2026-03-01 12:10:00",
            ],
            "flag": ["A", "B", "A"],
        }

        metadata = infer_time_series_metadata(samples, fields)

        self.assertEqual(metadata, {})

    def test_assembles_split_time_columns(self) -> None:
        fields = [
            FieldSchema(field_name="Year", field_path="Year", physical_type="int"),
            FieldSchema(field_name="Month", field_path="Month", physical_type="int"),
            FieldSchema(field_name="Day", field_path="Day", physical_type="int"),
            FieldSchema(field_name="Hour", field_path="Hour", physical_type="int"),
            FieldSchema(field_name="Minute", field_path="Minute", physical_type="int"),
            FieldSchema(field_name="Second", field_path="Second", physical_type="int"),
            FieldSchema(field_name="Wind_Speed_m_s", field_path="Wind_Speed_m_s", physical_type="float"),
        ]
        samples = {
            "Year": ["2021", "2021", "2021"],
            "Month": ["11", "11", "11"],
            "Day": ["8", "8", "8"],
            "Hour": ["0", "0", "0"],
            "Minute": ["6", "6", "6"],
            "Second": ["47", "48", "49"],
            "Wind_Speed_m_s": ["15.4", "15.8", "16.0"],
        }

        metadata = infer_time_series_metadata(samples, fields)

        self.assertEqual(metadata["time_axis"]["field"], "computed_from_parts")
        self.assertEqual(metadata["time_axis"]["computed_from"], ["Year", "Month", "Day", "Hour", "Minute", "Second"])
        self.assertEqual(metadata["time_axis"]["frequency"], "1 second")
        self.assertEqual(metadata["time_axis"]["regularity"], "regular")
        self.assertIn("Wind_Speed_m_s", metadata["measurements"])

    def test_exact_date_field_can_drive_time_series(self) -> None:
        fields = [
            FieldSchema(field_name="sensor_id", field_path="sensor_id", physical_type="string", logical_type="identifier", semantic_type="sensor_identifier"),
            FieldSchema(field_name="date", field_path="date", physical_type="datetime", semantic_type="observation_time"),
            FieldSchema(field_name="pm25", field_path="pm25", physical_type="int"),
        ]
        samples = {
            "sensor_id": ["A", "A", "A"],
            "date": ["2023-07-28 08:50:00", "2023-07-28 09:10:00", "2023-07-28 09:30:00"],
            "pm25": ["6", "6", "9"],
        }

        metadata = infer_time_series_metadata(samples, fields)

        self.assertEqual(metadata["time_axis"]["field"], "date")
        self.assertEqual(metadata["time_axis"]["frequency"], "20 minutes")
        self.assertEqual(metadata["series_identifier"], "sensor_id")


if __name__ == "__main__":
    unittest.main()
