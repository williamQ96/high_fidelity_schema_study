from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .build_semantic_calibration_pack import build_neutral_annotation_packet
from .semantic_gold_workflow import validate_annotation_packet


PACK_SCHEMA_VERSION = "ndp50-semantic-packet-pack/v1"


class NDPSemanticPacketError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_ndp50_semantic_packets(
    *,
    opportunity_manifest_path: Path,
    study_root: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    opportunities = _load_json(opportunity_manifest_path)
    if opportunities.get("schema_version") != (
        "ndp50-semantic-opportunity-manifest/v1"
    ):
        raise NDPSemanticPacketError("unexpected opportunity manifest schema")
    entries = []
    for case in opportunities["cases"]:
        if case["split"] == "test":
            raise NDPSemanticPacketError("test case leaked into semantic packets")
        schema_path = study_root / case["schema_artifact"]["file"]
        if not schema_path.is_file():
            raise NDPSemanticPacketError(
                f"schema artifact is missing for {case['case_id']}"
            )
        if _sha256_file(schema_path) != case["schema_artifact"]["sha256"]:
            raise NDPSemanticPacketError(
                f"schema hash mismatch for {case['case_id']}"
            )
        outcome = _load_json(schema_path)
        schema = outcome.get("schema")
        if not isinstance(schema, dict):
            raise NDPSemanticPacketError("schema artifact contains no schema")
        source_task = {
            "task": {
                "task_id": case["case_id"],
                "dataset_id": case["case_id"],
                "file_format": case["file_format"],
                "data_modality": case["data_modality"],
                "deterministic_schema": schema,
                "grounding_snippets": [
                    {
                        "source_type": "catalog_title",
                        "source_name": "NDP dataset title",
                        "detail": "Frozen NDP catalog title; metadata evidence, not gold.",
                        "text": case["title"],
                        "applicable_field_paths": [
                            str(field["field_path"])
                            for field in schema["fields"]
                        ],
                    }
                ],
            }
        }
        packet = build_neutral_annotation_packet(
            source_task,
            case_id=case["case_id"],
            source_task_sha256=case["schema_artifact"]["sha256"],
            purpose="ndp50_independent_semantic_gold",
            research_evidence_status=(
                "pre_model_independent_gold_preparation"
            ),
            allowed_evidence_types=frozenset(
                {
                    "csv_header",
                    "sample_rows",
                    "json_sample_observation",
                    "json_schema_declaration",
                    "hdf5_dataset_path",
                    "hdf5_attribute",
                }
            ),
        )
        packet.update(
            {
                "source_dataset_id": case["dataset_id"],
                "source_resource_id": case["resource_id"],
                "primary_analysis_cluster": case["dataset_id"],
                "split": case["split"],
            }
        )
        validation = validate_annotation_packet(packet)
        if validation["status"] != "ready":
            raise NDPSemanticPacketError(
                f"neutral packet invalid for {case['case_id']}: "
                f"{validation['errors']}"
            )
        packet_path = output_dir / "packets" / (
            f"{case['case_id']}.annotation-packet.json"
        )
        _write_json(packet_path, packet)
        entries.append(
            {
                "case_id": case["case_id"],
                "dataset_id": case["dataset_id"],
                "resource_id": case["resource_id"],
                "split": case["split"],
                "packet_file": packet_path.relative_to(output_dir).as_posix(),
                "packet_sha256": _sha256_file(packet_path),
                "field_count": len(packet["field_inventory"]),
                "source_bundle_status": "blocked_pending_frozen_vocabulary",
            }
        )
    manifest = {
        "schema_version": PACK_SCHEMA_VERSION,
        "protocol_version": "semantic-architecture-protocol/v1",
        "created_at": _utc_now(),
        "status": "neutral_packets_ready_source_bundles_blocked",
        "claim_boundary": (
            "Packets contain structural observations and frozen catalog titles "
            "only; no logical/semantic/unit predictions, gold, model output, or "
            "test identities."
        ),
        "opportunity_manifest": {
            "file": opportunity_manifest_path.name,
            "sha256": _sha256_file(opportunity_manifest_path),
        },
        "case_count": len(entries),
        "field_count": sum(item["field_count"] for item in entries),
        "cases": sorted(entries, key=lambda item: item["case_id"]),
        "blockers": [
            "corpus-specific vocabulary is not frozen",
            "approved raw/documentation source bundles are not frozen",
            "two independent non-developer annotators are not assigned",
        ],
    }
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build prediction-neutral NDP-50 semantic annotation packets."
    )
    parser.add_argument("--opportunity-manifest", type=Path, required=True)
    parser.add_argument("--study-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_ndp50_semantic_packets(
        opportunity_manifest_path=args.opportunity_manifest,
        study_root=args.study_root,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "case_count": manifest["case_count"],
                "field_count": manifest["field_count"],
                "status": manifest["status"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
