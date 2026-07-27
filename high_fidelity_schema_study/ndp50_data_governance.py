from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence
from urllib.parse import parse_qs, urlparse


SCHEMA_VERSION = "ndp50-data-governance-audit/v1"
VALIDATION_SCHEMA_VERSION = "ndp50-data-governance-audit-validation/v1"
OPEN_SPLITS = ("development", "validation")
STANDARD_OR_PUBLIC_DOMAIN_IDS = {
    "cc-by-sa-4.0",
    "cc0-1.0",
    "cc by 4.0",
    "other-pd",
}
VAGUE_OPEN_IDS = {"other-open", "other-at"}
UNSPECIFIED_IDS = {"notspecified", "not provided"}


class NDPDataGovernanceError(ValueError):
    pass


def _load_json(path: Path) -> Dict[str, Any]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _relative(path: Path, study_root: Path) -> str:
    try:
        return path.resolve().relative_to(study_root.resolve()).as_posix()
    except ValueError as exc:
        raise NDPDataGovernanceError(
            f"audit input must be inside the study root: {path}"
        ) from exc


def _binding(path: Path, study_root: Path) -> Dict[str, str]:
    return {
        "file": _relative(path, study_root),
        "sha256": _sha256_file(path),
    }


def _is_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(char in "0123456789abcdef" for char in text)


def _is_utc_timestamp(value: Any) -> bool:
    text = str(value or "")
    if not text.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _license_category(license_id: Any, license_title: Any) -> str:
    identifier = str(license_id or "").strip().casefold()
    title = str(license_title or "").strip().casefold()
    if not identifier and not title:
        return "missing"
    if identifier in UNSPECIFIED_IDS or title in UNSPECIFIED_IDS:
        return "explicitly_unspecified"
    if identifier in VAGUE_OPEN_IDS:
        return "vague_open_or_attribution"
    if identifier in STANDARD_OR_PUBLIC_DOMAIN_IDS:
        return "standard_or_public_domain_identifier"
    return "other_identifier_requires_review"


def _selected_ids(selection: Mapping[str, Any], split: str) -> set[str]:
    return {
        str(item.get("dataset_id") or "")
        for item in selection.get("selected_datasets") or []
        if item.get("split") == split
    }


def _validate_manifest(
    manifest: Mapping[str, Any],
    *,
    split: str,
    selection_hash: str,
    expected_ids: set[str],
) -> None:
    if manifest.get("schema_version") != "ndp50-detail-capture-manifest/v1":
        raise NDPDataGovernanceError(f"unexpected {split} detail-manifest schema")
    if manifest.get("captured_splits") != [split]:
        raise NDPDataGovernanceError(
            f"{split} detail manifest must contain exactly its own split"
        )
    if manifest.get("selection", {}).get("sha256") != selection_hash:
        raise NDPDataGovernanceError(
            f"{split} detail manifest does not bind the selection"
        )
    records = manifest.get("records")
    if not isinstance(records, list):
        raise NDPDataGovernanceError(f"{split} manifest records must be a list")
    actual_ids = [str(item.get("dataset_id") or "") for item in records]
    if (
        not all(actual_ids)
        or len(actual_ids) != len(set(actual_ids))
        or set(actual_ids) != expected_ids
    ):
        raise NDPDataGovernanceError(
            f"{split} manifest dataset identity does not match selection"
        )
    if manifest.get("counts", {}).get("dataset_count") != len(records):
        raise NDPDataGovernanceError(
            f"{split} manifest declared dataset count is inconsistent"
        )


def _validate_run(
    run: Mapping[str, Any],
    *,
    split: str,
    expected_ids: set[str],
) -> Dict[str, Mapping[str, Any]]:
    if run.get("schema_version") != "ndp50-execution/v2":
        raise NDPDataGovernanceError(f"unexpected {split} run schema")
    if run.get("run_role") != split:
        raise NDPDataGovernanceError(f"{split} run has the wrong role")
    datasets = run.get("datasets")
    if not isinstance(datasets, list):
        raise NDPDataGovernanceError(f"{split} run datasets must be a list")
    by_id = {str(item.get("dataset_id") or ""): item for item in datasets}
    if "" in by_id or len(by_id) != len(datasets) or set(by_id) != expected_ids:
        raise NDPDataGovernanceError(
            f"{split} run dataset identity does not match selection"
        )
    return by_id


def _resource_audit(
    resources: Sequence[Mapping[str, Any]],
) -> Dict[str, int]:
    return {
        "resource_count": len(resources),
        "https_url_count": sum(
            str(item.get("url") or "").startswith("https://")
            for item in resources
        ),
        "catalog_hash_present_count": sum(
            bool(str(item.get("hash") or "").strip()) for item in resources
        ),
        "last_modified_present_count": sum(
            bool(str(item.get("last_modified") or "").strip())
            for item in resources
        ),
    }


def _acquisition_audit(dataset: Mapping[str, Any]) -> Dict[str, int]:
    records = dataset.get("resource_records")
    if not isinstance(records, list):
        raise NDPDataGovernanceError("run resource_records must be a list")
    attempted = [
        item for item in records if item.get("plan", {}).get("decision") == "attempt"
    ]
    acquired = [
        item for item in attempted if item.get("download", {}).get("status") == "acquired"
    ]
    invalid_hashes = [
        item
        for item in acquired
        if not _is_sha256(item.get("download", {}).get("sha256"))
    ]
    if invalid_hashes:
        raise NDPDataGovernanceError(
            "every acquired payload must have a lowercase SHA-256"
        )
    return {
        "run_resource_record_count": len(records),
        "attempted_resource_count": len(attempted),
        "acquired_resource_count": len(acquired),
        "acquired_payload_sha256_count": len(acquired),
        "acquired_https_final_url_count": sum(
            str(item.get("download", {}).get("final_url") or "").startswith(
                "https://"
            )
            for item in acquired
        ),
        "acquired_bytes": sum(
            int(item.get("download", {}).get("bytes_downloaded") or 0)
            for item in acquired
        ),
    }


def build_audit(
    *,
    selection_path: Path,
    development_manifest_path: Path,
    development_details_dir: Path,
    development_run_path: Path,
    validation_manifest_path: Path,
    validation_details_dir: Path,
    validation_run_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    file_paths = {
        "selection": selection_path,
        "development_manifest": development_manifest_path,
        "development_run": development_run_path,
        "validation_manifest": validation_manifest_path,
        "validation_run": validation_run_path,
    }
    for label, path in file_paths.items():
        if not path.is_file():
            raise NDPDataGovernanceError(f"{label} does not exist: {path}")
    for label, path in (
        ("development_details", development_details_dir),
        ("validation_details", validation_details_dir),
    ):
        if not path.is_dir():
            raise NDPDataGovernanceError(f"{label} does not exist: {path}")

    selection = _load_json(selection_path)
    if selection.get("schema_version") != "ndp50-selection/v1":
        raise NDPDataGovernanceError("unexpected selection schema")
    selection_hash = _sha256_file(selection_path)
    split_inputs = {
        "development": (
            development_manifest_path,
            development_details_dir,
            development_run_path,
        ),
        "validation": (
            validation_manifest_path,
            validation_details_dir,
            validation_run_path,
        ),
    }
    records: list[Dict[str, Any]] = []
    for split, (manifest_path, details_dir, run_path) in split_inputs.items():
        expected_ids = _selected_ids(selection, split)
        manifest = _load_json(manifest_path)
        _validate_manifest(
            manifest,
            split=split,
            selection_hash=selection_hash,
            expected_ids=expected_ids,
        )
        run_by_id = _validate_run(
            _load_json(run_path),
            split=split,
            expected_ids=expected_ids,
        )
        for manifest_item in manifest["records"]:
            dataset_id = str(manifest_item["dataset_id"])
            snapshot_path = details_dir / str(manifest_item["snapshot_file"])
            if not snapshot_path.is_file():
                raise NDPDataGovernanceError(
                    f"missing {split} detail snapshot for {dataset_id}"
                )
            if _sha256_file(snapshot_path) != manifest_item.get("snapshot_sha256"):
                raise NDPDataGovernanceError(
                    f"detail snapshot hash mismatch for {dataset_id}"
                )
            snapshot = _load_json(snapshot_path)
            if (
                snapshot.get("schema_version")
                != "ndp-dataset-detail-snapshot/v1"
            ):
                raise NDPDataGovernanceError(
                    f"unexpected detail snapshot schema for {dataset_id}"
                )
            if (
                snapshot.get("dataset_id") != dataset_id
                or snapshot.get("source_repository") != "ndp"
                or not str(snapshot.get("request_url") or "").startswith(
                    "https://nationaldataplatform.org/"
                )
                or not _is_utc_timestamp(snapshot.get("retrieved_at"))
                or not _is_sha256(snapshot.get("response_sha256"))
            ):
                raise NDPDataGovernanceError(
                    f"invalid snapshot provenance for {dataset_id}"
                )
            query_id = parse_qs(urlparse(snapshot["request_url"]).query).get(
                "id", []
            )
            if query_id != [dataset_id]:
                raise NDPDataGovernanceError(
                    f"snapshot request identity mismatch for {dataset_id}"
                )
            raw_response = snapshot.get("raw_catalog_response")
            if (
                not isinstance(raw_response, dict)
                or raw_response.get("success") is not True
                or raw_response.get("result", {}).get("id") != dataset_id
            ):
                raise NDPDataGovernanceError(
                    f"raw CKAN response identity mismatch for {dataset_id}"
                )
            dataset = raw_response["result"]
            resources = dataset.get("resources")
            if not isinstance(resources, list):
                raise NDPDataGovernanceError(
                    f"CKAN resources must be a list for {dataset_id}"
                )
            resource_summary = _resource_audit(resources)
            acquisition_summary = _acquisition_audit(run_by_id[dataset_id])
            if (
                acquisition_summary["run_resource_record_count"]
                != resource_summary["resource_count"]
            ):
                raise NDPDataGovernanceError(
                    f"run and catalog resource counts disagree for {dataset_id}"
                )
            license_id = str(dataset.get("license_id") or "").strip()
            license_title = str(dataset.get("license_title") or "").strip()
            records.append(
                {
                    "dataset_id": dataset_id,
                    "split": split,
                    "detail_snapshot_sha256": manifest_item["snapshot_sha256"],
                    "catalog_response_body_sha256": snapshot["response_sha256"],
                    "retrieved_at": snapshot["retrieved_at"],
                    "metadata_created_present": bool(
                        str(dataset.get("metadata_created") or "").strip()
                    ),
                    "metadata_modified_present": bool(
                        str(dataset.get("metadata_modified") or "").strip()
                    ),
                    "license": {
                        "license_id": license_id or None,
                        "license_title": license_title or None,
                        "license_url": (
                            str(dataset.get("license_url") or "").strip() or None
                        ),
                        "category": _license_category(
                            license_id, license_title
                        ),
                    },
                    "attribution": {
                        "author_present": bool(
                            str(dataset.get("author") or "").strip()
                        ),
                        "maintainer_present": bool(
                            str(dataset.get("maintainer") or "").strip()
                        ),
                        "dataset_url_present": bool(
                            str(dataset.get("url") or "").strip()
                        ),
                    },
                    "catalog_resources": resource_summary,
                    "acquisition": acquisition_summary,
                }
            )
    records.sort(key=lambda item: (item["split"], item["dataset_id"]))

    test_ids = _selected_ids(selection, "test")
    serialized_records = json.dumps(records, sort_keys=True)
    leaked_test_ids = sorted(
        dataset_id for dataset_id in test_ids if dataset_id in serialized_records
    )
    if leaked_test_ids:
        raise NDPDataGovernanceError(
            "data-governance audit unexpectedly contains test identities"
        )

    license_counts = Counter(
        item["license"]["category"] for item in records
    )
    resource_count = sum(
        item["catalog_resources"]["resource_count"] for item in records
    )
    resource_https_count = sum(
        item["catalog_resources"]["https_url_count"] for item in records
    )
    acquired_count = sum(
        item["acquisition"]["acquired_resource_count"] for item in records
    )
    acquired_hash_count = sum(
        item["acquisition"]["acquired_payload_sha256_count"] for item in records
    )
    acquired_https_count = sum(
        item["acquisition"]["acquired_https_final_url_count"]
        for item in records
    )
    license_metadata_complete = all(
        item["license"]["category"]
        == "standard_or_public_domain_identifier"
        and item["license"]["license_url"] is not None
        for item in records
    )
    implementation = Path(__file__).resolve()
    return {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "provenance_integrity_passed_governance_review_required"
        ),
        "scope": {
            "included_splits": list(OPEN_SPLITS),
            "dataset_count": len(records),
            "test_dataset_detail_count": 0,
            "test_dataset_identities_included": False,
            "claim_boundary": (
                "This audit verifies archived provenance and reports catalog "
                "governance metadata. It is not legal advice and does not "
                "grant redistribution or external data-transfer permission."
            ),
        },
        "artifact_bindings": {
            key: _binding(path, study_root) for key, path in file_paths.items()
        },
        "detail_directories": {
            "development": _relative(development_details_dir, study_root),
            "validation": _relative(validation_details_dir, study_root),
        },
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "counts": {
            "datasets": len(records),
            "license_category_counts": dict(sorted(license_counts.items())),
            "license_url_present": sum(
                item["license"]["license_url"] is not None for item in records
            ),
            "author_or_maintainer_present": sum(
                item["attribution"]["author_present"]
                or item["attribution"]["maintainer_present"]
                for item in records
            ),
            "catalog_resources": resource_count,
            "catalog_resources_https": resource_https_count,
            "catalog_resource_hashes_present": sum(
                item["catalog_resources"]["catalog_hash_present_count"]
                for item in records
            ),
            "catalog_resource_last_modified_present": sum(
                item["catalog_resources"]["last_modified_present_count"]
                for item in records
            ),
            "acquired_resources": acquired_count,
            "acquired_payload_sha256": acquired_hash_count,
            "acquired_https_final_urls": acquired_https_count,
            "acquired_bytes": sum(
                item["acquisition"]["acquired_bytes"] for item in records
            ),
        },
        "gates": {
            "detail_snapshot_hashes_verified": True,
            "dataset_identity_verified": True,
            "catalog_resource_transport_https_complete": (
                resource_count == resource_https_count
            ),
            "acquired_payload_hashes_complete": (
                acquired_count == acquired_hash_count
            ),
            "acquired_transport_https_complete": (
                acquired_count == acquired_https_count
            ),
            "catalog_response_body_hash_recomputable_from_archive": False,
            "license_metadata_complete_and_resolvable": (
                license_metadata_complete
            ),
            "human_license_and_attribution_review_complete": False,
            "external_model_data_transfer_policy_frozen": False,
            "artifact_redistribution_policy_frozen": False,
            "test_split_unopened": True,
        },
        "limitations": [
            (
                "The original CKAN response bytes are not archived; the "
                "captured response-body SHA-256 cannot be independently "
                "recomputed from the parsed snapshot."
            ),
            (
                "Catalog resource hashes are provider metadata and are absent "
                "for most or all resources; locally acquired payload hashes "
                "are reported separately."
            ),
            (
                "License identifiers and titles are catalog assertions. "
                "Missing or vague metadata requires source-level human review."
            ),
        ],
        "required_actions": [
            (
                "Resolve and record authoritative license terms and attribution "
                "requirements for every analyzed dataset."
            ),
            (
                "Freeze whether semantic processing is local-only or permits "
                "external model transfer, including retention and redaction."
            ),
            (
                "Freeze which metadata, samples, schemas, and raw payloads may "
                "be redistributed with the research artifact."
            ),
            (
                "Capture an immutable review record without treating this "
                "automated audit as legal approval."
            ),
        ],
        "datasets": records,
    }


def validate_audit(
    payload: Mapping[str, Any],
    **kwargs: Any,
) -> Dict[str, Any]:
    expected = build_audit(**kwargs)
    differing = sorted(
        key
        for key in set(payload) | set(expected)
        if payload.get(key) != expected.get(key)
    )
    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "status": "passed" if not differing else "failed",
        "differing_top_level_keys": differing,
    }


def validate_audit_file(
    payload: Mapping[str, Any],
    *,
    study_root: Path,
) -> Dict[str, Any]:
    bindings = payload.get("artifact_bindings")
    detail_directories = payload.get("detail_directories")
    if not isinstance(bindings, dict) or not isinstance(
        detail_directories, dict
    ):
        return {
            "schema_version": VALIDATION_SCHEMA_VERSION,
            "status": "failed",
            "differing_top_level_keys": ["artifact_bindings"],
        }

    root = study_root.resolve()

    def resolve_file(binding_key: str) -> Path:
        relative = str(bindings.get(binding_key, {}).get("file") or "")
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise NDPDataGovernanceError(
                f"{binding_key} resolves outside the study root"
            ) from exc
        if not candidate.is_file():
            raise NDPDataGovernanceError(
                f"{binding_key} does not resolve to a file"
            )
        return candidate

    def resolve_dir(split: str) -> Path:
        relative = str(detail_directories.get(split) or "")
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise NDPDataGovernanceError(
                f"{split} details resolve outside the study root"
            ) from exc
        if not candidate.is_dir():
            raise NDPDataGovernanceError(
                f"{split} details do not resolve to a directory"
            )
        return candidate

    return validate_audit(
        payload,
        selection_path=resolve_file("selection"),
        development_manifest_path=resolve_file("development_manifest"),
        development_details_dir=resolve_dir("development"),
        development_run_path=resolve_file("development_run"),
        validation_manifest_path=resolve_file("validation_manifest"),
        validation_details_dir=resolve_dir("validation"),
        validation_run_path=resolve_file("validation_run"),
        study_root=root,
    )


def _add_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--development-manifest", type=Path, required=True)
    parser.add_argument("--development-details-dir", type=Path, required=True)
    parser.add_argument("--development-run", type=Path, required=True)
    parser.add_argument("--validation-manifest", type=Path, required=True)
    parser.add_argument("--validation-details-dir", type=Path, required=True)
    parser.add_argument("--validation-run", type=Path, required=True)
    parser.add_argument("--study-root", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or validate the NDP-50 data-governance audit."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    _add_inputs(build)
    build.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate")
    _add_inputs(validate)
    validate.add_argument("--artifact", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kwargs = {
        "selection_path": args.selection,
        "development_manifest_path": args.development_manifest,
        "development_details_dir": args.development_details_dir,
        "development_run_path": args.development_run,
        "validation_manifest_path": args.validation_manifest,
        "validation_details_dir": args.validation_details_dir,
        "validation_run_path": args.validation_run,
        "study_root": args.study_root,
    }
    if args.command == "build":
        payload = build_audit(**kwargs)
        _write_json(args.output, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "datasets": payload["counts"]["datasets"],
                    "license_category_counts": payload["counts"][
                        "license_category_counts"
                    ],
                    "acquired_payload_sha256": payload["counts"][
                        "acquired_payload_sha256"
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    payload = _load_json(args.artifact)
    report = validate_audit(payload, **kwargs)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
