from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
PILOT_MANIFEST_PATH = DATA_ROOT / "pilot_corpus_manifest.json"
SEMANTIC_MERGED_MANIFEST_PATH = DATA_ROOT / "semantic_merged" / "manifest.json"
REPORT_JSON_PATH = DATA_ROOT / "semantic_merged" / "semantic_merge_report.json"
REPORT_MD_PATH = DATA_ROOT / "semantic_merged" / "semantic_merge_report.md"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def evaluate_schema(schema: Dict[str, Any], gold: Dict[str, Any]) -> Dict[str, Any]:
    gold_fields = {field["field_path"]: field for field in gold["fields"]}
    schema_fields = {field["field_path"]: field for field in schema["fields"]}

    physical_correct = 0
    logical_correct = 0
    semantic_correct = 0
    unit_correct = 0
    unit_expected = 0
    accepted_for_merge_count = 0

    per_field = []
    for field_path, gold_field in gold_fields.items():
        schema_field = schema_fields[field_path]
        physical_match = schema_field["physical_type"] == gold_field["correct_physical_type"]
        logical_match = schema_field["logical_type"] == gold_field["correct_logical_type"]
        semantic_match = schema_field["semantic_type"] == gold_field["correct_semantic_type"]
        if physical_match:
            physical_correct += 1
        if logical_match:
            logical_correct += 1
        if semantic_match:
            semantic_correct += 1
        if gold_field["unit"] is not None:
            unit_expected += 1
            if schema_field.get("unit") == gold_field["unit"]:
                unit_correct += 1
        accepted = schema_field.get("semantic_annotation", {}).get("accepted_for_merge")
        if accepted:
            accepted_for_merge_count += 1

        per_field.append(
            {
                "field_path": field_path,
                "physical_match": physical_match,
                "logical_match": logical_match,
                "semantic_match": semantic_match,
                "accepted_for_merge": accepted,
                "semantic_annotation": schema_field.get("semantic_annotation"),
            }
        )

    field_count = len(gold_fields)
    return {
        "field_count": field_count,
        "physical_accuracy": safe_ratio(physical_correct, field_count),
        "logical_accuracy": safe_ratio(logical_correct, field_count),
        "semantic_accuracy": safe_ratio(semantic_correct, field_count),
        "unit_accuracy": safe_ratio(unit_correct, unit_expected),
        "accepted_for_merge_count": accepted_for_merge_count,
        "per_field": per_field,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Semantic Merge Report",
        "",
        "This report compares baseline deterministic schemas against semantic-merged schemas for internal tasks that have both gold references and semantic merge outputs.",
        "",
        "## Aggregate Summary",
        "",
        f"- Dataset count: `{report['dataset_count']}`",
        f"- Datasets with any metric gain: `{report['aggregate']['improved_dataset_count']}`",
        f"- Total accepted semantic merges: `{report['aggregate']['accepted_for_merge_count']}`",
        f"- Total conflicts: `{report['aggregate']['conflict_count']}`",
        f"- Mean logical accuracy delta: `{report['aggregate']['mean_logical_accuracy_delta']:+.4f}`",
        "",
    ]
    for dataset in report["datasets"]:
        lines.extend(
            [
                f"## {dataset['dataset_id']}",
                "",
                "| Metric | Baseline | Merged | Delta |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for metric in ["physical_accuracy", "logical_accuracy", "semantic_accuracy", "unit_accuracy"]:
            baseline = dataset["baseline"][metric]
            merged = dataset["merged"][metric]
            delta = round(merged - baseline, 4)
            lines.append(f"| {metric} | {baseline:.4f} | {merged:.4f} | {delta:+.4f} |")
        lines.extend(
            [
                "",
                f"- Accepted semantic merges: `{dataset['merged']['accepted_for_merge_count']}`",
                f"- Conflict count: `{dataset['conflict_count']}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    pilot_manifest = load_json(PILOT_MANIFEST_PATH)
    pilot_lookup = {entry["dataset_id"]: entry for entry in pilot_manifest["datasets"]}
    semantic_manifest = load_json(SEMANTIC_MERGED_MANIFEST_PATH)

    datasets = []
    for item in semantic_manifest["entries"]:
        if item["scope"] != "internal":
            continue
        dataset_id = Path(item["task_file"]).name.replace(".task.json", "")
        pilot_entry = pilot_lookup.get(dataset_id)
        if pilot_entry is None:
            continue
        gold = load_json(DATA_ROOT / pilot_entry["gold_file"])
        baseline = load_json(DATA_ROOT / "derived" / pilot_entry["category"] / f"{dataset_id}.schema.json")
        merged = load_json(DATA_ROOT / item["merged_file"])

        baseline_metrics = evaluate_schema(baseline, gold)
        merged_metrics = evaluate_schema(merged, gold)
        conflict_count = len(merged.get("metadata", {}).get("semantic_annotation", {}).get("conflicts", []))
        datasets.append(
            {
                "dataset_id": dataset_id,
                "baseline": baseline_metrics,
                "merged": merged_metrics,
                "conflict_count": conflict_count,
            }
        )

    improved_dataset_count = 0
    accepted_for_merge_count = 0
    conflict_count = 0
    logical_delta_sum = 0.0
    for dataset in datasets:
        metric_gains = [
            dataset["merged"][metric] > dataset["baseline"][metric]
            for metric in ["physical_accuracy", "logical_accuracy", "semantic_accuracy", "unit_accuracy"]
        ]
        if any(metric_gains):
            improved_dataset_count += 1
        accepted_for_merge_count += dataset["merged"]["accepted_for_merge_count"]
        conflict_count += dataset["conflict_count"]
        logical_delta_sum += dataset["merged"]["logical_accuracy"] - dataset["baseline"]["logical_accuracy"]

    aggregate = {
        "improved_dataset_count": improved_dataset_count,
        "accepted_for_merge_count": accepted_for_merge_count,
        "conflict_count": conflict_count,
        "mean_logical_accuracy_delta": safe_ratio(round(logical_delta_sum * 10000), max(len(datasets), 1) * 10000),
    }
    report = {"dataset_count": len(datasets), "aggregate": aggregate, "datasets": datasets}
    REPORT_JSON_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    REPORT_MD_PATH.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
