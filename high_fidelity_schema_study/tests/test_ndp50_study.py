from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_study import (
    ADAPTER_ID,
    DESIGN_SCHEMA_VERSION,
    DETAIL_SNAPSHOT_SCHEMA_VERSION,
    INDEX_SNAPSHOT_SCHEMA_VERSION,
    NDPStudyError,
    build_index_frame,
    build_selection,
    normalize_detail_snapshot,
    normalize_index_snapshot,
)


def _write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _index_record(
    dataset_id: str, organization: str, resource_format: str
) -> dict:
    return {
        "id": dataset_id,
        "name": f"name-{dataset_id}",
        "title": f"Title {dataset_id}",
        "organization": organization,
        "metadata_modified": "2026-07-26T00:00:00Z",
        "res_format": [resource_format],
    }


def _index_snapshot(records: list[dict]) -> dict:
    return {
        "schema_version": INDEX_SNAPSHOT_SCHEMA_VERSION,
        "adapter_id": ADAPTER_ID,
        "source_repository": "ndp",
        "page_ordinal": 1,
        "request_url": (
            "https://nationaldataplatform.org/catalog/api/3/action/"
            "package_search?q=*:*&rows=6000&start=0"
            "&fl=id,name,title,organization,metadata_modified,res_format"
            "&sort=id%20asc"
        ),
        "retrieved_at": "2026-07-26T00:00:00Z",
        "response_sha256": "0" * 64,
        "raw_catalog_response": {
            "success": True,
            "result": {"count": len(records), "results": records},
        },
    }


def test_index_frame_requires_complete_catalog_capture(tmp_path: Path) -> None:
    snapshot = _index_snapshot(
        [_index_record("d1", "org-a", "CSV"), _index_record("d2", "org-b", "HDF5")]
    )
    snapshot["raw_catalog_response"]["result"]["count"] = 3
    path = tmp_path / "index.json"
    _write(path, snapshot)

    assert normalize_index_snapshot(path)["returned_dataset_count"] == 2
    with pytest.raises(NDPStudyError, match="complete catalog identity frame"):
        build_index_frame(
            snapshot_paths=[path],
            frame_scope="incomplete test frame",
            frozen_at="2026-07-26T00:00:00Z",
        )


def test_detail_normalization_preserves_declared_observed_conflict(
    tmp_path: Path,
) -> None:
    payload = {
        "schema_version": DETAIL_SNAPSHOT_SCHEMA_VERSION,
        "adapter_id": ADAPTER_ID,
        "source_repository": "ndp",
        "dataset_id": "d1",
        "request_url": (
            "https://nationaldataplatform.org/catalog/api/3/action/"
            "package_show?id=d1"
        ),
        "retrieved_at": "2026-07-26T00:00:00Z",
        "response_sha256": "0" * 64,
        "raw_catalog_response": {
            "success": True,
            "result": {
                "id": "d1",
                "name": "weather",
                "title": "Weather",
                "type": "dataset",
                "notes": "Hourly observations",
                "owner_org": "org-a",
                "organization": {"id": "org-a", "title": "Org A"},
                "metadata_created": "2026-01-01T00:00:00Z",
                "metadata_modified": "2026-07-26T00:00:00Z",
                "license_id": "cc-by",
                "tags": [{"name": "weather"}],
                "extras": [
                    {"key": "uploadType", "value": "dataset"},
                    {"key": "dataAuthType", "value": "public"},
                    {"key": "theme", "value": '["climate"]'},
                    {"key": "columnDataDict", "value": '[{"name":"temp"}]'},
                ],
                "resources": [
                    {
                        "id": "r1",
                        "name": "weather.csv",
                        "url": "https://example.org/weather.csv",
                        "format": "JSON",
                        "mimetype": "text/csv",
                        "size": 10,
                    }
                ],
            },
        },
    }
    path = tmp_path / "detail.json"
    _write(path, payload)

    normalized = normalize_detail_snapshot(path)["dataset"]

    assert normalized["selection_eligible"] is True
    assert normalized["scientific_family"] == "climate"
    assert normalized["supported_resource_count"] == 1
    assert normalized["format_conflict_resource_count"] == 1
    resource = normalized["resources"][0]
    assert resource["normalized_format"] == "json"
    assert resource["format_signals"] == {
        "declared": "json",
        "mimetype": "csv",
        "suffix": "csv",
    }


def test_selection_is_deterministic_and_honors_frozen_split_quotas(
    tmp_path: Path,
) -> None:
    records = [
        _index_record("t1", "org-a", "CSV"),
        _index_record("t2", "org-b", "CSV"),
        _index_record("t3", "org-c", "CSV"),
        _index_record("t4", "org-d", "CSV"),
        _index_record("h1", "org-a", "HDF5"),
        _index_record("h2", "org-b", "HDF5"),
        _index_record("h3", "org-c", "HDF5"),
        _index_record("h4", "org-d", "HDF5"),
    ]
    snapshot_path = tmp_path / "index.json"
    _write(snapshot_path, _index_snapshot(records))
    frame_payload = build_index_frame(
        snapshot_paths=[snapshot_path],
        frame_scope="test frame",
        frozen_at="2026-07-26T00:00:00Z",
    )
    frame_path = tmp_path / "frame.json"
    _write(frame_path, frame_payload)
    design = {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "protocol_version": "ndp50-external-validation-protocol/v1",
        "status": "frozen_before_selection",
        "candidate_frame_sha256": _sha256(frame_path),
        "seed": "unit-test-seed",
        "target_count": 4,
        "max_per_organization": 2,
        "split_counts": {"development": 2, "test": 1, "validation": 1},
        "strata": {
            "supported_hierarchical": {
                "development": 1,
                "validation": 0,
                "test": 1,
                "reserve": 1,
            },
            "supported_tabular": {
                "development": 1,
                "validation": 1,
                "test": 0,
                "reserve": 1,
            },
        },
    }
    design_path = tmp_path / "design.json"
    _write(design_path, design)

    first = build_selection(
        frame_path=frame_path,
        design_path=design_path,
        selected_at="2026-07-26T00:00:00Z",
    )
    second = build_selection(
        frame_path=frame_path,
        design_path=design_path,
        selected_at="2026-07-26T00:00:00Z",
    )

    assert first == second
    assert first["counts"]["selected_dataset_count"] == 4
    assert first["counts"]["split_counts"] == {
        "development": 2,
        "test": 1,
        "validation": 1,
    }
    assert first["counts"]["stratum_counts"] == {
        "supported_hierarchical": 2,
        "supported_tabular": 2,
    }
    assert len(first["deterministic_reserves"]) == 2
