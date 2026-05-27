from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
DOCS_ROOT = ROOT / "docs"

FREEZE_PATH = DOCS_ROOT / "benchmark_freeze_2026-05-04.json"
INTERNAL_BASELINE_PATH = DATA_ROOT / "derived" / "internal_baseline_report.json"
DERIVED_MANIFEST_PATH = DATA_ROOT / "derived" / "derived_manifest.json"
RETRIEVAL_REPORT_PATH = DATA_ROOT / "retrieval" / "external_candidate_pool" / "retrieval_report.json"
SEMANTIC_MERGE_REPORT_PATH = DATA_ROOT / "semantic_merged" / "semantic_merge_report.json"
RELATIONSHIP_PROFILE_PATH = DATA_ROOT / "derived" / "internal_relationship_profile.json"
PROVENANCE_MANIFEST_PATH = DATA_ROOT / "derived" / "provenance_manifest.json"
QRELS_PATH = DATA_ROOT / "retrieval" / "external_candidate_pool" / "qrels.json"
SCHEMA_CLAIM_MODEL_PATH = DOCS_ROOT / "schema_claim_model.md"
BENCHMARK_CARD_PATH = DOCS_ROOT / "benchmark_card_2026-05-15.md"

REPORT_ID = "paper-result-tables-2026-05-15"
REPORT_JSON_PATH = DOCS_ROOT / "paper_result_tables_2026-05-15.json"
REPORT_MD_PATH = DOCS_ROOT / "paper_result_tables_2026-05-15.md"


SCHEMA_SOURCE_LABELS = {
    "metadata_only": "metadata only",
    "readme_only": "README text only",
    "schema_enhanced": "deterministic schema, compatibility alias",
    "schema_enhanced_deterministic": "deterministic schema",
    "schema_enhanced_semantic_merged": "semantic-merged schema",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def round4(value: float) -> float:
    return round(value, 4)


def safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round4(numerator / denominator)


def metric_delta(current: Dict[str, float], baseline: Dict[str, float], metric: str) -> float:
    return round4(current[metric] - baseline[metric])


def build_benchmark_slice_table(freeze: Dict[str, Any]) -> List[Dict[str, Any]]:
    retrieval_systems = freeze["retrieval_protocol"]["systems"]
    locked_subsets = freeze["locked_regression_subsets"]
    return [
        {
            "measure": "Internal pilot datasets",
            "value": freeze["internal_pilot"]["dataset_count"],
            "source": freeze["internal_pilot"]["source_manifest"],
        },
        {
            "measure": "External retrieval candidate files",
            "value": freeze["external_retrieval_pool"]["entry_count"],
            "source": freeze["external_retrieval_pool"]["source_manifest"],
        },
        {
            "measure": "Promoted external target files",
            "value": freeze["external_retrieval_pool"]["target_count"],
            "source": freeze["external_retrieval_pool"]["source_manifest"],
        },
        {
            "measure": "External distractor files",
            "value": freeze["external_retrieval_pool"]["distractor_count"],
            "source": freeze["external_retrieval_pool"]["source_manifest"],
        },
        {
            "measure": "Current retrieval systems",
            "value": len(retrieval_systems),
            "source": freeze["retrieval_protocol"]["artifact_manifest"],
        },
        {
            "measure": "Locked external field-subset regression groups",
            "value": len(locked_subsets),
            "source": FREEZE_PATH.relative_to(ROOT).as_posix(),
        },
    ]


def build_internal_baseline_tables(internal_baseline: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    aggregate = internal_baseline["aggregate"]
    aggregate_table = [
        {"metric": metric, "value": value}
        for metric, value in aggregate["metrics"].items()
    ]

    by_category_table = []
    for category, metrics in aggregate["by_category"].items():
        by_category_table.append(
            {
                "category": category,
                "physical_completeness": metrics["physical_completeness"],
                "physical_accuracy": metrics["physical_accuracy"],
                "logical_accuracy": metrics["logical_accuracy"],
                "semantic_accuracy": metrics["semantic_accuracy"],
                "unit_accuracy": metrics["unit_accuracy"],
                "time_axis_accuracy": metrics["time_axis_accuracy"],
            }
        )

    error_modes = [
        {"error_mode": mode, "count": count}
        for mode, count in aggregate["error_modes"]["counts"].items()
    ]
    return {
        "internal_baseline_aggregate": aggregate_table,
        "internal_baseline_by_category": by_category_table,
        "internal_error_modes": error_modes,
    }


def build_retrieval_tables(retrieval_report: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    metrics_table = []
    artifact_metrics: Dict[str, Dict[str, float]] = {}
    for artifact in retrieval_report["artifacts"]:
        metrics = artifact["metrics"]
        artifact_metrics[artifact["artifact_name"]] = metrics
        metrics_table.append(
            {
                "system": artifact["artifact_name"],
                "schema_source": SCHEMA_SOURCE_LABELS.get(artifact["artifact_name"], "unknown"),
                "query_count": artifact["query_count"],
                "recall_at_1": metrics["recall_at_1"],
                "recall_at_3": metrics["recall_at_3"],
                "precision_at_1": metrics["precision_at_1"],
                "precision_at_3": metrics["precision_at_3"],
                "mrr": metrics["mrr"],
                "ndcg_at_3": metrics["ndcg_at_3"],
            }
        )

    metadata_metrics = artifact_metrics["metadata_only"]
    gain_table = []
    for row in metrics_table:
        if row["system"] == "metadata_only":
            continue
        metrics = artifact_metrics[row["system"]]
        gain_table.append(
            {
                "system": row["system"],
                "recall_at_1_delta": metric_delta(metrics, metadata_metrics, "recall_at_1"),
                "recall_at_3_delta": metric_delta(metrics, metadata_metrics, "recall_at_3"),
                "precision_at_1_delta": metric_delta(metrics, metadata_metrics, "precision_at_1"),
                "mrr_delta": metric_delta(metrics, metadata_metrics, "mrr"),
                "ndcg_at_3_delta": metric_delta(metrics, metadata_metrics, "ndcg_at_3"),
            }
        )
    return {
        "retrieval_metrics": metrics_table,
        "retrieval_gain_vs_metadata": gain_table,
    }


def build_semantic_merge_tables(report: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    aggregate = report["aggregate"]
    aggregate_table = [
        {
            "dataset_count": report["dataset_count"],
            "improved_dataset_count": aggregate["improved_dataset_count"],
            "accepted_for_merge_count": aggregate["accepted_for_merge_count"],
            "conflict_count": aggregate["conflict_count"],
            "mean_logical_accuracy_delta": aggregate["mean_logical_accuracy_delta"],
        }
    ]

    dataset_table = []
    for item in report["datasets"]:
        baseline = item["baseline"]
        merged = item["merged"]
        dataset_table.append(
            {
                "dataset_id": item["dataset_id"],
                "accepted_merges": merged["accepted_for_merge_count"],
                "conflicts": item["conflict_count"],
                "baseline_logical_accuracy": baseline["logical_accuracy"],
                "merged_logical_accuracy": merged["logical_accuracy"],
                "logical_accuracy_delta": round4(merged["logical_accuracy"] - baseline["logical_accuracy"]),
                "baseline_semantic_accuracy": baseline["semantic_accuracy"],
                "merged_semantic_accuracy": merged["semantic_accuracy"],
                "semantic_accuracy_delta": round4(merged["semantic_accuracy"] - baseline["semantic_accuracy"]),
                "baseline_unit_accuracy": baseline["unit_accuracy"],
                "merged_unit_accuracy": merged["unit_accuracy"],
                "unit_accuracy_delta": round4(merged["unit_accuracy"] - baseline["unit_accuracy"]),
            }
        )
    return {
        "semantic_merge_aggregate": aggregate_table,
        "semantic_merge_dataset_delta": dataset_table,
    }


def load_derived_schemas(derived_manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        load_json(DATA_ROOT / entry["derived_schema_file"])
        for entry in derived_manifest["datasets"]
    ]


def build_evidence_adequacy_tables(
    derived_schemas: List[Dict[str, Any]],
    semantic_merge_report: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    fields = [
        field
        for schema in derived_schemas
        for field in schema.get("fields", [])
    ]
    total_fields = len(fields)
    fields_with_source_evidence = sum(1 for field in fields if field.get("source_evidence"))
    fields_with_confidence = sum(1 for field in fields if field.get("confidence") is not None)
    fields_with_uncertainty_reason = sum(1 for field in fields if field.get("uncertainty_reason"))

    evidence_type_counts: Counter[str] = Counter()
    total_evidence_records = 0
    unit_claim_count = 0
    unit_claims_with_unit_evidence = 0
    explicit_metadata_unit_claims = 0
    name_inferred_unit_claims = 0
    for field in fields:
        source_evidence = field.get("source_evidence", [])
        total_evidence_records += len(source_evidence)
        field_evidence_types = {evidence.get("evidence_type") for evidence in source_evidence}
        for evidence_type in field_evidence_types:
            if evidence_type:
                evidence_type_counts[evidence_type] += 1
        if field.get("unit") is not None:
            unit_claim_count += 1
            if {"hdf5_attribute", "column_name_unit_hint"} & field_evidence_types:
                unit_claims_with_unit_evidence += 1
            if "hdf5_attribute" in field_evidence_types:
                explicit_metadata_unit_claims += 1
            if "column_name_unit_hint" in field_evidence_types:
                name_inferred_unit_claims += 1

    annotated_fields = []
    for dataset in semantic_merge_report["datasets"]:
        for field in dataset["merged"].get("per_field", []):
            annotation = field.get("semantic_annotation")
            if annotation is not None:
                annotated_fields.append(annotation)

    accepted_annotations = [
        annotation
        for annotation in annotated_fields
        if annotation.get("accepted_for_merge") is True
    ]
    accepted_with_support = [
        annotation
        for annotation in accepted_annotations
        if annotation.get("supporting_evidence")
    ]
    unsupported_accepted = len(accepted_annotations) - len(accepted_with_support)

    summary_table = [
        {
            "metric": "Derived fields with source evidence",
            "numerator": fields_with_source_evidence,
            "denominator": total_fields,
            "value": safe_ratio(fields_with_source_evidence, total_fields),
            "interpretation": "Every deterministic field should be auditable back to file evidence.",
        },
        {
            "metric": "Derived fields with confidence",
            "numerator": fields_with_confidence,
            "denominator": total_fields,
            "value": safe_ratio(fields_with_confidence, total_fields),
            "interpretation": "Confidence is reported separately from correctness.",
        },
        {
            "metric": "Derived fields with uncertainty reason",
            "numerator": fields_with_uncertainty_reason,
            "denominator": total_fields,
            "value": safe_ratio(fields_with_uncertainty_reason, total_fields),
            "interpretation": "Reasons are attached when the deterministic layer is conservative.",
        },
        {
            "metric": "Unit claims with unit evidence",
            "numerator": unit_claims_with_unit_evidence,
            "denominator": unit_claim_count,
            "value": safe_ratio(unit_claims_with_unit_evidence, unit_claim_count),
            "interpretation": "Units should come from explicit metadata or deterministic name evidence.",
        },
        {
            "metric": "Explicit-metadata unit claims",
            "numerator": explicit_metadata_unit_claims,
            "denominator": unit_claim_count,
            "value": safe_ratio(explicit_metadata_unit_claims, unit_claim_count),
            "interpretation": "HDF5 unit attributes are stronger than name-based unit hints.",
        },
        {
            "metric": "Name-inferred unit claims",
            "numerator": name_inferred_unit_claims,
            "denominator": unit_claim_count,
            "value": safe_ratio(name_inferred_unit_claims, unit_claim_count),
            "interpretation": "CSV suffix units are useful but weaker than explicit metadata.",
        },
        {
            "metric": "Accepted semantic merges with support",
            "numerator": len(accepted_with_support),
            "denominator": len(accepted_annotations),
            "value": safe_ratio(len(accepted_with_support), len(accepted_annotations)),
            "interpretation": "Accepted semantic merge decisions should cite supporting evidence.",
        },
        {
            "metric": "Unsupported accepted semantic merges",
            "numerator": unsupported_accepted,
            "denominator": len(accepted_annotations),
            "value": safe_ratio(unsupported_accepted, len(accepted_annotations)),
            "interpretation": "This should stay at zero under the merge safety policy.",
        },
    ]
    evidence_type_table = [
        {"evidence_type": evidence_type, "field_count": count}
        for evidence_type, count in sorted(evidence_type_counts.items())
    ]
    evidence_type_table.append({"evidence_type": "total_evidence_records", "field_count": total_evidence_records})
    return {
        "evidence_adequacy_summary": summary_table,
        "source_evidence_type_counts": evidence_type_table,
    }


def build_unit_normalization_tables(derived_schemas: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    status_counts: Counter[str] = Counter()
    unit_status_counts: Counter[str] = Counter()
    evidence_basis_counts: Counter[str] = Counter()
    for schema in derived_schemas:
        for field in schema.get("fields", []):
            normalization = field.get("unit_normalization") or {}
            status = normalization.get("status", "missing_status")
            evidence_basis = normalization.get("evidence_basis", "missing_basis")
            status_counts[status] += 1
            if field.get("unit") is not None:
                unit_status_counts[status] += 1
                evidence_basis_counts[evidence_basis] += 1

    status_table = [
        {
            "status": status,
            "field_count": status_counts[status],
            "unit_claim_count": unit_status_counts.get(status, 0),
        }
        for status in sorted(status_counts)
    ]
    basis_table = [
        {"evidence_basis": basis, "unit_claim_count": count}
        for basis, count in sorted(evidence_basis_counts.items())
    ]
    return {
        "unit_normalization_status": status_table,
        "unit_normalization_evidence_basis": basis_table,
    }


def build_provenance_summary_table(provenance_manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"metric": metric, "value": value}
        for metric, value in provenance_manifest["summary"].items()
    ]


def build_qrels_summary_table(qrels: Dict[str, Any]) -> List[Dict[str, Any]]:
    judgments = qrels.get("qrels", [])
    planted_count = sum(1 for item in judgments if item.get("query_source") == "planted")
    high_relevance_count = sum(1 for item in judgments if item.get("relevance_grade") == 2)
    return [
        {"metric": "Qrels schema", "value": qrels.get("qrels_schema")},
        {"metric": "Query count", "value": qrels.get("query_count", 0)},
        {"metric": "Judgment count", "value": qrels.get("judgment_count", 0)},
        {"metric": "Planted judgments", "value": planted_count},
        {"metric": "Highly relevant judgments", "value": high_relevance_count},
        {"metric": "Judgment style", "value": "one positive planted target per query"},
    ]


def build_profile_tables(
    derived_schemas: List[Dict[str, Any]],
    relationship_profile: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    totals = {
        "dataset_count": 0,
        "field_count": 0,
        "fields_with_missing_count": 0,
        "total_missing_cells": 0,
        "identifier_candidate_count": 0,
        "best_identifier_field_count": 0,
    }
    for schema in derived_schemas:
        profile = schema["metadata"]["deterministic_profile"]
        missingness = profile["missingness"]
        identifier_quality = profile["identifier_quality"]
        totals["dataset_count"] += 1
        totals["field_count"] += missingness["field_count"]
        totals["fields_with_missing_count"] += missingness["fields_with_missing_count"]
        totals["total_missing_cells"] += missingness["total_missing_cells"]
        totals["identifier_candidate_count"] += identifier_quality["candidate_count"]
        totals["best_identifier_field_count"] += len(identifier_quality["best_identifier_fields"])
    summary_table = [
        {
            "metric": "Internal datasets with deterministic profile",
            "value": totals["dataset_count"],
            "interpretation": "All frozen internal pilot datasets have profile metadata.",
        },
        {
            "metric": "Derived fields profiled",
            "value": totals["field_count"],
            "interpretation": "Field-level missingness and identifier checks are attached to schemas.",
        },
        {
            "metric": "Fields with sampled missing values",
            "value": totals["fields_with_missing_count"],
            "interpretation": "Missingness is rare in the current synthetic internal slice.",
        },
        {
            "metric": "Total sampled missing cells",
            "value": totals["total_missing_cells"],
            "interpretation": "Counted from deterministic file scans where rows are sampled.",
        },
        {
            "metric": "Identifier candidates",
            "value": totals["identifier_candidate_count"],
            "interpretation": "Fields that look like identifiers by logical or semantic labels.",
        },
        {
            "metric": "Best identifier fields",
            "value": totals["best_identifier_field_count"],
            "interpretation": "Identifier candidates with unique or group-identifier quality.",
        },
        {
            "metric": "Cross-file relationship candidates",
            "value": relationship_profile["relationship_count"],
            "interpretation": "Deterministic candidates only; not asserted joins.",
        },
    ]
    relationship_table = [
        {"relationship_type": relationship_type, "count": count}
        for relationship_type, count in relationship_profile["relationship_counts"].items()
    ]
    return {
        "deterministic_profile_summary": summary_table,
        "deterministic_profile_relationships": relationship_table,
    }


def build_regression_subset_table(freeze: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "subset": subset,
            "field_count": len(fields),
            "fields": ", ".join(fields),
        }
        for subset, fields in freeze["locked_regression_subsets"].items()
    ]


def build_known_limitations_table(freeze: Dict[str, Any]) -> List[Dict[str, str]]:
    return [{"limitation": item} for item in freeze["known_non_final_items"]]


def build_paper_tables() -> Dict[str, Any]:
    freeze = load_json(FREEZE_PATH)
    internal_baseline = load_json(INTERNAL_BASELINE_PATH)
    derived_manifest = load_json(DERIVED_MANIFEST_PATH)
    retrieval_report = load_json(RETRIEVAL_REPORT_PATH)
    semantic_merge_report = load_json(SEMANTIC_MERGE_REPORT_PATH)
    relationship_profile = load_json(RELATIONSHIP_PROFILE_PATH)
    provenance_manifest = load_json(PROVENANCE_MANIFEST_PATH)
    qrels = load_json(QRELS_PATH)
    derived_schemas = load_derived_schemas(derived_manifest)

    baseline_tables = build_internal_baseline_tables(internal_baseline)
    retrieval_tables = build_retrieval_tables(retrieval_report)
    semantic_tables = build_semantic_merge_tables(semantic_merge_report)
    evidence_tables = build_evidence_adequacy_tables(derived_schemas, semantic_merge_report)
    unit_tables = build_unit_normalization_tables(derived_schemas)
    profile_tables = build_profile_tables(derived_schemas, relationship_profile)

    tables = {
        "benchmark_slice": build_benchmark_slice_table(freeze),
        **baseline_tables,
        **evidence_tables,
        **unit_tables,
        **retrieval_tables,
        **semantic_tables,
        **profile_tables,
        "provenance_summary": build_provenance_summary_table(provenance_manifest),
        "qrels_summary": build_qrels_summary_table(qrels),
        "locked_regression_subsets": build_regression_subset_table(freeze),
        "known_limitations": build_known_limitations_table(freeze),
    }

    return {
        "report_id": REPORT_ID,
        "generated_from": {
            "benchmark_freeze": FREEZE_PATH.relative_to(ROOT).as_posix(),
            "internal_baseline": INTERNAL_BASELINE_PATH.relative_to(ROOT).as_posix(),
            "retrieval_report": RETRIEVAL_REPORT_PATH.relative_to(ROOT).as_posix(),
            "semantic_merge_report": SEMANTIC_MERGE_REPORT_PATH.relative_to(ROOT).as_posix(),
            "derived_manifest": DERIVED_MANIFEST_PATH.relative_to(ROOT).as_posix(),
            "relationship_profile": RELATIONSHIP_PROFILE_PATH.relative_to(ROOT).as_posix(),
            "provenance_manifest": PROVENANCE_MANIFEST_PATH.relative_to(ROOT).as_posix(),
            "qrels": QRELS_PATH.relative_to(ROOT).as_posix(),
            "schema_claim_model": SCHEMA_CLAIM_MODEL_PATH.relative_to(ROOT).as_posix(),
            "benchmark_card": BENCHMARK_CARD_PATH.relative_to(ROOT).as_posix(),
        },
        "tables": tables,
    }


def format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def markdown_table(columns: List[str], rows: Iterable[Dict[str, Any]]) -> List[str]:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(format_value(row.get(column, "")) for column in columns) + " |")
    return lines


def render_markdown(report: Dict[str, Any]) -> str:
    tables = report["tables"]
    generated = report["generated_from"]
    lines = [
        "# Paper-Ready Result Tables",
        "",
        "These tables are generated from frozen study artifacts rather than hand-edited numbers.",
        "",
        "## Source Artifacts",
        "",
        "| Source | Path |",
        "| --- | --- |",
    ]
    for source, path in generated.items():
        lines.append(f"| {source} | `{path}` |")

    lines.extend(
        [
            "",
            "## Table 1. Frozen Benchmark Slice",
            "",
            *markdown_table(["measure", "value", "source"], tables["benchmark_slice"]),
            "",
            "## Table 2. Deterministic Extraction Baseline",
            "",
            *markdown_table(["metric", "value"], tables["internal_baseline_aggregate"]),
            "",
            "## Table 3. Deterministic Baseline By Data Family",
            "",
            *markdown_table(
                [
                    "category",
                    "physical_completeness",
                    "physical_accuracy",
                    "logical_accuracy",
                    "semantic_accuracy",
                    "unit_accuracy",
                    "time_axis_accuracy",
                ],
                tables["internal_baseline_by_category"],
            ),
            "",
            "## Table 4. Deterministic Baseline Error Modes",
            "",
            *markdown_table(["error_mode", "count"], tables["internal_error_modes"]),
            "",
            "## Table 5. Evidence Adequacy Summary",
            "",
            *markdown_table(
                ["metric", "numerator", "denominator", "value", "interpretation"],
                tables["evidence_adequacy_summary"],
            ),
            "",
            "## Table 6. Source Evidence Type Counts",
            "",
            *markdown_table(["evidence_type", "field_count"], tables["source_evidence_type_counts"]),
            "",
            "## Table 7. Unit Normalization Status",
            "",
            *markdown_table(["status", "field_count", "unit_claim_count"], tables["unit_normalization_status"]),
            "",
            "## Table 8. Unit Normalization Evidence Basis",
            "",
            *markdown_table(["evidence_basis", "unit_claim_count"], tables["unit_normalization_evidence_basis"]),
            "",
            "## Table 9. PROV-Like Provenance Export Summary",
            "",
            *markdown_table(["metric", "value"], tables["provenance_summary"]),
            "",
            "## Table 10. Retrieval Qrels Summary",
            "",
            *markdown_table(["metric", "value"], tables["qrels_summary"]),
            "",
            "## Table 11. External Retrieval Metrics",
            "",
            *markdown_table(
                [
                    "system",
                    "schema_source",
                    "query_count",
                    "recall_at_1",
                    "recall_at_3",
                    "precision_at_1",
                    "precision_at_3",
                    "mrr",
                    "ndcg_at_3",
                ],
                tables["retrieval_metrics"],
            ),
            "",
            "## Table 12. Retrieval Gain Vs Metadata-Only",
            "",
            *markdown_table(
                [
                    "system",
                    "recall_at_1_delta",
                    "recall_at_3_delta",
                    "precision_at_1_delta",
                    "mrr_delta",
                    "ndcg_at_3_delta",
                ],
                tables["retrieval_gain_vs_metadata"],
            ),
            "",
            "## Table 13. Semantic Merge Aggregate",
            "",
            *markdown_table(
                [
                    "dataset_count",
                    "improved_dataset_count",
                    "accepted_for_merge_count",
                    "conflict_count",
                    "mean_logical_accuracy_delta",
                ],
                tables["semantic_merge_aggregate"],
            ),
            "",
            "## Table 14. Semantic Merge Dataset Deltas",
            "",
            *markdown_table(
                [
                    "dataset_id",
                    "accepted_merges",
                    "conflicts",
                    "baseline_logical_accuracy",
                    "merged_logical_accuracy",
                    "logical_accuracy_delta",
                    "baseline_semantic_accuracy",
                    "merged_semantic_accuracy",
                    "semantic_accuracy_delta",
                    "baseline_unit_accuracy",
                    "merged_unit_accuracy",
                    "unit_accuracy_delta",
                ],
                tables["semantic_merge_dataset_delta"],
            ),
            "",
            "## Table 15. Deterministic Profile Summary",
            "",
            *markdown_table(["metric", "value", "interpretation"], tables["deterministic_profile_summary"]),
            "",
            "## Table 16. Deterministic Cross-File Relationship Candidates",
            "",
            *markdown_table(["relationship_type", "count"], tables["deterministic_profile_relationships"]),
            "",
            "## Table 17. Locked External Field-Subset Regression Groups",
            "",
            *markdown_table(["subset", "field_count", "fields"], tables["locked_regression_subsets"]),
            "",
            "## Table 18. Remaining Non-Final Items",
            "",
            *markdown_table(["limitation"], tables["known_limitations"]),
            "",
            "## Paper Claims Supported By These Tables",
            "",
            "- The frozen reproducible slice contains 9 internal pilot datasets and 16 external retrieval candidates.",
            "- Deterministic extraction has high field-level accuracy on the internal slice, while time-axis handling remains the clearest open gap.",
            "- Every deterministic field in the current internal slice has source evidence, making evidence adequacy measurable.",
            "- Unit claims now carry normalization status, separating UCUM-normalized units from unmapped scientific time-reference units.",
            "- The PROV-like export links source files, derived schemas, field claims, evidence records, semantic annotations, merge outputs, and reports.",
            "- Retrieval qrels now explicitly mark the current query set as one-positive planted judgments.",
            "- Schema-enhanced retrieval reaches Recall@1 = 1.0000 on the current planted-query external slice.",
            "- Evidence-constrained semantic merge improves logical accuracy on 2 of 3 reviewed internal datasets without measured metric regression.",
            "- Deterministic profiles add missingness, identifier quality, and relationship-candidate diagnostics without changing evaluation labels.",
            "",
        ]
    )
    return "\n".join(lines)


def write_paper_tables(report: Dict[str, Any]) -> None:
    DOCS_ROOT.mkdir(parents=True, exist_ok=True)
    REPORT_JSON_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    REPORT_MD_PATH.write_text(render_markdown(report), encoding="utf-8")


def main() -> None:
    write_paper_tables(build_paper_tables())


if __name__ == "__main__":
    main()
