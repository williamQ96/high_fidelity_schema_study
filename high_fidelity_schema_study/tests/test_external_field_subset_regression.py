from __future__ import annotations

import json
import unittest
from pathlib import Path


DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


def load_json(relative_path: str) -> dict:
    return json.loads((DATA_ROOT / relative_path).read_text(encoding="utf-8-sig"))


def fields_by_path(schema: dict) -> dict:
    return {field["field_path"]: field for field in schema["fields"]}


class ExternalFieldSubsetRegressionTests(unittest.TestCase):
    def test_greenland_cod_year1_semantic_subset(self) -> None:
        schema = load_json(
            "semantic_merged/external/"
            "external_Season_and_site_fidelity_determine_home_range_of_dispersing__f2aa642218.merged.json"
        )
        fields = fields_by_path(schema)

        expected = {
            "Hourbin": "time_axis",
            "COA_Lat": "coordinate",
            "COA_Lon": "coordinate",
            "Tag": "identifier",
            "Transplant": "label",
            "Cove": "label",
        }
        for field_path, logical_type in expected.items():
            with self.subTest(field_path=field_path):
                self.assertEqual(fields[field_path]["logical_type"], logical_type)
                self.assertTrue(fields[field_path]["semantic_annotation"]["accepted_for_merge"])

    def test_functional_traits_semantic_subset(self) -> None:
        schema = load_json("semantic_merged/external/external_functional_traits_7e780659c0.merged.json")
        fields = fields_by_path(schema)

        self.assertEqual(fields["Species"]["logical_type"], "identifier")
        self.assertTrue(fields["Species"]["semantic_annotation"]["accepted_for_merge"])
        self.assertEqual(fields["Mass.g"]["logical_type"], "measurement")
        self.assertEqual(fields["Mass.g"]["unit"], "g")
        self.assertTrue(fields["Mass.g"]["semantic_annotation"]["accepted_for_merge"])

    def test_weather_station_semantic_subset(self) -> None:
        schema = load_json("semantic_merged/external/external_weatherMQ-FP-20261011_3f95de2293.merged.json")
        fields = fields_by_path(schema)

        expected = {
            "dateTime": ("time_axis", "time_axis", None),
            "temperature": ("measurement", "air_temperature", None),
            "relativeHumidity": ("measurement", "relative_humidity", None),
            "barometricPressure": ("measurement", "surface_pressure", None),
            "rainfall": ("measurement", "precipitation", None),
            "windSpeed": ("measurement", "wind_speed", "m/s"),
        }
        for field_path, (logical_type, semantic_type, unit) in expected.items():
            with self.subTest(field_path=field_path):
                self.assertEqual(fields[field_path]["logical_type"], logical_type)
                self.assertEqual(fields[field_path]["semantic_type"], semantic_type)
                self.assertEqual(fields[field_path].get("unit"), unit)


if __name__ == "__main__":
    unittest.main()
