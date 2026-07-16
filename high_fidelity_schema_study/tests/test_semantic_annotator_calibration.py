from __future__ import annotations

import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.architecture_variants import ALLOWED_LOGICAL_TYPES
from high_fidelity_schema_study.semantic_annotator_calibration import (
    AnnotatorCalibrationError,
    build_annotator_calibration_summary,
    preflight_annotator_calibration_design,
    sha256_file,
    validate_annotator_calibration_summary,
    write_json,
)
from high_fidelity_schema_study.semantic_gold_workflow import (
    build_annotation_workflow_manifest,
    build_packet_source_bundle,
    compare_independent_artifacts,
)


def vocabulary_payload() -> dict:
    return {
        "schema_version": "semantic-annotation-vocabulary/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "status": "frozen",
        "vocabulary_version": "calibration-test-v1",
        "physical_types": ["float32"],
        "logical_types": sorted(ALLOWED_LOGICAL_TYPES),
        "semantic_types": ["air_temperature", "surface_temperature"],
        "units": ["degree_Celsius"],
        "unit_aliases": {"C": "degree_Celsius"},
        "unit_patterns": [],
        "unknown_representation": None,
    }


def packet_payload(case_id: str) -> dict:
    return {
        "schema_version": "semantic-annotation-packet/v1",
        "purpose": "annotator_calibration",
        "research_evidence_status": "non_blind_not_for_effect_estimation",
        "case_id": case_id,
        "task_id": f"calibration::{case_id}",
        "dataset_id": case_id,
        "file_format": "csv",
        "data_modality": "tabular",
        "field_inventory": [
            {
                "field_name": "temperature",
                "field_path": "temperature",
                "physical_type": "float32",
                "source_evidence": [],
            }
        ],
        "approved_evidence": [
            {
                "evidence_id": "S1",
                "source_type": "approved_documentation",
                "source_name": "README.md",
                "detail": "variables:temperature",
                "text": "temperature is air temperature in degree Celsius",
                "applicable_field_paths": ["temperature"],
            }
        ],
    }


def independent_annotation(
    *,
    case_id: str,
    annotator_id: str,
    submission_id: str,
    packet_path: Path,
    bundle_path: Path,
    vocabulary_path: Path,
    semantic_type: str | None = "air_temperature",
) -> dict:
    packet_hash = sha256_file(packet_path)
    values = {
        "physical_type": "float32",
        "logical_type": "measurement",
        "semantic_type": semantic_type,
        "unit": "degree_Celsius",
    }
    return {
        "schema_version": "blind-semantic-gold/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "dataset_id": case_id,
        "annotation_stage": "independent",
        "annotator_id": annotator_id,
        "submission_id": submission_id,
        "source_bundle_sha256": sha256_file(bundle_path),
        "annotation_packet_sha256": packet_hash,
        "vocabulary_sha256": sha256_file(vocabulary_path),
        "model_outputs_visible": False,
        "developer_participation": False,
        "fields": [
            {
                "field_name": "temperature",
                "field_path": "temperature",
                "correct_physical_type": values["physical_type"],
                "correct_logical_type": values["logical_type"],
                "correct_semantic_type": values["semantic_type"],
                "unit": values["unit"],
                "applicability": {key: True for key in values},
                "rationales": {
                    key: (
                        "Approved evidence does not resolve a canonical semantic label."
                        if key == "semantic_type" and semantic_type is None
                        else None
                    )
                    for key in values
                },
                "gold_evidence": [
                    {
                        "evidence_id": f"{submission_id}-{index}",
                        "catalog_evidence_id": "S1",
                        "property": property_name,
                        "source_type": "approved_documentation",
                        "source_sha256": packet_hash,
                        "selector": "approved_evidence:S1",
                        "field_path": "temperature",
                        "strength": "documentation",
                        "support": f"Documentation supports {property_name}.",
                    }
                    for index, property_name in enumerate(values, start=1)
                    if values[property_name] is not None
                ],
                "notes": None,
            }
        ],
    }


def threshold_policy(*, exact: bool = False) -> dict:
    threshold = 1.0 if exact else 0.8
    return {
        "minimum_case_count": 9,
        "minimum_overall_exact_label_agreement": threshold,
        "minimum_applicability_agreement": 1.0 if exact else 0.9,
        "minimum_case_exact_label_agreement": 1.0 if exact else 0.5,
        "minimum_property_exact_label_agreement": {
            property_name: 1.0 if exact else 0.7
            for property_name in (
                "physical_type",
                "logical_type",
                "semantic_type",
                "unit",
            )
        },
        "evidence_agreement_is_descriptive_only": True,
    }


def build_round(
    root: Path,
    *,
    disagreement_case: str | None = None,
    changed_pair_case: str | None = None,
    exact_thresholds: bool = False,
    vocabulary_path_override: Path | None = None,
    handbook_path_override: Path | None = None,
) -> dict[str, Path]:
    packets_dir = root / "packets"
    bundles_dir = root / "source_bundles"
    submissions_dir = root / "submissions"
    reports_dir = root / "disagreements"
    vocabulary_path = vocabulary_path_override or (root / "vocabulary.json")
    handbook_path = handbook_path_override or (root / "handbook.md")
    calibration_manifest_path = root / "manifest.json"
    workflow_path = root / "annotation_workflow_manifest.json"
    design_path = root / "calibration-design.json"
    receipt_path = root / "registration-receipt.json"
    round_path = root / "calibration-round.json"
    summary_path = root / "calibration-summary.json"
    if vocabulary_path_override is None:
        write_json(vocabulary_path, vocabulary_payload())
    if handbook_path_override is None:
        handbook_path.write_text("# Frozen calibration handbook\n", encoding="utf-8")

    calibration_cases = []
    case_sources = {}
    for index in range(1, 10):
        case_id = f"case-{index}"
        packet_path = packets_dir / f"{case_id}.json"
        bundle_path = bundles_dir / f"{case_id}.source-bundle.json"
        write_json(packet_path, packet_payload(case_id))
        write_json(
            bundle_path,
            build_packet_source_bundle(packet_path, vocabulary_path),
        )
        calibration_cases.append(
            {
                "case_id": case_id,
                "packet_file": f"packets/{packet_path.name}",
                "packet_sha256": sha256_file(packet_path),
            }
        )
        case_sources[case_id] = (packet_path, bundle_path)
    write_json(
        calibration_manifest_path,
        {
            "schema_version": "semantic-calibration-manifest/v1",
            "cases": calibration_cases,
        },
    )
    workflow = build_annotation_workflow_manifest(
        calibration_manifest_path,
        vocabulary_path=vocabulary_path,
        source_bundle_dir=bundles_dir,
        handbook_path=handbook_path,
        output_path=workflow_path,
    )
    write_json(workflow_path, workflow)

    round_cases = []
    for index, case_id in enumerate((f"case-{i}" for i in range(1, 10)), start=1):
        packet_path, bundle_path = case_sources[case_id]
        artifact_a_path = submissions_dir / f"{case_id}.a.json"
        artifact_b_path = submissions_dir / f"{case_id}.b.json"
        disagreement_path = reports_dir / f"{case_id}.json"
        annotator_b = "annotator-c" if case_id == changed_pair_case else "annotator-b"
        vocabulary = json.loads(vocabulary_path.read_text(encoding="utf-8"))
        alternatives = [
            item for item in vocabulary["semantic_types"] if item != "air_temperature"
        ]
        semantic_b = (
            (alternatives[0] if alternatives else None)
            if case_id == disagreement_case
            else "air_temperature"
        )
        write_json(
            artifact_a_path,
            independent_annotation(
                case_id=case_id,
                annotator_id="annotator-a",
                submission_id=f"a-{index}",
                packet_path=packet_path,
                bundle_path=bundle_path,
                vocabulary_path=vocabulary_path,
            ),
        )
        write_json(
            artifact_b_path,
            independent_annotation(
                case_id=case_id,
                annotator_id=annotator_b,
                submission_id=f"b-{index}",
                packet_path=packet_path,
                bundle_path=bundle_path,
                vocabulary_path=vocabulary_path,
                semantic_type=semantic_b,
            ),
        )
        disagreement = compare_independent_artifacts(
            artifact_a_path,
            artifact_b_path,
            packet_path=packet_path,
            source_bundle_path=bundle_path,
            vocabulary_path=vocabulary_path,
        )
        write_json(disagreement_path, disagreement)
        round_cases.append(
            {
                "case_id": case_id,
                "independent_annotations": [
                    {
                        "file": str(artifact_a_path.relative_to(root)),
                        "sha256": sha256_file(artifact_a_path),
                    },
                    {
                        "file": str(artifact_b_path.relative_to(root)),
                        "sha256": sha256_file(artifact_b_path),
                    },
                ],
                "disagreement_report": {
                    "file": str(disagreement_path.relative_to(root)),
                    "sha256": sha256_file(disagreement_path),
                },
            }
        )
    design = {
        "schema_version": "semantic-annotator-calibration-design/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "status": "frozen_before_submissions",
        "round_id": "calibration-round-1",
        "round_index": 1,
        "prior_round_summary": None,
        "workflow_manifest": {
            "file": workflow_path.name,
            "sha256": sha256_file(workflow_path),
        },
        "threshold_policy": threshold_policy(exact=exact_thresholds),
    }
    write_json(design_path, design)
    receipt = {
        "schema_version": "semantic-preregistration-receipt/v1",
        "design_sha256": sha256_file(design_path),
        "registered_at": "2026-07-16T00:00:00Z",
        "registry": "test-fixture-registry",
        "registration_identifier": "fixture-registration-1",
        "frozen_before_first_submission": True,
    }
    write_json(receipt_path, receipt)
    write_json(
        round_path,
        {
            "schema_version": "semantic-annotator-calibration-round/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "submissions_frozen",
            "design": {
                "file": design_path.name,
                "sha256": sha256_file(design_path),
            },
            "registration_receipt": {
                "file": receipt_path.name,
                "sha256": sha256_file(receipt_path),
            },
            "cases": round_cases,
        },
    )
    return {
        "round": round_path,
        "design": design_path,
        "receipt": receipt_path,
        "summary": summary_path,
        "workflow": workflow_path,
    }


def refresh_design_registration(paths: dict[str, Path]) -> None:
    design_hash = sha256_file(paths["design"])
    receipt = json.loads(paths["receipt"].read_text(encoding="utf-8"))
    receipt["design_sha256"] = design_hash
    write_json(paths["receipt"], receipt)
    round_payload = json.loads(paths["round"].read_text(encoding="utf-8"))
    round_payload["design"]["sha256"] = design_hash
    round_payload["registration_receipt"]["sha256"] = sha256_file(paths["receipt"])
    write_json(paths["round"], round_payload)


def test_complete_nine_case_round_passes_and_recalculates(tmp_path: Path) -> None:
    paths = build_round(tmp_path)

    summary = build_annotator_calibration_summary(
        round_manifest_path=paths["round"], output_path=paths["summary"]
    )
    write_json(paths["summary"], summary)

    assert summary["status"] == "passed"
    assert summary["annotator_ids"] == ["annotator-a", "annotator-b"]
    assert summary["metrics"]["case_count"] == 9
    assert summary["metrics"]["exact_label_agreement_rate"] == 1.0
    assert validate_annotator_calibration_summary(paths["summary"])["status"] == "ready"


def test_design_can_be_preflighted_before_receipt_or_submissions(
    tmp_path: Path,
) -> None:
    paths = build_round(tmp_path)

    report = preflight_annotator_calibration_design(paths["design"])

    assert report["status"] == "ready_for_external_registration"
    assert report["errors"] == []
    assert report["design"]["sha256"] == sha256_file(paths["design"])
    assert report["workflow"]["case_count"] == 9
    assert report["not_a_registration_receipt"] is True


def test_invalid_design_is_blocked_before_human_work(tmp_path: Path) -> None:
    paths = build_round(tmp_path)
    design = json.loads(paths["design"].read_text(encoding="utf-8"))
    design["threshold_policy"]["minimum_case_count"] = 8
    write_json(paths["design"], design)

    report = preflight_annotator_calibration_design(paths["design"])

    assert report["status"] == "blocked"
    assert report["errors"][0]["code"] == "annotator_calibration_design_invalid"
    assert "at least 9" in report["errors"][0]["detail"]


def test_gate_can_fail_without_automatic_adjudication(tmp_path: Path) -> None:
    paths = build_round(tmp_path, disagreement_case="case-1", exact_thresholds=True)

    summary = build_annotator_calibration_summary(
        round_manifest_path=paths["round"], output_path=paths["summary"]
    )

    assert summary["status"] == "failed"
    assert any(not item["passed"] for item in summary["gate_checks"])
    assert "new calibration cases" in summary["next_action"]


def test_same_annotator_pair_is_required_for_every_case(tmp_path: Path) -> None:
    paths = build_round(tmp_path, changed_pair_case="case-9")

    with pytest.raises(AnnotatorCalibrationError, match="same two annotators"):
        build_annotator_calibration_summary(
            round_manifest_path=paths["round"], output_path=paths["summary"]
        )


def test_disagreement_report_must_be_exact_rebuild(tmp_path: Path) -> None:
    paths = build_round(tmp_path)
    round_payload = json.loads(paths["round"].read_text(encoding="utf-8"))
    record = round_payload["cases"][0]["disagreement_report"]
    report_path = tmp_path / record["file"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["exact_label_agreement_rate"] = 0.0
    write_json(report_path, report)
    record["sha256"] = sha256_file(report_path)
    write_json(paths["round"], round_payload)

    with pytest.raises(AnnotatorCalibrationError, match="deterministic rebuild"):
        build_annotator_calibration_summary(
            round_manifest_path=paths["round"], output_path=paths["summary"]
        )


def test_thresholds_cannot_be_lowered_below_protocol_floors(tmp_path: Path) -> None:
    paths = build_round(tmp_path)
    design = json.loads(paths["design"].read_text(encoding="utf-8"))
    design["threshold_policy"]["minimum_overall_exact_label_agreement"] = 0.1
    write_json(paths["design"], design)
    refresh_design_registration(paths)

    with pytest.raises(AnnotatorCalibrationError, match=r"\[0.8, 1\]"):
        build_annotator_calibration_summary(
            round_manifest_path=paths["round"], output_path=paths["summary"]
        )


def test_receipt_must_bind_the_exact_preregistered_design(tmp_path: Path) -> None:
    paths = build_round(tmp_path)
    receipt = json.loads(paths["receipt"].read_text(encoding="utf-8"))
    receipt["design_sha256"] = "a" * 64
    write_json(paths["receipt"], receipt)
    round_payload = json.loads(paths["round"].read_text(encoding="utf-8"))
    round_payload["registration_receipt"]["sha256"] = sha256_file(paths["receipt"])
    write_json(paths["round"], round_payload)

    with pytest.raises(AnnotatorCalibrationError, match="design hash"):
        build_annotator_calibration_summary(
            round_manifest_path=paths["round"], output_path=paths["summary"]
        )


def test_failed_round_cases_cannot_be_reused_after_reveal(tmp_path: Path) -> None:
    paths = build_round(tmp_path, disagreement_case="case-1", exact_thresholds=True)
    summary = build_annotator_calibration_summary(
        round_manifest_path=paths["round"], output_path=paths["summary"]
    )
    write_json(paths["summary"], summary)
    design = json.loads(paths["design"].read_text(encoding="utf-8"))
    design["round_id"] = "calibration-round-2"
    design["round_index"] = 2
    design["prior_round_summary"] = {
        "file": paths["summary"].name,
        "sha256": sha256_file(paths["summary"]),
    }
    write_json(paths["design"], design)
    refresh_design_registration(paths)

    with pytest.raises(AnnotatorCalibrationError, match="cannot be reused"):
        build_annotator_calibration_summary(
            round_manifest_path=paths["round"], output_path=paths["summary"]
        )


def test_tampered_summary_fails_self_validation(tmp_path: Path) -> None:
    paths = build_round(tmp_path)
    summary = build_annotator_calibration_summary(
        round_manifest_path=paths["round"], output_path=paths["summary"]
    )
    summary["metrics"]["exact_label_agreement_rate"] = 0.0
    write_json(paths["summary"], summary)

    validation = validate_annotator_calibration_summary(paths["summary"])

    assert validation["status"] == "blocked"
    assert validation["errors"][0]["code"] == (
        "annotator_calibration_summary_recalculation_mismatch"
    )
