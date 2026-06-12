from __future__ import annotations

import json
import sys
from pathlib import Path

from high_fidelity_schema_study import cli
from high_fidelity_schema_study.extractors.base import ExtractionRequest
from high_fidelity_schema_study.extractors.registry import extract_path
from high_fidelity_schema_study.gui_demo.server import extract_uploaded_schema


ROOT = Path(__file__).resolve().parents[1]
CHALLENGE_ROOT = ROOT / "testdata" / "xml_phase16b"


def _extract(name: str, sample_limit: int = 200):
    return extract_path(ExtractionRequest(str(CHALLENGE_ROOT / name), sample_limit=sample_limit))


def test_xml_observed_elements_attributes_and_repetition_are_bounded():
    outcome = _extract("basic.xml")

    assert outcome.status == "success"
    assert outcome.extractor is not None
    assert outcome.extractor.extractor_id == "xml_xsd_bounded_structure_extractor"
    assert outcome.schema is not None
    observed = {
        item["field_path"]: item
        for item in outcome.schema.metadata["xml_analysis"]["observed_fields"]
    }
    assert observed["/catalog/item"]["repeated"] is True
    assert observed["/catalog/item"]["max_sibling_occurs"] == 2
    assert observed["/catalog/item/@id"]["observed_types"] == ["string"]
    assert observed["/catalog/item/value"]["observed_types"] == ["integer", "number"]
    assert all(field.semantic_type == "unknown" for field in outcome.schema.fields)


def test_xml_namespaces_use_portable_clark_paths():
    outcome = _extract("namespaced.xml")

    assert outcome.schema is not None
    analysis = outcome.schema.metadata["xml_analysis"]
    assert set(analysis["namespaces"].values()) == {"urn:example:observations", "urn:example:geo"}
    assert any(
        field.field_path.endswith("/@{urn:example:geo}station")
        for field in outcome.schema.fields
    )


def test_xsd_declarations_do_not_leak_nested_attributes_to_parent():
    outcome = _extract("schema.xsd")

    assert outcome.schema is not None
    analysis = outcome.schema.metadata["xml_analysis"]
    declared = {item["field_path"]: item for item in analysis["declared_fields"]}
    assert analysis["mode"] == "declared_xsd"
    assert "/catalog/@id" not in declared
    assert declared["/catalog/item"]["max_occurs"] == "unbounded"
    assert declared["/catalog/item/@id"]["required"] is True
    assert all(field.extraction_method == "xsd_declaration" for field in outcome.schema.fields)


def test_xsi_type_conflict_is_explicit_and_does_not_promote():
    outcome = _extract("xsi_conflict.xml")

    assert outcome.schema is not None
    analysis = outcome.schema.metadata["xml_analysis"]
    assert analysis["conflicts"][0]["code"] == "declared_observed_type_conflict"
    assert analysis["conflicts"][0]["declared_type"] == "xs:int"
    assert analysis["conflicts"][0]["observed_type"] == "string"
    assert all(field.semantic_type == "unknown" for field in outcome.schema.fields)


def test_xml_sampling_and_malformed_failure_are_structured(tmp_path):
    sampled = _extract("sampled.xml", sample_limit=4)
    malformed_path = tmp_path / "broken.xml"
    malformed_path.write_text("<root><broken></root>\n", encoding="utf-8")
    malformed = extract_path(ExtractionRequest(str(malformed_path)))

    assert sampled.schema is not None
    assert sampled.schema.metadata["sampling"]["sample_truncated"] is True
    assert {issue.code for issue in sampled.issues} == {"sampling_insufficient"}
    assert malformed.status == "failed"
    assert malformed.issues[0].code == "parser_error"


def test_generic_cli_and_gui_extract_xml(monkeypatch, capsys):
    path = CHALLENGE_ROOT / "basic.xml"
    monkeypatch.setattr(sys, "argv", ["schema-study", "extract", "--input", str(path), "--format", "auto"])

    cli.main()
    payload = json.loads(capsys.readouterr().out)
    gui = extract_uploaded_schema(path, "basic.xml", "auto")

    assert payload["status"] == "success"
    assert payload["extractor"]["extractor_id"] == "xml_xsd_bounded_structure_extractor"
    assert gui["detected_mode"] == "xml"
    assert "bounded XML structure" in gui["runtime_notes"][-1]
