from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent
EXTERNAL_ROOT = ROOT / "data" / "external"
CURATED_PATH = EXTERNAL_ROOT / "curated_sources.json"
IMPORT_MANIFEST_PATH = EXTERNAL_ROOT / "import_manifest.json"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def record_dir(source: Dict[str, Any]) -> Path:
    if source["source"] == "dryad":
        return EXTERNAL_ROOT / "dryad" / source["dataset_doi"].replace("/", "_").replace(":", "_")
    return EXTERNAL_ROOT / "zenodo" / f"record_{source['record_id']}"


def find_local_file(directory: Path, expected_name: str) -> Path | None:
    exact = directory / expected_name
    if exact.exists():
        return exact

    target_lower = expected_name.lower()
    expected_plus = expected_name.replace(" ", "+").lower()
    expected_under = expected_name.replace(" ", "_").lower()
    for item in directory.iterdir():
        if not item.is_file():
            continue
        lowered = item.name.lower()
        if lowered == target_lower or lowered == expected_plus or lowered == expected_under:
            return item
    return None


def existing_download_map(import_manifest: Dict[str, Any]) -> Dict[tuple[str, str], Dict[str, Any]]:
    mapping = {}
    for source in import_manifest.get("imports", []):
        source_key = source["record_directory"]
        for download in source.get("downloads", []):
            mapping[(source_key, download["file_name"])] = download
    return mapping


def main() -> None:
    curated = load_json(CURATED_PATH)
    existing = load_json(IMPORT_MANIFEST_PATH) if IMPORT_MANIFEST_PATH.exists() else {"imports": []}
    existing_map = existing_download_map(existing)

    imports: List[Dict[str, Any]] = []
    for source in curated["sources"]:
        directory = record_dir(source)
        record_directory = str(directory.relative_to(EXTERNAL_ROOT)).replace("\\", "/")
        downloads = []
        for file_name in source["files"]:
            prior = existing_map.get((record_directory, file_name), {})
            local_file = find_local_file(directory, file_name) if directory.exists() else None
            if local_file is not None:
                downloads.append(
                    {
                        "file_name": file_name,
                        "destination": str(local_file.relative_to(EXTERNAL_ROOT)).replace("\\", "/"),
                        "download_url": prior.get("download_url"),
                        "bytes_downloaded": local_file.stat().st_size,
                        "expected_size": prior.get("expected_size", local_file.stat().st_size),
                        "mime_type": prior.get("mime_type"),
                        "status": "downloaded",
                    }
                )
            else:
                downloads.append(
                    {
                        "file_name": file_name,
                        "destination": f"{record_directory}/{file_name}",
                        "download_url": prior.get("download_url"),
                        "expected_size": prior.get("expected_size"),
                        "mime_type": prior.get("mime_type"),
                        "status": "download_missing",
                    }
                )

        imports.append(
            {
                "source": source["source"],
                "label": source["label"],
                "landing_url": source["landing_url"],
                "why_selected": source["why_selected"],
                "record_directory": record_directory,
                "downloads": downloads,
            }
        )

    manifest = {
        "batch_id": curated["batch_id"],
        "selection_policy": curated["selection_policy"],
        "imports": imports,
    }
    write_json(IMPORT_MANIFEST_PATH, manifest)


if __name__ == "__main__":
    main()
