from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class GroundingSnippet:
    source_type: str
    source_name: str
    detail: str
    text: str
    priority: int


@dataclass
class SemanticAnnotationTask:
    task_id: str
    dataset_id: str
    file_format: str
    data_modality: str
    deterministic_schema: Dict[str, Any]
    grounding_snippets: List[GroundingSnippet] = field(default_factory=list)
    instructions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticFieldAnnotation:
    field_path: str
    semantic_type: str
    logical_type: Optional[str] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    supporting_evidence: List[str] = field(default_factory=list)
    confidence: float = 0.0
    uncertainty_reason: Optional[str] = None


@dataclass
class SemanticAnnotationResult:
    task_id: str
    annotations: List[SemanticFieldAnnotation] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


SYSTEM_RULES = [
    "You are given a deterministic schema extracted from a dataset file.",
    "You may only make claims supported by the provided evidence.",
    "Do not invent fields, units, or shapes that are not grounded in the deterministic schema or supplied snippets.",
    "Prefer unknown over unsupported guessing.",
    "If explicit metadata conflicts with weaker name-based inference, preserve the explicit metadata and surface a conflict.",
]

ALLOWED_LOGICAL_TYPES = {
    "identifier",
    "time_axis",
    "measurement",
    "coordinate",
    "label",
    "attribute",
    "relationship",
    "unknown",
}


def normalize_supporting_evidence(items: List[Any]) -> List[str]:
    normalized = []
    for item in items:
        if isinstance(item, str):
            normalized.append(item)
        elif isinstance(item, dict):
            source = item.get("source")
            detail = item.get("detail")
            if source and detail:
                normalized.append(f"{source}: {detail}")
            elif detail:
                normalized.append(str(detail))
        elif item is not None:
            normalized.append(str(item))
    return normalized


def compatible_logical_types_from_semantic(semantic_type: Optional[str]) -> Set[str]:
    if semantic_type is None or semantic_type in {"", "unknown"}:
        return set()
    if semantic_type.endswith("_identifier") or semantic_type in {"postal_zone_code"}:
        return {"identifier"}
    if semantic_type in {"observation_time", "collection_date", "forecast_hour"}:
        return {"attribute", "time_axis"}
    if semantic_type in {"latitude", "longitude", "depth", "elevation"}:
        if semantic_type == "elevation":
            return {"coordinate", "measurement"}
        return {"coordinate"}
    if semantic_type in {
        "precipitation",
        "relative_humidity",
        "surface_pressure",
        "wind_speed",
        "air_temperature",
        "water_temperature",
        "power",
        "voltage",
        "acidity_ph",
        "dissolved_oxygen",
        "turbidity",
        "salinity",
    }:
        return {"measurement"}
    if semantic_type in {"quality_flag", "operational_status", "station_name", "free_text_note"}:
        return {"label"}
    return set()


def expected_logical_type_from_semantic(semantic_type: Optional[str]) -> Optional[str]:
    compatible = compatible_logical_types_from_semantic(semantic_type)
    if not compatible:
        return None
    return sorted(compatible)[0]


def build_prompt_payload(task: SemanticAnnotationTask) -> Dict[str, Any]:
    return {
        "system_rules": SYSTEM_RULES,
        "task": task.to_dict(),
        "expected_output_schema": {
            "task_id": "string",
            "annotations": [
                {
                    "field_path": "string",
                    "semantic_type": "string",
                    "logical_type": "string|null",
                    "unit": "string|null",
                    "description": "string|null",
                    "supporting_evidence": ["string"],
                    "confidence": "number",
                    "uncertainty_reason": "string|null",
                }
            ],
            "conflicts": [
                {
                    "field_path": "string",
                    "conflict_type": "string",
                    "detail": "string",
                }
            ],
            "notes": ["string"],
        },
    }


def write_prompt_payload(path: Path, task: SemanticAnnotationTask) -> None:
    path.write_text(json.dumps(build_prompt_payload(task), indent=2) + "\n", encoding="utf-8")


def validate_annotation_result(result: Dict[str, Any], task_payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    task = task_payload["task"]
    if result.get("task_id") != task["task_id"]:
        errors.append("task_id mismatch")

    valid_field_paths = {
        field["field_path"]
        for field in task["deterministic_schema"].get("fields", [])
    }
    for annotation in result.get("annotations", []):
        field_path = annotation.get("field_path")
        if field_path not in valid_field_paths:
            errors.append(f"unknown field_path: {field_path}")
        logical_type = annotation.get("logical_type")
        if logical_type is not None and logical_type not in ALLOWED_LOGICAL_TYPES:
            errors.append(f"invalid logical_type for {field_path}: {logical_type}")
        confidence = annotation.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
            errors.append(f"invalid confidence for {field_path}")
        if annotation.get("semantic_type") == "unknown" and not annotation.get("uncertainty_reason"):
            errors.append(f"unknown semantic_type without uncertainty_reason: {field_path}")
        if not isinstance(annotation.get("supporting_evidence", []), list):
            errors.append(f"supporting_evidence must be a list: {field_path}")
    return errors


def normalize_annotation_result(result: Dict[str, Any], task_payload: Dict[str, Any]) -> Dict[str, Any]:
    task = task_payload["task"]
    normalized = {
        "task_id": result.get("task_id", task["task_id"]),
        "annotations": [],
        "conflicts": result.get("conflicts", []),
        "notes": result.get("notes", []),
    }

    for annotation in result.get("annotations", []):
        semantic_type = annotation.get("semantic_type")
        uncertainty_reason = annotation.get("uncertainty_reason")
        if semantic_type in {None, ""}:
            semantic_type = "unknown"
            if not uncertainty_reason:
                uncertainty_reason = "model omitted semantic_type"
        elif semantic_type == "unknown" and not uncertainty_reason:
            uncertainty_reason = "semantic type left unknown because provided evidence does not support a precise semantic claim"
        normalized["annotations"].append(
            {
                "field_path": annotation.get("field_path"),
                "semantic_type": semantic_type,
                "logical_type": annotation.get("logical_type"),
                "unit": annotation.get("unit"),
                "description": annotation.get("description"),
                "supporting_evidence": normalize_supporting_evidence(annotation.get("supporting_evidence", [])),
                "confidence": float(annotation.get("confidence", 0.0)),
                "uncertainty_reason": uncertainty_reason,
            }
        )

    return normalized


def _has_explicit_unit(field: Dict[str, Any]) -> bool:
    for evidence in field.get("source_evidence", []):
        if evidence.get("evidence_type") == "hdf5_attribute":
            return True
    return False


def merge_annotation_result(
    deterministic_schema: Dict[str, Any],
    result: Dict[str, Any],
    model_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    merged = json.loads(json.dumps(deterministic_schema))
    annotations = {item["field_path"]: item for item in result.get("annotations", [])}
    merge_conflicts: List[Dict[str, Any]] = list(result.get("conflicts", []))
    logical_type_overrides: List[Dict[str, Any]] = []

    for field_item in merged.get("fields", []):
        annotation = annotations.get(field_item["field_path"])
        if annotation is None:
            continue
        supporting_evidence = annotation.get("supporting_evidence", [])
        annotation_supported = bool(supporting_evidence)
        effective_semantic_type = annotation.get("semantic_type")
        if effective_semantic_type in {None, "", "unknown"}:
            effective_semantic_type = field_item.get("semantic_type")
        compatible_logical = compatible_logical_types_from_semantic(effective_semantic_type)

        if not annotation_supported and (
            annotation.get("logical_type")
            or annotation.get("semantic_type") not in {None, "", "unknown"}
            or annotation.get("unit")
        ):
            merge_conflicts.append(
                {
                    "field_path": field_item["field_path"],
                    "conflict_type": "unsupported_annotation_no_evidence",
                    "detail": "annotation proposed changes without supporting_evidence",
                }
            )

        if annotation_supported and annotation.get("logical_type"):
            if annotation["logical_type"] not in ALLOWED_LOGICAL_TYPES:
                merge_conflicts.append(
                    {
                        "field_path": field_item["field_path"],
                        "conflict_type": "invalid_logical_type",
                        "proposed": annotation["logical_type"],
                    }
                )
            elif compatible_logical and annotation["logical_type"] not in compatible_logical:
                merge_conflicts.append(
                    {
                        "field_path": field_item["field_path"],
                        "conflict_type": "semantic_logical_incompatibility",
                        "semantic_type": effective_semantic_type,
                        "proposed": annotation["logical_type"],
                        "expected": sorted(compatible_logical),
                    }
                )
            elif field_item.get("logical_type") in {None, "", "unknown"}:
                field_item["logical_type"] = annotation["logical_type"]
            elif field_item["logical_type"] != annotation["logical_type"]:
                existing_is_compatible = not compatible_logical or field_item["logical_type"] in compatible_logical
                annotation_semantic = annotation.get("semantic_type")
                semantic_agrees = annotation_semantic in {None, "", "unknown", field_item.get("semantic_type")}
                if existing_is_compatible and semantic_agrees and float(annotation.get("confidence", 0.0)) >= 0.85:
                    logical_type_overrides.append(
                        {
                            "field_path": field_item["field_path"],
                            "existing": field_item["logical_type"],
                            "proposed": annotation["logical_type"],
                            "semantic_type": effective_semantic_type,
                            "reason": "evidence-backed compatible logical refinement",
                        }
                    )
                    field_item["logical_type"] = annotation["logical_type"]
                else:
                    merge_conflicts.append(
                        {
                            "field_path": field_item["field_path"],
                            "conflict_type": "logical_type_conflict",
                            "existing": field_item["logical_type"],
                            "proposed": annotation["logical_type"],
                        }
                    )

        if annotation_supported and annotation.get("semantic_type"):
            if field_item.get("semantic_type") in {None, "", "unknown"}:
                field_item["semantic_type"] = annotation["semantic_type"]
            elif field_item["semantic_type"] != annotation["semantic_type"]:
                merge_conflicts.append(
                    {
                        "field_path": field_item["field_path"],
                        "conflict_type": "semantic_type_conflict",
                        "existing": field_item["semantic_type"],
                        "proposed": annotation["semantic_type"],
                    }
                )

        if annotation_supported and annotation.get("unit"):
            if not field_item.get("unit"):
                field_item["unit"] = annotation["unit"]
            elif field_item["unit"] != annotation["unit"]:
                conflict_type = "unit_conflict_explicit_metadata" if _has_explicit_unit(field_item) else "unit_conflict"
                merge_conflicts.append(
                    {
                        "field_path": field_item["field_path"],
                        "conflict_type": conflict_type,
                        "existing": field_item["unit"],
                        "proposed": annotation["unit"],
                    }
                )

        if annotation_supported and annotation.get("description") and not field_item.get("description"):
            field_item["description"] = annotation["description"]

        field_item["semantic_annotation"] = {
            "confidence": annotation.get("confidence"),
            "uncertainty_reason": annotation.get("uncertainty_reason"),
            "supporting_evidence": supporting_evidence,
            "accepted_for_merge": annotation_supported,
        }

    metadata = merged.setdefault("metadata", {})
    metadata["semantic_annotation"] = {
        "task_id": result.get("task_id"),
        "model_info": model_info or {},
        "conflicts": merge_conflicts,
        "logical_type_overrides": logical_type_overrides,
        "notes": result.get("notes", []),
    }
    return merged
