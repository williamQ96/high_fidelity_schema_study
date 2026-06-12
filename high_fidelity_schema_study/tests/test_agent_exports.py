from __future__ import annotations

import json
import sys
from pathlib import Path

from high_fidelity_schema_study import cli
from high_fidelity_schema_study.agent_exports import export_agent_bundle, export_capability_registry
from high_fidelity_schema_study.extractors.base import ExtractionRequest
from high_fidelity_schema_study.extractors.registry import extract_unified


ROOT = Path(__file__).resolve().parents[1]


def test_agent_bundle_is_read_only_and_claim_faithful():
    envelope = extract_unified(
        ExtractionRequest(str(ROOT / "testdata" / "json_phase16a" / "declared_schema.json"))
    )

    bundle = export_agent_bundle(envelope)

    assert bundle["policy"]["canonical_mutation_allowed"] is False
    assert bundle["policy"]["silent_claim_promotion_allowed"] is False
    assert bundle["claim_records"] == envelope["claims"]
    assert bundle["retrieval_context"]["conflicts"] == envelope["conflicts"]
    assert all(item["effect"] != "canonical_mutation" for item in bundle["requestable_actions"])


def test_capability_export_is_complete_and_nonpromoting():
    registry = export_capability_registry()

    assert len(registry["capabilities"]) == 7
    assert registry["policy"]["agent_can_register_or_promote_claims"] is False
    assert {item["formats"][0] for item in registry["capabilities"]} == {
        "csv", "hdf5", "json", "netcdf", "parquet", "xml", "zarr"
    }


def test_agent_export_cli(monkeypatch, capsys):
    path = ROOT / "testdata" / "xml_phase16b" / "basic.xml"
    monkeypatch.setattr(sys, "argv", ["schema-study", "agent-export", "--input", str(path)])

    cli.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["schema_summary"]["identity"]["file_format"] == "xml"
    assert payload["policy"]["canonical_mutation_allowed"] is False
