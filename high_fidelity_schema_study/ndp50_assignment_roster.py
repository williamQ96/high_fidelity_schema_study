from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .ndp50_assignment_distribution import (
    PACKET_ROSTER_SLOTS,
    RECEIPT_SCHEMA_VERSION as DISTRIBUTION_RECEIPT_SCHEMA_VERSION,
    SPEC_SCHEMA_VERSION as DISTRIBUTION_SPEC_SCHEMA_VERSION,
    VALIDATION_SCHEMA_VERSION as DISTRIBUTION_VALIDATION_SCHEMA_VERSION,
    _repository_boundary,
    validate_distribution,
)


ROSTER_SCHEMA_VERSION = "ndp50-human-assignment-roster/v1"
ROSTER_VALIDATION_SCHEMA_VERSION = (
    "ndp50-human-assignment-roster-validation/v1"
)
RELEASE_SCHEMA_VERSION = "ndp50-human-assignment-release/v1"
HANDOFF_SCHEMA_VERSION = "ndp50-human-handoff/v1"
PLACEHOLDER_TOKENS = ("replace-with", "placeholder", "todo", "tbd")
SLOT_CONTRACTS = {
    "governance_stewardship": {
        "assignment_id": "data_governance_review",
        "assignment_role": "stewardship_review",
        "allowed_roles": [
            "institutional_data_steward",
            "research_compliance_reviewer",
        ],
        "developer_policy": "forbidden",
        "project_collaborator_policy": "must_declare",
        "independent_reviewer": True,
    },
    "governance_accountable_approval": {
        "assignment_id": "data_governance_review",
        "assignment_role": "accountable_approval",
        "allowed_roles": [
            "principal_investigator",
            "institutional_data_controller",
        ],
        "developer_policy": "must_declare",
        "project_collaborator_policy": "must_declare",
        "independent_reviewer": False,
    },
    "vocabulary_discovery_a": {
        "assignment_id": "vocabulary_discovery_a",
        "assignment_role": "scientific_metadata_curator",
        "allowed_roles": ["scientific_metadata_curator"],
        "developer_policy": "forbidden",
        "project_collaborator_policy": "forbidden",
        "independent_reviewer": True,
    },
    "vocabulary_discovery_b": {
        "assignment_id": "vocabulary_discovery_b",
        "assignment_role": "annotation_methodologist",
        "allowed_roles": ["annotation_methodologist"],
        "developer_policy": "forbidden",
        "project_collaborator_policy": "forbidden",
        "independent_reviewer": True,
    },
    "feedback_response_signoff": {
        "assignment_id": "feedback_response_signoff",
        "assignment_role": "postdoctoral_research_collaborator",
        "allowed_roles": ["postdoctoral_research_collaborator"],
        "developer_policy": "forbidden",
        "project_collaborator_policy": "required",
        "independent_reviewer": False,
    },
}


class NDPAssignmentRosterError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _binding(path: Path, root: Path) -> Dict[str, str]:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise NDPAssignmentRosterError(
            "roster bindings must stay inside the study root"
        ) from exc
    return {"file": relative, "sha256": _sha256_file(resolved)}


def _sha256_value(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise NDPAssignmentRosterError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return value


def _external_binding(
    path: Path,
    *,
    canonical_sha256: str | None = None,
) -> Dict[str, str]:
    name = path.name
    if (
        not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
    ):
        raise NDPAssignmentRosterError(
            "external evidence filename is invalid"
        )
    result = {
        "filename": name,
        "sha256": _sha256_file(path.resolve()),
    }
    if canonical_sha256 is not None:
        result["canonical_sha256"] = _sha256_value(
            canonical_sha256,
            "distribution receipt canonical digest",
        )
    return result


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NDPAssignmentRosterError(f"{label} must be non-empty")
    result = value.strip()
    if any(token in result.casefold() for token in PLACEHOLDER_TOKENS):
        raise NDPAssignmentRosterError(f"{label} is still a placeholder")
    return result


def _utc_timestamp(value: Any, label: str) -> datetime:
    text = _identifier(value, label)
    if not text.endswith("Z"):
        raise NDPAssignmentRosterError(
            f"{label} must be an RFC 3339 UTC timestamp ending in Z"
        )
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise NDPAssignmentRosterError(
            f"{label} must be an RFC 3339 UTC timestamp"
        ) from exc
    if parsed.tzinfo != timezone.utc:
        raise NDPAssignmentRosterError(f"{label} must use UTC")
    return parsed


def _slot_template(contract: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        **contract,
        "reviewer_id": None,
        "reviewer_role": None,
        "qualification_summary": None,
        "conflict_of_interest_declared": None,
        "developer_participation": None,
        "project_collaborator": None,
        "assigned_at": None,
        "distribution_packet_id": None,
        "distribution_packet_manifest_sha256": None,
        "packet_delivered_at": None,
        "received_exact_packet_attested": None,
        "no_other_assignment_packet_received": None,
        "accepted_at": None,
        "accepted_assignment_contract": None,
        "no_test_data_access": None,
        "no_model_outputs_visible": None,
    }


def build_roster_template(
    *,
    assignment_release_path: Path,
    handoff_path: Path,
    distribution_spec_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    release = _load_json(assignment_release_path)
    handoff = _load_json(handoff_path)
    distribution_spec = _load_json(distribution_spec_path)
    if (
        release.get("schema_version") != RELEASE_SCHEMA_VERSION
        or release.get("status") != "released_unassigned"
        or release.get("assignment_count") != 4
        or set(release.get("assignments", {}))
        != {
            "data_governance_review",
            "vocabulary_discovery_a",
            "vocabulary_discovery_b",
            "feedback_response_signoff",
        }
    ):
        raise NDPAssignmentRosterError(
            "roster preparation requires the exact initial assignment release"
        )
    if (
        handoff.get("schema_version") != HANDOFF_SCHEMA_VERSION
        or handoff.get("status")
        != "human_work_released_downstream_locked"
    ):
        raise NDPAssignmentRosterError(
            "roster preparation requires a released human handoff"
        )
    if release.get("handoff") != _binding(handoff_path, study_root):
        raise NDPAssignmentRosterError(
            "assignment release does not bind the exact handoff"
        )
    packets = distribution_spec.get("packets")
    if (
        distribution_spec.get("schema_version")
        != DISTRIBUTION_SPEC_SCHEMA_VERSION
        or distribution_spec.get("status")
        != "neutral_packets_specified_unmaterialized"
        or distribution_spec.get("assignment_release")
        != _binding(assignment_release_path, study_root)
        or distribution_spec.get("packet_count") != 4
        or not isinstance(packets, Mapping)
        or set(packets) != set(PACKET_ROSTER_SLOTS)
        or any(
            not isinstance(packets[packet_id], Mapping)
            or packets[packet_id].get("roster_slots")
            != PACKET_ROSTER_SLOTS[packet_id]
            for packet_id in PACKET_ROSTER_SLOTS
        )
    ):
        raise NDPAssignmentRosterError(
            "roster preparation requires the exact four-packet "
            "distribution specification"
        )
    return {
        "schema_version": ROSTER_SCHEMA_VERSION,
        "status": "pending_assignment_acceptance",
        "assignment_release": _binding(
            assignment_release_path, study_root
        ),
        "handoff": _binding(handoff_path, study_root),
        "assignment_distribution": {
            "spec": _binding(distribution_spec_path, study_root),
            "receipt": None,
            "validation": None,
            "packet_count": None,
            "sealed_identity_match_count": None,
            "extra_file_count": None,
            "packet_root_outside_repository": None,
            "validated_before_roster_freeze": None,
            "validated_at": None,
        },
        "operator_id": None,
        "frozen_at": None,
        "slots": {
            slot_id: _slot_template(contract)
            for slot_id, contract in SLOT_CONTRACTS.items()
        },
        "prework_attestations": {
            "all_roles_confirmed_before_submission": None,
            "no_human_submission_started": None,
            "vocabulary_reviewers_isolated": None,
            "feedback_collaborator_excluded_from_independent_roles": None,
            "distribution_receipt_validated_before_roster_freeze": None,
            "packet_delivery_bound_to_exact_reviewer_slots": None,
            "no_cross_packet_access_before_submission": None,
        },
        "completion_attestation": None,
    }


def _distribution_evidence(
    *,
    receipt_path: Path,
    validation_path: Path,
    validation: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "receipt": _external_binding(
            receipt_path,
            canonical_sha256=validation[
                "distribution_receipt_canonical_sha256"
            ],
        ),
        "validation": {
            **_external_binding(validation_path),
            "schema_version": DISTRIBUTION_VALIDATION_SCHEMA_VERSION,
            "status": "passed",
        },
        "packet_count": validation["packet_count"],
        "sealed_identity_match_count": validation[
            "sealed_identity_match_count"
        ],
        "extra_file_count": validation["extra_file_count"],
        "packet_root_outside_repository": True,
        "validated_before_roster_freeze": True,
    }


def _validate_distribution_evidence_shape(
    value: Any,
) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        raise NDPAssignmentRosterError(
            "assignment distribution evidence is missing"
        )
    if set(value) != {
        "spec",
        "receipt",
        "validation",
        "packet_count",
        "sealed_identity_match_count",
        "extra_file_count",
        "packet_root_outside_repository",
        "validated_before_roster_freeze",
        "validated_at",
    }:
        raise NDPAssignmentRosterError(
            "assignment distribution evidence has unexpected fields"
        )
    receipt = value.get("receipt")
    validation = value.get("validation")
    if (
        not isinstance(receipt, Mapping)
        or set(receipt) != {"filename", "sha256", "canonical_sha256"}
        or not isinstance(receipt.get("filename"), str)
        or Path(receipt["filename"]).name != receipt["filename"]
        or "/" in receipt["filename"]
        or "\\" in receipt["filename"]
    ):
        raise NDPAssignmentRosterError(
            "distribution receipt binding is invalid"
        )
    _sha256_value(receipt.get("sha256"), "distribution receipt digest")
    _sha256_value(
        receipt.get("canonical_sha256"),
        "distribution receipt canonical digest",
    )
    if (
        not isinstance(validation, Mapping)
        or set(validation)
        != {"filename", "sha256", "schema_version", "status"}
        or not isinstance(validation.get("filename"), str)
        or Path(validation["filename"]).name != validation["filename"]
        or "/" in validation["filename"]
        or "\\" in validation["filename"]
        or validation.get("schema_version")
        != DISTRIBUTION_VALIDATION_SCHEMA_VERSION
        or validation.get("status") != "passed"
    ):
        raise NDPAssignmentRosterError(
            "distribution validation binding is invalid"
        )
    _sha256_value(validation.get("sha256"), "distribution validation digest")
    if (
        value.get("packet_count") != 4
        or value.get("sealed_identity_match_count") != 0
        or value.get("extra_file_count") != 0
        or value.get("packet_root_outside_repository") is not True
        or value.get("validated_before_roster_freeze") is not True
    ):
        raise NDPAssignmentRosterError(
            "distribution evidence does not prove four clean external packets"
        )
    return dict(value)


def _validate_frozen_roster(
    roster: Mapping[str, Any],
    *,
    roster_path: Path,
    assignment_release_path: Path,
    handoff_path: Path,
    distribution_spec_path: Path,
    study_root: Path,
    expected_distribution: Mapping[str, Any] | None,
    expected_packet_manifest_sha256: Mapping[str, str] | None,
) -> Dict[str, Any]:
    template = build_roster_template(
        assignment_release_path=assignment_release_path,
        handoff_path=handoff_path,
        distribution_spec_path=distribution_spec_path,
        study_root=study_root,
    )
    if set(roster) != set(template):
        raise NDPAssignmentRosterError(
            "roster has missing or unexpected top-level fields"
        )
    if roster.get("schema_version") != ROSTER_SCHEMA_VERSION:
        raise NDPAssignmentRosterError("unexpected roster schema")
    if roster.get("status") != "frozen_before_human_submissions":
        raise NDPAssignmentRosterError(
            "roster status must be frozen_before_human_submissions"
        )
    for key in ("assignment_release", "handoff"):
        if roster.get(key) != template[key]:
            raise NDPAssignmentRosterError(
                f"roster {key} binding mismatch"
            )
    operator_id = _identifier(roster.get("operator_id"), "operator ID")
    frozen_at = _utc_timestamp(roster.get("frozen_at"), "roster frozen_at")
    distribution = _validate_distribution_evidence_shape(
        roster.get("assignment_distribution")
    )
    if distribution.get("spec") != template[
        "assignment_distribution"
    ]["spec"]:
        raise NDPAssignmentRosterError(
            "roster distribution specification binding mismatch"
        )
    if expected_distribution is not None:
        for key, expected in expected_distribution.items():
            if distribution.get(key) != expected:
                raise NDPAssignmentRosterError(
                    f"roster distribution {key} binding mismatch"
                )
    distribution_validated_at = _utc_timestamp(
        distribution.get("validated_at"),
        "distribution validated_at",
    )
    if distribution_validated_at > frozen_at:
        raise NDPAssignmentRosterError(
            "distribution validation must precede roster freeze"
        )
    slots = roster.get("slots")
    if not isinstance(slots, Mapping) or set(slots) != set(SLOT_CONTRACTS):
        raise NDPAssignmentRosterError(
            "roster must contain exactly the five assignment slots"
        )

    reviewer_ids: Dict[str, str] = {}
    reviewer_roles: Dict[str, str] = {}
    for slot_id, contract in SLOT_CONTRACTS.items():
        slot = slots[slot_id]
        if not isinstance(slot, Mapping):
            raise NDPAssignmentRosterError(
                f"roster slot {slot_id} must be an object"
            )
        if set(slot) != set(template["slots"][slot_id]):
            raise NDPAssignmentRosterError(
                f"roster slot {slot_id} has unexpected fields"
            )
        for key, expected in contract.items():
            if slot.get(key) != expected:
                raise NDPAssignmentRosterError(
                    f"roster slot {slot_id} changes {key}"
                )
        reviewer_id = _identifier(
            slot.get("reviewer_id"), f"{slot_id} reviewer ID"
        )
        role = _identifier(
            slot.get("reviewer_role"), f"{slot_id} reviewer role"
        )
        if role not in contract["allowed_roles"]:
            raise NDPAssignmentRosterError(
                f"{slot_id} reviewer role is not allowed"
            )
        _identifier(
            slot.get("qualification_summary"),
            f"{slot_id} qualification summary",
        )
        if slot.get("conflict_of_interest_declared") is not False:
            raise NDPAssignmentRosterError(
                f"{slot_id} must be conflict-cleared"
            )
        developer = slot.get("developer_participation")
        collaborator = slot.get("project_collaborator")
        if not isinstance(developer, bool) or not isinstance(
            collaborator, bool
        ):
            raise NDPAssignmentRosterError(
                f"{slot_id} participation flags must be Boolean"
            )
        if (
            contract["developer_policy"] == "forbidden"
            and developer
        ):
            raise NDPAssignmentRosterError(
                f"{slot_id} cannot be assigned to a developer"
            )
        collaborator_policy = contract["project_collaborator_policy"]
        if collaborator_policy == "forbidden" and collaborator:
            raise NDPAssignmentRosterError(
                f"{slot_id} cannot be assigned to a project collaborator"
            )
        if collaborator_policy == "required" and not collaborator:
            raise NDPAssignmentRosterError(
                f"{slot_id} requires a project collaborator"
            )
        if slot.get("independent_reviewer") is not contract[
            "independent_reviewer"
        ]:
            raise NDPAssignmentRosterError(
                f"{slot_id} independence declaration mismatch"
            )
        assigned_at = _utc_timestamp(
            slot.get("assigned_at"), f"{slot_id} assigned_at"
        )
        packet_id = _identifier(
            slot.get("distribution_packet_id"),
            f"{slot_id} distribution packet ID",
        )
        if packet_id != contract["assignment_id"]:
            raise NDPAssignmentRosterError(
                f"{slot_id} received the wrong distribution packet"
            )
        packet_manifest_sha256 = _sha256_value(
            slot.get("distribution_packet_manifest_sha256"),
            f"{slot_id} packet manifest digest",
        )
        if (
            expected_packet_manifest_sha256 is not None
            and packet_manifest_sha256
            != expected_packet_manifest_sha256[slot_id]
        ):
            raise NDPAssignmentRosterError(
                f"{slot_id} packet manifest digest mismatch"
            )
        packet_delivered_at = _utc_timestamp(
            slot.get("packet_delivered_at"),
            f"{slot_id} packet_delivered_at",
        )
        accepted_at = _utc_timestamp(
            slot.get("accepted_at"), f"{slot_id} accepted_at"
        )
        if not (
            distribution_validated_at
            <= assigned_at
            <= packet_delivered_at
            <= accepted_at
            <= frozen_at
        ):
            raise NDPAssignmentRosterError(
                f"{slot_id} assignment timestamps are out of order"
            )
        for attestation in (
            "received_exact_packet_attested",
            "no_other_assignment_packet_received",
            "accepted_assignment_contract",
            "no_test_data_access",
            "no_model_outputs_visible",
        ):
            if slot.get(attestation) is not True:
                raise NDPAssignmentRosterError(
                    f"{slot_id} {attestation} must be true"
                )
        reviewer_ids[slot_id] = reviewer_id
        reviewer_roles[slot_id] = role

    if (
        reviewer_ids["governance_stewardship"]
        == reviewer_ids["governance_accountable_approval"]
    ):
        raise NDPAssignmentRosterError(
            "governance signatories must be distinct"
        )
    if (
        reviewer_ids["vocabulary_discovery_a"]
        == reviewer_ids["vocabulary_discovery_b"]
    ):
        raise NDPAssignmentRosterError(
            "vocabulary reviewers must be distinct"
        )
    feedback_id = reviewer_ids["feedback_response_signoff"]
    if feedback_id in {
        reviewer_ids["vocabulary_discovery_a"],
        reviewer_ids["vocabulary_discovery_b"],
    }:
        raise NDPAssignmentRosterError(
            "feedback collaborator cannot fill an independent vocabulary role"
        )
    attestations = roster.get("prework_attestations")
    if (
        not isinstance(attestations, Mapping)
        or set(attestations)
        != set(template["prework_attestations"])
        or any(value is not True for value in attestations.values())
    ):
        raise NDPAssignmentRosterError(
            "all prework roster attestations must be true"
        )
    if roster.get("completion_attestation") is not True:
        raise NDPAssignmentRosterError(
            "roster completion must be attested"
        )
    return {
        "schema_version": ROSTER_VALIDATION_SCHEMA_VERSION,
        "status": "passed",
        "roster_sha256": _sha256_file(roster_path),
        "assignment_release_sha256": _sha256_file(
            assignment_release_path
        ),
        "handoff_sha256": _sha256_file(handoff_path),
        "assignment_distribution_spec_sha256": _sha256_file(
            distribution_spec_path
        ),
        "distribution_receipt_sha256": distribution["receipt"]["sha256"],
        "distribution_receipt_canonical_sha256": distribution["receipt"][
            "canonical_sha256"
        ],
        "distribution_validation_sha256": distribution["validation"][
            "sha256"
        ],
        "distribution_validated_at": distribution["validated_at"],
        "distribution_packet_count": distribution["packet_count"],
        "distribution_sealed_identity_match_count": 0,
        "distribution_extra_file_count": 0,
        "distribution_packet_root_outside_repository": True,
        "distribution_validated_before_roster_freeze": True,
        "operator_id": operator_id,
        "frozen_at": roster["frozen_at"],
        "assigned_slot_count": len(SLOT_CONTRACTS),
        "reviewer_ids": reviewer_ids,
        "reviewer_roles": reviewer_roles,
        "governance_signatories_distinct": True,
        "vocabulary_reviewers_distinct": True,
        "feedback_collaborator_excluded_from_independent_roles": True,
        "distribution_packet_ids_by_slot": {
            slot_id: slots[slot_id]["distribution_packet_id"]
            for slot_id in SLOT_CONTRACTS
        },
        "distribution_packet_manifest_sha256_by_slot": {
            slot_id: slots[slot_id][
                "distribution_packet_manifest_sha256"
            ]
            for slot_id in SLOT_CONTRACTS
        },
        "packet_delivery_attested": True,
        "no_cross_packet_access_attested": True,
        "human_submissions_present": False,
        "next_authorized_action": "begin_exact_released_assignments",
    }


def validate_assignment_roster(
    roster: Mapping[str, Any],
    *,
    roster_path: Path,
    assignment_release_path: Path,
    handoff_path: Path,
    distribution_spec_path: Path,
    distribution_receipt_path: Path,
    distribution_validation_path: Path,
    public_manifest_path: Path,
    selection_path: Path,
    packet_root: Path,
    study_root: Path,
    repo_root: Path,
) -> Dict[str, Any]:
    for evidence_path in (
        distribution_receipt_path,
        distribution_validation_path,
    ):
        if evidence_path.resolve().is_relative_to(
            _repository_boundary(repo_root)
        ):
            raise NDPAssignmentRosterError(
                "distribution receipts must remain outside the repository"
            )
    receipt = _load_json(distribution_receipt_path)
    validation = _load_json(distribution_validation_path)
    if (
        receipt.get("schema_version")
        != DISTRIBUTION_RECEIPT_SCHEMA_VERSION
        or receipt.get("status")
        != "materialized_and_verified_unassigned"
    ):
        raise NDPAssignmentRosterError(
            "distribution receipt is not a verified neutral receipt"
        )
    expected_validation = validate_distribution(
        receipt,
        spec_path=distribution_spec_path,
        assignment_release_path=assignment_release_path,
        public_manifest_path=public_manifest_path,
        selection_path=selection_path,
        study_root=study_root,
        repo_root=repo_root,
        packet_root=packet_root,
    )
    if validation != expected_validation:
        raise NDPAssignmentRosterError(
            "distribution validation is not an exact passing replay"
        )
    evidence = _distribution_evidence(
        receipt_path=distribution_receipt_path,
        validation_path=distribution_validation_path,
        validation=validation,
    )
    packet_hashes = {
        slot_id: receipt["packets"][contract["assignment_id"]][
            "packet_manifest_sha256"
        ]
        for slot_id, contract in SLOT_CONTRACTS.items()
    }
    return _validate_frozen_roster(
        roster,
        roster_path=roster_path,
        assignment_release_path=assignment_release_path,
        handoff_path=handoff_path,
        distribution_spec_path=distribution_spec_path,
        study_root=study_root,
        expected_distribution=evidence,
        expected_packet_manifest_sha256=packet_hashes,
    )


def replay_assignment_roster_validation(
    roster: Mapping[str, Any],
    *,
    roster_path: Path,
    assignment_release_path: Path,
    handoff_path: Path,
    distribution_spec_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    """Replay the frozen roster receipt without reopening delivered packets."""
    return _validate_frozen_roster(
        roster,
        roster_path=roster_path,
        assignment_release_path=assignment_release_path,
        handoff_path=handoff_path,
        distribution_spec_path=distribution_spec_path,
        study_root=study_root,
        expected_distribution=None,
        expected_packet_manifest_sha256=None,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare or validate the pre-submission NDP-50 assignment roster."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument(
        "--assignment-release", type=Path, required=True
    )
    prepare.add_argument("--handoff", type=Path, required=True)
    prepare.add_argument("--distribution-spec", type=Path, required=True)
    prepare.add_argument("--study-root", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--roster", type=Path, required=True)
    validate.add_argument(
        "--assignment-release", type=Path, required=True
    )
    validate.add_argument("--handoff", type=Path, required=True)
    validate.add_argument("--distribution-spec", type=Path, required=True)
    validate.add_argument("--distribution-receipt", type=Path, required=True)
    validate.add_argument(
        "--distribution-validation", type=Path, required=True
    )
    validate.add_argument(
        "--public-package-manifest", type=Path, required=True
    )
    validate.add_argument("--selection", type=Path, required=True)
    validate.add_argument("--packet-root", type=Path, required=True)
    validate.add_argument("--study-root", type=Path, required=True)
    validate.add_argument("--repo-root", type=Path, required=True)
    validate.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        payload = build_roster_template(
            assignment_release_path=args.assignment_release,
            handoff_path=args.handoff,
            distribution_spec_path=args.distribution_spec,
            study_root=args.study_root,
        )
        _write_json(args.output, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "slot_count": len(payload["slots"]),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    payload = validate_assignment_roster(
        _load_json(args.roster),
        roster_path=args.roster,
        assignment_release_path=args.assignment_release,
        handoff_path=args.handoff,
        distribution_spec_path=args.distribution_spec,
        distribution_receipt_path=args.distribution_receipt,
        distribution_validation_path=args.distribution_validation,
        public_manifest_path=args.public_package_manifest,
        selection_path=args.selection,
        packet_root=args.packet_root,
        study_root=args.study_root,
        repo_root=args.repo_root,
    )
    _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
