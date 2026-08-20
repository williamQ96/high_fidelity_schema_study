from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import high_fidelity_schema_study.ndp50_assignment_roster as roster_module
from high_fidelity_schema_study.ndp50_assignment_roster import (
    NDPAssignmentRosterError,
    build_roster_template,
    replay_assignment_roster_validation,
    validate_assignment_roster,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _binding(path: Path, root: Path) -> dict:
    return {
        "file": path.resolve().relative_to(root.resolve()).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _inputs(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, Path, Path]:
    root = tmp_path / "study"
    handoff_path = root / "semantic" / "human_handoff.json"
    _write(
        handoff_path,
        {
            "schema_version": "ndp50-human-handoff/v1",
            "status": "human_work_released_downstream_locked",
        },
    )
    assignment_dir = root / "semantic" / "human_assignments"
    assignments = {}
    for assignment_id in (
        "data_governance_review",
        "feedback_response_signoff",
        "vocabulary_discovery_a",
        "vocabulary_discovery_b",
    ):
        path = assignment_dir / f"{assignment_id}.json"
        _write(path, {"assignment_id": assignment_id})
        assignments[assignment_id] = _binding(path, root)
    release_path = assignment_dir / "assignment_release.json"
    _write(
        release_path,
        {
            "schema_version": "ndp50-human-assignment-release/v1",
            "status": "released_unassigned",
            "assignment_count": 4,
            "assignments": assignments,
            "handoff": _binding(handoff_path, root),
        },
    )
    packet_slots = {
        "data_governance_review": [
            "governance_stewardship",
            "governance_accountable_approval",
        ],
        "feedback_response_signoff": ["feedback_response_signoff"],
        "vocabulary_discovery_a": ["vocabulary_discovery_a"],
        "vocabulary_discovery_b": ["vocabulary_discovery_b"],
    }
    distribution_spec_path = (
        assignment_dir / "assignment_distribution_spec.json"
    )
    _write(
        distribution_spec_path,
        {
            "schema_version": (
                "ndp50-human-assignment-distribution-spec/v1"
            ),
            "status": "neutral_packets_specified_unmaterialized",
            "assignment_release": _binding(release_path, root),
            "packet_count": 4,
            "packets": {
                packet_id: {"roster_slots": slots}
                for packet_id, slots in packet_slots.items()
            },
        },
    )
    receipt = {
        "schema_version": (
            "ndp50-human-assignment-distribution-receipt/v1"
        ),
        "status": "materialized_and_verified_unassigned",
        "packets": {
            packet_id: {
                "packet_manifest_sha256": hashlib.sha256(
                    packet_id.encode("utf-8")
                ).hexdigest()
            }
            for packet_id in packet_slots
        },
    }
    receipt_path = tmp_path / "private" / "distribution_receipt.json"
    _write(receipt_path, receipt)
    canonical_receipt = hashlib.sha256(
        json.dumps(
            receipt,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    validation = {
        "schema_version": (
            "ndp50-human-assignment-distribution-validation/v1"
        ),
        "status": "passed",
        "distribution_receipt_canonical_sha256": canonical_receipt,
        "packet_count": 4,
        "sealed_identity_match_count": 0,
        "extra_file_count": 0,
    }
    validation_path = (
        tmp_path / "private" / "distribution_validation.json"
    )
    _write(validation_path, validation)
    return (
        root,
        handoff_path,
        release_path,
        distribution_spec_path,
        receipt_path,
        validation_path,
    )


def _completed(
    template: dict,
    *,
    receipt_path: Path,
    validation_path: Path,
) -> dict:
    roster = copy.deepcopy(template)
    roster["status"] = "frozen_before_human_submissions"
    roster["operator_id"] = "operator-01"
    roster["frozen_at"] = "2026-07-27T10:02:00Z"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    roster["assignment_distribution"].update(
        {
            "receipt": {
                "filename": receipt_path.name,
                "sha256": hashlib.sha256(
                    receipt_path.read_bytes()
                ).hexdigest(),
                "canonical_sha256": validation[
                    "distribution_receipt_canonical_sha256"
                ],
            },
            "validation": {
                "filename": validation_path.name,
                "sha256": hashlib.sha256(
                    validation_path.read_bytes()
                ).hexdigest(),
                "schema_version": validation["schema_version"],
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
    values = {
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
    for slot_id, (reviewer, role, developer, collaborator) in values.items():
        assignment_id = roster["slots"][slot_id]["assignment_id"]
        roster["slots"][slot_id].update(
            {
                "reviewer_id": reviewer,
                "reviewer_role": role,
                "qualification_summary": "Qualified for the assigned role.",
                "conflict_of_interest_declared": False,
                "developer_participation": developer,
                "project_collaborator": collaborator,
                "assigned_at": "2026-07-27T10:00:00Z",
                "distribution_packet_id": assignment_id,
                "distribution_packet_manifest_sha256": hashlib.sha256(
                    assignment_id.encode("utf-8")
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
    return roster


def test_roster_freezes_five_roles_before_submissions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (
        root,
        handoff_path,
        release_path,
        distribution_spec_path,
        receipt_path,
        validation_path,
    ) = _inputs(tmp_path)
    template = build_roster_template(
        assignment_release_path=release_path,
        handoff_path=handoff_path,
        distribution_spec_path=distribution_spec_path,
        study_root=root,
    )
    roster = _completed(
        template,
        receipt_path=receipt_path,
        validation_path=validation_path,
    )
    roster_path = root / "semantic" / "human_assignments" / "roster.json"
    _write(roster_path, roster)
    expected_validation = json.loads(
        validation_path.read_text(encoding="utf-8")
    )
    monkeypatch.setattr(
        roster_module,
        "validate_distribution",
        lambda receipt, **kwargs: expected_validation,
    )

    report = validate_assignment_roster(
        roster,
        roster_path=roster_path,
        assignment_release_path=release_path,
        handoff_path=handoff_path,
        distribution_spec_path=distribution_spec_path,
        distribution_receipt_path=receipt_path,
        distribution_validation_path=validation_path,
        public_manifest_path=root / "public_manifest.json",
        selection_path=root / "selection.json",
        packet_root=tmp_path / "private" / "packets",
        study_root=root,
        repo_root=root,
    )

    assert report["status"] == "passed"
    assert report["assigned_slot_count"] == 5
    assert report["human_submissions_present"] is False
    assert report[
        "feedback_collaborator_excluded_from_independent_roles"
    ] is True
    assert report["distribution_validated_before_roster_freeze"] is True
    assert report["packet_delivery_attested"] is True


def test_roster_rejects_postdoc_in_independent_vocabulary_role(
    tmp_path: Path,
) -> None:
    (
        root,
        handoff_path,
        release_path,
        distribution_spec_path,
        receipt_path,
        validation_path,
    ) = _inputs(tmp_path)
    roster = _completed(
        build_roster_template(
            assignment_release_path=release_path,
            handoff_path=handoff_path,
            distribution_spec_path=distribution_spec_path,
            study_root=root,
        ),
        receipt_path=receipt_path,
        validation_path=validation_path,
    )
    roster["slots"]["vocabulary_discovery_a"]["reviewer_id"] = "swathi-01"
    roster_path = root / "semantic" / "human_assignments" / "roster.json"
    _write(roster_path, roster)

    with pytest.raises(
        NDPAssignmentRosterError,
        match="feedback collaborator cannot fill",
    ):
        replay_assignment_roster_validation(
            roster,
            roster_path=roster_path,
            assignment_release_path=release_path,
            handoff_path=handoff_path,
            distribution_spec_path=distribution_spec_path,
            study_root=root,
        )


def test_roster_rejects_acceptance_after_freeze(tmp_path: Path) -> None:
    (
        root,
        handoff_path,
        release_path,
        distribution_spec_path,
        receipt_path,
        validation_path,
    ) = _inputs(tmp_path)
    roster = _completed(
        build_roster_template(
            assignment_release_path=release_path,
            handoff_path=handoff_path,
            distribution_spec_path=distribution_spec_path,
            study_root=root,
        ),
        receipt_path=receipt_path,
        validation_path=validation_path,
    )
    roster["slots"]["vocabulary_discovery_b"]["accepted_at"] = (
        "2026-07-27T10:03:00Z"
    )
    roster_path = root / "semantic" / "human_assignments" / "roster.json"
    _write(roster_path, roster)

    with pytest.raises(
        NDPAssignmentRosterError,
        match="timestamps are out of order",
    ):
        replay_assignment_roster_validation(
            roster,
            roster_path=roster_path,
            assignment_release_path=release_path,
            handoff_path=handoff_path,
            distribution_spec_path=distribution_spec_path,
            study_root=root,
        )
