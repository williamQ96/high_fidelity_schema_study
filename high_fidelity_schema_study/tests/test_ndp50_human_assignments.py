from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import high_fidelity_schema_study.ndp50_human_assignments as assignments
from high_fidelity_schema_study.ndp50_assignment_roster import (
    replay_assignment_roster_validation,
)
from high_fidelity_schema_study.ndp50_human_assignments import (
    NDPHumanAssignmentError,
    prepare_assignment_package,
    prepare_consensus_assignment_package,
    prepare_decision_assignment_package,
    validate_assignment_release,
    validate_consensus_assignment_release,
    validate_consensus_return_manifest,
    validate_decision_assignment_release,
    validate_decision_return_manifest,
    validate_return_manifest,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding(path: Path, root: Path) -> dict:
    return {
        "file": path.resolve().relative_to(root.resolve()).as_posix(),
        "sha256": _sha256(path),
    }


@pytest.fixture(autouse=True)
def _stub_distribution_spec(monkeypatch) -> None:
    def build_stub(*, assignment_release_path: Path, **kwargs) -> dict:
        packet_slots = {
            "data_governance_review": [
                "governance_stewardship",
                "governance_accountable_approval",
            ],
            "feedback_response_signoff": ["feedback_response_signoff"],
            "vocabulary_discovery_a": ["vocabulary_discovery_a"],
            "vocabulary_discovery_b": ["vocabulary_discovery_b"],
        }
        return {
            "schema_version": (
                "ndp50-human-assignment-distribution-spec/v1"
            ),
            "status": "neutral_packets_specified_unmaterialized",
            "assignment_release": _binding(
                assignment_release_path,
                kwargs["study_root"],
            ),
            "packet_count": 4,
            "packets": {
                packet_id: {"roster_slots": slots}
                for packet_id, slots in packet_slots.items()
            },
            "reviewer_ids_present": False,
            "human_decisions_present": False,
        }

    monkeypatch.setattr(
        assignments,
        "build_distribution_spec",
        build_stub,
    )


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "ndp50"
    files = {
        "data_governance": root / "reports" / "governance.json",
        "data_governance_review_template": (
            root / "governance" / "review_template.json"
        ),
        "data_governance_review_workflow": (
            root / "governance" / "workflow.json"
        ),
        "vocabulary_review_template": (
            root / "semantic" / "vocabulary_template.json"
        ),
        "vocabulary": root / "semantic" / "vocabulary_draft.json",
        "source_bundle_manifest": (
            root / "semantic" / "sources" / "manifest.json"
        ),
        "vocabulary_review_workflow": (
            root / "semantic" / "vocabulary_workflow.json"
        ),
        "publication_gate_workflow": (
            root / "preregistration" / "publication_gate_workflow.json"
        ),
        "feedback_response_signoff_template": (
            root / "preregistration" / "feedback_signoff_template.json"
        ),
    }
    for index, (name, path) in enumerate(files.items()):
        _write(path, {"artifact": name, "ordinal": index})
    handoff_source = Path(assignments.__file__).with_name(
        "ndp50_human_handoff.py"
    )
    handoff = {
        "schema_version": "ndp50-human-handoff/v1",
        "status": "human_work_released_downstream_locked",
        "artifact_bindings": {
            name: _binding(path, root) for name, path in files.items()
        },
        "implementation": {
            "file": handoff_source.name,
            "sha256": _sha256(handoff_source),
        },
        "current_release": {
            "released_stage_ids": [
                "data_governance_review",
                "vocabulary_governance",
                "feedback_response_signoff",
            ]
        },
        "stages": [
            {"stage_id": "data_governance_review", "status": "released"},
            {"stage_id": "vocabulary_governance", "status": "released"},
            {"stage_id": "feedback_response_signoff", "status": "released"},
            {"stage_id": "source_approval", "status": "locked"},
        ],
    }
    handoff_path = root / "semantic" / "human_handoff.json"
    _write(handoff_path, handoff)
    return root, handoff_path


def test_prepare_builds_neutral_isolated_replayable_assignments(
    tmp_path: Path,
) -> None:
    root, handoff_path = _fixture(tmp_path)
    output_dir = root / "semantic" / "human_assignments"

    release = prepare_assignment_package(
        handoff_path=handoff_path,
        study_root=root,
        output_dir=output_dir,
    )
    release_path = output_dir / "assignment_release_v1.json"
    validation = validate_assignment_release(
        release,
        release_path=release_path,
        handoff_path=handoff_path,
        study_root=root,
    )

    assert validation["status"] == "passed"
    assert validation["distribution_spec_sha256"] == _sha256(
        output_dir / "assignment_distribution_spec_v1.json"
    )
    assert release["assignment_count"] == 4
    assert release["pre_submission_roster_contract"][
        "must_be_frozen_before_human_submissions"
    ] is True
    assert release["pre_submission_roster_contract"][
        "distribution_revalidated_from_live_packet_root_by_roster"
    ] is True
    assert release["pre_submission_roster_contract"][
        "per_role_packet_manifest_and_delivery_attestation_required"
    ] is True
    roster = json.loads(
        (output_dir / "assignment_roster_neutral_v1.json").read_text()
    )
    assert roster["status"] == "pending_assignment_acceptance"
    assert len(roster["slots"]) == 5
    assert all(
        slot["reviewer_id"] is None
        for slot in roster["slots"].values()
    )
    assert release["independence_controls"] == {
        "reviewer_ids_present_at_release": False,
        "human_decisions_present_at_release": False,
        "vocabulary_payloads_byte_identical": True,
        "vocabulary_assignment_wrappers_distinct": True,
        "cross_review_visibility_before_dual_freeze": False,
        "collaborator_feedback_review_claimed_independent": False,
        "test_data_access": "forbidden",
    }
    first = output_dir / "vocabulary_discovery_a_payload.json"
    second = output_dir / "vocabulary_discovery_b_payload.json"
    assert first.read_bytes() == second.read_bytes()
    wrapper_a = json.loads(
        (output_dir / "vocabulary_discovery_a_assignment.json").read_text()
    )
    wrapper_b = json.loads(
        (output_dir / "vocabulary_discovery_b_assignment.json").read_text()
    )
    assert wrapper_a["reviewer_id"] is None
    assert wrapper_b["reviewer_id"] is None
    assert wrapper_a["assignment_id"] != wrapper_b["assignment_id"]
    for wrapper, slot in (
        (wrapper_a, "vocabulary_discovery_a"),
        (wrapper_b, "vocabulary_discovery_b"),
    ):
        contract = wrapper["submission_contract"]
        assert contract["return_manifest_slot"] == slot
        assert contract["working_copy_filename"] == f"{slot}.json"
        command = contract["validator_command_template"]
        assert "validate-discovery" in command
        assert "--output" in command
        assert command[-1] == f"<{slot}_validation.json>"
        assert any(
            "other vocabulary reviewer" in action
            for action in contract["forbidden_actions"]
        )
    governance = json.loads(
        (
            output_dir / "data_governance_review_assignment.json"
        ).read_text()
    )
    governance_contract = governance["submission_contract"]
    assert governance_contract["return_manifest_slot"] == (
        "data_governance_review"
    )
    assert set(
        governance_contract["validator_command_templates"]
    ) == {
        "validate_review",
        "generate_approval",
        "verify_approval",
    }
    for command in governance_contract[
        "validator_command_templates"
    ].values():
        assert "--output" in command
    feedback = json.loads(
        (
            output_dir / "feedback_response_signoff_assignment.json"
        ).read_text()
    )
    assert feedback["reviewer_contract"]["project_collaborator"] is True
    assert feedback["reviewer_contract"]["independent_reviewer"] is False


def test_release_replay_detects_modified_neutral_copy(tmp_path: Path) -> None:
    root, handoff_path = _fixture(tmp_path)
    output_dir = root / "semantic" / "human_assignments"
    prepare_assignment_package(
        handoff_path=handoff_path,
        study_root=root,
        output_dir=output_dir,
    )
    release_path = output_dir / "assignment_release_v1.json"
    payload_path = output_dir / "vocabulary_discovery_b_payload.json"
    payload = json.loads(payload_path.read_text())
    payload["human_decision"] = True
    _write(payload_path, payload)

    validation = validate_assignment_release(
        json.loads(release_path.read_text()),
        release_path=release_path,
        handoff_path=handoff_path,
        study_root=root,
    )

    assert validation["status"] == "failed"
    assert validation["differing_top_level_keys"] == ["replay"]
    assert "not byte-identical" in validation["detail"]


def _completed_returns(
    *,
    root: Path,
    output_dir: Path,
    monkeypatch,
) -> tuple[Path, dict]:
    governance = {
        "reviewer_signoff": {"reviewer_id": "steward-01"},
        "accountable_approval": {"approver_id": "pi-01"},
    }
    governance_path = output_dir / "returned_governance.json"
    _write(governance_path, governance)
    governance_receipt = {
        "schema_version": "ndp50-data-governance-review-validation/v1",
        "status": "passed",
        "dataset_count": 2,
        "errors": [],
    }
    governance_receipt_path = output_dir / "governance_receipt.json"
    _write(governance_receipt_path, governance_receipt)
    monkeypatch.setattr(
        assignments,
        "validate_review",
        lambda review, *, template, audit: governance_receipt,
    )
    monkeypatch.setattr(
        assignments,
        "load_evidence_registry",
        lambda path, *, require_approved: ({}, {}, False),
    )
    feedback = {
        "collaborator": {"reviewer_id": "swathi-01"},
    }
    feedback_path = output_dir / "returned_feedback_signoff.json"
    _write(feedback_path, feedback)
    feedback_receipt = {
        "schema_version": "ndp50-publication-gate-validation/v1",
        "artifact_type": "feedback_response_signoff",
        "status": "passed",
        "collaborator_id": "swathi-01",
        "signed_at": "2026-07-27T12:00:00Z",
        "independent_validation_claimed": False,
        "test_release_authorized": False,
    }
    feedback_receipt_path = output_dir / "feedback_signoff_receipt.json"
    _write(feedback_receipt_path, feedback_receipt)
    monkeypatch.setattr(
        assignments,
        "validate_feedback_signoff",
        lambda payload, **kwargs: feedback_receipt,
    )

    vocabulary_reports = {}
    for slot, reviewer, role, submission_id in (
        (
            "vocabulary_discovery_a",
            "curator-01",
            "scientific_metadata_curator",
            "discovery-a-01",
        ),
        (
            "vocabulary_discovery_b",
            "methodologist-01",
            "annotation_methodologist",
            "discovery-b-01",
        ),
    ):
        submission = {
            "slot": slot,
            "reviewer_id": reviewer,
            "reviewer_role": role,
            "submission_id": submission_id,
        }
        submission_path = output_dir / f"returned_{slot}.json"
        _write(submission_path, submission)
        report = {
            "schema_version": "ndp50-vocabulary-discovery-validation/v1",
            "status": "passed",
            "reviewer_id": reviewer,
            "reviewer_role": role,
            "submission_id": submission_id,
            "submission_sha256": _sha256(submission_path),
            "case_count": 1,
            "proposal_count": 0,
        }
        receipt_path = output_dir / f"{slot}_receipt.json"
        _write(receipt_path, report)
        vocabulary_reports[slot] = {
            "submission": submission,
            "submission_path": submission_path,
            "report": report,
            "receipt_path": receipt_path,
        }

    def fake_validate_discovery(
        submission,
        template,
        *,
        evidence_registry,
        submission_sha256,
    ):
        return {
            **vocabulary_reports[submission["slot"]]["report"],
            "submission_sha256": submission_sha256,
        }

    monkeypatch.setattr(
        assignments, "validate_discovery", fake_validate_discovery
    )

    manifest = json.loads(
        (output_dir / "return_manifest_neutral_v1.json").read_text()
    )
    roster = json.loads(
        (output_dir / "assignment_roster_neutral_v1.json").read_text()
    )
    roster["status"] = "frozen_before_human_submissions"
    roster["operator_id"] = "study-operator-01"
    roster["frozen_at"] = "2026-07-27T10:02:00Z"
    roster["assignment_distribution"].update(
        {
            "receipt": {
                "filename": "distribution_receipt.json",
                "sha256": "1" * 64,
                "canonical_sha256": "2" * 64,
            },
            "validation": {
                "filename": "distribution_validation.json",
                "sha256": "3" * 64,
                "schema_version": (
                    "ndp50-human-assignment-distribution-validation/v1"
                ),
                "status": "passed",
            },
            "packet_count": 4,
            "sealed_identity_match_count": 0,
            "extra_file_count": 0,
            "packet_root_outside_repository": True,
            "validated_before_roster_freeze": True,
            "validated_at": "2026-07-27T09:59:00Z",
        }
    )
    roster_values = {
        "governance_stewardship": (
            "steward-01",
            "institutional_data_steward",
            False,
            False,
        ),
        "governance_accountable_approval": (
            "pi-01",
            "principal_investigator",
            True,
            True,
        ),
        "vocabulary_discovery_a": (
            "curator-01",
            "scientific_metadata_curator",
            False,
            False,
        ),
        "vocabulary_discovery_b": (
            "methodologist-01",
            "annotation_methodologist",
            False,
            False,
        ),
        "feedback_response_signoff": (
            "swathi-01",
            "postdoctoral_research_collaborator",
            False,
            True,
        ),
    }
    for slot_id, (
        reviewer_id,
        role,
        developer,
        collaborator,
    ) in roster_values.items():
        slot = roster["slots"][slot_id]
        slot.update(
            {
                "reviewer_id": reviewer_id,
                "reviewer_role": role,
                "qualification_summary": (
                    f"Qualified for {slot_id} under the released contract."
                ),
                "conflict_of_interest_declared": False,
                "developer_participation": developer,
                "project_collaborator": collaborator,
                "assigned_at": "2026-07-27T10:00:00Z",
                "distribution_packet_id": slot["assignment_id"],
                "distribution_packet_manifest_sha256": hashlib.sha256(
                    slot["assignment_id"].encode("utf-8")
                ).hexdigest(),
                "packet_delivered_at": "2026-07-27T10:00:30Z",
                "received_exact_packet_attested": True,
                "no_other_assignment_packet_received": True,
                "accepted_at": "2026-07-27T10:01:00Z",
                "accepted_assignment_contract": True,
                "no_test_data_access": True,
                "no_model_outputs_visible": True,
            }
        )
    roster["prework_attestations"] = {
        key: True for key in roster["prework_attestations"]
    }
    roster["completion_attestation"] = True
    roster_path = output_dir / "assignment_roster_completed.json"
    _write(roster_path, roster)
    roster_receipt = replay_assignment_roster_validation(
        roster,
        roster_path=roster_path,
        assignment_release_path=(
            output_dir / "assignment_release_v1.json"
        ),
        handoff_path=output_dir.parent / "human_handoff.json",
        distribution_spec_path=(
            output_dir / "assignment_distribution_spec_v1.json"
        ),
        study_root=root,
    )
    roster_receipt_path = output_dir / "assignment_roster_validation.json"
    _write(roster_receipt_path, roster_receipt)

    manifest["status"] = "completed_pending_validator_acceptance"
    manifest["assignment_roster"] = _binding(roster_path, root)
    manifest["assignment_roster_validation_receipt"] = _binding(
        roster_receipt_path, root
    )
    manifest["returns"]["data_governance_review"] = {
        "stewardship_reviewer_id": "steward-01",
        "accountable_approver_id": "pi-01",
        "submission": _binding(governance_path, root),
        "validation_receipt": _binding(governance_receipt_path, root),
    }
    manifest["returns"]["feedback_response_signoff"] = {
        "reviewer_id": "swathi-01",
        "submission": _binding(feedback_path, root),
        "validation_receipt": _binding(feedback_receipt_path, root),
    }
    for slot, item in vocabulary_reports.items():
        manifest["returns"][slot] = {
            "reviewer_id": item["report"]["reviewer_id"],
            "reviewer_role": item["report"]["reviewer_role"],
            "submission_id": item["report"]["submission_id"],
            "submission": _binding(item["submission_path"], root),
            "validation_receipt": _binding(item["receipt_path"], root),
        }
    manifest["dual_freeze_record"] = {
        "operator_id": "study-operator-01",
        "frozen_on": "2026-07-27",
        "discovery_a_sha256": vocabulary_reports[
            "vocabulary_discovery_a"
        ]["report"]["submission_sha256"],
        "discovery_b_sha256": vocabulary_reports[
            "vocabulary_discovery_b"
        ]["report"]["submission_sha256"],
        "both_receipts_passed_before_comparison": True,
        "no_cross_review_visibility_before_freeze": True,
        "candidate_catalog_not_built_before_freeze": True,
    }
    manifest["completion_attestation"] = True
    manifest_path = output_dir / "return_manifest_completed.json"
    _write(manifest_path, manifest)
    return manifest_path, manifest


def test_return_manifest_requires_atomic_independent_dual_freeze(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, handoff_path = _fixture(tmp_path)
    output_dir = root / "semantic" / "human_assignments"
    prepare_assignment_package(
        handoff_path=handoff_path,
        study_root=root,
        output_dir=output_dir,
    )
    manifest_path, manifest = _completed_returns(
        root=root,
        output_dir=output_dir,
        monkeypatch=monkeypatch,
    )

    report = validate_return_manifest(
        manifest,
        manifest_path=manifest_path,
        release_path=output_dir / "assignment_release_v1.json",
        handoff_path=handoff_path,
        study_root=root,
    )

    assert report["status"] == "passed"
    assert report["vocabulary_reviewer_ids_distinct"] is True
    assert report["required_role_coverage_met"] is True
    assert report["assignment_roster_frozen_before_submissions"] is True
    assert report["next_authorized_action"].startswith("build_vocabulary")


def test_return_manifest_rejects_feedback_reviewer_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, handoff_path = _fixture(tmp_path)
    output_dir = root / "semantic" / "human_assignments"
    prepare_assignment_package(
        handoff_path=handoff_path,
        study_root=root,
        output_dir=output_dir,
    )
    manifest_path, manifest = _completed_returns(
        root=root,
        output_dir=output_dir,
        monkeypatch=monkeypatch,
    )
    manifest["returns"]["feedback_response_signoff"][
        "reviewer_id"
    ] = "different-collaborator"
    _write(manifest_path, manifest)

    with pytest.raises(
        NDPHumanAssignmentError,
        match="feedback-response return reviewer ID mismatch",
    ):
        validate_return_manifest(
            manifest,
            manifest_path=manifest_path,
            release_path=output_dir / "assignment_release_v1.json",
            handoff_path=handoff_path,
            study_root=root,
        )


def test_return_manifest_rejects_cross_review_visibility(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, handoff_path = _fixture(tmp_path)
    output_dir = root / "semantic" / "human_assignments"
    prepare_assignment_package(
        handoff_path=handoff_path,
        study_root=root,
        output_dir=output_dir,
    )
    manifest_path, manifest = _completed_returns(
        root=root,
        output_dir=output_dir,
        monkeypatch=monkeypatch,
    )
    manifest["dual_freeze_record"][
        "no_cross_review_visibility_before_freeze"
    ] = False
    _write(manifest_path, manifest)

    with pytest.raises(
        NDPHumanAssignmentError,
        match="no_cross_review_visibility_before_freeze",
    ):
        validate_return_manifest(
            manifest,
            manifest_path=manifest_path,
            release_path=output_dir / "assignment_release_v1.json",
            handoff_path=handoff_path,
            study_root=root,
        )


def test_return_manifest_rejects_reused_vocabulary_reviewer(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, handoff_path = _fixture(tmp_path)
    output_dir = root / "semantic" / "human_assignments"
    prepare_assignment_package(
        handoff_path=handoff_path,
        study_root=root,
        output_dir=output_dir,
    )
    manifest_path, manifest = _completed_returns(
        root=root,
        output_dir=output_dir,
        monkeypatch=monkeypatch,
    )
    second = manifest["returns"]["vocabulary_discovery_b"]
    second["reviewer_id"] = "curator-01"
    original_validator = assignments.validate_discovery

    def duplicate_reviewer(*args, **kwargs):
        report = copy.deepcopy(original_validator(*args, **kwargs))
        if report["submission_id"] == "discovery-b-01":
            report["reviewer_id"] = "curator-01"
        return report

    monkeypatch.setattr(
        assignments, "validate_discovery", duplicate_reviewer
    )
    second_receipt_path = (
        root / second["validation_receipt"]["file"]
    ).resolve()
    receipt = json.loads(second_receipt_path.read_text())
    receipt["reviewer_id"] = "curator-01"
    _write(second_receipt_path, receipt)
    second["validation_receipt"] = _binding(second_receipt_path, root)
    _write(manifest_path, manifest)

    with pytest.raises(
        NDPHumanAssignmentError,
        match="identity does not match|reviewers must be distinct",
    ):
        validate_return_manifest(
            manifest,
            manifest_path=manifest_path,
            release_path=output_dir / "assignment_release_v1.json",
            handoff_path=handoff_path,
            study_root=root,
        )


def _prepare_decision_release(
    *,
    root: Path,
    handoff_path: Path,
    output_dir: Path,
    monkeypatch,
) -> tuple[Path, Path, Path, dict]:
    initial_return_path, initial_manifest = _completed_returns(
        root=root,
        output_dir=output_dir,
        monkeypatch=monkeypatch,
    )
    initial_release_path = output_dir / "assignment_release_v1.json"
    initial_validation = validate_return_manifest(
        initial_manifest,
        manifest_path=initial_return_path,
        release_path=initial_release_path,
        handoff_path=handoff_path,
        study_root=root,
    )
    initial_validation_path = output_dir / "return_validation.json"
    _write(initial_validation_path, initial_validation)
    candidate_catalog = {
        "schema_version": "ndp50-vocabulary-candidate-catalog/v1",
        "status": "ready_for_independent_candidate_decisions",
        "candidate_count": 1,
        "candidates": [
            {
                "candidate_id": "vocab-soil-moisture",
                "proposal": {
                    "category": "semantic_type",
                    "term": "soil_moisture",
                },
            }
        ],
    }
    monkeypatch.setattr(
        assignments,
        "build_candidate_catalog",
        lambda *args, **kwargs: copy.deepcopy(candidate_catalog),
    )
    decision_dir = root / "semantic" / "decision_assignments"
    release = prepare_decision_assignment_package(
        return_manifest_path=initial_return_path,
        return_validation_path=initial_validation_path,
        initial_release_path=initial_release_path,
        handoff_path=handoff_path,
        study_root=root,
        output_dir=decision_dir,
    )
    return (
        decision_dir,
        initial_return_path,
        initial_validation_path,
        release,
    )


def test_post_discovery_transition_is_replayed_and_uses_fresh_pair(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, handoff_path = _fixture(tmp_path)
    output_dir = root / "semantic" / "human_assignments"
    prepare_assignment_package(
        handoff_path=handoff_path,
        study_root=root,
        output_dir=output_dir,
    )
    (
        decision_dir,
        initial_return_path,
        initial_validation_path,
        release,
    ) = _prepare_decision_release(
        root=root,
        handoff_path=handoff_path,
        output_dir=output_dir,
        monkeypatch=monkeypatch,
    )
    release_path = decision_dir / "decision_assignment_release_v1.json"

    validation = validate_decision_assignment_release(
        release,
        release_path=release_path,
        return_manifest_path=initial_return_path,
        return_validation_path=initial_validation_path,
        initial_release_path=output_dir / "assignment_release_v1.json",
        handoff_path=handoff_path,
        study_root=root,
    )

    assert validation["status"] == "passed"
    assert release["reviewer_continuity_policy"]["fresh_pair_required"] is True
    assert release["assignment_count"] == 2
    payload_a = (
        decision_dir / "vocabulary_candidate_decision_a_payload.json"
    )
    payload_b = (
        decision_dir / "vocabulary_candidate_decision_b_payload.json"
    )
    assert payload_a.read_bytes() == payload_b.read_bytes()
    assert release["independence_controls"][
        "human_candidate_decisions_present_at_release"
    ] is False


def test_post_discovery_transition_rejects_catalog_tampering(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, handoff_path = _fixture(tmp_path)
    output_dir = root / "semantic" / "human_assignments"
    prepare_assignment_package(
        handoff_path=handoff_path,
        study_root=root,
        output_dir=output_dir,
    )
    (
        decision_dir,
        initial_return_path,
        initial_validation_path,
        _,
    ) = _prepare_decision_release(
        root=root,
        handoff_path=handoff_path,
        output_dir=output_dir,
        monkeypatch=monkeypatch,
    )
    release_path = decision_dir / "decision_assignment_release_v1.json"
    catalog_path = decision_dir / "vocabulary_candidate_catalog.json"
    catalog = json.loads(catalog_path.read_text())
    catalog["automatic_acceptance"] = True
    _write(catalog_path, catalog)

    validation = validate_decision_assignment_release(
        json.loads(release_path.read_text()),
        release_path=release_path,
        return_manifest_path=initial_return_path,
        return_validation_path=initial_validation_path,
        initial_release_path=output_dir / "assignment_release_v1.json",
        handoff_path=handoff_path,
        study_root=root,
    )

    assert validation["status"] == "failed"
    assert "does not replay" in validation["detail"]


def _completed_decision_return(
    *,
    root: Path,
    decision_dir: Path,
    monkeypatch,
    reviewer_b: str = "decision-methodologist-01",
) -> tuple[Path, dict]:
    reports = {}
    for suffix, reviewer, role in (
        (
            "a",
            "decision-curator-01",
            "scientific_metadata_curator",
        ),
        ("b", reviewer_b, "annotation_methodologist"),
    ):
        slot = f"vocabulary_candidate_decision_{suffix}"
        submission = {
            "slot": slot,
            "reviewer_id": reviewer,
            "reviewer_role": role,
            "submission_id": f"candidate-decision-{suffix}-01",
        }
        submission_path = decision_dir / f"returned_{slot}.json"
        _write(submission_path, submission)
        report = {
            "schema_version": "ndp50-vocabulary-decision-validation/v1",
            "status": "passed",
            "reviewer_id": reviewer,
            "reviewer_role": role,
            "submission_id": submission["submission_id"],
            "submission_sha256": _sha256(submission_path),
            "candidate_count": 1,
        }
        receipt_path = decision_dir / f"{slot}_receipt.json"
        _write(receipt_path, report)
        reports[slot] = {
            "submission_path": submission_path,
            "report": report,
            "receipt_path": receipt_path,
        }

    def fake_validate_decision(
        submission,
        catalog,
        *,
        evidence_registry,
        submission_sha256,
    ):
        return {
            **reports[submission["slot"]]["report"],
            "submission_sha256": submission_sha256,
        }

    monkeypatch.setattr(assignments, "validate_decision", fake_validate_decision)
    manifest = json.loads(
        (
            decision_dir / "decision_return_manifest_neutral_v1.json"
        ).read_text()
    )
    manifest["status"] = "completed_pending_validator_acceptance"
    for slot, item in reports.items():
        manifest["returns"][slot] = {
            "reviewer_id": item["report"]["reviewer_id"],
            "reviewer_role": item["report"]["reviewer_role"],
            "submission_id": item["report"]["submission_id"],
            "submission": _binding(item["submission_path"], root),
            "validation_receipt": _binding(item["receipt_path"], root),
        }
    manifest["dual_freeze_record"] = {
        "operator_id": "study-operator-02",
        "frozen_on": "2026-07-28",
        "decision_a_sha256": reports[
            "vocabulary_candidate_decision_a"
        ]["report"]["submission_sha256"],
        "decision_b_sha256": reports[
            "vocabulary_candidate_decision_b"
        ]["report"]["submission_sha256"],
        "both_receipts_passed_before_comparison": True,
        "no_cross_decision_visibility_before_freeze": True,
        "disagreement_worksheet_not_built_before_freeze": True,
        "consensus_not_started_before_freeze": True,
    }
    manifest["completion_attestation"] = True
    path = decision_dir / "decision_return_manifest_completed.json"
    _write(path, manifest)
    return path, manifest


def test_candidate_decision_return_requires_fresh_isolated_pair(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, handoff_path = _fixture(tmp_path)
    output_dir = root / "semantic" / "human_assignments"
    prepare_assignment_package(
        handoff_path=handoff_path,
        study_root=root,
        output_dir=output_dir,
    )
    (
        decision_dir,
        initial_return_path,
        initial_validation_path,
        _,
    ) = _prepare_decision_release(
        root=root,
        handoff_path=handoff_path,
        output_dir=output_dir,
        monkeypatch=monkeypatch,
    )
    decision_return_path, decision_return = _completed_decision_return(
        root=root,
        decision_dir=decision_dir,
        monkeypatch=monkeypatch,
    )

    report = validate_decision_return_manifest(
        decision_return,
        manifest_path=decision_return_path,
        release_path=decision_dir / "decision_assignment_release_v1.json",
        initial_return_path=initial_return_path,
        initial_return_validation_path=initial_validation_path,
        initial_release_path=output_dir / "assignment_release_v1.json",
        handoff_path=handoff_path,
        study_root=root,
    )

    assert report["status"] == "passed"
    assert report["decision_reviewers_fresh_from_discovery"] is True
    assert report["dual_freeze_attested"] is True


def test_candidate_decision_return_rejects_discovery_reviewer_reuse(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, handoff_path = _fixture(tmp_path)
    output_dir = root / "semantic" / "human_assignments"
    prepare_assignment_package(
        handoff_path=handoff_path,
        study_root=root,
        output_dir=output_dir,
    )
    (
        decision_dir,
        initial_return_path,
        initial_validation_path,
        _,
    ) = _prepare_decision_release(
        root=root,
        handoff_path=handoff_path,
        output_dir=output_dir,
        monkeypatch=monkeypatch,
    )
    decision_return_path, decision_return = _completed_decision_return(
        root=root,
        decision_dir=decision_dir,
        monkeypatch=monkeypatch,
        reviewer_b="methodologist-01",
    )

    with pytest.raises(
        NDPHumanAssignmentError,
        match="must be fresh from discovery",
    ):
        validate_decision_return_manifest(
            decision_return,
            manifest_path=decision_return_path,
            release_path=(
                decision_dir / "decision_assignment_release_v1.json"
            ),
            initial_return_path=initial_return_path,
            initial_return_validation_path=initial_validation_path,
            initial_release_path=output_dir / "assignment_release_v1.json",
            handoff_path=handoff_path,
            study_root=root,
        )


def _prepare_consensus_release(
    *,
    root: Path,
    handoff_path: Path,
    output_dir: Path,
    decision_dir: Path,
    initial_return_path: Path,
    initial_validation_path: Path,
    monkeypatch,
) -> tuple[Path, Path, Path, dict]:
    decision_return_path, decision_return = _completed_decision_return(
        root=root,
        decision_dir=decision_dir,
        monkeypatch=monkeypatch,
    )
    decision_release_path = (
        decision_dir / "decision_assignment_release_v1.json"
    )
    decision_validation = validate_decision_return_manifest(
        decision_return,
        manifest_path=decision_return_path,
        release_path=decision_release_path,
        initial_return_path=initial_return_path,
        initial_return_validation_path=initial_validation_path,
        initial_release_path=output_dir / "assignment_release_v1.json",
        handoff_path=handoff_path,
        study_root=root,
    )
    decision_validation_path = (
        decision_dir / "decision_return_validation.json"
    )
    _write(decision_validation_path, decision_validation)
    worksheet = {
        "schema_version": "ndp50-vocabulary-disagreement/v1",
        "status": "ready_for_human_adjudication",
        "candidate_catalog_sha256": "c" * 64,
        "decision_a": {
            "reviewer_id": "decision-curator-01",
            "reviewer_role": "scientific_metadata_curator",
            "submission_id": "candidate-decision-a-01",
            "submission_sha256": decision_validation["decision_a_sha256"],
        },
        "decision_b": {
            "reviewer_id": "decision-methodologist-01",
            "reviewer_role": "annotation_methodologist",
            "submission_id": "candidate-decision-b-01",
            "submission_sha256": decision_validation["decision_b_sha256"],
        },
        "slot_count": 1,
        "agreement_count": 0,
        "disagreement_count": 1,
        "slots": [
            {
                "slot_id": "policy:logical_types_fixed",
                "value_a": True,
                "value_b": False,
                "agreed": False,
                "status": "pending_human_adjudication",
            }
        ],
        "automatic_adjudication": False,
    }
    monkeypatch.setattr(
        assignments,
        "compare_decisions",
        lambda *args, **kwargs: copy.deepcopy(worksheet),
    )
    consensus_dir = root / "semantic" / "consensus_assignment"
    release = prepare_consensus_assignment_package(
        decision_return_path=decision_return_path,
        decision_return_validation_path=decision_validation_path,
        decision_release_path=decision_release_path,
        initial_return_path=initial_return_path,
        initial_return_validation_path=initial_validation_path,
        initial_release_path=output_dir / "assignment_release_v1.json",
        handoff_path=handoff_path,
        study_root=root,
        output_dir=consensus_dir,
    )
    return (
        consensus_dir,
        decision_return_path,
        decision_validation_path,
        release,
    )


def test_consensus_assignment_requires_replayed_decision_dual_freeze(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, handoff_path = _fixture(tmp_path)
    output_dir = root / "semantic" / "human_assignments"
    prepare_assignment_package(
        handoff_path=handoff_path,
        study_root=root,
        output_dir=output_dir,
    )
    (
        decision_dir,
        initial_return_path,
        initial_validation_path,
        _,
    ) = _prepare_decision_release(
        root=root,
        handoff_path=handoff_path,
        output_dir=output_dir,
        monkeypatch=monkeypatch,
    )
    (
        consensus_dir,
        decision_return_path,
        decision_validation_path,
        release,
    ) = _prepare_consensus_release(
        root=root,
        handoff_path=handoff_path,
        output_dir=output_dir,
        decision_dir=decision_dir,
        initial_return_path=initial_return_path,
        initial_validation_path=initial_validation_path,
        monkeypatch=monkeypatch,
    )
    release_path = consensus_dir / "consensus_assignment_release_v1.json"

    validation = validate_consensus_assignment_release(
        release,
        release_path=release_path,
        decision_return_path=decision_return_path,
        decision_return_validation_path=decision_validation_path,
        decision_release_path=(
            decision_dir / "decision_assignment_release_v1.json"
        ),
        initial_return_path=initial_return_path,
        initial_return_validation_path=initial_validation_path,
        initial_release_path=output_dir / "assignment_release_v1.json",
        handoff_path=handoff_path,
        study_root=root,
    )

    assert validation["status"] == "passed"
    assert release["adjudicator_policy"][
        "fresh_from_discovery_and_decisions_required"
    ] is True
    assignment = json.loads(
        (
            consensus_dir / "vocabulary_consensus_assignment.json"
        ).read_text()
    )
    assert assignment["adjudicator_id"] is None
    assert len(assignment["excluded_reviewer_ids"]) == 4
    assert release["human_consensus_present_at_release"] is False


def test_consensus_return_replays_qualified_independent_adjudication(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, handoff_path = _fixture(tmp_path)
    output_dir = root / "semantic" / "human_assignments"
    prepare_assignment_package(
        handoff_path=handoff_path,
        study_root=root,
        output_dir=output_dir,
    )
    (
        decision_dir,
        initial_return_path,
        initial_validation_path,
        _,
    ) = _prepare_decision_release(
        root=root,
        handoff_path=handoff_path,
        output_dir=output_dir,
        monkeypatch=monkeypatch,
    )
    (
        consensus_dir,
        decision_return_path,
        decision_validation_path,
        _,
    ) = _prepare_consensus_release(
        root=root,
        handoff_path=handoff_path,
        output_dir=output_dir,
        decision_dir=decision_dir,
        initial_return_path=initial_return_path,
        initial_validation_path=initial_validation_path,
        monkeypatch=monkeypatch,
    )
    consensus = {
        "adjudicator_id": "ontology-lead-01",
        "adjudicator_role": "ontology_governance_lead",
    }
    consensus_path = consensus_dir / "returned_consensus.json"
    _write(consensus_path, consensus)
    receipt = {
        "schema_version": "ndp50-vocabulary-consensus-validation/v1",
        "status": "passed",
        "adjudicator_id": "ontology-lead-01",
        "adjudicator_role": "ontology_governance_lead",
        "adjudicator_independent_of_prior_stages": True,
        "consensus_sha256": _sha256(consensus_path),
        "worksheet_sha256": _sha256(
            consensus_dir / "vocabulary_disagreement_worksheet.json"
        ),
        "slot_count": 1,
        "disagreement_count": 1,
        "all_required_policies_accepted": True,
        "corpus_coverage_accepted": True,
    }
    receipt_path = consensus_dir / "consensus_receipt.json"
    _write(receipt_path, receipt)
    monkeypatch.setattr(
        assignments,
        "validate_consensus",
        lambda *args, **kwargs: copy.deepcopy(receipt),
    )
    manifest = json.loads(
        (
            consensus_dir / "consensus_return_manifest_neutral_v1.json"
        ).read_text()
    )
    manifest.update(
        {
            "status": "completed_pending_validator_acceptance",
            "adjudicator_id": "ontology-lead-01",
            "adjudicator_role": "ontology_governance_lead",
            "submission": _binding(consensus_path, root),
            "validation_receipt": _binding(receipt_path, root),
            "completion_attestation": True,
        }
    )
    manifest_path = consensus_dir / "consensus_return_completed.json"
    _write(manifest_path, manifest)

    report = validate_consensus_return_manifest(
        manifest,
        manifest_path=manifest_path,
        release_path=consensus_dir / "consensus_assignment_release_v1.json",
        decision_return_path=decision_return_path,
        decision_return_validation_path=decision_validation_path,
        decision_release_path=(
            decision_dir / "decision_assignment_release_v1.json"
        ),
        initial_return_path=initial_return_path,
        initial_return_validation_path=initial_validation_path,
        initial_release_path=output_dir / "assignment_release_v1.json",
        handoff_path=handoff_path,
        study_root=root,
    )

    assert report["status"] == "passed"
    assert report["adjudicator_independent_of_prior_stages"] is True
    assert report["next_authorized_action"].startswith("build_frozen")
