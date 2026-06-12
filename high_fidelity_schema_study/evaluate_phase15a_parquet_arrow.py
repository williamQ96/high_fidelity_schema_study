from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .extractors.base import ExtractionRequest
from .extractors.registry import extract_path


ROOT = Path(__file__).resolve().parent
CHALLENGE_ROOT = ROOT / "testdata" / "parquet_phase15a"
MANIFEST_PATH = CHALLENGE_ROOT / "manifest.json"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "experiments" / "phase15a_parquet_arrow"


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


def evaluate_phase15a(manifest_path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    counters = {key: [0, 0] for key in (
        "format", "routing", "arrow_fields", "parquet_columns", "row_groups", "compression",
        "encodings", "statistics", "nullability", "timezone", "metadata", "evidence", "value_abstention",
    )}
    cases = []
    unsupported_promotions = 0

    def check(name: str, value: bool) -> bool:
        counters[name][0] += int(value)
        counters[name][1] += 1
        return value

    for case in manifest["cases"]:
        outcome = _portable(extract_path(ExtractionRequest(str((CHALLENGE_ROOT / case["file"]).resolve()))).to_dict())
        schema = outcome.get("schema") or {}
        metadata = schema.get("metadata", {})
        analysis = metadata.get("parquet_analysis", {})
        fields = {item["field_path"]: item for item in schema.get("fields", [])}
        arrow_fields = {item["field_path"]: item for item in analysis.get("arrow_fields", [])}
        columns = {item["path"]: item for item in analysis.get("parquet_columns", [])}
        row_groups = analysis.get("row_groups", [])
        checks: Dict[str, Any] = {}
        checks["format"] = check("format", outcome["format_decision"]["selected_format"] == "parquet")
        checks["routing"] = check(
            "routing", (outcome.get("extractor") or {}).get("extractor_id") == "parquet_arrow_metadata_extractor"
        )
        checks["arrow_fields"] = {
            path: check("arrow_fields", path in fields and path in arrow_fields)
            for path in case["expected_fields"]
        }
        checks["parquet_columns"] = {
            path: check("parquet_columns", path in columns)
            for path in case["expected_columns"]
        }
        checks["row_groups"] = check("row_groups", len(row_groups) == case["expected_row_groups"])
        observed_compression = {
            column["compression"]
            for group in row_groups
            for column in group["columns"]
        }
        checks["compression"] = [
            check("compression", value in observed_compression)
            for value in case.get("expected_compression", [])
        ]
        observed_encodings = {
            encoding
            for group in row_groups
            for column in group["columns"]
            for encoding in column["encodings"]
        }
        checks["encodings"] = [
            check("encodings", value in observed_encodings)
            for value in case.get("expected_encodings", [])
        ]
        expected_statistics_state: Optional[str] = case.get("expected_statistics_state")
        if expected_statistics_state is not None:
            checks["statistics"] = [
                check("statistics", column["statistics"]["state"] == expected_statistics_state)
                for group in row_groups
                for column in group["columns"]
            ]
        checks["nullability"] = {
            path: check("nullability", fields.get(path, {}).get("nullable") == expected)
            for path, expected in case.get("expected_nullability", {}).items()
        }
        checks["timezones"] = {
            path: check(
                "timezone",
                arrow_fields.get(path, {}).get("temporal_claim", {}).get("timezone") == expected,
            )
            for path, expected in case.get("expected_timezones", {}).items()
        }
        checks["metadata"] = [
            check("metadata", key in metadata.get("key_value_metadata", {}))
            for key in case.get("expected_metadata_keys", [])
        ]
        for path, keys in case.get("expected_field_metadata", {}).items():
            checks["metadata"].extend(
                check("metadata", key in arrow_fields.get(path, {}).get("metadata", {}))
                for key in keys
            )
        evidence_checks = [
            bool(field.get("source_evidence"))
            for field in schema.get("fields", [])
        ] + [
            bool(item.get("evidence_refs"))
            for item in analysis.get("arrow_fields", [])
        ] + [
            bool(item.get("evidence_refs"))
            for item in analysis.get("parquet_columns", [])
        ]
        checks["evidence"] = [check("evidence", value) for value in evidence_checks]
        value_abstention = (
            metadata.get("value_observation", {}).get("row_values_read") == 0
            and metadata.get("value_observation", {}).get("reason_code") == "row_values_not_read"
        )
        checks["value_abstention"] = check("value_abstention", value_abstention)
        if any(field.get("semantic_type") != "unknown" for field in schema.get("fields", [])):
            unsupported_promotions += 1
        cases.append({"case_id": case["case_id"], "checks": checks, "outcome": outcome})

    metrics = {
        "case_count": len(cases),
        "format_detection_accuracy": _ratio(*counters["format"]),
        "extractor_routing_accuracy": _ratio(*counters["routing"]),
        "arrow_field_accuracy": _ratio(*counters["arrow_fields"]),
        "parquet_column_accuracy": _ratio(*counters["parquet_columns"]),
        "row_group_accuracy": _ratio(*counters["row_groups"]),
        "compression_accuracy": _ratio(*counters["compression"]),
        "encoding_accuracy": _ratio(*counters["encodings"]),
        "statistics_policy_accuracy": _ratio(*counters["statistics"]),
        "nullability_accuracy": _ratio(*counters["nullability"]),
        "timestamp_timezone_accuracy": _ratio(*counters["timezone"]),
        "metadata_accuracy": _ratio(*counters["metadata"]),
        "evidence_coverage": _ratio(*counters["evidence"]),
        "row_value_abstention_accuracy": _ratio(*counters["value_abstention"]),
        "unsupported_promotion_count": unsupported_promotions,
    }
    return {
        "experiment_id": manifest["experiment_id"],
        "claim_boundary": manifest["claim_boundary"],
        "generation": manifest["generation"],
        "metrics": metrics,
        "cases": cases,
    }


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Phase 15A Parquet / Arrow Metadata-First Evaluation",
        "",
        report["claim_boundary"],
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for name, value in report["metrics"].items():
        lines.append(f"| {name} | {value:.4f} |" if isinstance(value, float) else f"| {name} | {value} |")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Parquet footer and Arrow schema metadata only; row values are not read.",
            "- Footer statistics are reported as metadata and are not independently validated against row values.",
            "- Semantic roles are not inferred from field names.",
            "- The controlled pack is not representative ecosystem evidence.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_phase15a_artifacts(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    report = report or evaluate_phase15a()
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
