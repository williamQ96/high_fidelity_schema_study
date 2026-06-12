from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, Optional

from .extractors.base import ExtractionRequest
from .extractors.registry import extract_path


ROOT = Path(__file__).resolve().parent
CHALLENGE_ROOT = ROOT / "testdata" / "zarr_phase14a"
MANIFEST_PATH = CHALLENGE_ROOT / "manifest.json"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "experiments" / "phase14a_zarr"
ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")


def safe_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _portable_paths(value: Any) -> Any:
    if isinstance(value, str):
        root_text = str(ROOT)
        if value.startswith(root_text):
            return value[len(root_text) :].lstrip("\\/").replace("\\", "/")
        return value
    if isinstance(value, dict):
        return {key: _portable_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_portable_paths(item) for item in value]
    return value


def _has_absolute_path(value: Any) -> bool:
    if isinstance(value, str):
        return bool(ABSOLUTE_PATH_RE.match(value)) or str(ROOT) in value
    if isinstance(value, dict):
        return any(_has_absolute_path(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_absolute_path(item) for item in value)
    return False


def _field_maps(schema: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    by_path = {field["field_path"]: field for field in schema.get("fields", [])}
    by_name = {field["field_name"]: field for field in schema.get("fields", [])}
    return by_path, by_name


def _find_field(key: str, by_path: Dict[str, Any], by_name: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return by_path.get(key) or by_name.get(key)


def _analysis_map(schema: Dict[str, Any]) -> Dict[str, Any]:
    return {
        item["field_path"]: item
        for item in schema.get("metadata", {}).get("zarr_analysis", {}).get("arrays", [])
    }


def _accepted_claims(schema: Dict[str, Any]) -> list[Dict[str, Any]]:
    claims: list[Dict[str, Any]] = []
    analysis = schema.get("metadata", {}).get("zarr_analysis", {})
    for array in analysis.get("arrays", []):
        for key in ("dimension_claim", "coordinate_role_claim", "unit_claim"):
            claim = array.get(key)
            if claim and claim.get("state") in {"supported", "derived"}:
                claims.append(claim)
    for claim in analysis.get("calendar_claims", {}).values():
        if claim.get("state") in {"supported", "derived"}:
            claims.append(claim)
    for claim in analysis.get("temporal", {}).get("property_claims", {}).values():
        if claim.get("state") in {"supported", "derived"}:
            claims.append(claim)
    return claims


def evaluate_phase14a(manifest_path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    counters: Dict[str, Any] = {
        "detection": [0, 0],
        "routing": [0, 0],
        "status": [0, 0],
        "groups": [0, 0],
        "arrays": [0, 0],
        "physical": [0, 0],
        "attributes": [0, 0],
        "dimensions": [0, 0],
        "coordinates": [0, 0],
        "calendar": [0, 0],
        "units": [0, 0],
        "issues": [0, 0],
        "partial": [0, 0],
        "evidence": [0, 0],
        "portability": [0, 0],
        "value_observation_abstention": [0, 0],
        "abstention_tp": 0,
        "abstention_fp": 0,
        "abstention_fn": 0,
    }
    unsupported_promotion_count = 0
    cases = []

    for case in manifest["cases"]:
        raw_outcome = extract_path(
            ExtractionRequest(
                str((CHALLENGE_ROOT / case["store"]).resolve()),
                resource_kind="directory_store",
            )
        ).to_dict()
        portable = not _has_absolute_path(raw_outcome)
        outcome = _portable_paths(raw_outcome)
        schema = outcome.get("schema") or {}
        by_path, by_name = _field_maps(schema)
        analyses = _analysis_map(schema)
        value_observation_abstained = None
        if schema:
            value_observation = schema.get("metadata", {}).get("value_observation", {})
            value_observation_abstained = (
                value_observation.get("state") == "unknown"
                and value_observation.get("reason_code") == "chunk_payloads_not_read"
                and "deterministic_profile" not in schema.get("metadata", {})
            )
            counters["value_observation_abstention"][0] += int(value_observation_abstained)
            counters["value_observation_abstention"][1] += 1

        detection_match = outcome["format_decision"]["selected_format"] == "zarr"
        routing_match = (outcome.get("extractor") or {}).get("extractor_id") == "zarr_v2_metadata_extractor"
        status_match = outcome["status"] == case["expected_status"]
        for key, match in (("detection", detection_match), ("routing", routing_match), ("status", status_match)):
            counters[key][0] += int(match)
            counters[key][1] += 1
        counters["portability"][0] += int(portable)
        counters["portability"][1] += 1

        group_matches: Dict[str, bool] = {}
        for expected in case.get("expected_groups", []):
            group = next((item for item in schema.get("groups", []) if item.get("path") == expected), None)
            match = bool(group and group.get("source_evidence"))
            group_matches[expected] = match
            counters["groups"][0] += int(match)
            counters["groups"][1] += 1

        array_matches: Dict[str, bool] = {}
        physical_matches: Dict[str, bool] = {}
        for expected_path, expected_metadata in case.get("expected_arrays", {}).items():
            field = _find_field(expected_path, by_path, by_name)
            analysis = analyses.get(field["field_path"]) if field else None
            array_match = bool(
                field
                and analysis
                and any(item.get("evidence_type") == "zarr_array_metadata" for item in field.get("source_evidence", []))
            )
            array_matches[expected_path] = array_match
            counters["arrays"][0] += int(array_match)
            counters["arrays"][1] += 1
            actual_metadata = (analysis or {}).get("array_metadata", {})
            for key, expected_value in expected_metadata.items():
                match = actual_metadata.get(key) == expected_value
                physical_matches[f"{expected_path}:{key}"] = match
                counters["physical"][0] += int(match)
                counters["physical"][1] += 1

        attribute_matches: Dict[str, bool] = {}
        for field_key, expected_attrs in case.get("expected_attributes", {}).items():
            field = _find_field(field_key, by_path, by_name)
            analysis = analyses.get(field["field_path"]) if field else None
            attrs = (analysis or {}).get("attributes", {})
            match = all(attrs.get(key) == value for key, value in expected_attrs.items())
            attribute_matches[field_key] = match
            counters["attributes"][0] += int(match)
            counters["attributes"][1] += 1

        dimension_matches: Dict[str, bool] = {}
        dimensions = schema.get("metadata", {}).get("dimensions", {})
        for name, expected_size in case.get("expected_dimensions", {}).items():
            dimension = dimensions.get(name)
            match = bool(
                dimension
                and dimension.get("size") == expected_size
                and dimension.get("state") == "supported"
                and dimension.get("source_evidence")
            )
            dimension_matches[name] = match
            counters["dimensions"][0] += int(match)
            counters["dimensions"][1] += 1

        coordinate_matches: Dict[str, bool] = {}
        for field_key, expected_roles in case.get("expected_coordinate_roles", {}).items():
            field = _find_field(field_key, by_path, by_name)
            analysis = analyses.get(field["field_path"]) if field else None
            match = set(expected_roles).issubset(set((analysis or {}).get("coordinate_roles", [])))
            coordinate_matches[field_key] = match
            counters["coordinates"][0] += int(match)
            counters["coordinates"][1] += 1
        for field_key, expected_state in case.get("expected_coordinate_states", {}).items():
            field = _find_field(field_key, by_path, by_name)
            analysis = analyses.get(field["field_path"]) if field else None
            match = (analysis or {}).get("coordinate_role_claim", {}).get("state") == expected_state
            coordinate_matches[f"{field_key}:state"] = match
            counters["coordinates"][0] += int(match)
            counters["coordinates"][1] += 1

        calendar_matches: Dict[str, bool] = {}
        calendars = schema.get("metadata", {}).get("zarr_analysis", {}).get("calendar_claims", {})
        for field_key, (expected_value, expected_state) in case.get("expected_calendar", {}).items():
            field = _find_field(field_key, by_path, by_name)
            claim = calendars.get(field["field_path"]) if field else None
            match = bool(claim and claim.get("value") == expected_value and claim.get("state") == expected_state)
            calendar_matches[field_key] = match
            counters["calendar"][0] += int(match)
            counters["calendar"][1] += 1

        unit_matches: Dict[str, bool] = {}
        for field_key, expected_status in case.get("expected_units", {}).items():
            field = _find_field(field_key, by_path, by_name)
            match = bool(field and (field.get("unit_normalization") or {}).get("status") == expected_status)
            unit_matches[field_key] = match
            counters["units"][0] += int(match)
            counters["units"][1] += 1

        issue_codes = {issue["code"] for issue in outcome.get("issues", [])}
        for expected_code in case.get("expected_issue_codes", []):
            match = expected_code in issue_codes
            counters["issues"][0] += int(match)
            counters["issues"][1] += 1

        if case["expected_status"] == "partial":
            counters["partial"][0] += int(outcome["status"] == "partial" and "partial_extraction" in issue_codes)
            counters["partial"][1] += 1

        for field_key in case.get("expected_unknown_fields", []):
            field = _find_field(field_key, by_path, by_name)
            if field and (field.get("logical_type") != "unknown" or field.get("semantic_type") != "unknown"):
                unsupported_promotion_count += 1

        selected_time = schema.get("metadata", {}).get("time_series", {}).get("time_axis")
        expected_temporal_abstention = case.get("expect_temporal_abstention", True)
        actual_temporal_abstention = selected_time is None
        if expected_temporal_abstention and actual_temporal_abstention:
            counters["abstention_tp"] += 1
        elif not expected_temporal_abstention and actual_temporal_abstention:
            counters["abstention_fp"] += 1
        elif expected_temporal_abstention and not actual_temporal_abstention:
            counters["abstention_fn"] += 1
            unsupported_promotion_count += 1

        for field in schema.get("fields", []):
            counters["evidence"][1] += 1
            counters["evidence"][0] += int(bool(field.get("source_evidence")))
        for group in schema.get("groups", []):
            counters["evidence"][1] += 1
            counters["evidence"][0] += int(bool(group.get("source_evidence")))
        for dimension in dimensions.values():
            if dimension.get("state") == "supported":
                counters["evidence"][1] += 1
                counters["evidence"][0] += int(bool(dimension.get("source_evidence")))
        for claim in _accepted_claims(schema):
            counters["evidence"][1] += 1
            counters["evidence"][0] += int(bool(claim.get("evidence_refs")))

        cases.append(
            {
                "case_id": case["case_id"],
                "status": outcome["status"],
                "detection_match": detection_match,
                "routing_match": routing_match,
                "status_match": status_match,
                "group_matches": group_matches,
                "array_matches": array_matches,
                "physical_matches": physical_matches,
                "attribute_matches": attribute_matches,
                "dimension_matches": dimension_matches,
                "coordinate_matches": coordinate_matches,
                "calendar_matches": calendar_matches,
                "unit_matches": unit_matches,
                "expected_temporal_abstention": expected_temporal_abstention,
                "actual_temporal_abstention": actual_temporal_abstention,
                "value_observation_abstained": value_observation_abstained,
                "path_portable": portable,
                "outcome": outcome,
            }
        )

    tp = counters["abstention_tp"]
    fp = counters["abstention_fp"]
    fn = counters["abstention_fn"]
    return {
        "experiment_id": manifest["experiment_id"],
        "manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "metrics": {
            "case_count": len(cases),
            "store_detection_accuracy": safe_ratio(*counters["detection"]),
            "extractor_routing_accuracy": safe_ratio(*counters["routing"]),
            "outcome_status_accuracy": safe_ratio(*counters["status"]),
            "group_discovery_accuracy": safe_ratio(*counters["groups"]),
            "array_discovery_accuracy": safe_ratio(*counters["arrays"]),
            "physical_metadata_accuracy": safe_ratio(*counters["physical"]),
            "attribute_extraction_accuracy": safe_ratio(*counters["attributes"]),
            "xarray_dimension_accuracy": safe_ratio(*counters["dimensions"]),
            "coordinate_role_accuracy": safe_ratio(*counters["coordinates"]),
            "calendar_handling_accuracy": safe_ratio(*counters["calendar"]),
            "unit_mapping_accuracy": safe_ratio(*counters["units"]),
            "reason_code_coverage": safe_ratio(*counters["issues"]),
            "partial_extraction_accuracy": safe_ratio(*counters["partial"]),
            "temporal_abstention_precision": safe_ratio(tp, tp + fp),
            "temporal_abstention_recall": safe_ratio(tp, tp + fn),
            "value_observation_abstention_accuracy": safe_ratio(*counters["value_observation_abstention"]),
            "evidence_coverage": safe_ratio(*counters["evidence"]),
            "unsupported_promotion_count": unsupported_promotion_count,
            "path_portability_accuracy": safe_ratio(*counters["portability"]),
        },
        "cases": cases,
        "notes": [
            "Phase 14A evaluates local directory-store Zarr v2 metadata extraction only.",
            "Chunk payloads, remote stores, Zarr v3, and full Xarray semantic reconstruction are out of scope.",
            "All temporal candidates abstain because Phase 14A does not read chunk payload samples.",
            "Value-level statistics remain unknown because Phase 14A does not read chunk payload samples.",
        ],
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Phase 14A Zarr Directory-Store Experiment",
        "",
        "This generated report evaluates the isolated local Zarr v2 metadata challenge pack.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for metric, value in report["metrics"].items():
        lines.append(f"| {metric} | {value:.4f} |" if isinstance(value, float) else f"| {metric} | {value} |")
    lines.extend(["", "## Cases", "", "| Case | Status | Detection | Routing | Expected Status | Portable |", "| --- | --- | --- | --- | --- | --- |"])
    for case in report["cases"]:
        lines.append(
            f"| {case['case_id']} | {case['status']} | {'pass' if case['detection_match'] else 'fail'} | "
            f"{'pass' if case['routing_match'] else 'fail'} | {'pass' if case['status_match'] else 'fail'} | "
            f"{'pass' if case['path_portable'] else 'fail'} |"
        )
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


def write_phase14a_artifacts(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    report = report or evaluate_phase14a()
    outcomes_root = output_root / "outcomes"
    outcomes_root.mkdir(parents=True, exist_ok=True)
    for case in report["cases"]:
        (outcomes_root / f"{case['case_id']}.json").write_text(
            json.dumps(case["outcome"], indent=2) + "\n",
            encoding="utf-8",
        )
    summary = {key: value for key, value in report.items() if key != "cases"}
    summary["cases"] = [{key: value for key, value in case.items() if key != "outcome"} for case in report["cases"]]
    (output_root / "report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output_root / "report.md").write_text(render_markdown(report), encoding="utf-8")
    return report
