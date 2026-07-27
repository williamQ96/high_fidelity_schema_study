from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_data_governance import (
    NDPDataGovernanceError,
    build_audit,
    validate_audit,
    validate_audit_file,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_gzip(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(
    dataset_id: str,
    *,
    license_id: str | None,
    license_title: str | None,
    resource_url: str = "https://example.test/data.csv",
) -> dict:
    return {
        "schema_version": "ndp-dataset-detail-snapshot/v1",
        "source_repository": "ndp",
        "dataset_id": dataset_id,
        "request_url": (
            "https://nationaldataplatform.org/catalog/api/3/action/"
            f"package_show?id={dataset_id}"
        ),
        "retrieved_at": "2026-07-26T00:00:00Z",
        "response_sha256": "a" * 64,
        "raw_catalog_response": {
            "success": True,
            "result": {
                "id": dataset_id,
                "license_id": license_id,
                "license_title": license_title,
                "license_url": None,
                "author": None,
                "maintainer": None,
                "url": None,
                "metadata_created": "2026-01-01T00:00:00",
                "metadata_modified": "2026-01-02T00:00:00",
                "resources": [
                    {
                        "id": f"{dataset_id}-resource",
                        "url": resource_url,
                        "hash": "",
                        "last_modified": None,
                    }
                ],
            },
        },
    }


def _run(dataset_id: str, split: str) -> dict:
    return {
        "schema_version": "ndp50-execution/v2",
        "run_role": split,
        "datasets": [
            {
                "dataset_id": dataset_id,
                "resource_records": [
                    {
                        "resource_id": f"{dataset_id}-resource",
                        "plan": {"decision": "attempt"},
                        "download": {
                            "status": "acquired",
                            "sha256": "b" * 64,
                            "final_url": "https://example.test/data.csv",
                            "bytes_downloaded": 10,
                        },
                    }
                ],
            }
        ],
    }


def _fixture(tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "ndp50"
    selection = root / "selection.json"
    _write(
        selection,
        {
            "schema_version": "ndp50-selection/v1",
            "selected_datasets": [
                {"dataset_id": "dev-id", "split": "development"},
                {"dataset_id": "val-id", "split": "validation"},
                {"dataset_id": "sealed-test-id", "split": "test"},
            ],
        },
    )
    selection_hash = _sha256(selection)
    paths: dict[str, Path] = {
        "study_root": root,
        "selection_path": selection,
    }
    for split, dataset_id, license_id, license_title in (
        ("development", "dev-id", "CC0-1.0", "CC0-1.0"),
        ("validation", "val-id", None, None),
    ):
        details = root / "acquisition" / f"{split}_details"
        snapshot_path = details / f"{dataset_id}.json.gz"
        _write_gzip(
            snapshot_path,
            _snapshot(
                dataset_id,
                license_id=license_id,
                license_title=license_title,
            ),
        )
        manifest = root / "acquisition" / f"{split}_manifest.json"
        _write(
            manifest,
            {
                "schema_version": "ndp50-detail-capture-manifest/v1",
                "captured_splits": [split],
                "selection": {"sha256": selection_hash},
                "counts": {"dataset_count": 1},
                "records": [
                    {
                        "dataset_id": dataset_id,
                        "snapshot_file": snapshot_path.name,
                        "snapshot_sha256": _sha256(snapshot_path),
                    }
                ],
            },
        )
        run = root / "runs" / f"{split}_run.json"
        _write(run, _run(dataset_id, split))
        paths[f"{split}_manifest_path"] = manifest
        paths[f"{split}_details_dir"] = details
        paths[f"{split}_run_path"] = run
    return paths


def test_audit_separates_provenance_integrity_from_license_review(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    report = build_audit(**inputs)

    assert report["status"] == (
        "provenance_integrity_passed_governance_review_required"
    )
    assert report["counts"]["license_category_counts"] == {
        "missing": 1,
        "standard_or_public_domain_identifier": 1,
    }
    assert report["counts"]["acquired_payload_sha256"] == 2
    assert report["gates"]["detail_snapshot_hashes_verified"] is True
    assert report["gates"]["license_metadata_complete_and_resolvable"] is False
    assert "sealed-test-id" not in json.dumps(report, sort_keys=True)


def test_audit_is_recalculable_and_tamper_evident(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    report = build_audit(**inputs)
    assert validate_audit(report, **inputs)["status"] == "passed"

    report["counts"]["datasets"] = 99
    validation = validate_audit(report, **inputs)

    assert validation["status"] == "failed"
    assert validation["differing_top_level_keys"] == ["counts"]


def test_bound_audit_replays_from_study_relative_paths(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    report = build_audit(**inputs)

    assert (
        validate_audit_file(report, study_root=inputs["study_root"])["status"]
        == "passed"
    )


def test_detail_snapshot_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    path = inputs["development_details_dir"] / "dev-id.json.gz"
    _write_gzip(
        path,
        _snapshot(
            "dev-id",
            license_id="CC-BY-SA-4.0",
            license_title="CC-BY-SA-4.0",
        ),
    )

    with pytest.raises(NDPDataGovernanceError, match="hash mismatch"):
        build_audit(**inputs)


def test_acquired_payload_without_hash_is_rejected(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    path = inputs["development_run_path"]
    run = json.loads(path.read_text(encoding="utf-8"))
    run["datasets"][0]["resource_records"][0]["download"]["sha256"] = None
    _write(path, run)

    with pytest.raises(NDPDataGovernanceError, match="lowercase SHA-256"):
        build_audit(**inputs)


def test_non_https_catalog_transport_is_reported_not_hidden(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    snapshot_path = inputs["validation_details_dir"] / "val-id.json.gz"
    _write_gzip(
        snapshot_path,
        _snapshot(
            "val-id",
            license_id=None,
            license_title=None,
            resource_url="http://example.test/data.csv",
        ),
    )
    manifest_path = inputs["validation_manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["records"][0]["snapshot_sha256"] = _sha256(snapshot_path)
    _write(manifest_path, manifest)

    report = build_audit(**inputs)

    assert (
        report["gates"]["catalog_resource_transport_https_complete"] is False
    )
