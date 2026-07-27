from __future__ import annotations

import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_execution import (
    NDPExecutionError,
    ResourcePolicy,
    acquire_resource,
    assess_downloaded_payload,
    authorize_run_role,
    plan_dataset_resources,
)


def _resource(resource_id: str, file_format: str, *, http: bool = True) -> dict:
    return {
        "resource_id": resource_id,
        "normalized_format": file_format,
        "http_access_url": http,
    }


def test_resource_plan_is_stable_and_bounded() -> None:
    dataset = {
        "resources": [
            _resource("r3", "csv"),
            _resource("r1", "zarr"),
            _resource("r4", "json"),
            _resource("r2", "csv"),
            _resource("r5", "image"),
        ]
    }
    plan = {
        item["resource_id"]: item["decision"]
        for item in plan_dataset_resources(
            dataset, ResourcePolicy(max_resources_per_dataset=2)
        )
    }

    assert plan == {
        "r1": "skip_remote_store_locator_incomplete",
        "r2": "attempt",
        "r3": "attempt",
        "r4": "skip_dataset_resource_cap",
        "r5": "skip_unsupported_format",
    }


def test_resource_plan_rejects_non_http_transport() -> None:
    dataset = {"resources": [_resource("r1", "csv", http=False)]}
    plan = plan_dataset_resources(dataset, ResourcePolicy())

    assert plan[0]["decision"] == "skip_unsupported_transport"


def test_resource_plan_rejects_duplicate_resource_identity() -> None:
    dataset = {"resources": [_resource("r1", "csv"), _resource("r1", "csv")]}

    with pytest.raises(NDPExecutionError, match="duplicate resource IDs"):
        plan_dataset_resources(dataset, ResourcePolicy())


def test_held_out_roles_require_explicit_authorization() -> None:
    authorize_run_role("development", None)
    with pytest.raises(NDPExecutionError, match="authorization freeze"):
        authorize_run_role("validation", None)
    with pytest.raises(NDPExecutionError, match="authorization freeze"):
        authorize_run_role("test", None)


def test_test_role_rejects_structural_validation_only_freeze(
    tmp_path: Path,
) -> None:
    freeze = tmp_path / "freeze.json"
    freeze.write_text(
        json.dumps(
            {
                "schema_version": "ndp50-structural-validation-freeze/v1",
                "readiness_boundaries": {
                    "structural_validation_authorized": True,
                    "test_authorized": False,
                },
                "implementation_hashes": {},
            }
        ),
        encoding="utf-8",
    )

    authorize_run_role("validation", freeze)
    with pytest.raises(NDPExecutionError, match="does not permit test"):
        authorize_run_role("test", freeze)


def test_provider_export_status_is_not_treated_as_dataset(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "download"
    payload.write_text(
        json.dumps(
            {
                "message": "Please check back later.",
                "status": "ExportingData",
                "progressInPercent": 68,
            }
        ),
        encoding="utf-8",
    )

    assessment = assess_downloaded_payload(
        payload, {"content_type": "application/json"}
    )

    assert assessment["status"] == "provider_export_pending"
    assert assessment["reason"]["code"] == "provider_control_response"


def test_provider_export_retry_is_bounded_and_auditable(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "payload"
    calls = 0
    sleeps = []

    def fake_download(**kwargs):
        nonlocal calls
        calls += 1
        if calls < 3:
            destination.write_text(
                json.dumps(
                    {
                        "message": "Please check back later.",
                        "status": "Pending",
                    }
                ),
                encoding="utf-8",
            )
            return {
                "status": "acquired",
                "content_type": "application/json",
                "bytes_downloaded": destination.stat().st_size,
                "sha256": f"pending-{calls}",
                "failure": None,
            }
        destination.write_text("a,b\n1,2\n", encoding="utf-8")
        return {
            "status": "acquired",
            "content_type": "text/csv",
            "bytes_downloaded": destination.stat().st_size,
            "sha256": "data",
            "failure": None,
        }

    result = acquire_resource(
        resource={"url": "https://example.invalid/data.csv"},
        destination=destination,
        policy=ResourcePolicy(
            max_download_attempts=3, retry_delay_seconds=7
        ),
        remaining_dataset_bytes=1000,
        sleep_fn=sleeps.append,
        download_fn=fake_download,
    )

    assert result["status"] == "acquired"
    assert result["attempt_count"] == 3
    assert [item["status"] for item in result["attempts"]] == [
        "provider_export_pending",
        "provider_export_pending",
        "acquired",
    ]
    assert sleeps == [7, 7]
    assert result["transfer_bytes"] == sum(
        item["bytes_downloaded"] for item in result["attempts"]
    )


def test_provider_export_retry_stops_at_frozen_attempt_limit(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "payload"

    def pending_download(**kwargs):
        destination.write_text(
            json.dumps({"message": "wait", "status": "Pending"}),
            encoding="utf-8",
        )
        return {
            "status": "acquired",
            "content_type": "application/json",
            "bytes_downloaded": destination.stat().st_size,
            "failure": None,
        }

    result = acquire_resource(
        resource={"url": "https://example.invalid/data.csv"},
        destination=destination,
        policy=ResourcePolicy(
            max_download_attempts=2, retry_delay_seconds=0
        ),
        remaining_dataset_bytes=1000,
        sleep_fn=lambda _: None,
        download_fn=pending_download,
    )

    assert result["status"] == "provider_export_pending"
    assert result["attempt_count"] == 2
