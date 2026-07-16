from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .architecture_variants import (
    ALLOWED_LOGICAL_TYPES,
    EVALUATED_PROPERTIES,
    load_json,
)


PROPERTY_VALUE_KEYS = {
    "physical_type": "correct_physical_type",
    "logical_type": "correct_logical_type",
    "semantic_type": "correct_semantic_type",
    "unit": "unit",
}
HASH_LENGTH = 64
PACKET_FORBIDDEN_PREDICTION_KEYS = {
    "logical_type",
    "semantic_type",
    "unit",
    "confidence",
    "uncertainty_reason",
    "semantic_logical_hint",
    "description",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == HASH_LENGTH and all(char in "0123456789abcdef" for char in text)


def _issue(
    errors: List[Dict[str, Any]],
    code: str,
    detail: str,
    *,
    field_path: Optional[str] = None,
    property_name: Optional[str] = None,
) -> None:
    item: Dict[str, Any] = {"code": code, "detail": detail}
    if field_path is not None:
        item["field_path"] = field_path
    if property_name is not None:
        item["property"] = property_name
    errors.append(item)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _packet_fields(packet: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for field in packet.get("field_inventory", []):
        if not isinstance(field, dict):
            continue
        field_path = str(field.get("field_path") or "")
        if field_path:
            result[field_path] = field
    return result


def _snippet_field_paths(
    snippet: Dict[str, Any], fields: Iterable[Dict[str, Any]]
) -> List[str]:
    haystack = " ".join(
        str(snippet.get(key) or "") for key in ("text", "detail", "source_name")
    ).lower()
    result: List[str] = []
    for field in fields:
        field_path = str(field.get("field_path") or "")
        field_name = str(field.get("field_name") or "")
        if any(
            token and token.lower() in haystack for token in (field_path, field_name)
        ):
            result.append(field_path)
    return sorted(set(result))


def build_packet_source_bundle(
    packet_path: Path,
    vocabulary_path: Path,
) -> Dict[str, Any]:
    packet = load_json(packet_path)
    packet_hash = sha256_file(packet_path)
    vocabulary_hash = sha256_file(vocabulary_path)
    fields = list(_packet_fields(packet).values())
    evidence_catalog: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for field in fields:
        field_path = str(field["field_path"])
        for item in field.get("source_evidence", []):
            evidence_id = str(item.get("evidence_id") or "")
            if not evidence_id or evidence_id in seen:
                raise ValueError(
                    f"packet evidence id is missing or duplicate: {evidence_id!r}"
                )
            seen.add(evidence_id)
            evidence_catalog.append(
                {
                    "catalog_evidence_id": evidence_id,
                    "source_id": "ANNOTATION_PACKET",
                    "source_type": str(item.get("evidence_type") or "structural"),
                    "source_sha256": packet_hash,
                    "selector": f"field_inventory:{field_path}:{evidence_id}",
                    "applicable_field_paths": [field_path],
                    "strength": str(item.get("tier") or "structural"),
                }
            )
    for item in packet.get("approved_evidence", []):
        evidence_id = str(item.get("evidence_id") or "")
        if not evidence_id or evidence_id in seen:
            raise ValueError(
                f"packet evidence id is missing or duplicate: {evidence_id!r}"
            )
        seen.add(evidence_id)
        applicable = item.get("applicable_field_paths")
        if not isinstance(applicable, list):
            applicable = _snippet_field_paths(item, fields)
        evidence_catalog.append(
            {
                "catalog_evidence_id": evidence_id,
                "source_id": "ANNOTATION_PACKET",
                "source_type": str(item.get("source_type") or "approved_documentation"),
                "source_sha256": packet_hash,
                "selector": f"approved_evidence:{evidence_id}",
                "applicable_field_paths": sorted(
                    set(str(value) for value in applicable)
                ),
                "strength": "documentation",
            }
        )
    return {
        "schema_version": "semantic-source-bundle/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "dataset_id": packet["dataset_id"],
        "annotation_packet_file": packet_path.name,
        "annotation_packet_sha256": packet_hash,
        "vocabulary_file": vocabulary_path.name,
        "vocabulary_sha256": vocabulary_hash,
        "sources": [
            {
                "source_id": "ANNOTATION_PACKET",
                "source_type": "frozen_neutral_annotation_packet",
                "source_file": packet_path.name,
                "source_sha256": packet_hash,
            }
        ],
        "evidence_catalog": evidence_catalog,
    }


def build_annotation_workflow_manifest(
    calibration_manifest_path: Path,
    *,
    vocabulary_path: Path,
    source_bundle_dir: Path,
    handbook_path: Path,
    output_path: Path,
) -> Dict[str, Any]:
    calibration = load_json(calibration_manifest_path)
    vocabulary = load_json(vocabulary_path)
    vocabulary_report = validate_vocabulary(vocabulary)
    if vocabulary_report["status"] != "ready":
        raise ValueError(f"vocabulary is invalid: {vocabulary_report['errors']}")
    cases: List[Dict[str, Any]] = []
    for item in calibration.get("cases", []):
        case_id = str(item["case_id"])
        packet_path = (
            calibration_manifest_path.parent / str(item["packet_file"])
        ).resolve()
        if sha256_file(packet_path) != item.get("packet_sha256"):
            raise ValueError(f"calibration packet hash mismatch for {case_id}")
        packet = load_json(packet_path)
        packet_report = validate_annotation_packet(packet)
        if packet_report["status"] != "ready":
            raise ValueError(
                f"neutral packet is invalid for {case_id}: {packet_report['errors']}"
            )
        bundle_path = source_bundle_dir / f"{case_id}.source-bundle.json"
        bundle = load_json(bundle_path)
        bundle_report = validate_source_bundle(
            bundle,
            packet=packet,
            packet_sha256=sha256_file(packet_path),
            vocabulary_sha256=sha256_file(vocabulary_path),
        )
        if bundle_report["status"] != "ready":
            raise ValueError(
                f"source bundle is invalid for {case_id}: {bundle_report['errors']}"
            )
        bundle_file_report = validate_source_bundle_files(
            bundle,
            bundle_path=bundle_path,
            packet_path=packet_path,
        )
        if bundle_file_report["status"] != "ready":
            raise ValueError(
                f"source files are invalid for {case_id}: {bundle_file_report['errors']}"
            )
        cases.append(
            {
                "case_id": case_id,
                "dataset_id": packet["dataset_id"],
                "packet_file": f"packets/{packet_path.name}",
                "packet_sha256": sha256_file(packet_path),
                "source_bundle_file": f"source_bundles/{bundle_path.name}",
                "source_bundle_sha256": sha256_file(bundle_path),
                "field_count": len(packet["field_inventory"]),
                "required_independent_submission_count": 2,
            }
        )
    if not cases:
        raise ValueError("calibration workflow contains no cases")
    output_parent = output_path.resolve().parent

    def relative_file(path: Path) -> str:
        resolved = path.resolve()
        try:
            return Path(os.path.relpath(resolved, output_parent)).as_posix()
        except ValueError:
            return resolved.as_posix()

    return {
        "schema_version": "semantic-annotation-workflow-manifest/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "benchmark_role": "annotator_calibration",
        "research_evidence_status": "non_blind_not_for_effect_estimation",
        "workflow_status": "ready_for_independent_annotation",
        "calibration_manifest_file": relative_file(calibration_manifest_path),
        "calibration_manifest_sha256": sha256_file(calibration_manifest_path),
        "vocabulary_file": relative_file(vocabulary_path),
        "vocabulary_sha256": sha256_file(vocabulary_path),
        "handbook_file": relative_file(handbook_path),
        "handbook_sha256": sha256_file(handbook_path),
        "workflow_implementation_file": relative_file(Path(__file__)),
        "workflow_implementation_sha256": sha256_file(Path(__file__)),
        "independence_policy": {
            "annotator_count": 2,
            "developer_participation": False,
            "model_outputs_visible": False,
            "other_annotation_visible_before_freeze": False,
            "comparison_only_after_both_validate": True,
        },
        "case_count": len(cases),
        "cases": cases,
    }


def validate_vocabulary(vocabulary: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    if vocabulary.get("schema_version") != "semantic-annotation-vocabulary/v1":
        _issue(
            errors, "vocabulary_schema", "expected semantic-annotation-vocabulary/v1"
        )
    if vocabulary.get("protocol_version") != "semantic-architecture-protocol/v1":
        _issue(errors, "vocabulary_protocol", "protocol version mismatch")
    if vocabulary.get("status") != "frozen":
        _issue(errors, "vocabulary_not_frozen", "vocabulary status must be frozen")
    if not str(vocabulary.get("vocabulary_version") or ""):
        _issue(errors, "vocabulary_version_missing", "vocabulary_version is required")
    for key in ("physical_types", "logical_types", "semantic_types", "units"):
        values = vocabulary.get(key)
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(item, str) or not item for item in values)
            or len(values) != len(set(values))
        ):
            _issue(
                errors,
                "vocabulary_values_invalid",
                f"{key} must be a non-empty unique string list",
            )
    logical_types = vocabulary.get("logical_types")
    if isinstance(logical_types, list) and set(logical_types) != set(
        ALLOWED_LOGICAL_TYPES
    ):
        _issue(
            errors,
            "logical_vocabulary_mismatch",
            "logical_types must exactly match the frozen architecture vocabulary",
        )
    if vocabulary.get("unknown_representation", "missing") is not None:
        _issue(
            errors,
            "unknown_representation_invalid",
            "unknown_representation must be JSON null",
        )
    canonical_units = set(vocabulary.get("units", []))
    aliases = vocabulary.get("unit_aliases")
    if not isinstance(aliases, dict):
        _issue(errors, "unit_aliases_invalid", "unit_aliases must be an object")
    else:
        for alias, canonical in aliases.items():
            if (
                not isinstance(alias, str)
                or not alias
                or not isinstance(canonical, str)
                or canonical not in canonical_units
                or alias in canonical_units
            ):
                _issue(
                    errors,
                    "unit_alias_invalid",
                    f"alias {alias!r} must map to a distinct canonical unit",
                )
    patterns = vocabulary.get("unit_patterns")
    if not isinstance(patterns, list):
        _issue(errors, "unit_patterns_invalid", "unit_patterns must be a list")
    else:
        for item in patterns:
            if not isinstance(item, dict) or not str(item.get("meaning") or ""):
                _issue(
                    errors,
                    "unit_pattern_invalid",
                    "unit pattern requires a meaning",
                )
                continue
            try:
                re.compile(str(item.get("pattern") or ""))
            except re.error as exc:
                _issue(errors, "unit_pattern_invalid", str(exc))
    return {"status": "ready" if not errors else "blocked", "errors": errors}


def validate_annotation_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    if packet.get("schema_version") != "semantic-annotation-packet/v1":
        _issue(errors, "packet_schema", "expected semantic-annotation-packet/v1")
    if not str(packet.get("dataset_id") or ""):
        _issue(errors, "packet_dataset_id", "dataset_id is required")
    fields = packet.get("field_inventory")
    seen: set[str] = set()
    if not isinstance(fields, list) or not fields:
        _issue(errors, "packet_fields_empty", "field_inventory must be non-empty")
        fields = []
    for field in fields:
        if not isinstance(field, dict):
            _issue(errors, "packet_field_shape", "field entry must be an object")
            continue
        field_path = str(field.get("field_path") or "")
        if not field_path or field_path in seen:
            _issue(errors, "packet_field_identity", "field paths must be unique")
        seen.add(field_path)
        leaked = sorted(PACKET_FORBIDDEN_PREDICTION_KEYS & set(field))
        if leaked:
            _issue(
                errors,
                "packet_prediction_leakage",
                f"neutral field {field_path} contains predictions {leaked}",
                field_path=field_path,
            )
        source_evidence = field.get("source_evidence", [])
        if not isinstance(source_evidence, list):
            _issue(
                errors,
                "packet_evidence_shape",
                "source_evidence must be a list",
                field_path=field_path,
            )
            continue
        for item in source_evidence:
            if not isinstance(item, dict):
                _issue(errors, "packet_evidence_item", "evidence must be an object")
                continue
            if item.get("evidence_type") == "column_name_unit_hint" or any(
                key in item for key in PACKET_FORBIDDEN_PREDICTION_KEYS
            ):
                _issue(
                    errors,
                    "packet_derived_evidence_leakage",
                    "derived semantic evidence/confidence is forbidden",
                    field_path=field_path,
                )
            source_label = str(item.get("source_label") or "").replace("\\", "/")
            if source_label.startswith("/") or ":/" in source_label:
                _issue(
                    errors,
                    "packet_absolute_path_leakage",
                    "source_label must not expose an absolute source path",
                    field_path=field_path,
                )
    for item in packet.get("approved_evidence", []):
        if isinstance(item, dict) and any(
            key in item for key in PACKET_FORBIDDEN_PREDICTION_KEYS
        ):
            _issue(
                errors,
                "packet_approved_evidence_leakage",
                "approved evidence metadata contains prediction fields",
            )
    return {"status": "ready" if not errors else "blocked", "errors": errors}


def validate_source_bundle(
    bundle: Dict[str, Any],
    *,
    packet: Dict[str, Any],
    packet_sha256: str,
    vocabulary_sha256: str,
) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    if bundle.get("schema_version") != "semantic-source-bundle/v1":
        _issue(errors, "source_bundle_schema", "expected semantic-source-bundle/v1")
    if bundle.get("protocol_version") != "semantic-architecture-protocol/v1":
        _issue(errors, "source_bundle_protocol", "protocol version mismatch")
    if bundle.get("dataset_id") != packet.get("dataset_id"):
        _issue(errors, "source_bundle_dataset", "bundle and packet dataset_id differ")
    if bundle.get("annotation_packet_sha256") != packet_sha256:
        _issue(errors, "source_bundle_packet_hash", "annotation packet hash mismatch")
    if bundle.get("vocabulary_sha256") != vocabulary_sha256:
        _issue(errors, "source_bundle_vocabulary_hash", "vocabulary hash mismatch")
    sources = bundle.get("sources")
    source_map: Dict[str, Dict[str, Any]] = {}
    if not isinstance(sources, list) or not sources:
        _issue(
            errors, "source_bundle_sources", "at least one approved source is required"
        )
        sources = []
    for source in sources:
        if not isinstance(source, dict):
            _issue(
                errors, "source_bundle_source_shape", "source entry must be an object"
            )
            continue
        source_id = str(source.get("source_id") or "")
        if not source_id or source_id in source_map:
            _issue(
                errors,
                "source_bundle_source_id",
                "source ids must be unique and non-empty",
            )
            continue
        source_map[source_id] = source
        if not _is_sha256(source.get("source_sha256")):
            _issue(
                errors,
                "source_bundle_source_hash",
                f"source {source_id} hash is invalid",
            )
        if not str(source.get("source_type") or ""):
            _issue(
                errors,
                "source_bundle_source_type",
                f"source {source_id} type is required",
            )

    packet_paths = set(_packet_fields(packet))
    catalog = bundle.get("evidence_catalog")
    catalog_ids: set[str] = set()
    if not isinstance(catalog, list) or not catalog:
        _issue(errors, "source_bundle_catalog", "evidence_catalog must be non-empty")
        catalog = []
    for item in catalog:
        if not isinstance(item, dict):
            _issue(
                errors, "source_bundle_evidence_shape", "catalog item must be an object"
            )
            continue
        evidence_id = str(item.get("catalog_evidence_id") or "")
        if not evidence_id or evidence_id in catalog_ids:
            _issue(
                errors,
                "source_bundle_evidence_id",
                "catalog evidence ids must be unique",
            )
        catalog_ids.add(evidence_id)
        source_id = str(item.get("source_id") or "")
        source = source_map.get(source_id)
        if source is None:
            _issue(
                errors,
                "source_bundle_evidence_source",
                f"unknown source_id {source_id}",
            )
        elif item.get("source_sha256") != source.get("source_sha256"):
            _issue(
                errors,
                "source_bundle_evidence_hash",
                f"evidence {evidence_id} source hash mismatch",
            )
        for key in ("source_type", "selector", "strength"):
            if not str(item.get(key) or ""):
                _issue(
                    errors,
                    "source_bundle_evidence_incomplete",
                    f"evidence {evidence_id} requires {key}",
                )
        applicable = item.get("applicable_field_paths")
        if (
            not isinstance(applicable, list)
            or not applicable
            or any(
                not isinstance(value, str) or value not in packet_paths
                for value in applicable
            )
        ):
            _issue(
                errors,
                "source_bundle_evidence_relevance",
                f"evidence {evidence_id} must declare existing applicable fields",
            )
    return {"status": "ready" if not errors else "blocked", "errors": errors}


def validate_source_bundle_files(
    bundle: Dict[str, Any],
    *,
    bundle_path: Path,
    packet_path: Path,
) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    for source in bundle.get("sources", []):
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("source_id") or "")
        raw_file = source.get("source_file")
        if not str(raw_file or ""):
            _issue(
                errors,
                "approved_source_file_missing",
                f"source {source_id} must declare source_file",
            )
            continue
        if source_id == "ANNOTATION_PACKET":
            source_path = packet_path
        else:
            source_path = Path(str(raw_file))
            if not source_path.is_absolute():
                source_path = (bundle_path.parent / source_path).resolve()
        if not source_path.is_file():
            _issue(
                errors,
                "approved_source_unavailable",
                f"source {source_id} does not exist: {source_path}",
            )
            continue
        actual_hash = sha256_file(source_path)
        if actual_hash != source.get("source_sha256"):
            _issue(
                errors,
                "approved_source_hash_mismatch",
                f"source {source_id} expected {source.get('source_sha256')} but found {actual_hash}",
            )
    return {"status": "ready" if not errors else "blocked", "errors": errors}


def _artifact_field_map(
    artifact: Dict[str, Any], errors: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    fields = artifact.get("fields")
    result: Dict[str, Dict[str, Any]] = {}
    if not isinstance(fields, list) or not fields:
        _issue(errors, "annotation_fields_empty", "fields must be a non-empty list")
        return result
    for field in fields:
        if not isinstance(field, dict):
            _issue(errors, "annotation_field_shape", "field entry must be an object")
            continue
        field_path = str(field.get("field_path") or "")
        if not field_path or field_path in result:
            _issue(
                errors,
                "annotation_field_identity",
                "field paths must be unique and non-empty",
                field_path=field_path or None,
            )
            continue
        result[field_path] = field
    return result


def _slot_value(field: Dict[str, Any], property_name: str) -> Any:
    return field.get(PROPERTY_VALUE_KEYS[property_name])


def _slot_state(field: Dict[str, Any], property_name: str) -> Dict[str, Any]:
    applicability = field["applicability"][property_name]
    value = _slot_value(field, property_name)
    if not applicability:
        state = "not_applicable"
    elif value is None:
        state = "applicable_unknown"
    else:
        state = "applicable_value"
    return {"applicability": applicability, "value": value, "state": state}


def _validate_top_level_annotation(
    artifact: Dict[str, Any],
    *,
    expected_stage: str,
    packet: Dict[str, Any],
    packet_sha256: str,
    source_bundle_sha256: str,
    vocabulary_sha256: str,
    errors: List[Dict[str, Any]],
) -> None:
    if artifact.get("schema_version") != "blind-semantic-gold/v1":
        _issue(errors, "annotation_schema", "expected blind-semantic-gold/v1")
    if artifact.get("protocol_version") != "semantic-architecture-protocol/v1":
        _issue(errors, "annotation_protocol", "protocol version mismatch")
    if artifact.get("annotation_stage") != expected_stage:
        _issue(errors, "annotation_stage", f"annotation_stage must be {expected_stage}")
    if artifact.get("dataset_id") != packet.get("dataset_id"):
        _issue(errors, "annotation_dataset", "artifact and packet dataset_id differ")
    for key in ("annotator_id", "submission_id"):
        if not str(artifact.get(key) or ""):
            _issue(errors, "annotation_identity", f"{key} is required")
    if artifact.get("model_outputs_visible") is not False:
        _issue(
            errors, "annotation_model_visibility", "model_outputs_visible must be false"
        )
    if artifact.get("developer_participation") is not False:
        _issue(
            errors,
            "annotation_developer_boundary",
            "developer_participation must be false",
        )
    expected_hashes = {
        "source_bundle_sha256": source_bundle_sha256,
        "annotation_packet_sha256": packet_sha256,
        "vocabulary_sha256": vocabulary_sha256,
    }
    for key, expected in expected_hashes.items():
        if artifact.get(key) != expected:
            _issue(
                errors,
                "annotation_frozen_hash",
                f"{key} does not match the frozen input",
            )


def _vocabulary_sets(vocabulary: Dict[str, Any]) -> Dict[str, set[str]]:
    return {
        "physical_type": set(vocabulary.get("physical_types", [])),
        "logical_type": set(vocabulary.get("logical_types", [])),
        "semantic_type": set(vocabulary.get("semantic_types", [])),
        "unit": set(vocabulary.get("units", [])),
    }


def _unit_is_canonical(value: str, vocabulary: Dict[str, Any]) -> bool:
    if value in set(vocabulary.get("units", [])):
        return True
    for item in vocabulary.get("unit_patterns", []):
        if not isinstance(item, dict):
            continue
        try:
            if re.fullmatch(str(item.get("pattern") or ""), value):
                return True
        except re.error:
            continue
    return False


def _catalog_map(source_bundle: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(item["catalog_evidence_id"]): item
        for item in source_bundle.get("evidence_catalog", [])
        if isinstance(item, dict) and item.get("catalog_evidence_id")
    }


def _validate_annotation_fields(
    artifact: Dict[str, Any],
    *,
    packet: Dict[str, Any],
    source_bundle: Dict[str, Any],
    vocabulary: Dict[str, Any],
    errors: List[Dict[str, Any]],
) -> None:
    packet_fields = _packet_fields(packet)
    artifact_fields = _artifact_field_map(artifact, errors)
    missing = sorted(set(packet_fields) - set(artifact_fields))
    unexpected = sorted(set(artifact_fields) - set(packet_fields))
    if missing or unexpected:
        _issue(
            errors,
            "annotation_field_coverage",
            f"missing={missing}; unexpected={unexpected}",
        )
    vocabularies = _vocabulary_sets(vocabulary)
    catalog = _catalog_map(source_bundle)
    evidence_ids: set[str] = set()
    for field_path in sorted(set(packet_fields) & set(artifact_fields)):
        packet_field = packet_fields[field_path]
        field = artifact_fields[field_path]
        if field.get("field_name") != packet_field.get("field_name"):
            _issue(
                errors,
                "annotation_field_name",
                "field_name differs from neutral packet",
                field_path=field_path,
            )
        applicability = field.get("applicability")
        if not isinstance(applicability, dict) or set(applicability) != set(
            EVALUATED_PROPERTIES
        ):
            _issue(
                errors,
                "annotation_applicability_shape",
                "applicability must contain exactly all evaluated properties",
                field_path=field_path,
            )
            continue
        if any(not isinstance(value, bool) for value in applicability.values()):
            _issue(
                errors,
                "annotation_applicability_value",
                "applicability values must be boolean",
                field_path=field_path,
            )
            continue
        rationales = field.get("rationales")
        if not isinstance(rationales, dict) or set(rationales) != set(
            EVALUATED_PROPERTIES
        ):
            _issue(
                errors,
                "annotation_rationales_shape",
                "rationales must contain exactly all evaluated properties",
                field_path=field_path,
            )
            rationales = {}
        evidence = field.get("gold_evidence")
        if not isinstance(evidence, list):
            _issue(
                errors,
                "annotation_evidence_shape",
                "gold_evidence must be a list",
                field_path=field_path,
            )
            evidence = []
        valid_evidence_properties: set[str] = set()
        for item in evidence:
            if not isinstance(item, dict):
                _issue(
                    errors,
                    "annotation_evidence_item",
                    "evidence entry must be an object",
                    field_path=field_path,
                )
                continue
            evidence_id = str(item.get("evidence_id") or "")
            if not evidence_id or evidence_id in evidence_ids:
                _issue(
                    errors,
                    "annotation_evidence_id",
                    "annotation evidence ids must be globally unique and non-empty",
                    field_path=field_path,
                )
            evidence_ids.add(evidence_id)
            property_name = str(item.get("property") or "")
            if property_name not in EVALUATED_PROPERTIES:
                _issue(
                    errors,
                    "annotation_evidence_property",
                    "evidence property is outside the evaluated contract",
                    field_path=field_path,
                )
                continue
            if item.get("field_path") != field_path:
                _issue(
                    errors,
                    "annotation_evidence_field",
                    "evidence field_path differs from annotated field",
                    field_path=field_path,
                    property_name=property_name,
                )
                continue
            catalog_id = str(item.get("catalog_evidence_id") or "")
            catalog_item = catalog.get(catalog_id)
            if catalog_item is None:
                _issue(
                    errors,
                    "annotation_evidence_identity",
                    f"catalog evidence {catalog_id!r} does not exist",
                    field_path=field_path,
                    property_name=property_name,
                )
                continue
            if field_path not in catalog_item.get("applicable_field_paths", []):
                _issue(
                    errors,
                    "annotation_evidence_relevance",
                    "catalog evidence is not approved for this field",
                    field_path=field_path,
                    property_name=property_name,
                )
                continue
            identity_keys = ("source_type", "source_sha256", "selector", "strength")
            if any(item.get(key) != catalog_item.get(key) for key in identity_keys):
                _issue(
                    errors,
                    "annotation_evidence_provenance",
                    "evidence provenance differs from frozen catalog",
                    field_path=field_path,
                    property_name=property_name,
                )
                continue
            if not str(item.get("support") or "").strip():
                _issue(
                    errors,
                    "annotation_evidence_support",
                    "evidence support paraphrase is required",
                    field_path=field_path,
                    property_name=property_name,
                )
                continue
            valid_evidence_properties.add(property_name)

        for property_name in EVALUATED_PROPERTIES:
            value = _slot_value(field, property_name)
            applicable = applicability[property_name]
            if isinstance(value, str) and value.lower() == "unknown":
                _issue(
                    errors,
                    "annotation_unknown_string",
                    "unknown must be represented as JSON null",
                    field_path=field_path,
                    property_name=property_name,
                )
            known = value is not None and value != ""
            if not applicable and known:
                _issue(
                    errors,
                    "annotation_na_with_value",
                    "not-applicable property cannot contain a value",
                    field_path=field_path,
                    property_name=property_name,
                )
            if known:
                if property_name == "unit" and isinstance(value, str):
                    alias_target = vocabulary.get("unit_aliases", {}).get(value)
                    if alias_target is not None:
                        _issue(
                            errors,
                            "annotation_unit_alias",
                            f"unit alias {value!r} must be normalized to {alias_target!r}",
                            field_path=field_path,
                            property_name=property_name,
                        )
                    value_is_valid = _unit_is_canonical(value, vocabulary)
                else:
                    value_is_valid = (
                        isinstance(value, str) and value in vocabularies[property_name]
                    )
                if not value_is_valid:
                    _issue(
                        errors,
                        "annotation_out_of_vocabulary",
                        f"value {value!r} is outside frozen {property_name} vocabulary",
                        field_path=field_path,
                        property_name=property_name,
                    )
                if property_name not in valid_evidence_properties:
                    _issue(
                        errors,
                        "annotation_known_without_evidence",
                        "applicable known value requires valid property evidence",
                        field_path=field_path,
                        property_name=property_name,
                    )
            else:
                rationale = rationales.get(property_name)
                if not isinstance(rationale, str) or not rationale.strip():
                    _issue(
                        errors,
                        "annotation_rationale_missing",
                        "applicable unknown and N/A decisions require a property rationale",
                        field_path=field_path,
                        property_name=property_name,
                    )
                if property_name in valid_evidence_properties:
                    _issue(
                        errors,
                        "annotation_evidence_without_value",
                        "gold_evidence is reserved for applicable known values",
                        field_path=field_path,
                        property_name=property_name,
                    )


def validate_annotation_artifact(
    artifact_path: Path,
    *,
    packet_path: Path,
    source_bundle_path: Path,
    vocabulary_path: Path,
    expected_stage: str = "independent",
) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    try:
        artifact = load_json(artifact_path)
        packet = load_json(packet_path)
        source_bundle = load_json(source_bundle_path)
        vocabulary = load_json(vocabulary_path)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [{"code": "annotation_input_unreadable", "detail": str(exc)}],
        }
    packet_hash = sha256_file(packet_path)
    bundle_hash = sha256_file(source_bundle_path)
    vocabulary_hash = sha256_file(vocabulary_path)
    vocabulary_report = validate_vocabulary(vocabulary)
    errors.extend(vocabulary_report["errors"])
    packet_report = validate_annotation_packet(packet)
    errors.extend(packet_report["errors"])
    bundle_report = validate_source_bundle(
        source_bundle,
        packet=packet,
        packet_sha256=packet_hash,
        vocabulary_sha256=vocabulary_hash,
    )
    errors.extend(bundle_report["errors"])
    bundle_file_report = validate_source_bundle_files(
        source_bundle,
        bundle_path=source_bundle_path,
        packet_path=packet_path,
    )
    errors.extend(bundle_file_report["errors"])
    _validate_top_level_annotation(
        artifact,
        expected_stage=expected_stage,
        packet=packet,
        packet_sha256=packet_hash,
        source_bundle_sha256=bundle_hash,
        vocabulary_sha256=vocabulary_hash,
        errors=errors,
    )
    _validate_annotation_fields(
        artifact,
        packet=packet,
        source_bundle=source_bundle,
        vocabulary=vocabulary,
        errors=errors,
    )
    if expected_stage == "independent" and artifact.get("adjudication") not in (
        None,
        {},
    ):
        _issue(
            errors,
            "independent_adjudication_forbidden",
            "independent submissions cannot contain adjudication data",
        )
    return {
        "status": "ready" if not errors else "blocked",
        "errors": errors,
        "summary": {
            "dataset_id": artifact.get("dataset_id"),
            "annotator_id": artifact.get("annotator_id"),
            "submission_id": artifact.get("submission_id"),
            "artifact_sha256": sha256_file(artifact_path),
            "field_count": len(artifact.get("fields", []))
            if isinstance(artifact.get("fields"), list)
            else 0,
        },
    }


def _artifact_slots(artifact: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    slots: Dict[str, Dict[str, Any]] = {}
    for field in artifact["fields"]:
        field_path = str(field["field_path"])
        evidence_by_property = {
            property_name: sorted(
                str(item["catalog_evidence_id"])
                for item in field.get("gold_evidence", [])
                if item.get("property") == property_name
            )
            for property_name in EVALUATED_PROPERTIES
        }
        for property_name in EVALUATED_PROPERTIES:
            slot_id = f"{field_path}::{property_name}"
            slots[slot_id] = {
                "slot_id": slot_id,
                "field_path": field_path,
                "property": property_name,
                **_slot_state(field, property_name),
                "catalog_evidence_ids": evidence_by_property[property_name],
                "rationale": field["rationales"].get(property_name),
            }
    return slots


def compare_independent_artifacts(
    artifact_a_path: Path,
    artifact_b_path: Path,
    *,
    packet_path: Path,
    source_bundle_path: Path,
    vocabulary_path: Path,
) -> Dict[str, Any]:
    report_a = validate_annotation_artifact(
        artifact_a_path,
        packet_path=packet_path,
        source_bundle_path=source_bundle_path,
        vocabulary_path=vocabulary_path,
        expected_stage="independent",
    )
    report_b = validate_annotation_artifact(
        artifact_b_path,
        packet_path=packet_path,
        source_bundle_path=source_bundle_path,
        vocabulary_path=vocabulary_path,
        expected_stage="independent",
    )
    if report_a["status"] != "ready" or report_b["status"] != "ready":
        raise ValueError(
            "both independent artifacts must validate before disagreement reveal"
        )
    artifact_a = load_json(artifact_a_path)
    artifact_b = load_json(artifact_b_path)
    if artifact_a["annotator_id"] == artifact_b["annotator_id"]:
        raise ValueError("independent artifacts require two distinct annotator ids")
    if artifact_a["submission_id"] == artifact_b["submission_id"]:
        raise ValueError("independent artifacts require distinct submission ids")
    slots_a = _artifact_slots(artifact_a)
    slots_b = _artifact_slots(artifact_b)
    if set(slots_a) != set(slots_b):
        raise ValueError("independent artifacts cover different slots")
    disagreements: List[Dict[str, Any]] = []
    agreement_by_property = {
        property_name: {"agreed": 0, "total": 0}
        for property_name in EVALUATED_PROPERTIES
    }
    evidence_agreement_count = 0
    for slot_id in sorted(slots_a):
        a = slots_a[slot_id]
        b = slots_b[slot_id]
        property_name = a["property"]
        agreement_by_property[property_name]["total"] += 1
        label_agreement = (
            a["applicability"] == b["applicability"] and a["value"] == b["value"]
        )
        evidence_agreement = a["catalog_evidence_ids"] == b["catalog_evidence_ids"]
        if evidence_agreement:
            evidence_agreement_count += 1
        if label_agreement:
            agreement_by_property[property_name]["agreed"] += 1
            continue
        if a["applicability"] != b["applicability"] and a["value"] != b["value"]:
            disagreement_type = "applicability_and_value"
        elif a["applicability"] != b["applicability"]:
            disagreement_type = "applicability"
        else:
            disagreement_type = "value"
        disagreements.append(
            {
                "slot_id": slot_id,
                "field_path": a["field_path"],
                "property": property_name,
                "disagreement_type": disagreement_type,
                "annotator_a": a,
                "annotator_b": b,
                "resolution": {
                    "status": "pending_human_adjudication",
                    "rationale": None,
                },
            }
        )
    slot_count = len(slots_a)
    agreed_count = slot_count - len(disagreements)
    for values in agreement_by_property.values():
        values["exact_agreement_rate"] = (
            values["agreed"] / values["total"] if values["total"] else None
        )
    return {
        "schema_version": "semantic-disagreement-report/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "dataset_id": artifact_a["dataset_id"],
        "source_bundle_sha256": sha256_file(source_bundle_path),
        "annotation_packet_sha256": sha256_file(packet_path),
        "vocabulary_sha256": sha256_file(vocabulary_path),
        "independent_artifacts": [
            {
                "annotator_id": artifact_a["annotator_id"],
                "submission_id": artifact_a["submission_id"],
                "artifact_sha256": sha256_file(artifact_a_path),
            },
            {
                "annotator_id": artifact_b["annotator_id"],
                "submission_id": artifact_b["submission_id"],
                "artifact_sha256": sha256_file(artifact_b_path),
            },
        ],
        "slot_count": slot_count,
        "agreed_slot_count": agreed_count,
        "disagreement_count": len(disagreements),
        "exact_label_agreement_rate": agreed_count / slot_count if slot_count else None,
        "exact_evidence_agreement_rate": (
            evidence_agreement_count / slot_count if slot_count else None
        ),
        "agreement_by_property": agreement_by_property,
        "disagreements": disagreements,
    }


def _resolution_map(
    resolutions: Any, errors: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    if not isinstance(resolutions, list):
        _issue(errors, "consensus_resolutions_shape", "resolutions must be a list")
        return result
    for item in resolutions:
        if not isinstance(item, dict):
            _issue(errors, "consensus_resolution_item", "resolution must be an object")
            continue
        slot_id = str(item.get("slot_id") or "")
        if not slot_id or slot_id in result:
            _issue(
                errors, "consensus_resolution_id", "resolution slot ids must be unique"
            )
            continue
        result[slot_id] = item
    return result


def validate_consensus_artifact(
    consensus_path: Path,
    *,
    artifact_a_path: Path,
    artifact_b_path: Path,
    disagreement_report_path: Path,
    packet_path: Path,
    source_bundle_path: Path,
    vocabulary_path: Path,
) -> Dict[str, Any]:
    base = validate_annotation_artifact(
        consensus_path,
        packet_path=packet_path,
        source_bundle_path=source_bundle_path,
        vocabulary_path=vocabulary_path,
        expected_stage="consensus",
    )
    errors = list(base["errors"])
    if base["status"] != "ready":
        return {"status": "blocked", "errors": errors, "summary": base["summary"]}
    try:
        expected_disagreement = compare_independent_artifacts(
            artifact_a_path,
            artifact_b_path,
            packet_path=packet_path,
            source_bundle_path=source_bundle_path,
            vocabulary_path=vocabulary_path,
        )
        disagreement = load_json(disagreement_report_path)
        consensus = load_json(consensus_path)
        artifact_a = load_json(artifact_a_path)
        artifact_b = load_json(artifact_b_path)
    except Exception as exc:  # noqa: BLE001
        _issue(errors, "consensus_input_invalid", str(exc))
        return {"status": "blocked", "errors": errors, "summary": base["summary"]}
    if disagreement != expected_disagreement:
        _issue(
            errors,
            "disagreement_report_mismatch",
            "disagreement report is not the deterministic comparison of frozen submissions",
        )
    adjudication = consensus.get("adjudication")
    if not isinstance(adjudication, dict):
        _issue(
            errors, "consensus_adjudication_missing", "adjudication object is required"
        )
        adjudication = {}
    if adjudication.get("disagreement_report_sha256") != sha256_file(
        disagreement_report_path
    ):
        _issue(
            errors,
            "consensus_disagreement_hash",
            "disagreement report hash mismatch",
        )
    if adjudication.get("disagreement_count") != disagreement.get("disagreement_count"):
        _issue(
            errors,
            "consensus_disagreement_count",
            "consensus disagreement_count differs from report",
        )
    expected_refs = expected_disagreement.get("independent_artifacts", [])
    if adjudication.get("independent_artifacts") != expected_refs:
        _issue(
            errors,
            "consensus_independent_identity",
            "consensus must bind the exact two independent artifact identities",
        )
    expected_ids = [str(item["submission_id"]) for item in expected_refs]
    if adjudication.get("independent_artifact_ids") != expected_ids:
        _issue(
            errors,
            "consensus_independent_ids",
            "independent_artifact_ids must match frozen submission ids in order",
        )

    slots_a = _artifact_slots(artifact_a)
    slots_b = _artifact_slots(artifact_b)
    slots_consensus = _artifact_slots(consensus)
    disagreement_ids = {
        str(item["slot_id"]) for item in disagreement.get("disagreements", [])
    }
    resolutions = _resolution_map(adjudication.get("resolutions"), errors)
    if set(resolutions) != disagreement_ids:
        _issue(
            errors,
            "consensus_resolution_coverage",
            "every and only disagreement slots require a resolution",
        )
    unresolved = adjudication.get("unresolved_slots")
    if not isinstance(unresolved, list) or any(
        not isinstance(item, str) for item in unresolved
    ):
        _issue(errors, "consensus_unresolved_shape", "unresolved_slots must be strings")
        unresolved = []
    unresolved_set = set(unresolved)
    resolution_unresolved = {
        slot_id
        for slot_id, item in resolutions.items()
        if item.get("status") == "unresolved"
    }
    if unresolved_set != resolution_unresolved:
        _issue(
            errors,
            "consensus_unresolved_mismatch",
            "unresolved_slots must equal resolutions with status=unresolved",
        )
    allowed_statuses = {
        "selected_annotator_a",
        "selected_annotator_b",
        "revised",
        "unresolved",
        "not_applicable",
    }
    for slot_id in sorted(slots_consensus):
        consensus_slot = slots_consensus[slot_id]
        a = slots_a[slot_id]
        b = slots_b[slot_id]
        comparable_consensus = {
            "applicability": consensus_slot["applicability"],
            "value": consensus_slot["value"],
        }
        comparable_a = {"applicability": a["applicability"], "value": a["value"]}
        comparable_b = {"applicability": b["applicability"], "value": b["value"]}
        if slot_id not in disagreement_ids:
            if comparable_consensus != comparable_a or comparable_a != comparable_b:
                _issue(
                    errors,
                    "consensus_changed_agreement",
                    "consensus cannot silently change an agreed independent slot",
                    field_path=consensus_slot["field_path"],
                    property_name=consensus_slot["property"],
                )
            continue
        resolution = resolutions.get(slot_id, {})
        status = resolution.get("status")
        if status not in allowed_statuses:
            _issue(
                errors,
                "consensus_resolution_status",
                f"invalid resolution status {status!r}",
                field_path=consensus_slot["field_path"],
                property_name=consensus_slot["property"],
            )
            continue
        if not str(resolution.get("rationale") or "").strip():
            _issue(
                errors,
                "consensus_resolution_rationale",
                "human adjudication rationale is required",
                field_path=consensus_slot["field_path"],
                property_name=consensus_slot["property"],
            )
        if status == "selected_annotator_a" and comparable_consensus != comparable_a:
            _issue(
                errors,
                "consensus_resolution_value",
                "consensus does not match annotator A",
                field_path=consensus_slot["field_path"],
                property_name=consensus_slot["property"],
            )
        elif status == "selected_annotator_b" and comparable_consensus != comparable_b:
            _issue(
                errors,
                "consensus_resolution_value",
                "consensus does not match annotator B",
                field_path=consensus_slot["field_path"],
                property_name=consensus_slot["property"],
            )
        elif status == "unresolved" and not (
            consensus_slot["applicability"] is True and consensus_slot["value"] is None
        ):
            _issue(
                errors,
                "consensus_unresolved_value",
                "unresolved slots must be applicable null",
                field_path=consensus_slot["field_path"],
                property_name=consensus_slot["property"],
            )
        elif status == "not_applicable" and not (
            consensus_slot["applicability"] is False and consensus_slot["value"] is None
        ):
            _issue(
                errors,
                "consensus_na_value",
                "not-applicable resolution must be false/null",
                field_path=consensus_slot["field_path"],
                property_name=consensus_slot["property"],
            )
    return {
        "status": "ready" if not errors else "blocked",
        "errors": errors,
        "summary": {
            **base["summary"],
            "disagreement_count": disagreement.get("disagreement_count"),
            "unresolved_count": len(unresolved_set),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and validate model-blind semantic gold artifacts."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    bundle = subparsers.add_parser(
        "build-source-bundle",
        help="Build an approved evidence catalog from one neutral packet.",
    )
    bundle.add_argument("--packet", type=Path, required=True)
    bundle.add_argument("--vocabulary", type=Path, required=True)
    bundle.add_argument("--output", type=Path, required=True)

    workflow = subparsers.add_parser(
        "build-workflow-manifest",
        help="Bind calibration packets, bundles, vocabulary, and handbook by hash.",
    )
    workflow.add_argument("--calibration-manifest", type=Path, required=True)
    workflow.add_argument("--vocabulary", type=Path, required=True)
    workflow.add_argument("--source-bundle-dir", type=Path, required=True)
    workflow.add_argument("--handbook", type=Path, required=True)
    workflow.add_argument("--output", type=Path, required=True)

    validate = subparsers.add_parser(
        "validate-independent",
        help="Validate one independent annotator submission.",
    )
    validate.add_argument("--artifact", type=Path, required=True)
    validate.add_argument("--packet", type=Path, required=True)
    validate.add_argument("--source-bundle", type=Path, required=True)
    validate.add_argument("--vocabulary", type=Path, required=True)

    compare = subparsers.add_parser(
        "compare",
        help="Reveal differences only after both independent artifacts validate.",
    )
    compare.add_argument("--artifact-a", type=Path, required=True)
    compare.add_argument("--artifact-b", type=Path, required=True)
    compare.add_argument("--packet", type=Path, required=True)
    compare.add_argument("--source-bundle", type=Path, required=True)
    compare.add_argument("--vocabulary", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)

    consensus = subparsers.add_parser(
        "validate-consensus",
        help="Validate consensus against both originals and the disagreement report.",
    )
    consensus.add_argument("--artifact", type=Path, required=True)
    consensus.add_argument("--artifact-a", type=Path, required=True)
    consensus.add_argument("--artifact-b", type=Path, required=True)
    consensus.add_argument("--disagreement-report", type=Path, required=True)
    consensus.add_argument("--packet", type=Path, required=True)
    consensus.add_argument("--source-bundle", type=Path, required=True)
    consensus.add_argument("--vocabulary", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "build-source-bundle":
        payload = build_packet_source_bundle(args.packet, args.vocabulary)
        _write_json(args.output, payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    if args.command == "build-workflow-manifest":
        payload = build_annotation_workflow_manifest(
            args.calibration_manifest,
            vocabulary_path=args.vocabulary,
            source_bundle_dir=args.source_bundle_dir,
            handbook_path=args.handbook,
            output_path=args.output,
        )
        _write_json(args.output, payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    common = {
        "packet_path": args.packet,
        "source_bundle_path": args.source_bundle,
        "vocabulary_path": args.vocabulary,
    }
    if args.command == "validate-independent":
        report = validate_annotation_artifact(args.artifact, **common)
    elif args.command == "compare":
        report = compare_independent_artifacts(
            args.artifact_a,
            args.artifact_b,
            **common,
        )
        _write_json(args.output, report)
    else:
        report = validate_consensus_artifact(
            args.artifact,
            artifact_a_path=args.artifact_a,
            artifact_b_path=args.artifact_b,
            disagreement_report_path=args.disagreement_report,
            **common,
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report.get("status") == "blocked":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
