import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.extractors.registry import EXTRACTOR_RUNNERS
from high_fidelity_schema_study.gui_demo.server import (
    HDF5_MAGIC,
    build_raw_binary_schema,
    detect_upload_mode,
    extract_uploaded_schema,
    json_safe,
    extract_demo_example,
    load_demo_examples,
    materialize_uploaded_resource,
    normalize_upload_relative_path,
    parse_multipart_form,
)


ROOT = Path(__file__).resolve().parents[1]


def test_detect_upload_mode_prefers_hdf5_magic():
    assert detect_upload_mode("payload.bin", "auto", HDF5_MAGIC + b"rest") == "hdf5"


def test_detect_upload_mode_recognizes_netcdf_suffix():
    assert detect_upload_mode("payload.nc", "auto", HDF5_MAGIC + b"rest") == "netcdf"


def test_detect_upload_mode_recognizes_parquet_magic():
    assert detect_upload_mode("payload.bin", "auto", b"PAR1rest") == "parquet"


def test_detect_upload_mode_recognizes_json_lines_suffix():
    assert detect_upload_mode("payload.jsonl", "auto", b'{"id": 1}\n') == "json"


def test_detect_upload_mode_recognizes_xsd_suffix():
    assert detect_upload_mode("schema.xsd", "auto", b"<xs:schema/>") == "xml"


def test_raw_binary_schema_abstains_from_field_claims(tmp_path):
    path = tmp_path / "opaque.bin"
    payload = b"\x00\x01opaque"
    path.write_bytes(payload)

    schema = build_raw_binary_schema(path, "opaque.bin", payload)

    assert schema.file_format == "raw_binary"
    assert schema.fields == []
    assert schema.metadata["field_claim_policy"] == "abstain_without_sidecar_metadata"
    assert "underdetermined" in schema.notes[0]


def test_extract_uploaded_timeseries_csv_uses_existing_profiler(tmp_path):
    path = tmp_path / "series.csv"
    path.write_text(
        "ts_utc,sensor_id,temp_c\n"
        "2026-01-01T00:00:00,A,10.0\n"
        "2026-01-01T01:00:00,A,11.0\n"
        "2026-01-01T02:00:00,A,12.0\n",
        encoding="utf-8",
    )

    result = extract_uploaded_schema(path, "series.csv", "timeseries", sample_limit=10)
    schema = result["schema"]

    assert result["detected_mode"] == "timeseries"
    assert result["extraction_outcome"]["status"] == "success"
    assert result["extraction_outcome"]["extractor"]["extractor_id"] == "csv_conservative_profiler"
    assert schema["file_format"] == "csv"
    assert schema["data_modality"] == "time_series"
    assert schema["metadata"]["time_series"]["time_axis"]["field"] == "ts_utc"
    assert any(field["field_name"] == "temp_c" for field in schema["fields"])


def test_extract_uploaded_binary_preserves_legacy_schema_and_adds_outcome(tmp_path):
    path = tmp_path / "opaque.bin"
    path.write_bytes(b"\x00\x01opaque")

    result = extract_uploaded_schema(path, "opaque.bin", "auto")

    assert result["detected_mode"] == "binary"
    assert result["schema"]["fields"] == []
    assert result["schema"]["metadata"]["field_claim_policy"] == "abstain_without_sidecar_metadata"
    assert result["extraction_outcome"]["status"] == "abstained"
    assert result["extraction_outcome"]["issues"][0]["code"] == "unknown_no_signature"


def test_extract_uploaded_dependency_failure_preserves_structured_outcome(tmp_path, monkeypatch):
    path = tmp_path / "payload.h5"
    path.write_bytes(HDF5_MAGIC + b"rest")

    def unavailable(_request):
        raise RuntimeError("h5py is required for HDF5 extraction")

    monkeypatch.setitem(EXTRACTOR_RUNNERS, "hdf5", unavailable)
    result = extract_uploaded_schema(path, "payload.h5", "auto")

    assert result["ok"] is False
    assert result["schema"] is None
    assert result["detected_mode"] == "hdf5"
    assert result["extraction_outcome"]["status"] == "failed"
    assert result["extraction_outcome"]["extractor"]["extractor_id"] == "h5py_structure_traversal"
    assert result["extraction_outcome"]["issues"][0]["code"] == "dependency_unavailable"
    assert result["unified_schema_envelope"]["outcome"]["status"] == "failed"
    assert "h5py is required" in result["error"]


def test_extract_uploaded_netcdf_uses_registry():
    path = (
        Path(__file__).resolve().parents[1]
        / "testdata"
        / "netcdf_cf_phase13"
        / "standard_coordinates.nc"
    )

    result = extract_uploaded_schema(path, "standard_coordinates.nc", "auto")

    assert result["detected_mode"] == "netcdf"
    assert result["extraction_outcome"]["status"] == "success"
    assert result["extraction_outcome"]["extractor"]["extractor_id"] == "netcdf_cf_deterministic_extractor"
    assert result["schema"]["metadata"]["time_series"]["time_axis"]["field"] == "time"


def test_extract_uploaded_zarr_directory_uses_registry():
    path = Path(__file__).resolve().parents[1] / "testdata" / "zarr_phase14a" / "basic_array.zarr"

    result = extract_uploaded_schema(path, "basic_array.zarr", "auto")

    assert result["detected_mode"] == "zarr"
    assert result["extraction_outcome"]["status"] == "success"
    assert result["extraction_outcome"]["extractor"]["extractor_id"] == "zarr_v2_metadata_extractor"
    assert result["schema"]["fields"][0]["field_path"] == "temperature"


def test_materialize_uploaded_zarr_directory_preserves_safe_relative_paths(tmp_path):
    uploads = [
        ("sample.zarr/.zgroup", b'{"zarr_format": 2}'),
        (
            "sample.zarr/value/.zarray",
            b'{"zarr_format":2,"shape":[3],"chunks":[3],"dtype":"<f4","compressor":null,"fill_value":null,"order":"C","filters":null}',
        ),
    ]

    path, name = materialize_uploaded_resource(tmp_path, uploads)

    assert name == "sample.zarr"
    assert path == tmp_path / "upload_store" / "sample.zarr"
    assert (path / "value" / ".zarray").exists()


def test_parse_multipart_form_preserves_multiple_zarr_metadata_files():
    boundary = "phase14a-boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="mode"\r\n\r\n'
        "auto\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="sample.zarr/.zgroup"\r\n'
        "Content-Type: application/json\r\n\r\n"
        '{"zarr_format": 2}\r\n'
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="sample.zarr/value/.zarray"\r\n'
        "Content-Type: application/json\r\n\r\n"
        '{"zarr_format": 2, "shape": [1]}\r\n'
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    fields, uploads = parse_multipart_form(body, f"multipart/form-data; boundary={boundary}")

    assert fields == {"mode": "auto"}
    assert [name for name, _payload in uploads] == [
        "sample.zarr/.zgroup",
        "sample.zarr/value/.zarray",
    ]


def test_upload_relative_path_rejects_traversal():
    try:
        normalize_upload_relative_path("../escape/.zgroup")
    except ValueError as exc:
        assert "invalid relative path" in str(exc)
    else:
        raise AssertionError("path traversal must be rejected")


def test_json_safe_normalizes_hdf5_byte_attributes():
    payload = {"attrs": {"flag_values": [b"clear", b"cloudy"], "scalar": b"ok"}}

    assert json_safe(payload) == {"attrs": {"flag_values": ["clear", "cloudy"], "scalar": "ok"}}


def test_demo_examples_are_allowlisted_portable_and_extractable():
    examples = load_demo_examples()

    assert {item["format"] for item in examples} == {
        "csv", "raw_binary", "netcdf", "hdf5", "zarr", "parquet", "json", "xml"
    }
    for example in examples:
        result = extract_demo_example(example["id"])
        assert result["example"]["id"] == example["id"]
        assert result["extraction_outcome"]["status"] in {"success", "abstained"}
        assert Path(example["path"]).is_absolute() is False


def test_demo_example_manifest_hashes_match_payloads():
    payload = json.loads((ROOT / "demo_examples" / "manifest.json").read_text(encoding="utf-8"))

    for example in payload["examples"]:
        path = ROOT / "demo_examples" / example["path"]
        if path.is_file():
            assert hashlib.sha256(path.read_bytes()).hexdigest() == example["sha256"]
            continue
        for relative_path, expected in example["sha256_files"].items():
            assert hashlib.sha256((path / relative_path).read_bytes()).hexdigest() == expected


def test_unknown_demo_example_is_rejected():
    with pytest.raises(ValueError, match="Unknown demo example"):
        extract_demo_example("not-allowlisted")
