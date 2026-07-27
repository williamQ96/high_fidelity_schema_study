from __future__ import annotations

import hashlib
import json
from pathlib import Path

from high_fidelity_schema_study.ndp50_semantic_packets import (
    build_ndp50_semantic_packets,
)


def _write(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_packet_builder_removes_semantic_predictions(tmp_path: Path) -> None:
    study_root = tmp_path / "study"
    schema_path = study_root / "schemas" / "development" / "d1" / "r1.json"
    schema_hash = _write(
        schema_path,
        {
            "schema": {
                "file_format": "csv",
                "data_modality": "tabular",
                "fields": [
                    {
                        "field_name": "temp",
                        "field_path": "temp",
                        "physical_type": "float",
                        "logical_type": "measurement",
                        "semantic_type": "air_temperature",
                        "unit": "Celsius",
                        "confidence": 1.0,
                        "source_evidence": [
                            {
                                "tier": "structural",
                                "evidence_type": "csv_header",
                                "source": "/private/path/data.csv",
                                "detail": "header='temp'",
                            }
                        ],
                    }
                ],
            }
        },
    )
    opportunity = tmp_path / "opportunity.json"
    _write(
        opportunity,
        {
            "schema_version": "ndp50-semantic-opportunity-manifest/v1",
            "cases": [
                {
                    "case_id": "ndp50-development-r1",
                    "dataset_id": "d1",
                    "resource_id": "r1",
                    "split": "development",
                    "title": "Weather",
                    "schema_artifact": {
                        "file": "schemas/development/d1/r1.json",
                        "sha256": schema_hash,
                    },
                    "file_format": "csv",
                    "data_modality": "tabular",
                }
            ],
        },
    )

    manifest = build_ndp50_semantic_packets(
        opportunity_manifest_path=opportunity,
        study_root=study_root,
        output_dir=tmp_path / "pack",
    )
    packet = json.loads(
        (
            tmp_path
            / "pack"
            / manifest["cases"][0]["packet_file"]
        ).read_text(encoding="utf-8")
    )

    field = packet["field_inventory"][0]
    assert field["physical_type"] == "float"
    assert "logical_type" not in field
    assert "semantic_type" not in field
    assert "unit" not in field
    assert "confidence" not in field
    assert field["source_evidence"][0]["source_label"] == "data.csv"
