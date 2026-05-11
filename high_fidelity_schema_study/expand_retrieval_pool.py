from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import requests

from .extractors.csv_extractor import extract_csv_schema
from .extractors.hdf5_extractor import extract_hdf5_schema


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
EXTERNAL_ROOT = DATA_ROOT / "external"
BENCHMARK_CANDIDATES_PATH = EXTERNAL_ROOT / "benchmark_candidates.json"
POOL_EXPANSION_PATH = DATA_ROOT / "retrieval" / "external_candidate_pool" / "pool_expansion_sources.json"
POOL_MANIFEST_PATH = DATA_ROOT / "retrieval" / "external_candidate_pool" / "pool_manifest.json"
EXTERNAL_DERIVED_ROOT = EXTERNAL_ROOT / "derived"
REQUEST_HEADERS = {"User-Agent": "llm-schema-retrieval-pool/1.0"}


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def classify_format(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return "csv"
    if suffix in {".h5", ".hdf5", ".hdf"}:
        return "hdf5"
    return None


def derive_schema(source_file: str) -> str:
    source_path = EXTERNAL_ROOT / source_file
    record_dir = Path(source_file).parent
    output_dir = EXTERNAL_DERIVED_ROOT / record_dir
    ensure_dir(output_dir)
    output_path = output_dir / f"{source_path.name.replace(' ', '_')}.schema.json"

    file_format = classify_format(source_path)
    if file_format == "csv":
        schema = extract_csv_schema(str(source_path)).to_dict()
    elif file_format == "hdf5":
        schema = extract_hdf5_schema(str(source_path)).to_dict()
    else:
        raise ValueError(f"Unsupported retrieval-pool format: {source_path}")

    schema["external_source_file"] = source_file
    write_json(output_path, schema)
    return str(output_path.relative_to(DATA_ROOT)).replace("\\", "/")


def download_if_missing(source_file: str) -> None:
    source_path = EXTERNAL_ROOT / source_file
    if source_path.exists():
        return

    parts = Path(source_file).parts
    record_dir = EXTERNAL_ROOT / parts[0] / parts[1]
    source_record = load_json(record_dir / "source_record.json")
    file_lookup = {item["key"]: item["links"]["self"] for item in source_record.get("files", [])}
    file_name = parts[2]
    if file_name not in file_lookup:
        raise KeyError(f"File not present in source record: {source_file}")

    response = requests.get(file_lookup[file_name], headers=REQUEST_HEADERS, timeout=300)
    response.raise_for_status()
    ensure_dir(source_path.parent)
    source_path.write_bytes(response.content)


def build_pool_manifest() -> Dict[str, Any]:
    benchmark_candidates = load_json(BENCHMARK_CANDIDATES_PATH)
    expansion = load_json(POOL_EXPANSION_PATH)

    entries: List[Dict[str, Any]] = []
    for candidate in benchmark_candidates["candidates"]:
        if candidate["status"] in {"promoted", "distractor"}:
            derived_schema_file = derive_schema(candidate["source_file"])
            entries.append(
                {
                    "source_file": candidate["source_file"],
                    "role": "target" if candidate["status"] == "promoted" else "distractor",
                    "reason": candidate["reason"],
                    "derived_schema_file": derived_schema_file,
                }
            )

    for item in expansion["downloads"]:
        download_if_missing(item["source_file"])
        derived_schema_file = derive_schema(item["source_file"])
        entries.append(
            {
                "source_file": item["source_file"],
                "role": item["role"],
                "reason": item["reason"],
                "derived_schema_file": derived_schema_file,
            }
        )

    return {
        "entry_count": len(entries),
        "entries": entries,
    }


def main() -> None:
    manifest = build_pool_manifest()
    write_json(POOL_MANIFEST_PATH, manifest)


if __name__ == "__main__":
    main()
