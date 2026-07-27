from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from .architecture_variants import load_json


ROOT = Path(__file__).resolve().parent
REMOVED_PREDICTION_FIELDS = (
    "logical_type",
    "semantic_type",
    "unit",
    "confidence",
    "uncertainty_reason",
    "semantic_logical_hint",
    "description",
)
NEUTRAL_FIELD_KEYS = (
    "field_name",
    "field_path",
    "physical_type",
    "shape",
    "nullable",
    "missing_count",
    "unique_ratio",
    "example_values",
    "value_range",
    "extraction_method",
)
RAW_OBSERVATION_EVIDENCE_TYPES = frozenset(
    {
        "csv_header",
        "sample_rows",
        "hdf5_dataset_path",
        "hdf5_attribute",
    }
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(manifest_path: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    adjacent = (manifest_path.parent / candidate).resolve()
    if adjacent.exists():
        return adjacent
    return (ROOT / candidate).resolve()


def _source_label(value: Any) -> str:
    text = str(value or "")
    normalized = text.replace("\\", "/")
    if ":/" in normalized or normalized.startswith("/"):
        return normalized.rsplit("/", 1)[-1]
    return text


def _neutral_evidence(
    field_path: str,
    source_evidence: Any,
    *,
    allowed_evidence_types: frozenset[str] = RAW_OBSERVATION_EVIDENCE_TYPES,
) -> List[Dict[str, Any]]:
    if not isinstance(source_evidence, list):
        return []
    result: List[Dict[str, Any]] = []
    for index, item in enumerate(source_evidence, start=1):
        if not isinstance(item, dict):
            continue
        evidence_type = item.get("evidence_type")
        if evidence_type not in allowed_evidence_types:
            continue
        result.append(
            {
                "evidence_id": f"{field_path}::F{index}",
                "tier": item.get("tier"),
                "evidence_type": evidence_type,
                "source_label": _source_label(item.get("source")),
                "detail": item.get("detail"),
            }
        )
    return result


def build_neutral_annotation_packet(
    task_payload: Dict[str, Any],
    *,
    case_id: str,
    source_task_sha256: str,
    purpose: str = "annotator_calibration",
    research_evidence_status: str = "non_blind_not_for_effect_estimation",
    allowed_evidence_types: frozenset[str] = RAW_OBSERVATION_EVIDENCE_TYPES,
) -> Dict[str, Any]:
    task = task_payload["task"]
    fields: List[Dict[str, Any]] = []
    for raw_field in task["deterministic_schema"].get("fields", []):
        field = {
            key: raw_field.get(key) for key in NEUTRAL_FIELD_KEYS if key in raw_field
        }
        field_path = str(raw_field["field_path"])
        field["source_evidence"] = _neutral_evidence(
            field_path,
            raw_field.get("source_evidence", []),
            allowed_evidence_types=allowed_evidence_types,
        )
        fields.append(field)

    snippets: List[Dict[str, Any]] = []
    for index, raw_snippet in enumerate(task.get("grounding_snippets", []), start=1):
        snippet = {
            "evidence_id": f"S{index}",
            "source_type": raw_snippet.get("source_type"),
            "source_name": raw_snippet.get("source_name"),
            "detail": raw_snippet.get("detail"),
            "text": raw_snippet.get("text"),
        }
        applicable = raw_snippet.get("applicable_field_paths")
        if isinstance(applicable, list):
            snippet["applicable_field_paths"] = list(applicable)
        snippets.append(snippet)

    return {
        "schema_version": "semantic-annotation-packet/v1",
        "purpose": purpose,
        "research_evidence_status": research_evidence_status,
        "case_id": case_id,
        "task_id": task["task_id"],
        "dataset_id": task["dataset_id"],
        "file_format": task["file_format"],
        "data_modality": task["data_modality"],
        "source_task_sha256": source_task_sha256,
        "annotation_properties": [
            "physical_type",
            "logical_type",
            "semantic_type",
            "unit",
        ],
        "prediction_fields_removed": list(REMOVED_PREDICTION_FIELDS),
        "evidence_policy": {
            "mode": "allowlisted_raw_observations_only",
            "allowed_evidence_types": sorted(allowed_evidence_types),
            "derived_semantic_hints_removed": True,
        },
        "field_inventory": fields,
        "approved_evidence": snippets,
        "annotator_instructions": [
            "Annotate independently using the frozen handbook.",
            "Do not inspect existing gold, semantic model output, or another annotator artifact before submission.",
            "Assign applicability before assigning each value.",
            "Cite exact packet evidence or independently frozen raw-source evidence for every known value.",
        ],
    }


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def build_calibration_pack(manifest_path: Path, output_dir: Path) -> Dict[str, Any]:
    manifest = load_json(manifest_path)
    if manifest.get("benchmark_role") not in {
        "synthetic_development",
        "calibration",
    }:
        raise ValueError(
            "calibration source must be development/calibration, never blind"
        )
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("calibration manifest contains no cases")

    packets_dir = output_dir / "packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    entries: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in cases:
        case_id = str(item["case_id"])
        if case_id in seen:
            raise ValueError(f"duplicate calibration case_id: {case_id}")
        seen.add(case_id)
        raw_task_file = str(item["task_file"])
        task_path = _resolve(manifest_path, raw_task_file)
        task_sha256 = sha256_file(task_path)
        packet = build_neutral_annotation_packet(
            load_json(task_path),
            case_id=case_id,
            source_task_sha256=task_sha256,
        )
        packet_path = packets_dir / f"{case_id}.annotation-packet.json"
        _write_json(packet_path, packet)
        entries.append(
            {
                "case_id": case_id,
                "source_task_sha256": task_sha256,
                "packet_file": f"packets/{packet_path.name}",
                "packet_sha256": sha256_file(packet_path),
                "field_count": len(packet["field_inventory"]),
            }
        )

    output_manifest = {
        "schema_version": "semantic-calibration-pack/v1",
        "benchmark_role": "annotator_and_backend_calibration",
        "research_evidence_status": "non_blind_not_for_effect_estimation",
        "source_manifest_sha256": sha256_file(manifest_path),
        "prediction_fields_removed": list(REMOVED_PREDICTION_FIELDS),
        "case_count": len(entries),
        "cases": entries,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "manifest.json", output_manifest)
    return output_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build neutral non-blind packets for independent annotator calibration."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    report = build_calibration_pack(args.manifest, args.output_dir)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
