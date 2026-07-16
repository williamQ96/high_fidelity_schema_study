from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .extractors.base import ExtractionRequest
from .extractors.registry import extract_path


ROOT = Path(__file__).resolve().parent
CHALLENGE_ROOT = ROOT / "testdata" / "netcdf_cf_phase13"
MANIFEST_PATH = CHALLENGE_ROOT / "manifest.json"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "experiments" / "phase13_netcdf_cf"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _field_maps(schema: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
    by_path = {field["field_path"]: field for field in schema.get("fields", [])}
    by_name = {field["field_name"]: field for field in schema.get("fields", [])}
    return by_path, by_name


def _find_field(key: str, by_path: Dict[str, Any], by_name: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return by_path.get(key) or by_name.get(key)


def _analysis_map(schema: Dict[str, Any]) -> Dict[str, Any]:
    return {
        item["field_path"]: item
        for item in schema.get("metadata", {}).get("cf_analysis", {}).get("variables", [])
    }


def _selected_time_field(schema: Dict[str, Any]) -> Optional[str]:
    selected = (
        schema.get("metadata", {})
        .get("cf_analysis", {})
        .get("temporal", {})
        .get("selection", {})
        .get("selected_candidate")
    )
    return selected.get("field") if selected else None


def _calendar_claims(schema: Dict[str, Any]) -> Dict[str, Any]:
    return (
        schema.get("metadata", {})
        .get("cf_analysis", {})
        .get("temporal", {})
        .get("calendar_claims", {})
    )


def _accepted_claims(schema: Dict[str, Any]) -> list[Dict[str, Any]]:
    claims: list[Dict[str, Any]] = []
    cf = schema.get("metadata", {}).get("cf_analysis", {})
    for variable in cf.get("variables", []):
        for key in ("coordinate_role_claim", "bounds_claim", "unit_claim"):
            claim = variable.get(key)
            if claim and claim.get("state") in {"supported", "derived"}:
                claims.append(claim)
    for claim in cf.get("temporal", {}).get("calendar_claims", {}).values():
        if claim.get("state") in {"supported", "derived"}:
            claims.append(claim)
    for claim in cf.get("temporal", {}).get("selection", {}).get("property_claims", {}).values():
        if claim.get("state") in {"supported", "derived"}:
            claims.append(claim)
    return claims


def evaluate_phase13(manifest_path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    manifest = load_json(manifest_path)
    cases = []
    counters = {
        "format": [0, 0],
        "routing": [0, 0],
        "physical": [0, 0],
        "coordinate": [0, 0],
        "time_axis": [0, 0],
        "calendar": [0, 0],
        "unit": [0, 0],
        "abstention_tp": 0,
        "abstention_fp": 0,
        "abstention_fn": 0,
        "evidence": [0, 0],
    }
    unsupported_promotion_count = 0

    for case in manifest["cases"]:
        outcome = _portable_paths(
            extract_path(ExtractionRequest(str((CHALLENGE_ROOT / case["file"]).resolve()))).to_dict()
        )
        schema = outcome.get("schema") or {}
        by_path, by_name = _field_maps(schema)
        analyses = _analysis_map(schema)

        format_match = outcome["format_decision"]["selected_format"] == "netcdf"
        routing_match = (outcome.get("extractor") or {}).get("extractor_id") == "netcdf_cf_deterministic_extractor"
        counters["format"][0] += int(format_match)
        counters["format"][1] += 1
        counters["routing"][0] += int(routing_match)
        counters["routing"][1] += 1

        physical_matches: Dict[str, bool] = {}
        for expected in case["expected_variables"]:
            field = _find_field(expected, by_path, by_name)
            match = bool(
                field
                and field.get("physical_type")
                and isinstance(field.get("shape"), list)
                and any(item.get("evidence_type") == "netcdf_variable" for item in field.get("source_evidence", []))
            )
            physical_matches[expected] = match
            counters["physical"][0] += int(match)
            counters["physical"][1] += 1
        for expected_group in case.get("expected_groups", []):
            group = next(
                (item for item in schema.get("groups", []) if item.get("path") == expected_group),
                None,
            )
            match = bool(group and group.get("source_evidence"))
            physical_matches[f"group:{expected_group}"] = match
            counters["physical"][0] += int(match)
            counters["physical"][1] += 1
        for expected_dimension in case.get("expected_dimensions", []):
            dimension = schema.get("metadata", {}).get("dimensions", {}).get(expected_dimension)
            match = bool(dimension and dimension.get("source_evidence"))
            physical_matches[f"dimension:{expected_dimension}"] = match
            counters["physical"][0] += int(match)
            counters["physical"][1] += 1

        coordinate_matches: Dict[str, bool] = {}
        for field_key, expected_roles in case.get("expected_coordinate_roles", {}).items():
            field = _find_field(field_key, by_path, by_name)
            analysis = analyses.get(field["field_path"]) if field else None
            actual_roles = set((analysis or {}).get("coordinate_roles", []))
            match = set(expected_roles).issubset(actual_roles)
            coordinate_matches[field_key] = match
            counters["coordinate"][0] += int(match)
            counters["coordinate"][1] += 1
        for field_key, expected_state in case.get("expected_coordinate_claim_states", {}).items():
            field = _find_field(field_key, by_path, by_name)
            analysis = analyses.get(field["field_path"]) if field else None
            actual_state = (analysis or {}).get("coordinate_role_claim", {}).get("state")
            match = actual_state == expected_state
            coordinate_matches[f"{field_key}:claim_state"] = match
            counters["coordinate"][0] += int(match)
            counters["coordinate"][1] += 1

        selected_time = _selected_time_field(schema)
        time_match = selected_time == case.get("expected_time_field")
        counters["time_axis"][0] += int(time_match)
        counters["time_axis"][1] += 1

        calendar_matches: Dict[str, bool] = {}
        actual_calendars = _calendar_claims(schema)
        for field_key, (expected_value, expected_state) in case.get("expected_calendar", {}).items():
            field = _find_field(field_key, by_path, by_name)
            claim = actual_calendars.get(field["field_path"]) if field else None
            match = bool(claim and claim.get("value") == expected_value and claim.get("state") == expected_state)
            calendar_matches[field_key] = match
            counters["calendar"][0] += int(match)
            counters["calendar"][1] += 1

        unit_matches: Dict[str, bool] = {}
        for field_key, expected_status in case.get("expected_units", {}).items():
            field = _find_field(field_key, by_path, by_name)
            actual_status = (field.get("unit_normalization") or {}).get("status") if field else None
            match = actual_status == expected_status
            unit_matches[field_key] = match
            counters["unit"][0] += int(match)
            counters["unit"][1] += 1

        for field_key in case.get("expected_bounds_variables", []):
            field = _find_field(field_key, by_path, by_name)
            analysis = analyses.get(field["field_path"]) if field else None
            match = bool(analysis and analysis.get("is_bounds_variable"))
            physical_matches[f"bounds:{field_key}"] = match
            counters["physical"][0] += int(match)
            counters["physical"][1] += 1

        for field_key in case.get("expected_nullable_fields", []):
            field = _find_field(field_key, by_path, by_name)
            match = bool(field and field.get("nullable"))
            physical_matches[f"nullable:{field_key}"] = match
            counters["physical"][0] += int(match)
            counters["physical"][1] += 1

        for field_key in case.get("expected_unknown_fields", []):
            field = _find_field(field_key, by_path, by_name)
            if field and (field.get("logical_type") != "unknown" or field.get("semantic_type") != "unknown"):
                unsupported_promotion_count += 1

        expected_abstention = bool(case["expect_temporal_abstention"])
        actual_abstention = selected_time is None
        if expected_abstention and actual_abstention:
            counters["abstention_tp"] += 1
        elif not expected_abstention and actual_abstention:
            counters["abstention_fp"] += 1
        elif expected_abstention and not actual_abstention:
            counters["abstention_fn"] += 1
            unsupported_promotion_count += 1

        for field in schema.get("fields", []):
            accepted = bool(field.get("physical_type"))
            if field.get("logical_type") != "unknown" or field.get("semantic_type") != "unknown":
                accepted = True
            if accepted:
                counters["evidence"][1] += 1
                counters["evidence"][0] += int(bool(field.get("source_evidence")))
        for group in schema.get("groups", []):
            counters["evidence"][1] += 1
            counters["evidence"][0] += int(bool(group.get("source_evidence")))
        for dimension in schema.get("metadata", {}).get("dimensions", {}).values():
            counters["evidence"][1] += 1
            counters["evidence"][0] += int(bool(dimension.get("source_evidence")))
        for claim in _accepted_claims(schema):
            counters["evidence"][1] += 1
            counters["evidence"][0] += int(bool(claim.get("evidence_refs")))

        time_properties_match = True
        actual_time_axis = schema.get("metadata", {}).get("time_series", {}).get("time_axis", {})
        for key, expected_value in case.get("expected_time_properties", {}).items():
            time_properties_match = time_properties_match and actual_time_axis.get(key) == expected_value
        if not time_properties_match:
            counters["time_axis"][0] -= int(time_match)

        cases.append(
            {
                "case_id": case["case_id"],
                "status": outcome["status"],
                "format_match": format_match,
                "routing_match": routing_match,
                "physical_matches": physical_matches,
                "coordinate_matches": coordinate_matches,
                "time_axis_match": time_match and time_properties_match,
                "calendar_matches": calendar_matches,
                "unit_matches": unit_matches,
                "expected_temporal_abstention": expected_abstention,
                "actual_temporal_abstention": actual_abstention,
                "outcome": outcome,
            }
        )

    tp = counters["abstention_tp"]
    fp = counters["abstention_fp"]
    fn = counters["abstention_fn"]
    metrics = {
        "case_count": len(cases),
        "format_detection_accuracy": safe_ratio(*counters["format"]),
        "extractor_routing_accuracy": safe_ratio(*counters["routing"]),
        "physical_extraction_accuracy": safe_ratio(*counters["physical"]),
        "coordinate_role_accuracy": safe_ratio(*counters["coordinate"]),
        "time_axis_accuracy": safe_ratio(*counters["time_axis"]),
        "calendar_handling_accuracy": safe_ratio(*counters["calendar"]),
        "unit_mapping_accuracy": safe_ratio(*counters["unit"]),
        "temporal_abstention_precision": safe_ratio(tp, tp + fp),
        "temporal_abstention_recall": safe_ratio(tp, tp + fn),
        "unsupported_promotion_count": unsupported_promotion_count,
        "evidence_coverage": safe_ratio(*counters["evidence"]),
    }
    return {
        "experiment_id": manifest["experiment_id"],
        "manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "metrics": metrics,
        "cases": cases,
        "notes": [
            "Phase 13 is isolated from the frozen Artifact Paper benchmark.",
            "NetCDF/CF semantic claims are promoted only from explicit attributes or deterministic structure.",
            "Non-standard calendars are preserved but not decoded by the standard-calendar temporal path.",
        ],
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Phase 13 NetCDF/CF Experiment",
        "",
        "This generated report evaluates the isolated NetCDF/CF challenge pack.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for metric, value in report["metrics"].items():
        lines.append(f"| {metric} | {value:.4f} |" if isinstance(value, float) else f"| {metric} | {value} |")
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Case | Status | Format | Routing | Physical | Coordinate | Time | Calendar | Units | Abstention |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    def all_true(values: Dict[str, bool]) -> bool:
        return all(values.values()) if values else True

    for case in report["cases"]:
        lines.append(
            f"| {case['case_id']} | {case['status']} | {'pass' if case['format_match'] else 'fail'} | "
            f"{'pass' if case['routing_match'] else 'fail'} | {'pass' if all_true(case['physical_matches']) else 'fail'} | "
            f"{'pass' if all_true(case['coordinate_matches']) else 'fail'} | {'pass' if case['time_axis_match'] else 'fail'} | "
            f"{'pass' if all_true(case['calendar_matches']) else 'fail'} | {'pass' if all_true(case['unit_matches']) else 'fail'} | "
            f"{'pass' if case['expected_temporal_abstention'] == case['actual_temporal_abstention'] else 'fail'} |"
        )
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


def write_phase13_artifacts(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    report = report or evaluate_phase13()
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
