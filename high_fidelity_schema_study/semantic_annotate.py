from __future__ import annotations

import argparse
import json
import os
import urllib.request
from urllib.error import HTTPError
from pathlib import Path
from typing import Any, Dict, List

from .semantic_layer import normalize_annotation_result, validate_annotation_result


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
GROUNDING_MANIFEST_PATH = DATA_ROOT / "semantic_grounding" / "manifest.json"
ANNOTATION_ROOT = DATA_ROOT / "semantic_annotations"

GROUP_STRATEGIES: Dict[str, List[List[str]]] = {
    "Season and site fidelity determine home range": [
        ["Hourbin"],
        ["COA_Lat", "COA_Lon"],
        ["POINT_X", "POINT_Y"],
        ["Month", "Year"],
        ["Tag", "Transplant", "Cove"],
    ],
    "functional_traits.csv": [
        ["Species", "Mass.g"],
        ["Vertebrate", "Mammal", "Bird", "Herptile"],
        ["Fish", "Invertebrate", "Seed", "Fruit"],
        ["Nectar", "Root", "Woody", "Herbaceous", "Other"],
    ],
}

SEMANTIC_LOGICAL_HINTS: Dict[str, str] = {
    "postal_zone_code": "identifier",
    "record_identifier": "identifier",
    "device_identifier": "identifier",
    "station_identifier": "identifier",
    "sensor_identifier": "identifier",
    "buoy_identifier": "identifier",
    "observation_time": "attribute",
    "collection_date": "attribute",
    "forecast_hour": "attribute",
    "latitude": "coordinate",
    "longitude": "coordinate",
    "depth": "coordinate",
    "elevation": "measurement",
    "air_temperature": "measurement",
    "water_temperature": "measurement",
    "relative_humidity": "measurement",
    "surface_pressure": "measurement",
    "wind_speed": "measurement",
    "power": "measurement",
    "voltage": "measurement",
    "acidity_ph": "measurement",
    "dissolved_oxygen": "measurement",
    "turbidity": "measurement",
    "salinity": "measurement",
    "quality_flag": "label",
    "operational_status": "label",
}


def load_json(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        depth = 0
        in_string = False
        escape = False
        for index, char in enumerate(text[start:], start=start):
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start : index + 1])
        raise


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def response_json_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "task_id": {"type": "string"},
            "annotations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "field_path": {"type": "string"},
                        "semantic_type": {"type": "string"},
                        "logical_type": {"type": ["string", "null"]},
                        "unit": {"type": ["string", "null"]},
                        "description": {"type": ["string", "null"]},
                        "supporting_evidence": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number"},
                        "uncertainty_reason": {"type": ["string", "null"]},
                    },
                    "required": [
                        "field_path",
                        "semantic_type",
                        "logical_type",
                        "unit",
                        "description",
                        "supporting_evidence",
                        "confidence",
                        "uncertainty_reason",
                    ],
                },
            },
            "conflicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": True,
                    "properties": {
                        "field_path": {"type": "string"},
                        "conflict_type": {"type": "string"},
                        "detail": {"type": "string"},
                    },
                    "required": ["field_path", "conflict_type", "detail"],
                },
            },
            "notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["task_id", "annotations", "conflicts", "notes"],
    }


def compact_task_payload(task_payload: Dict[str, Any], target_field_paths: List[str] | None = None) -> Dict[str, Any]:
    task = task_payload["task"]
    snippets = task.get("grounding_snippets", [])
    target_fields = []
    context_fields = []
    target_filter = set(target_field_paths) if target_field_paths else None
    for field in task["deterministic_schema"].get("fields", []):
        available_evidence = []
        for index, evidence in enumerate(field.get("source_evidence", [])[:2], start=1):
            available_evidence.append(
                {
                    "id": f"F{index}",
                    "text": f"{evidence.get('evidence_type')}: {str(evidence.get('detail', ''))[:120]}",
                }
            )
        snippet_id = 1
        for snippet in snippets:
            lowered = snippet.get("text", "").lower()
            field_token = field["field_name"].lower()
            path_token = field["field_path"].lower()
            if field_token in lowered or path_token in lowered:
                available_evidence.append(
                    {
                        "id": f"S{snippet_id}",
                        "text": snippet.get("text", "")[:180],
                    }
                )
                snippet_id += 1

        target_reasons = []
        if field.get("logical_type") in {None, "", "unknown"}:
            target_reasons.append("logical_type is unresolved")
        if field.get("semantic_type") in {None, "", "unknown"}:
            target_reasons.append("semantic_type is unresolved")
        if target_reasons and field.get("uncertainty_reason"):
            target_reasons.append(field["uncertainty_reason"])
        if target_reasons and field.get("confidence") is not None and float(field.get("confidence", 1.0)) < 0.95:
            target_reasons.append("deterministic confidence is below 0.95")
        if target_filter is not None and field["field_path"] in target_filter and not target_reasons:
            target_reasons.append("explicitly selected for semantic review")

        semantic_hint = SEMANTIC_LOGICAL_HINTS.get(str(field.get("semantic_type")))

        compact_field = {
            "field_path": field["field_path"],
            "field_name": field["field_name"],
            "physical_type": field["physical_type"],
            "logical_type": field.get("logical_type"),
            "semantic_type": field.get("semantic_type"),
            "semantic_logical_hint": semantic_hint,
            "unit": field.get("unit"),
            "shape": field.get("shape"),
            "description": field.get("description"),
            "example_values": field.get("example_values", [])[:2],
            "value_range": field.get("value_range"),
            "confidence": field.get("confidence"),
            "uncertainty_reason": field.get("uncertainty_reason"),
            "annotation_goal": target_reasons,
            "evidence": [
                {
                    "evidence_type": evidence.get("evidence_type"),
                    "detail": str(evidence.get("detail", ""))[:160],
                }
                for evidence in field.get("source_evidence", [])[:2]
            ],
            "available_evidence": available_evidence,
        }
        if target_reasons:
            if target_filter is not None and field["field_path"] not in target_filter:
                continue
            target_fields.append(compact_field)
        else:
            context_fields.append(
                {
                    "field_path": field["field_path"],
                    "logical_type": field.get("logical_type"),
                    "semantic_type": field.get("semantic_type"),
                    "unit": field.get("unit"),
                }
            )

    compact_snippets = []
    for snippet in snippets:
        compact_snippets.append(
            {
                "source_type": snippet["source_type"],
                "detail": snippet["detail"],
                "priority": snippet["priority"],
                "text": snippet["text"][:700],
            }
        )

    return {
        "task": {
            "task_id": task["task_id"],
            "dataset_id": task["dataset_id"],
            "file_format": task["file_format"],
            "data_modality": task["data_modality"],
            "allowed_logical_types": [
                "identifier",
                "time_axis",
                "measurement",
                "coordinate",
                "label",
                "attribute",
                "relationship",
                "unknown",
            ],
            "annotation_targets": target_fields,
            "context_fields": context_fields[:8],
            "grounding_snippets": compact_snippets,
            "instructions": task.get("instructions", []),
        }
    }


def extract_json_object(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(stripped[start : end + 1])


def looks_like_annotation_result(payload: Dict[str, Any]) -> bool:
    required = {"task_id", "annotations", "conflicts", "notes"}
    return required.issubset(payload.keys())


def send_request(task_payload: Dict[str, Any], api_base: str, model: str, api_key: str) -> Dict[str, Any]:
    last_error: Exception | None = None
    for use_json_schema in (False, True):
        try:
            result = _send_request(task_payload, api_base, model, api_key, use_json_schema)
            if looks_like_annotation_result(result):
                return result
            raise RuntimeError("model returned JSON but not the required annotation-result shape")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise RuntimeError(f"semantic annotation request failed: {last_error}")


def _send_request(task_payload: Dict[str, Any], api_base: str, model: str, api_key: str, use_json_schema: bool) -> Dict[str, Any]:
    compact_payload = task_payload
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 1000,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an evidence-constrained semantic schema annotator. "
                    "Return strict JSON only. "
                    "Do not include markdown, reasoning trace, or commentary outside the JSON object. "
                    "Use the provided task_id exactly. "
                    "Only use logical_type values from the allowed_logical_types list. "
                    "The top-level JSON object must contain exactly these keys: "
                    "task_id, annotations, conflicts, notes. "
                    "Do not echo the input task object. "
                    "Only annotate fields listed in annotation_targets. "
                    "For any non-unknown semantic_type, logical_type override, or unit claim, include at least one supporting_evidence item. "
                    "Each supporting_evidence item must be an evidence id from the field's available_evidence list, such as F1 or S1. "
                    "Treat logical_type and semantic_type as separate decisions: if evidence supports a logical role such as measurement, identifier, coordinate, label, or attribute but does not support a precise semantic_type, set logical_type and keep semantic_type as unknown. "
                    "Use semantic_logical_hint when it is present and evidence does not contradict it; for example a postal zone code is an identifier, not a label. "
                    "Field descriptions like 'numeric observations with non-detect markers' support logical_type measurement even when the physical_type must remain string and semantic_type remains unknown. "
                    "If evidence is insufficient, keep semantic_type as unknown and explain uncertainty_reason."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Produce a semantic annotation result for this task.\n"
                    "Bad output example: {\"task\": {...}}\n"
                    "Good output example: "
                    "{\"task_id\":\"...\",\"annotations\":[{\"field_path\":\"...\",\"semantic_type\":\"unknown\",\"logical_type\":null,\"unit\":null,\"description\":null,\"supporting_evidence\":[],\"confidence\":0.0,\"uncertainty_reason\":\"...\"}],\"conflicts\":[...],\"notes\":[...]}\n\n"
                    + json.dumps(compact_payload, indent=2)
                ),
            },
        ],
    }
    if use_json_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "semantic_annotation_result",
                "schema": response_json_schema(),
            },
        }
    request = urllib.request.Request(
        url=f"{api_base.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"http {exc.code}: {body}") from exc
    parsed = json.loads(raw)
    message = parsed["choices"][0]["message"]
    content = message.get("content") or message.get("reasoning_content") or ""
    return extract_json_object(content)


def task_entries(scope: str, limit: int | None) -> List[Dict[str, Any]]:
    manifest = load_json(GROUNDING_MANIFEST_PATH)
    entries: List[Dict[str, Any]] = []
    if scope in {"internal", "all"}:
        entries.extend({"scope": "internal", **item} for item in manifest["internal_tasks"])
    if scope in {"external", "all"}:
        entries.extend({"scope": "external", **item} for item in manifest["external_tasks"])
    if limit is not None:
        return entries[:limit]
    return entries


def filter_entries(entries: List[Dict[str, Any]], task_id_pattern: str | None) -> List[Dict[str, Any]]:
    if not task_id_pattern:
        return entries
    return [entry for entry in entries if task_id_pattern in entry["task_id"]]


def grouped_field_sets(task_id: str, target_fields: List[Dict[str, Any]]) -> List[List[str]]:
    for key, groups in GROUP_STRATEGIES.items():
        if key in task_id:
            valid_paths = {field["field_path"] for field in target_fields}
            selected = []
            for group in groups:
                filtered = [field_path for field_path in group if field_path in valid_paths]
                if filtered:
                    selected.append(filtered)
            remaining = [field["field_path"] for field in target_fields if all(field["field_path"] not in group for group in selected)]
            for field_path in remaining:
                selected.append([field_path])
            return selected
    return [[field["field_path"]] for field in target_fields]


def aggregate_field_results(task_id: str, raw_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    annotations_by_path: Dict[str, Dict[str, Any]] = {}
    conflicts = []
    notes = []
    for result in raw_results:
        for annotation in result.get("annotations", []):
            field_path = annotation.get("field_path")
            if field_path:
                annotations_by_path[field_path] = annotation
        conflicts.extend(result.get("conflicts", []))
        notes.extend(result.get("notes", []))
    return {
        "task_id": task_id,
        "annotations": list(annotations_by_path.values()),
        "conflicts": conflicts,
        "notes": notes,
    }


def write_result(scope: str, task_file_relative: str, payload: Dict[str, Any]) -> Path:
    task_path = DATA_ROOT / task_file_relative
    output_name = task_path.name.replace(".task.json", ".result.json")
    output_dir = ANNOTATION_ROOT / scope
    ensure_dir(output_dir)
    output_path = output_dir / output_name
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run LLM-assisted semantic annotation over grounding task bundles.")
    parser.add_argument("--scope", choices=["internal", "external", "all"], default="all")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--api-base", default=os.getenv("LLM_SCHEMA_API_BASE", "http://127.0.0.1:1234/v1"))
    parser.add_argument("--model", default=os.getenv("LLM_SCHEMA_MODEL", "qwen/qwen3.5-9b"))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY", "lm-studio"))
    parser.add_argument("--task-id-pattern")
    parser.add_argument("--per-field", action="store_true", default=True)
    parser.add_argument("--field-offset", type=int, default=0)
    parser.add_argument("--field-limit", type=int)
    parser.add_argument("--target-field", action="append", default=[])
    parser.add_argument("--use-groups", action="store_true", default=True)
    parser.add_argument("--group-index", type=int)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if (ANNOTATION_ROOT / "manifest.json").exists():
        run_manifest = load_json(ANNOTATION_ROOT / "manifest.json")
        run_manifest["api_base"] = args.api_base
        run_manifest["model"] = args.model
    else:
        run_manifest = {
            "api_base": args.api_base,
            "model": args.model,
            "results": [],
        }

    entries = filter_entries(task_entries(args.scope, args.limit), args.task_id_pattern)
    for entry in entries:
        task_payload = load_json(DATA_ROOT / entry["task_file"])
        manifest_entry = {
            "task_file": entry["task_file"],
            "scope": entry["scope"],
        }
        try:
            explicit_target_fields = args.target_field or None
            compact_payload = compact_task_payload(task_payload, explicit_target_fields)
            target_fields = compact_payload["task"]["annotation_targets"]
            grouped_paths = None
            if args.use_groups and target_fields:
                grouped_paths = grouped_field_sets(entry["task_id"], target_fields)
                if args.group_index is not None:
                    if 0 <= args.group_index < len(grouped_paths):
                        grouped_paths = [grouped_paths[args.group_index]]
                    else:
                        grouped_paths = []
            if args.field_offset or args.field_limit is not None:
                start = max(args.field_offset, 0)
                end = None if args.field_limit is None else start + max(args.field_limit, 0)
                target_fields = target_fields[start:end]
                grouped_paths = [[field["field_path"]] for field in target_fields]

            if explicit_target_fields:
                grouped_paths = [[field["field_path"]] for field in target_fields]

            if args.per_field and target_fields:
                raw_results = []
                path_groups = grouped_paths or [[field["field_path"]] for field in target_fields]
                for path_group in path_groups:
                    field_payload = compact_task_payload(task_payload, path_group)
                    raw_results.append(send_request(field_payload, args.api_base, args.model, args.api_key))
                raw_result = aggregate_field_results(task_payload["task"]["task_id"], raw_results)
            else:
                raw_result = send_request(compact_payload, args.api_base, args.model, args.api_key)

            output_path = ANNOTATION_ROOT / entry["scope"] / Path(entry["task_file"]).name.replace(".task.json", ".result.json")
            existing_output = load_json(output_path) if output_path.exists() else None
            if existing_output is not None:
                combined_raw = aggregate_field_results(
                    task_payload["task"]["task_id"],
                    [existing_output["raw_result"], raw_result],
                )
            else:
                combined_raw = raw_result

            result = normalize_annotation_result(combined_raw, task_payload)
            validation_errors = validate_annotation_result(result, task_payload)
            output = {
                "task_file": entry["task_file"],
                "model_info": {
                    "api_base": args.api_base,
                    "model": args.model,
                },
                "raw_result": combined_raw,
                "validation_errors": validation_errors,
                "result": result,
            }
            output_path = write_result(entry["scope"], entry["task_file"], output)
            manifest_entry["result_file"] = str(output_path.relative_to(DATA_ROOT)).replace("\\", "/")
            manifest_entry["validation_error_count"] = len(validation_errors)
            manifest_entry["status"] = "ok"
        except Exception as exc:  # noqa: BLE001
            manifest_entry["status"] = "failed"
            manifest_entry["error"] = str(exc)

        run_manifest["results"] = [item for item in run_manifest["results"] if item["task_file"] != entry["task_file"]]
        run_manifest["results"].append(manifest_entry)

    atomic_write_json(ANNOTATION_ROOT / "manifest.json", run_manifest)


if __name__ == "__main__":
    main()
