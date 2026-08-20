from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_human_handoff import (
    NDPHumanHandoffError,
    build_handoff,
    validate_handoff,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "ndp50"
    semantic = root / "semantic"
    packet_manifest = semantic / "packet_manifest.json"
    vocabulary = semantic / "vocabulary.json"
    vocabulary_workflow = semantic / "vocabulary_workflow.json"
    vocabulary_template = semantic / "vocabulary_template.json"
    source_approval_spec = semantic / "source_approval_spec.json"
    source_bundle_manifest = semantic / "bundles" / "manifest.json"
    cpa_workflow = semantic / "cpa_workflow.json"
    cpa_screen = semantic / "cpa_screen.json"
    cpa_design = semantic / "cpa_design.json"
    power_feasibility = semantic / "power_feasibility.json"
    power_policy_template = semantic / "power_policy_template.json"
    power_freeze_workflow = semantic / "power_freeze_workflow.json"
    data_governance = root / "reports" / "data_governance.json"
    data_governance_review_template = (
        root / "governance" / "data_governance_review_template.json"
    )
    data_governance_review_workflow = (
        root / "governance" / "data_governance_review_workflow.json"
    )
    readiness = semantic / "readiness.json"
    semantic_gold_index_template = semantic / "gold_index_template.json"
    semantic_gold_workflow_spec = semantic / "gold_workflow_spec.json"
    demonstration_pool_workflow_spec = (
        semantic / "demonstration_pool_workflow_spec.json"
    )
    execution_freeze_config_template = (
        semantic / "execution_freeze_config_template.json"
    )
    execution_freeze_workflow = semantic / "execution_freeze_workflow.json"
    test_execution_workflow = semantic / "test_execution_workflow.json"
    publication_gate_workflow = (
        root / "preregistration" / "publication_gate_workflow.json"
    )
    feedback_response_signoff_template = (
        root / "preregistration" / "feedback_signoff_template.json"
    )

    _write(
        packet_manifest,
        {
            "schema_version": "ndp50-semantic-packet-pack/v1",
            "status": "neutral_packets_ready_source_bundles_blocked",
            "case_count": 0,
            "cases": [],
        },
    )
    _write(vocabulary, {"status": "draft"})
    _write(
        vocabulary_template,
        {
            "schema_version": "ndp50-vocabulary-discovery/v1",
            "reviewer_id": "replace-with-reviewer-id",
            "reviewer_role": "replace-with-reviewer-role",
            "submission_id": "replace-with-submission-id",
            "qualification_summary": None,
            "conflict_of_interest_declared": None,
            "completion_attestation": None,
            "policy_rationale": None,
            "developer_participation": False,
            "model_outputs_visible": False,
            "other_review_visible_before_freeze": False,
            "proposals": [],
            "policy_decisions": {"preserve_base_terms": None},
            "cases": [],
            "case_reviews": [],
        },
    )
    _write(
        source_bundle_manifest,
        {
            "schema_version": "ndp50-source-bundle-draft-manifest/v1",
            "status": "draft_bundles_structurally_valid_not_annotation_ready",
        },
    )
    _write(
        vocabulary_workflow,
        {
            "schema_version": "ndp50-vocabulary-review-workflow/v1",
            "status": "ready_for_independent_vocabulary_discovery",
            "human_decisions_present": False,
            "draft_vocabulary": {
                "file": "vocabulary_draft.json",
                "sha256": "a" * 64,
            },
        },
    )
    _write(
        source_approval_spec,
        {
            "schema_version": "ndp50-source-approval-workflow-spec/v1",
            "status": (
                "implementation_ready_waiting_on_frozen_vocabulary_and_"
                "rebuilt_bundles"
            ),
            "human_decisions_present": False,
        },
    )
    _write(
        cpa_workflow,
        {
            "schema_version": "ndp50-cpa-screen-workflow/v1",
            "status": "workflow_validated_screening_blocked_on_source_approval",
            "human_decisions_present": False,
        },
    )
    _write(
        cpa_screen,
        {
            "schema_version": "ndp50-cpa-applicability-screen/v1",
            "cases": [],
        },
    )
    _write(cpa_design, {"schema_version": "ndp50-cpa-design/v1"})
    _write(
        power_feasibility,
        {
            "schema_version": "ndp50-semantic-power-feasibility/v1",
            "gates": {"test_power_plan_frozen": False},
            "test_state": {
                "test_detail_snapshot_count": 0,
                "test_split_unopened": True,
            },
        },
    )
    _write(
        power_policy_template,
        {
            "schema_version": "ndp50-power-policy/v1",
            "status": "neutral_pending_precalibration_policy",
            "human_decisions_present": False,
        },
    )
    _write(
        power_freeze_workflow,
        {
            "schema_version": "ndp50-power-freeze-workflow/v1",
            "status": "implementation_ready_waiting_on_execution_freeze",
            "human_decisions_present": False,
            "test_outcomes_observed": False,
            "validation_or_test_outcomes_forbidden": True,
        },
    )
    _write(
        data_governance,
        {
            "schema_version": "ndp50-data-governance-audit/v1",
            "status": (
                "provenance_integrity_passed_governance_review_required"
            ),
            "gates": {
                "detail_snapshot_hashes_verified": True,
                "dataset_identity_verified": True,
                "acquired_payload_hashes_complete": True,
                "human_license_and_attribution_review_complete": False,
                "external_model_data_transfer_policy_frozen": False,
                "artifact_redistribution_policy_frozen": False,
                "test_split_unopened": True,
            },
        },
    )
    _write(
        data_governance_review_template,
        {
            "schema_version": "ndp50-data-governance-review/v1",
            "status": "neutral_pending_human_review",
            "dataset_reviews": [],
        },
    )
    _write(
        data_governance_review_workflow,
        {
            "schema_version": "ndp50-data-governance-review-workflow/v1",
            "status": (
                "ready_for_independent_governance_review_and_approval"
            ),
            "human_decisions_present": False,
        },
    )
    _write(
        semantic_gold_index_template,
        {
            "schema_version": "ndp50-semantic-gold-corpus-index/v1",
            "status": "neutral_pending_gold_artifacts",
            "human_decisions_present": False,
            "cases": [],
        },
    )
    _write(
        semantic_gold_workflow_spec,
        {
            "schema_version": "ndp50-semantic-gold-workflow-spec/v1",
            "status": (
                "implementation_ready_waiting_on_frozen_vocabulary_and_"
                "approved_sources"
            ),
            "human_decisions_present": False,
        },
    )
    _write(
        demonstration_pool_workflow_spec,
        {
            "schema_version": "ndp50-demonstration-pool-workflow/v1",
            "status": "implementation_ready_waiting_on_semantic_gold",
            "human_decisions_present": False,
            "candidate_inclusion_policy": (
                "all_approved_development_cases"
            ),
            "validation_or_test_candidates_forbidden": True,
        },
    )
    _write(
        execution_freeze_config_template,
        {
            "schema_version": "ndp50-execution-freeze-config/v1",
            "status": "neutral_pending_execution_configuration",
            "human_decisions_present": False,
        },
    )
    _write(
        execution_freeze_workflow,
        {
            "schema_version": "ndp50-execution-freeze-workflow/v1",
            "status": (
                "implementation_ready_waiting_on_upstream_human_gates"
            ),
            "human_decisions_present": False,
            "automatic_freeze": False,
        },
    )
    _write(
        test_execution_workflow,
        {
            "schema_version": "ndp50-test-execution-workflow/v1",
            "status": "implementation_ready_waiting_on_test_release",
            "human_decisions_present": False,
            "test_outcomes_observed": False,
            "test_dataset_identities_included": False,
            "test_dataset_count": 25,
        },
    )
    _write(
        publication_gate_workflow,
        {
            "schema_version": "ndp50-publication-gate-workflow/v1",
            "status": (
                "implementation_ready_waiting_on_collaborator_signoff_and_"
                "external_registration"
            ),
            "human_decisions_present": False,
            "test_outcomes_observed": False,
            "test_release_authorized": False,
        },
    )
    _write(
        feedback_response_signoff_template,
        {
            "schema_version": "ndp50-feedback-response-signoff/v2",
            "status": "pending_human_collaborator_review",
            "human_decisions_present": False,
            "independence_claimed": False,
        },
    )
    bindings = {
        "vocabulary_review_workflow": _sha256(vocabulary_workflow),
        "packet_manifest": _sha256(packet_manifest),
        "vocabulary": _sha256(vocabulary),
        "vocabulary_review_template": _sha256(vocabulary_template),
        "source_approval_workflow_spec": _sha256(source_approval_spec),
        "source_bundle_manifest": _sha256(source_bundle_manifest),
        "cpa_workflow": _sha256(cpa_workflow),
        "cpa_screen": _sha256(cpa_screen),
        "cpa_design": _sha256(cpa_design),
        "semantic_power_feasibility": _sha256(power_feasibility),
        "power_policy_template": _sha256(power_policy_template),
        "power_freeze_workflow": _sha256(power_freeze_workflow),
        "data_governance": _sha256(data_governance),
        "data_governance_review_template": _sha256(
            data_governance_review_template
        ),
        "data_governance_review_workflow": _sha256(
            data_governance_review_workflow
        ),
        "data_governance_approval": None,
        "semantic_gold_index_template": _sha256(
            semantic_gold_index_template
        ),
        "semantic_gold_workflow_spec": _sha256(
            semantic_gold_workflow_spec
        ),
        "demonstration_pool_workflow_spec": _sha256(
            demonstration_pool_workflow_spec
        ),
        "semantic_gold_approval": None,
        "execution_freeze_config_template": _sha256(
            execution_freeze_config_template
        ),
        "execution_freeze_workflow": _sha256(execution_freeze_workflow),
        "test_execution_workflow": _sha256(test_execution_workflow),
        "publication_gate_workflow": _sha256(
            publication_gate_workflow
        ),
        "feedback_response_signoff_template": _sha256(
            feedback_response_signoff_template
        ),
        "execution_freeze": None,
        "cpa_consensus": None,
    }
    readiness_implementation = (
        Path(__file__).resolve().parents[1] / "ndp50_readiness.py"
    )
    _write(
        readiness,
        {
            "schema_version": "ndp50-research-readiness/v1",
            "implementation": {
                "file": readiness_implementation.name,
                "sha256": _sha256(readiness_implementation),
            },
            "integrity_status": "passed",
            "readiness_status": "blocked_as_expected",
            "test_ready": False,
            "checks": [{"check_id": "test_split_unopened", "passed": True}],
            "artifact_hashes": bindings,
            "gates": {
                "vocabulary_review_workflow_ready": True,
                "vocabulary_frozen": False,
                "source_approval_workflow_implementation_ready": True,
                "source_bundles_annotation_ready": False,
                "cpa_applicability_consensus_complete": False,
                "independent_gold_complete": False,
                "prompt_and_backend_frozen": False,
                "semantic_power_feasibility_assessed": True,
                "power_freeze_workflow_ready": True,
                "test_power_plan_frozen": False,
                "test_split_unopened": True,
                "data_governance_review_workflow_ready": True,
                "human_license_and_attribution_review_complete": False,
                "external_model_data_transfer_policy_frozen": False,
                "artifact_redistribution_policy_frozen": False,
                "data_governance_policy_frozen": False,
                "semantic_gold_workflow_ready": True,
                "demonstration_pool_workflow_ready": True,
                "execution_freeze_workflow_ready": True,
                "test_execution_workflow_ready": True,
                "publication_gate_workflow_ready": True,
                "feedback_response_collaborator_signoff_complete": False,
                "external_preregistration_verified": False,
            },
        },
    )
    return {
        "study_root": root,
        "readiness_path": readiness,
        "packet_manifest_path": packet_manifest,
        "vocabulary_path": vocabulary,
        "vocabulary_workflow_path": vocabulary_workflow,
        "vocabulary_template_path": vocabulary_template,
        "source_approval_spec_path": source_approval_spec,
        "source_bundle_manifest_path": source_bundle_manifest,
        "cpa_workflow_path": cpa_workflow,
        "cpa_screen_path": cpa_screen,
        "cpa_design_path": cpa_design,
        "power_feasibility_path": power_feasibility,
        "power_policy_template_path": power_policy_template,
        "power_freeze_workflow_path": power_freeze_workflow,
        "data_governance_path": data_governance,
        "data_governance_review_template_path": (
            data_governance_review_template
        ),
        "data_governance_review_workflow_path": (
            data_governance_review_workflow
        ),
        "semantic_gold_index_template_path": (
            semantic_gold_index_template
        ),
        "semantic_gold_workflow_spec_path": semantic_gold_workflow_spec,
        "demonstration_pool_workflow_spec_path": (
            demonstration_pool_workflow_spec
        ),
        "execution_freeze_config_template_path": (
            execution_freeze_config_template
        ),
        "execution_freeze_workflow_path": execution_freeze_workflow,
        "test_execution_workflow_path": test_execution_workflow,
        "publication_gate_workflow_path": publication_gate_workflow,
        "feedback_response_signoff_template_path": (
            feedback_response_signoff_template
        ),
    }


def test_parallel_governance_vocabulary_and_feedback_work_is_released_initially(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    report = build_handoff(**inputs)

    assert report["status"] == "human_work_released_downstream_locked"
    assert report["current_release"]["released_stage_ids"] == [
        "data_governance_review",
        "vocabulary_governance",
        "feedback_response_signoff",
    ]
    assert [item["status"] for item in report["stages"]] == [
        "released",
        "released",
        "released",
        "locked",
        "locked",
        "locked",
        "locked",
        "locked",
        "locked",
        "locked",
        "locked",
    ]
    assert report["stages"][4]["stage_id"] == "annotator_calibration"
    assert "data_governance_assignment" in report["current_release"]
    assert "vocabulary_assignment" in report["current_release"]
    assert (
        "feedback_response_signoff_assignment"
        in report["current_release"]
    )
    serialized = json.dumps(report, sort_keys=True)
    assert str(tmp_path) not in serialized
    assert "test dataset identities" in serialized.lower()


def test_handoff_recalculates_and_detects_tampering(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    report = build_handoff(**inputs)
    assert validate_handoff(report, **inputs)["status"] == "passed"

    report["stages"][3]["status"] = "released"
    validation = validate_handoff(report, **inputs)

    assert validation["status"] == "failed"
    assert validation["differing_top_level_keys"] == ["stages"]


def test_readiness_binding_mismatch_is_rejected(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    path = inputs["cpa_screen_path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["tampered"] = True
    _write(path, payload)

    with pytest.raises(NDPHumanHandoffError, match="binding mismatch"):
        build_handoff(**inputs)


def test_manual_test_ready_flip_is_rejected(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    path = inputs["readiness_path"]
    readiness = json.loads(path.read_text(encoding="utf-8"))
    readiness["test_ready"] = True
    readiness["readiness_status"] = "ready"
    _write(path, readiness)

    with pytest.raises(
        NDPHumanHandoffError,
        match="inconsistent release gates",
    ):
        build_handoff(**inputs)


def test_manual_annotator_calibration_gate_flip_is_rejected(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    path = inputs["readiness_path"]
    readiness = json.loads(path.read_text(encoding="utf-8"))
    readiness["gates"]["annotator_calibration_passed"] = True
    _write(path, readiness)

    with pytest.raises(
        NDPHumanHandoffError,
        match="annotator-calibration gate and supplied summary disagree",
    ):
        build_handoff(**inputs)


def test_stale_readiness_implementation_is_rejected(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    path = inputs["readiness_path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["implementation"]["sha256"] = "0" * 64
    _write(path, payload)

    with pytest.raises(NDPHumanHandoffError, match="implementation binding"):
        build_handoff(**inputs)


def test_opened_test_state_is_rejected(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    path = inputs["power_feasibility_path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["test_state"]["test_detail_snapshot_count"] = 1
    _write(path, payload)
    readiness_path = inputs["readiness_path"]
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    readiness["artifact_hashes"]["semantic_power_feasibility"] = _sha256(path)
    _write(readiness_path, readiness)

    with pytest.raises(NDPHumanHandoffError, match="snapshots are forbidden"):
        build_handoff(**inputs)


def test_non_neutral_released_vocabulary_template_is_rejected(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    path = inputs["vocabulary_template_path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["reviewer_id"] = "reviewer-already-assigned"
    _write(path, payload)
    readiness_path = inputs["readiness_path"]
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    readiness["artifact_hashes"]["vocabulary_review_template"] = _sha256(path)
    _write(readiness_path, readiness)

    with pytest.raises(NDPHumanHandoffError, match="placeholder reviewer_id"):
        build_handoff(**inputs)


def test_governance_policy_blocks_execution_freeze_release(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    path = inputs["readiness_path"]
    readiness = json.loads(path.read_text(encoding="utf-8"))
    readiness["gates"].update(
        {
            "vocabulary_frozen": True,
            "source_bundles_annotation_ready": True,
            "cpa_applicability_consensus_complete": True,
            "independent_gold_complete": True,
        }
    )
    _write(path, readiness)

    report = build_handoff(**inputs)
    execution_stage = next(
        item
        for item in report["stages"]
        if item["stage_id"] == "execution_freeze"
    )

    assert execution_stage["status"] == "locked"
    assert report["current_release"]["released_stage_ids"] == [
        "data_governance_review",
        "feedback_response_signoff",
        "annotator_calibration",
    ]
