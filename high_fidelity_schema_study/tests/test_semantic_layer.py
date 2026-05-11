from __future__ import annotations

import unittest

from high_fidelity_schema_study.semantic_layer import (
    GroundingSnippet,
    SemanticAnnotationTask,
    build_prompt_payload,
    merge_annotation_result,
    normalize_annotation_result,
    validate_annotation_result,
)


class SemanticLayerTests(unittest.TestCase):
    def test_build_prompt_payload_contains_rules_and_task(self) -> None:
        task = SemanticAnnotationTask(
            task_id="internal::demo",
            dataset_id="demo",
            file_format="csv",
            data_modality="tabular",
            deterministic_schema={"fields": []},
            grounding_snippets=[
                GroundingSnippet(
                    source_type="dataset_readme",
                    source_name="README.md",
                    detail="demo",
                    text="demo grounding",
                    priority=1,
                )
            ],
            instructions=["Use only evidence."],
        )

        payload = build_prompt_payload(task)

        self.assertEqual(payload["task"]["task_id"], "internal::demo")
        self.assertIn("system_rules", payload)
        self.assertIn("expected_output_schema", payload)

    def test_validate_annotation_result(self) -> None:
        task = SemanticAnnotationTask(
            task_id="internal::demo",
            dataset_id="demo",
            file_format="csv",
            data_modality="tabular",
            deterministic_schema={"fields": [{"field_path": "temperature"}]},
        )
        payload = build_prompt_payload(task)
        result = {
            "task_id": "internal::demo",
            "annotations": [
                {
                    "field_path": "temperature",
                    "semantic_type": "air_temperature",
                    "logical_type": "measurement",
                    "unit": "Celsius",
                    "description": "Air temperature",
                    "supporting_evidence": ["column name temp_C"],
                    "confidence": 0.9,
                    "uncertainty_reason": None,
                }
            ],
            "conflicts": [],
            "notes": [],
        }
        self.assertEqual(validate_annotation_result(result, payload), [])

    def test_normalize_annotation_result_fills_defaults(self) -> None:
        task = SemanticAnnotationTask(
            task_id="internal::demo",
            dataset_id="demo",
            file_format="csv",
            data_modality="tabular",
            deterministic_schema={"fields": [{"field_path": "temperature"}]},
        )
        payload = build_prompt_payload(task)
        raw = {
            "task_id": "internal::demo",
            "annotations": [
                {
                    "field_path": "temperature",
                    "logical_type": "measurement",
                }
            ],
            "conflicts": [],
            "notes": [],
        }
        normalized = normalize_annotation_result(raw, payload)
        annotation = normalized["annotations"][0]
        self.assertEqual(annotation["semantic_type"], "unknown")
        self.assertEqual(annotation["confidence"], 0.0)
        self.assertEqual(annotation["uncertainty_reason"], "model omitted semantic_type")

    def test_normalize_annotation_result_explains_explicit_unknown_semantic_type(self) -> None:
        task = SemanticAnnotationTask(
            task_id="internal::demo",
            dataset_id="demo",
            file_format="csv",
            data_modality="tabular",
            deterministic_schema={"fields": [{"field_path": "mass_g"}]},
        )
        payload = build_prompt_payload(task)
        raw = {
            "task_id": "internal::demo",
            "annotations": [
                {
                    "field_path": "mass_g",
                    "semantic_type": "unknown",
                    "logical_type": "measurement",
                    "unit": "g",
                    "supporting_evidence": ["F1"],
                    "confidence": 0.9,
                    "uncertainty_reason": None,
                }
            ],
            "conflicts": [],
            "notes": [],
        }
        normalized = normalize_annotation_result(raw, payload)

        self.assertEqual(
            normalized["annotations"][0]["uncertainty_reason"],
            "semantic type left unknown because provided evidence does not support a precise semantic claim",
        )

    def test_merge_annotation_result_preserves_explicit_unit_conflict(self) -> None:
        schema = {
            "fields": [
                {
                    "field_path": "/observations/temperature",
                    "logical_type": "measurement",
                    "semantic_type": "air_temperature",
                    "unit": "C",
                    "source_evidence": [
                        {
                            "evidence_type": "hdf5_attribute",
                        }
                    ],
                }
            ],
            "metadata": {},
        }
        result = {
            "task_id": "demo",
            "annotations": [
                {
                    "field_path": "/observations/temperature",
                    "semantic_type": "air_temperature",
                    "logical_type": "measurement",
                    "unit": "Kelvin",
                    "description": "Air temperature",
                    "supporting_evidence": ["note"],
                    "confidence": 0.8,
                    "uncertainty_reason": None,
                }
            ],
            "conflicts": [],
            "notes": [],
        }
        merged = merge_annotation_result(schema, result, {"model": "demo"})
        self.assertEqual(merged["fields"][0]["unit"], "C")
        self.assertEqual(
            merged["metadata"]["semantic_annotation"]["conflicts"][0]["conflict_type"],
            "unit_conflict_explicit_metadata",
        )

    def test_merge_annotation_result_rejects_invalid_logical_type(self) -> None:
        schema = {
            "fields": [
                {
                    "field_path": "zc",
                    "logical_type": "unknown",
                    "semantic_type": "postal_zone_code",
                    "unit": None,
                    "source_evidence": [],
                }
            ],
            "metadata": {},
        }
        result = {
            "task_id": "demo",
            "annotations": [
                {
                    "field_path": "zc",
                    "semantic_type": "postal_zone_code",
                    "logical_type": "string",
                    "unit": None,
                    "description": "postal zone code",
                    "supporting_evidence": ["readme"],
                    "confidence": 0.9,
                    "uncertainty_reason": None,
                }
            ],
            "conflicts": [],
            "notes": [],
        }
        merged = merge_annotation_result(schema, result, {"model": "demo"})
        self.assertEqual(merged["fields"][0]["logical_type"], "unknown")
        self.assertEqual(
            merged["metadata"]["semantic_annotation"]["conflicts"][0]["conflict_type"],
            "invalid_logical_type",
        )

    def test_merge_annotation_result_requires_supporting_evidence(self) -> None:
        schema = {
            "fields": [
                {
                    "field_path": "max_VIL",
                    "logical_type": "unknown",
                    "semantic_type": "unknown",
                    "unit": None,
                    "source_evidence": [],
                }
            ],
            "metadata": {},
        }
        result = {
            "task_id": "demo",
            "annotations": [
                {
                    "field_path": "max_VIL",
                    "semantic_type": "maximum_vertically_integrated_liquid",
                    "logical_type": "measurement",
                    "unit": "dBZ",
                    "description": None,
                    "supporting_evidence": [],
                    "confidence": 0.7,
                    "uncertainty_reason": None,
                }
            ],
            "conflicts": [],
            "notes": [],
        }
        merged = merge_annotation_result(schema, result, {"model": "demo"})
        field = merged["fields"][0]
        self.assertEqual(field["logical_type"], "unknown")
        self.assertEqual(field["semantic_type"], "unknown")
        self.assertEqual(field["unit"], None)
        self.assertEqual(field["semantic_annotation"]["accepted_for_merge"], False)

    def test_merge_annotation_result_rejects_semantic_logical_incompatibility(self) -> None:
        schema = {
            "fields": [
                {
                    "field_path": "zc",
                    "logical_type": "unknown",
                    "semantic_type": "postal_zone_code",
                    "unit": None,
                    "source_evidence": [],
                }
            ],
            "metadata": {},
        }
        result = {
            "task_id": "demo",
            "annotations": [
                {
                    "field_path": "zc",
                    "semantic_type": "postal_zone_code",
                    "logical_type": "label",
                    "unit": None,
                    "description": None,
                    "supporting_evidence": ["readme: zc is a postal zone code"],
                    "confidence": 0.8,
                    "uncertainty_reason": None,
                }
            ],
            "conflicts": [],
            "notes": [],
        }
        merged = merge_annotation_result(schema, result, {"model": "demo"})
        self.assertEqual(merged["fields"][0]["logical_type"], "unknown")
        self.assertEqual(
            merged["metadata"]["semantic_annotation"]["conflicts"][0]["conflict_type"],
            "semantic_logical_incompatibility",
        )

    def test_merge_annotation_result_allows_compatible_logical_refinement(self) -> None:
        schema = {
            "fields": [
                {
                    "field_path": "elevation_m",
                    "logical_type": "coordinate",
                    "semantic_type": "elevation",
                    "unit": "meter",
                    "source_evidence": [],
                }
            ],
            "metadata": {},
        }
        result = {
            "task_id": "demo",
            "annotations": [
                {
                    "field_path": "elevation_m",
                    "semantic_type": "elevation",
                    "logical_type": "measurement",
                    "unit": "meter",
                    "description": "Meters above sea level",
                    "supporting_evidence": ["readme: elevation_m is meters above sea level"],
                    "confidence": 0.9,
                    "uncertainty_reason": None,
                }
            ],
            "conflicts": [],
            "notes": [],
        }

        merged = merge_annotation_result(schema, result, {"model": "demo"})

        self.assertEqual(merged["fields"][0]["logical_type"], "measurement")
        self.assertEqual(merged["metadata"]["semantic_annotation"]["conflicts"], [])
        self.assertEqual(
            merged["metadata"]["semantic_annotation"]["logical_type_overrides"][0]["existing"],
            "coordinate",
        )


if __name__ == "__main__":
    unittest.main()
