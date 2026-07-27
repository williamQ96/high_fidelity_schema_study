from __future__ import annotations

import hashlib
import json
from pathlib import Path

from high_fidelity_schema_study.ndp50_source_bundles import (
    build_source_bundle_drafts,
)


def _write(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_bundle_draft_binds_packet_raw_and_detail_sources(
    tmp_path: Path,
) -> None:
    study = tmp_path / "study"
    raw = study / "resources" / "development" / "d1" / "data.csv"
    raw.parent.mkdir(parents=True)
    raw.write_text("a,b\n1,2\n", encoding="utf-8")
    raw_hash = hashlib.sha256(raw.read_bytes()).hexdigest()
    detail = study / "acquisition" / "development_details" / "d1.json.gz"
    detail.parent.mkdir(parents=True)
    detail.write_bytes(b"detail")
    detail_hash = hashlib.sha256(detail.read_bytes()).hexdigest()

    packet = tmp_path / "pack" / "packets" / "case.json"
    packet_hash = _write(
        packet,
        {
            "schema_version": "semantic-annotation-packet/v1",
            "dataset_id": "case",
            "field_inventory": [
                {
                    "field_name": "a",
                    "field_path": "a",
                    "physical_type": "int",
                    "source_evidence": [
                        {
                            "evidence_id": "a::F1",
                            "tier": "structural",
                            "evidence_type": "csv_header",
                            "source_label": "data.csv",
                            "detail": "header='a'",
                        }
                    ],
                }
            ],
            "approved_evidence": [],
        },
    )
    packet_manifest = tmp_path / "pack" / "manifest.json"
    _write(
        packet_manifest,
        {
            "schema_version": "ndp50-semantic-packet-pack/v1",
            "cases": [
                {
                    "case_id": "case",
                    "split": "development",
                    "packet_file": "packets/case.json",
                    "packet_sha256": packet_hash,
                }
            ],
        },
    )
    opportunity = tmp_path / "opportunity.json"
    _write(
        opportunity,
        {
            "schema_version": "ndp50-semantic-opportunity-manifest/v1",
            "cases": [
                {
                    "case_id": "case",
                    "dataset_id": "d1",
                    "resource_id": "r1",
                    "split": "development",
                    "file_format": "csv",
                    "source_resource": {
                        "download_file": "data.csv",
                        "download_sha256": raw_hash,
                    },
                    "source_detail_snapshot": {
                        "file": "d1.json.gz",
                        "sha256": detail_hash,
                    },
                }
            ],
        },
    )
    vocabulary = tmp_path / "vocabulary.json"
    _write(vocabulary, {"status": "draft"})

    manifest = build_source_bundle_drafts(
        opportunity_manifest_path=opportunity,
        packet_manifest_path=packet_manifest,
        vocabulary_path=vocabulary,
        study_root=study,
        output_dir=tmp_path / "bundles",
    )
    bundle = json.loads(
        (
            tmp_path
            / "bundles"
            / manifest["cases"][0]["bundle_file"]
        ).read_text(encoding="utf-8")
    )

    assert manifest["status"] == (
        "draft_bundles_structurally_valid_not_annotation_ready"
    )
    assert {item["source_id"] for item in bundle["sources"]} == {
        "ANNOTATION_PACKET",
        "RAW_RESOURCE",
        "NDP_DETAIL_SNAPSHOT",
    }
    assert manifest["cases"][0]["file_identity_validation"] == "ready"

    _write(
        vocabulary,
        {
            "schema_version": "semantic-annotation-vocabulary/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "frozen",
            "vocabulary_version": "ndp50-v1",
            "physical_types": ["string"],
            "logical_types": [
                "attribute",
                "coordinate",
                "identifier",
                "label",
                "measurement",
                "relationship",
                "time_axis",
                "unknown",
            ],
            "semantic_types": ["record_identifier"],
            "units": ["meter"],
            "unit_aliases": {"m": "meter"},
            "unit_patterns": [],
            "unknown_representation": None,
        },
    )
    frozen_manifest = build_source_bundle_drafts(
        opportunity_manifest_path=opportunity,
        packet_manifest_path=packet_manifest,
        vocabulary_path=vocabulary,
        study_root=study,
        output_dir=tmp_path / "frozen-bundles",
    )

    assert frozen_manifest["status"] == (
        "draft_bundles_structurally_valid_pending_human_source_approval"
    )
    assert "vocabulary status is draft, not frozen" not in frozen_manifest[
        "blockers"
    ]
