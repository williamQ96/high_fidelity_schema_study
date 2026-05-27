from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from high_fidelity_schema_study.extractors.csv_extractor import extract_csv_schema


class CsvExtractorTests(unittest.TestCase):
    def test_extracts_conservative_types_and_time_series_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "weather.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["station_id", "timestamp", "temp_C"])
                writer.writerow(["00123", "2026-01-01 00:00:00", "12.5"])
                writer.writerow(["00123", "2026-01-01 01:00:00", "13.1"])
                writer.writerow(["00123", "2026-01-01 02:00:00", "11.8"])

            schema = extract_csv_schema(str(csv_path))

        fields = {field.field_name: field for field in schema.fields}
        self.assertEqual(schema.file_format, "csv")
        self.assertEqual(schema.data_modality, "time_series")
        self.assertEqual(fields["station_id"].physical_type, "string")
        self.assertEqual(fields["station_id"].semantic_type, "station_identifier")
        self.assertEqual(fields["timestamp"].physical_type, "datetime")
        self.assertEqual(fields["timestamp"].logical_type, "time_axis")
        self.assertEqual(fields["temp_C"].physical_type, "float")
        self.assertEqual(fields["temp_C"].unit, "Celsius")
        self.assertEqual(fields["temp_C"].unit_normalization["status"], "normalized_ucum")
        self.assertEqual(fields["temp_C"].unit_normalization["ucum_code"], "Cel")
        self.assertEqual(fields["temp_C"].logical_type, "measurement")
        self.assertEqual(fields["temp_C"].semantic_type, "air_temperature")
        self.assertEqual(schema.metadata["time_series"]["time_axis"]["frequency"], "1 hour")


if __name__ == "__main__":
    unittest.main()
