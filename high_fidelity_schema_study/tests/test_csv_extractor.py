from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from high_fidelity_schema_study.extractors.base import ExtractionRequest
from high_fidelity_schema_study.extractors.csv_extractor import extract_csv_schema
from high_fidelity_schema_study.extractors.registry import extract_path
from high_fidelity_schema_study.unified_schema import build_unified_schema_envelope


ROOT = Path(__file__).resolve().parents[1]


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

    def test_ml_gpu_training_log_avoids_air_temperature_and_channel_unit_overclaims(self) -> None:
        csv_path = ROOT / "testdata" / "csv" / "ml_gpu_training_log.csv"

        outcome = extract_path(ExtractionRequest(str(csv_path)))
        schema = outcome.schema
        envelope = build_unified_schema_envelope(outcome)

        fields = {field.field_name: field for field in schema.fields}
        self.assertEqual(outcome.status, "success")
        self.assertEqual(len(schema.fields), 32)
        self.assertEqual(schema.metadata["column_count"], 32)
        self.assertEqual(fields["max_gpu_temp"].semantic_type, "gpu_temperature")
        self.assertEqual(fields["avg_gpu_temp"].semantic_type, "gpu_temperature")
        self.assertNotEqual(fields["max_gpu_temp"].semantic_type, "air_temperature")
        self.assertNotEqual(fields["avg_gpu_temp"].semantic_type, "air_temperature")
        self.assertEqual(fields["max_gpu_temp"].logical_type, "measurement")
        self.assertEqual(fields["avg_gpu_temp"].logical_type, "measurement")
        self.assertEqual(fields["input_dim_c"].semantic_type, "input_channel_count")
        self.assertEqual(fields["input_dim_c"].logical_type, "attribute")
        self.assertIsNone(fields["input_dim_c"].unit)
        self.assertEqual(fields["input_dim_c"].unit_normalization["status"], "no_unit_claim")

        semantic_hints = {
            item["field_path"]: item["semantic_type"]
            for item in envelope["semantic_hints"]
        }
        unit_paths = {item["field_path"] for item in envelope["units"] if item["unit"] is not None}
        self.assertEqual(len(envelope["physical_structure"]["fields"]), 32)
        self.assertEqual(semantic_hints["max_gpu_temp"], "gpu_temperature")
        self.assertEqual(semantic_hints["avg_gpu_temp"], "gpu_temperature")
        self.assertNotIn("input_dim_c", unit_paths)
        self.assertTrue(envelope["logical_roles"])
        self.assertTrue(envelope["semantic_hints"])

    def test_generic_temp_and_c_suffix_do_not_promote_without_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "generic.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["temp", "value_c"])
                writer.writerow(["25.0", "3"])
                writer.writerow(["26.0", "4"])

            schema = extract_csv_schema(str(csv_path))

        fields = {field.field_name: field for field in schema.fields}
        self.assertEqual(fields["temp"].semantic_type, "unknown")
        self.assertIsNone(fields["temp"].unit)
        self.assertEqual(fields["value_c"].semantic_type, "unknown")
        self.assertIsNone(fields["value_c"].unit)
        self.assertEqual(fields["value_c"].unit_normalization["status"], "no_unit_claim")


if __name__ == "__main__":
    unittest.main()
