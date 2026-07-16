from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


ADAPTER_ID = "zenodo_dryad_catalog_snapshot/v1"
SNAPSHOT_SCHEMA_VERSION = "semantic-catalog-snapshot/v1"
SUPPORTED_REPOSITORIES = {"zenodo", "dryad"}
ALLOWED_HOST_BY_REPOSITORY = {
    "zenodo": "zenodo.org",
    "dryad": "datadryad.org",
}

FORMAT_BY_SUFFIX = {
    ".csv": "csv",
    ".tsv": "csv",
    ".h5": "hdf5",
    ".hdf5": "hdf5",
    ".hdf": "hdf5",
    ".he5": "hdf5",
    ".nc": "netcdf",
    ".cdf": "netcdf",
    ".json": "json",
    ".jsonl": "json",
    ".ndjson": "json",
    ".parquet": "parquet",
}


class CatalogSnapshotError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fetch_json(url: str, repository: str, timeout_seconds: float) -> Dict[str, Any]:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != ALLOWED_HOST_BY_REPOSITORY[repository]
    ):
        raise CatalogSnapshotError(
            f"{repository} URL must use its frozen official HTTPS host"
        )
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "high-fidelity-schema-study-blind-acquisition/1",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        charset = response.headers.get_content_charset() or "utf-8"
        payload = json.loads(response.read().decode(charset))
    if not isinstance(payload, dict):
        raise CatalogSnapshotError("catalog API response must be a JSON object")
    return payload


def capture_catalog_snapshot(
    *, repository: str, request_url: str, page_ordinal: int, timeout_seconds: float
) -> Dict[str, Any]:
    if repository not in SUPPORTED_REPOSITORIES:
        raise CatalogSnapshotError(f"unsupported repository: {repository!r}")
    if page_ordinal <= 0:
        raise CatalogSnapshotError("page_ordinal must be positive")
    retrieved_at = _utc_now()
    raw = _fetch_json(request_url, repository, timeout_seconds)
    payload: Dict[str, Any] = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "adapter_id": ADAPTER_ID,
        "source_repository": repository,
        "page_ordinal": page_ordinal,
        "request_url": request_url,
        "retrieved_at": retrieved_at,
        "raw_catalog_response": raw,
    }
    if repository == "dryad":
        datasets = raw.get("_embedded", {}).get("stash:datasets")
        if not isinstance(datasets, list):
            raise CatalogSnapshotError("Dryad stash:datasets must be a list")
        expansions = []
        for dataset in datasets:
            identifier = str(dataset.get("identifier") or "")
            version_href = str(
                (dataset.get("_links") or {}).get("stash:version", {}).get("href") or ""
            )
            if not identifier or not version_href:
                raise CatalogSnapshotError(
                    "Dryad dataset identifier and version link are required"
                )
            version_url = urljoin("https://datadryad.org", version_href)
            version_response = _fetch_json(version_url, "dryad", timeout_seconds)
            files_href = str(
                (version_response.get("_links") or {})
                .get("stash:files", {})
                .get("href")
                or ""
            )
            if not files_href:
                raise CatalogSnapshotError("Dryad version files link is required")
            files_url = urljoin("https://datadryad.org", files_href)
            files_response = _fetch_json(files_url, "dryad", timeout_seconds)
            expansions.append(
                {
                    "identifier": identifier,
                    "version_request_url": version_url,
                    "version_response": version_response,
                    "files_request_url": files_url,
                    "files_response": files_response,
                }
            )
        payload["dataset_expansions"] = expansions
    return payload


def _canonical_source_identity(
    source_repository: str, source_record_id: str, source_resource_id: str
) -> str:
    values = {
        "source_record_id": source_record_id.strip(),
        "source_repository": source_repository.strip().casefold(),
        "source_resource_id": source_resource_id.strip(),
    }
    if any(not value for value in values.values()):
        raise CatalogSnapshotError("source identity components are required")
    material = json.dumps(
        values, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _format_for_resource(resource_id: str) -> str:
    lowered = resource_id.casefold()
    for suffix, file_format in FORMAT_BY_SUFFIX.items():
        if lowered.endswith(suffix):
            return file_format
    return "unsupported"


def _first_text(values: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list):
        return None
    found: List[str] = []
    for value in values:
        if isinstance(value, str) and value.strip():
            found.append(value.strip())
        elif isinstance(value, dict):
            for key in keys:
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    found.append(candidate.strip())
                    break
    return sorted(found, key=str.casefold)[0] if found else None


def _zenodo_resources(raw: Dict[str, Any]) -> tuple[int, List[Dict[str, Any]]]:
    hits = raw.get("hits", {}).get("hits")
    if not isinstance(hits, list):
        raise CatalogSnapshotError("Zenodo response hits.hits must be a list")
    resources: List[Dict[str, Any]] = []
    for record in hits:
        if not isinstance(record, dict):
            raise CatalogSnapshotError("Zenodo records must be objects")
        record_id = str(record.get("id") or record.get("recid") or "")
        if not record_id:
            raise CatalogSnapshotError("Zenodo record ID is required")
        metadata = record.get("metadata") or {}
        concept_id = str(record.get("conceptrecid") or record_id)
        family = _first_text(metadata.get("subjects"), ("subject", "title", "id"))
        rights = metadata.get("rights")
        license_value = _first_text(rights, ("id", "title"))
        if license_value is None:
            license_value = _first_text(metadata.get("license"), ("id", "title"))
        files = record.get("files") or []
        if not isinstance(files, list):
            raise CatalogSnapshotError("Zenodo record files must be a list")
        for file_record in files:
            if not isinstance(file_record, dict):
                raise CatalogSnapshotError("Zenodo file records must be objects")
            resource_id = str(file_record.get("key") or "")
            source_url = str((file_record.get("links") or {}).get("self") or "")
            size = file_record.get("size")
            checksum = str(file_record.get("checksum") or "unreported")
            if not resource_id or not source_url:
                raise CatalogSnapshotError("Zenodo file identity and URL are required")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise CatalogSnapshotError("Zenodo file size must be non-negative")
            resources.append(
                _resource_record(
                    repository="zenodo",
                    record_id=f"record_{record_id}",
                    resource_id=resource_id,
                    dataset_group_id=f"zenodo::concept::{concept_id}",
                    source_url=source_url,
                    source_size_bytes=size,
                    provider_checksum=checksum,
                    license_value=license_value or "unreported",
                    scientific_family=family or "unclassified",
                )
            )
    return len(hits), resources


def _dryad_record_id(identifier: str) -> str:
    normalized = identifier.strip().casefold()
    if normalized.startswith("doi:"):
        normalized = normalized[4:]
    return normalized.replace("/", "_")


def _dryad_resources(payload: Dict[str, Any]) -> tuple[int, List[Dict[str, Any]]]:
    raw = payload.get("raw_catalog_response")
    if not isinstance(raw, dict):
        raise CatalogSnapshotError("Dryad raw_catalog_response is required")
    datasets = raw.get("_embedded", {}).get("stash:datasets")
    if not isinstance(datasets, list):
        raise CatalogSnapshotError("Dryad stash:datasets must be a list")
    expansions = payload.get("dataset_expansions")
    if not isinstance(expansions, list):
        raise CatalogSnapshotError("Dryad dataset_expansions must be a list")
    expansion_by_identifier: Dict[str, Dict[str, Any]] = {}
    for expansion in expansions:
        if not isinstance(expansion, dict):
            raise CatalogSnapshotError("Dryad expansions must be objects")
        identifier = str(expansion.get("identifier") or "")
        if not identifier or identifier in expansion_by_identifier:
            raise CatalogSnapshotError("Dryad expansion identifiers must be unique")
        expansion_by_identifier[identifier] = expansion
    dataset_identifiers = [str(dataset.get("identifier") or "") for dataset in datasets]
    if set(dataset_identifiers) != set(expansion_by_identifier):
        raise CatalogSnapshotError(
            "Dryad expansions must cover every returned dataset exactly once"
        )
    resources: List[Dict[str, Any]] = []
    for dataset in datasets:
        identifier = str(dataset["identifier"])
        expansion = expansion_by_identifier[identifier]
        files = (
            expansion.get("files_response", {}).get("_embedded", {}).get("stash:files")
        )
        if not isinstance(files, list):
            raise CatalogSnapshotError("Dryad stash:files must be a list")
        family_raw = dataset.get("fieldOfScience")
        family = (
            family_raw.strip()
            if isinstance(family_raw, str) and family_raw.strip()
            else "unclassified"
        )
        license_value = str(dataset.get("license") or "unreported")
        record_id = _dryad_record_id(identifier)
        for file_record in files:
            if not isinstance(file_record, dict):
                raise CatalogSnapshotError("Dryad file records must be objects")
            resource_id = str(file_record.get("path") or "")
            download = str(
                (file_record.get("_links") or {}).get("stash:download", {}).get("href")
                or ""
            )
            source_url = urljoin("https://datadryad.org", download)
            size = file_record.get("size")
            digest = str(file_record.get("digest") or "")
            digest_type = str(file_record.get("digestType") or "")
            if not resource_id or not download:
                raise CatalogSnapshotError("Dryad file identity and URL are required")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise CatalogSnapshotError("Dryad file size must be non-negative")
            checksum = (
                f"{digest_type}:{digest}" if digest and digest_type else "unreported"
            )
            resources.append(
                _resource_record(
                    repository="dryad",
                    record_id=record_id,
                    resource_id=resource_id,
                    dataset_group_id=f"dryad::{record_id}",
                    source_url=source_url,
                    source_size_bytes=size,
                    provider_checksum=checksum,
                    license_value=license_value,
                    scientific_family=family,
                )
            )
    return len(datasets), resources


def _resource_record(
    *,
    repository: str,
    record_id: str,
    resource_id: str,
    dataset_group_id: str,
    source_url: str,
    source_size_bytes: int,
    provider_checksum: str,
    license_value: str,
    scientific_family: str,
) -> Dict[str, Any]:
    identity = _canonical_source_identity(repository, record_id, resource_id)
    file_format = _format_for_resource(resource_id)
    return {
        "dataset_group_id": dataset_group_id,
        "source_identity": identity,
        "source_repository": repository,
        "source_record_id": record_id,
        "source_resource_id": resource_id,
        "source_url": source_url,
        "source_size_bytes": source_size_bytes,
        "provider_checksum": provider_checksum,
        "license": license_value,
        "scientific_family": scientific_family,
        "file_format": file_format,
        "selection_stratum": file_format,
    }


def normalize_catalog_snapshot(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise CatalogSnapshotError(f"expected {SNAPSHOT_SCHEMA_VERSION}")
    if payload.get("adapter_id") != ADAPTER_ID:
        raise CatalogSnapshotError(f"expected adapter {ADAPTER_ID}")
    repository = str(payload.get("source_repository") or "")
    if repository not in SUPPORTED_REPOSITORIES:
        raise CatalogSnapshotError(f"unsupported repository: {repository!r}")
    for key in ("request_url", "retrieved_at"):
        if not str(payload.get(key) or "").strip():
            raise CatalogSnapshotError(f"snapshot {key} is required")
    page_ordinal = payload.get("page_ordinal")
    if (
        not isinstance(page_ordinal, int)
        or isinstance(page_ordinal, bool)
        or page_ordinal <= 0
    ):
        raise CatalogSnapshotError("snapshot page_ordinal must be positive")
    raw = payload.get("raw_catalog_response")
    if not isinstance(raw, dict):
        raise CatalogSnapshotError("raw_catalog_response must be an object")
    if repository == "zenodo":
        dataset_count, resources = _zenodo_resources(raw)
    else:
        dataset_count, resources = _dryad_resources(payload)
    resources.sort(key=lambda item: item["source_identity"])
    identities = [item["source_identity"] for item in resources]
    if len(identities) != len(set(identities)):
        raise CatalogSnapshotError("snapshot contains duplicate source identities")
    return {
        "adapter_id": ADAPTER_ID,
        "source_repository": repository,
        "page_ordinal": page_ordinal,
        "request_url": payload["request_url"],
        "retrieved_at": payload["retrieved_at"],
        "returned_dataset_record_count": dataset_count,
        "enumerated_resource_count": len(resources),
        "resources": resources,
    }


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture and replay frozen Zenodo/Dryad catalog snapshots."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture")
    capture.add_argument(
        "--repository", choices=sorted(SUPPORTED_REPOSITORIES), required=True
    )
    capture.add_argument("--request-url", required=True)
    capture.add_argument("--page-ordinal", type=int, required=True)
    capture.add_argument("--timeout-seconds", type=float, default=30.0)
    capture.add_argument("--output", type=Path, required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--snapshot", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "capture":
        payload = capture_catalog_snapshot(
            repository=args.repository,
            request_url=args.request_url,
            page_ordinal=args.page_ordinal,
            timeout_seconds=args.timeout_seconds,
        )
        _write_json(args.output, payload)
        normalized = normalize_catalog_snapshot(args.output)
        print(json.dumps(normalized, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    normalized = normalize_catalog_snapshot(args.snapshot)
    print(json.dumps(normalized, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
