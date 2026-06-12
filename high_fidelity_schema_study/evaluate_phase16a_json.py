from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .extractors.base import ExtractionRequest
from .extractors.registry import extract_path


ROOT = Path(__file__).resolve().parent
CHALLENGE_ROOT = ROOT / "testdata" / "json_phase16a"
MANIFEST_PATH = CHALLENGE_ROOT / "manifest.json"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "experiments" / "phase16a_json_structure"


def _ratio(hit: int, total: int) -> float:
    return round(hit / total, 4) if total else 0.0


def _portable(value: Any) -> Any:
    if isinstance(value, str):
        root = str(ROOT)
        return value[len(root) :].lstrip("\\/").replace("\\", "/") if value.startswith(root) else value
    if isinstance(value, dict):
        return {key: _portable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_portable(item) for item in value]
    return value


def evaluate_phase16a(manifest_path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    counters = {key: [0, 0] for key in (
        "format", "routing", "mode", "path", "missing", "nullable", "array", "declared", "conflict", "sampling", "evidence",
    )}
    cases = []
    unsupported_promotions = 0

    def check(name: str, value: bool) -> bool:
        counters[name][0] += int(value)
        counters[name][1] += 1
        return value

    for case in manifest["cases"]:
        outcome = _portable(
            extract_path(
                ExtractionRequest(
                    str((CHALLENGE_ROOT / case["file"]).resolve()),
                    sample_limit=case.get("sample_limit", 200),
                )
            ).to_dict()
        )
        schema = outcome.get("schema") or {}
        analysis = schema.get("metadata", {}).get("json_analysis", {})
        fields = {field["field_path"]: field for field in schema.get("fields", [])}
        observed = {item["field_path"]: item for item in analysis.get("observed_fields", [])}
        declared = {item["field_path"]: item for item in analysis.get("declared_fields", [])}
        checks: Dict[str, Any] = {
            "format": check("format", outcome["format_decision"]["selected_format"] == "json"),
            "routing": check(
                "routing", (outcome.get("extractor") or {}).get("extractor_id") == "json_bounded_structure_extractor"
            ),
            "mode": check("mode", analysis.get("mode") == case["expected_mode"]),
            "paths": {path: check("path", path in fields) for path in case["expected_paths"]},
            "missing": {
                path: check("missing", observed.get(path, {}).get("missing_count") == count)
                for path, count in case.get("expected_missing", {}).items()
            },
            "nullable": {
                path: check("nullable", fields.get(path, {}).get("nullable") is True)
                for path in case.get("expected_nullable", [])
            },
            "arrays": {
                path: check("array", observed.get(path, {}).get("array", {}).get("heterogeneous") is True)
                for path in case.get("expected_heterogeneous_arrays", [])
            },
            "declared": {
                path: check("declared", declared.get(path, {}).get("required") == required)
                for path, required in case.get("expected_declared_required", {}).items()
            },
        }
        if case.get("expected_sampling_issue"):
            checks["sampling"] = check(
                "sampling",
                any(issue["code"] == "sampling_insufficient" for issue in outcome["issues"]),
            )
        if "expected_conflict_count" in case:
            checks["conflicts"] = check(
                "conflict",
                len(analysis.get("conflicts", [])) == case["expected_conflict_count"],
            )
        checks["evidence"] = [
            check("evidence", bool(field.get("source_evidence")))
            for field in schema.get("fields", [])
        ]
        if any(field.get("semantic_type") != "unknown" for field in schema.get("fields", [])):
            unsupported_promotions += 1
        cases.append({"case_id": case["case_id"], "checks": checks, "outcome": outcome})

    metrics = {
        "case_count": len(cases),
        "format_detection_accuracy": _ratio(*counters["format"]),
        "extractor_routing_accuracy": _ratio(*counters["routing"]),
        "mode_accuracy": _ratio(*counters["mode"]),
        "path_accuracy": _ratio(*counters["path"]),
        "missingness_accuracy": _ratio(*counters["missing"]),
        "nullability_accuracy": _ratio(*counters["nullable"]),
        "heterogeneous_array_accuracy": _ratio(*counters["array"]),
        "declared_schema_accuracy": _ratio(*counters["declared"]),
        "declared_observed_conflict_accuracy": _ratio(*counters["conflict"]),
        "sampling_issue_accuracy": _ratio(*counters["sampling"]),
        "evidence_coverage": _ratio(*counters["evidence"]),
        "unsupported_promotion_count": unsupported_promotions,
    }
    return {
        "experiment_id": manifest["experiment_id"],
        "claim_boundary": manifest["claim_boundary"],
        "metrics": metrics,
        "cases": cases,
    }


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Phase 16A JSON Structure Evaluation",
        "",
        report["claim_boundary"],
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["metrics"].items():
        lines.append(f"| {key} | {value:.4f} |" if isinstance(value, float) else f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Observed paths and type sets are bounded by the configured record sample.",
            "- JSON Schema documents produce declared claims, not observed-data claims.",
            "- Semantic roles are not inferred from names.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_phase16a_artifacts(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    report = report or evaluate_phase16a()
    outcomes = output_root / "outcomes"
    outcomes.mkdir(parents=True, exist_ok=True)
    for case in report["cases"]:
        (outcomes / f"{case['case_id']}.json").write_text(
            json.dumps({"case_id": case["case_id"], "outcome": case["outcome"]}, indent=2) + "\n",
            encoding="utf-8",
        )
    summary = {key: value for key, value in report.items() if key != "cases"}
    summary["cases"] = [{"case_id": case["case_id"], "checks": case["checks"]} for case in report["cases"]]
    (output_root / "report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output_root / "report.md").write_text(_markdown(report), encoding="utf-8")
    return report
