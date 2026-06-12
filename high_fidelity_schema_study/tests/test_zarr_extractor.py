from __future__ import annotations

import json
import sys
from pathlib import Path

from high_fidelity_schema_study import cli
from high_fidelity_schema_study.extractors.base import ExtractionRequest
from high_fidelity_schema_study.extractors.registry import extract_path


ROOT = Path(__file__).resolve().parents[1]
CHALLENGE_ROOT = ROOT / "testdata" / "zarr_phase14a"


def _extract(name: str):
    return extract_path(ExtractionRequest(str(CHALLENGE_ROOT / name)))


def test_zarr_directory_auto_detection_and_physical_metadata():
    outcome = _extract("physical_metadata.zarr")

    assert outcome.status == "success"
    assert outcome.format_decision.selected_format == "zarr"
    assert outcome.format_decision.basis == "zarr_store_metadata"
    assert outcome.extractor is not None
    assert outcome.extractor.extractor_id == "zarr_v2_metadata_extractor"
    assert outcome.schema is not None
    field = outcome.schema.fields[0]
    analysis = outcome.schema.metadata["zarr_analysis"]["arrays"][0]
    assert field.physical_type == "<i2"
    assert field.shape == [4, 6]
    assert field.nullable is True
    assert analysis["array_metadata"]["chunks"] == [2, 3]
    assert analysis["array_metadata"]["compressor"] == {"id": "zlib", "level": 1}
    assert analysis["array_metadata"]["fill_value"] == -9999
    assert analysis["array_metadata"]["order"] == "F"
    assert outcome.schema.metadata["value_observation"]["state"] == "unknown"
    assert outcome.schema.metadata["value_observation"]["reason_code"] == "chunk_payloads_not_read"
    assert "deterministic_profile" not in outcome.schema.metadata
    assert any(item.evidence_type == "zarr_array_metadata" for item in field.source_evidence)
    assert all(not item.source.startswith(str(ROOT)) for item in field.source_evidence)


def test_zarr_xarray_dimensions_and_coordinates_are_convention_backed():
    outcome = _extract("xarray_coordinates.zarr")

    assert outcome.status == "success"
    assert outcome.schema is not None
    fields = {field.field_name: field for field in outcome.schema.fields}
    analyses = {
        item["field_path"]: item
        for item in outcome.schema.metadata["zarr_analysis"]["arrays"]
    }
    assert fields["time"].physical_type == "<f8"
    assert fields["time"].logical_type == "temporal_coordinate"
    assert "time_series" not in outcome.schema.metadata
    assert "dimension_coordinate" in analyses["time"]["coordinate_roles"]
    assert analyses["temperature"]["dimensions"] == ["time", "lat"]
    assert outcome.schema.metadata["dimensions"]["time"]["state"] == "supported"


def test_zarr_coordinate_conflict_stays_unknown():
    outcome = _extract("coordinate_conflict.zarr")

    assert outcome.schema is not None
    field = outcome.schema.fields[0]
    analysis = outcome.schema.metadata["zarr_analysis"]["arrays"][0]
    assert field.logical_type == "unknown"
    assert field.semantic_type == "unknown"
    assert analysis["coordinate_role_claim"]["state"] == "conflicted"


def test_zarr_partial_malformed_store_retains_valid_array():
    outcome = _extract("partial_malformed.zarr")

    assert outcome.status == "partial"
    assert outcome.schema is not None
    assert [field.field_path for field in outcome.schema.fields] == ["valid"]
    assert {issue.code for issue in outcome.issues} >= {"partial_extraction", "zarr_metadata_malformed"}


def test_zarr_missing_metadata_and_v3_are_structured_abstentions():
    missing = _extract("missing_metadata.zarr")
    version3 = _extract("zarr_v3.zarr")

    assert missing.status == "abstained"
    assert missing.issues[0].code == "zarr_metadata_missing"
    assert version3.status == "abstained"
    assert version3.issues[0].code == "unsupported_zarr_version"


def test_directory_resource_kind_mismatch_is_structured():
    outcome = extract_path(
        ExtractionRequest(
            str(CHALLENGE_ROOT / "basic_array.zarr"),
            resource_kind="file",
        )
    )

    assert outcome.status == "failed"
    assert outcome.issues[0].code == "resource_kind_mismatch"


def test_generic_cli_extracts_zarr_directory(monkeypatch, capsys):
    path = CHALLENGE_ROOT / "basic_array.zarr"
    monkeypatch.setattr(sys, "argv", ["schema-study", "extract", "--input", str(path), "--format", "auto"])

    cli.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "success"
    assert payload["format_decision"]["selected_format"] == "zarr"
    assert payload["extractor"]["extractor_id"] == "zarr_v2_metadata_extractor"
