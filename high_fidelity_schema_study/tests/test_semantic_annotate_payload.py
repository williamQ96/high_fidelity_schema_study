from __future__ import annotations

import unittest

from high_fidelity_schema_study.semantic_annotate import compact_task_payload


class SemanticAnnotatePayloadTests(unittest.TestCase):
    def test_compact_payload_marks_uncertain_fields_as_annotation_targets(self) -> None:
        task_payload = {
            "task": {
                "task_id": "internal::demo",
                "dataset_id": "demo",
                "file_format": "csv",
                "data_modality": "tabular",
                "grounding_snippets": [
                    {
                        "source_type": "dataset_readme",
                        "detail": "local README",
                        "priority": 1,
                        "text": "`val` mixes numeric observations with non-detect markers",
                    }
                ],
                "instructions": [],
                "deterministic_schema": {
                    "fields": [
                        {
                            "field_name": "val",
                            "field_path": "val",
                            "physical_type": "string",
                            "logical_type": "unknown",
                            "semantic_type": "unknown",
                            "unit": None,
                            "shape": None,
                            "description": None,
                            "example_values": ["17.2", "ND"],
                            "value_range": None,
                            "confidence": 0.9,
                            "uncertainty_reason": "conservative fallback to string",
                            "source_evidence": [
                                {
                                    "evidence_type": "csv_header",
                                    "detail": "header='val'",
                                }
                            ],
                        },
                        {
                            "field_name": "zc",
                            "field_path": "zc",
                            "physical_type": "string",
                            "logical_type": "unknown",
                            "semantic_type": "postal_zone_code",
                            "unit": None,
                            "shape": None,
                            "description": None,
                            "example_values": ["02139", "94107"],
                            "value_range": None,
                            "confidence": 0.9,
                            "uncertainty_reason": "conservative fallback to string",
                            "source_evidence": [],
                        },
                    ]
                },
            }
        }

        compact = compact_task_payload(task_payload)
        targets = {field["field_path"]: field for field in compact["task"]["annotation_targets"]}

        self.assertIn("val", targets)
        self.assertIn("logical_type is unresolved", targets["val"]["annotation_goal"])
        self.assertIn("semantic_type is unresolved", targets["val"]["annotation_goal"])
        self.assertEqual(targets["zc"]["semantic_logical_hint"], "identifier")

    def test_compact_payload_includes_explicit_review_targets(self) -> None:
        task_payload = {
            "task": {
                "task_id": "internal::demo",
                "dataset_id": "demo",
                "file_format": "csv",
                "data_modality": "tabular",
                "grounding_snippets": [],
                "instructions": [],
                "deterministic_schema": {
                    "fields": [
                        {
                            "field_name": "elevation_m",
                            "field_path": "elevation_m",
                            "physical_type": "int",
                            "logical_type": "coordinate",
                            "semantic_type": "elevation",
                            "unit": "meter",
                            "shape": None,
                            "description": None,
                            "example_values": ["312", "128"],
                            "value_range": [15.0, 312.0],
                            "confidence": 1.0,
                            "uncertainty_reason": None,
                            "source_evidence": [],
                        }
                    ]
                },
            }
        }

        compact = compact_task_payload(task_payload, ["elevation_m"])
        targets = compact["task"]["annotation_targets"]

        self.assertEqual([field["field_path"] for field in targets], ["elevation_m"])
        self.assertEqual(targets[0]["semantic_logical_hint"], "measurement")
        self.assertIn("explicitly selected for semantic review", targets[0]["annotation_goal"])


if __name__ == "__main__":
    unittest.main()
