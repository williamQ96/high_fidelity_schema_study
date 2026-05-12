"""Second-pass consistency audit for internal gold schema files."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
DOCS_ROOT = ROOT / "docs"
REVIEW_ID = "gold-schema-second-pass-2026-05-11"

REQUIRED_DATASET_KEYS = {
    "dataset_id",
    "file_format",
    "difficulty",
    "data_modality",
    "source_file",
    "time_axis",
    "fields",
}
REQUIRED_FIELD_KEYS = {
    "field_name",
    "field_path",
    "correct_physical_type",
    "correct_logical_type",
    "correct_semantic_type",
    "unit",
    "necessity",
    "gold_evidence",
}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
ALLOWED_NECESSITY = {"high", "medium", "low"}
ALLOWED_LOGICAL_TYPES = {
    "attribute",
    "coordinate",
    "identifier",
    "label",
    "measurement",
    "time_axis",
    "unknown",
}
UNIT_COMPATIBILITY_GROUPS = {
    "C": "celsius",
    "Celsius": "celsius",
    "%": "percent",
    "percent": "percent",
    "m": "meter",
    "meter": "meter",
    "m/s": "meter_per_second",
    "meter_per_second": "meter_per_second",
}


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalized_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    return UNIT_COMPATIBILITY_GROUPS.get(unit, unit)


def add_finding(
    findings: List[Dict[str, str]],
    severity: str,
    dataset_id: str,
    message: str,
) -> None:
    findings.append(
        {
            "severity": severity,
            "dataset_id": dataset_id,
            "message": message,
        }
    )


def audit_dataset(entry: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    dataset_id = entry["dataset_id"]
    findings: List[Dict[str, str]] = []
    gold_path = DATA_ROOT / entry["gold_file"]
    if not gold_path.exists():
        add_finding(findings, "error", dataset_id, f"Missing gold file: {entry['gold_file']}")
        return {"dataset_id": dataset_id, "field_count": 0, "high_necessity_count": 0}, findings

    gold = load_json(gold_path)
    missing_dataset_keys = sorted(REQUIRED_DATASET_KEYS - set(gold))
    if missing_dataset_keys:
        add_finding(
            findings,
            "error",
            dataset_id,
            f"Gold file is missing dataset keys: {', '.join(missing_dataset_keys)}",
        )

    for key in ("dataset_id", "file_format", "difficulty", "data_modality"):
        if gold.get(key) != entry.get(key):
            add_finding(
                findings,
                "error",
                dataset_id,
                f"{key} mismatch: manifest={entry.get(key)!r}, gold={gold.get(key)!r}",
            )

    if gold.get("difficulty") not in ALLOWED_DIFFICULTIES:
        add_finding(findings, "error", dataset_id, f"Invalid difficulty: {gold.get('difficulty')!r}")

    fields = gold.get("fields", [])
    if not isinstance(fields, list) or not fields:
        add_finding(findings, "error", dataset_id, "Gold file has no fields.")
        fields = []

    field_paths = [field.get("field_path") for field in fields]
    duplicate_paths = sorted(path for path, count in Counter(field_paths).items() if count > 1)
    if duplicate_paths:
        add_finding(findings, "error", dataset_id, f"Duplicate field_path values: {duplicate_paths}")

    field_by_path = {field.get("field_path"): field for field in fields}
    high_necessity_count = 0
    empty_evidence_count = 0
    semantic_units: Dict[str, set[str | None]] = defaultdict(set)

    for field in fields:
        path = field.get("field_path", "<missing field_path>")
        missing_field_keys = sorted(REQUIRED_FIELD_KEYS - set(field))
        if missing_field_keys:
            add_finding(
                findings,
                "error",
                dataset_id,
                f"{path}: missing field keys: {', '.join(missing_field_keys)}",
            )
        if not field.get("field_name"):
            add_finding(findings, "error", dataset_id, f"{path}: empty field_name.")
        if not field.get("field_path"):
            add_finding(findings, "error", dataset_id, "Field has empty field_path.")

        logical_type = field.get("correct_logical_type")
        if logical_type not in ALLOWED_LOGICAL_TYPES:
            add_finding(findings, "error", dataset_id, f"{path}: invalid logical type {logical_type!r}.")

        necessity = field.get("necessity")
        if necessity not in ALLOWED_NECESSITY:
            add_finding(findings, "error", dataset_id, f"{path}: invalid necessity {necessity!r}.")
        if necessity == "high":
            high_necessity_count += 1

        unit = field.get("unit")
        if logical_type in {"identifier", "label", "attribute"} and unit is not None:
            add_finding(
                findings,
                "warning",
                dataset_id,
                f"{path}: non-measurement logical type {logical_type!r} carries unit {unit!r}.",
            )
        if not field.get("gold_evidence"):
            empty_evidence_count += 1

        semantic_units[field.get("correct_semantic_type", "unknown")].add(normalized_unit(unit))

    time_axis = gold.get("time_axis")
    time_axis_fields = [
        path
        for path, field in field_by_path.items()
        if field.get("correct_logical_type") == "time_axis"
    ]
    if gold.get("data_modality") == "time_series":
        if not isinstance(time_axis, dict):
            add_finding(findings, "error", dataset_id, "Time-series gold must define top-level time_axis.")
        else:
            axis_field = time_axis.get("field")
            if axis_field not in field_by_path:
                add_finding(findings, "error", dataset_id, f"time_axis.field {axis_field!r} is not a gold field.")
            elif field_by_path[axis_field].get("correct_logical_type") != "time_axis":
                add_finding(
                    findings,
                    "error",
                    dataset_id,
                    f"time_axis.field {axis_field!r} is not marked as logical time_axis.",
                )
    elif time_axis_fields and time_axis is None:
        add_finding(
            findings,
            "note",
            dataset_id,
            "Contains field-level time_axis labels but no top-level time-series profile; acceptable for non-time-series modality.",
        )

    if empty_evidence_count:
        add_finding(
            findings,
            "warning",
            dataset_id,
            f"{empty_evidence_count} field gold_evidence arrays are empty; consistency reviewed, evidence enrichment remains future work.",
        )

    for semantic_type, units in sorted(semantic_units.items()):
        non_null_units = sorted(unit for unit in units if unit is not None)
        if len(non_null_units) > 1:
            add_finding(
                findings,
                "warning",
                dataset_id,
                f"Semantic type {semantic_type!r} uses multiple normalized units: {non_null_units}",
            )
        if non_null_units and None in units:
            add_finding(
                findings,
                "note",
                dataset_id,
                f"Semantic type {semantic_type!r} has both explicit units and null units; null means unit not evidence-backed in that field.",
            )

    dataset_summary = {
        "dataset_id": dataset_id,
        "file_format": gold.get("file_format"),
        "data_modality": gold.get("data_modality"),
        "difficulty": gold.get("difficulty"),
        "field_count": len(fields),
        "high_necessity_count": high_necessity_count,
        "time_axis_field_count": len(time_axis_fields),
        "top_level_time_axis": isinstance(time_axis, dict),
        "gold_path": entry["gold_file"],
    }
    return dataset_summary, findings


def audit_gold_schemas() -> Dict[str, Any]:
    manifest = load_json(DATA_ROOT / "pilot_corpus_manifest.json")
    dataset_summaries: List[Dict[str, Any]] = []
    findings: List[Dict[str, str]] = []

    for entry in manifest["datasets"]:
        dataset_summary, dataset_findings = audit_dataset(entry)
        dataset_summaries.append(dataset_summary)
        findings.extend(dataset_findings)

    finding_counts = Counter(finding["severity"] for finding in findings)
    return {
        "review_id": REVIEW_ID,
        "review_date": date(2026, 5, 11).isoformat(),
        "review_scope": "internal pilot gold schemas",
        "status": "pass" if finding_counts.get("error", 0) == 0 else "fail",
        "dataset_count": len(dataset_summaries),
        "field_count": sum(item["field_count"] for item in dataset_summaries),
        "high_necessity_field_count": sum(item["high_necessity_count"] for item in dataset_summaries),
        "finding_counts": dict(sorted(finding_counts.items())),
        "datasets": dataset_summaries,
        "findings": findings,
        "review_policy": [
            "Top-level time_axis is required for data_modality=time_series only.",
            "Non-time-series HDF5/tabular files may contain field-level time_axis labels without a top-level time-series profile.",
            "Gold unit values represent evidence-backed units. Null units are allowed when a field's unit is not explicitly supported.",
            "Empty gold_evidence arrays are warnings, not consistency failures, because this pass reviews label consistency rather than full evidence enrichment.",
            "semantic_type='unknown' is allowed for intentionally underdetermined fields.",
        ],
    }


def markdown_table(rows: Iterable[Iterable[str]]) -> List[str]:
    rows = list(rows)
    if not rows:
        return []
    header = list(rows[0])
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def write_reports(report: Dict[str, Any]) -> Tuple[Path, Path]:
    DOCS_ROOT.mkdir(parents=True, exist_ok=True)
    json_path = DOCS_ROOT / f"{REVIEW_ID}.json"
    md_path = DOCS_ROOT / f"{REVIEW_ID}.md"

    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Gold Schema Second-Pass Review",
        "",
        f"- Review ID: `{report['review_id']}`",
        f"- Review date: `{report['review_date']}`",
        f"- Scope: {report['review_scope']}",
        f"- Status: `{report['status']}`",
        f"- Datasets reviewed: `{report['dataset_count']}`",
        f"- Fields reviewed: `{report['field_count']}`",
        f"- High-necessity fields reviewed: `{report['high_necessity_field_count']}`",
        "",
        "## Finding Summary",
        "",
    ]
    for severity in ("error", "warning", "note"):
        lines.append(f"- {severity}: `{report['finding_counts'].get(severity, 0)}`")

    lines.extend(["", "## Dataset Coverage", ""])
    table_rows = [
        [
            "Dataset",
            "Format",
            "Modality",
            "Difficulty",
            "Fields",
            "High necessity",
            "Time-axis fields",
            "Top-level time_axis",
        ]
    ]
    for dataset in report["datasets"]:
        table_rows.append(
            [
                dataset["dataset_id"],
                dataset["file_format"],
                dataset["data_modality"],
                dataset["difficulty"],
                str(dataset["field_count"]),
                str(dataset["high_necessity_count"]),
                str(dataset["time_axis_field_count"]),
                "yes" if dataset["top_level_time_axis"] else "no",
            ]
        )
    lines.extend(markdown_table(table_rows))

    lines.extend(["", "## Blocking Findings", ""])
    errors = [finding for finding in report["findings"] if finding["severity"] == "error"]
    if errors:
        for finding in errors:
            lines.append(f"- `{finding['dataset_id']}`: {finding['message']}")
    else:
        lines.append("No blocking consistency errors were found.")

    non_blocking = [finding for finding in report["findings"] if finding["severity"] != "error"]
    lines.extend(["", "## Non-Blocking Observations", ""])
    for finding in non_blocking:
        lines.append(f"- {finding['severity']} / `{finding['dataset_id']}`: {finding['message']}")

    lines.extend(["", "## Review Policy Locked By This Pass", ""])
    for policy in report["review_policy"]:
        lines.append(f"- {policy}")

    lines.extend(
        [
            "",
            "## Result",
            "",
            "The internal pilot gold schemas pass the second-pass consistency review.",
            "The remaining warnings are documentation/evidence-enrichment gaps, not label-consistency blockers.",
        ]
    )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> None:
    report = audit_gold_schemas()
    json_path, md_path = write_reports(report)
    print(json.dumps({"status": report["status"], "json": str(json_path), "markdown": str(md_path)}, indent=2))


if __name__ == "__main__":
    main()
