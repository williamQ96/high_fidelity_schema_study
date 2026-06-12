from __future__ import annotations

import json
import sys
from pathlib import Path

from high_fidelity_schema_study import cli
from high_fidelity_schema_study.extractors.base import ExtractionRequest
from high_fidelity_schema_study.extractors.registry import extract_path, extract_unified
from high_fidelity_schema_study.gui_demo.server import extract_uploaded_schema
from high_fidelity_schema_study.unified_schema import CLAIM_STATES, build_unified_schema_envelope


ROOT = Path(__file__).resolve().parents[1]


def test_unified_envelope_is_additive_and_evidence_integral():
    path = ROOT / "testdata" / "parquet_phase15a" / "primitives.parquet"
    outcome = extract_path(ExtractionRequest(str(path)))
    before = outcome.to_dict()

    envelope = build_unified_schema_envelope(outcome)

    assert outcome.to_dict() == before
    assert envelope["schema_envelope_version"] == "1.0.0"
    assert envelope["identity"]["file_format"] == "parquet"
    assert envelope["physical_structure"]["fields"] == before["schema"]["fields"]
    assert set(envelope["evaluation_metadata"]["claim_state_vocabulary"]) == set(CLAIM_STATES)
    evidence_ids = {item["evidence_id"] for item in envelope["evidence"]}
    assert all(ref in evidence_ids for claim in envelope["claims"] for ref in claim["evidence_refs"])
    assert all(
        claim["evidence_refs"]
        for claim in envelope["claims"]
        if claim["state"] in {"observed", "declared", "derived", "supported"}
    )


def test_unified_envelope_projects_conflicts_and_abstentions():
    conflict = extract_unified(
        ExtractionRequest(str(ROOT / "testdata" / "xml_phase16b" / "xsi_conflict.xml"))
    )
    abstained = extract_unified(
        ExtractionRequest(str(ROOT / "testdata" / "temporal_phase12" / "opaque.bin"))
    )

    assert conflict["conflicts"]
    assert conflict["outcome"]["status"] == "success"
    assert abstained["outcome"]["status"] == "abstained"
    assert abstained["abstentions"]
    assert abstained["extractor_capability"] is None


def test_cli_output_shapes_preserve_legacy_default(monkeypatch, capsys):
    path = ROOT / "testdata" / "json_phase16a" / "single_object.json"
    monkeypatch.setattr(sys, "argv", ["schema-study", "extract", "--input", str(path)])
    cli.main()
    legacy = json.loads(capsys.readouterr().out)
    monkeypatch.setattr(
        sys,
        "argv",
        ["schema-study", "extract", "--input", str(path), "--output-shape", "both"],
    )
    cli.main()
    both = json.loads(capsys.readouterr().out)

    assert "schema" in legacy
    assert "unified_schema_envelope" not in legacy
    assert both["extraction_outcome"] == legacy
    assert both["unified_schema_envelope"]["identity"]["file_format"] == "json"


def test_gui_adds_unified_envelope_without_removing_legacy_schema():
    path = ROOT / "testdata" / "json_phase16a" / "single_object.json"

    payload = extract_uploaded_schema(path, "single_object.json", "auto")

    assert "schema" in payload
    assert "extraction_outcome" in payload
    assert payload["unified_schema_envelope"]["identity"]["file_format"] == "json"
