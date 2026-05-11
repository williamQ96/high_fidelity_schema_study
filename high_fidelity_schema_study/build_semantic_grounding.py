from __future__ import annotations

import json
import re
import hashlib
from html import unescape
from pathlib import Path
from typing import Any, Dict, List

from .semantic_layer import GroundingSnippet, SemanticAnnotationTask, write_prompt_payload


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
INTERNAL_DERIVED_ROOT = DATA_ROOT / "derived"
INTERNAL_GROUNDING_ROOT = DATA_ROOT / "semantic_grounding" / "internal"
EXTERNAL_ROOT = DATA_ROOT / "external"
EXTERNAL_DERIVED_MANIFEST_PATH = EXTERNAL_ROOT / "derived" / "derived_manifest.json"
EXTERNAL_GROUNDING_ROOT = DATA_ROOT / "semantic_grounding" / "external"
PILOT_MANIFEST_PATH = DATA_ROOT / "pilot_corpus_manifest.json"
RETRIEVAL_POOL_MANIFEST_PATH = DATA_ROOT / "retrieval" / "external_candidate_pool" / "pool_manifest.json"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def strip_html(text: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(no_tags)).strip()


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def short_task_filename(prefix: str, source_file: str) -> str:
    stem = Path(source_file).stem
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_")
    digest = hashlib.sha1(source_file.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{safe_stem[:60]}_{digest}.task.json"


def grounding_from_internal_readme(dataset_entry: Dict[str, Any]) -> List[GroundingSnippet]:
    source_path = DATA_ROOT / dataset_entry["source_file"]
    readme_path = source_path.parent / "README.md"
    text = read_text_if_exists(readme_path)
    if not text:
        return []
    return [
        GroundingSnippet(
            source_type="dataset_readme",
            source_name=str(readme_path.relative_to(DATA_ROOT)).replace("\\", "/"),
            detail="local pilot dataset README",
            text=text,
            priority=1,
        )
    ]


def grounding_from_external_record(source_file: str) -> List[GroundingSnippet]:
    parts = Path(source_file).parts
    record_dir = EXTERNAL_ROOT / parts[0] / parts[1]
    source_record = load_json(record_dir / "source_record.json")
    metadata = source_record.get("metadata", {})

    snippets = [
        GroundingSnippet(
            source_type="record_title",
            source_name=str((record_dir / "source_record.json").relative_to(DATA_ROOT)).replace("\\", "/"),
            detail="record title",
            text=metadata.get("title") or source_record.get("title", ""),
            priority=1,
        ),
        GroundingSnippet(
            source_type="record_description",
            source_name=str((record_dir / "source_record.json").relative_to(DATA_ROOT)).replace("\\", "/"),
            detail="record description",
            text=strip_html(metadata.get("description", "")),
            priority=1,
        ),
    ]
    notes = metadata.get("notes", "")
    if notes:
        snippets.append(
            GroundingSnippet(
                source_type="record_notes",
                source_name=str((record_dir / "source_record.json").relative_to(DATA_ROOT)).replace("\\", "/"),
                detail="record notes",
                text=notes,
                priority=2,
            )
        )
    keywords = metadata.get("keywords", [])
    if keywords:
        snippets.append(
            GroundingSnippet(
                source_type="record_keywords",
                source_name=str((record_dir / "source_record.json").relative_to(DATA_ROOT)).replace("\\", "/"),
                detail="record keywords",
                text="; ".join(keywords),
                priority=2,
            )
        )
    return [snippet for snippet in snippets if snippet.text]


def build_internal_tasks() -> List[Dict[str, Any]]:
    pilot_manifest = load_json(PILOT_MANIFEST_PATH)
    outputs = []
    for dataset_entry in pilot_manifest["datasets"]:
        derived_path = INTERNAL_DERIVED_ROOT / dataset_entry["category"] / f"{dataset_entry['dataset_id']}.schema.json"
        derived_schema = load_json(derived_path)
        task = SemanticAnnotationTask(
            task_id=f"internal::{dataset_entry['dataset_id']}",
            dataset_id=dataset_entry["dataset_id"],
            file_format=derived_schema["file_format"],
            data_modality=derived_schema["data_modality"],
            deterministic_schema=derived_schema,
            grounding_snippets=grounding_from_internal_readme(dataset_entry),
            instructions=[
                "Use only the deterministic schema and grounding snippets.",
                "If a field already has explicit unit metadata, do not replace it with weaker inference.",
            ],
        )
        output_path = INTERNAL_GROUNDING_ROOT / f"{dataset_entry['dataset_id']}.task.json"
        ensure_dir(output_path.parent)
        write_prompt_payload(output_path, task)
        outputs.append(
            {
                "task_id": task.task_id,
                "dataset_id": dataset_entry["dataset_id"],
                "task_file": str(output_path.relative_to(DATA_ROOT)).replace("\\", "/"),
            }
        )
    return outputs


def build_external_tasks() -> List[Dict[str, Any]]:
    pool_manifest = load_json(RETRIEVAL_POOL_MANIFEST_PATH)
    outputs = []
    for entry in pool_manifest["entries"]:
        derived_schema = load_json(DATA_ROOT / entry["derived_schema_file"])
        task = SemanticAnnotationTask(
            task_id=f"external::{entry['source_file'].replace('/', '::')}",
            dataset_id=Path(entry["source_file"]).name,
            file_format=derived_schema["file_format"],
            data_modality=derived_schema["data_modality"],
            deterministic_schema=derived_schema,
            grounding_snippets=grounding_from_external_record(entry["source_file"]),
            instructions=[
                "Treat source-record descriptions and notes as weaker than explicit field metadata.",
                "If multiple files come from the same record family, annotate only the current file and do not copy assumptions across siblings without direct evidence.",
            ],
        )
        out_name = short_task_filename("external", entry["source_file"])
        output_path = EXTERNAL_GROUNDING_ROOT / out_name
        ensure_dir(output_path.parent)
        write_prompt_payload(output_path, task)
        outputs.append(
            {
                "task_id": task.task_id,
                "source_file": entry["source_file"],
                "role": entry["role"],
                "task_file": str(output_path.relative_to(DATA_ROOT)).replace("\\", "/"),
            }
        )
    return outputs


def main() -> None:
    internal_outputs = build_internal_tasks()
    external_outputs = build_external_tasks()
    manifest = {
        "internal_task_count": len(internal_outputs),
        "external_task_count": len(external_outputs),
        "internal_tasks": internal_outputs,
        "external_tasks": external_outputs,
    }
    ensure_dir((DATA_ROOT / "semantic_grounding").parent)
    (DATA_ROOT / "semantic_grounding" / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
