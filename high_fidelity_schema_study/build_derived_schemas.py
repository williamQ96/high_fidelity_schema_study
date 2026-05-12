from __future__ import annotations

import json
from pathlib import Path

from .extractors.csv_extractor import extract_csv_schema
from .extractors.hdf5_extractor import extract_hdf5_schema
from .deterministic_profile import infer_multi_file_relationships


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
MANIFEST_PATH = DATA_ROOT / "pilot_corpus_manifest.json"
DERIVED_ROOT = DATA_ROOT / "derived"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def extract_dataset(source_path: Path, file_format: str) -> dict:
    if file_format == "csv":
        return extract_csv_schema(str(source_path)).to_dict()
    if file_format == "hdf5":
        return extract_hdf5_schema(str(source_path)).to_dict()
    raise ValueError(f"Unsupported file format in manifest: {file_format}")


def main() -> None:
    manifest = load_manifest()
    derived_entries = []
    derived_schemas = []

    for dataset in manifest["datasets"]:
        source_path = DATA_ROOT / dataset["source_file"]
        output_dir = DERIVED_ROOT / dataset["category"]
        ensure_dir(output_dir)

        schema = extract_dataset(source_path, dataset["file_format"])
        schema["study_dataset_id"] = dataset["dataset_id"]
        schema["study_category"] = dataset["category"]
        schema["study_difficulty"] = dataset["difficulty"]
        schema["study_source_file"] = dataset["source_file"]

        output_path = output_dir / f"{dataset['dataset_id']}.schema.json"
        output_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        derived_schemas.append(schema)

        derived_entries.append(
            {
                "dataset_id": dataset["dataset_id"],
                "category": dataset["category"],
                "difficulty": dataset["difficulty"],
                "file_format": dataset["file_format"],
                "source_file": dataset["source_file"],
                "derived_schema_file": str(output_path.relative_to(DATA_ROOT)).replace("\\", "/"),
            }
        )

    relationship_profile = infer_multi_file_relationships(derived_schemas)
    relationship_profile_path = DERIVED_ROOT / "internal_relationship_profile.json"
    relationship_profile_path.write_text(
        json.dumps(relationship_profile, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = {
        "datasets": derived_entries,
        "profile_files": {
            "internal_relationship_profile": str(relationship_profile_path.relative_to(DATA_ROOT)).replace("\\", "/"),
        },
    }
    (DERIVED_ROOT / "derived_manifest.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
