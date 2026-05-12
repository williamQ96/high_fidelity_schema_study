import csv
import json
import tempfile
import unittest
from pathlib import Path

from high_fidelity_schema_study.deterministic_profile import infer_multi_file_relationships
from high_fidelity_schema_study.extractors.csv_extractor import extract_csv_schema


DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


class DeterministicProfileTests(unittest.TestCase):
    def test_csv_profile_records_missingness_and_identifier_quality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "stations.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["station_id", "timestamp", "temp_C"])
                writer.writerow(["ST001", "2026-01-01 00:00:00", "12.5"])
                writer.writerow(["ST001", "2026-01-01 01:00:00", ""])
                writer.writerow(["ST002", "2026-01-01 02:00:00", "13.1"])

            schema = extract_csv_schema(str(csv_path))

        profile = schema.metadata["deterministic_profile"]
        temp_profile = {
            item["field_path"]: item
            for item in profile["missingness"]["fields"]
        }["temp_C"]
        self.assertEqual(temp_profile["missing_count"], 1)
        self.assertEqual(temp_profile["missing_ratio"], 0.3333)

        identifier_profile = {
            item["field_path"]: item
            for item in profile["identifier_quality"]["fields"]
        }["station_id"]
        self.assertEqual(identifier_profile["quality"], "group_identifier")
        self.assertEqual(identifier_profile["duplicate_count"], 1)

    def test_relationship_profile_links_shared_identifier_semantics(self) -> None:
        relationship_profile = infer_multi_file_relationships(
            [
                {
                    "study_dataset_id": "left",
                    "fields": [
                        {
                            "field_path": "station_id",
                            "logical_type": "identifier",
                            "semantic_type": "station_identifier",
                        }
                    ],
                },
                {
                    "study_dataset_id": "right",
                    "fields": [
                        {
                            "field_path": "/station_id",
                            "logical_type": "identifier",
                            "semantic_type": "station_identifier",
                        }
                    ],
                },
            ]
        )

        self.assertEqual(relationship_profile["relationship_count"], 1)
        self.assertEqual(
            relationship_profile["relationships"][0]["relationship_type"],
            "shared_identifier_semantic",
        )

    def test_checked_in_internal_derived_manifest_points_to_relationship_profile(self) -> None:
        manifest = json.loads((DATA_ROOT / "derived" / "derived_manifest.json").read_text(encoding="utf-8"))
        relationship_path = DATA_ROOT / manifest["profile_files"]["internal_relationship_profile"]
        relationship_profile = json.loads(relationship_path.read_text(encoding="utf-8"))

        self.assertEqual(relationship_profile["dataset_count"], 9)
        self.assertGreaterEqual(
            relationship_profile["relationship_counts"]["shared_identifier_semantic"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
