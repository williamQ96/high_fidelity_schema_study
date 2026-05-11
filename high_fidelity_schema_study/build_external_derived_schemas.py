from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from .extractors.csv_extractor import extract_csv_schema
from .extractors.hdf5_extractor import extract_hdf5_schema


ROOT = Path(__file__).resolve().parent
EXTERNAL_ROOT = ROOT / "data" / "external"
IMPORT_MANIFEST_PATH = EXTERNAL_ROOT / "import_manifest.json"
EXTERNAL_DERIVED_ROOT = EXTERNAL_ROOT / "derived"
DERIVED_MANIFEST_PATH = EXTERNAL_DERIVED_ROOT / "derived_manifest.json"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sanitize_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")


def classify_format(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return "csv"
    if suffix in {".h5", ".hdf5", ".hdf"}:
        return "hdf5"
    return None


def extract_supported_file(path: Path, file_format: str) -> Dict[str, Any]:
    if file_format == "csv":
        return extract_csv_schema(str(path)).to_dict()
    if file_format == "hdf5":
        return extract_hdf5_schema(str(path)).to_dict()
    raise ValueError(f"Unsupported format: {file_format}")


def main() -> None:
    manifest = load_json(IMPORT_MANIFEST_PATH)
    ensure_dir(EXTERNAL_DERIVED_ROOT)
    results: List[Dict[str, Any]] = []

    for source_entry in manifest["imports"]:
        record_dir = source_entry["record_directory"]
        for download in source_entry["downloads"]:
            source_path = EXTERNAL_ROOT / download["destination"]
            file_format = classify_format(source_path)
            if download["status"] != "downloaded":
                results.append(
                    {
                        "record_directory": record_dir,
                        "file_name": download["file_name"],
                        "status": "skipped_not_downloaded",
                    }
                )
                continue
            if file_format is None:
                results.append(
                    {
                        "record_directory": record_dir,
                        "file_name": download["file_name"],
                        "status": "skipped_unsupported_format",
                    }
                )
                continue

            relative_record_dir = Path(record_dir)
            output_dir = EXTERNAL_DERIVED_ROOT / relative_record_dir
            ensure_dir(output_dir)
            output_name = f"{sanitize_name(source_path.name)}.schema.json"
            output_path = output_dir / output_name

            try:
                extracted = extract_supported_file(source_path, file_format)
                extracted["external_source"] = source_entry["source"]
                extracted["external_label"] = source_entry["label"]
                extracted["external_record_directory"] = record_dir
                extracted["external_source_file"] = download["destination"]
                output_path.write_text(json.dumps(extracted, indent=2) + "\n", encoding="utf-8")

                results.append(
                    {
                        "record_directory": record_dir,
                        "file_name": download["file_name"],
                        "status": "derived_built",
                        "file_format": file_format,
                        "source_file": download["destination"],
                        "derived_schema_file": str(output_path.relative_to(EXTERNAL_ROOT)).replace("\\", "/"),
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "record_directory": record_dir,
                        "file_name": download["file_name"],
                        "status": "extraction_failed",
                        "file_format": file_format,
                        "source_file": download["destination"],
                        "error": str(exc),
                    }
                )

    DERIVED_MANIFEST_PATH.write_text(json.dumps({"files": results}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
