from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List

import requests
from requests import RequestException


ROOT = Path(__file__).resolve().parent
EXTERNAL_ROOT = ROOT / "data" / "external"
CURATED_PATH = EXTERNAL_ROOT / "curated_sources.json"
IMPORT_MANIFEST_PATH = EXTERNAL_ROOT / "import_manifest.json"
REQUEST_HEADERS = {
    "User-Agent": "llm-schema-study-importer/1.0"
}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def fetch_json(url: str) -> Dict[str, Any]:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=60)
    response.raise_for_status()
    return response.json()


def fetch_text(url: str) -> str:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=60)
    response.raise_for_status()
    return response.text


def sanitize_name(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    return cleaned.strip("_")


def download_file(url: str, destination: Path) -> int:
    ensure_dir(destination.parent)
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=300)
    response.raise_for_status()
    destination.write_bytes(response.content)
    return len(response.content)


def resolve_dryad_source(entry: Dict[str, Any]) -> Dict[str, Any]:
    doi = entry["dataset_doi"]
    dataset_url = f"https://datadryad.org/api/v2/datasets/{urllib.parse.quote('doi:' + doi, safe='')}"
    dataset = fetch_json(dataset_url)
    version = fetch_json("https://datadryad.org" + dataset["_links"]["stash:version"]["href"])
    files = fetch_json("https://datadryad.org" + version["_links"]["stash:files"]["href"])
    file_lookup = {
        item["path"]: {
            "download_url": "https://datadryad.org/downloads/file_stream/"
            + item["_links"]["self"]["href"].rstrip("/").split("/")[-1],
            "size": item["size"],
            "mime_type": item["mimeType"],
        }
        for item in files.get("_embedded", {}).get("stash:files", [])
    }
    return {
        "record_metadata": version,
        "file_lookup": file_lookup,
    }


def resolve_zenodo_source(entry: Dict[str, Any]) -> Dict[str, Any]:
    record = fetch_json(f"https://zenodo.org/api/records/{entry['record_id']}")
    file_lookup = {}
    for item in record.get("files", []):
        links = item.get("links", {})
        download_url = links.get("self") or links.get("download") or links.get("content")
        file_lookup[item["key"]] = {
            "download_url": download_url,
            "size": item.get("size"),
            "mime_type": item.get("type"),
        }
    return {
        "record_metadata": record,
        "file_lookup": file_lookup,
    }


def import_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    source = entry["source"]
    if source == "dryad":
        resolved = resolve_dryad_source(entry)
        record_key = sanitize_name(entry["dataset_doi"])
    elif source == "zenodo":
        resolved = resolve_zenodo_source(entry)
        record_key = f"record_{entry['record_id']}"
    else:
        raise ValueError(f"Unsupported source: {source}")

    output_dir = EXTERNAL_ROOT / source / record_key
    ensure_dir(output_dir)

    metadata_path = output_dir / "source_record.json"
    metadata_path.write_text(json.dumps(resolved["record_metadata"], indent=2) + "\n", encoding="utf-8")
    landing_page_path = output_dir / "landing_page.html"
    landing_page_path.write_text(fetch_text(entry["landing_url"]), encoding="utf-8")

    downloads: List[Dict[str, Any]] = []
    for file_name in entry["files"]:
        if file_name not in resolved["file_lookup"]:
            raise KeyError(f"Selected file not found in source record: {file_name}")
        file_info = resolved["file_lookup"][file_name]
        destination = output_dir / file_name
        try:
            byte_count = download_file(file_info["download_url"], destination)
            downloads.append(
                {
                    "file_name": file_name,
                    "destination": str(destination.relative_to(EXTERNAL_ROOT)).replace("\\", "/"),
                    "download_url": file_info["download_url"],
                    "bytes_downloaded": byte_count,
                    "expected_size": file_info["size"],
                    "mime_type": file_info["mime_type"],
                    "status": "downloaded",
                }
            )
        except RequestException as exc:
            downloads.append(
                {
                    "file_name": file_name,
                    "destination": str(destination.relative_to(EXTERNAL_ROOT)).replace("\\", "/"),
                    "download_url": file_info["download_url"],
                    "expected_size": file_info["size"],
                    "mime_type": file_info["mime_type"],
                    "status": "download_failed",
                    "error": str(exc),
                }
            )

    return {
        "source": source,
        "label": entry["label"],
        "landing_url": entry["landing_url"],
        "why_selected": entry["why_selected"],
        "record_directory": str(output_dir.relative_to(EXTERNAL_ROOT)).replace("\\", "/"),
        "downloads": downloads,
    }


def main() -> None:
    curated = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
    results = []
    for entry in curated["sources"]:
        results.append(import_entry(entry))

    IMPORT_MANIFEST_PATH.write_text(
        json.dumps(
            {
                "batch_id": curated["batch_id"],
                "selection_policy": curated["selection_policy"],
                "imports": results,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
