from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence


SCHEMA_VERSION = "ndp50-semantic-opportunity-manifest/v1"
ALLOWED_SPLITS = {"development", "validation"}


class NDPSemanticOpportunityError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_semantic_opportunity_manifest(
    *,
    run_paths: Sequence[Path],
    selection_path: Path,
    schemas_root: Path,
    failure_ledger_paths: Sequence[Path],
) -> Dict[str, Any]:
    selection = _load_json(selection_path)
    selection_by_id = {
        item["dataset_id"]: item for item in selection["selected_datasets"]
    }
    cases = []
    seen_case_ids = set()
    input_runs = []
    run_splits = set()
    for run_path in run_paths:
        run = _load_json(run_path)
        split = str(run.get("run_role") or "")
        if split not in ALLOWED_SPLITS:
            raise NDPSemanticOpportunityError(
                "opportunity construction accepts development/validation only"
            )
        if split in run_splits:
            raise NDPSemanticOpportunityError(f"duplicate run split: {split}")
        run_splits.add(split)
        expected_ids = {
            dataset_id
            for dataset_id, item in selection_by_id.items()
            if item["split"] == split
        }
        observed_ids = {item["dataset_id"] for item in run["datasets"]}
        if observed_ids != expected_ids:
            raise NDPSemanticOpportunityError(
                f"{split} run does not match frozen selection identities"
            )
        input_runs.append(
            {
                "split": split,
                "file": run_path.name,
                "sha256": _sha256_file(run_path),
            }
        )
        for dataset in run["datasets"]:
            for resource in dataset["resource_records"]:
                extraction = resource.get("extraction")
                if not extraction or extraction.get("status") not in {
                    "success",
                    "partial",
                }:
                    continue
                artifact = extraction.get("artifact") or {}
                artifact_file = str(artifact.get("file") or "")
                schema_path = (
                    schemas_root
                    / split
                    / dataset["dataset_id"]
                    / artifact_file
                )
                if not artifact_file or not schema_path.is_file():
                    raise NDPSemanticOpportunityError(
                        f"schema artifact missing for {resource['resource_id']}"
                    )
                schema_hash = _sha256_file(schema_path)
                if schema_hash != artifact.get("sha256"):
                    raise NDPSemanticOpportunityError(
                        f"schema artifact hash mismatch for {resource['resource_id']}"
                    )
                outcome = _load_json(schema_path)
                schema = outcome.get("schema")
                if not isinstance(schema, dict):
                    raise NDPSemanticOpportunityError(
                        "schema-bearing extraction has no schema object"
                    )
                fields = schema.get("fields")
                if not isinstance(fields, list):
                    raise NDPSemanticOpportunityError("schema fields must be a list")
                field_paths = [str(item.get("field_path") or "") for item in fields]
                if any(not item for item in field_paths) or len(field_paths) != len(
                    set(field_paths)
                ):
                    raise NDPSemanticOpportunityError(
                        f"invalid or duplicate field paths for {resource['resource_id']}"
                    )
                case_id = f"ndp50-{split}-{resource['resource_id']}"
                if case_id in seen_case_ids:
                    raise NDPSemanticOpportunityError(
                        f"duplicate semantic case ID: {case_id}"
                    )
                seen_case_ids.add(case_id)
                file_format = str(schema.get("file_format") or "")
                if file_format == "csv" and len(fields) >= 2:
                    cpa_status = "requires_manual_relation_and_subject_assessment"
                    subject_status = "unassigned_requires_independent_annotation"
                elif file_format == "csv":
                    cpa_status = "not_applicable_insufficient_columns"
                    subject_status = "not_applicable"
                else:
                    cpa_status = "not_applicable_non_tabular_format"
                    subject_status = "not_applicable"
                cases.append(
                    {
                        "case_id": case_id,
                        "annotation_unit": "one acquired dataset resource",
                        "primary_analysis_cluster": dataset["dataset_id"],
                        "dataset_id": dataset["dataset_id"],
                        "resource_id": resource["resource_id"],
                        "split": split,
                        "title": dataset.get("title") or "",
                        "selection_stratum": selection_by_id[
                            dataset["dataset_id"]
                        ].get("primary_format_class", "unreported"),
                        "source_detail_snapshot": dataset["detail_snapshot"],
                        "source_resource": {
                            "url": resource.get("url") or "",
                            "download_file": (
                                resource.get("download") or {}
                            ).get("file"),
                            "download_sha256": (
                                resource.get("download") or {}
                            ).get("sha256"),
                            "download_bytes": (
                                resource.get("download") or {}
                            ).get("bytes_downloaded"),
                            "content_type": (
                                resource.get("download") or {}
                            ).get("content_type"),
                        },
                        "schema_artifact": {
                            "file": schema_path.relative_to(
                                schemas_root.parent
                            ).as_posix(),
                            "sha256": schema_hash,
                        },
                        "file_format": file_format,
                        "data_modality": schema.get("data_modality") or "unknown",
                        "field_count": len(fields),
                        "field_paths": field_paths,
                        "semantic_annotation_status": (
                            "eligible_requires_independent_gold"
                            if fields
                            else "not_applicable_no_fields"
                        ),
                        "cpa_applicability_status": cpa_status,
                        "cpa_subject_column_status": subject_status,
                        "source_bundle_status": "not_built",
                    }
                )

    cases.sort(key=lambda item: item["case_id"])
    semantic_statuses = Counter(
        item["semantic_annotation_status"] for item in cases
    )
    cpa_statuses = Counter(item["cpa_applicability_status"] for item in cases)
    failure_ledgers = []
    for path in failure_ledger_paths:
        ledger = _load_json(path)
        if ledger.get("run_role") not in ALLOWED_SPLITS:
            raise NDPSemanticOpportunityError(
                "failure ledger must be development or validation"
            )
        failure_ledgers.append(
            {
                "split": ledger["run_role"],
                "file": path.name,
                "sha256": _sha256_file(path),
                "entry_count": ledger["entry_count"],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": "ndp50-external-validation-protocol/v1",
        "created_at": _utc_now(),
        "claim_boundary": (
            "Development/validation opportunity inventory only. It contains no "
            "test identities, semantic labels, subject-column labels, or gold."
        ),
        "selection": {
            "file": selection_path.name,
            "sha256": _sha256_file(selection_path),
        },
        "input_runs": sorted(input_runs, key=lambda item: item["split"]),
        "failure_ledgers": sorted(
            failure_ledgers, key=lambda item: item["split"]
        ),
        "counts": {
            "case_count": len(cases),
            "dataset_cluster_count": len(
                {item["dataset_id"] for item in cases}
            ),
            "split_case_counts": dict(
                sorted(Counter(item["split"] for item in cases).items())
            ),
            "semantic_annotation_statuses": dict(
                sorted(semantic_statuses.items())
            ),
            "cpa_applicability_statuses": dict(sorted(cpa_statuses.items())),
        },
        "cases": cases,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the NDP-50 non-test semantic opportunity inventory."
    )
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--schemas-root", type=Path, required=True)
    parser.add_argument(
        "--failure-ledger", type=Path, action="append", required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_semantic_opportunity_manifest(
        run_paths=args.run,
        selection_path=args.selection,
        schemas_root=args.schemas_root,
        failure_ledger_paths=args.failure_ledger,
    )
    _write_json(args.output, manifest)
    print(json.dumps(manifest["counts"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
