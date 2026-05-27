from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
DOCS_ROOT = ROOT / "docs"
DERIVED_MANIFEST_PATH = DATA_ROOT / "derived" / "derived_manifest.json"
SEMANTIC_ANNOTATION_MANIFEST_PATH = DATA_ROOT / "semantic_annotations" / "manifest.json"
SEMANTIC_MERGED_MANIFEST_PATH = DATA_ROOT / "semantic_merged" / "manifest.json"
RETRIEVAL_ARTIFACT_MANIFEST_PATH = DATA_ROOT / "retrieval" / "external_candidate_pool" / "artifact_manifest.json"
PROVENANCE_MANIFEST_PATH = DATA_ROOT / "derived" / "provenance_manifest.json"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def maybe_load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return load_json(path)


def data_path(relative_path: str) -> Path:
    return DATA_ROOT / relative_path


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def normalize_source(source: str | None) -> str | None:
    if source is None:
        return None
    try:
        source_path = Path(source)
        if source_path.is_absolute():
            return rel(source_path)
    except ValueError:
        return source
    return source


def add_entity(entities: List[Dict[str, Any]], entity_id: str, entity_type: str, **payload: Any) -> None:
    entities.append({"id": entity_id, "type": entity_type, **payload})


def add_activity(activities: List[Dict[str, Any]], activity_id: str, activity_type: str, **payload: Any) -> None:
    activities.append({"id": activity_id, "type": activity_type, **payload})


def add_relation(relations: Dict[str, List[Dict[str, str]]], relation_type: str, **payload: str) -> None:
    relations.setdefault(relation_type, []).append(payload)


def field_entity_id(dataset_id: str, field_path: str) -> str:
    safe_path = field_path.replace("/", "__").replace(" ", "_")
    return f"field:{dataset_id}:{safe_path}"


def build_provenance_manifest() -> Dict[str, Any]:
    derived_manifest = load_json(DERIVED_MANIFEST_PATH)
    semantic_annotation_manifest = maybe_load_json(SEMANTIC_ANNOTATION_MANIFEST_PATH)
    semantic_merged_manifest = maybe_load_json(SEMANTIC_MERGED_MANIFEST_PATH)
    retrieval_artifact_manifest = maybe_load_json(RETRIEVAL_ARTIFACT_MANIFEST_PATH)

    agents = [
        {
            "id": "agent:deterministic_extractors",
            "type": "software",
            "label": "CSV/HDF5/time-series deterministic extractors",
        },
        {
            "id": "agent:semantic_annotation_model",
            "type": "llm",
            "label": semantic_annotation_manifest.get("model", "semantic annotation model"),
            "api_base": semantic_annotation_manifest.get("api_base"),
        },
        {
            "id": "agent:semantic_merge_policy",
            "type": "software",
            "label": "evidence-constrained semantic merge policy",
        },
        {
            "id": "agent:evaluation_scripts",
            "type": "software",
            "label": "field-level evaluation and retrieval scripts",
        },
        {
            "id": "agent:paper_table_builder",
            "type": "software",
            "label": "paper result table builder",
        },
        {
            "id": "agent:gold_review",
            "type": "human_review",
            "label": "internal gold schema second-pass consistency review",
        },
    ]

    entities: List[Dict[str, Any]] = []
    activities: List[Dict[str, Any]] = []
    relations: Dict[str, List[Dict[str, str]]] = {
        "used": [],
        "wasGeneratedBy": [],
        "wasDerivedFrom": [],
        "wasAttributedTo": [],
    }

    field_count = 0
    evidence_count = 0
    for entry in derived_manifest["datasets"]:
        dataset_id = entry["dataset_id"]
        source_id = f"source_file:{entry['source_file']}"
        schema_id = f"derived_schema:{dataset_id}"
        activity_id = f"activity:deterministic_extraction:{dataset_id}"
        schema = load_json(data_path(entry["derived_schema_file"]))

        add_entity(
            entities,
            source_id,
            "source_file",
            path=f"data/{entry['source_file']}",
            file_format=entry["file_format"],
            category=entry["category"],
            difficulty=entry["difficulty"],
        )
        add_entity(
            entities,
            schema_id,
            "derived_schema",
            path=f"data/{entry['derived_schema_file']}",
            dataset_id=dataset_id,
        )
        add_activity(
            activities,
            activity_id,
            "deterministic_extraction",
            dataset_id=dataset_id,
            extraction_method="csv_conservative_profiler" if entry["file_format"] == "csv" else "h5py_structure_traversal",
        )
        add_relation(relations, "used", activity=activity_id, entity=source_id)
        add_relation(relations, "wasGeneratedBy", entity=schema_id, activity=activity_id)
        add_relation(relations, "wasDerivedFrom", generated=schema_id, source=source_id)
        add_relation(relations, "wasAttributedTo", entity=schema_id, agent="agent:deterministic_extractors")

        for field in schema.get("fields", []):
            field_count += 1
            field_id = field_entity_id(dataset_id, field["field_path"])
            add_entity(
                entities,
                field_id,
                "field_schema",
                dataset_id=dataset_id,
                field_path=field["field_path"],
                physical_type=field.get("physical_type"),
                logical_type=field.get("logical_type"),
                semantic_type=field.get("semantic_type"),
                unit=field.get("unit"),
                unit_normalization_status=(field.get("unit_normalization") or {}).get("status"),
            )
            add_relation(relations, "wasGeneratedBy", entity=field_id, activity=activity_id)
            add_relation(relations, "wasDerivedFrom", generated=field_id, source=schema_id)
            add_relation(relations, "wasAttributedTo", entity=field_id, agent="agent:deterministic_extractors")

            for index, evidence in enumerate(field.get("source_evidence", []), start=1):
                evidence_count += 1
                evidence_id = f"evidence:{dataset_id}:{field_id.rsplit(':', 1)[-1]}:{index}"
                add_entity(
                    entities,
                    evidence_id,
                    "evidence_record",
                    dataset_id=dataset_id,
                    field_path=field["field_path"],
                    tier=evidence.get("tier"),
                    evidence_type=evidence.get("evidence_type"),
                    source=normalize_source(evidence.get("source")),
                    detail=evidence.get("detail"),
                    confidence=evidence.get("confidence"),
                )
                add_relation(relations, "wasGeneratedBy", entity=evidence_id, activity=activity_id)
                add_relation(relations, "wasDerivedFrom", generated=evidence_id, source=source_id)
                add_relation(relations, "used", activity=activity_id, entity=evidence_id)

    annotation_results = [
        item
        for item in semantic_annotation_manifest.get("results", [])
        if item.get("status") == "ok" and item.get("result_file")
    ]
    for item in annotation_results:
        task_id = f"semantic_task:{item['task_file']}"
        result_id = f"semantic_annotation:{item['result_file']}"
        activity_id = f"activity:semantic_annotation:{item['result_file']}"
        add_entity(entities, task_id, "semantic_grounding_task", path=f"data/{item['task_file']}", scope=item.get("scope"))
        add_entity(entities, result_id, "semantic_annotation_result", path=f"data/{item['result_file']}", scope=item.get("scope"))
        add_activity(activities, activity_id, "semantic_annotation", scope=item.get("scope"))
        add_relation(relations, "used", activity=activity_id, entity=task_id)
        add_relation(relations, "wasGeneratedBy", entity=result_id, activity=activity_id)
        add_relation(relations, "wasDerivedFrom", generated=result_id, source=task_id)
        add_relation(relations, "wasAttributedTo", entity=result_id, agent="agent:semantic_annotation_model")

    for item in semantic_merged_manifest.get("entries", []):
        task_id = f"semantic_task:{item['task_file']}"
        merged_id = f"semantic_merged:{item['merged_file']}"
        activity_id = f"activity:semantic_merge:{item['merged_file']}"
        add_entity(entities, merged_id, "semantic_merged_schema", path=f"data/{item['merged_file']}", scope=item.get("scope"))
        add_activity(
            activities,
            activity_id,
            "semantic_merge",
            scope=item.get("scope"),
            conflict_count=item.get("conflict_count", 0),
        )
        add_relation(relations, "used", activity=activity_id, entity=task_id)
        add_relation(relations, "wasGeneratedBy", entity=merged_id, activity=activity_id)
        add_relation(relations, "wasDerivedFrom", generated=merged_id, source=task_id)
        add_relation(relations, "wasAttributedTo", entity=merged_id, agent="agent:semantic_merge_policy")

    reports = [
        ("report:internal_baseline", "evaluation_report", DATA_ROOT / "derived" / "internal_baseline_report.json", "activity:evaluate_internal_baseline"),
        ("report:semantic_merge", "evaluation_report", DATA_ROOT / "semantic_merged" / "semantic_merge_report.json", "activity:evaluate_semantic_merge"),
        ("report:retrieval", "evaluation_report", DATA_ROOT / "retrieval" / "external_candidate_pool" / "retrieval_report.json", "activity:evaluate_retrieval"),
        ("report:paper_tables", "paper_table_report", DOCS_ROOT / "paper_result_tables_2026-05-15.json", "activity:build_paper_tables"),
    ]
    for entity_id, entity_type, path, activity_id in reports:
        add_entity(entities, entity_id, entity_type, path=rel(path))
        add_activity(activities, activity_id, entity_type)
        add_relation(relations, "wasGeneratedBy", entity=entity_id, activity=activity_id)
        add_relation(relations, "wasAttributedTo", entity=entity_id, agent="agent:evaluation_scripts" if "paper" not in entity_id else "agent:paper_table_builder")

    for artifact_name, artifact_path in retrieval_artifact_manifest.get("artifact_files", {}).items():
        artifact_id = f"retrieval_artifact:{artifact_name}"
        add_entity(entities, artifact_id, "retrieval_artifact", path=f"data/{artifact_path}", artifact_name=artifact_name)
        add_relation(relations, "used", activity="activity:evaluate_retrieval", entity=artifact_id)

    summary = {
        "dataset_count": len(derived_manifest["datasets"]),
        "field_entity_count": field_count,
        "evidence_entity_count": evidence_count,
        "semantic_annotation_result_count": len(annotation_results),
        "semantic_merge_output_count": len(semantic_merged_manifest.get("entries", [])),
        "entity_count": len(entities),
        "activity_count": len(activities),
        "agent_count": len(agents),
    }

    return {
        "provenance_model": "lightweight_prov_v1",
        "description": "Internal PROV-like export over files, schemas, field claims, evidence, semantic annotations, merges, evaluations, and reports.",
        "generated_from": [
            rel(DERIVED_MANIFEST_PATH),
            rel(SEMANTIC_ANNOTATION_MANIFEST_PATH),
            rel(SEMANTIC_MERGED_MANIFEST_PATH),
            rel(RETRIEVAL_ARTIFACT_MANIFEST_PATH),
        ],
        "summary": summary,
        "agents": agents,
        "entities": entities,
        "activities": activities,
        "relations": relations,
    }


def main() -> None:
    PROVENANCE_MANIFEST_PATH.write_text(
        json.dumps(build_provenance_manifest(), indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
