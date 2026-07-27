from __future__ import annotations

import hashlib
import json
from pathlib import Path

from high_fidelity_schema_study.ndp50_vocabulary_draft import (
    build_vocabulary_draft,
)
from high_fidelity_schema_study.semantic_gold_workflow import validate_vocabulary


def _write(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_vocabulary_draft_adds_only_observed_physical_types(
    tmp_path: Path,
) -> None:
    base = tmp_path / "base.json"
    _write(
        base,
        {
            "schema_version": "semantic-annotation-vocabulary/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "frozen",
            "vocabulary_version": "base-v1",
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
            "unit_patterns": [
                {"pattern": "^days since .+$", "meaning": "reference time"}
            ],
            "unknown_representation": None,
        },
    )
    packet = tmp_path / "packets" / "case.json"
    packet_hash = _write(
        packet,
        {
            "field_inventory": [
                {"field_path": "station_code", "physical_type": "int64"}
            ]
        },
    )
    manifest = tmp_path / "manifest.json"
    _write(
        manifest,
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

    draft = build_vocabulary_draft(
        packet_manifest_path=manifest,
        base_vocabulary_path=base,
    )

    assert draft["status"] == "draft"
    assert draft["physical_types"] == ["int64", "string"]
    assert draft["semantic_types"] == ["record_identifier"]
    assert validate_vocabulary(draft)["status"] == "blocked"
