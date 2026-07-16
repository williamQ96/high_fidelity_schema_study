from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path, PurePosixPath
import re
from typing import Any, Dict, Optional

import numpy as np

from .extractors.base import ExtractionRequest
from .extractors.registry import extract_path
from .zarr_cross_parser import collect_cross_parser_metadata


ROOT = Path(__file__).resolve().parent
CORPUS_ROOT = ROOT / "testdata" / "zarr_phase14c_external"
MANIFEST_PATH = CORPUS_ROOT / "manifest.json"
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "experiments" / "phase14c_zarr_external_conformance"
ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
METADATA_NAMES = {".zgroup", ".zarray", ".zattrs", ".zmetadata", "zarr.json"}
SOURCE_REQUIRED_KEYS = {
    "source_kind",
    "upstream",
    "version",
    "license",
    "source_url",
    "generation_method",
    "usage_note",
}


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


def _normalize(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            value = value.item()
        except ValueError:
            pass
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def _normalize_dtype(value: Any) -> Any:
    if isinstance(value, list):
        fields = []
        for item in value:
            if not isinstance(item, list) or len(item) not in {2, 3}:
                return _normalize(value)
            name = tuple(item[0]) if isinstance(item[0], list) else item[0]
            if len(item) == 2:
                fields.append((name, _normalize_dtype(item[1])))
            else:
                fields.append((name, _normalize_dtype(item[1]), tuple(item[2])))
        dtype = np.dtype(fields)
    else:
        dtype = np.dtype(value)
    return _normalize(dtype.descr if dtype.names else dtype.str)


def _field_map(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {field["field_path"]: field for field in schema.get("fields", [])}


def _analysis_map(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        item["field_path"]: item
        for item in schema.get("metadata", {}).get("zarr_analysis", {}).get("arrays", [])
    }


def _metadata_source(source: str) -> bool:
    return PurePosixPath(source.split("#", 1)[0]).name in METADATA_NAMES


def _evidence_checks(schema: Dict[str, Any]) -> list[bool]:
    checks = [bool(field.get("source_evidence")) for field in schema.get("fields", [])]
    checks.extend(bool(group.get("source_evidence")) for group in schema.get("groups", []))
    analysis = schema.get("metadata", {}).get("zarr_analysis", {})
    for array in analysis.get("arrays", []):
        for key in ("dimension_claim", "coordinate_role_claim", "unit_claim"):
            claim = array.get(key, {})
            if claim.get("state") in {"supported", "derived"}:
                checks.append(bool(claim.get("evidence_refs")))
    checks.extend(bool(gap.get("evidence_refs")) for gap in analysis.get("compatibility_gaps", []))
    return checks


def _canonical_checks(case: Dict[str, Any], outcome: Dict[str, Any], portable: bool) -> Dict[str, bool]:
    schema = outcome.get("schema") or {}
    fields = _field_map(schema)
    issue_codes = {item.get("code") for item in outcome.get("issues", [])}
    gap_codes = {
        item.get("code")
        for item in schema.get("metadata", {}).get("zarr_analysis", {}).get("compatibility_gaps", [])
    }
    metadata = schema.get("metadata", {})
    evidence_sources = [
        item.get("source", "")
        for entity in [*schema.get("fields", []), *schema.get("groups", [])]
        for item in entity.get("source_evidence", [])
    ]
    metadata_only = not schema or bool(
        metadata.get("chunk_payloads_read") is False
        and metadata.get("store_inventory", {}).get("payload_bytes_read") == 0
        and metadata.get("value_observation", {}).get("state") == "unknown"
        and "deterministic_profile" not in metadata
        and all(_metadata_source(item) for item in metadata.get("documents_discovered", []))
        and all(_metadata_source(item) for item in evidence_sources)
    )
    unknowns = all(
        fields.get(path, {}).get("logical_type") == "unknown"
        and fields.get(path, {}).get("semantic_type") == "unknown"
        for path in case.get("expected_unknown_fields", [])
    )
    no_time_promotion = not schema or metadata.get("time_series", {}).get("time_axis") is None
    source_documented = SOURCE_REQUIRED_KEYS.issubset(case.get("source", {}))
    if case.get("source", {}).get("source_kind") == "external_public_sdist":
        source_documented = source_documented and bool(case["source"].get("source_sha256"))
    return {
        "status": outcome.get("status") == case["expected_status"],
        "issues": set(case.get("expected_issue_codes", [])).issubset(issue_codes),
        "gaps": set(case.get("expected_gap_codes", [])).issubset(gap_codes),
        "unknowns": unknowns,
        "evidence": all(_evidence_checks(schema)),
        "metadata_only": metadata_only,
        "no_time_promotion": no_time_promotion,
        "source_documented": source_documented,
        "portable": portable,
    }


def _canonical_array_metadata(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        path: {
            "dtype": _normalize_dtype(item["array_metadata"]["dtype"]),
            "shape": item["array_metadata"]["shape"],
            "chunks": item["array_metadata"]["chunks"],
            "compressor": _normalize(item["array_metadata"]["compressor"]),
            "fill_value": _normalize(item["array_metadata"]["fill_value"]),
            "order": item["array_metadata"]["order"],
            "filters": _normalize(item["array_metadata"]["filters"]),
        }
        for path, item in _analysis_map(schema).items()
    }


def _compare_zarr(schema: Dict[str, Any], parsed: Dict[str, Any], expected_open: bool) -> list[Dict[str, Any]]:
    differences: list[Dict[str, Any]] = []
    if not parsed.get("available"):
        return [{"parser": "zarr", "kind": "not_assessed", "detail": parsed.get("reason")}]
    if parsed.get("status") != "success":
        if expected_open:
            differences.append({"parser": "zarr", "kind": "unexpected_open_failure", "detail": parsed.get("error_type")})
        return differences
    if not expected_open:
        return [{"parser": "zarr", "kind": "unexpected_open_success"}]

    canonical = _canonical_array_metadata(schema)
    other = parsed.get("arrays", {})
    if set(canonical) != set(other):
        differences.append(
            {
                "parser": "zarr",
                "kind": "array_set_difference",
                "canonical": sorted(canonical),
                "cross_parser": sorted(other),
            }
        )
    for path in sorted(set(canonical) & set(other)):
        for key in ("dtype", "shape", "chunks", "compressor", "fill_value", "order", "filters"):
            canonical_value = _normalize(canonical[path].get(key))
            parsed_value = _normalize(other[path].get(key))
            if canonical_value == parsed_value:
                continue
            if (
                key == "compressor"
                and isinstance(canonical_value, dict)
                and isinstance(parsed_value, dict)
                and parsed_value.get("blocksize") == 0
                and {name: value for name, value in parsed_value.items() if name != "blocksize"} == canonical_value
            ):
                kind = "parser_default_materialization"
            elif (
                key == "fill_value"
                and isinstance(canonical[path].get("dtype"), list)
                and isinstance(canonical_value, str)
                and isinstance(parsed_value, list)
            ):
                kind = "encoded_fill_value_interpretation"
            else:
                kind = "physical_metadata_difference"
            differences.append({"parser": "zarr", "kind": kind, "field_path": path, "property": key})
    return differences


def _compare_xarray(schema: Dict[str, Any], parsed: Dict[str, Any], group: Optional[str]) -> list[Dict[str, Any]]:
    if not parsed.get("available"):
        return [{"parser": "xarray", "kind": "not_assessed", "detail": parsed.get("reason")}]
    if parsed.get("status") != "success":
        return [{"parser": "xarray", "kind": "unexpected_open_failure", "detail": parsed.get("error_type")}]
    prefix = f"{group}/" if group else ""
    analyses = _analysis_map(schema)
    canonical = {
        path.removeprefix(prefix): {
            "dimensions": item.get("dimensions", []),
            "shape": item.get("array_metadata", {}).get("shape", []),
        }
        for path, item in analyses.items()
        if not prefix or path.startswith(prefix)
    }
    other = parsed.get("variables", {})
    differences: list[Dict[str, Any]] = []
    if set(canonical) != set(other):
        differences.append(
            {
                "parser": "xarray",
                "kind": "variable_set_difference",
                "canonical": sorted(canonical),
                "cross_parser": sorted(other),
            }
        )
    for name in sorted(set(canonical) & set(other)):
        for key in ("dimensions", "shape"):
            if canonical[name].get(key) != other[name].get(key):
                differences.append({"parser": "xarray", "kind": "structure_difference", "variable": name, "property": key})
    return differences


def evaluate_phase14c(
    manifest_path: Path = MANIFEST_PATH,
    *,
    enable_cross_parser: bool = False,
) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases: list[Dict[str, Any]] = []
    classification_counts: Counter[str] = Counter()
    classification_passes: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    difference_counts: Counter[str] = Counter()
    evidence_hits = 0
    evidence_total = 0
    unsupported_promotion_count = 0
    zarr_assessed = zarr_conformant = 0
    xarray_assessed = xarray_conformant = 0

    for case in manifest["cases"]:
        store = (CORPUS_ROOT / case["store"]).resolve()
        raw_outcome = extract_path(ExtractionRequest(str(store), resource_kind="directory_store")).to_dict()
        portable = not _has_absolute_path(raw_outcome)
        outcome = _portable_paths(raw_outcome)
        checks = _canonical_checks(case, outcome, portable)
        canonical_match = all(checks.values())
        classification_counts[case["classification"]] += 1
        classification_passes[case["classification"]] += int(canonical_match)
        source_counts[case["source"]["source_kind"]] += 1
        schema = outcome.get("schema") or {}
        evidence = _evidence_checks(schema)
        evidence_hits += sum(evidence)
        evidence_total += len(evidence)
        if not checks["unknowns"] or not checks["no_time_promotion"]:
            unsupported_promotion_count += 1

        cross_parser = (
            collect_cross_parser_metadata(store, case.get("cross_parser", {}))
            if enable_cross_parser
            else {"role": "dev_only_supporting_evidence", "enabled": False, "value_reads": 0}
        )
        differences: list[Dict[str, Any]] = []
        if enable_cross_parser and "zarr" in cross_parser:
            parsed = cross_parser["zarr"]
            expected_open = case.get("cross_parser", {}).get("expected_zarr_open", True)
            zarr_differences = _compare_zarr(schema, parsed, expected_open)
            differences.extend(zarr_differences)
            if parsed.get("available") and not any(item["kind"] == "not_assessed" for item in zarr_differences):
                zarr_assessed += 1
                zarr_conformant += int(not zarr_differences)
        if enable_cross_parser and "xarray" in cross_parser:
            parsed = cross_parser["xarray"]
            xarray_differences = _compare_xarray(schema, parsed, case.get("cross_parser", {}).get("group"))
            differences.extend(xarray_differences)
            if parsed.get("available") and not any(item["kind"] == "not_assessed" for item in xarray_differences):
                xarray_assessed += 1
                xarray_conformant += int(not xarray_differences)
        difference_counts.update(item["kind"] for item in differences)

        cases.append(
            {
                "case_id": case["case_id"],
                "store": case["store"],
                "classification": case["classification"],
                "source": case["source"],
                "expected_features": case["expected_features"],
                "expected_status": case["expected_status"],
                "actual_status": outcome["status"],
                "canonical_checks": checks,
                "canonical_expectations_met": canonical_match,
                "cross_parser": _portable_paths(cross_parser),
                "conformance_differences": differences,
                "outcome": outcome,
            }
        )

    true_bug_count = sum(not case["canonical_expectations_met"] for case in cases)
    explained_difference_kinds = {
        "parser_default_materialization",
        "encoded_fill_value_interpretation",
    }
    return {
        "experiment_id": manifest["experiment_id"],
        "manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "corpus_claim_boundary": manifest["corpus_claim_boundary"],
        "generation_environment": manifest["generation_environment"],
        "chunk_payload_policy": manifest["chunk_payload_policy"],
        "metrics": {
            "case_count": len(cases),
            "external_public_case_count": source_counts["external_public_sdist"],
            "library_produced_case_count": source_counts["library_produced"],
            "library_derived_edge_count": source_counts["library_derived_edge"],
            "supported_compatibility_rate": safe_ratio(classification_passes["supported"], classification_counts["supported"]),
            "structured_abstention_quality": safe_ratio(
                classification_passes["structured_abstention"],
                classification_counts["structured_abstention"],
            ),
            "unsupported_feature_visibility": safe_ratio(
                classification_passes["unsupported_feature"],
                classification_counts["unsupported_feature"],
            ),
            "malformed_edge_quality": safe_ratio(
                classification_passes["malformed_edge"],
                classification_counts["malformed_edge"],
            ),
            "source_documentation_completeness": safe_ratio(
                sum(case["canonical_checks"]["source_documented"] for case in cases),
                len(cases),
            ),
            "evidence_coverage": safe_ratio(evidence_hits, evidence_total),
            "path_portability_accuracy": safe_ratio(sum(case["canonical_checks"]["portable"] for case in cases), len(cases)),
            "chunk_payload_non_claim_rate": safe_ratio(sum(case["canonical_checks"]["metadata_only"] for case in cases), len(cases)),
            "unsupported_promotion_count": unsupported_promotion_count,
            "true_bug_count": true_bug_count,
            "zarr_conformance_assessed_count": zarr_assessed,
            "zarr_physical_conformance_rate": safe_ratio(zarr_conformant, zarr_assessed),
            "xarray_conformance_assessed_count": xarray_assessed,
            "xarray_structure_conformance_rate": safe_ratio(xarray_conformant, xarray_assessed),
            "conformance_difference_count": sum(difference_counts.values()),
            "unexplained_conformance_difference_count": sum(
                count
                for kind, count in difference_counts.items()
                if kind not in explained_difference_kinds
            ),
        },
        "classification_summary": {
            key: {"case_count": classification_counts[key], "expectations_met": classification_passes[key]}
            for key in sorted(classification_counts)
        },
        "source_summary": dict(sorted(source_counts.items())),
        "conformance_difference_summary": dict(sorted(difference_counts.items())),
        "cases": cases,
        "notes": [
            "Cross-parser results are dev-only supporting evidence and do not override canonical extraction outcomes.",
            "No canonical or cross-parser path reads array values.",
            "The public-source subset retains metadata documents only; official fixture chunk payloads are excluded.",
            "Library-produced stores are generated with pinned versions and stripped of any eagerly written non-metadata objects.",
            "Zarr v3, remote stores, full Xarray reconstruction, and value-level profiling remain out of scope.",
        ],
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Phase 14C External/Library Zarr Conformance",
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
    lines.extend(["", "## Sources", ""])
    for source_kind, count in report["source_summary"].items():
        lines.append(f"- `{source_kind}`: {count}")
    lines.extend(["", "## Conformance Differences", ""])
    if report["conformance_difference_summary"]:
        for kind, count in report["conformance_difference_summary"].items():
            lines.append(f"- `{kind}`: {count}")
    else:
        lines.append("- No differences were observed in the assessed metadata properties.")
    for classification in ("supported", "structured_abstention", "unsupported_feature", "malformed_edge"):
        lines.extend(
            [
                "",
                f"## {classification.replace('_', ' ').title()}",
                "",
                "| Case | Source | Status | Canonical | Differences |",
                "| --- | --- | --- | --- | ---: |",
            ]
        )
        for case in report["cases"]:
            if case["classification"] == classification:
                lines.append(
                    f"| {case['case_id']} | {case['source']['source_kind']} | {case['actual_status']} | "
                    f"{'pass' if case['canonical_expectations_met'] else 'bug'} | {len(case['conformance_differences'])} |"
                )
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


def write_phase14c_artifacts(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report: Optional[Dict[str, Any]] = None,
    *,
    enable_cross_parser: bool = False,
) -> Dict[str, Any]:
    report = report or evaluate_phase14c(enable_cross_parser=enable_cross_parser)
    outcomes_root = output_root / "outcomes"
    outcomes_root.mkdir(parents=True, exist_ok=True)
    for case in report["cases"]:
        (outcomes_root / f"{case['case_id']}.json").write_text(
            json.dumps(
                {
                    "case_id": case["case_id"],
                    "classification": case["classification"],
                    "source": case["source"],
                    "canonical_outcome": case["outcome"],
                    "cross_parser": case["cross_parser"],
                    "conformance_differences": case["conformance_differences"],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    summary = {key: value for key, value in report.items() if key != "cases"}
    summary["cases"] = [
        {key: value for key, value in case.items() if key not in {"outcome", "cross_parser"}}
        for case in report["cases"]
    ]
    (output_root / "report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output_root / "report.md").write_text(render_markdown(report), encoding="utf-8")
    return report
