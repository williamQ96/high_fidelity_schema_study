from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest
import high_fidelity_schema_study.semantic_catalog_acquisition as catalog_adapter

from high_fidelity_schema_study.semantic_catalog_acquisition import (
    ADAPTER_ID,
    CatalogSnapshotError,
    capture_catalog_snapshot,
    normalize_catalog_snapshot,
)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_zenodo_snapshot_expands_every_file_resource(tmp_path: Path) -> None:
    path = tmp_path / "zenodo.json"
    write_json(
        path,
        {
            "schema_version": "semantic-catalog-snapshot/v1",
            "adapter_id": ADAPTER_ID,
            "source_repository": "zenodo",
            "page_ordinal": 1,
            "request_url": "https://zenodo.org/api/records?page=1",
            "retrieved_at": "2026-07-16T00:00:00Z",
            "raw_catalog_response": {
                "hits": {
                    "hits": [
                        {
                            "id": 123,
                            "conceptrecid": "100",
                            "metadata": {
                                "rights": [{"id": "cc-by-4.0"}],
                                "subjects": [{"subject": "Oceanography"}],
                            },
                            "files": [
                                {
                                    "key": "measurements.csv",
                                    "size": 1234,
                                    "checksum": "md5:abc",
                                    "links": {
                                        "self": "https://zenodo.org/api/records/123/files/measurements.csv/content"
                                    },
                                },
                                {
                                    "key": "README.txt",
                                    "size": 100,
                                    "checksum": "md5:def",
                                    "links": {
                                        "self": "https://zenodo.org/api/records/123/files/README.txt/content"
                                    },
                                },
                            ],
                        }
                    ]
                }
            },
        },
    )

    normalized = normalize_catalog_snapshot(path)

    assert normalized["returned_dataset_record_count"] == 1
    assert normalized["enumerated_resource_count"] == 2
    by_id = {item["source_resource_id"]: item for item in normalized["resources"]}
    assert by_id["measurements.csv"]["file_format"] == "csv"
    assert by_id["README.txt"]["file_format"] == "unsupported"
    assert by_id["measurements.csv"]["source_record_id"] == "record_123"


def test_capture_rejects_nonofficial_catalog_host() -> None:
    with pytest.raises(CatalogSnapshotError, match="official HTTPS host"):
        capture_catalog_snapshot(
            repository="zenodo",
            request_url="https://example.test/api/records",
            page_ordinal=1,
            timeout_seconds=1.0,
        )


def test_dryad_snapshot_requires_expansion_for_every_dataset(tmp_path: Path) -> None:
    path = tmp_path / "dryad.json"
    payload = {
        "schema_version": "semantic-catalog-snapshot/v1",
        "adapter_id": ADAPTER_ID,
        "source_repository": "dryad",
        "page_ordinal": 1,
        "request_url": "https://datadryad.org/api/v2/search?page=1",
        "retrieved_at": "2026-07-16T00:00:00Z",
        "raw_catalog_response": {
            "_embedded": {
                "stash:datasets": [
                    {
                        "identifier": "doi:10.5061/dryad.abc123",
                        "license": "https://spdx.org/licenses/CC0-1.0.html",
                        "fieldOfScience": "Earth sciences",
                    }
                ]
            }
        },
        "dataset_expansions": [],
    }
    write_json(path, payload)

    with pytest.raises(CatalogSnapshotError, match="cover every returned dataset"):
        normalize_catalog_snapshot(path)


def test_dryad_snapshot_normalizes_checksum_and_download_url(tmp_path: Path) -> None:
    path = tmp_path / "dryad.json"
    write_json(
        path,
        {
            "schema_version": "semantic-catalog-snapshot/v1",
            "adapter_id": ADAPTER_ID,
            "source_repository": "dryad",
            "page_ordinal": 1,
            "request_url": "https://datadryad.org/api/v2/search?page=1",
            "retrieved_at": "2026-07-16T00:00:00Z",
            "raw_catalog_response": {
                "_embedded": {
                    "stash:datasets": [
                        {
                            "identifier": "doi:10.5061/dryad.abc123",
                            "license": "https://spdx.org/licenses/CC0-1.0.html",
                            "fieldOfScience": "Earth sciences",
                        }
                    ]
                }
            },
            "dataset_expansions": [
                {
                    "identifier": "doi:10.5061/dryad.abc123",
                    "files_response": {
                        "_embedded": {
                            "stash:files": [
                                {
                                    "path": "observations.h5",
                                    "size": 4321,
                                    "digest": "abcdef",
                                    "digestType": "sha-256",
                                    "_links": {
                                        "stash:download": {
                                            "href": "/api/v2/files/42/download"
                                        }
                                    },
                                }
                            ]
                        }
                    },
                }
            ],
        },
    )

    normalized = normalize_catalog_snapshot(path)

    resource = normalized["resources"][0]
    assert resource["source_record_id"] == "10.5061_dryad.abc123"
    assert resource["provider_checksum"] == "sha-256:abcdef"
    assert resource["source_url"] == "https://datadryad.org/api/v2/files/42/download"
    assert resource["file_format"] == "hdf5"


def test_checked_in_catalog_adapter_smoke_is_reproducible() -> None:
    package_root = Path(__file__).resolve().parents[1]
    smoke_root = (
        package_root
        / "data"
        / "experiments"
        / "semantic_blind_sampling_v1"
        / "catalog_adapter_smoke"
    )
    manifest = json.loads((smoke_root / "manifest.json").read_text(encoding="utf-8"))
    adapter_path = (smoke_root / manifest["adapter"]["file"]).resolve()
    assert adapter_path == Path(catalog_adapter.__file__).resolve()
    assert sha256_file(adapter_path) == manifest["adapter"]["sha256"]
    for record in manifest["snapshots"]:
        snapshot_path = smoke_root / record["file"]
        assert sha256_file(snapshot_path) == record["sha256"]
        normalized = normalize_catalog_snapshot(snapshot_path)
        assert (
            normalized["returned_dataset_record_count"]
            == record["returned_dataset_record_count"]
        )
        assert (
            normalized["enumerated_resource_count"]
            == record["enumerated_resource_count"]
        )
        supported = sum(
            resource["file_format"] != "unsupported"
            for resource in normalized["resources"]
        )
        assert supported == record["supported_resource_count"]
