from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Callable, Dict, Iterable, List, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .extractors.base import ExtractionRequest
from .extractors.registry import extract_path
from .ndp50_study import normalize_detail_snapshot


EXECUTION_SCHEMA_VERSION = "ndp50-execution/v2"
FILE_EXTRACTABLE_FORMATS = {"csv", "hdf5", "json", "netcdf", "parquet", "xml"}
REMOTE_DIRECTORY_FORMATS = {"zarr"}
RUN_ROLES = {"development", "validation", "test"}


class NDPExecutionError(ValueError):
    pass


@dataclass(frozen=True)
class ResourcePolicy:
    max_resources_per_dataset: int = 3
    max_bytes_per_resource: int = 25 * 1024 * 1024
    max_bytes_per_dataset: int = 50 * 1024 * 1024
    timeout_seconds: float = 90.0
    sample_limit: int = 200
    max_download_attempts: int = 3
    retry_delay_seconds: float = 10.0

    def validate(self) -> None:
        if self.max_resources_per_dataset <= 0:
            raise NDPExecutionError("max_resources_per_dataset must be positive")
        if self.max_bytes_per_resource <= 0:
            raise NDPExecutionError("max_bytes_per_resource must be positive")
        if self.max_bytes_per_dataset <= 0:
            raise NDPExecutionError("max_bytes_per_dataset must be positive")
        if self.timeout_seconds <= 0:
            raise NDPExecutionError("timeout_seconds must be positive")
        if self.sample_limit <= 0:
            raise NDPExecutionError("sample_limit must be positive")
        if self.max_download_attempts <= 0:
            raise NDPExecutionError("max_download_attempts must be positive")
        if self.retry_delay_seconds < 0:
            raise NDPExecutionError("retry_delay_seconds cannot be negative")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def authorize_run_role(
    run_role: str, authorization_freeze: Path | None
) -> None:
    if run_role not in RUN_ROLES:
        raise NDPExecutionError(f"unsupported run role: {run_role}")
    if run_role == "development":
        return
    if authorization_freeze is None:
        raise NDPExecutionError(
            f"{run_role} execution requires an authorization freeze"
        )
    freeze = json.loads(authorization_freeze.read_text(encoding="utf-8"))
    if freeze.get("schema_version") != "ndp50-structural-validation-freeze/v1":
        raise NDPExecutionError("authorization freeze schema is invalid")
    boundary = (
        "structural_validation_authorized"
        if run_role == "validation"
        else "test_authorized"
    )
    if (freeze.get("readiness_boundaries") or {}).get(boundary) is not True:
        raise NDPExecutionError(f"authorization freeze does not permit {run_role}")
    expected_hashes = freeze.get("implementation_hashes") or {}
    package_root = Path(__file__).resolve().parent
    for relative_path, expected_hash in expected_hashes.items():
        source_path = package_root / relative_path
        if not source_path.is_file() or _sha256_file(source_path) != expected_hash:
            raise NDPExecutionError(
                f"implementation hash mismatch blocks {run_role}: {relative_path}"
            )


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _safe_filename(resource: Mapping[str, Any]) -> str:
    resource_id = str(resource["resource_id"])
    name = str(resource.get("name") or "").strip()
    if not name:
        name = Path(str(resource.get("url") or "")).name or "resource"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    if not name:
        name = "resource"
    return f"{resource_id}__{name[:160]}"


def plan_dataset_resources(
    dataset: Mapping[str, Any], policy: ResourcePolicy
) -> List[Dict[str, Any]]:
    policy.validate()
    resources = dataset.get("resources")
    if not isinstance(resources, list):
        raise NDPExecutionError("dataset resources must be a list")
    resource_ids = [str(item.get("resource_id") or "") for item in resources]
    if any(not resource_id for resource_id in resource_ids):
        raise NDPExecutionError("every resource must have a non-empty resource_id")
    if len(resource_ids) != len(set(resource_ids)):
        raise NDPExecutionError("dataset resources contain duplicate resource IDs")
    ordered = sorted(resources, key=lambda item: str(item["resource_id"]))
    eligible = [
        item
        for item in ordered
        if item.get("normalized_format") in FILE_EXTRACTABLE_FORMATS
        and item.get("http_access_url") is True
    ]
    selected_ids = {
        item["resource_id"] for item in eligible[: policy.max_resources_per_dataset]
    }
    plan = []
    for item in ordered:
        normalized_format = item.get("normalized_format")
        if normalized_format in REMOTE_DIRECTORY_FORMATS:
            decision = "skip_remote_store_locator_incomplete"
            reason = (
                "resource metadata does not uniquely locate a Zarr store with "
                "discoverable metadata markers"
            )
        elif normalized_format not in FILE_EXTRACTABLE_FORMATS:
            decision = "skip_unsupported_format"
            reason = "no registered file extractor in the frozen development policy"
        elif item.get("http_access_url") is not True:
            decision = "skip_unsupported_transport"
            reason = "resource does not expose an HTTP(S) URL"
        elif item["resource_id"] not in selected_ids:
            decision = "skip_dataset_resource_cap"
            reason = (
                "resource falls after the stable resource-ID order cap of "
                f"{policy.max_resources_per_dataset}"
            )
        else:
            decision = "attempt"
            reason = None
        plan.append(
            {
                "resource_id": item["resource_id"],
                "decision": decision,
                "reason": reason,
            }
        )
    return plan


def _download_resource(
    *,
    resource: Mapping[str, Any],
    destination: Path,
    policy: ResourcePolicy,
    remaining_dataset_bytes: int,
) -> Dict[str, Any]:
    maximum = min(policy.max_bytes_per_resource, remaining_dataset_bytes)
    if maximum <= 0:
        return {
            "status": "skipped_dataset_byte_cap",
            "failure": {
                "code": "dataset_byte_cap_reached",
                "message": "No dataset byte budget remains.",
            },
        }
    request = Request(
        str(resource["url"]),
        headers={
            "Accept": "*/*",
            "User-Agent": "high-fidelity-schema-study-ndp50/1",
        },
    )
    started = time.perf_counter()
    part_path = destination.with_suffix(destination.suffix + ".part")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urlopen(request, timeout=policy.timeout_seconds) as response:  # noqa: S310
            content_length_raw = response.headers.get("Content-Length")
            content_length = (
                int(content_length_raw)
                if content_length_raw and content_length_raw.isdigit()
                else None
            )
            if content_length is not None and content_length > maximum:
                return {
                    "status": "skipped_too_large",
                    "http_status": getattr(response, "status", None),
                    "final_url": response.geturl(),
                    "content_type": response.headers.get("Content-Type"),
                    "content_length": content_length,
                    "failure": {
                        "code": "content_length_exceeds_frozen_limit",
                        "message": f"Declared {content_length} bytes exceeds {maximum}.",
                    },
                    "elapsed_seconds": time.perf_counter() - started,
                }
            digest = hashlib.sha256()
            total = 0
            with part_path.open("wb") as handle:
                while True:
                    chunk = response.read(min(1024 * 1024, maximum - total + 1))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > maximum:
                        raise NDPExecutionError(
                            f"stream exceeded frozen byte limit {maximum}"
                        )
                    digest.update(chunk)
                    handle.write(chunk)
            part_path.replace(destination)
            return {
                "status": "acquired",
                "http_status": getattr(response, "status", None),
                "final_url": response.geturl(),
                "content_type": response.headers.get("Content-Type"),
                "content_length": content_length,
                "bytes_downloaded": total,
                "sha256": digest.hexdigest(),
                "file": destination.name,
                "elapsed_seconds": time.perf_counter() - started,
                "failure": None,
            }
    except NDPExecutionError as exc:
        if part_path.exists():
            part_path.unlink()
        return {
            "status": "skipped_too_large",
            "failure": {"code": "stream_exceeds_frozen_limit", "message": str(exc)},
            "elapsed_seconds": time.perf_counter() - started,
        }
    except HTTPError as exc:
        if part_path.exists():
            part_path.unlink()
        return {
            "status": "download_failed",
            "http_status": exc.code,
            "failure": {"code": "http_error", "message": str(exc)},
            "elapsed_seconds": time.perf_counter() - started,
        }
    except (URLError, TimeoutError, OSError) as exc:
        if part_path.exists():
            part_path.unlink()
        return {
            "status": "download_failed",
            "failure": {"code": "transport_error", "message": str(exc)},
            "elapsed_seconds": time.perf_counter() - started,
        }


def assess_downloaded_payload(
    path: Path, download: Mapping[str, Any]
) -> Dict[str, Any]:
    """Reject recognizable provider control responses before schema extraction."""
    content_type = str(download.get("content_type") or "").lower()
    if path.stat().st_size > 1024 * 1024:
        return {"status": "accepted", "reason": None}
    try:
        prefix = path.read_bytes()
        if "json" not in content_type and prefix.lstrip()[:1] not in {b"{", b"["}:
            return {"status": "accepted", "reason": None}
        payload = json.loads(prefix.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "accepted", "reason": None}
    if not isinstance(payload, Mapping):
        return {"status": "accepted", "reason": None}

    provider_status = str(payload.get("status") or "").strip()
    normalized_status = provider_status.lower().replace("_", "").replace(" ", "")
    if normalized_status in {
        "pending",
        "processing",
        "exporting",
        "exportingdata",
        "queued",
    } and ("message" in payload or "progressInPercent" in payload):
        return {
            "status": "provider_export_pending",
            "reason": {
                "code": "provider_control_response",
                "message": "Provider returned an asynchronous export status document, not the dataset payload.",
                "provider_status": provider_status,
            },
        }
    if "error" in payload and len(payload) <= 10:
        return {
            "status": "provider_error_payload",
            "reason": {
                "code": "provider_error_response",
                "message": "Provider returned a JSON error document, not the dataset payload.",
            },
        }
    return {"status": "accepted", "reason": None}


def acquire_resource(
    *,
    resource: Mapping[str, Any],
    destination: Path,
    policy: ResourcePolicy,
    remaining_dataset_bytes: int,
    sleep_fn: Callable[[float], None] = time.sleep,
    download_fn: Callable[..., Dict[str, Any]] = _download_resource,
) -> Dict[str, Any]:
    """Acquire one payload under a bounded, fully recorded retry policy."""
    attempts: List[Dict[str, Any]] = []
    remaining_bytes = remaining_dataset_bytes
    final: Dict[str, Any] = {}
    for attempt_number in range(1, policy.max_download_attempts + 1):
        destination.unlink(missing_ok=True)
        result = download_fn(
            resource=resource,
            destination=destination,
            policy=policy,
            remaining_dataset_bytes=remaining_bytes,
        )
        if result["status"] == "acquired":
            assessment = assess_downloaded_payload(destination, result)
            result["payload_assessment"] = assessment
            if assessment["status"] != "accepted":
                result["status"] = assessment["status"]
                result["failure"] = assessment["reason"]
        transferred = int(result.get("bytes_downloaded") or 0)
        remaining_bytes = max(remaining_bytes - transferred, 0)
        attempt_record = dict(result)
        attempt_record["attempt_number"] = attempt_number
        attempts.append(attempt_record)
        final = result
        retryable = result["status"] == "provider_export_pending"
        if (
            not retryable
            or attempt_number >= policy.max_download_attempts
            or remaining_bytes <= 0
        ):
            break
        sleep_fn(policy.retry_delay_seconds)

    final = dict(final)
    final["attempt_count"] = len(attempts)
    final["attempts"] = attempts
    final["transfer_bytes"] = sum(
        int(item.get("bytes_downloaded") or 0) for item in attempts
    )
    return final


def _declared_observed_comparison(
    resource: Mapping[str, Any],
    download: Mapping[str, Any],
    outcome: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    selected_format = None
    if outcome is not None:
        selected_format = (
            outcome.get("format_decision") or {}
        ).get("selected_format")
    catalog_format = resource.get("normalized_format")
    if outcome is None:
        format_status = "not_observed"
    elif selected_format is None:
        format_status = "observed_unknown"
    elif selected_format == catalog_format:
        format_status = "agree"
    else:
        format_status = "conflict"
    catalog_size = resource.get("size_bytes")
    observed_size = download.get("bytes_downloaded")
    if catalog_size is None:
        size_status = "catalog_missing"
    elif observed_size is None:
        size_status = "not_observed"
    elif catalog_size == observed_size:
        size_status = "agree"
    else:
        size_status = "conflict"
    return {
        "catalog_normalized_format": catalog_format,
        "extractor_selected_format": selected_format,
        "format_status": format_status,
        "catalog_size_bytes": catalog_size,
        "observed_size_bytes": observed_size,
        "size_status": size_status,
        "catalog_mimetype": resource.get("declared_mimetype_raw") or None,
        "observed_content_type": download.get("content_type"),
    }


def run_execution(
    *,
    detail_paths: Sequence[Path],
    resource_root: Path,
    schema_root: Path,
    policy: ResourcePolicy,
    run_role: str,
) -> Dict[str, Any]:
    policy.validate()
    if run_role not in RUN_ROLES:
        raise NDPExecutionError(f"unsupported run role: {run_role}")
    dataset_records = []
    for detail_path in sorted(detail_paths):
        dataset = normalize_detail_snapshot(detail_path)["dataset"]
        plan = {
            item["resource_id"]: item
            for item in plan_dataset_resources(dataset, policy)
        }
        dataset_dir = resource_root / dataset["dataset_id"]
        schema_dir = schema_root / dataset["dataset_id"]
        dataset_bytes = 0
        resource_records = []
        for resource in dataset["resources"]:
            plan_item = plan[resource["resource_id"]]
            if plan_item["decision"] != "attempt":
                resource_records.append(
                    {
                        "resource_id": resource["resource_id"],
                        "name": resource["name"],
                        "url": resource["url"],
                        "catalog_format": resource["normalized_format"],
                        "plan": plan_item,
                        "download": {"status": plan_item["decision"]},
                        "extraction": None,
                        "declared_observed": _declared_observed_comparison(
                            resource, {}, None
                        ),
                    }
                )
                continue
            destination = dataset_dir / _safe_filename(resource)
            schema_path = schema_dir / f"{resource['resource_id']}.json"
            schema_path.unlink(missing_ok=True)
            download = acquire_resource(
                resource=resource,
                destination=destination,
                policy=policy,
                remaining_dataset_bytes=policy.max_bytes_per_dataset - dataset_bytes,
            )
            extraction_payload = None
            dataset_bytes += int(download["transfer_bytes"])
            if download["status"] == "acquired":
                extraction_started = time.perf_counter()
                outcome = extract_path(
                    ExtractionRequest(
                        path=str(destination),
                        sample_limit=policy.sample_limit,
                    )
                )
                extraction_payload = outcome.to_dict()
                extraction_payload["elapsed_seconds"] = (
                    time.perf_counter() - extraction_started
                )
                _write_json(schema_path, extraction_payload)
                extraction_payload["artifact"] = {
                    "file": schema_path.name,
                    "sha256": _sha256_file(schema_path),
                }
            resource_records.append(
                {
                    "resource_id": resource["resource_id"],
                    "name": resource["name"],
                    "url": resource["url"],
                    "catalog_format": resource["normalized_format"],
                    "plan": plan_item,
                    "download": download,
                    "extraction": extraction_payload,
                    "declared_observed": _declared_observed_comparison(
                        resource, download, extraction_payload
                    ),
                }
            )
        dataset_records.append(
            {
                "dataset_id": dataset["dataset_id"],
                "title": dataset["title"],
                "organization_id": dataset["organization_id"],
                "detail_snapshot": {
                    "file": detail_path.name,
                    "sha256": _sha256_file(detail_path),
                },
                "bytes_downloaded": dataset_bytes,
                "resource_records": resource_records,
            }
        )
    statuses = Counter()
    download_statuses = Counter()
    format_statuses = Counter()
    for dataset in dataset_records:
        for resource in dataset["resource_records"]:
            download_statuses[resource["download"]["status"]] += 1
            format_statuses[resource["declared_observed"]["format_status"]] += 1
            if resource["extraction"] is not None:
                statuses[resource["extraction"]["status"]] += 1
    return {
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "protocol_version": "ndp50-external-validation-protocol/v1",
        "run_role": run_role,
        "completed_at": _utc_now(),
        "policy": asdict(policy),
        "counts": {
            "dataset_count": len(dataset_records),
            "resource_count": sum(
                len(item["resource_records"]) for item in dataset_records
            ),
            "bytes_downloaded": sum(
                item["bytes_downloaded"] for item in dataset_records
            ),
            "download_statuses": dict(sorted(download_statuses.items())),
            "extraction_statuses": dict(sorted(statuses.items())),
            "declared_observed_format_statuses": dict(
                sorted(format_statuses.items())
            ),
        },
        "datasets": dataset_records,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the frozen bounded NDP-50 development resource policy."
    )
    parser.add_argument("--detail-dir", type=Path, required=True)
    parser.add_argument("--resource-root", type=Path, required=True)
    parser.add_argument("--schema-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-resources-per-dataset", type=int, default=3)
    parser.add_argument(
        "--max-bytes-per-resource", type=int, default=25 * 1024 * 1024
    )
    parser.add_argument(
        "--max-bytes-per-dataset", type=int, default=50 * 1024 * 1024
    )
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--sample-limit", type=int, default=200)
    parser.add_argument("--max-download-attempts", type=int, default=3)
    parser.add_argument("--retry-delay-seconds", type=float, default=10.0)
    parser.add_argument(
        "--run-role",
        choices=sorted(RUN_ROLES),
        default="development",
    )
    parser.add_argument("--authorization-freeze", type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    detail_paths = sorted(args.detail_dir.glob("*.json.gz"))
    if not detail_paths:
        raise NDPExecutionError("detail directory contains no .json.gz snapshots")
    authorize_run_role(args.run_role, args.authorization_freeze)
    report = run_execution(
        detail_paths=detail_paths,
        resource_root=args.resource_root,
        schema_root=args.schema_root,
        run_role=args.run_role,
        policy=ResourcePolicy(
            max_resources_per_dataset=args.max_resources_per_dataset,
            max_bytes_per_resource=args.max_bytes_per_resource,
            max_bytes_per_dataset=args.max_bytes_per_dataset,
            timeout_seconds=args.timeout_seconds,
            sample_limit=args.sample_limit,
            max_download_attempts=args.max_download_attempts,
            retry_delay_seconds=args.retry_delay_seconds,
        ),
    )
    _write_json(args.output, report)
    print(
        json.dumps(
            report["counts"], indent=2, ensure_ascii=False, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
