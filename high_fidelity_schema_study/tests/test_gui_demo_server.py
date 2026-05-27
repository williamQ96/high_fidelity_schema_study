from high_fidelity_schema_study.gui_demo.server import (
    HDF5_MAGIC,
    build_raw_binary_schema,
    detect_upload_mode,
    extract_uploaded_schema,
    json_safe,
)


def test_detect_upload_mode_prefers_hdf5_magic():
    assert detect_upload_mode("payload.bin", "auto", HDF5_MAGIC + b"rest") == "hdf5"


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
    assert schema["file_format"] == "csv"
    assert schema["data_modality"] == "time_series"
    assert schema["metadata"]["time_series"]["time_axis"]["field"] == "ts_utc"
    assert any(field["field_name"] == "temp_c" for field in schema["fields"])


def test_json_safe_normalizes_hdf5_byte_attributes():
    payload = {"attrs": {"flag_values": [b"clear", b"cloudy"], "scalar": b"ok"}}

    assert json_safe(payload) == {"attrs": {"flag_values": ["clear", "cloudy"], "scalar": "ok"}}
