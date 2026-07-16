from __future__ import annotations

import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.build_semantic_calibration_pack import (
    REMOVED_PREDICTION_FIELDS,
    build_calibration_pack,
    sha256_file,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def source_task() -> dict:
    return {
        "system_rules": ["fixture"],
        "task": {
            "task_id": "fixture::case-1",
            "dataset_id": "case-1",
            "file_format": "csv",
            "data_modality": "tabular",
            "deterministic_schema": {
                "fields": [
                    {
                        "field_name": "temp_c",
                        "field_path": "temp_c",
                        "physical_type": "float",
                        "logical_type": "measurement",
                        "semantic_type": "air_temperature",
                        "unit": "degree_Celsius",
                        "description": "Predicted description.",
                        "semantic_logical_hint": "measurement",
                        "confidence": 1.0,
                        "uncertainty_reason": None,
                        "nullable": False,
                        "missing_count": 0,
                        "unique_ratio": 1.0,
                        "shape": None,
                        "example_values": ["20.1", "21.3"],
                        "value_range": [20.1, 21.3],
                        "extraction_method": "fixture_profiler",
                        "source_evidence": [
                            {
                                "tier": "structural",
                                "evidence_type": "csv_header",
                                "source": "C:\\secret\\raw\\weather.csv",
                                "detail": "header='temp_c'",
                                "confidence": 1.0,
                            },
                            {
                                "tier": "structural",
                                "evidence_type": "column_name_unit_hint",
                                "source": "temp_c",
                                "detail": "inferred unit from suffix: degree_Celsius",
                                "confidence": 0.82,
                            },
                        ],
                    }
                ]
            },
            "grounding_snippets": [
                {
                    "source_type": "README",
                    "source_name": "README.md",
                    "detail": "line 7",
                    "text": "Temperature is reported by the station sensor.",
                }
            ],
        },
    }


def source_manifest(role: str = "calibration") -> dict:
    return {
        "schema_version": "minimal-architecture-manifest/v1",
        "benchmark_role": role,
        "cases": [
            {
                "case_id": "case-1",
                "task_file": "case-1.task.json",
                "gold_file": "secret.gold.json",
                "legacy_result_file": "legacy.result.json",
            }
        ],
    }


def build_fixture(tmp_path: Path, *, role: str = "calibration") -> tuple[Path, Path]:
    manifest_path = tmp_path / "source" / "manifest.json"
    task_path = manifest_path.parent / "case-1.task.json"
    write_json(task_path, source_task())
    write_json(manifest_path, source_manifest(role))
    return manifest_path, task_path


def test_pack_strips_predictions_derived_hints_and_gold_paths(tmp_path: Path) -> None:
    manifest_path, task_path = build_fixture(tmp_path)
    output_dir = tmp_path / "pack"

    manifest = build_calibration_pack(manifest_path, output_dir)
    packet_path = output_dir / manifest["cases"][0]["packet_file"]
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    field = packet["field_inventory"][0]

    assert set(REMOVED_PREDICTION_FIELDS).isdisjoint(field)
    assert field["physical_type"] == "float"
    assert [item["evidence_type"] for item in field["source_evidence"]] == [
        "csv_header"
    ]
    assert field["source_evidence"][0]["source_label"] == "weather.csv"
    assert "confidence" not in field["source_evidence"][0]
    assert packet["evidence_policy"]["derived_semantic_hints_removed"] is True

    serialized_manifest = (output_dir / "manifest.json").read_text(encoding="utf-8")
    assert "secret.gold.json" not in serialized_manifest
    assert "legacy.result.json" not in serialized_manifest
    assert "case-1.task.json" not in serialized_manifest
    assert "source_task_file" not in manifest["cases"][0]
    assert manifest["source_manifest_sha256"] == sha256_file(manifest_path)
    assert manifest["cases"][0]["source_task_sha256"] == sha256_file(task_path)
    assert manifest["research_evidence_status"] == (
        "non_blind_not_for_effect_estimation"
    )


def test_pack_build_is_content_deterministic(tmp_path: Path) -> None:
    manifest_path, _ = build_fixture(tmp_path)

    first = build_calibration_pack(manifest_path, tmp_path / "first")
    second = build_calibration_pack(manifest_path, tmp_path / "second")

    assert first == second
    first_packet = tmp_path / "first" / first["cases"][0]["packet_file"]
    second_packet = tmp_path / "second" / second["cases"][0]["packet_file"]
    assert first_packet.read_bytes() == second_packet.read_bytes()
    assert sha256_file(first_packet) == first["cases"][0]["packet_sha256"]


def test_pack_rejects_blind_source(tmp_path: Path) -> None:
    manifest_path, _ = build_fixture(tmp_path, role="blind_external")

    with pytest.raises(ValueError, match="never blind"):
        build_calibration_pack(manifest_path, tmp_path / "pack")


def test_pack_rejects_duplicate_case_identity(tmp_path: Path) -> None:
    manifest_path, _ = build_fixture(tmp_path)
    duplicate = source_manifest()
    duplicate["cases"].append(dict(duplicate["cases"][0]))
    write_json(manifest_path, duplicate)

    with pytest.raises(ValueError, match="duplicate calibration case_id"):
        build_calibration_pack(manifest_path, tmp_path / "pack")


def test_checked_in_calibration_pack_is_exact_rebuild(tmp_path: Path) -> None:
    package_root = Path(__file__).resolve().parents[1]
    source = (
        package_root
        / "data"
        / "experiments"
        / "minimal_architecture_redesign"
        / "development_manifest.json"
    )
    checked_in = (
        package_root / "data" / "experiments" / "semantic_architecture_calibration_v1"
    )

    rebuilt = build_calibration_pack(source, tmp_path / "rebuilt")
    frozen = json.loads((checked_in / "manifest.json").read_text(encoding="utf-8"))

    assert rebuilt == frozen
    for item in frozen["cases"]:
        expected = checked_in / item["packet_file"]
        actual = tmp_path / "rebuilt" / item["packet_file"]
        assert actual.read_bytes() == expected.read_bytes()
        assert sha256_file(expected) == item["packet_sha256"]
