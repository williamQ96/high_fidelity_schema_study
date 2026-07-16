from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .architecture_variants import build_observation_payload, load_json
from . import semantic_catalog_acquisition as catalog_adapter


FRAME_SCHEMA_VERSION = "semantic-blind-candidate-frame/v1"
ACQUISITION_LOG_SCHEMA_VERSION = "semantic-blind-acquisition-log/v1"
DESIGN_SCHEMA_VERSION = "semantic-blind-sampling-design/v1"
SELECTION_SCHEMA_VERSION = "semantic-blind-selection/v1"
KNOWN_RESOURCES_SCHEMA_VERSION = "semantic-known-nonblind-resources/v1"
RECEIPT_SCHEMA_VERSION = "semantic-sampling-registration-receipt/v1"
PROTOCOL_VERSION = "semantic-architecture-protocol/v1"
POWER_SCHEMA_VERSION = "semantic-power-analysis/v2"
SELECTION_ALGORITHM = "stratum_ordered_sha256_priority_with_frozen_caps/v1"
SOURCE_IDENTITY_ALGORITHM = "canonical_source_tuple_sha256/v1"
ACQUISITION_TERMINATION_REASONS = {
    "api_exhausted",
    "frozen_page_cap_reached",
}


class BlindSamplingError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_provider_checksum(path: Path, checksum: str) -> None:
    if ":" not in checksum:
        raise BlindSamplingError("provider checksum must include an algorithm prefix")
    algorithm, expected = checksum.split(":", 1)
    normalized_algorithm = algorithm.casefold().replace("-", "")
    if normalized_algorithm not in {"md5", "sha256"}:
        raise BlindSamplingError(
            f"unsupported provider checksum algorithm: {algorithm!r}"
        )
    digest = hashlib.new(normalized_algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest().casefold() != expected.casefold():
        raise BlindSamplingError(f"provider checksum mismatch for {path}")


def _resolve(owner: Path, raw_path: Any) -> Path:
    candidate = Path(str(raw_path or ""))
    if candidate.is_absolute():
        return candidate
    return (owner.resolve().parent / candidate).resolve()


def _relative(path: Path, owner: Path) -> str:
    try:
        return Path(os.path.relpath(path.resolve(), owner.resolve().parent)).as_posix()
    except ValueError:
        return str(path.resolve())


def _check_file(owner: Path, record: Any, label: str) -> Path:
    if not isinstance(record, dict):
        raise BlindSamplingError(f"{label} record must be an object")
    path = _resolve(owner, record.get("file"))
    if not path.is_file():
        raise BlindSamplingError(f"{label} is missing: {path}")
    expected = str(record.get("sha256") or "")
    actual = sha256_file(path)
    if actual != expected:
        raise BlindSamplingError(
            f"{label} hash mismatch: expected {expected}, got {actual}"
        )
    return path


def _forbidden_task_key_paths(value: Any, prefix: str = "") -> List[str]:
    forbidden: List[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            normalized = str(key).lower()
            if normalized in {
                "gold",
                "gold_schema",
                "legacy_result",
                "model_output",
                "model_response",
            } or normalized.startswith("correct_"):
                forbidden.append(path)
            forbidden.extend(_forbidden_task_key_paths(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            forbidden.extend(_forbidden_task_key_paths(item, f"{prefix}[{index}]"))
    return forbidden


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def canonical_source_identity(
    source_repository: str, source_record_id: str, source_resource_id: str
) -> str:
    values = {
        "source_record_id": str(source_record_id).strip(),
        "source_repository": str(source_repository).strip().casefold(),
        "source_resource_id": str(source_resource_id).strip(),
    }
    if any(not value for value in values.values()):
        raise BlindSamplingError("canonical source identity components are required")
    material = json.dumps(
        values, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _find_unique_string(value: Any, key: str) -> str:
    found: List[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for item_key, child in item.items():
                if item_key == key and isinstance(child, str) and child:
                    found.append(child)
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    if len(found) != 1:
        raise BlindSamplingError(
            f"expected exactly one non-empty {key!r}, found {len(found)}"
        )
    return found[0]


def _validate_known_resources(path: Path) -> Dict[str, set[str]]:
    payload = load_json(path)
    if payload.get("schema_version") != KNOWN_RESOURCES_SCHEMA_VERSION:
        raise BlindSamplingError(f"expected {KNOWN_RESOURCES_SCHEMA_VERSION}")
    if payload.get("status") != "frozen_before_candidate_frame":
        raise BlindSamplingError(
            "known non-blind registry must be frozen_before_candidate_frame"
        )
    if payload.get("source_identity_algorithm") != SOURCE_IDENTITY_ALGORITHM:
        raise BlindSamplingError(
            f"source_identity_algorithm must be {SOURCE_IDENTITY_ALGORITHM}"
        )
    if not str(payload.get("frozen_at") or "").strip():
        raise BlindSamplingError("known non-blind registry frozen_at is required")
    construction_sources = payload.get("construction_sources")
    if not isinstance(construction_sources, list) or not construction_sources:
        raise BlindSamplingError(
            "known non-blind registry construction_sources are required"
        )
    for index, source in enumerate(construction_sources):
        _check_file(path, source, f"known registry construction source {index}")
    _check_file(path, payload.get("generator"), "known registry generator")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise BlindSamplingError("known non-blind registry records are required")
    identities: List[str] = []
    task_hashes: List[str] = []
    resource_hashes: List[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise BlindSamplingError("known non-blind registry records must be objects")
        identity = str(record.get("source_identity") or "")
        if not identity:
            raise BlindSamplingError(
                f"known registry record {index} source_identity is required"
            )
        expected_identity = canonical_source_identity(
            record.get("source_repository", ""),
            record.get("source_record_id", ""),
            record.get("source_resource_id", ""),
        )
        if identity != expected_identity:
            raise BlindSamplingError(
                f"known registry record {index} source_identity is not reproducible"
            )
        identities.append(identity)
        task_path = _check_file(
            path, record.get("task"), f"known registry task {identity}"
        )
        task_hashes.append(sha256_file(task_path))
        available = record.get("resource_available_at_freeze")
        if not isinstance(available, bool):
            raise BlindSamplingError(
                f"known registry record {identity} resource availability must be Boolean"
            )
        if available:
            resource_path = _check_file(
                path, record.get("resource"), f"known registry resource {identity}"
            )
            resource_hashes.append(sha256_file(resource_path))
            if record.get("resource_absence_reason") is not None:
                raise BlindSamplingError(
                    f"known registry record {identity} cannot have an absence reason"
                )
        else:
            if record.get("resource") is not None:
                raise BlindSamplingError(
                    f"known registry record {identity} unavailable resource must be null"
                )
            if not str(record.get("resource_absence_reason") or "").strip():
                raise BlindSamplingError(
                    f"known registry record {identity} absence reason is required"
                )
    if len(identities) != len(set(identities)):
        raise BlindSamplingError("known non-blind source identities must be unique")
    expected_lists = {
        "source_identities": sorted(identities),
        "task_sha256s": sorted(set(task_hashes)),
        "resource_sha256s": sorted(set(resource_hashes)),
    }
    for key, expected in expected_lists.items():
        observed = payload.get(key)
        if observed != expected:
            raise BlindSamplingError(
                f"known non-blind registry {key} is not reproducible from records"
            )
    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        raise BlindSamplingError("known non-blind registry coverage is required")
    expected_coverage = {
        "total_record_count": len(records),
        "resource_hash_available_count": len(set(resource_hashes)),
        "source_identity_count": len(set(identities)),
    }
    for key, expected in expected_coverage.items():
        if coverage.get(key) != expected:
            raise BlindSamplingError(
                f"known non-blind registry coverage.{key} is not reproducible"
            )
    if any(not _is_sha256(value) for value in task_hashes + resource_hashes):
        raise BlindSamplingError("known non-blind hashes must be lowercase SHA-256")
    return {
        "resource_sha256s": set(resource_hashes),
        "source_identities": set(identities),
        "task_sha256s": set(task_hashes),
    }


def build_known_nonblind_registry(
    *, grounding_manifest_path: Path, data_root: Path, frozen_at: str, output_path: Path
) -> Dict[str, Any]:
    grounding_manifest_path = grounding_manifest_path.resolve()
    data_root = data_root.resolve()
    output_path = output_path.resolve()
    if not str(frozen_at).strip():
        raise BlindSamplingError("frozen_at is required")
    manifest = load_json(grounding_manifest_path)
    internal = manifest.get("internal_tasks")
    external = manifest.get("external_tasks")
    if not isinstance(internal, list) or not isinstance(external, list):
        raise BlindSamplingError("grounding manifest task lists are required")
    if manifest.get("internal_task_count") != len(internal) or manifest.get(
        "external_task_count"
    ) != len(external):
        raise BlindSamplingError("grounding manifest task counts are inconsistent")
    records: List[Dict[str, Any]] = []
    for namespace, entries, source_key in (
        ("internal", internal, "study_source_file"),
        ("external", external, "external_source_file"),
    ):
        for entry in entries:
            task_id = str(entry.get("task_id") or "")
            task_path = (data_root / str(entry.get("task_file") or "")).resolve()
            if not task_id or not task_path.is_file():
                raise BlindSamplingError(f"invalid grounding task entry: {entry}")
            task = load_json(task_path)
            source_file = _find_unique_string(task, source_key)
            if namespace == "external" and entry.get("source_file") != source_file:
                raise BlindSamplingError(
                    f"external source mismatch for {task_id}: {source_file}"
                )
            if namespace == "internal":
                source_repository = "internal-study-corpus"
                source_record_id = str(entry.get("dataset_id") or "")
                source_resource_id = source_file
            else:
                source_parts = source_file.split("/", 2)
                if len(source_parts) != 3 or any(not part for part in source_parts):
                    raise BlindSamplingError(
                        f"external source path is not repository/record/resource: {source_file}"
                    )
                source_repository, source_record_id, source_resource_id = source_parts
            source_identity = canonical_source_identity(
                source_repository, source_record_id, source_resource_id
            )
            resource_path = (data_root / source_file).resolve()
            available = resource_path.is_file()
            record: Dict[str, Any] = {
                "source_identity": source_identity,
                "source_repository": source_repository,
                "source_record_id": source_record_id,
                "source_resource_id": source_resource_id,
                "source_namespace": namespace,
                "source_file": source_file,
                "grounding_task_id": task_id,
                "grounding_role": entry.get("role", "development"),
                "exposure_roles": [
                    "semantic_grounding",
                    "system_visible_before_blind_sampling",
                ],
                "task": {
                    "file": _relative(task_path, output_path),
                    "sha256": sha256_file(task_path),
                },
                "resource_available_at_freeze": available,
                "resource": (
                    {
                        "file": _relative(resource_path, output_path),
                        "sha256": sha256_file(resource_path),
                    }
                    if available
                    else None
                ),
                "resource_absence_reason": (
                    None
                    if available
                    else "original external resource bytes are not present in the workspace"
                ),
            }
            records.append(record)
    records.sort(key=lambda item: item["source_identity"])
    resource_hashes = sorted(
        {
            str(record["resource"]["sha256"])
            for record in records
            if record["resource_available_at_freeze"]
        }
    )
    task_hashes = sorted({str(record["task"]["sha256"]) for record in records})
    return {
        "schema_version": KNOWN_RESOURCES_SCHEMA_VERSION,
        "status": "frozen_before_candidate_frame",
        "source_identity_algorithm": SOURCE_IDENTITY_ALGORITHM,
        "frozen_at": frozen_at,
        "construction_note": (
            "Complete union of resources represented in the semantic-grounding "
            "manifest and therefore visible during system development. Missing "
            "external bytes are excluded by stable source identity, not an invented hash."
        ),
        "construction_sources": [
            {
                "file": _relative(grounding_manifest_path, output_path),
                "sha256": sha256_file(grounding_manifest_path),
            }
        ],
        "generator": {
            "file": _relative(Path(__file__).resolve(), output_path),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "coverage": {
            "internal_task_count": len(internal),
            "external_task_count": len(external),
            "total_record_count": len(records),
            "resource_hash_available_count": len(resource_hashes),
            "source_identity_count": len(records),
        },
        "source_identities": [record["source_identity"] for record in records],
        "task_sha256s": task_hashes,
        "resource_sha256s": resource_hashes,
        "records": records,
    }


def validate_known_nonblind_registry(path: Path) -> Dict[str, Any]:
    try:
        sets = _validate_known_resources(path.resolve())
        payload = load_json(path.resolve())
        return {
            "status": "ready",
            "errors": [],
            "registry_sha256": sha256_file(path.resolve()),
            "record_count": len(payload["records"]),
            "source_identity_count": len(sets["source_identities"]),
            "resource_hash_count": len(sets["resource_sha256s"]),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [{"code": "known_nonblind_registry_invalid", "detail": str(exc)}],
        }


def validate_acquisition_log(path: Path) -> Dict[str, Any]:
    path = path.resolve()
    payload = load_json(path)
    if payload.get("schema_version") != ACQUISITION_LOG_SCHEMA_VERSION:
        raise BlindSamplingError(f"expected {ACQUISITION_LOG_SCHEMA_VERSION}")
    if payload.get("protocol_version") != PROTOCOL_VERSION:
        raise BlindSamplingError(f"expected {PROTOCOL_VERSION}")
    if payload.get("status") != "frozen_before_candidate_frame":
        raise BlindSamplingError(
            "acquisition log must be frozen_before_candidate_frame"
        )
    if not str(payload.get("frozen_at") or "").strip():
        raise BlindSamplingError("acquisition log frozen_at is required")
    boundary = payload.get("construction_boundary")
    if boundary != {
        "model_outputs_consulted": False,
        "architecture_results_consulted": False,
        "gold_labels_created": False,
    }:
        raise BlindSamplingError("acquisition construction boundary is invalid")
    enumeration = payload.get("enumeration")
    if not isinstance(enumeration, dict):
        raise BlindSamplingError("acquisition enumeration is required")
    adapter = enumeration.get("adapter")
    if not isinstance(adapter, dict) or not str(adapter.get("adapter_id") or ""):
        raise BlindSamplingError("enumeration adapter identity is required")
    if adapter["adapter_id"] != catalog_adapter.ADAPTER_ID:
        raise BlindSamplingError(
            f"enumeration adapter must be {catalog_adapter.ADAPTER_ID}"
        )
    adapter_path = _check_file(
        path, adapter.get("implementation"), "enumeration adapter"
    )
    if adapter_path != Path(catalog_adapter.__file__).resolve():
        raise BlindSamplingError(
            "enumeration adapter path is not the frozen implementation"
        )
    retrieval_cutoff = str(enumeration.get("retrieval_cutoff") or "")
    repositories = enumeration.get("source_repositories")
    if not retrieval_cutoff:
        raise BlindSamplingError("enumeration retrieval_cutoff is required")
    if (
        not isinstance(repositories, list)
        or not repositories
        or any(not isinstance(value, str) or not value for value in repositories)
        or len(repositories) != len(set(repositories))
    ):
        raise BlindSamplingError(
            "enumeration source_repositories must be unique non-empty strings"
        )
    snapshots = enumeration.get("catalog_snapshots")
    if not isinstance(snapshots, list) or not snapshots:
        raise BlindSamplingError("catalog snapshots are required")
    snapshot_by_id: Dict[str, Dict[str, Any]] = {}
    normalized_by_snapshot: Dict[str, Dict[str, Any]] = {}
    pages_by_repository: Dict[str, List[int]] = {value: [] for value in repositories}
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            raise BlindSamplingError("catalog snapshots must be objects")
        snapshot_id = str(snapshot.get("snapshot_id") or "")
        repository = str(snapshot.get("source_repository") or "")
        page_ordinal = snapshot.get("page_ordinal")
        if not snapshot_id or snapshot_id in snapshot_by_id:
            raise BlindSamplingError("catalog snapshot IDs must be present and unique")
        if repository not in repositories:
            raise BlindSamplingError("catalog snapshot repository is outside scope")
        if (
            not isinstance(page_ordinal, int)
            or isinstance(page_ordinal, bool)
            or page_ordinal <= 0
        ):
            raise BlindSamplingError("catalog snapshot page ordinal must be positive")
        for key in ("request_url", "retrieved_at"):
            if not str(snapshot.get(key) or "").strip():
                raise BlindSamplingError(f"catalog snapshot {key} is required")
        for count_key in (
            "returned_dataset_record_count",
            "enumerated_resource_count",
        ):
            if (
                not isinstance(snapshot.get(count_key), int)
                or isinstance(snapshot[count_key], bool)
                or snapshot[count_key] < 0
            ):
                raise BlindSamplingError(f"catalog snapshot {count_key} is invalid")
        response_path = _check_file(
            path, snapshot.get("response"), f"catalog snapshot {snapshot_id}"
        )
        try:
            normalized_snapshot = catalog_adapter.normalize_catalog_snapshot(
                response_path
            )
        except catalog_adapter.CatalogSnapshotError as exc:
            raise BlindSamplingError(
                f"catalog snapshot {snapshot_id} cannot be replayed: {exc}"
            ) from exc
        expected_snapshot_metadata = {
            "source_repository": repository,
            "page_ordinal": page_ordinal,
            "request_url": snapshot["request_url"],
            "retrieved_at": snapshot["retrieved_at"],
            "returned_dataset_record_count": snapshot["returned_dataset_record_count"],
            "enumerated_resource_count": snapshot["enumerated_resource_count"],
        }
        for key, expected in expected_snapshot_metadata.items():
            if normalized_snapshot[key] != expected:
                raise BlindSamplingError(
                    f"catalog snapshot {snapshot_id}.{key} is not reproducible"
                )
        snapshot_by_id[snapshot_id] = snapshot
        normalized_by_snapshot[snapshot_id] = normalized_snapshot
        pages_by_repository[repository].append(page_ordinal)
    termination = enumeration.get("repository_boundaries")
    if not isinstance(termination, list) or len(termination) != len(repositories):
        raise BlindSamplingError("one repository boundary per repository is required")
    boundary_by_repository: Dict[str, Dict[str, Any]] = {}
    for item in termination:
        if not isinstance(item, dict):
            raise BlindSamplingError("repository boundaries must be objects")
        repository = str(item.get("source_repository") or "")
        if repository not in repositories or repository in boundary_by_repository:
            raise BlindSamplingError("repository boundary identities are invalid")
        last_page = item.get("last_page_ordinal")
        if (
            not isinstance(last_page, int)
            or isinstance(last_page, bool)
            or last_page <= 0
        ):
            raise BlindSamplingError("repository boundary last page is invalid")
        if item.get("termination_reason") not in ACQUISITION_TERMINATION_REASONS:
            raise BlindSamplingError("repository termination reason is invalid")
        if sorted(pages_by_repository[repository]) != list(range(1, last_page + 1)):
            raise BlindSamplingError(
                f"repository {repository} catalog pages are not complete and contiguous"
            )
        boundary_by_repository[repository] = item
    criteria = payload.get("acquisition_criteria")
    if not isinstance(criteria, dict):
        raise BlindSamplingError("acquisition criteria are required")
    criterion_kinds: Dict[str, str] = {}
    for key, kind in (("inclusion", "inclusion"), ("exclusion", "exclusion")):
        values = criteria.get(key)
        if not isinstance(values, list) or not values:
            raise BlindSamplingError(f"acquisition criteria {key} list is required")
        for criterion in values:
            if not isinstance(criterion, dict):
                raise BlindSamplingError("acquisition criteria must be objects")
            criterion_id = str(criterion.get("criterion_id") or "")
            if not criterion_id or criterion_id in criterion_kinds:
                raise BlindSamplingError(
                    "acquisition criterion IDs must be present and unique"
                )
            for required in ("description", "assessment_method"):
                if not str(criterion.get(required) or "").strip():
                    raise BlindSamplingError(
                        f"acquisition criterion {criterion_id}.{required} is required"
                    )
            criterion_kinds[criterion_id] = kind
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise BlindSamplingError("acquisition records are required")
    seen_identities: set[str] = set()
    seen_candidates: set[str] = set()
    record_counts_by_snapshot = {snapshot_id: 0 for snapshot_id in snapshot_by_id}
    records_by_snapshot: Dict[str, Dict[str, Dict[str, Any]]] = {
        snapshot_id: {} for snapshot_id in snapshot_by_id
    }
    normalized: List[Dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            raise BlindSamplingError("acquisition records must be objects")
        candidate_id = str(record.get("candidate_id") or "")
        identity = str(record.get("source_identity") or "")
        if not candidate_id or candidate_id in seen_candidates:
            raise BlindSamplingError(
                "acquisition candidate IDs must be present and unique"
            )
        expected_identity = canonical_source_identity(
            record.get("source_repository", ""),
            record.get("source_record_id", ""),
            record.get("source_resource_id", ""),
        )
        if identity != expected_identity or identity in seen_identities:
            raise BlindSamplingError(
                "acquisition source identities must be reproducible and unique"
            )
        if record.get("catalog_snapshot_id") not in snapshot_by_id:
            raise BlindSamplingError("acquisition record snapshot identity is unknown")
        record_counts_by_snapshot[str(record["catalog_snapshot_id"])] += 1
        if (
            record.get("source_repository")
            != snapshot_by_id[record["catalog_snapshot_id"]]["source_repository"]
        ):
            raise BlindSamplingError(
                "acquisition record repository differs from snapshot"
            )
        for key in (
            "dataset_group_id",
            "source_url",
            "discovered_at",
            "scientific_family",
            "file_format",
            "selection_stratum",
            "license",
            "source_size_bytes",
            "provider_checksum",
        ):
            if key == "source_size_bytes":
                valid = (
                    isinstance(record.get(key), int)
                    and not isinstance(record[key], bool)
                    and record[key] >= 0
                )
            else:
                valid = bool(str(record.get(key) or "").strip())
            if not valid:
                raise BlindSamplingError(
                    f"acquisition record {candidate_id}.{key} is required"
                )
        results = record.get("criterion_results")
        if not isinstance(results, dict) or set(results) != set(criterion_kinds):
            raise BlindSamplingError(
                "each acquisition record must assess every criterion exactly once"
            )
        if any(not isinstance(value, bool) for value in results.values()):
            raise BlindSamplingError("acquisition criterion results must be Boolean")
        failed = sorted(
            criterion_id
            for criterion_id, observed in results.items()
            if (criterion_kinds[criterion_id] == "inclusion" and not observed)
            or (criterion_kinds[criterion_id] == "exclusion" and observed)
        )
        eligible = not failed
        if record.get("eligible_for_acquisition") != eligible:
            raise BlindSamplingError(
                "acquisition eligibility is not mechanically derived"
            )
        if record.get("reasons") != failed:
            raise BlindSamplingError(
                "acquisition reasons must equal failed criterion IDs"
            )
        status = record.get("acquisition_status")
        if eligible and status not in {"acquired", "download_failed"}:
            raise BlindSamplingError("eligible acquisition record has invalid status")
        if not eligible and status != "excluded_before_download":
            raise BlindSamplingError("ineligible acquisition record has invalid status")
        resource_path: Path | None = None
        if status == "acquired":
            if not str(record.get("acquired_at") or "").strip():
                raise BlindSamplingError("acquired record acquired_at is required")
            resource_path = _check_file(
                path, record.get("resource"), f"acquired resource {candidate_id}"
            )
            _verify_provider_checksum(resource_path, str(record["provider_checksum"]))
            if record.get("failure") is not None:
                raise BlindSamplingError("acquired record cannot contain a failure")
        else:
            if record.get("acquired_at") is not None:
                raise BlindSamplingError("unacquired record acquired_at must be null")
            if record.get("resource") is not None:
                raise BlindSamplingError("unacquired record resource must be null")
            if status == "download_failed" and not str(record.get("failure") or ""):
                raise BlindSamplingError("download failure detail is required")
        seen_candidates.add(candidate_id)
        seen_identities.add(identity)
        records_by_snapshot[str(record["catalog_snapshot_id"])][identity] = record
        normalized.append({**record, "_resource_path": resource_path})
    for snapshot_id, snapshot in snapshot_by_id.items():
        if (
            record_counts_by_snapshot[snapshot_id]
            != snapshot["enumerated_resource_count"]
        ):
            raise BlindSamplingError(
                f"catalog snapshot {snapshot_id} normalized resource count is not reproducible"
            )
        expected_resources = {
            str(resource["source_identity"]): resource
            for resource in normalized_by_snapshot[snapshot_id]["resources"]
        }
        observed_resources = records_by_snapshot[snapshot_id]
        if set(expected_resources) != set(observed_resources):
            raise BlindSamplingError(
                f"catalog snapshot {snapshot_id} resources differ from adapter replay"
            )
        for identity, expected_resource in expected_resources.items():
            observed_resource = observed_resources[identity]
            for key in (
                "dataset_group_id",
                "source_identity",
                "source_repository",
                "source_record_id",
                "source_resource_id",
                "source_url",
                "source_size_bytes",
                "provider_checksum",
                "license",
                "scientific_family",
                "file_format",
                "selection_stratum",
            ):
                if observed_resource[key] != expected_resource[key]:
                    raise BlindSamplingError(
                        f"catalog resource {identity}.{key} differs from adapter replay"
                    )
            if observed_resource["discovered_at"] != snapshot["retrieved_at"]:
                raise BlindSamplingError(
                    f"catalog resource {identity}.discovered_at differs from snapshot"
                )
    declared_counts = payload.get("counts")
    expected_counts = {
        "enumerated_resource_count": len(records),
        "eligible_for_acquisition_count": sum(
            bool(record["eligible_for_acquisition"]) for record in records
        ),
        "acquired_count": sum(
            record["acquisition_status"] == "acquired" for record in records
        ),
        "download_failed_count": sum(
            record["acquisition_status"] == "download_failed" for record in records
        ),
        "excluded_before_download_count": sum(
            record["acquisition_status"] == "excluded_before_download"
            for record in records
        ),
    }
    if declared_counts != expected_counts:
        raise BlindSamplingError("acquisition counts are not reproducible")
    return {
        "payload": payload,
        "records": normalized,
        "acquired": [
            record
            for record in normalized
            if record["acquisition_status"] == "acquired"
        ],
    }


def validate_candidate_frame(path: Path) -> Dict[str, Any]:
    path = path.resolve()
    payload = load_json(path)
    if payload.get("schema_version") != FRAME_SCHEMA_VERSION:
        raise BlindSamplingError(f"expected {FRAME_SCHEMA_VERSION}")
    if payload.get("protocol_version") != PROTOCOL_VERSION:
        raise BlindSamplingError(f"expected {PROTOCOL_VERSION}")
    if payload.get("status") != "frozen_before_selection":
        raise BlindSamplingError("candidate frame must be frozen_before_selection")
    if not str(payload.get("frozen_at") or "").strip():
        raise BlindSamplingError("candidate frame frozen_at is required")
    boundary = payload.get("construction_boundary")
    expected_boundary = {
        "model_outputs_consulted": False,
        "architecture_results_consulted": False,
        "gold_labels_created": False,
        "eligibility_decided_before_selection": True,
    }
    if boundary != expected_boundary:
        raise BlindSamplingError("candidate frame construction boundary is invalid")
    definition = payload.get("frame_definition")
    if not isinstance(definition, dict):
        raise BlindSamplingError("candidate frame_definition is required")
    if definition.get("source_identity_algorithm") != SOURCE_IDENTITY_ALGORITHM:
        raise BlindSamplingError(
            f"frame source_identity_algorithm must be {SOURCE_IDENTITY_ALGORITHM}"
        )
    for key in (
        "scope_statement",
        "candidate_unit",
        "enumeration_method",
        "retrieval_cutoff",
    ):
        if not str(definition.get(key) or "").strip():
            raise BlindSamplingError(f"frame_definition.{key} is required")
    source_repositories = definition.get("source_repositories")
    if (
        not isinstance(source_repositories, list)
        or not source_repositories
        or any(
            not isinstance(value, str) or not value.strip()
            for value in source_repositories
        )
    ):
        raise BlindSamplingError(
            "frame_definition.source_repositories must be a non-empty string list"
        )
    criteria_by_id: Dict[str, Dict[str, Any]] = {}
    criterion_kinds: Dict[str, str] = {}
    for key, kind in (
        ("inclusion_criteria", "inclusion"),
        ("exclusion_criteria", "exclusion"),
    ):
        values = definition.get(key)
        if not isinstance(values, list) or not values:
            raise BlindSamplingError(
                f"frame_definition.{key} must be a non-empty criterion list"
            )
        for criterion in values:
            if not isinstance(criterion, dict):
                raise BlindSamplingError(
                    f"frame_definition.{key} entries must be objects"
                )
            criterion_id = str(criterion.get("criterion_id") or "")
            if not criterion_id or criterion_id in criteria_by_id:
                raise BlindSamplingError(
                    "eligibility criterion IDs must be present and unique"
                )
            for required_key in ("description", "assessment_method"):
                if not str(criterion.get(required_key) or "").strip():
                    raise BlindSamplingError(
                        f"eligibility criterion {criterion_id}.{required_key} is required"
                    )
            criteria_by_id[criterion_id] = criterion
            criterion_kinds[criterion_id] = kind
    known_path = _check_file(
        path,
        payload.get("known_nonblind_resources"),
        "known non-blind resource registry",
    )
    known = _validate_known_resources(known_path)
    acquisition_path = _check_file(
        path, payload.get("acquisition_log"), "blind acquisition log"
    )
    acquisition = validate_acquisition_log(acquisition_path)
    acquisition_enumeration = acquisition["payload"]["enumeration"]
    if definition["retrieval_cutoff"] != acquisition_enumeration["retrieval_cutoff"]:
        raise BlindSamplingError(
            "candidate frame retrieval cutoff differs from acquisition log"
        )
    if source_repositories != acquisition_enumeration["source_repositories"]:
        raise BlindSamplingError(
            "candidate frame repositories differ from acquisition log"
        )
    acquired_by_candidate = {
        str(record["candidate_id"]): record for record in acquisition["acquired"]
    }
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise BlindSamplingError("candidate frame must contain candidates")
    seen_ids: set[str] = set()
    seen_source_identities: set[str] = set()
    seen_resource_hashes: set[str] = set()
    normalized: List[Dict[str, Any]] = []
    for item in candidates:
        if not isinstance(item, dict):
            raise BlindSamplingError("candidate entries must be objects")
        candidate_id = str(item.get("candidate_id") or "")
        if not candidate_id or candidate_id in seen_ids:
            raise BlindSamplingError("candidate IDs must be present and unique")
        seen_ids.add(candidate_id)
        for key in (
            "dataset_group_id",
            "source_identity",
            "source_repository",
            "source_record_id",
            "source_resource_id",
            "scientific_family",
            "file_format",
            "selection_stratum",
            "license",
            "source_url",
            "acquired_at",
        ):
            if not str(item.get(key) or "").strip():
                raise BlindSamplingError(f"{candidate_id}.{key} is required")
        source_identity = str(item["source_identity"])
        expected_source_identity = canonical_source_identity(
            item["source_repository"],
            item["source_record_id"],
            item["source_resource_id"],
        )
        if source_identity != expected_source_identity:
            raise BlindSamplingError(
                f"{candidate_id} source_identity is not reproducible"
            )
        if source_identity in seen_source_identities:
            raise BlindSamplingError("candidate source identities must be unique")
        seen_source_identities.add(source_identity)
        if item["source_repository"] not in source_repositories:
            raise BlindSamplingError(
                f"{candidate_id} source_repository is outside the frozen frame scope"
            )
        acquired = acquired_by_candidate.get(candidate_id)
        if acquired is None:
            raise BlindSamplingError(
                f"{candidate_id} is not an acquired record in the frozen acquisition log"
            )
        for key in (
            "dataset_group_id",
            "source_identity",
            "source_repository",
            "source_record_id",
            "source_resource_id",
            "source_url",
            "scientific_family",
            "file_format",
            "selection_stratum",
            "license",
            "acquired_at",
        ):
            if item[key] != acquired[key]:
                raise BlindSamplingError(
                    f"{candidate_id}.{key} differs from the frozen acquisition log"
                )
        resource_path = _check_file(
            path, item.get("resource"), f"{candidate_id} resource"
        )
        task_path = _check_file(path, item.get("task"), f"{candidate_id} task")
        source_bundle_path = _check_file(
            path, item.get("source_bundle"), f"{candidate_id} source bundle"
        )
        resource_hash = sha256_file(resource_path)
        if resource_hash != sha256_file(acquired["_resource_path"]):
            raise BlindSamplingError(
                f"{candidate_id} resource differs from the frozen acquisition log"
            )
        if resource_hash in seen_resource_hashes:
            raise BlindSamplingError("candidate resource hashes must be unique")
        seen_resource_hashes.add(resource_hash)
        task = load_json(task_path)
        forbidden = _forbidden_task_key_paths(task)
        if forbidden:
            raise BlindSamplingError(
                f"{candidate_id} task contains outcome-only keys: {forbidden}"
            )
        source_bundle = load_json(source_bundle_path)
        forbidden_source_keys = _forbidden_task_key_paths(source_bundle)
        if forbidden_source_keys:
            raise BlindSamplingError(
                f"{candidate_id} source bundle contains outcome-only keys: {forbidden_source_keys}"
            )
        try:
            target_count = len(build_observation_payload(task)["targets"])
        except Exception as exc:  # noqa: BLE001
            raise BlindSamplingError(
                f"{candidate_id} task cannot produce deterministic observations: {exc}"
            ) from exc
        declared_target_count = item.get("semantic_opportunity_target_count")
        if declared_target_count != target_count:
            raise BlindSamplingError(
                f"{candidate_id} semantic-opportunity target count is not reproducible"
            )
        eligibility = item.get("eligibility")
        if not isinstance(eligibility, dict) or not isinstance(
            eligibility.get("eligible"), bool
        ):
            raise BlindSamplingError(f"{candidate_id} eligibility is invalid")
        reasons = eligibility.get("reasons")
        if not isinstance(reasons, list) or any(
            not isinstance(reason, str) or not reason for reason in reasons
        ):
            raise BlindSamplingError(f"{candidate_id} eligibility reasons are invalid")
        criterion_results = eligibility.get("criterion_results")
        if not isinstance(criterion_results, dict) or set(criterion_results) != set(
            criteria_by_id
        ):
            raise BlindSamplingError(
                f"{candidate_id} must assess every frozen eligibility criterion exactly once"
            )
        if any(not isinstance(value, bool) for value in criterion_results.values()):
            raise BlindSamplingError(
                f"{candidate_id} eligibility criterion results must be booleans"
            )
        failed_criteria = sorted(
            criterion_id
            for criterion_id, observed in criterion_results.items()
            if (criterion_kinds[criterion_id] == "inclusion" and not observed)
            or (criterion_kinds[criterion_id] == "exclusion" and observed)
        )
        expected_eligible = not failed_criteria
        if eligibility["eligible"] != expected_eligible:
            raise BlindSamplingError(
                f"{candidate_id} eligibility is not mechanically derived from criterion results"
            )
        if sorted(reasons) != failed_criteria:
            raise BlindSamplingError(
                f"{candidate_id} eligibility reasons must equal failed criterion IDs"
            )
        known_overlap = (
            resource_hash in known["resource_sha256s"]
            or source_identity in known["source_identities"]
        )
        if "known_nonblind_overlap" not in criterion_results:
            raise BlindSamplingError(
                "frozen criteria must include known_nonblind_overlap"
            )
        if criterion_results["known_nonblind_overlap"] != known_overlap:
            raise BlindSamplingError(
                f"{candidate_id} known_nonblind_overlap is not reproducible"
            )
        if known_overlap and eligibility["eligible"]:
            raise BlindSamplingError(
                f"{candidate_id} overlaps a known non-blind source but is eligible"
            )
        normalized.append(
            {
                **item,
                "_resource_path": resource_path,
                "_task_path": task_path,
                "_source_bundle_path": source_bundle_path,
                "_resource_sha256": resource_hash,
            }
        )
    if seen_ids != set(acquired_by_candidate):
        missing = sorted(set(acquired_by_candidate) - seen_ids)
        extra = sorted(seen_ids - set(acquired_by_candidate))
        raise BlindSamplingError(
            f"candidate frame must cover every acquired record; missing={missing}, extra={extra}"
        )
    return {
        "payload": payload,
        "candidates": normalized,
        "known_nonblind_resources_sha256": sha256_file(known_path),
        "acquisition_log_sha256": sha256_file(acquisition_path),
    }


def _validate_sampling_design(path: Path) -> Dict[str, Any]:
    path = path.resolve()
    payload = load_json(path)
    if payload.get("schema_version") != DESIGN_SCHEMA_VERSION:
        raise BlindSamplingError(f"expected {DESIGN_SCHEMA_VERSION}")
    if payload.get("protocol_version") != PROTOCOL_VERSION:
        raise BlindSamplingError(f"expected {PROTOCOL_VERSION}")
    if payload.get("status") != "frozen_before_selection":
        raise BlindSamplingError("sampling design must be frozen_before_selection")
    if not str(payload.get("design_id") or "").strip():
        raise BlindSamplingError("sampling design_id is required")
    if payload.get("selection_algorithm") != SELECTION_ALGORITHM:
        raise BlindSamplingError(f"selection_algorithm must be {SELECTION_ALGORITHM}")
    if not str(payload.get("selection_seed") or ""):
        raise BlindSamplingError("selection_seed is required")
    seed_provenance = payload.get("seed_provenance")
    if not isinstance(seed_provenance, dict):
        raise BlindSamplingError("seed_provenance is required")
    if seed_provenance.get("committed_before_selection") is not True:
        raise BlindSamplingError("selection seed must be committed before selection")
    for key in ("method", "source"):
        if not str(seed_provenance.get(key) or "").strip():
            raise BlindSamplingError(f"seed_provenance.{key} is required")
    frame_path = _check_file(path, payload.get("candidate_frame"), "candidate frame")
    frame = validate_candidate_frame(frame_path)
    power_path = _check_file(path, payload.get("power_analysis"), "power analysis")
    power = load_json(power_path)
    if (
        power.get("schema_version") != POWER_SCHEMA_VERSION
        or power.get("status") != "frozen"
    ):
        raise BlindSamplingError("sampling design requires a frozen power analysis")
    required_count = power.get("assumptions", {}).get("required_dataset_count")
    required_opportunities = power.get("assumptions", {}).get(
        "required_semantic_opportunity_case_count"
    )
    if payload.get("required_dataset_count") != required_count:
        raise BlindSamplingError(
            "sampling design dataset count differs from power analysis"
        )
    if (
        payload.get("required_semantic_opportunity_case_count")
        != required_opportunities
    ):
        raise BlindSamplingError(
            "sampling design opportunity count differs from power analysis"
        )
    if not isinstance(required_count, int) or required_count <= 0:
        raise BlindSamplingError("required dataset count must be positive")
    if (
        not isinstance(required_opportunities, int)
        or not 0 < required_opportunities <= required_count
    ):
        raise BlindSamplingError("required opportunity count is invalid")
    quotas = payload.get("stratum_quotas")
    if not isinstance(quotas, dict) or not quotas:
        raise BlindSamplingError("stratum_quotas must be a non-empty object")
    if any(
        not isinstance(key, str)
        or not key
        or not isinstance(value, int)
        or isinstance(value, bool)
        or value <= 0
        for key, value in quotas.items()
    ):
        raise BlindSamplingError("every stratum quota must be a positive integer")
    if sum(quotas.values()) != required_count:
        raise BlindSamplingError("stratum quotas must sum to required_dataset_count")
    frame_strata = {
        str(item["selection_stratum"])
        for item in frame["candidates"]
        if item["eligibility"]["eligible"]
    }
    missing = sorted(set(quotas) - frame_strata)
    if missing:
        raise BlindSamplingError(f"sampling design strata absent from frame: {missing}")
    minimum_families = payload.get("minimum_scientific_family_count")
    maximum_source = payload.get("maximum_cases_per_source_repository")
    if (
        not isinstance(minimum_families, int)
        or isinstance(minimum_families, bool)
        or minimum_families <= 0
    ):
        raise BlindSamplingError("minimum_scientific_family_count must be positive")
    if (
        not isinstance(maximum_source, int)
        or isinstance(maximum_source, bool)
        or maximum_source <= 0
    ):
        raise BlindSamplingError("maximum_cases_per_source_repository must be positive")
    if payload.get("maximum_cases_per_dataset_group") != 1:
        raise BlindSamplingError("maximum_cases_per_dataset_group must remain 1")
    return {
        "payload": payload,
        "frame_path": frame_path,
        "frame": frame,
        "power_path": power_path,
        "power": power,
    }


def preflight_sampling_design(path: Path) -> Dict[str, Any]:
    try:
        validated = _validate_sampling_design(path)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [{"code": "blind_sampling_design_invalid", "detail": str(exc)}],
        }
    payload = validated["payload"]
    eligible = [
        item
        for item in validated["frame"]["candidates"]
        if item["eligibility"]["eligible"]
    ]
    counts = {
        stratum: sum(item["selection_stratum"] == stratum for item in eligible)
        for stratum in sorted(payload["stratum_quotas"])
    }
    return {
        "status": "ready_for_external_registration",
        "errors": [],
        "design_sha256": sha256_file(path.resolve()),
        "candidate_frame_sha256": sha256_file(validated["frame_path"]),
        "power_analysis_sha256": sha256_file(validated["power_path"]),
        "eligible_candidate_count": len(eligible),
        "eligible_count_by_stratum": counts,
        "required_dataset_count": payload["required_dataset_count"],
        "required_semantic_opportunity_case_count": payload[
            "required_semantic_opportunity_case_count"
        ],
        "not_a_registration_receipt": True,
    }


def _validate_receipt(receipt_path: Path, design_sha256: str) -> Dict[str, Any]:
    receipt = load_json(receipt_path)
    if receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise BlindSamplingError(f"expected {RECEIPT_SCHEMA_VERSION}")
    if receipt.get("design_sha256") != design_sha256:
        raise BlindSamplingError("registration receipt does not bind sampling design")
    for key in ("registered_at", "registry", "registration_identifier"):
        if not str(receipt.get(key) or "").strip():
            raise BlindSamplingError(f"registration receipt {key} is required")
    if receipt.get("frozen_before_selection") is not True:
        raise BlindSamplingError(
            "sampling receipt must state frozen_before_selection=true"
        )
    if receipt.get("selection_not_executed_at_registration") is not True:
        raise BlindSamplingError(
            "sampling receipt must state selection_not_executed_at_registration=true"
        )
    return receipt


def _selection_key(seed: str, candidate: Dict[str, Any]) -> str:
    material = "\x1f".join(
        [seed, str(candidate["candidate_id"]), candidate["_resource_sha256"]]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_blind_selection(
    *, design_path: Path, receipt_path: Path, output_path: Path
) -> Dict[str, Any]:
    design_path = design_path.resolve()
    receipt_path = receipt_path.resolve()
    output_path = output_path.resolve()
    validated = _validate_sampling_design(design_path)
    design = validated["payload"]
    design_hash = sha256_file(design_path)
    receipt = _validate_receipt(receipt_path, design_hash)
    eligible = [
        item
        for item in validated["frame"]["candidates"]
        if item["eligibility"]["eligible"]
    ]
    seed = str(design["selection_seed"])
    selected: List[Dict[str, Any]] = []
    used_groups: set[str] = set()
    source_counts: Dict[str, int] = {}
    stratum_results: Dict[str, Any] = {}
    max_source = int(design["maximum_cases_per_source_repository"])
    for stratum in sorted(design["stratum_quotas"]):
        quota = int(design["stratum_quotas"][stratum])
        ranked = sorted(
            (item for item in eligible if item["selection_stratum"] == stratum),
            key=lambda item: (_selection_key(seed, item), item["candidate_id"]),
        )
        accepted = []
        for item in ranked:
            group = str(item["dataset_group_id"])
            source = str(item["source_repository"])
            if group in used_groups or source_counts.get(source, 0) >= max_source:
                continue
            accepted.append(item)
            selected.append(item)
            used_groups.add(group)
            source_counts[source] = source_counts.get(source, 0) + 1
            if len(accepted) == quota:
                break
        if len(accepted) != quota:
            raise BlindSamplingError(
                f"frozen constraints cannot fill stratum {stratum!r}: required {quota}, selected {len(accepted)}"
            )
        stratum_results[stratum] = {
            "quota": quota,
            "eligible_candidate_count": len(ranked),
            "selected_candidate_ids": [item["candidate_id"] for item in accepted],
        }
    opportunity_count = sum(
        int(item["semantic_opportunity_target_count"]) > 0 for item in selected
    )
    required_opportunities = int(design["required_semantic_opportunity_case_count"])
    if opportunity_count < required_opportunities:
        raise BlindSamplingError(
            "frozen selection contains fewer semantic-opportunity cases than required"
        )
    family_count = len({str(item["scientific_family"]) for item in selected})
    if family_count < int(design["minimum_scientific_family_count"]):
        raise BlindSamplingError(
            "frozen selection contains fewer scientific families than required"
        )
    implementation_path = Path(__file__).resolve()
    selected_cases = [
        {
            "case_id": item["candidate_id"],
            "candidate_id": item["candidate_id"],
            "dataset_group_id": item["dataset_group_id"],
            "source_repository": item["source_repository"],
            "source_identity": item["source_identity"],
            "source_record_id": item["source_record_id"],
            "source_resource_id": item["source_resource_id"],
            "scientific_family": item["scientific_family"],
            "file_format": item["file_format"],
            "selection_stratum": item["selection_stratum"],
            "selection_priority_sha256": _selection_key(seed, item),
            "semantic_opportunity_target_count": item[
                "semantic_opportunity_target_count"
            ],
            "resource_file": _relative(item["_resource_path"], output_path),
            "resource_sha256": item["_resource_sha256"],
            "task_file": _relative(item["_task_path"], output_path),
            "task_sha256": sha256_file(item["_task_path"]),
            "source_bundle_file": _relative(item["_source_bundle_path"], output_path),
            "source_bundle_sha256": sha256_file(item["_source_bundle_path"]),
        }
        for item in selected
    ]
    return {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "status": "selected_and_frozen",
        "research_evidence_status": "blind_corpus_selection_not_architecture_outcome",
        "selection_boundary": {
            "model_outputs_consulted": False,
            "architecture_results_consulted": False,
            "gold_labels_created": False,
        },
        "source_artifacts": {
            "sampling_design": {
                "file": _relative(design_path, output_path),
                "sha256": design_hash,
            },
            "candidate_frame": {
                "file": _relative(validated["frame_path"], output_path),
                "sha256": sha256_file(validated["frame_path"]),
            },
            "power_analysis": {
                "file": _relative(validated["power_path"], output_path),
                "sha256": sha256_file(validated["power_path"]),
            },
            "registration_receipt": {
                "file": _relative(receipt_path, output_path),
                "sha256": sha256_file(receipt_path),
                "registered_at": receipt["registered_at"],
                "registry": receipt["registry"],
                "registration_identifier": receipt["registration_identifier"],
            },
        },
        "selection_algorithm": SELECTION_ALGORITHM,
        "selection_seed_sha256": hashlib.sha256(seed.encode("utf-8")).hexdigest(),
        "required_dataset_count": design["required_dataset_count"],
        "selected_dataset_count": len(selected_cases),
        "required_semantic_opportunity_case_count": required_opportunities,
        "selected_semantic_opportunity_case_count": opportunity_count,
        "minimum_scientific_family_count": design["minimum_scientific_family_count"],
        "selected_scientific_family_count": family_count,
        "strata": stratum_results,
        "selected_cases": selected_cases,
        "analysis_implementation": {
            "file": implementation_path.name,
            "sha256": sha256_file(implementation_path),
        },
        "runtime": {"python": platform.python_version()},
    }


def validate_blind_selection(path: Path) -> Dict[str, Any]:
    try:
        payload = load_json(path)
        if payload.get("schema_version") != SELECTION_SCHEMA_VERSION:
            raise BlindSamplingError(f"expected {SELECTION_SCHEMA_VERSION}")
        sources = payload.get("source_artifacts", {})
        design_path = _check_file(
            path, sources.get("sampling_design"), "sampling design"
        )
        receipt_path = _check_file(
            path, sources.get("registration_receipt"), "registration receipt"
        )
        expected = build_blind_selection(
            design_path=design_path,
            receipt_path=receipt_path,
            output_path=path,
        )
        if payload != expected:
            differing = sorted(
                key
                for key in set(payload) | set(expected)
                if payload.get(key) != expected.get(key)
            )
            raise BlindSamplingError(
                f"recomputed selection differs at keys: {differing}"
            )
        return {"status": "ready", "errors": [], "payload": payload}
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [{"code": "blind_selection_invalid", "detail": str(exc)}],
        }


def _write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preflight and execute frozen blind-corpus sampling."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    registry = commands.add_parser("build-known-registry")
    registry.add_argument("--grounding-manifest", type=Path, required=True)
    registry.add_argument("--data-root", type=Path, required=True)
    registry.add_argument("--frozen-at", required=True)
    registry.add_argument("--output", type=Path, required=True)
    validate_registry = commands.add_parser("validate-known-registry")
    validate_registry.add_argument("--artifact", type=Path, required=True)
    validate_acquisition = commands.add_parser("validate-acquisition")
    validate_acquisition.add_argument("--artifact", type=Path, required=True)
    preflight = commands.add_parser("preflight-design")
    preflight.add_argument("--design", type=Path, required=True)
    select = commands.add_parser("select")
    select.add_argument("--design", type=Path, required=True)
    select.add_argument("--receipt", type=Path, required=True)
    select.add_argument("--output", type=Path, required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--artifact", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build-known-registry":
        payload = build_known_nonblind_registry(
            grounding_manifest_path=args.grounding_manifest,
            data_root=args.data_root,
            frozen_at=args.frozen_at,
            output_path=args.output,
        )
        _write(args.output, payload)
        _validate_known_resources(args.output.resolve())
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "record_count": payload["coverage"]["total_record_count"],
                    "resource_hash_available_count": payload["coverage"][
                        "resource_hash_available_count"
                    ],
                    "output": str(args.output.resolve()),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "validate-known-registry":
        report = validate_known_nonblind_registry(args.artifact)
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if report["status"] == "ready" else 1
    if args.command == "validate-acquisition":
        try:
            validated = validate_acquisition_log(args.artifact)
            report = {
                "status": "ready",
                "errors": [],
                "artifact_sha256": sha256_file(args.artifact.resolve()),
                **validated["payload"]["counts"],
            }
        except Exception as exc:  # noqa: BLE001
            report = {
                "status": "blocked",
                "errors": [{"code": "blind_acquisition_invalid", "detail": str(exc)}],
            }
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if report["status"] == "ready" else 1
    if args.command == "preflight-design":
        report = preflight_sampling_design(args.design)
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if report["status"] == "ready_for_external_registration" else 1
    if args.command == "select":
        payload = build_blind_selection(
            design_path=args.design,
            receipt_path=args.receipt,
            output_path=args.output,
        )
        _write(args.output, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "selected_dataset_count": payload["selected_dataset_count"],
                    "output": str(args.output.resolve()),
                },
                indent=2,
            )
        )
        return 0
    report = validate_blind_selection(args.artifact)
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
