from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
from statistics import median
from typing import Any, Dict, Iterable, Mapping


SUMMARY_SCHEMA_VERSION = "ndp50-execution-summary/v2"
FAILURE_LEDGER_SCHEMA_VERSION = "ndp50-failure-ledger/v1"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    index = round((len(ordered) - 1) * probability)
    return ordered[index]


def _dataset_bootstrap_interval(
    values: list[int], *, run_role: str, repetitions: int = 10_000
) -> Dict[str, Any]:
    seed_text = f"ndp50:{run_role}:dataset-end-to-end:v1"
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    samples = [
        sum(values[rng.randrange(len(values))] for _ in values) / len(values)
        for _ in range(repetitions)
    ]
    return {
        "method": "fixed_seed_nonparametric_dataset_bootstrap_percentile",
        "confidence_level": 0.95,
        "repetitions": repetitions,
        "seed_text": seed_text,
        "lower": round(_percentile(samples, 0.025), 6),
        "upper": round(_percentile(samples, 0.975), 6),
    }


def summarize_run(
    execution: Mapping[str, Any], selection: Mapping[str, Any]
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    run_role = str(execution.get("run_role") or "")
    if run_role not in {"development", "validation", "test"}:
        raise ValueError("execution run_role must be development, validation, or test")
    expected_ids = {
        item["dataset_id"]
        for item in selection["selected_datasets"]
        if item["split"] == run_role
    }
    observed_ids = {item["dataset_id"] for item in execution["datasets"]}
    if observed_ids != expected_ids:
        raise ValueError(
            f"execution dataset IDs do not exactly match the frozen {run_role} split"
        )

    resources = [
        (dataset, resource)
        for dataset in execution["datasets"]
        for resource in dataset["resource_records"]
    ]
    plan_counts = Counter(resource["plan"]["decision"] for _, resource in resources)
    download_counts = Counter(resource["download"]["status"] for _, resource in resources)
    extraction_counts = Counter(
        resource["extraction"]["status"]
        for _, resource in resources
        if resource["extraction"] is not None
    )
    issue_counts = Counter(
        issue["code"]
        for _, resource in resources
        if resource["extraction"] is not None
        for issue in resource["extraction"].get("issues", [])
    )

    successful_resources = sum(
        resource["extraction"] is not None
        and resource["extraction"]["status"] == "success"
        for _, resource in resources
    )
    attempted_resources = plan_counts["attempt"]
    acquired_resources = download_counts["acquired"]
    successful_datasets = sum(
        any(
            resource["extraction"] is not None
            and resource["extraction"]["status"] == "success"
            for resource in dataset["resource_records"]
        )
        for dataset in execution["datasets"]
    )
    selection_by_id = {
        item["dataset_id"]: item for item in selection["selected_datasets"]
    }
    dataset_summaries = []
    stratum_rows: Dict[str, list[Dict[str, Any]]] = {}
    for dataset in execution["datasets"]:
        records = dataset["resource_records"]
        successes = sum(
            resource["extraction"] is not None
            and resource["extraction"]["status"] == "success"
            for resource in records
        )
        partials = sum(
            resource["extraction"] is not None
            and resource["extraction"]["status"] == "partial"
            for resource in records
        )
        abstentions = sum(
            resource["extraction"] is not None
            and resource["extraction"]["status"] == "abstained"
            for resource in records
        )
        attempts = sum(resource["plan"]["decision"] == "attempt" for resource in records)
        acquired = sum(resource["download"]["status"] == "acquired" for resource in records)
        if successes or partials:
            outcome_class = "schema_extracted"
        elif abstentions:
            outcome_class = "acquired_but_abstained"
        elif attempts:
            outcome_class = "attempted_but_not_acquired"
        else:
            outcome_class = "no_policy_attempt"
        selection_item = selection_by_id[dataset["dataset_id"]]
        row = {
            "dataset_id": dataset["dataset_id"],
            "title": dataset.get("title") or "",
            "primary_format_class": selection_item.get(
                "primary_format_class", "unreported"
            ),
            "catalog_resource_count": len(records),
            "attempted_resource_count": attempts,
            "acquired_payload_count": acquired,
            "successful_extraction_count": successes,
            "partial_extraction_count": partials,
            "abstention_count": abstentions,
            "outcome_class": outcome_class,
            "resource_end_to_end_rate": _rate(successes, len(records)),
        }
        dataset_summaries.append(row)
        stratum_rows.setdefault(row["primary_format_class"], []).append(row)

    outcome_classes = Counter(item["outcome_class"] for item in dataset_summaries)
    stratum_summary = {}
    for stratum, rows in sorted(stratum_rows.items()):
        stratum_successes = sum(
            item["outcome_class"] == "schema_extracted" for item in rows
        )
        stratum_resources = sum(item["catalog_resource_count"] for item in rows)
        stratum_resource_successes = sum(
            item["successful_extraction_count"] for item in rows
        )
        stratum_summary[stratum] = {
            "dataset_count": len(rows),
            "datasets_with_schema": stratum_successes,
            "dataset_end_to_end_rate": _rate(stratum_successes, len(rows)),
            "catalog_resource_count": stratum_resources,
            "resources_with_schema": stratum_resource_successes,
            "resource_end_to_end_rate": _rate(
                stratum_resource_successes, stratum_resources
            ),
        }
    resource_counts = [
        item["catalog_resource_count"] for item in dataset_summaries
    ]
    macro_resource_rate = round(
        sum(item["resource_end_to_end_rate"] or 0.0 for item in dataset_summaries)
        / len(dataset_summaries),
        6,
    )
    dataset_success_values = [
        int(item["outcome_class"] == "schema_extracted")
        for item in dataset_summaries
    ]

    ledger_entries = []
    for dataset, resource in resources:
        download_status = resource["download"]["status"]
        extraction = resource["extraction"]
        if extraction is not None and extraction["status"] == "success":
            continue
        failure = resource["download"].get("failure") or {}
        extraction_issues = (
            extraction.get("issues", []) if extraction is not None else []
        )
        extraction_issue = (
            extraction_issues[0] if extraction_issues else {}
        )
        ledger_entries.append(
            {
                "dataset_id": dataset["dataset_id"],
                "resource_id": resource["resource_id"],
                "catalog_format": resource["catalog_format"],
                "plan_decision": resource["plan"]["decision"],
                "download_status": download_status,
                "extraction_status": (
                    extraction["status"] if extraction is not None else "not_run"
                ),
                "reason_code": (
                    extraction_issue.get("code")
                    or failure.get("code")
                    or resource["plan"].get("decision")
                    or "unknown"
                ),
                "reason": (
                    extraction_issue.get("message")
                    or failure.get("message")
                    or resource["plan"].get("reason")
                    or "No reason recorded."
                ),
            }
        )
    reason_counts = Counter(item["reason_code"] for item in ledger_entries)

    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "run_role": run_role,
        "claim_boundary": (
            "Structural acquisition/extraction coverage only; semantic accuracy "
            "requires independently frozen gold."
        ),
        "selection_integrity": {
            "expected_dataset_count": len(expected_ids),
            "observed_dataset_count": len(observed_ids),
            "split": run_role,
            "exact_id_match": True,
        },
        "denominators": {
            "datasets": len(execution["datasets"]),
            "catalog_resources": len(resources),
            "policy_attempted_resources": attempted_resources,
            "acquired_dataset_payloads": acquired_resources,
        },
        "coverage": {
            "datasets_with_successful_extraction": successful_datasets,
            "dataset_end_to_end_rate": _rate(
                successful_datasets, len(execution["datasets"])
            ),
            "resources_with_successful_extraction": successful_resources,
            "resource_end_to_end_rate": _rate(successful_resources, len(resources)),
            "macro_mean_dataset_resource_end_to_end_rate": macro_resource_rate,
            "acquisition_rate_given_attempt": _rate(
                acquired_resources, attempted_resources
            ),
            "extraction_success_rate_given_acquisition": _rate(
                successful_resources, acquired_resources
            ),
        },
        "dataset_bootstrap_interval": _dataset_bootstrap_interval(
            dataset_success_values, run_role=run_role
        ),
        "dataset_outcome_classes": dict(sorted(outcome_classes.items())),
        "resource_count_skew": {
            "minimum": min(resource_counts),
            "median": median(resource_counts),
            "maximum": max(resource_counts),
            "maximum_dataset_id": max(
                dataset_summaries,
                key=lambda item: item["catalog_resource_count"],
            )["dataset_id"],
            "maximum_share_of_all_resources": _rate(
                max(resource_counts), sum(resource_counts)
            ),
        },
        "stratum_summary": stratum_summary,
        "dataset_summaries": sorted(
            dataset_summaries, key=lambda item: item["dataset_id"]
        ),
        "plan_decisions": dict(sorted(plan_counts.items())),
        "download_statuses": dict(sorted(download_counts.items())),
        "extraction_statuses": dict(sorted(extraction_counts.items())),
        "extraction_issue_codes": dict(sorted(issue_counts.items())),
        "failure_reason_counts": dict(sorted(reason_counts.items())),
    }
    ledger = {
        "schema_version": FAILURE_LEDGER_SCHEMA_VERSION,
        "run_role": run_role,
        "entry_count": len(ledger_entries),
        "reason_counts": dict(sorted(reason_counts.items())),
        "entries": ledger_entries,
    }
    return summary, ledger


def _markdown(summary: Mapping[str, Any]) -> str:
    coverage = summary["coverage"]
    denominators = summary["denominators"]
    lines = [
        f"# NDP-50 {summary['run_role']} structural checkpoint",
        "",
        "This report measures structural acquisition/extraction coverage. It is not",
        "a semantic accuracy estimate and must not be merged with controlled fixtures.",
        "",
        "## Frozen-split integrity",
        "",
        (
            f"- {summary['run_role'].title()} datasets: {denominators['datasets']} "
            "(exact frozen selection-ID match)"
        ),
        "",
        "## End-to-end coverage",
        "",
        (
            f"- Dataset level: {coverage['datasets_with_successful_extraction']}/"
            f"{denominators['datasets']} ({coverage['dataset_end_to_end_rate']:.1%})"
        ),
        (
            "- Dataset bootstrap 95% interval: "
            f"{summary['dataset_bootstrap_interval']['lower']:.1%} to "
            f"{summary['dataset_bootstrap_interval']['upper']:.1%}"
        ),
        (
            f"- Catalog-resource level: {coverage['resources_with_successful_extraction']}/"
            f"{denominators['catalog_resources']} ({coverage['resource_end_to_end_rate']:.1%})"
        ),
        (
            f"- Acquisition conditional on a policy attempt: "
            f"{coverage['acquisition_rate_given_attempt']:.1%}"
        ),
        (
            f"- Extraction success conditional on an acquired data payload: "
            f"{coverage['extraction_success_rate_given_acquisition']:.1%}"
        ),
        (
            "- Macro mean of per-dataset resource coverage: "
            f"{coverage['macro_mean_dataset_resource_end_to_end_rate']:.1%}"
        ),
        "",
        "## Resource-count skew",
        "",
        (
            f"- Min / median / max resources per dataset: "
            f"{summary['resource_count_skew']['minimum']} / "
            f"{summary['resource_count_skew']['median']:g} / "
            f"{summary['resource_count_skew']['maximum']}"
        ),
        (
            "- Largest dataset share of all catalog resources: "
            f"{summary['resource_count_skew']['maximum_share_of_all_resources']:.1%}"
        ),
        "",
        "## Capability and acquisition ledger",
        "",
    ]
    for reason, count in summary["failure_reason_counts"].items():
        lines.append(f"- `{reason}`: {count}")
    lines.extend(["", "## Dataset outcome classes", ""])
    for outcome_class, count in summary["dataset_outcome_classes"].items():
        lines.append(f"- `{outcome_class}`: {count}")
    lines.extend(["", "## Selection-stratum results", ""])
    for stratum, row in summary["stratum_summary"].items():
        lines.append(
            f"- `{stratum}`: {row['datasets_with_schema']}/"
            f"{row['dataset_count']} datasets with schema; "
            f"{row['resources_with_schema']}/{row['catalog_resource_count']} resources"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The conditional extraction rate must not be reported alone: most coverage loss",
            "occurs before extraction through unsupported formats, remote directory stores,",
            "resource caps, or byte limits. The dataset- and catalog-resource denominators",
            "above are the primary engineering coverage measures.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the reproducible NDP-50 development summary and failure ledger."
    )
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary, ledger = summarize_run(
        _load_json(args.execution), _load_json(args.selection)
    )
    _write_json(args.output_dir / "summary.json", summary)
    _write_json(args.output_dir / "failure_ledger.json", ledger)
    (args.output_dir / "report.md").write_text(
        _markdown(summary), encoding="utf-8"
    )
    print(json.dumps(summary["coverage"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
