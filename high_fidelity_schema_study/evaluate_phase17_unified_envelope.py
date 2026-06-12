from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .extractors.base import ExtractionRequest
from .extractors.registry import extract_path
from .unified_schema import CLAIM_STATES, build_unified_schema_envelope


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "experiments" / "phase17_unified_schema_envelope"
CASES = [
    ("csv", "testdata/temporal_phase12/utc_z_regular.csv"),
    ("hdf5", "data/raw/hdf5/hdf5_easy_climate_cube/climate_cube.h5"),
    ("netcdf", "testdata/netcdf_cf_phase13/standard_coordinates.nc"),
    ("zarr", "testdata/zarr_phase14a/basic_array.zarr"),
    ("parquet", "testdata/parquet_phase15a/primitives.parquet"),
    ("json", "testdata/json_phase16a/declared_schema.json"),
    ("xml", "testdata/xml_phase16b/xsi_conflict.xml"),
    ("raw_binary", "testdata/temporal_phase12/opaque.bin"),
]
REQUIRED_SECTIONS = {
    "identity",
    "format_detection",
    "extractor_capability",
    "outcome",
    "physical_structure",
    "logical_roles",
    "semantic_hints",
    "units",
    "temporal_semantics",
    "relationships",
    "claims",
    "evidence",
    "provenance",
    "conflicts",
    "abstentions",
    "unsupported_features",
    "evaluation_metadata",
}


def _ratio(hit: int, total: int) -> float:
    return round(hit / total, 4) if total else 0.0


def evaluate_phase17() -> Dict[str, Any]:
    counters = {key: [0, 0] for key in (
        "sections", "identity", "format", "capability", "physical", "states",
        "evidence", "provenance", "conflict", "abstention", "compatibility",
    )}
    cases = []

    def check(name: str, value: bool) -> bool:
        counters[name][0] += int(value)
        counters[name][1] += 1
        return value

    for expected_format, relative_path in CASES:
        outcome = extract_path(ExtractionRequest(str((ROOT / relative_path).resolve())))
        before = outcome.to_dict()
        envelope = build_unified_schema_envelope(outcome)
        after = outcome.to_dict()
        evidence_ids = {item["evidence_id"] for item in envelope["evidence"]}
        accepted_claims = [
            claim
            for claim in envelope["claims"]
            if claim["state"] in {"observed", "declared", "derived", "supported"}
        ]
        checks = {
            "sections": check("sections", REQUIRED_SECTIONS.issubset(envelope)),
            "identity": check(
                "identity",
                envelope["identity"]["file_format"] == (before.get("schema") or {}).get("file_format"),
            ),
            "format": check(
                "format",
                envelope["format_detection"]["selected_format"] == before["format_decision"]["selected_format"],
            ),
            "capability": check(
                "capability",
                bool(envelope["extractor_capability"]) == (before["status"] != "abstained"),
            ),
            "physical": check(
                "physical",
                envelope["physical_structure"]["fields"] == (before.get("schema") or {}).get("fields", []),
            ),
            "states": check(
                "states",
                all(claim["state"] in CLAIM_STATES for claim in envelope["claims"]),
            ),
            "evidence": check(
                "evidence",
                all(
                    claim.get("evidence_refs")
                    and all(ref in evidence_ids for ref in claim["evidence_refs"])
                    for claim in accepted_claims
                ),
            ),
            "provenance": check(
                "provenance",
                envelope["provenance"]["transformation"] == "deterministic_unified_envelope_projection",
            ),
            "compatibility": check("compatibility", before == after),
        }
        if expected_format in {"json", "xml"}:
            checks["conflict"] = check("conflict", bool(envelope["conflicts"]))
        if expected_format == "raw_binary":
            checks["abstention"] = check(
                "abstention",
                envelope["outcome"]["status"] == "abstained" and bool(envelope["abstentions"]),
            )
        cases.append(
            {
                "case_id": expected_format,
                "source": relative_path,
                "checks": checks,
                "envelope": envelope,
            }
        )

    return {
        "experiment_id": "phase17_unified_schema_envelope",
        "schema_envelope_version": "1.0.0",
        "metrics": {
            "case_count": len(cases),
            "section_completeness": _ratio(*counters["sections"]),
            "identity_accuracy": _ratio(*counters["identity"]),
            "format_projection_accuracy": _ratio(*counters["format"]),
            "capability_or_abstention_accuracy": _ratio(*counters["capability"]),
            "physical_structure_fidelity": _ratio(*counters["physical"]),
            "claim_state_validity": _ratio(*counters["states"]),
            "claim_evidence_integrity": _ratio(*counters["evidence"]),
            "provenance_completeness": _ratio(*counters["provenance"]),
            "conflict_projection_accuracy": _ratio(*counters["conflict"]),
            "abstention_projection_accuracy": _ratio(*counters["abstention"]),
            "legacy_outcome_immutability": _ratio(*counters["compatibility"]),
        },
        "claim_state_vocabulary": CLAIM_STATES,
        "cases": cases,
        "notes": [
            "The unified envelope is an additive deterministic projection over legacy outcomes.",
            "Legacy ExtractionOutcome.schema remains authoritative and unchanged.",
            "The envelope does not promote new semantic truth.",
        ],
    }


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Phase 17 Unified Schema Envelope",
        "",
        "Additive cross-format projection over legacy extraction outcomes.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["metrics"].items():
        lines.append(f"| {key} | {value:.4f} |" if isinstance(value, float) else f"| {key} | {value} |")
    lines.extend(["", "## Claim State Vocabulary", "", ", ".join(f"`{item}`" for item in report["claim_state_vocabulary"])])
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


def write_phase17_artifacts(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    report = report or evaluate_phase17()
    envelopes = output_root / "envelopes"
    envelopes.mkdir(parents=True, exist_ok=True)
    for case in report["cases"]:
        (envelopes / f"{case['case_id']}.json").write_text(
            json.dumps(case["envelope"], indent=2) + "\n", encoding="utf-8"
        )
    summary = {key: value for key, value in report.items() if key != "cases"}
    summary["cases"] = [
        {key: value for key, value in case.items() if key != "envelope"}
        for case in report["cases"]
    ]
    (output_root / "report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output_root / "report.md").write_text(_markdown(report), encoding="utf-8")
    return report
