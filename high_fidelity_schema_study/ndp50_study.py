from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
import mimetypes
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


SNAPSHOT_SCHEMA_VERSION = "ndp-catalog-snapshot/v1"
FRAME_SCHEMA_VERSION = "ndp50-candidate-frame/v1"
INDEX_SNAPSHOT_SCHEMA_VERSION = "ndp-catalog-index-snapshot/v1"
INDEX_FRAME_SCHEMA_VERSION = "ndp50-index-frame/v1"
DETAIL_SNAPSHOT_SCHEMA_VERSION = "ndp-dataset-detail-snapshot/v1"
DESIGN_SCHEMA_VERSION = "ndp50-selection-design/v1"
SELECTION_SCHEMA_VERSION = "ndp50-selection/v1"
ADAPTER_ID = "ndp-ckan-catalog-snapshot/v1"
NDP_CKAN_HOST = "nationaldataplatform.org"
NDP_PACKAGE_SEARCH_PATH = "/catalog/api/3/action/package_search"
NDP_PACKAGE_SHOW_PATH = "/catalog/api/3/action/package_show"
INDEX_REQUIRED_FIELDS = {
    "id",
    "metadata_modified",
    "name",
    "organization",
    "res_format",
    "title",
}

SUPPORTED_FORMATS = {
    "csv",
    "hdf5",
    "json",
    "netcdf",
    "parquet",
    "xml",
    "zarr",
}

FORMAT_ALIASES = {
    "csv": "csv",
    "text/csv": "csv",
    "tsv": "csv",
    "text/tab-separated-values": "csv",
    "h5": "hdf5",
    "hdf": "hdf5",
    "hdf5": "hdf5",
    "application/x-hdf5": "hdf5",
    "application/x-hdf": "hdf5",
    "nc": "netcdf",
    "cdf": "netcdf",
    "netcdf": "netcdf",
    "application/x-netcdf": "netcdf",
    "json": "json",
    "jsonl": "json",
    "ndjson": "json",
    "application/json": "json",
    "application/x-ndjson": "json",
    "geojson": "json",
    "application/geo+json": "json",
    "parquet": "parquet",
    "application/vnd.apache.parquet": "parquet",
    "xml": "xml",
    "application/xml": "xml",
    "text/xml": "xml",
    "zarr": "zarr",
    "zip": "archive",
    "application/zip": "archive",
    "tar": "archive",
    "gz": "archive",
    "gzip": "archive",
    "application/gzip": "archive",
    "7z": "archive",
    "image/tiff": "geospatial_or_image",
    "tif": "geospatial_or_image",
    "tiff": "geospatial_or_image",
    "geotiff": "geospatial_or_image",
    "las": "geospatial_or_image",
    "laz": "geospatial_or_image",
    "jpg": "image",
    "jpeg": "image",
    "png": "image",
    "image/jpeg": "image",
    "image/png": "image",
    "pdf": "document",
    "application/pdf": "document",
    "html": "document",
    "text/html": "document",
    "md": "document",
    "markdown": "document",
    "text/markdown": "document",
    "txt": "text",
    "text/plain": "text",
}

SUFFIX_FORMATS = {
    ".csv": "csv",
    ".tsv": "csv",
    ".h5": "hdf5",
    ".hdf": "hdf5",
    ".hdf5": "hdf5",
    ".he5": "hdf5",
    ".nc": "netcdf",
    ".cdf": "netcdf",
    ".json": "json",
    ".jsonl": "json",
    ".ndjson": "json",
    ".parquet": "parquet",
    ".xml": "xml",
    ".zarr": "zarr",
    ".zip": "archive",
    ".tar": "archive",
    ".gz": "archive",
    ".tgz": "archive",
    ".7z": "archive",
    ".tif": "geospatial_or_image",
    ".tiff": "geospatial_or_image",
    ".las": "geospatial_or_image",
    ".laz": "geospatial_or_image",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".pdf": "document",
    ".html": "document",
    ".htm": "document",
    ".md": "document",
    ".txt": "text",
}

METADATA_COMPLETENESS_FIELDS = (
    "title",
    "description",
    "tags",
    "organization",
    "license",
    "issue_date",
    "last_update_date",
    "documentation_url",
    "doi",
    "data_type",
    "column_dictionary",
    "spatial",
    "temporal",
    "provenance",
)


class NDPStudyError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if path.suffix.casefold() == ".gz":
        with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    else:
        path.write_text(text, encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    if path.suffix.casefold() == ".gz":
        with gzip.open(path, "rt", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    else:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise NDPStudyError(f"{path} must contain a JSON object")
    return payload


def _require_ndp_search_url(request_url: str) -> None:
    parsed = urlparse(request_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != NDP_CKAN_HOST
        or parsed.path != NDP_PACKAGE_SEARCH_PATH
    ):
        raise NDPStudyError(
            "request URL must use the official NDP CKAN package_search HTTPS endpoint"
        )
    query = parse_qs(parsed.query)
    if not query.get("q"):
        raise NDPStudyError("NDP package_search URL must freeze a q parameter")
    if not query.get("rows"):
        raise NDPStudyError("NDP package_search URL must freeze a rows parameter")
    if not query.get("sort"):
        raise NDPStudyError("NDP package_search URL must freeze a sort parameter")


def _fetch_json_bytes(
    *, request_url: str, timeout_seconds: float
) -> tuple[Dict[str, Any], bytes]:
    request = Request(
        request_url,
        headers={
            "Accept": "application/json",
            "User-Agent": "high-fidelity-schema-study-ndp50/1",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read()
        payload = json.loads(body.decode(charset))
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise NDPStudyError("NDP CKAN response must be a successful JSON object")
    return payload, body


def capture_catalog_snapshot(
    *,
    request_url: str,
    page_ordinal: int,
    timeout_seconds: float = 60.0,
) -> Dict[str, Any]:
    _require_ndp_search_url(request_url)
    if page_ordinal <= 0:
        raise NDPStudyError("page_ordinal must be positive")
    payload, body = _fetch_json_bytes(
        request_url=request_url, timeout_seconds=timeout_seconds
    )
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("results"), list):
        raise NDPStudyError("NDP CKAN result.results must be a list")
    count = result.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise NDPStudyError("NDP CKAN result.count must be non-negative")
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "adapter_id": ADAPTER_ID,
        "source_repository": "ndp",
        "page_ordinal": page_ordinal,
        "request_url": request_url,
        "retrieved_at": _utc_now(),
        "response_sha256": _sha256_bytes(body),
        "raw_catalog_response": payload,
    }


def capture_index_snapshot(
    *,
    request_url: str,
    page_ordinal: int,
    timeout_seconds: float = 60.0,
) -> Dict[str, Any]:
    _require_ndp_search_url(request_url)
    if page_ordinal <= 0:
        raise NDPStudyError("page_ordinal must be positive")
    parsed = urlparse(request_url)
    query = parse_qs(parsed.query)
    frozen_fields = {
        part.strip()
        for value in query.get("fl", [])
        for part in value.split(",")
        if part.strip()
    }
    if not INDEX_REQUIRED_FIELDS.issubset(frozen_fields):
        raise NDPStudyError(
            "index capture fl must include exactly the fields needed for "
            f"selection: {sorted(INDEX_REQUIRED_FIELDS)}"
        )
    payload, body = _fetch_json_bytes(
        request_url=request_url, timeout_seconds=timeout_seconds
    )
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("results"), list):
        raise NDPStudyError("NDP CKAN index result.results must be a list")
    count = result.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise NDPStudyError("NDP CKAN index result.count must be non-negative")
    return {
        "schema_version": INDEX_SNAPSHOT_SCHEMA_VERSION,
        "adapter_id": ADAPTER_ID,
        "source_repository": "ndp",
        "page_ordinal": page_ordinal,
        "request_url": request_url,
        "retrieved_at": _utc_now(),
        "response_sha256": _sha256_bytes(body),
        "raw_catalog_response": payload,
    }


def capture_dataset_detail(
    *, dataset_id: str, timeout_seconds: float = 90.0
) -> Dict[str, Any]:
    dataset_id = dataset_id.strip()
    if not dataset_id:
        raise NDPStudyError("dataset_id is required")
    request_url = (
        "https://nationaldataplatform.org"
        f"{NDP_PACKAGE_SHOW_PATH}?id={dataset_id}"
    )
    payload, body = _fetch_json_bytes(
        request_url=request_url, timeout_seconds=timeout_seconds
    )
    result = payload.get("result")
    if not isinstance(result, dict) or str(result.get("id") or "") != dataset_id:
        raise NDPStudyError("NDP package_show result does not match dataset_id")
    return {
        "schema_version": DETAIL_SNAPSHOT_SCHEMA_VERSION,
        "adapter_id": ADAPTER_ID,
        "source_repository": "ndp",
        "dataset_id": dataset_id,
        "request_url": request_url,
        "retrieved_at": _utc_now(),
        "response_sha256": _sha256_bytes(body),
        "raw_catalog_response": payload,
    }


def _extra_multimap(extras: Any) -> Dict[str, List[str]]:
    if extras is None:
        return {}
    if not isinstance(extras, list):
        raise NDPStudyError("CKAN extras must be a list")
    values: Dict[str, List[str]] = defaultdict(list)
    for item in extras:
        if not isinstance(item, dict):
            raise NDPStudyError("CKAN extra entries must be objects")
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        value = item.get("value")
        if value is None:
            text = ""
        elif isinstance(value, str):
            text = value.strip()
        else:
            text = _canonical_json(value)
        values[key].append(text)
    return {
        key: sorted(set(items), key=str.casefold)
        for key, items in sorted(values.items(), key=lambda pair: pair[0].casefold())
    }


def _first_extra(extras: Mapping[str, Sequence[str]], *keys: str) -> str | None:
    casefolded = {key.casefold(): values for key, values in extras.items()}
    for key in keys:
        values = casefolded.get(key.casefold(), ())
        for value in values:
            if value.strip():
                return value.strip()
    return None


def _list_like(value: str | None) -> List[str]:
    if value is None or not value.strip():
        return []
    text = value.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        return sorted(
            {str(item).strip() for item in parsed if str(item).strip()},
            key=str.casefold,
        )
    if isinstance(parsed, str) and parsed.strip():
        return [parsed.strip()]
    return sorted(
        {part.strip() for part in re.split(r"[,;|]", text) if part.strip()},
        key=str.casefold,
    )


def _normalize_format_signal(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().casefold()
    if not text:
        return None
    if ";" in text:
        text = text.split(";", 1)[0].strip()
    normalized = FORMAT_ALIASES.get(text)
    if normalized is not None:
        return normalized
    compact = re.sub(r"[^a-z0-9+.-]+", "", text)
    return FORMAT_ALIASES.get(compact, compact or None)


def _suffix_format(name: str, url: str) -> str | None:
    candidates = [name, urlparse(url).path]
    for candidate in candidates:
        lowered = candidate.casefold()
        for suffix, file_format in sorted(
            SUFFIX_FORMATS.items(), key=lambda pair: len(pair[0]), reverse=True
        ):
            if lowered.endswith(suffix):
                return file_format
    return None


def _format_class(format_value: str | None) -> str:
    if format_value in {"csv", "parquet"}:
        return "supported_tabular"
    if format_value in {"hdf5", "netcdf", "zarr"}:
        return "supported_hierarchical"
    if format_value in {"json", "xml"}:
        return "supported_semistructured"
    if format_value == "archive":
        return "archive"
    if format_value in {"geospatial_or_image", "image"}:
        return "geospatial_or_image"
    if format_value in {"document", "text"}:
        return "documentation_or_text"
    return "other_or_unknown"


def _normalize_resource(resource: Any, dataset_id: str) -> Dict[str, Any]:
    if not isinstance(resource, dict):
        raise NDPStudyError("CKAN resources must be objects")
    resource_id = str(resource.get("id") or "").strip()
    if not resource_id:
        raise NDPStudyError(f"dataset {dataset_id} has a resource without an ID")
    name = str(resource.get("name") or "").strip()
    url = str(resource.get("url") or "").strip()
    declared_raw = str(resource.get("format") or "").strip()
    mimetype_raw = str(resource.get("mimetype") or "").strip()
    declared = _normalize_format_signal(declared_raw)
    suffix = _suffix_format(name, url)
    mime = _normalize_format_signal(mimetype_raw)
    if mime is None and name:
        guessed_mime, _ = mimetypes.guess_type(name)
        mime = _normalize_format_signal(guessed_mime)
    signals = {
        key: value
        for key, value in (
            ("declared", declared),
            ("suffix", suffix),
            ("mimetype", mime),
        )
        if value is not None
    }
    unique_signals = sorted(set(signals.values()))
    observed_format = declared or suffix or mime or "unknown"
    parsed = urlparse(url)
    size = resource.get("size")
    size_bytes = (
        size
        if isinstance(size, int) and not isinstance(size, bool) and size >= 0
        else None
    )
    return {
        "resource_id": resource_id,
        "name": name,
        "url": url,
        "url_scheme": parsed.scheme.casefold(),
        "url_host": (parsed.hostname or "").casefold(),
        "description": str(resource.get("description") or "").strip(),
        "declared_format_raw": declared_raw,
        "declared_mimetype_raw": mimetype_raw,
        "format_signals": signals,
        "normalized_format": observed_format,
        "format_class": _format_class(observed_format),
        "format_conflict": len(unique_signals) > 1,
        "extractor_supported": observed_format in SUPPORTED_FORMATS,
        "size_bytes": size_bytes,
        "hash": str(resource.get("hash") or "").strip() or None,
        "created": str(resource.get("created") or "").strip() or None,
        "last_modified": str(resource.get("last_modified") or "").strip() or None,
        "access_url_present": bool(url),
        "http_access_url": parsed.scheme.casefold() in {"http", "https"},
    }


def _normalize_dataset(record: Any) -> Dict[str, Any]:
    if not isinstance(record, dict):
        raise NDPStudyError("CKAN dataset records must be objects")
    dataset_id = str(record.get("id") or "").strip()
    if not dataset_id:
        raise NDPStudyError("CKAN dataset ID is required")
    extras = _extra_multimap(record.get("extras"))
    upload_type = _first_extra(extras, "uploadType")
    entity_type = (
        upload_type.casefold()
        if upload_type
        else str(record.get("type") or "unknown").strip().casefold()
    )
    resources_raw = record.get("resources") or []
    if not isinstance(resources_raw, list):
        raise NDPStudyError(f"dataset {dataset_id} resources must be a list")
    resources = [_normalize_resource(item, dataset_id) for item in resources_raw]
    resource_ids = [item["resource_id"] for item in resources]
    if len(resource_ids) != len(set(resource_ids)):
        raise NDPStudyError(f"dataset {dataset_id} has duplicate resource IDs")
    resources.sort(key=lambda item: item["resource_id"])
    organization = record.get("organization")
    organization_id = str(record.get("owner_org") or "").strip()
    organization_title = ""
    if isinstance(organization, dict):
        organization_id = str(organization.get("id") or organization_id).strip()
        organization_title = str(
            organization.get("title") or organization.get("name") or ""
        ).strip()
    tags = []
    for item in record.get("tags") or []:
        if isinstance(item, dict):
            text = str(item.get("display_name") or item.get("name") or "").strip()
        else:
            text = str(item).strip()
        if text:
            tags.append(text)
    tags = sorted(set(tags), key=str.casefold)
    themes = _list_like(_first_extra(extras, "theme", "themes"))
    scientific_family = (themes or tags or ["unclassified"])[0]
    declared_access = _first_extra(extras, "dataAuthType", "accessRights")
    access_category = "unspecified"
    if declared_access:
        lowered = declared_access.casefold()
        if "public" in lowered or "open" in lowered:
            access_category = "public"
        elif any(token in lowered for token in ("restricted", "private", "request")):
            access_category = "restricted"
        else:
            access_category = "other_declared"
    resource_format_counts = Counter(item["format_class"] for item in resources)
    if resource_format_counts:
        primary_format_class = sorted(
            resource_format_counts,
            key=lambda key: (-resource_format_counts[key], key),
        )[0]
    else:
        primary_format_class = "no_resources"
    fields = {
        "title": str(record.get("title") or "").strip(),
        "description": str(record.get("notes") or "").strip(),
        "tags": tags,
        "organization": organization_title or organization_id,
        "license": str(record.get("license_id") or "").strip()
        or (_first_extra(extras, "license", "otherLicense") or ""),
        "issue_date": _first_extra(extras, "issueDate"),
        "last_update_date": _first_extra(extras, "lastUpdateDate"),
        "documentation_url": _first_extra(extras, "docsURL", "datasetPageUrl"),
        "doi": _first_extra(extras, "doi"),
        "data_type": _first_extra(extras, "dataType"),
        "column_dictionary": _first_extra(
            extras, "columnDataDict", "resDataDict"
        ),
        "spatial": _first_extra(extras, "spatial", "spatialCov", "dataBbox"),
        "temporal": _first_extra(
            extras, "temporal", "startDateTime", "endDateTime", "temporalRes"
        ),
        "provenance": _first_extra(extras, "dataProvenance", "creationMethod"),
    }
    completeness_count = sum(bool(fields[key]) for key in METADATA_COMPLETENESS_FIELDS)
    has_http_resource = any(item["http_access_url"] for item in resources)
    selection_eligible = (
        entity_type == "dataset" and bool(resources) and has_http_resource
    )
    return {
        "dataset_id": dataset_id,
        "name": str(record.get("name") or "").strip(),
        "title": fields["title"],
        "description": fields["description"],
        "entity_type": entity_type,
        "organization_id": organization_id,
        "organization_title": organization_title,
        "tags": tags,
        "themes": themes,
        "scientific_family": scientific_family,
        "access_category": access_category,
        "license": fields["license"] or "unreported",
        "metadata_created": str(record.get("metadata_created") or "").strip() or None,
        "metadata_modified": str(record.get("metadata_modified") or "").strip()
        or None,
        "metadata_fields": fields,
        "metadata_completeness_count": completeness_count,
        "metadata_completeness_denominator": len(METADATA_COMPLETENESS_FIELDS),
        "metadata_completeness_rate": completeness_count
        / len(METADATA_COMPLETENESS_FIELDS),
        "primary_format_class": primary_format_class,
        "resource_format_class_counts": dict(sorted(resource_format_counts.items())),
        "resource_count": len(resources),
        "supported_resource_count": sum(
            item["extractor_supported"] for item in resources
        ),
        "format_conflict_resource_count": sum(
            item["format_conflict"] for item in resources
        ),
        "selection_eligible": selection_eligible,
        "selection_ineligibility_reasons": [
            reason
            for condition, reason in (
                (entity_type != "dataset", "entity_type_not_dataset"),
                (not resources, "no_resources"),
                (bool(resources) and not has_http_resource, "no_http_resource_url"),
            )
            if condition
        ],
        "extras": extras,
        "resources": resources,
    }


def normalize_catalog_snapshot(path: Path) -> Dict[str, Any]:
    payload = _read_json(path)
    if payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise NDPStudyError(f"expected {SNAPSHOT_SCHEMA_VERSION}")
    if payload.get("adapter_id") != ADAPTER_ID:
        raise NDPStudyError(f"expected adapter {ADAPTER_ID}")
    _require_ndp_search_url(str(payload.get("request_url") or ""))
    page_ordinal = payload.get("page_ordinal")
    if (
        not isinstance(page_ordinal, int)
        or isinstance(page_ordinal, bool)
        or page_ordinal <= 0
    ):
        raise NDPStudyError("page_ordinal must be positive")
    raw = payload.get("raw_catalog_response")
    if not isinstance(raw, dict) or raw.get("success") is not True:
        raise NDPStudyError("raw_catalog_response must be successful")
    result = raw.get("result")
    if not isinstance(result, dict):
        raise NDPStudyError("raw catalog result must be an object")
    total_count = result.get("count")
    records = result.get("results")
    if (
        not isinstance(total_count, int)
        or isinstance(total_count, bool)
        or total_count < 0
        or not isinstance(records, list)
    ):
        raise NDPStudyError("raw catalog count/results are invalid")
    datasets = [_normalize_dataset(record) for record in records]
    dataset_ids = [item["dataset_id"] for item in datasets]
    if len(dataset_ids) != len(set(dataset_ids)):
        raise NDPStudyError("snapshot contains duplicate dataset IDs")
    datasets.sort(key=lambda item: item["dataset_id"])
    return {
        "adapter_id": ADAPTER_ID,
        "source_repository": "ndp",
        "page_ordinal": page_ordinal,
        "request_url": payload["request_url"],
        "retrieved_at": str(payload.get("retrieved_at") or ""),
        "catalog_total_count": total_count,
        "returned_dataset_count": len(datasets),
        "datasets": datasets,
    }


def _normalize_index_record(record: Any) -> Dict[str, Any]:
    if not isinstance(record, dict):
        raise NDPStudyError("NDP index records must be objects")
    dataset_id = str(record.get("id") or "").strip()
    if not dataset_id:
        raise NDPStudyError("NDP index record ID is required")
    organization_id = str(record.get("organization") or "").strip()
    formats_raw = record.get("res_format") or []
    if isinstance(formats_raw, str):
        formats_raw = [formats_raw]
    if not isinstance(formats_raw, list):
        raise NDPStudyError(f"index record {dataset_id} res_format must be a list")
    normalized_formats = sorted(
        {
            normalized
            for value in formats_raw
            if (normalized := _normalize_format_signal(str(value))) is not None
        }
    )
    format_class_counts = Counter(_format_class(value) for value in normalized_formats)
    if format_class_counts:
        primary_format_class = sorted(
            format_class_counts,
            key=lambda key: (-format_class_counts[key], key),
        )[0]
    else:
        primary_format_class = "other_or_unknown"
    return {
        "dataset_id": dataset_id,
        "name": str(record.get("name") or "").strip(),
        "title": str(record.get("title") or "").strip(),
        "metadata_modified": str(record.get("metadata_modified") or "").strip()
        or None,
        "organization_id": organization_id,
        "organization_title": organization_id,
        "scientific_family": "unclassified_at_index_stage",
        "primary_format_class": primary_format_class,
        "indexed_resource_formats": normalized_formats,
        "resource_count": None,
        "supported_resource_count": None,
        "selection_eligible": True,
        "selection_ineligibility_reasons": [],
    }


def normalize_index_snapshot(path: Path) -> Dict[str, Any]:
    payload = _read_json(path)
    if payload.get("schema_version") != INDEX_SNAPSHOT_SCHEMA_VERSION:
        raise NDPStudyError(f"expected {INDEX_SNAPSHOT_SCHEMA_VERSION}")
    if payload.get("adapter_id") != ADAPTER_ID:
        raise NDPStudyError(f"expected adapter {ADAPTER_ID}")
    request_url = str(payload.get("request_url") or "")
    _require_ndp_search_url(request_url)
    page_ordinal = payload.get("page_ordinal")
    if (
        not isinstance(page_ordinal, int)
        or isinstance(page_ordinal, bool)
        or page_ordinal <= 0
    ):
        raise NDPStudyError("index snapshot page_ordinal must be positive")
    raw = payload.get("raw_catalog_response")
    if not isinstance(raw, dict) or raw.get("success") is not True:
        raise NDPStudyError("raw_catalog_response must be successful")
    result = raw.get("result")
    if not isinstance(result, dict):
        raise NDPStudyError("raw catalog result must be an object")
    total_count = result.get("count")
    records = result.get("results")
    if (
        not isinstance(total_count, int)
        or isinstance(total_count, bool)
        or total_count < 0
        or not isinstance(records, list)
    ):
        raise NDPStudyError("raw catalog index count/results are invalid")
    datasets = [_normalize_index_record(record) for record in records]
    dataset_ids = [item["dataset_id"] for item in datasets]
    if len(dataset_ids) != len(set(dataset_ids)):
        raise NDPStudyError("index snapshot contains duplicate dataset IDs")
    datasets.sort(key=lambda item: item["dataset_id"])
    return {
        "adapter_id": ADAPTER_ID,
        "source_repository": "ndp",
        "page_ordinal": page_ordinal,
        "request_url": request_url,
        "retrieved_at": str(payload.get("retrieved_at") or ""),
        "catalog_total_count": total_count,
        "returned_dataset_count": len(datasets),
        "datasets": datasets,
    }


def normalize_detail_snapshot(path: Path) -> Dict[str, Any]:
    payload = _read_json(path)
    if payload.get("schema_version") != DETAIL_SNAPSHOT_SCHEMA_VERSION:
        raise NDPStudyError(f"expected {DETAIL_SNAPSHOT_SCHEMA_VERSION}")
    if payload.get("adapter_id") != ADAPTER_ID:
        raise NDPStudyError(f"expected adapter {ADAPTER_ID}")
    raw = payload.get("raw_catalog_response")
    if not isinstance(raw, dict) or raw.get("success") is not True:
        raise NDPStudyError("detail raw_catalog_response must be successful")
    dataset = _normalize_dataset(raw.get("result"))
    if dataset["dataset_id"] != payload.get("dataset_id"):
        raise NDPStudyError("detail dataset ID mismatch")
    return {
        "adapter_id": ADAPTER_ID,
        "source_repository": "ndp",
        "dataset_id": dataset["dataset_id"],
        "request_url": str(payload.get("request_url") or ""),
        "retrieved_at": str(payload.get("retrieved_at") or ""),
        "dataset": dataset,
    }


def build_index_frame(
    *,
    snapshot_paths: Sequence[Path],
    frame_scope: str,
    frozen_at: str | None = None,
) -> Dict[str, Any]:
    if not snapshot_paths:
        raise NDPStudyError("at least one index snapshot is required")
    pages = [normalize_index_snapshot(path) for path in snapshot_paths]
    ordinals = sorted(page["page_ordinal"] for page in pages)
    if ordinals != list(range(1, len(pages) + 1)):
        raise NDPStudyError("index page ordinals must be contiguous from 1")
    total_counts = {page["catalog_total_count"] for page in pages}
    if len(total_counts) != 1:
        raise NDPStudyError("index pages must report one catalog total count")
    datasets = [
        dataset
        for page in sorted(pages, key=lambda item: item["page_ordinal"])
        for dataset in page["datasets"]
    ]
    dataset_ids = [item["dataset_id"] for item in datasets]
    if len(dataset_ids) != len(set(dataset_ids)):
        raise NDPStudyError("index snapshots overlap on dataset IDs")
    total_count = next(iter(total_counts))
    if len(datasets) != total_count:
        raise NDPStudyError(
            "publication-grade index capture must return the complete catalog "
            f"identity frame: returned {len(datasets)} of {total_count}"
        )
    datasets.sort(key=lambda item: item["dataset_id"])
    organization_counts = Counter(
        item["organization_id"] or "unreported" for item in datasets
    )
    format_counts = Counter(item["primary_format_class"] for item in datasets)
    snapshots = []
    for path, page in sorted(
        zip(snapshot_paths, pages), key=lambda pair: pair[1]["page_ordinal"]
    ):
        snapshots.append(
            {
                "page_ordinal": page["page_ordinal"],
                "request_url": page["request_url"],
                "retrieved_at": page["retrieved_at"],
                "returned_dataset_count": page["returned_dataset_count"],
                "file": path.name,
                "sha256": _sha256_file(path),
            }
        )
    return {
        "schema_version": INDEX_FRAME_SCHEMA_VERSION,
        "protocol_version": "ndp50-external-validation-protocol/v1",
        "status": "frozen_before_selection",
        "frozen_at": frozen_at or _utc_now(),
        "construction_boundary": {
            "model_outputs_consulted": False,
            "architecture_results_consulted": False,
            "gold_labels_created": False,
            "dataset_details_expanded": False,
        },
        "frame_definition": {
            "population_scope": frame_scope,
            "candidate_unit": "NDP CKAN dataset identity record",
            "processing_unit": "resource expanded only after split selection",
            "source_repository": "NDP Central Catalog",
            "catalog_total_count_at_capture": total_count,
            "captured_dataset_count": len(datasets),
            "selection_eligibility_rule": (
                "record is present in the complete NDP package_search identity "
                "frame at the frozen retrieval boundary"
            ),
        },
        "adapter": {
            "adapter_id": ADAPTER_ID,
            "implementation_file": Path(__file__).name,
            "implementation_sha256": _sha256_file(Path(__file__)),
        },
        "snapshots": snapshots,
        "counts": {
            "dataset_count": len(datasets),
            "selection_eligible_dataset_count": len(datasets),
            "organization_count": len(organization_counts),
        },
        "distributions": {
            "primary_format_class": dict(sorted(format_counts.items())),
            "organization_id": dict(sorted(organization_counts.items())),
        },
        "datasets": datasets,
    }


def build_candidate_frame(
    *,
    snapshot_paths: Sequence[Path],
    frame_scope: str,
    termination_reason: str,
    frozen_at: str | None = None,
) -> Dict[str, Any]:
    if not snapshot_paths:
        raise NDPStudyError("at least one snapshot is required")
    normalized_pages = [normalize_catalog_snapshot(path) for path in snapshot_paths]
    page_ordinals = [page["page_ordinal"] for page in normalized_pages]
    if sorted(page_ordinals) != list(range(1, len(page_ordinals) + 1)):
        raise NDPStudyError("snapshot page ordinals must be contiguous from 1")
    total_counts = {page["catalog_total_count"] for page in normalized_pages}
    if len(total_counts) != 1:
        raise NDPStudyError("all snapshots must report one catalog total count")
    datasets: List[Dict[str, Any]] = []
    snapshots = []
    for path, page in sorted(
        zip(snapshot_paths, normalized_pages),
        key=lambda pair: pair[1]["page_ordinal"],
    ):
        datasets.extend(page["datasets"])
        snapshots.append(
            {
                "page_ordinal": page["page_ordinal"],
                "request_url": page["request_url"],
                "retrieved_at": page["retrieved_at"],
                "catalog_total_count": page["catalog_total_count"],
                "returned_dataset_count": page["returned_dataset_count"],
                "file": path.name,
                "sha256": _sha256_file(path),
            }
        )
    dataset_ids = [item["dataset_id"] for item in datasets]
    if len(dataset_ids) != len(set(dataset_ids)):
        raise NDPStudyError("candidate frame snapshots overlap on dataset IDs")
    datasets.sort(key=lambda item: item["dataset_id"])
    eligible = [item for item in datasets if item["selection_eligible"]]
    return {
        "schema_version": FRAME_SCHEMA_VERSION,
        "protocol_version": "ndp50-external-validation-protocol/v1",
        "status": "frozen_before_selection",
        "frozen_at": frozen_at or _utc_now(),
        "construction_boundary": {
            "model_outputs_consulted": False,
            "architecture_results_consulted": False,
            "gold_labels_created": False,
        },
        "frame_definition": {
            "population_scope": frame_scope,
            "candidate_unit": "NDP CKAN dataset record",
            "processing_unit": "resource attached to a selected dataset record",
            "source_repository": "NDP Central Catalog",
            "termination_reason": termination_reason,
            "catalog_total_count_at_capture": next(iter(total_counts)),
            "captured_dataset_count": len(datasets),
            "selection_eligibility_rule": (
                "uploadType/type is dataset; at least one resource exists; "
                "at least one resource has an HTTP(S) access URL"
            ),
        },
        "adapter": {
            "adapter_id": ADAPTER_ID,
            "implementation_file": Path(__file__).name,
            "implementation_sha256": _sha256_file(Path(__file__)),
        },
        "snapshots": snapshots,
        "counts": {
            "dataset_count": len(datasets),
            "selection_eligible_dataset_count": len(eligible),
            "resource_count": sum(item["resource_count"] for item in datasets),
            "supported_resource_count": sum(
                item["supported_resource_count"] for item in datasets
            ),
            "format_conflict_resource_count": sum(
                item["format_conflict_resource_count"] for item in datasets
            ),
        },
        "distributions": {
            "entity_type": dict(
                sorted(Counter(item["entity_type"] for item in datasets).items())
            ),
            "primary_format_class": dict(
                sorted(
                    Counter(item["primary_format_class"] for item in eligible).items()
                )
            ),
            "access_category": dict(
                sorted(Counter(item["access_category"] for item in eligible).items())
            ),
            "organization_id": dict(
                sorted(
                    Counter(
                        item["organization_id"] or "unreported" for item in eligible
                    ).items()
                )
            ),
        },
        "datasets": datasets,
    }


def _selection_priority(seed: str, purpose: str, dataset_id: str) -> str:
    return _sha256_bytes(f"{seed}\0{purpose}\0{dataset_id}".encode("utf-8"))


def build_selection(
    *, frame_path: Path, design_path: Path, selected_at: str | None = None
) -> Dict[str, Any]:
    frame = _read_json(frame_path)
    design = _read_json(design_path)
    if frame.get("schema_version") not in {
        FRAME_SCHEMA_VERSION,
        INDEX_FRAME_SCHEMA_VERSION,
    }:
        raise NDPStudyError(
            f"expected frame {FRAME_SCHEMA_VERSION} or {INDEX_FRAME_SCHEMA_VERSION}"
        )
    if design.get("schema_version") != DESIGN_SCHEMA_VERSION:
        raise NDPStudyError(f"expected design {DESIGN_SCHEMA_VERSION}")
    frame_sha256 = _sha256_file(frame_path)
    if design.get("candidate_frame_sha256") != frame_sha256:
        raise NDPStudyError("selection design candidate_frame_sha256 mismatch")
    seed = str(design.get("seed") or "")
    if not seed:
        raise NDPStudyError("selection design seed is required")
    max_per_org = design.get("max_per_organization")
    if (
        not isinstance(max_per_org, int)
        or isinstance(max_per_org, bool)
        or max_per_org <= 0
    ):
        raise NDPStudyError("max_per_organization must be positive")
    strata = design.get("strata")
    if not isinstance(strata, dict) or not strata:
        raise NDPStudyError("selection design strata must be a non-empty object")
    datasets = frame.get("datasets")
    if not isinstance(datasets, list):
        raise NDPStudyError("candidate frame datasets must be a list")
    eligible = [item for item in datasets if item.get("selection_eligible") is True]
    by_stratum: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in eligible:
        by_stratum[str(item.get("primary_format_class") or "other_or_unknown")].append(
            item
        )
    selected: List[Dict[str, Any]] = []
    reserves: List[Dict[str, Any]] = []
    organization_counts: Counter[str] = Counter()
    for stratum_name in sorted(strata):
        stratum_design = strata[stratum_name]
        if not isinstance(stratum_design, dict):
            raise NDPStudyError(f"stratum {stratum_name} design must be an object")
        split_counts = {
            key: stratum_design.get(key)
            for key in ("development", "validation", "test")
        }
        if any(
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            for value in split_counts.values()
        ):
            raise NDPStudyError(f"stratum {stratum_name} split counts are invalid")
        total = sum(split_counts.values())
        reserve_count = stratum_design.get("reserve", 0)
        if (
            not isinstance(reserve_count, int)
            or isinstance(reserve_count, bool)
            or reserve_count < 0
        ):
            raise NDPStudyError(f"stratum {stratum_name} reserve is invalid")
        ranked = sorted(
            by_stratum.get(stratum_name, []),
            key=lambda item: _selection_priority(
                seed, f"select:{stratum_name}", item["dataset_id"]
            ),
        )
        accepted: List[Dict[str, Any]] = []
        deferred: List[Dict[str, Any]] = []
        for item in ranked:
            org = item["organization_id"] or "unreported"
            if organization_counts[org] >= max_per_org:
                deferred.append(item)
                continue
            if len(accepted) < total:
                accepted.append(item)
                organization_counts[org] += 1
            else:
                deferred.append(item)
        if len(accepted) != total:
            raise NDPStudyError(
                f"stratum {stratum_name} cannot satisfy quota {total} "
                f"under organization cap {max_per_org}"
            )
        split_ranked = sorted(
            accepted,
            key=lambda item: _selection_priority(
                seed, f"split:{stratum_name}", item["dataset_id"]
            ),
        )
        offset = 0
        for split_name in ("development", "validation", "test"):
            count = split_counts[split_name]
            for item in split_ranked[offset : offset + count]:
                selected.append(
                    {
                        "dataset_id": item["dataset_id"],
                        "title": item["title"],
                        "organization_id": item["organization_id"],
                        "scientific_family": item["scientific_family"],
                        "primary_format_class": item["primary_format_class"],
                        "resource_count": item.get("resource_count"),
                        "supported_resource_count": item.get(
                            "supported_resource_count"
                        ),
                        "split": split_name,
                        "selection_priority": _selection_priority(
                            seed, f"select:{stratum_name}", item["dataset_id"]
                        ),
                        "split_priority": _selection_priority(
                            seed, f"split:{stratum_name}", item["dataset_id"]
                        ),
                    }
                )
            offset += count
        reserve_ranked = sorted(
            deferred,
            key=lambda item: _selection_priority(
                seed, f"reserve:{stratum_name}", item["dataset_id"]
            ),
        )
        for rank, item in enumerate(reserve_ranked[:reserve_count], start=1):
            reserves.append(
                {
                    "dataset_id": item["dataset_id"],
                    "title": item["title"],
                    "organization_id": item["organization_id"],
                    "primary_format_class": item["primary_format_class"],
                    "reserve_stratum": stratum_name,
                    "reserve_rank": rank,
                    "reserve_priority": _selection_priority(
                        seed, f"reserve:{stratum_name}", item["dataset_id"]
                    ),
                }
            )
    selected.sort(key=lambda item: (item["split"], item["dataset_id"]))
    reserves.sort(
        key=lambda item: (item["reserve_stratum"], item["reserve_rank"])
    )
    expected_split_counts = design.get("split_counts")
    actual_split_counts = dict(
        sorted(Counter(item["split"] for item in selected).items())
    )
    if expected_split_counts != actual_split_counts:
        raise NDPStudyError(
            f"selection split counts {actual_split_counts} do not match design "
            f"{expected_split_counts}"
        )
    target_count = design.get("target_count")
    if target_count != len(selected):
        raise NDPStudyError(
            f"selected {len(selected)} datasets, expected target_count {target_count}"
        )
    return {
        "schema_version": SELECTION_SCHEMA_VERSION,
        "protocol_version": "ndp50-external-validation-protocol/v1",
        "status": "selected_before_outcome_inspection",
        "selected_at": selected_at or _utc_now(),
        "candidate_frame": {
            "file": frame_path.name,
            "sha256": frame_sha256,
        },
        "selection_design": {
            "file": design_path.name,
            "sha256": _sha256_file(design_path),
        },
        "algorithm": "stratum_sha256_priority_with_org_cap_and_frozen_split_quotas/v1",
        "seed": seed,
        "counts": {
            "selected_dataset_count": len(selected),
            "reserve_dataset_count": len(reserves),
            "split_counts": actual_split_counts,
            "stratum_counts": dict(
                sorted(
                    Counter(
                        item["primary_format_class"] for item in selected
                    ).items()
                )
            ),
        },
        "selected_datasets": selected,
        "deterministic_reserves": reserves,
    }


def _summary(payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        key: payload[key]
        for key in (
            "schema_version",
            "status",
            "frozen_at",
            "selected_at",
            "counts",
            "distributions",
        )
        if key in payload
    }


def capture_selected_details(
    *,
    selection_path: Path,
    output_dir: Path,
    splits: Sequence[str],
    timeout_seconds: float,
) -> Dict[str, Any]:
    selection = _read_json(selection_path)
    if selection.get("schema_version") != SELECTION_SCHEMA_VERSION:
        raise NDPStudyError(f"expected {SELECTION_SCHEMA_VERSION}")
    allowed_splits = {"development", "validation", "test"}
    requested_splits = set(splits)
    if not requested_splits or not requested_splits.issubset(allowed_splits):
        raise NDPStudyError(
            f"splits must be one or more of {sorted(allowed_splits)}"
        )
    selected = selection.get("selected_datasets")
    if not isinstance(selected, list):
        raise NDPStudyError("selection selected_datasets must be a list")
    records = []
    for item in selected:
        if not isinstance(item, dict) or item.get("split") not in requested_splits:
            continue
        dataset_id = str(item.get("dataset_id") or "")
        snapshot = capture_dataset_detail(
            dataset_id=dataset_id, timeout_seconds=timeout_seconds
        )
        output_path = output_dir / f"{dataset_id}.json.gz"
        _write_json(output_path, snapshot)
        normalized = normalize_detail_snapshot(output_path)
        dataset = normalized["dataset"]
        records.append(
            {
                "dataset_id": dataset_id,
                "split": item["split"],
                "snapshot_file": output_path.name,
                "snapshot_sha256": _sha256_file(output_path),
                "resource_count": dataset["resource_count"],
                "supported_resource_count": dataset["supported_resource_count"],
                "format_conflict_resource_count": dataset[
                    "format_conflict_resource_count"
                ],
                "primary_format_class": dataset["primary_format_class"],
                "access_category": dataset["access_category"],
            }
        )
    records.sort(key=lambda item: (item["split"], item["dataset_id"]))
    return {
        "schema_version": "ndp50-detail-capture-manifest/v1",
        "protocol_version": "ndp50-external-validation-protocol/v1",
        "captured_at": _utc_now(),
        "selection": {
            "file": selection_path.name,
            "sha256": _sha256_file(selection_path),
        },
        "captured_splits": sorted(requested_splits),
        "counts": {
            "dataset_count": len(records),
            "resource_count": sum(item["resource_count"] for item in records),
            "supported_resource_count": sum(
                item["supported_resource_count"] for item in records
            ),
            "format_conflict_resource_count": sum(
                item["format_conflict_resource_count"] for item in records
            ),
        },
        "records": records,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture, normalize, frame, and select the NDP-50 study."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    capture = commands.add_parser("capture")
    capture.add_argument("--request-url", required=True)
    capture.add_argument("--page-ordinal", type=int, default=1)
    capture.add_argument("--timeout-seconds", type=float, default=60.0)
    capture.add_argument("--output", type=Path, required=True)

    validate = commands.add_parser("validate-snapshot")
    validate.add_argument("--snapshot", type=Path, required=True)

    capture_index = commands.add_parser("capture-index")
    capture_index.add_argument("--request-url", required=True)
    capture_index.add_argument("--page-ordinal", type=int, required=True)
    capture_index.add_argument("--timeout-seconds", type=float, default=60.0)
    capture_index.add_argument("--output", type=Path, required=True)

    validate_index = commands.add_parser("validate-index")
    validate_index.add_argument("--snapshot", type=Path, required=True)

    frame = commands.add_parser("build-frame")
    frame.add_argument("--snapshot", action="append", type=Path, required=True)
    frame.add_argument("--frame-scope", required=True)
    frame.add_argument("--termination-reason", required=True)
    frame.add_argument("--frozen-at")
    frame.add_argument("--output", type=Path, required=True)

    index_frame = commands.add_parser("build-index-frame")
    index_frame.add_argument(
        "--snapshot", action="append", type=Path, required=True
    )
    index_frame.add_argument("--frame-scope", required=True)
    index_frame.add_argument("--frozen-at")
    index_frame.add_argument("--output", type=Path, required=True)

    select = commands.add_parser("select")
    select.add_argument("--frame", type=Path, required=True)
    select.add_argument("--design", type=Path, required=True)
    select.add_argument("--selected-at")
    select.add_argument("--output", type=Path, required=True)

    details = commands.add_parser("capture-details")
    details.add_argument("--selection", type=Path, required=True)
    details.add_argument("--output-dir", type=Path, required=True)
    details.add_argument(
        "--split",
        action="append",
        choices=("development", "validation", "test"),
        required=True,
    )
    details.add_argument("--timeout-seconds", type=float, default=90.0)
    details.add_argument("--manifest", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "capture":
        payload = capture_catalog_snapshot(
            request_url=args.request_url,
            page_ordinal=args.page_ordinal,
            timeout_seconds=args.timeout_seconds,
        )
        _write_json(args.output, payload)
        print(
            json.dumps(
                _summary(normalize_catalog_snapshot(args.output)),
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "capture-index":
        payload = capture_index_snapshot(
            request_url=args.request_url,
            page_ordinal=args.page_ordinal,
            timeout_seconds=args.timeout_seconds,
        )
        _write_json(args.output, payload)
        normalized = normalize_index_snapshot(args.output)
        print(
            json.dumps(
                {
                    "catalog_total_count": normalized["catalog_total_count"],
                    "returned_dataset_count": normalized["returned_dataset_count"],
                },
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "validate-snapshot":
        payload = normalize_catalog_snapshot(args.snapshot)
        print(json.dumps(_summary(payload), indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "validate-index":
        payload = normalize_index_snapshot(args.snapshot)
        print(
            json.dumps(
                {
                    "catalog_total_count": payload["catalog_total_count"],
                    "returned_dataset_count": payload["returned_dataset_count"],
                },
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "build-frame":
        payload = build_candidate_frame(
            snapshot_paths=args.snapshot,
            frame_scope=args.frame_scope,
            termination_reason=args.termination_reason,
            frozen_at=args.frozen_at,
        )
        _write_json(args.output, payload)
        print(json.dumps(_summary(payload), indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "build-index-frame":
        payload = build_index_frame(
            snapshot_paths=args.snapshot,
            frame_scope=args.frame_scope,
            frozen_at=args.frozen_at,
        )
        _write_json(args.output, payload)
        print(json.dumps(_summary(payload), indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "capture-details":
        payload = capture_selected_details(
            selection_path=args.selection,
            output_dir=args.output_dir,
            splits=args.split,
            timeout_seconds=args.timeout_seconds,
        )
        _write_json(args.manifest, payload)
        print(json.dumps(_summary(payload), indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    payload = build_selection(
        frame_path=args.frame,
        design_path=args.design,
        selected_at=args.selected_at,
    )
    _write_json(args.output, payload)
    print(json.dumps(_summary(payload), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
