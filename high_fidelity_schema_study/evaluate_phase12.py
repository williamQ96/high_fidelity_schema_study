from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .extractors.base import ExtractionRequest
from .extractors.registry import extract_path


ROOT = Path(__file__).resolve().parent
CHALLENGE_ROOT = ROOT / "testdata" / "temporal_phase12"
MANIFEST_PATH = CHALLENGE_ROOT / "manifest.json"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "experiments" / "phase12_deterministic_substrate"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _case_path(case: Dict[str, Any]) -> Path:
    return (CHALLENGE_ROOT / case["file"]).resolve()


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


def _extractor_id(outcome: Dict[str, Any]) -> Optional[str]:
    extractor = outcome.get("extractor")
    return extractor.get("extractor_id") if extractor else None


def _selected_temporal_field(outcome: Dict[str, Any]) -> Optional[str]:
    schema = outcome.get("schema") or {}
    analysis = schema.get("metadata", {}).get("temporal_analysis", {})
    selected = analysis.get("selected_candidate")
    return selected.get("field") if selected else None


def _time_axis(outcome: Dict[str, Any]) -> Dict[str, Any]:
    schema = outcome.get("schema") or {}
    return schema.get("metadata", {}).get("time_series", {}).get("time_axis", {})


def _property_claims(outcome: Dict[str, Any]) -> Dict[str, Any]:
    schema = outcome.get("schema") or {}
    return schema.get("metadata", {}).get("temporal_analysis", {}).get("property_claims", {})


def _actual_abstention(case_type: str, outcome: Dict[str, Any]) -> bool:
    if outcome["status"] == "abstained":
        return True
    if case_type == "temporal":
        return _selected_temporal_field(outcome) is None
    return False


def evaluate_phase12(manifest_path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    manifest = load_json(manifest_path)
    evaluated_cases = []

    format_correct = 0
    routing_correct = 0
    failure_complete = 0
    failure_expected = 0
    selection_correct = 0
    temporal_case_count = 0
    property_correct = 0
    property_total = 0
    exact_profile_correct = 0
    evidence_supported = 0
    evidence_total = 0
    reason_supported = 0
    reason_total = 0
    unsupported_promotion_count = 0
    abstention_tp = 0
    abstention_fp = 0
    abstention_fn = 0

    combined_cases = [
        ("temporal", case) for case in manifest["temporal_cases"]
    ] + [
        ("format", case) for case in manifest["format_cases"]
    ]

    for case_type, case in combined_cases:
        outcome_obj = extract_path(
            ExtractionRequest(
                path=str(_case_path(case)),
                format_hint=case.get("format_hint"),
                sample_limit=case.get("sample_limit", 200),
            )
        )
        outcome = _portable_paths(outcome_obj.to_dict())
        actual_format = outcome["format_decision"]["selected_format"]
        actual_extractor = _extractor_id(outcome)
        issue_codes = [issue["code"] for issue in outcome["issues"]]

        format_match = actual_format == case.get("expected_format")
        routing_match = actual_extractor == case.get("expected_extractor")
        format_correct += int(format_match)
        routing_correct += int(routing_match)

        expected_failure = case["expected_status"] in {"abstained", "failed"}
        if expected_failure:
            failure_expected += 1
            expected_issue = case.get("expected_issue_code")
            complete = bool(issue_codes) and (expected_issue is None or expected_issue in issue_codes)
            if case["expected_status"] == "abstained":
                schema = outcome.get("schema") or {}
                complete = complete and schema.get("fields") == []
            failure_complete += int(complete)

        expected_abstention = bool(case.get("expect_abstention"))
        actual_abstention = _actual_abstention(case_type, outcome)
        if expected_abstention and actual_abstention:
            abstention_tp += 1
        elif not expected_abstention and actual_abstention:
            abstention_fp += 1
        elif expected_abstention and not actual_abstention:
            abstention_fn += 1

        temporal_detail: Dict[str, Any] = {}
        if case_type == "temporal":
            temporal_case_count += 1
            actual_selected = _selected_temporal_field(outcome)
            expected_selected = case.get("expected_selected_field")
            selected_match = actual_selected == expected_selected
            selection_correct += int(selected_match)

            axis = _time_axis(outcome)
            claims = _property_claims(outcome)
            property_matches: Dict[str, bool] = {}
            for property_name, expected_value in case.get("expected_properties", {}).items():
                matches = axis.get(property_name) == expected_value
                property_matches[property_name] = matches
                property_correct += int(matches)
                property_total += 1

            state_matches: Dict[str, bool] = {}
            for property_name, expected_state in case.get("expected_property_states", {}).items():
                actual_state = (claims.get(property_name) or {}).get("state")
                state_matches[property_name] = actual_state == expected_state
                if expected_state in {"unknown", "conflicted"} and actual_state in {"supported", "derived"}:
                    unsupported_promotion_count += 1

            exact_match = selected_match and all(property_matches.values()) and all(state_matches.values())
            exact_profile_correct += int(exact_match)

            for claim in claims.values():
                evidence_total += 1
                evidence_supported += int(bool(claim.get("evidence_refs")))
                if claim.get("state") in {"unknown", "conflicted"}:
                    reason_total += 1
                    reason_supported += int(bool(claim.get("reason_code")))

            analysis_issues = (
                (outcome.get("schema") or {})
                .get("metadata", {})
                .get("temporal_analysis", {})
                .get("issues", [])
            )
            for issue in analysis_issues:
                reason_total += 1
                reason_supported += int(bool(issue.get("code")))

            temporal_detail = {
                "expected_selected_field": expected_selected,
                "actual_selected_field": actual_selected,
                "selection_match": selected_match,
                "property_matches": property_matches,
                "property_state_matches": state_matches,
                "exact_profile_match": exact_match,
            }

        if expected_failure:
            for issue in outcome["issues"]:
                reason_total += 1
                reason_supported += int(bool(issue.get("code")))

        evaluated_cases.append(
            {
                "case_id": case["case_id"],
                "case_type": case_type,
                "source_file": case["file"],
                "expected_status": case["expected_status"],
                "actual_status": outcome["status"],
                "format_match": format_match,
                "routing_match": routing_match,
                "expected_abstention": expected_abstention,
                "actual_abstention": actual_abstention,
                "issue_codes": issue_codes,
                "temporal": temporal_detail,
                "outcome": outcome,
            }
        )

    case_count = len(combined_cases)
    abstention_precision = safe_ratio(abstention_tp, abstention_tp + abstention_fp)
    abstention_recall = safe_ratio(abstention_tp, abstention_tp + abstention_fn)
    metrics = {
        "case_count": case_count,
        "temporal_case_count": temporal_case_count,
        "format_detection_accuracy": safe_ratio(format_correct, case_count),
        "extractor_routing_accuracy": safe_ratio(routing_correct, case_count),
        "structured_failure_artifact_completeness": safe_ratio(failure_complete, failure_expected),
        "time_axis_selection_accuracy": safe_ratio(selection_correct, temporal_case_count),
        "per_property_temporal_accuracy": safe_ratio(property_correct, property_total),
        "exact_temporal_profile_accuracy": safe_ratio(exact_profile_correct, temporal_case_count),
        "abstention_precision": abstention_precision,
        "abstention_recall": abstention_recall,
        "reason_code_coverage": safe_ratio(reason_supported, reason_total),
        "evidence_coverage": safe_ratio(evidence_supported, evidence_total),
        "unsupported_promotion_count": unsupported_promotion_count,
    }
    return {
        "experiment_id": manifest["experiment_id"],
        "manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "metrics": metrics,
        "cases": evaluated_cases,
        "notes": [
            "This Phase 12 experiment is separate from the frozen Artifact Paper benchmark.",
            "Support scores are deterministic rule strengths, not calibrated probabilities.",
            "Sidecar documentation is not used to promote canonical temporal claims.",
        ],
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Phase 12 Deterministic Substrate Experiment",
        "",
        "This report is generated from the isolated Phase 12 challenge pack. It does not replace frozen paper metrics.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for metric, value in report["metrics"].items():
        if isinstance(value, float):
            lines.append(f"| {metric} | {value:.4f} |")
        else:
            lines.append(f"| {metric} | {value} |")

    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Case | Type | Status | Format | Routing | Abstention | Temporal exact |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for case in report["cases"]:
        temporal_exact = case["temporal"].get("exact_profile_match")
        lines.append(
            f"| {case['case_id']} | {case['case_type']} | {case['actual_status']} | "
            f"{'pass' if case['format_match'] else 'fail'} | {'pass' if case['routing_match'] else 'fail'} | "
            f"{'pass' if case['actual_abstention'] == case['expected_abstention'] else 'fail'} | "
            f"{'n/a' if temporal_exact is None else ('pass' if temporal_exact else 'fail')} |"
        )

    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


def write_phase12_artifacts(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    report = report or evaluate_phase12()
    outcomes_root = output_root / "outcomes"
    outcomes_root.mkdir(parents=True, exist_ok=True)

    for case in report["cases"]:
        case_path = outcomes_root / f"{case['case_id']}.json"
        case_path.write_text(json.dumps(case["outcome"], indent=2) + "\n", encoding="utf-8")

    summary = {key: value for key, value in report.items() if key != "cases"}
    summary["cases"] = [
        {key: value for key, value in case.items() if key != "outcome"}
        for case in report["cases"]
    ]
    (output_root / "report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output_root / "report.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def all_phase12_output_paths(output_root: Path = DEFAULT_OUTPUT_ROOT) -> Iterable[Path]:
    yield output_root / "report.json"
    yield output_root / "report.md"
    for case in load_json(MANIFEST_PATH)["temporal_cases"] + load_json(MANIFEST_PATH)["format_cases"]:
        yield output_root / "outcomes" / f"{case['case_id']}.json"
