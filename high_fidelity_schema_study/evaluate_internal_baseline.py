from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
GOLD_ROOT = DATA_ROOT / "gold"
DERIVED_ROOT = DATA_ROOT / "derived"
PILOT_MANIFEST_PATH = DATA_ROOT / "pilot_corpus_manifest.json"
JSON_REPORT_PATH = DERIVED_ROOT / "internal_baseline_report.json"
MARKDOWN_REPORT_PATH = DERIVED_ROOT / "internal_baseline_report.md"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def compare_dataset(dataset_entry: Dict[str, Any]) -> Dict[str, Any]:
    gold_path = DATA_ROOT / dataset_entry["gold_file"]
    derived_path = DERIVED_ROOT / dataset_entry["category"] / f"{dataset_entry['dataset_id']}.schema.json"

    gold = load_json(gold_path)
    derived = load_json(derived_path)

    gold_fields = {field["field_path"]: field for field in gold["fields"]}
    derived_fields = {field["field_path"]: field for field in derived["fields"]}

    matched_paths = sorted(set(gold_fields) & set(derived_fields))
    missing_paths = sorted(set(gold_fields) - set(derived_fields))
    unexpected_paths = sorted(set(derived_fields) - set(gold_fields))

    physical_correct = 0
    logical_correct = 0
    semantic_correct = 0
    logical_present = 0
    semantic_present = 0
    unit_expected_count = 0
    unit_correct = 0
    high_necessity_count = 0
    high_necessity_present = 0
    high_necessity_physical_correct = 0
    time_axis_correct = False
    time_axis_present = "time_axis" in gold

    field_results: List[Dict[str, Any]] = []
    for field_path, gold_field in gold_fields.items():
        derived_field = derived_fields.get(field_path)
        if gold_field["necessity"] == "high":
            high_necessity_count += 1
        if derived_field is None:
            field_results.append(
                {
                    "field_path": field_path,
                    "status": "missing",
                    "gold_physical_type": gold_field["correct_physical_type"],
                    "gold_logical_type": gold_field["correct_logical_type"],
                    "gold_semantic_type": gold_field["correct_semantic_type"],
                }
            )
            continue

        if gold_field["necessity"] == "high":
            high_necessity_present += 1

        physical_match = derived_field["physical_type"] == gold_field["correct_physical_type"]
        logical_match = derived_field["logical_type"] == gold_field["correct_logical_type"]
        semantic_match = derived_field["semantic_type"] == gold_field["correct_semantic_type"]

        if physical_match:
            physical_correct += 1
            if gold_field["necessity"] == "high":
                high_necessity_physical_correct += 1
        if logical_match:
            logical_correct += 1
        if semantic_match:
            semantic_correct += 1

        if derived_field["logical_type"] != "unknown":
            logical_present += 1
        if derived_field["semantic_type"] != "unknown":
            semantic_present += 1

        expected_unit = gold_field["unit"]
        if expected_unit is not None:
            unit_expected_count += 1
            if derived_field["unit"] == expected_unit:
                unit_correct += 1

        field_results.append(
            {
                "field_path": field_path,
                "status": "matched",
                "physical_match": physical_match,
                "logical_match": logical_match,
                "semantic_match": semantic_match,
                "gold_physical_type": gold_field["correct_physical_type"],
                "derived_physical_type": derived_field["physical_type"],
                "gold_logical_type": gold_field["correct_logical_type"],
                "derived_logical_type": derived_field["logical_type"],
                "gold_semantic_type": gold_field["correct_semantic_type"],
                "derived_semantic_type": derived_field["semantic_type"],
                "gold_unit": expected_unit,
                "derived_unit": derived_field["unit"],
                "derived_confidence": derived_field.get("confidence"),
                "derived_uncertainty_reason": derived_field.get("uncertainty_reason"),
                "necessity": gold_field["necessity"],
            }
        )

    if time_axis_present:
        gold_time_axis = gold["time_axis"]
        derived_time_series = derived.get("metadata", {}).get("time_series", {})
        derived_time_axis = derived_time_series.get("time_axis")
        time_axis_correct = derived_time_axis == gold_time_axis

    gold_count = len(gold_fields)
    matched_count = len(matched_paths)
    logical_gold_count = gold_count
    semantic_gold_count = gold_count

    summary = {
        "dataset_id": dataset_entry["dataset_id"],
        "category": dataset_entry["category"],
        "difficulty": dataset_entry["difficulty"],
        "gold_field_count": gold_count,
        "extracted_field_count": len(derived_fields),
        "matched_field_count": matched_count,
        "missing_field_count": len(missing_paths),
        "unexpected_field_count": len(unexpected_paths),
        "physical_completeness": safe_ratio(matched_count, gold_count),
        "physical_accuracy": safe_ratio(physical_correct, gold_count),
        "logical_completeness": safe_ratio(logical_present, logical_gold_count),
        "logical_accuracy": safe_ratio(logical_correct, logical_gold_count),
        "semantic_completeness": safe_ratio(semantic_present, semantic_gold_count),
        "semantic_accuracy": safe_ratio(semantic_correct, semantic_gold_count),
        "unit_accuracy": safe_ratio(unit_correct, unit_expected_count),
        "high_necessity_coverage": safe_ratio(high_necessity_present, high_necessity_count),
        "high_necessity_physical_accuracy": safe_ratio(high_necessity_physical_correct, high_necessity_count),
        "time_axis_accuracy": 1.0 if (not time_axis_present or time_axis_correct) else 0.0,
        "missing_fields": missing_paths,
        "unexpected_fields": unexpected_paths,
        "field_results": field_results,
    }
    return summary


def bucket_confidence(confidence: float) -> str:
    if confidence >= 0.95:
        return "0.95-1.00"
    if confidence >= 0.85:
        return "0.85-0.95"
    if confidence >= 0.70:
        return "0.70-0.85"
    return "<0.70"


def analyze_uncertainty(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    calibration: Dict[str, Dict[str, float]] = {}
    unknown_counts = {"logical_unknown": 0, "semantic_unknown": 0}
    total_fields = 0

    for result in results:
        for field in result["field_results"]:
            if field["status"] != "matched":
                continue
            total_fields += 1
            confidence = field.get("derived_confidence")
            if confidence is None:
                continue
            bucket = bucket_confidence(confidence)
            entry = calibration.setdefault(
                bucket,
                {"count": 0, "physical_correct": 0, "logical_correct": 0, "semantic_correct": 0},
            )
            entry["count"] += 1
            entry["physical_correct"] += 1 if field["physical_match"] else 0
            entry["logical_correct"] += 1 if field["logical_match"] else 0
            entry["semantic_correct"] += 1 if field["semantic_match"] else 0

            if field["derived_logical_type"] == "unknown":
                unknown_counts["logical_unknown"] += 1
            if field["derived_semantic_type"] == "unknown":
                unknown_counts["semantic_unknown"] += 1

    for bucket, entry in calibration.items():
        count = entry["count"]
        entry["physical_accuracy"] = safe_ratio(entry["physical_correct"], count)
        entry["logical_accuracy"] = safe_ratio(entry["logical_correct"], count)
        entry["semantic_accuracy"] = safe_ratio(entry["semantic_correct"], count)

    return {
        "confidence_buckets": calibration,
        "unknown_rates": {
            "logical_unknown_rate": safe_ratio(unknown_counts["logical_unknown"], total_fields),
            "semantic_unknown_rate": safe_ratio(unknown_counts["semantic_unknown"], total_fields),
        },
    }


def categorize_field_failure(field: Dict[str, Any]) -> List[str]:
    categories = []
    if field["status"] == "missing":
        categories.append("missing_field")
        return categories
    if not field["physical_match"]:
        categories.append("physical_type_mismatch")
    if field["derived_logical_type"] == "unknown" and field["gold_logical_type"] != "unknown":
        categories.append("logical_unknown")
    elif not field["logical_match"]:
        categories.append("logical_mismatch")
    if field["derived_semantic_type"] == "unknown" and field["gold_semantic_type"] != "unknown":
        categories.append("semantic_unknown")
    elif not field["semantic_match"]:
        categories.append("semantic_mismatch")
    if field["gold_unit"] is not None and field["derived_unit"] != field["gold_unit"]:
        categories.append("unit_mismatch")
    return categories


def analyze_error_modes(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    examples: Dict[str, List[Dict[str, Any]]] = {}

    for result in results:
        if result["unexpected_fields"]:
            counts["unexpected_field"] = counts.get("unexpected_field", 0) + len(result["unexpected_fields"])
            example_list = examples.setdefault("unexpected_field", [])
            for field_path in result["unexpected_fields"][:3]:
                if len(example_list) < 5:
                    example_list.append({"dataset_id": result["dataset_id"], "field_path": field_path})

        if result["time_axis_accuracy"] == 0.0:
            counts["time_axis_mismatch"] = counts.get("time_axis_mismatch", 0) + 1
            example_list = examples.setdefault("time_axis_mismatch", [])
            if len(example_list) < 5:
                example_list.append({"dataset_id": result["dataset_id"]})

        for field in result["field_results"]:
            categories = categorize_field_failure(field)
            for category in categories:
                counts[category] = counts.get(category, 0) + 1
                example_list = examples.setdefault(category, [])
                if len(example_list) < 5:
                    example = {"dataset_id": result["dataset_id"], "field_path": field["field_path"]}
                    if field["status"] == "matched":
                        example["derived_logical_type"] = field.get("derived_logical_type")
                        example["derived_semantic_type"] = field.get("derived_semantic_type")
                    example_list.append(example)

    sorted_counts = dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
    return {
        "counts": sorted_counts,
        "examples": examples,
    }


def aggregate(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    metric_names = [
        "physical_completeness",
        "physical_accuracy",
        "logical_completeness",
        "logical_accuracy",
        "semantic_completeness",
        "semantic_accuracy",
        "unit_accuracy",
        "high_necessity_coverage",
        "high_necessity_physical_accuracy",
        "time_axis_accuracy",
    ]
    aggregate_metrics = {}
    for metric in metric_names:
        aggregate_metrics[metric] = round(sum(result[metric] for result in results) / len(results), 4)

    by_category: Dict[str, Dict[str, Any]] = {}
    for category in sorted({result["category"] for result in results}):
        category_results = [result for result in results if result["category"] == category]
        by_category[category] = {
            metric: round(sum(item[metric] for item in category_results) / len(category_results), 4)
            for metric in metric_names
        }

    return {
        "dataset_count": len(results),
        "metrics": aggregate_metrics,
        "by_category": by_category,
    }


def render_markdown(aggregate_summary: Dict[str, Any], dataset_results: List[Dict[str, Any]]) -> str:
    lines = [
        "# Internal Baseline Report",
        "",
        "This report compares deterministic derived schemas against the internal gold references.",
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for metric, value in aggregate_summary["metrics"].items():
        lines.append(f"| {metric} | {value:.4f} |")

    lines.extend(
        [
            "",
            "## Metrics By Category",
            "",
            "| Category | physical_completeness | physical_accuracy | logical_completeness | logical_accuracy | semantic_completeness | semantic_accuracy | high_necessity_coverage |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for category, metrics in aggregate_summary["by_category"].items():
        lines.append(
            f"| {category} | {metrics['physical_completeness']:.4f} | {metrics['physical_accuracy']:.4f} | "
            f"{metrics['logical_completeness']:.4f} | {metrics['logical_accuracy']:.4f} | "
            f"{metrics['semantic_completeness']:.4f} | {metrics['semantic_accuracy']:.4f} | "
            f"{metrics['high_necessity_coverage']:.4f} |"
        )

    uncertainty = aggregate_summary["uncertainty"]
    lines.extend(
        [
            "",
            "## Uncertainty Analysis",
            "",
            "| Confidence Bucket | Count | Physical Accuracy | Logical Accuracy | Semantic Accuracy |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for bucket, bucket_metrics in uncertainty["confidence_buckets"].items():
        lines.append(
            f"| {bucket} | {bucket_metrics['count']} | {bucket_metrics['physical_accuracy']:.4f} | "
            f"{bucket_metrics['logical_accuracy']:.4f} | {bucket_metrics['semantic_accuracy']:.4f} |"
        )
    lines.extend(
        [
            "",
            f"- Logical unknown rate: `{uncertainty['unknown_rates']['logical_unknown_rate']:.4f}`",
            f"- Semantic unknown rate: `{uncertainty['unknown_rates']['semantic_unknown_rate']:.4f}`",
        ]
    )

    error_modes = aggregate_summary["error_modes"]
    lines.extend(
        [
            "",
            "## Error Modes",
            "",
            "| Error Mode | Count |",
            "| --- | ---: |",
        ]
    )
    for mode, count in error_modes["counts"].items():
        lines.append(f"| {mode} | {count} |")

    lines.extend(["", "## Dataset Results", ""])
    for result in dataset_results:
        lines.extend(
            [
                f"### {result['dataset_id']}",
                "",
                f"- Category: `{result['category']}`",
                f"- Difficulty: `{result['difficulty']}`",
                f"- Physical completeness: `{result['physical_completeness']:.4f}`",
                f"- Physical accuracy: `{result['physical_accuracy']:.4f}`",
                f"- Logical completeness: `{result['logical_completeness']:.4f}`",
                f"- Logical accuracy: `{result['logical_accuracy']:.4f}`",
                f"- Semantic completeness: `{result['semantic_completeness']:.4f}`",
                f"- Semantic accuracy: `{result['semantic_accuracy']:.4f}`",
                f"- High necessity coverage: `{result['high_necessity_coverage']:.4f}`",
            ]
        )
        if result["missing_fields"]:
            lines.append(f"- Missing fields: `{', '.join(result['missing_fields'])}`")
        if result["unexpected_fields"]:
            lines.append(f"- Unexpected fields: `{', '.join(result['unexpected_fields'])}`")
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    pilot_manifest = load_json(PILOT_MANIFEST_PATH)
    dataset_results = [compare_dataset(entry) for entry in pilot_manifest["datasets"]]
    aggregate_summary = aggregate(dataset_results)
    aggregate_summary["uncertainty"] = analyze_uncertainty(dataset_results)
    aggregate_summary["error_modes"] = analyze_error_modes(dataset_results)
    report = {
        "aggregate": aggregate_summary,
        "datasets": dataset_results,
    }

    JSON_REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    MARKDOWN_REPORT_PATH.write_text(render_markdown(aggregate_summary, dataset_results), encoding="utf-8")


if __name__ == "__main__":
    main()
