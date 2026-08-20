from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_assignment_distribution import (
    NDPAssignmentDistributionError,
    build_distribution_spec,
    materialize_distribution,
    validate_distribution,
)
from high_fidelity_schema_study.ndp50_assignment_roster import (
    build_roster_template,
    validate_assignment_roster,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
STUDY_ROOT = (
    PACKAGE_ROOT / "data" / "experiments" / "ndp50_v1"
)
ASSIGNMENT_DIR = (
    STUDY_ROOT / "semantic" / "human_assignments_v1"
)
RELEASE_PATH = ASSIGNMENT_DIR / "assignment_release_v1.json"
SPEC_PATH = ASSIGNMENT_DIR / "assignment_distribution_spec_v1.json"
PUBLIC_MANIFEST_PATH = (
    STUDY_ROOT / "preregistration" / "public_package_manifest_v1.json"
)
SELECTION_PATH = STUDY_ROOT / "selection.json"
HANDOFF_PATH = STUDY_ROOT / "semantic" / "human_handoff_v1.json"


def _build_spec() -> dict:
    return build_distribution_spec(
        assignment_release_path=RELEASE_PATH,
        public_manifest_path=PUBLIC_MANIFEST_PATH,
        selection_path=SELECTION_PATH,
        study_root=STUDY_ROOT,
        repo_root=PACKAGE_ROOT,
    )


def _materialize(tmp_path: Path) -> tuple[Path, dict]:
    packet_root = tmp_path / "isolated-reviewer-packets"
    receipt = materialize_distribution(
        spec_path=SPEC_PATH,
        assignment_release_path=RELEASE_PATH,
        public_manifest_path=PUBLIC_MANIFEST_PATH,
        selection_path=SELECTION_PATH,
        study_root=STUDY_ROOT,
        repo_root=PACKAGE_ROOT,
        packet_root=packet_root,
    )
    return packet_root, receipt


def test_production_distribution_spec_replays_and_is_least_access() -> None:
    observed = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    expected = _build_spec()

    assert observed == expected
    assert observed["packet_count"] == 4
    assert observed["distribution_invariants"][
        "packet_roots_must_be_outside_repository"
    ] is True
    assert observed["distribution_invariants"][
        "sealed_test_ids_and_titles_are_scanned"
    ] is True
    manifest = json.loads(
        PUBLIC_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    public_count = manifest["public_scope"]["file_count"]
    release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    wrapper_paths = {
        assignment_id: (
            STUDY_ROOT / binding["file"]
        ).resolve().relative_to(PACKAGE_ROOT).as_posix()
        for assignment_id, binding in release["assignments"].items()
    }
    for packet_id, packet in observed["packets"].items():
        files = {entry["file"] for entry in packet["files"]}
        assert packet["file_count"] >= public_count + 4
        assert packet["reviewer_ids_present"] is False
        assert packet["human_decisions_present"] is False
        assert packet["test_data_access"] == "forbidden"
        assert wrapper_paths[packet_id] in files
        for other_id, path in wrapper_paths.items():
            if other_id != packet_id:
                assert path not in files
                assert path in packet["forbidden_assignment_files"]
    packet_a = observed["packets"]["vocabulary_discovery_a"]
    packet_b = observed["packets"]["vocabulary_discovery_b"]
    payload_a = next(
        item
        for item in packet_a["files"]
        if item["scope"] == "assignment_payload"
    )
    payload_b = next(
        item
        for item in packet_b["files"]
        if item["scope"] == "assignment_payload"
    )
    assert payload_a["sha256"] == payload_b["sha256"]
    assert payload_a["file"] != payload_b["file"]


def test_materialized_packets_replay_without_test_identity_leakage(
    tmp_path: Path,
) -> None:
    packet_root, receipt = _materialize(tmp_path)

    validation = validate_distribution(
        receipt,
        spec_path=SPEC_PATH,
        assignment_release_path=RELEASE_PATH,
        public_manifest_path=PUBLIC_MANIFEST_PATH,
        selection_path=SELECTION_PATH,
        study_root=STUDY_ROOT,
        repo_root=PACKAGE_ROOT,
        packet_root=packet_root,
    )

    assert receipt["status"] == "materialized_and_verified_unassigned"
    assert receipt["packet_count"] == 4
    assert receipt["sealed_identity_match_count"] == 0
    assert receipt["extra_file_count"] == 0
    assert validation["status"] == "passed"
    assert validation["packet_count"] == 4
    assert validation["sealed_identity_match_count"] == 0

    receipt_path = tmp_path / "distribution_receipt.json"
    validation_path = tmp_path / "distribution_validation.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    validation_path.write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    roster = copy.deepcopy(
        build_roster_template(
            assignment_release_path=RELEASE_PATH,
            handoff_path=HANDOFF_PATH,
            distribution_spec_path=SPEC_PATH,
            study_root=STUDY_ROOT,
        )
    )
    roster["status"] = "frozen_before_human_submissions"
    roster["operator_id"] = "integration-test-operator"
    roster["frozen_at"] = "2026-07-27T10:04:00Z"
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
            "validated_at": "2026-07-27T10:00:00Z",
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
        reviewer_role,
        developer,
        collaborator,
    ) in roster_values.items():
        slot = roster["slots"][slot_id]
        packet_id = slot["assignment_id"]
        slot.update(
            {
                "reviewer_id": reviewer_id,
                "reviewer_role": reviewer_role,
                "qualification_summary": "Qualified integration fixture.",
                "conflict_of_interest_declared": False,
                "developer_participation": developer,
                "project_collaborator": collaborator,
                "assigned_at": "2026-07-27T10:01:00Z",
                "distribution_packet_id": packet_id,
                "distribution_packet_manifest_sha256": receipt[
                    "packets"
                ][packet_id]["packet_manifest_sha256"],
                "packet_delivered_at": "2026-07-27T10:02:00Z",
                "received_exact_packet_attested": True,
                "no_other_assignment_packet_received": True,
                "accepted_at": "2026-07-27T10:03:00Z",
                "accepted_assignment_contract": True,
                "no_test_data_access": True,
                "no_model_outputs_visible": True,
            }
        )
    roster["prework_attestations"] = {
        key: True for key in roster["prework_attestations"]
    }
    roster["completion_attestation"] = True
    roster_path = tmp_path / "completed_assignment_roster.json"
    roster_path.write_text(
        json.dumps(roster, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    roster_validation = validate_assignment_roster(
        roster,
        roster_path=roster_path,
        assignment_release_path=RELEASE_PATH,
        handoff_path=HANDOFF_PATH,
        distribution_spec_path=SPEC_PATH,
        distribution_receipt_path=receipt_path,
        distribution_validation_path=validation_path,
        public_manifest_path=PUBLIC_MANIFEST_PATH,
        selection_path=SELECTION_PATH,
        packet_root=packet_root,
        study_root=STUDY_ROOT,
        repo_root=PACKAGE_ROOT,
    )
    assert roster_validation[
        "distribution_validated_before_roster_freeze"
    ] is True
    assert roster_validation["packet_delivery_attested"] is True


def test_distribution_validation_rejects_extra_packet_material(
    tmp_path: Path,
) -> None:
    packet_root, receipt = _materialize(tmp_path)
    extra = (
        packet_root
        / "vocab-a"
        / "unapproved-reviewer-note.txt"
    )
    extra.write_text("not in the packet manifest\n", encoding="utf-8")

    with pytest.raises(
        NDPAssignmentDistributionError,
        match="extra entries",
    ):
        validate_distribution(
            receipt,
            spec_path=SPEC_PATH,
            assignment_release_path=RELEASE_PATH,
            public_manifest_path=PUBLIC_MANIFEST_PATH,
            selection_path=SELECTION_PATH,
            study_root=STUDY_ROOT,
            repo_root=PACKAGE_ROOT,
            packet_root=packet_root,
        )


def test_distribution_refuses_packet_root_inside_repository() -> None:
    for forbidden_root in (
        PACKAGE_ROOT / "forbidden-packet-root",
        PACKAGE_ROOT.parent / "forbidden-packet-root",
    ):
        with pytest.raises(
            NDPAssignmentDistributionError,
            match="outside the repository",
        ):
            materialize_distribution(
                spec_path=SPEC_PATH,
                assignment_release_path=RELEASE_PATH,
                public_manifest_path=PUBLIC_MANIFEST_PATH,
                selection_path=SELECTION_PATH,
                study_root=STUDY_ROOT,
                repo_root=PACKAGE_ROOT,
                packet_root=forbidden_root,
            )
