from __future__ import annotations

import json
import sys
from pathlib import Path

from high_fidelity_schema_study import cli
from high_fidelity_schema_study.extractors.base import ExtractionRequest
from high_fidelity_schema_study.extractors.registry import extract_path
from high_fidelity_schema_study.gui_demo.server import extract_uploaded_schema


ROOT = Path(__file__).resolve().parents[1]
CHALLENGE_ROOT = ROOT / "testdata" / "json_phase16a"


def _extract(name: str, sample_limit: int = 200):
    return extract_path(ExtractionRequest(str(CHALLENGE_ROOT / name), sample_limit=sample_limit))


def test_json_observed_paths_missingness_and_nullability_are_bounded():
    outcome = _extract("records_missing_null.json")

    assert outcome.status == "success"
    assert outcome.extractor is not None
    assert outcome.extractor.extractor_id == "json_bounded_structure_extractor"
    assert outcome.schema is not None
    fields = {field.field_path: field for field in outcome.schema.fields}
    observed = {
        item["field_path"]: item
        for item in outcome.schema.metadata["json_analysis"]["observed_fields"]
    }
    assert observed["$.value"]["observed_types"] == ["null", "number"]
    assert observed["$.value"]["missing_count"] == 1
    assert fields["$.value"].nullable is True
    assert fields["$.id"].semantic_type == "unknown"
    assert fields["$.id"].uncertainty_reason == "sample_bounded_observation"


def test_json_heterogeneous_array_and_nested_paths_are_explicit():
    outcome = _extract("heterogeneous_arrays.json")

    assert outcome.schema is not None
    observed = {
        item["field_path"]: item
        for item in outcome.schema.metadata["json_analysis"]["observed_fields"]
    }
    assert observed["$.items"]["array"]["heterogeneous"] is True
    assert observed["$.items"]["array"]["element_types"] == ["integer", "null", "object", "string"]
    assert "$.items[].nested" in observed


def test_json_schema_declarations_and_example_conflict_remain_separate():
    outcome = _extract("declared_schema.json")

    assert outcome.schema is not None
    analysis = outcome.schema.metadata["json_analysis"]
    declared = {item["field_path"]: item for item in analysis["declared_fields"]}
    assert analysis["mode"] == "declared_json_schema"
    assert declared["$.id"]["required"] is True
    assert declared["$.value"]["required"] is False
    assert analysis["conflicts"] == [
        {
            "field_path": "$.value",
            "code": "declared_observed_type_conflict",
            "declared_types": ["null", "number"],
            "observed_types": ["number", "string"],
            "evidence_refs": ["json_schema:$.value", "json_sample:$.value"],
        }
    ]
    assert all(field.extraction_method == "json_schema_declaration" for field in outcome.schema.fields)


def test_json_lines_sampling_is_structured():
    outcome = _extract("sampled.jsonl", sample_limit=3)

    assert outcome.status == "success"
    assert outcome.schema is not None
    assert outcome.schema.metadata["sampling"]["sample_truncated"] is True
    assert outcome.schema.metadata["sampling"]["observed_record_count"] == 3
    assert outcome.schema.metadata["sampling"]["known_total_record_count"] == 6
    assert {issue.code for issue in outcome.issues} == {"sampling_insufficient"}


def test_malformed_json_is_structured_parser_failure(tmp_path):
    path = tmp_path / "malformed.json"
    path.write_text("{not-json}\n", encoding="utf-8")

    outcome = extract_path(ExtractionRequest(str(path)))

    assert outcome.status == "failed"
    assert outcome.format_decision.selected_format == "json"
    assert outcome.issues[0].code == "parser_error"


def test_generic_cli_and_gui_extract_json(monkeypatch, capsys):
    path = CHALLENGE_ROOT / "single_object.json"
    monkeypatch.setattr(sys, "argv", ["schema-study", "extract", "--input", str(path), "--format", "auto"])

    cli.main()
    payload = json.loads(capsys.readouterr().out)
    gui = extract_uploaded_schema(path, "single_object.json", "auto")

    assert payload["status"] == "success"
    assert payload["extractor"]["extractor_id"] == "json_bounded_structure_extractor"
    assert gui["detected_mode"] == "json"
    assert "bounded JSON structure" in gui["runtime_notes"][-1]
