from __future__ import annotations

from collections import Counter
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Dict, Optional

from .extractors.base import ExtractionRequest
from .extractors.registry import extract_path


ROOT = Path(__file__).resolve().parent
CORPUS_ROOT = ROOT / "testdata" / "zarr_phase14b_compatibility"
MANIFEST_PATH = CORPUS_ROOT / "manifest.json"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "experiments" / "phase14b_zarr_compatibility"
ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
METADATA_NAMES = {".zgroup", ".zarray", ".zattrs", ".zmetadata", "zarr.json"}


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


def _metadata_source(source: str) -> bool:
    base = source.split("#", 1)[0]
    return PurePosixPath(base).name in METADATA_NAMES


def _field_map(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {field["field_path"]: field for field in schema.get("fields", [])}


def _analysis_map(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        item["field_path"]: item
        for item in schema.get("metadata", {}).get("zarr_analysis", {}).get("arrays", [])
    }


def _evidence_entities(schema: Dict[str, Any]) -> list[bool]:
    present = [bool(field.get("source_evidence")) for field in schema.get("fields", [])]
    present.extend(bool(group.get("source_evidence")) for group in schema.get("groups", []))
    dimensions = schema.get("metadata", {}).get("dimensions", {})
    present.extend(
        bool(dimension.get("source_evidence"))
        for dimension in dimensions.values()
        if dimension.get("state") == "supported"
    )
    analysis = schema.get("metadata", {}).get("zarr_analysis", {})
    for array in analysis.get("arrays", []):
        for key in ("dimension_claim", "coordinate_role_claim", "unit_claim"):
            claim = array.get(key, {})
            if claim.get("state") in {"supported", "derived"}:
                present.append(bool(claim.get("evidence_refs")))
    for claim in analysis.get("calendar_claims", {}).values():
        if claim.get("state") in {"supported", "derived"}:
            present.append(bool(claim.get("evidence_refs")))
    present.extend(bool(gap.get("evidence_refs")) for gap in analysis.get("compatibility_gaps", []))
    return present


def _case_matches(
    case: Dict[str, Any],
    outcome: Dict[str, Any],
    portable: bool,
) -> Dict[str, Any]:
    schema = outcome.get("schema") or {}
    fields = _field_map(schema)
    analyses = _analysis_map(schema)
    expected_fields = set(case.get("expected_fields", []))
    actual_fields = set(fields)
    expected_groups = set(case.get("expected_groups", []))
    actual_groups = {group.get("path") for group in schema.get("groups", [])}
    issue_codes = {issue.get("code") for issue in outcome.get("issues", [])}
    gaps = schema.get("metadata", {}).get("zarr_analysis", {}).get("compatibility_gaps", [])
    gap_codes = {gap.get("code") for gap in gaps}

    physical_matches: Dict[str, bool] = {}
    for field_path, expected in case.get("expected_physical", {}).items():
        actual = analyses.get(field_path, {}).get("array_metadata", {})
        for key, value in expected.items():
            physical_matches[f"{field_path}:{key}"] = actual.get(key) == value

    coordinate_matches: Dict[str, bool] = {}
    for field_path in case.get("expected_coordinate_fields", []):
        claim = analyses.get(field_path, {}).get("coordinate_role_claim", {})
        coordinate_matches[field_path] = claim.get("state") == "supported" and bool(claim.get("value"))
    for field_path in case.get("expected_not_coordinate_fields", []):
        claim = analyses.get(field_path, {}).get("coordinate_role_claim", {})
        coordinate_matches[f"{field_path}:not_coordinate"] = claim.get("state") == "unknown"

    unknown_matches = {
        field_path: bool(
            fields.get(field_path, {}).get("logical_type") == "unknown"
            and fields.get(field_path, {}).get("semantic_type") == "unknown"
        )
        for field_path in case.get("expected_unknown_fields", [])
    }

    metadata = schema.get("metadata", {})
    inventory = metadata.get("store_inventory", {})
    evidence_sources = [
        item.get("source", "")
        for entity in [*schema.get("fields", []), *schema.get("groups", [])]
        for item in entity.get("source_evidence", [])
    ]
    chunk_safe = not schema or bool(
        metadata.get("chunk_payloads_read") is False
        and inventory.get("payload_bytes_read") == 0
        and all(_metadata_source(item) for item in metadata.get("documents_discovered", []))
        and all(_metadata_source(source) for source in evidence_sources)
    )
    value_abstained = not schema or bool(
        metadata.get("value_observation", {}).get("state") == "unknown"
        and metadata.get("value_observation", {}).get("reason_code") == "chunk_payloads_not_read"
        and "deterministic_profile" not in metadata
    )
    pruned_match = (
        inventory.get("pruned_array_directory_count", 0)
        >= case.get("expected_pruned_array_directories_min", 0)
    )

    checks = {
        "status": outcome.get("status") == case["expected_status"],
        "fields": actual_fields == expected_fields,
        "groups": expected_groups.issubset(actual_groups),
        "physical": all(physical_matches.values()),
        "issues": set(case.get("expected_issue_codes", [])).issubset(issue_codes),
        "gaps": set(case.get("expected_gap_codes", [])).issubset(gap_codes),
        "coordinates": all(coordinate_matches.values()),
        "unknowns": all(unknown_matches.values()),
        "evidence": all(_evidence_entities(schema)),
        "portable": portable,
        "chunk_safe": chunk_safe,
        "value_abstained": value_abstained,
        "array_walk_pruned": pruned_match,
    }
    return {
        "checks": checks,
        "physical_matches": physical_matches,
        "coordinate_matches": coordinate_matches,
        "unknown_matches": unknown_matches,
        "issue_codes": sorted(code for code in issue_codes if code),
        "gap_codes": sorted(code for code in gap_codes if code),
        "compatibility_gaps": gaps,
        "actual_fields": sorted(actual_fields),
        "all_expectations_met": all(checks.values()),
    }


def evaluate_phase14b(manifest_path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases: list[Dict[str, Any]] = []
    classification_counts: Counter[str] = Counter()
    classification_passes: Counter[str] = Counter()
    gap_counts: Counter[str] = Counter()
    evidence_hits = 0
    evidence_total = 0
    unsupported_promotion_count = 0

    for case in manifest["cases"]:
        raw_outcome = extract_path(
            ExtractionRequest(
                str((CORPUS_ROOT / case["store"]).resolve()),
                resource_kind="directory_store",
            )
        ).to_dict()
        portable = not _has_absolute_path(raw_outcome)
        outcome = _portable_paths(raw_outcome)
        match = _case_matches(case, outcome, portable)
        classification = case["classification"]
        classification_counts[classification] += 1
        classification_passes[classification] += int(match["all_expectations_met"])
        gap_counts.update(match["gap_codes"])

        schema = outcome.get("schema") or {}
        evidence = _evidence_entities(schema)
        evidence_hits += sum(evidence)
        evidence_total += len(evidence)
        analyses = _analysis_map(schema)
        for field_path in case.get("expected_unknown_fields", []):
            field = _field_map(schema).get(field_path, {})
            if field and (
                field.get("logical_type") != "unknown"
                or field.get("semantic_type") != "unknown"
            ):
                unsupported_promotion_count += 1
        for field_path in case.get("expected_not_coordinate_fields", []):
            if analyses.get(field_path, {}).get("coordinate_role_claim", {}).get("state") != "unknown":
                unsupported_promotion_count += 1
        if schema.get("metadata", {}).get("time_series", {}).get("time_axis") is not None:
            unsupported_promotion_count += 1

        cases.append(
            {
                "case_id": case["case_id"],
                "store": case["store"],
                "producer_profile": case["producer_profile"],
                "classification": classification,
                "expected_status": case["expected_status"],
                "actual_status": outcome["status"],
                **match,
                "outcome": outcome,
            }
        )

    total_passes = sum(case["all_expectations_met"] for case in cases)
    true_bug_count = len(cases) - total_passes
    return {
        "experiment_id": manifest["experiment_id"],
        "manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "corpus_origin": manifest["corpus_origin"],
        "corpus_claim_boundary": manifest["corpus_claim_boundary"],
        "metrics": {
            "case_count": len(cases),
            "supported_case_count": classification_counts["supported"],
            "supported_compatibility_rate": safe_ratio(
                classification_passes["supported"],
                classification_counts["supported"],
            ),
            "unsupported_feature_visibility": safe_ratio(
                classification_passes["unsupported_feature"],
                classification_counts["unsupported_feature"],
            ),
            "malformed_failure_quality": safe_ratio(
                classification_passes["malformed_failure"],
                classification_counts["malformed_failure"],
            ),
            "structured_abstention_quality": safe_ratio(
                classification_passes["structured_abstention"],
                classification_counts["structured_abstention"],
            ),
            "overall_expectation_match": safe_ratio(total_passes, len(cases)),
            "evidence_coverage": safe_ratio(evidence_hits, evidence_total),
            "path_portability_accuracy": safe_ratio(
                sum(case["checks"]["portable"] for case in cases),
                len(cases),
            ),
            "chunk_payload_non_claim_rate": safe_ratio(
                sum(case["checks"]["chunk_safe"] for case in cases),
                len(cases),
            ),
            "value_observation_abstention_accuracy": safe_ratio(
                sum(case["checks"]["value_abstained"] for case in cases),
                len(cases),
            ),
            "compatibility_gap_count": sum(gap_counts.values()),
            "unsupported_promotion_count": unsupported_promotion_count,
            "true_bug_count": true_bug_count,
        },
        "classification_summary": {
            key: {
                "case_count": classification_counts[key],
                "expectations_met": classification_passes[key],
            }
            for key in sorted(classification_counts)
        },
        "compatibility_gap_summary": dict(sorted(gap_counts.items())),
        "cases": cases,
        "notes": [
            "The corpus reconstructs common local Zarr v2 producer layouts; it is not a downloaded representative ecosystem sample.",
            "Chunk keys contain dummy invalid bytes and are never used to create schema or value-level claims.",
            "Unsupported features and malformed stores are successful compatibility observations when surfaced as expected.",
            "Remote stores, Zarr v3 extraction, chunk decoding, and full Xarray reconstruction remain out of scope.",
        ],
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Phase 14B Zarr Compatibility Validation",
        "",
        report["corpus_claim_boundary"],
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for metric, value in report["metrics"].items():
        lines.append(f"| {metric} | {value:.4f} |" if isinstance(value, float) else f"| {metric} | {value} |")
    lines.extend(["", "## Classification Summary", "", "| Classification | Cases | Expectations Met |", "| --- | ---: | ---: |"])
    for name, summary in report["classification_summary"].items():
        lines.append(f"| {name} | {summary['case_count']} | {summary['expectations_met']} |")
    lines.extend(["", "## Compatibility Gaps", ""])
    if report["compatibility_gap_summary"]:
        for code, count in report["compatibility_gap_summary"].items():
            lines.append(f"- `{code}`: {count}")
    else:
        lines.append("- No compatibility gaps were surfaced.")
    for classification in ("supported", "unsupported_feature", "malformed_failure", "structured_abstention"):
        lines.extend(
            [
                "",
                f"## {classification.replace('_', ' ').title()}",
                "",
                "| Case | Profile | Status | Expectations |",
                "| --- | --- | --- | --- |",
            ]
        )
        for case in report["cases"]:
            if case["classification"] == classification:
                result = "pass" if case["all_expectations_met"] else "bug"
                lines.append(
                    f"| {case['case_id']} | {case['producer_profile']} | {case['actual_status']} | {result} |"
                )
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


def write_phase14b_artifacts(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    report = report or evaluate_phase14b()
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
