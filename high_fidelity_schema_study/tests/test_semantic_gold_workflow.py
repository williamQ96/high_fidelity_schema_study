from __future__ import annotations

import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.architecture_variants import ALLOWED_LOGICAL_TYPES
from high_fidelity_schema_study.semantic_gold_workflow import (
    _cohen_kappa,
    build_annotation_workflow_manifest,
    build_packet_source_bundle,
    compare_independent_artifacts,
    main as gold_workflow_main,
    sha256_file,
    validate_annotation_artifact,
    validate_consensus_artifact,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def packet_payload() -> dict:
    return {
        "schema_version": "semantic-annotation-packet/v1",
        "purpose": "annotator_calibration",
        "research_evidence_status": "non_blind_not_for_effect_estimation",
        "case_id": "case-1",
        "task_id": "calibration::case-1",
        "dataset_id": "case-1",
        "file_format": "csv",
        "data_modality": "tabular",
        "field_inventory": [
            {
                "field_name": "temperature",
                "field_path": "temperature",
                "physical_type": "float32",
                "source_evidence": [
                    {
                        "evidence_id": "temperature::F1",
                        "tier": "structural",
                        "evidence_type": "csv_header",
                        "source_label": "weather.csv",
                        "detail": "header='temperature'",
                    }
                ],
            }
        ],
        "approved_evidence": [
            {
                "evidence_id": "S1",
                "source_type": "approved_documentation",
                "source_name": "README.md",
                "detail": "line 1",
                "text": "temperature is air temperature in degree Celsius",
                "applicable_field_paths": ["temperature"],
            }
        ],
    }


def vocabulary_payload() -> dict:
    return {
        "schema_version": "semantic-annotation-vocabulary/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "status": "frozen",
        "vocabulary_version": "fixture-v1",
        "physical_types": ["float32"],
        "logical_types": sorted(ALLOWED_LOGICAL_TYPES),
        "semantic_types": ["air_temperature", "surface_temperature"],
        "units": ["degree_Celsius"],
        "unit_aliases": {"C": "degree_Celsius", "Celsius": "degree_Celsius"},
        "unit_patterns": [],
        "unknown_representation": None,
    }


def build_inputs(tmp_path: Path) -> dict[str, Path]:
    packet_path = tmp_path / "packet.json"
    vocabulary_path = tmp_path / "vocabulary.json"
    bundle_path = tmp_path / "source-bundle.json"
    write_json(packet_path, packet_payload())
    write_json(vocabulary_path, vocabulary_payload())
    write_json(
        bundle_path,
        build_packet_source_bundle(packet_path, vocabulary_path),
    )
    return {
        "packet_path": packet_path,
        "vocabulary_path": vocabulary_path,
        "source_bundle_path": bundle_path,
    }


def evidence(
    evidence_id: str,
    property_name: str,
    *,
    packet_hash: str,
    catalog_evidence_id: str = "S1",
) -> dict:
    return {
        "evidence_id": evidence_id,
        "catalog_evidence_id": catalog_evidence_id,
        "property": property_name,
        "source_type": "approved_documentation",
        "source_sha256": packet_hash,
        "selector": "approved_evidence:S1",
        "field_path": "temperature",
        "strength": "documentation",
        "support": f"Approved documentation supports {property_name}.",
    }


def independent_artifact(
    inputs: dict[str, Path],
    *,
    annotator_id: str,
    submission_id: str,
    semantic_type: str | None = "air_temperature",
) -> dict:
    packet_hash = sha256_file(inputs["packet_path"])
    values = {
        "physical_type": "float32",
        "logical_type": "measurement",
        "semantic_type": semantic_type,
        "unit": "degree_Celsius",
    }
    return {
        "schema_version": "blind-semantic-gold/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "dataset_id": "case-1",
        "annotation_stage": "independent",
        "annotator_id": annotator_id,
        "submission_id": submission_id,
        "source_bundle_sha256": sha256_file(inputs["source_bundle_path"]),
        "annotation_packet_sha256": packet_hash,
        "vocabulary_sha256": sha256_file(inputs["vocabulary_path"]),
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
                "applicability": {property_name: True for property_name in values},
                "rationales": {
                    "physical_type": None,
                    "logical_type": None,
                    "semantic_type": (
                        None
                        if semantic_type is not None
                        else "Approved evidence does not resolve the semantic label."
                    ),
                    "unit": None,
                },
                "gold_evidence": [
                    evidence(
                        f"{submission_id}-{index}",
                        property_name,
                        packet_hash=packet_hash,
                    )
                    for index, property_name in enumerate(values, start=1)
                    if values[property_name] is not None
                ],
                "notes": None,
            }
        ],
    }


def write_independent_pair(tmp_path: Path) -> tuple[dict[str, Path], Path, Path]:
    inputs = build_inputs(tmp_path)
    artifact_a_path = tmp_path / "annotator-a.json"
    artifact_b_path = tmp_path / "annotator-b.json"
    write_json(
        artifact_a_path,
        independent_artifact(
            inputs, annotator_id="annotator-a", submission_id="submission-a"
        ),
    )
    write_json(
        artifact_b_path,
        independent_artifact(
            inputs,
            annotator_id="annotator-b",
            submission_id="submission-b",
            semantic_type="surface_temperature",
        ),
    )
    return inputs, artifact_a_path, artifact_b_path


def error_codes(report: dict) -> set[str]:
    return {str(item["code"]) for item in report["errors"]}


def test_valid_independent_artifact_passes_all_frozen_boundaries(
    tmp_path: Path,
) -> None:
    inputs = build_inputs(tmp_path)
    artifact_path = tmp_path / "annotation.json"
    write_json(
        artifact_path,
        independent_artifact(
            inputs, annotator_id="annotator-a", submission_id="submission-a"
        ),
    )

    report = validate_annotation_artifact(artifact_path, **inputs)

    assert report["status"] == "ready"
    assert report["errors"] == []
    assert report["summary"]["artifact_sha256"] == sha256_file(artifact_path)


def test_model_visibility_and_developer_participation_fail_closed(
    tmp_path: Path,
) -> None:
    inputs = build_inputs(tmp_path)
    artifact = independent_artifact(
        inputs, annotator_id="annotator-a", submission_id="submission-a"
    )
    artifact["model_outputs_visible"] = True
    artifact["developer_participation"] = True
    artifact_path = tmp_path / "annotation.json"
    write_json(artifact_path, artifact)

    codes = error_codes(validate_annotation_artifact(artifact_path, **inputs))

    assert "annotation_model_visibility" in codes
    assert "annotation_developer_boundary" in codes


def test_neutral_packet_prediction_leakage_blocks_annotation(tmp_path: Path) -> None:
    inputs = build_inputs(tmp_path)
    packet = json.loads(inputs["packet_path"].read_text(encoding="utf-8"))
    packet["field_inventory"][0]["logical_type"] = "measurement"
    write_json(inputs["packet_path"], packet)
    artifact_path = tmp_path / "annotation.json"
    write_json(
        artifact_path,
        independent_artifact(
            inputs, annotator_id="annotator-a", submission_id="submission-a"
        ),
    )

    codes = error_codes(validate_annotation_artifact(artifact_path, **inputs))

    assert "packet_prediction_leakage" in codes
    assert "source_bundle_packet_hash" in codes


def test_unknown_string_and_missing_property_rationale_are_rejected(
    tmp_path: Path,
) -> None:
    inputs = build_inputs(tmp_path)
    artifact = independent_artifact(
        inputs, annotator_id="annotator-a", submission_id="submission-a"
    )
    field = artifact["fields"][0]
    field["correct_semantic_type"] = "unknown"
    field["gold_evidence"] = [
        item for item in field["gold_evidence"] if item["property"] != "semantic_type"
    ]
    field["rationales"]["semantic_type"] = None
    artifact_path = tmp_path / "annotation.json"
    write_json(artifact_path, artifact)

    codes = error_codes(validate_annotation_artifact(artifact_path, **inputs))

    assert "annotation_unknown_string" in codes
    assert "annotation_out_of_vocabulary" in codes

    field["correct_semantic_type"] = None
    write_json(artifact_path, artifact)
    codes = error_codes(validate_annotation_artifact(artifact_path, **inputs))
    assert "annotation_rationale_missing" in codes


def test_unit_alias_must_be_normalized_before_gold(tmp_path: Path) -> None:
    inputs = build_inputs(tmp_path)
    artifact = independent_artifact(
        inputs, annotator_id="annotator-a", submission_id="submission-a"
    )
    artifact["fields"][0]["unit"] = "C"
    artifact_path = tmp_path / "annotation.json"
    write_json(artifact_path, artifact)

    codes = error_codes(validate_annotation_artifact(artifact_path, **inputs))

    assert "annotation_unit_alias" in codes
    assert "annotation_out_of_vocabulary" in codes


def test_nonexistent_or_wrong_provenance_evidence_cannot_support_gold(
    tmp_path: Path,
) -> None:
    inputs = build_inputs(tmp_path)
    artifact = independent_artifact(
        inputs, annotator_id="annotator-a", submission_id="submission-a"
    )
    semantic_evidence = next(
        item
        for item in artifact["fields"][0]["gold_evidence"]
        if item["property"] == "semantic_type"
    )
    semantic_evidence["catalog_evidence_id"] = "DOES_NOT_EXIST"
    semantic_evidence["source_sha256"] = "0" * 64
    artifact_path = tmp_path / "annotation.json"
    write_json(artifact_path, artifact)

    codes = error_codes(validate_annotation_artifact(artifact_path, **inputs))

    assert "annotation_evidence_identity" in codes
    assert "annotation_known_without_evidence" in codes


def test_declared_approved_source_must_exist_and_match_bytes(tmp_path: Path) -> None:
    inputs = build_inputs(tmp_path)
    bundle = json.loads(inputs["source_bundle_path"].read_text(encoding="utf-8"))
    bundle["sources"].append(
        {
            "source_id": "MISSING_DOC",
            "source_type": "approved_documentation",
            "source_file": "missing-readme.md",
            "source_sha256": "0" * 64,
        }
    )
    write_json(inputs["source_bundle_path"], bundle)
    artifact_path = tmp_path / "annotation.json"
    write_json(
        artifact_path,
        independent_artifact(
            inputs, annotator_id="annotator-a", submission_id="submission-a"
        ),
    )

    codes = error_codes(validate_annotation_artifact(artifact_path, **inputs))

    assert "approved_source_unavailable" in codes


def test_comparison_is_deterministic_and_never_auto_adjudicates(tmp_path: Path) -> None:
    inputs, artifact_a_path, artifact_b_path = write_independent_pair(tmp_path)

    first = compare_independent_artifacts(artifact_a_path, artifact_b_path, **inputs)
    second = compare_independent_artifacts(artifact_a_path, artifact_b_path, **inputs)

    assert first == second
    assert first["slot_count"] == 4
    assert first["agreed_slot_count"] == 3
    assert first["disagreement_count"] == 1
    assert first["disagreements"][0]["slot_id"] == "temperature::semantic_type"
    assert first["disagreements"][0]["resolution"]["status"] == (
        "pending_human_adjudication"
    )
    semantic_agreement = first["agreement_by_property"]["semantic_type"]
    assert semantic_agreement["cohen_kappa"] == 0.0
    assert semantic_agreement["cohen_kappa_status"] == "defined"
    assert semantic_agreement["label_state_support"]["annotator_a"] == {
        'applicable_value:"air_temperature"': 1
    }
    physical_agreement = first["agreement_by_property"]["physical_type"]
    assert physical_agreement["cohen_kappa"] is None
    assert physical_agreement["cohen_kappa_status"] == (
        "undefined_degenerate_marginals"
    )


def test_cohen_kappa_reports_defined_and_degenerate_cases() -> None:
    assert _cohen_kappa(
        ["a", "a", "b", "b"],
        ["a", "b", "b", "b"],
    ) == 0.5
    assert _cohen_kappa(["a", "a"], ["a", "a"]) is None


def test_comparison_requires_distinct_annotators(tmp_path: Path) -> None:
    inputs, artifact_a_path, artifact_b_path = write_independent_pair(tmp_path)
    artifact_b = json.loads(artifact_b_path.read_text(encoding="utf-8"))
    artifact_b["annotator_id"] = "annotator-a"
    write_json(artifact_b_path, artifact_b)

    with pytest.raises(ValueError, match="distinct annotator ids"):
        compare_independent_artifacts(artifact_a_path, artifact_b_path, **inputs)


def build_consensus(
    inputs: dict[str, Path],
    artifact_a_path: Path,
    artifact_b_path: Path,
    disagreement_path: Path,
) -> dict:
    artifact = independent_artifact(
        inputs, annotator_id="consensus-panel", submission_id="consensus-1"
    )
    artifact["annotation_stage"] = "consensus"
    disagreement = json.loads(disagreement_path.read_text(encoding="utf-8"))
    artifact["adjudication"] = {
        "independent_artifact_ids": [
            item["submission_id"] for item in disagreement["independent_artifacts"]
        ],
        "independent_artifacts": disagreement["independent_artifacts"],
        "disagreement_report_sha256": sha256_file(disagreement_path),
        "disagreement_count": disagreement["disagreement_count"],
        "unresolved_slots": [],
        "resolutions": [
            {
                "slot_id": "temperature::semantic_type",
                "status": "selected_annotator_a",
                "rationale": "Approved documentation uses the more specific air-temperature label.",
            }
        ],
    }
    return artifact


def test_valid_consensus_is_bound_to_both_frozen_originals(tmp_path: Path) -> None:
    inputs, artifact_a_path, artifact_b_path = write_independent_pair(tmp_path)
    disagreement_path = tmp_path / "disagreement.json"
    write_json(
        disagreement_path,
        compare_independent_artifacts(artifact_a_path, artifact_b_path, **inputs),
    )
    consensus_path = tmp_path / "consensus.json"
    write_json(
        consensus_path,
        build_consensus(inputs, artifact_a_path, artifact_b_path, disagreement_path),
    )

    report = validate_consensus_artifact(
        consensus_path,
        artifact_a_path=artifact_a_path,
        artifact_b_path=artifact_b_path,
        disagreement_report_path=disagreement_path,
        **inputs,
    )

    assert report["status"] == "ready"
    assert report["summary"]["disagreement_count"] == 1
    assert report["summary"]["unresolved_count"] == 0


def test_cli_writes_independent_and_consensus_validation_receipts(
    tmp_path: Path,
) -> None:
    inputs, artifact_a_path, artifact_b_path = write_independent_pair(tmp_path)
    disagreement_path = tmp_path / "disagreement.json"
    write_json(
        disagreement_path,
        compare_independent_artifacts(
            artifact_a_path, artifact_b_path, **inputs
        ),
    )
    consensus_path = tmp_path / "consensus.json"
    write_json(
        consensus_path,
        build_consensus(
            inputs,
            artifact_a_path,
            artifact_b_path,
            disagreement_path,
        ),
    )
    independent_receipt = tmp_path / "independent-validation.json"
    consensus_receipt = tmp_path / "consensus-validation.json"

    gold_workflow_main(
        [
            "validate-independent",
            "--artifact",
            str(artifact_a_path),
            "--packet",
            str(inputs["packet_path"]),
            "--source-bundle",
            str(inputs["source_bundle_path"]),
            "--vocabulary",
            str(inputs["vocabulary_path"]),
            "--output",
            str(independent_receipt),
        ]
    )
    gold_workflow_main(
        [
            "validate-consensus",
            "--artifact",
            str(consensus_path),
            "--artifact-a",
            str(artifact_a_path),
            "--artifact-b",
            str(artifact_b_path),
            "--disagreement-report",
            str(disagreement_path),
            "--packet",
            str(inputs["packet_path"]),
            "--source-bundle",
            str(inputs["source_bundle_path"]),
            "--vocabulary",
            str(inputs["vocabulary_path"]),
            "--output",
            str(consensus_receipt),
        ]
    )

    assert json.loads(independent_receipt.read_text())["status"] == "ready"
    assert json.loads(consensus_receipt.read_text())["status"] == "ready"


def test_consensus_cannot_silently_change_an_agreed_slot(tmp_path: Path) -> None:
    inputs, artifact_a_path, artifact_b_path = write_independent_pair(tmp_path)
    disagreement_path = tmp_path / "disagreement.json"
    write_json(
        disagreement_path,
        compare_independent_artifacts(artifact_a_path, artifact_b_path, **inputs),
    )
    consensus = build_consensus(
        inputs, artifact_a_path, artifact_b_path, disagreement_path
    )
    consensus["fields"][0]["correct_logical_type"] = "coordinate"
    consensus_path = tmp_path / "consensus.json"
    write_json(consensus_path, consensus)

    report = validate_consensus_artifact(
        consensus_path,
        artifact_a_path=artifact_a_path,
        artifact_b_path=artifact_b_path,
        disagreement_report_path=disagreement_path,
        **inputs,
    )

    assert "consensus_changed_agreement" in error_codes(report)


def test_consensus_detects_post_reveal_independent_artifact_tampering(
    tmp_path: Path,
) -> None:
    inputs, artifact_a_path, artifact_b_path = write_independent_pair(tmp_path)
    disagreement_path = tmp_path / "disagreement.json"
    write_json(
        disagreement_path,
        compare_independent_artifacts(artifact_a_path, artifact_b_path, **inputs),
    )
    consensus_path = tmp_path / "consensus.json"
    write_json(
        consensus_path,
        build_consensus(inputs, artifact_a_path, artifact_b_path, disagreement_path),
    )
    artifact_a = json.loads(artifact_a_path.read_text(encoding="utf-8"))
    artifact_a["fields"][0]["notes"] = "Changed after disagreement reveal."
    write_json(artifact_a_path, artifact_a)

    report = validate_consensus_artifact(
        consensus_path,
        artifact_a_path=artifact_a_path,
        artifact_b_path=artifact_b_path,
        disagreement_report_path=disagreement_path,
        **inputs,
    )

    codes = error_codes(report)
    assert "disagreement_report_mismatch" in codes
    assert "consensus_independent_identity" in codes


def test_checked_in_calibration_workflow_is_exact_rebuild() -> None:
    package_root = Path(__file__).resolve().parents[1]
    base = (
        package_root / "data" / "experiments" / "semantic_architecture_calibration_v1"
    )
    rebuilt = build_annotation_workflow_manifest(
        base / "manifest.json",
        vocabulary_path=base / "vocabulary.json",
        source_bundle_dir=base / "source_bundles",
        handbook_path=package_root / "docs" / "semantic_gold_annotation_handbook_v1.md",
        output_path=base / "annotation_workflow_manifest.json",
    )
    checked_in = json.loads(
        (base / "annotation_workflow_manifest.json").read_text(encoding="utf-8")
    )

    assert rebuilt == checked_in
    assert checked_in["case_count"] == 9
    assert checked_in["independence_policy"]["annotator_count"] == 2
