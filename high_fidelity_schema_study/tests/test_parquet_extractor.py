from __future__ import annotations

import json
import sys
from pathlib import Path

from high_fidelity_schema_study import cli
from high_fidelity_schema_study.extractors.base import ExtractionRequest
from high_fidelity_schema_study.extractors.registry import extract_path
from high_fidelity_schema_study.gui_demo.server import extract_uploaded_schema


ROOT = Path(__file__).resolve().parents[1]
CHALLENGE_ROOT = ROOT / "testdata" / "parquet_phase15a"


def _extract(name: str):
    return extract_path(ExtractionRequest(str(CHALLENGE_ROOT / name)))


def test_parquet_magic_routes_to_metadata_extractor():
    outcome = _extract("primitives.parquet")

    assert outcome.status == "success"
    assert outcome.format_decision.selected_format == "parquet"
    assert outcome.format_decision.basis == "magic"
    assert outcome.extractor is not None
    assert outcome.extractor.extractor_id == "parquet_arrow_metadata_extractor"
    assert outcome.schema is not None
    assert outcome.schema.metadata["num_rows"] == 4
    assert outcome.schema.metadata["num_row_groups"] == 2
    assert outcome.schema.metadata["value_observation"]["row_values_read"] == 0
    assert "deterministic_profile" not in outcome.schema.metadata


def test_parquet_preserves_arrow_metadata_nullability_and_footer_statistics():
    primitives = _extract("primitives.parquet")
    required = _extract("required_nullable.parquet")

    assert primitives.schema is not None
    assert primitives.schema.metadata["key_value_metadata"]["dataset"] == "phase15a_primitives"
    analysis = {
        item["field_path"]: item
        for item in primitives.schema.metadata["parquet_analysis"]["arrow_fields"]
    }
    assert analysis["id"]["metadata"]["role"] == "identifier"
    assert analysis["id"]["parquet_column"]["physical_type"] == "INT64"
    statistics = primitives.schema.metadata["parquet_analysis"]["row_groups"][0]["columns"][0]["statistics"]
    assert statistics["source"] == "parquet_footer"
    assert statistics["state"] == "observed"

    assert required.schema is not None
    fields = {field.field_path: field for field in required.schema.fields}
    assert fields["required_id"].nullable is False
    assert fields["optional_value"].nullable is True


def test_parquet_nested_arrow_and_physical_paths_are_both_retained():
    outcome = _extract("nested_struct_list.parquet")

    assert outcome.schema is not None
    analysis = {
        item["field_path"]: item
        for item in outcome.schema.metadata["parquet_analysis"]["arrow_fields"]
    }
    assert analysis["profile"]["container"] is True
    assert analysis["profile.tags.element"]["nullable"] is False
    mapping = analysis["profile.tags.element"]["physical_path_mapping"]
    assert mapping["arrow_path"] == "profile.tags.element"
    assert mapping["parquet_path"] == "profile.tags.list.element"
    assert mapping["state"] == "derived"


def test_parquet_timestamp_timezone_and_absent_statistics_are_explicit():
    timestamps = _extract("timestamps.parquet")
    no_statistics = _extract("no_statistics.parquet")

    assert timestamps.schema is not None
    analysis = {
        item["field_path"]: item
        for item in timestamps.schema.metadata["parquet_analysis"]["arrow_fields"]
    }
    assert analysis["event_time"]["temporal_claim"]["timezone"] == "UTC"
    assert analysis["local_time"]["temporal_claim"]["timezone"] == "unknown"
    assert all(field.semantic_type == "unknown" for field in timestamps.schema.fields)

    assert no_statistics.schema is not None
    groups = no_statistics.schema.metadata["parquet_analysis"]["row_groups"]
    assert groups[0]["columns"][0]["statistics"]["state"] == "unknown"
    assert groups[0]["columns"][0]["statistics"]["reason_code"] == "footer_statistics_absent"


def test_parquet_footer_statistics_decode_failure_preserves_raw_values():
    class Statistics:
        has_min_max = True
        min_raw = 1
        max_raw = 2
        null_count = 0
        distinct_count = None
        num_values = 2
        physical_type = "INT64"

        @property
        def min(self):
            raise RuntimeError("timezone database unavailable")

        @property
        def max(self):
            raise RuntimeError("timezone database unavailable")

    class Column:
        statistics = Statistics()

    from high_fidelity_schema_study.extractors.parquet_extractor import _statistics

    result = _statistics(Column())

    assert result["state"] == "observed"
    assert result["min_raw"] == 1
    assert result["max_raw"] == 2
    assert result["min_max_representation"] == "raw_physical_values"
    assert result["decode_issue"]["code"] == "footer_statistics_decode_unavailable"


def test_generic_cli_and_gui_extract_parquet(monkeypatch, capsys):
    path = CHALLENGE_ROOT / "primitives.parquet"
    monkeypatch.setattr(sys, "argv", ["schema-study", "extract", "--input", str(path), "--format", "auto"])

    cli.main()
    payload = json.loads(capsys.readouterr().out)
    gui = extract_uploaded_schema(path, "primitives.parquet", "auto")

    assert payload["status"] == "success"
    assert payload["extractor"]["extractor_id"] == "parquet_arrow_metadata_extractor"
    assert gui["detected_mode"] == "parquet"
    assert "without reading row values" in gui["runtime_notes"][-1]
