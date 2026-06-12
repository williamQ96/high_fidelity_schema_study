from __future__ import annotations

from high_fidelity_schema_study.models import FieldSchema
from high_fidelity_schema_study.temporal_semantics import analyze_temporal_semantics


def _fields(*names: str) -> list[FieldSchema]:
    fields = []
    for name in names:
        physical_type = "datetime" if "time" in name else "float"
        fields.append(FieldSchema(field_name=name, field_path=name, physical_type=physical_type))
    return fields


def test_explicit_utc_is_supported():
    result = analyze_temporal_semantics(
        {
            "ts_utc": ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z", "2026-01-01T02:00:00Z"],
            "value": ["1", "2", "3"],
        },
        _fields("ts_utc", "value"),
    )

    assert result["time_series"]["time_axis"]["timezone"] == "UTC"
    assert result["temporal_analysis"]["property_claims"]["timezone"]["state"] == "supported"


def test_naive_timezone_stays_unknown():
    result = analyze_temporal_semantics(
        {
            "timestamp": ["2026-01-01 00:00:00", "2026-01-01 01:00:00", "2026-01-01 02:00:00"],
            "value": ["1", "2", "3"],
        },
        _fields("timestamp", "value"),
    )

    claim = result["temporal_analysis"]["property_claims"]["timezone"]
    assert result["time_series"]["time_axis"]["timezone"] == "unknown"
    assert claim["state"] == "unknown"
    assert claim["reason_code"] == "timezone_not_encoded_in_values"


def test_mixed_offsets_surface_conflict():
    result = analyze_temporal_semantics(
        {
            "event_time": ["2026-01-01T00:00:00Z", "2026-01-01T02:00:00+01:00"],
            "value": ["1", "2"],
        },
        _fields("event_time", "value"),
    )

    claim = result["temporal_analysis"]["property_claims"]["timezone"]
    assert claim["state"] == "conflicted"
    assert claim["reason_code"] == "conflicting_timezone_offsets"


def test_equal_time_candidates_abstain_from_axis_selection():
    result = analyze_temporal_semantics(
        {
            "event_time": ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"],
            "ingest_time": ["2026-01-01T00:01:00Z", "2026-01-01T01:01:00Z"],
            "value": ["1", "2"],
        },
        _fields("event_time", "ingest_time", "value"),
    )

    assert result["time_series"] == {}
    assert result["temporal_analysis"]["selected_candidate"] is None
    assert result["temporal_analysis"]["issues"][0]["code"] == "ambiguous_time_axis_candidates"
