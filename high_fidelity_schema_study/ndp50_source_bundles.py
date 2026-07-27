from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .semantic_gold_workflow import (
    build_packet_source_bundle,
    validate_annotation_packet,
    validate_source_bundle,
    validate_source_bundle_files,
    validate_vocabulary,
)


MANIFEST_SCHEMA_VERSION = "ndp50-source-bundle-draft-manifest/v1"


class NDPSourceBundleError(ValueError):
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


def _relative(path: Path, owner_dir: Path) -> str:
    return Path(os.path.relpath(path.resolve(), owner_dir.resolve())).as_posix()


def build_source_bundle_drafts(
    *,
    opportunity_manifest_path: Path,
    packet_manifest_path: Path,
    vocabulary_path: Path,
    study_root: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    opportunities = _load_json(opportunity_manifest_path)
    packet_manifest = _load_json(packet_manifest_path)
    vocabulary = _load_json(vocabulary_path)
    vocabulary_hash = _sha256_file(vocabulary_path)
    vocabulary_status = vocabulary.get("status")
    if vocabulary_status == "frozen" and validate_vocabulary(vocabulary)[
        "status"
    ] != "ready":
        raise NDPSourceBundleError(
            "a frozen vocabulary must pass the vocabulary validator"
        )
    bundle_status = (
        "draft_blocked_on_human_source_approval"
        if vocabulary_status == "frozen"
        else "draft_blocked_on_frozen_vocabulary_and_human_approval"
    )
    annotation_readiness = (
        "blocked_on_human_source_approval"
        if vocabulary_status == "frozen"
        else "blocked_on_frozen_vocabulary_and_human_approval"
    )
    if opportunities.get("schema_version") != (
        "ndp50-semantic-opportunity-manifest/v1"
    ):
        raise NDPSourceBundleError("unexpected opportunity manifest schema")
    if packet_manifest.get("schema_version") != "ndp50-semantic-packet-pack/v1":
        raise NDPSourceBundleError("unexpected packet manifest schema")
    opportunity_by_case = {
        item["case_id"]: item for item in opportunities["cases"]
    }
    packet_by_case = {
        item["case_id"]: item for item in packet_manifest["cases"]
    }
    if set(opportunity_by_case) != set(packet_by_case):
        raise NDPSourceBundleError(
            "opportunity and packet manifests have different case identities"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for case_id in sorted(opportunity_by_case):
        case = opportunity_by_case[case_id]
        packet_item = packet_by_case[case_id]
        packet_path = (
            packet_manifest_path.parent / packet_item["packet_file"]
        ).resolve()
        if _sha256_file(packet_path) != packet_item["packet_sha256"]:
            raise NDPSourceBundleError(f"packet hash mismatch for {case_id}")
        packet = _load_json(packet_path)
        if validate_annotation_packet(packet)["status"] != "ready":
            raise NDPSourceBundleError(f"packet is invalid for {case_id}")

        download_file = str(case["source_resource"].get("download_file") or "")
        raw_path = (
            study_root
            / "resources"
            / case["split"]
            / case["dataset_id"]
            / download_file
        )
        if not download_file or not raw_path.is_file():
            raise NDPSourceBundleError(f"raw resource unavailable for {case_id}")
        raw_hash = _sha256_file(raw_path)
        if raw_hash != case["source_resource"]["download_sha256"]:
            raise NDPSourceBundleError(f"raw resource hash mismatch for {case_id}")

        detail_file = str(case["source_detail_snapshot"].get("file") or "")
        detail_path = (
            study_root
            / "acquisition"
            / f"{case['split']}_details"
            / detail_file
        )
        if not detail_file or not detail_path.is_file():
            raise NDPSourceBundleError(f"detail snapshot unavailable for {case_id}")
        detail_hash = _sha256_file(detail_path)
        if detail_hash != case["source_detail_snapshot"]["sha256"]:
            raise NDPSourceBundleError(
                f"detail snapshot hash mismatch for {case_id}"
            )

        bundle_path = output_dir / f"{case_id}.source-bundle.json"
        bundle = build_packet_source_bundle(packet_path, vocabulary_path)
        bundle.update(
            {
                "status": bundle_status,
                "annotation_packet_file": _relative(packet_path, output_dir),
                "vocabulary_file": _relative(vocabulary_path, output_dir),
                "source_dataset_id": case["dataset_id"],
                "source_resource_id": case["resource_id"],
                "primary_analysis_cluster": case["dataset_id"],
                "split": case["split"],
            }
        )
        bundle["sources"][0]["source_file"] = _relative(packet_path, output_dir)
        bundle["sources"].extend(
            [
                {
                    "source_id": "RAW_RESOURCE",
                    "source_type": "original_acquired_dataset_resource",
                    "source_file": _relative(raw_path, output_dir),
                    "source_sha256": raw_hash,
                },
                {
                    "source_id": "NDP_DETAIL_SNAPSHOT",
                    "source_type": "frozen_ndp_ckan_package_show_snapshot",
                    "source_file": _relative(detail_path, output_dir),
                    "source_sha256": detail_hash,
                },
            ]
        )
        field_paths = [
            str(item["field_path"]) for item in packet["field_inventory"]
        ]
        raw_selector_prefix = (
            "column" if case["file_format"] == "csv" else "field_path"
        )
        for index, field_path in enumerate(field_paths, start=1):
            bundle["evidence_catalog"].append(
                {
                    "catalog_evidence_id": f"RAW-{index}",
                    "source_id": "RAW_RESOURCE",
                    "source_type": "original_resource_observation",
                    "source_sha256": raw_hash,
                    "selector": f"{raw_selector_prefix}:{field_path}",
                    "applicable_field_paths": [field_path],
                    "strength": "original_data",
                }
            )
        for evidence_id, selector in (
            ("NDP-TITLE", "raw_catalog_response.result.title"),
            ("NDP-NOTES", "raw_catalog_response.result.notes"),
        ):
            bundle["evidence_catalog"].append(
                {
                    "catalog_evidence_id": evidence_id,
                    "source_id": "NDP_DETAIL_SNAPSHOT",
                    "source_type": "catalog_documentation",
                    "source_sha256": detail_hash,
                    "selector": selector,
                    "applicable_field_paths": field_paths,
                    "strength": "documentation",
                }
            )
        structure_report = validate_source_bundle(
            bundle,
            packet=packet,
            packet_sha256=packet_item["packet_sha256"],
            vocabulary_sha256=vocabulary_hash,
        )
        file_report = validate_source_bundle_files(
            bundle,
            bundle_path=bundle_path,
            packet_path=packet_path,
        )
        if structure_report["status"] != "ready" or file_report["status"] != "ready":
            raise NDPSourceBundleError(
                f"source bundle validation failed for {case_id}: "
                f"{structure_report['errors'] + file_report['errors']}"
            )
        _write_json(bundle_path, bundle)
        entries.append(
            {
                "case_id": case_id,
                "split": case["split"],
                "bundle_file": bundle_path.name,
                "bundle_sha256": _sha256_file(bundle_path),
                "source_count": len(bundle["sources"]),
                "evidence_count": len(bundle["evidence_catalog"]),
                "structural_validation": "ready",
                "file_identity_validation": "ready",
                "annotation_readiness": annotation_readiness,
            }
        )

    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "protocol_version": "semantic-architecture-protocol/v1",
        "created_at": _utc_now(),
        "status": (
            "draft_bundles_structurally_valid_pending_human_source_approval"
            if vocabulary_status == "frozen"
            else "draft_bundles_structurally_valid_not_annotation_ready"
        ),
        "opportunity_manifest": {
            "file": opportunity_manifest_path.name,
            "sha256": _sha256_file(opportunity_manifest_path),
        },
        "packet_manifest": {
            "file": packet_manifest_path.name,
            "sha256": _sha256_file(packet_manifest_path),
        },
        "vocabulary": {
            "file": vocabulary_path.name,
            "sha256": vocabulary_hash,
            "status": vocabulary_status,
        },
        "case_count": len(entries),
        "cases": entries,
        "blockers": (
            ([] if vocabulary_status == "frozen" else [
                "vocabulary status is draft, not frozen"
            ])
            + [
                "human curators have not approved source relevance/entailment",
                "additional domain documentation may be required",
                "two independent non-developer annotators are not assigned",
            ]
        ),
    }
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build content-addressed draft NDP-50 source bundles."
    )
    parser.add_argument("--opportunity-manifest", type=Path, required=True)
    parser.add_argument("--packet-manifest", type=Path, required=True)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--study-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = build_source_bundle_drafts(
        opportunity_manifest_path=args.opportunity_manifest,
        packet_manifest_path=args.packet_manifest,
        vocabulary_path=args.vocabulary,
        study_root=args.study_root,
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "case_count": manifest["case_count"],
                "status": manifest["status"],
                "blocker_count": len(manifest["blockers"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
