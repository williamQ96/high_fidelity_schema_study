from __future__ import annotations

import json
import sys
from pathlib import Path

import h5py

from high_fidelity_schema_study import cli
from high_fidelity_schema_study.extractors.base import ExtractionRequest
from high_fidelity_schema_study.extractors.registry import extract_path


ROOT = Path(__file__).resolve().parents[1]
CHALLENGE_ROOT = ROOT / "testdata" / "netcdf_cf_phase13"


def _extract(name: str):
    return extract_path(ExtractionRequest(str(CHALLENGE_ROOT / name)))


def test_netcdf_classic_auto_detection_and_cf_structure():
    outcome = _extract("standard_coordinates.nc")

    assert outcome.status == "success"
    assert outcome.format_decision.selected_format == "netcdf"
    assert outcome.extractor is not None
    assert outcome.extractor.extractor_id == "netcdf_cf_deterministic_extractor"
    assert outcome.schema is not None
    assert outcome.schema.metadata["backend"] == "scipy.io.netcdf_file"
    assert outcome.schema.metadata["dimensions"]["time"]["size"] == 3
    assert outcome.schema.metadata["dimensions"]["time"]["source_evidence"]

    fields = {field.field_name: field for field in outcome.schema.fields}
    assert fields["time"].physical_type != "datetime"
    assert fields["time"].logical_type == "time_axis"
    assert fields["temperature"].shape == [3, 2, 2]
    assert fields["temperature"].semantic_type == "air_temperature"
    assert fields["temperature"].unit_normalization["status"] == "normalized_ucum"
    assert any(item.evidence_type == "netcdf_variable" for item in fields["temperature"].source_evidence)

    analyses = {
        item["field_path"]: item
        for item in outcome.schema.metadata["cf_analysis"]["variables"]
    }
    assert {"dimension_coordinate", "axis_t", "standard_time"}.issubset(
        analyses["time"]["coordinate_roles"]
    )
    assert outcome.schema.metadata["time_series"]["time_axis"]["timezone"] == "UTC"


def test_netcdf_hdf5_backend_preserves_groups_and_paths():
    outcome = _extract("grouped_netcdf4.nc")

    assert outcome.status == "success"
    assert outcome.schema is not None
    assert outcome.schema.metadata["backend"] == "h5py_netcdf4_compatible"
    assert any(
        group["path"] == "/observations" and group["source_evidence"]
        for group in outcome.schema.groups
    )
    assert {field.field_path for field in outcome.schema.fields} == {
        "/observations/time",
        "/observations/temperature",
    }
    analyses = {
        item["field_path"]: item
        for item in outcome.schema.metadata["cf_analysis"]["variables"]
    }
    assert "dimension_coordinate" in analyses["/observations/time"]["coordinate_roles"]
    assert "dimension_coordinate" not in analyses["/observations/temperature"]["coordinate_roles"]


def test_netcdf_fill_and_missing_markers_are_auditable():
    outcome = _extract("missing_markers.nc")

    assert outcome.schema is not None
    field = outcome.schema.fields[0]
    assert field.nullable is True
    assert field.missing_count == 1
    assert any("_FillValue" in item.detail for item in field.source_evidence)
    assert any("missing_value" in item.detail for item in field.source_evidence)


def test_netcdf_multiple_time_candidates_abstain():
    outcome = _extract("multiple_time_variables.nc")

    assert outcome.schema is not None
    assert "time_series" not in outcome.schema.metadata
    assert {
        field.logical_type
        for field in outcome.schema.fields
        if field.field_name in {"time", "forecast_time"}
    } == {"temporal_coordinate"}
    assert outcome.schema.metadata["cf_analysis"]["temporal"]["selection"]["selected_candidate"] is None
    assert outcome.schema.metadata["cf_analysis"]["issues"][0]["code"] == "ambiguous_cf_time_candidates"


def test_netcdf_cdf_suffix_routes_to_registry(tmp_path):
    source = CHALLENGE_ROOT / "standard_coordinates.nc"
    path = tmp_path / "standard_coordinates.cdf"
    path.write_bytes(source.read_bytes())

    outcome = extract_path(ExtractionRequest(str(path)))

    assert outcome.status == "success"
    assert outcome.format_decision.selected_format == "netcdf"


def test_generic_hdf5_renamed_nc_is_not_promoted_to_netcdf(tmp_path):
    path = tmp_path / "generic.nc"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("value", data=[1, 2, 3])

    outcome = extract_path(ExtractionRequest(str(path)))

    assert outcome.status == "success"
    assert outcome.format_decision.selected_format == "hdf5"
    assert outcome.extractor is not None
    assert outcome.extractor.extractor_id == "h5py_structure_traversal"


def test_generic_cli_extracts_netcdf(monkeypatch, capsys):
    path = CHALLENGE_ROOT / "standard_coordinates.nc"
    monkeypatch.setattr(
        sys,
        "argv",
        ["schema-study", "extract", "--input", str(path), "--format", "auto"],
    )

    cli.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "success"
    assert payload["format_decision"]["selected_format"] == "netcdf"
    assert payload["extractor"]["extractor_id"] == "netcdf_cf_deterministic_extractor"
