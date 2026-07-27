from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping

from .semantic_gold_workflow import PROPERTY_VALUE_KEYS


POOL_SCHEMA_VERSION = "ndp50-demonstration-pool/v2"
WORKFLOW_SCHEMA_VERSION = "ndp50-demonstration-pool-workflow/v1"
VALIDATION_SCHEMA_VERSION = "ndp50-demonstration-pool-replay/v1"
PACKET_SCHEMA_VERSION = "semantic-annotation-packet/v1"
GOLD_SCHEMA_VERSION = "blind-semantic-gold/v1"
PROPERTIES = tuple(PROPERTY_VALUE_KEYS)


class NDPDemonstrationPoolError(ValueError):
    pass


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _study_relative(path: Path, study_root: Path) -> str:
    try:
        return path.resolve().relative_to(study_root.resolve()).as_posix()
    except ValueError as exc:
        raise NDPDemonstrationPoolError(
            f"artifact must be inside the study root: {path}"
        ) from exc


def _binding(path: Path, study_root: Path) -> Dict[str, str]:
    if not path.is_file():
        raise NDPDemonstrationPoolError(f"artifact does not exist: {path}")
    return {
        "file": _study_relative(path, study_root),
        "sha256": _sha256_file(path),
    }


def _bound_path(
    ref: Any,
    *,
    study_root: Path,
    label: str,
) -> Path:
    if not isinstance(ref, dict):
        raise NDPDemonstrationPoolError(f"{label} binding is missing")
    value = ref.get("file")
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise NDPDemonstrationPoolError(
            f"{label} must use a study-relative file"
        )
    root = study_root.resolve()
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise NDPDemonstrationPoolError(
            f"{label} escapes the study root"
        ) from exc
    if not path.is_file():
        raise NDPDemonstrationPoolError(f"{label} does not exist")
    if _sha256_file(path) != ref.get("sha256"):
        raise NDPDemonstrationPoolError(f"{label} hash mismatch")
    return path


def _packet_manifest(path: Path) -> Dict[str, Any]:
    manifest = _load_json(path)
    if (
        manifest.get("schema_version")
        != "ndp50-semantic-packet-pack/v1"
        or manifest.get("status")
        != "neutral_packets_ready_source_bundles_blocked"
    ):
        raise NDPDemonstrationPoolError("unexpected packet manifest")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise NDPDemonstrationPoolError("packet manifest has no cases")
    case_ids = [str(item.get("case_id") or "") for item in cases]
    if (
        any(not case_id for case_id in case_ids)
        or len(case_ids) != len(set(case_ids))
        or any(
            item.get("split") not in {"development", "validation"}
            for item in cases
        )
    ):
        raise NDPDemonstrationPoolError(
            "packet cases must be unique development/validation cases"
        )
    return manifest


def _packet_path(
    item: Mapping[str, Any],
    *,
    manifest_path: Path,
) -> Path:
    value = item.get("packet_file")
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise NDPDemonstrationPoolError(
            f"{item.get('case_id')} packet_file must be manifest-relative"
        )
    path = (manifest_path.parent / value).resolve()
    if not path.is_file():
        raise NDPDemonstrationPoolError(
            f"{item.get('case_id')} packet does not exist"
        )
    if _sha256_file(path) != item.get("packet_sha256"):
        raise NDPDemonstrationPoolError(
            f"{item.get('case_id')} packet hash mismatch"
        )
    return path


def _input_projection(
    packet: Mapping[str, Any],
    *,
    case_id: str,
) -> Dict[str, Any]:
    if packet.get("schema_version") != PACKET_SCHEMA_VERSION:
        raise NDPDemonstrationPoolError(
            f"{case_id} has unexpected packet schema"
        )
    fields = packet.get("field_inventory")
    if not isinstance(fields, list) or not fields:
        raise NDPDemonstrationPoolError(
            f"{case_id} packet field inventory is empty"
        )
    projected = []
    seen: set[str] = set()
    for field in fields:
        if not isinstance(field, dict):
            raise NDPDemonstrationPoolError(
                f"{case_id} packet field must be an object"
            )
        field_path = str(field.get("field_path") or "")
        if not field_path or field_path in seen:
            raise NDPDemonstrationPoolError(
                f"{case_id} packet field paths must be unique"
            )
        seen.add(field_path)
        examples = field.get("example_values")
        if examples is None:
            examples = []
        if not isinstance(examples, list):
            raise NDPDemonstrationPoolError(
                f"{case_id}.{field_path} example_values must be a list"
            )
        projected.append(
            {
                "field_path": field_path,
                "field_name": field.get("field_name"),
                "observed_physical_type": field.get("physical_type"),
                "example_values": examples,
                "nullable": field.get("nullable"),
                "shape": field.get("shape"),
            }
        )
    projected.sort(key=lambda item: item["field_path"])
    return {
        "case_id": case_id,
        "dataset_id": packet.get("dataset_id"),
        "data_modality": packet.get("data_modality"),
        "fields": projected,
    }


def _gold_projection(
    consensus: Mapping[str, Any],
    *,
    case_id: str,
) -> Dict[str, Any]:
    if (
        consensus.get("schema_version") != GOLD_SCHEMA_VERSION
        or consensus.get("annotation_stage") != "consensus"
    ):
        raise NDPDemonstrationPoolError(
            f"{case_id} has unexpected consensus schema or stage"
        )
    fields = consensus.get("fields")
    if not isinstance(fields, list) or not fields:
        raise NDPDemonstrationPoolError(
            f"{case_id} consensus fields are empty"
        )
    projected = []
    seen: set[str] = set()
    for field in fields:
        if not isinstance(field, dict):
            raise NDPDemonstrationPoolError(
                f"{case_id} consensus field must be an object"
            )
        field_path = str(field.get("field_path") or "")
        if not field_path or field_path in seen:
            raise NDPDemonstrationPoolError(
                f"{case_id} consensus field paths must be unique"
            )
        seen.add(field_path)
        applicability = field.get("applicability")
        if not isinstance(applicability, dict):
            raise NDPDemonstrationPoolError(
                f"{case_id}.{field_path} applicability is missing"
            )
        annotations: Dict[str, Dict[str, Any]] = {}
        for property_name in PROPERTIES:
            applicable = applicability.get(property_name)
            if not isinstance(applicable, bool):
                raise NDPDemonstrationPoolError(
                    f"{case_id}.{field_path}.{property_name} "
                    "applicability must be boolean"
                )
            value = field.get(PROPERTY_VALUE_KEYS[property_name])
            if not applicable and value is not None:
                raise NDPDemonstrationPoolError(
                    f"{case_id}.{field_path}.{property_name} "
                    "cannot have a value when not applicable"
                )
            annotations[property_name] = {
                "applicability": applicable,
                "value": value,
            }
        projected.append(
            {
                "field_path": field_path,
                "annotations": annotations,
            }
        )
    projected.sort(key=lambda item: item["field_path"])
    return {"case_id": case_id, "fields": projected}


def build_workflow_spec(
    *,
    packet_manifest_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    manifest = _packet_manifest(packet_manifest_path)
    development_count = sum(
        item.get("split") == "development"
        for item in manifest["cases"]
    )
    if development_count < 5:
        raise NDPDemonstrationPoolError(
            "at least five development cases are required"
        )
    implementation = Path(__file__).resolve()
    return {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "status": "implementation_ready_waiting_on_semantic_gold",
        "human_decisions_present": False,
        "packet_manifest": _binding(packet_manifest_path, study_root),
        "source_split": "development",
        "candidate_inclusion_policy": "all_approved_development_cases",
        "minimum_candidate_count": 5,
        "development_case_count": development_count,
        "validation_or_test_candidates_forbidden": True,
        "model_outputs_used_for_inclusion": False,
        "output_schema_version": POOL_SCHEMA_VERSION,
        "semantic_projection_policy": {
            "input": "neutral_packet_structural_observations_only",
            "output": "approved_consensus_property_applicability_and_value",
            "evidence_rationales_and_annotator_identities_excluded": True,
        },
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            "semantic_gold_workflow.py": _sha256_file(
                implementation.with_name("semantic_gold_workflow.py")
            )
        },
    }


def build_pool(
    *,
    semantic_gold_approval_path: Path,
    packet_manifest_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    manifest = _packet_manifest(packet_manifest_path)
    approval = _load_json(semantic_gold_approval_path)
    if (
        approval.get("schema_version")
        != "ndp50-semantic-gold-approval/v1"
        or approval.get("status")
        != "approved_independent_gold_complete"
        or approval.get("derived_gates", {}).get(
            "independent_gold_complete"
        )
        is not True
    ):
        raise NDPDemonstrationPoolError(
            "semantic gold approval is not complete"
        )
    gold_cases = approval.get("index", {}).get("cases")
    if not isinstance(gold_cases, list):
        raise NDPDemonstrationPoolError("gold approval cases are missing")
    gold_by_id = {
        str(item.get("case_id") or ""): item
        for item in gold_cases
        if isinstance(item, dict)
    }
    development = sorted(
        (
            item
            for item in manifest["cases"]
            if item.get("split") == "development"
        ),
        key=lambda item: str(item["case_id"]),
    )
    if len(development) < 5:
        raise NDPDemonstrationPoolError(
            "at least five development cases are required"
        )
    cases = []
    for packet_item in development:
        case_id = str(packet_item["case_id"])
        gold_item = gold_by_id.get(case_id)
        if gold_item is None or gold_item.get("split") != "development":
            raise NDPDemonstrationPoolError(
                f"{case_id} lacks approved development gold"
            )
        packet_path = _packet_path(
            packet_item,
            manifest_path=packet_manifest_path,
        )
        consensus_path = _bound_path(
            gold_item.get("consensus"),
            study_root=study_root,
            label=f"{case_id} consensus",
        )
        packet = _load_json(packet_path)
        consensus = _load_json(consensus_path)
        input_projection = _input_projection(packet, case_id=case_id)
        gold_projection = _gold_projection(consensus, case_id=case_id)
        input_paths = {
            item["field_path"] for item in input_projection["fields"]
        }
        output_paths = {
            item["field_path"] for item in gold_projection["fields"]
        }
        if input_paths != output_paths:
            raise NDPDemonstrationPoolError(
                f"{case_id} packet and gold field coverage differ"
            )
        cases.append(
            {
                "case_id": case_id,
                "source_split": "development",
                "packet": _binding(packet_path, study_root),
                "gold_consensus": _binding(consensus_path, study_root),
                "input_projection": input_projection,
                "gold_projection": gold_projection,
            }
        )
    implementation = Path(__file__).resolve()
    return {
        "schema_version": POOL_SCHEMA_VERSION,
        "status": "validator_generated_development_only",
        "source_split": "development",
        "candidate_inclusion_policy": "all_approved_development_cases",
        "model_outputs_used_for_inclusion": False,
        "validation_or_test_candidates_included": False,
        "packet_manifest": _binding(packet_manifest_path, study_root),
        "semantic_gold_approval": _binding(
            semantic_gold_approval_path, study_root
        ),
        "case_count": len(cases),
        "cases": cases,
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            "semantic_gold_workflow.py": _sha256_file(
                implementation.with_name("semantic_gold_workflow.py")
            )
        },
    }


def verify_pool(
    pool: Mapping[str, Any],
    *,
    semantic_gold_approval_path: Path,
    packet_manifest_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    try:
        expected = build_pool(
            semantic_gold_approval_path=semantic_gold_approval_path,
            packet_manifest_path=packet_manifest_path,
            study_root=study_root,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": VALIDATION_SCHEMA_VERSION,
            "status": "failed",
            "differing_top_level_keys": ["inputs"],
            "detail": str(exc),
        }
    differing = sorted(
        key
        for key in set(pool) | set(expected)
        if pool.get(key) != expected.get(key)
    )
    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "status": "passed" if not differing else "failed",
        "differing_top_level_keys": differing,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare, build, or replay the deterministic NDP-50 "
            "development demonstration pool."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--packet-manifest", type=Path, required=True)
    prepare.add_argument("--study-root", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    for command in ("build", "verify"):
        item = subparsers.add_parser(command)
        item.add_argument(
            "--semantic-gold-approval", type=Path, required=True
        )
        item.add_argument("--packet-manifest", type=Path, required=True)
        item.add_argument("--study-root", type=Path, required=True)
        if command == "build":
            item.add_argument("--output", type=Path, required=True)
        else:
            item.add_argument("--artifact", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "prepare":
        payload = build_workflow_spec(
            packet_manifest_path=args.packet_manifest,
            study_root=args.study_root,
        )
        _write_json(args.output, payload)
    elif args.command == "build":
        payload = build_pool(
            semantic_gold_approval_path=args.semantic_gold_approval,
            packet_manifest_path=args.packet_manifest,
            study_root=args.study_root,
        )
        _write_json(args.output, payload)
    else:
        payload = verify_pool(
            _load_json(args.artifact),
            semantic_gold_approval_path=args.semantic_gold_approval,
            packet_manifest_path=args.packet_manifest,
            study_root=args.study_root,
        )
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
