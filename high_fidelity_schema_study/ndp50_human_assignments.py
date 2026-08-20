from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .ndp50_assignment_distribution import build_distribution_spec
from .ndp50_assignment_roster import (
    ROSTER_VALIDATION_SCHEMA_VERSION,
    build_roster_template,
    replay_assignment_roster_validation,
)
from .ndp50_cpa_screen_workflow import load_evidence_registry
from .ndp50_data_governance_review import (
    VALIDATION_SCHEMA_VERSION as GOVERNANCE_VALIDATION_SCHEMA_VERSION,
    validate_review,
)
from .ndp50_publication_gate import (
    VALIDATION_SCHEMA_VERSION as PUBLICATION_VALIDATION_SCHEMA_VERSION,
    validate_feedback_signoff,
)
from .ndp50_vocabulary_workflow import (
    CONSENSUS_ADJUDICATOR_ROLES,
    CURATOR_ROLES,
    DISCOVERY_SCHEMA_VERSION,
    REVIEWER_ROLES,
    build_candidate_catalog,
    build_consensus_template,
    build_decision_template,
    compare_decisions,
    validate_consensus,
    validate_decision,
    validate_discovery,
)


RELEASE_SCHEMA_VERSION = "ndp50-human-assignment-release/v1"
ASSIGNMENT_SCHEMA_VERSION = "ndp50-human-assignment/v1"
RETURN_SCHEMA_VERSION = "ndp50-human-assignment-return/v1"
RELEASE_VALIDATION_SCHEMA_VERSION = (
    "ndp50-human-assignment-release-validation/v1"
)
RETURN_VALIDATION_SCHEMA_VERSION = (
    "ndp50-human-assignment-return-validation/v1"
)
DECISION_RELEASE_SCHEMA_VERSION = (
    "ndp50-vocabulary-decision-assignment-release/v1"
)
DECISION_RETURN_SCHEMA_VERSION = (
    "ndp50-vocabulary-decision-assignment-return/v1"
)
DECISION_RELEASE_VALIDATION_SCHEMA_VERSION = (
    "ndp50-vocabulary-decision-assignment-release-validation/v1"
)
DECISION_RETURN_VALIDATION_SCHEMA_VERSION = (
    "ndp50-vocabulary-decision-assignment-return-validation/v1"
)
CONSENSUS_RELEASE_SCHEMA_VERSION = (
    "ndp50-vocabulary-consensus-assignment-release/v1"
)
CONSENSUS_RETURN_SCHEMA_VERSION = (
    "ndp50-vocabulary-consensus-assignment-return/v1"
)
CONSENSUS_RELEASE_VALIDATION_SCHEMA_VERSION = (
    "ndp50-vocabulary-consensus-assignment-release-validation/v1"
)
CONSENSUS_RETURN_VALIDATION_SCHEMA_VERSION = (
    "ndp50-vocabulary-consensus-assignment-return-validation/v1"
)
HANDOFF_SCHEMA_VERSION = "ndp50-human-handoff/v1"
PLACEHOLDER_TOKENS = ("replace-with", "placeholder", "todo", "tbd")
ASSIGNMENT_FILENAMES = {
    "data_governance_review": "data_governance_review_assignment.json",
    "vocabulary_discovery_a": "vocabulary_discovery_a_assignment.json",
    "vocabulary_discovery_b": "vocabulary_discovery_b_assignment.json",
    "feedback_response_signoff": (
        "feedback_response_signoff_assignment.json"
    ),
}
PAYLOAD_FILENAMES = {
    "data_governance_review": "data_governance_review_payload.json",
    "vocabulary_discovery_a": "vocabulary_discovery_a_payload.json",
    "vocabulary_discovery_b": "vocabulary_discovery_b_payload.json",
    "feedback_response_signoff": "feedback_response_signoff_payload.json",
}
PACKAGE_ROOT = Path(__file__).resolve().parent
FEEDBACK_MATRIX_PATH = (
    PACKAGE_ROOT / "docs" / "swathi_feedback_response_matrix_v1.md"
)
FEEDBACK_AMENDMENT_PATH = (
    PACKAGE_ROOT / "docs" / "ndp50_feedback_improvement_amendment_v1.md"
)


class NDPHumanAssignmentError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_payload(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _relative(path: Path, root: Path) -> str:
    resolved = path.resolve()
    root = root.resolve()
    if not resolved.is_relative_to(root):
        raise NDPHumanAssignmentError(
            f"assignment artifact must be inside the study root: {path}"
        )
    return resolved.relative_to(root).as_posix()


def _binding(path: Path, root: Path) -> Dict[str, str]:
    if not path.is_file():
        raise NDPHumanAssignmentError(f"bound file does not exist: {path}")
    return {"file": _relative(path, root), "sha256": _sha256_file(path)}


def _resolve_binding(
    binding: Mapping[str, Any],
    *,
    root: Path,
    label: str,
) -> Path:
    file = binding.get("file")
    sha256 = binding.get("sha256")
    if (
        not isinstance(file, str)
        or not file
        or Path(file).is_absolute()
        or not isinstance(sha256, str)
        or len(sha256) != 64
    ):
        raise NDPHumanAssignmentError(f"{label} has an invalid binding")
    path = (root.resolve() / Path(file)).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise NDPHumanAssignmentError(f"{label} resolves outside the study root")
    if _sha256_file(path) != sha256:
        raise NDPHumanAssignmentError(f"{label} hash mismatch")
    return path


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NDPHumanAssignmentError(f"{label} must be non-empty")
    result = value.strip()
    if any(token in result.casefold() for token in PLACEHOLDER_TOKENS):
        raise NDPHumanAssignmentError(f"{label} is still a placeholder")
    return result


def _iso_date(value: Any, label: str) -> str:
    result = _identifier(value, label)
    try:
        date.fromisoformat(result)
    except ValueError as exc:
        raise NDPHumanAssignmentError(
            f"{label} must be an ISO calendar date"
        ) from exc
    return result


def _verify_handoff(
    handoff_path: Path,
    *,
    study_root: Path,
) -> Dict[str, Any]:
    handoff = _load_json(handoff_path)
    if handoff.get("schema_version") != HANDOFF_SCHEMA_VERSION:
        raise NDPHumanAssignmentError("unexpected human-handoff schema")
    if handoff.get("status") != "human_work_released_downstream_locked":
        raise NDPHumanAssignmentError(
            "assignment release requires a human-work-released handoff"
        )
    implementation = handoff.get("implementation")
    expected_source = Path(__file__).with_name("ndp50_human_handoff.py")
    if (
        not isinstance(implementation, Mapping)
        or implementation.get("file") != expected_source.name
        or implementation.get("sha256") != _sha256_file(expected_source)
    ):
        raise NDPHumanAssignmentError(
            "handoff implementation binding is stale"
        )
    released = handoff.get("current_release", {}).get("released_stage_ids")
    if released != [
        "data_governance_review",
        "vocabulary_governance",
        "feedback_response_signoff",
    ]:
        raise NDPHumanAssignmentError(
            "this release protocol requires exactly the three initial stages"
        )
    stage_status = {
        item.get("stage_id"): item.get("status")
        for item in handoff.get("stages", [])
        if isinstance(item, Mapping)
    }
    if any(stage_status.get(stage_id) != "released" for stage_id in released):
        raise NDPHumanAssignmentError(
            "handoff release list and stage statuses disagree"
        )
    bindings = handoff.get("artifact_bindings")
    if not isinstance(bindings, Mapping):
        raise NDPHumanAssignmentError("handoff lacks artifact bindings")
    for label, binding in bindings.items():
        if not isinstance(binding, Mapping):
            raise NDPHumanAssignmentError(
                f"handoff artifact {label} has an invalid binding"
            )
        _resolve_binding(binding, root=study_root, label=f"handoff.{label}")
    return handoff


def _source_paths(
    handoff: Mapping[str, Any],
    *,
    study_root: Path,
) -> Dict[str, Path]:
    bindings = handoff["artifact_bindings"]
    keys = {
        "governance_audit": "data_governance",
        "governance_template": "data_governance_review_template",
        "governance_workflow": "data_governance_review_workflow",
        "vocabulary_template": "vocabulary_review_template",
        "draft_vocabulary": "vocabulary",
        "source_bundle_manifest": "source_bundle_manifest",
        "vocabulary_workflow": "vocabulary_review_workflow",
        "feedback_signoff_template": (
            "feedback_response_signoff_template"
        ),
        "publication_gate_workflow": "publication_gate_workflow",
    }
    return {
        name: _resolve_binding(
            bindings[key],
            root=study_root,
            label=f"handoff.{key}",
        )
        for name, key in keys.items()
    }


def _payload_binding(
    *,
    slot_id: str,
    output_dir: Path,
    source_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    payload_path = output_dir / PAYLOAD_FILENAMES[slot_id]
    if not payload_path.is_file():
        raise NDPHumanAssignmentError(
            f"missing neutral payload copy for {slot_id}"
        )
    if payload_path.read_bytes() != source_path.read_bytes():
        raise NDPHumanAssignmentError(
            f"neutral payload copy for {slot_id} is not byte-identical"
        )
    return {
        **_binding(payload_path, study_root),
        "copied_from": _binding(source_path, study_root),
        "copy_integrity": "byte_identical",
    }


def _vocabulary_submission_contract(
    *, slot_id: str
) -> Dict[str, Any]:
    if slot_id not in {
        "vocabulary_discovery_a",
        "vocabulary_discovery_b",
    }:
        raise NDPHumanAssignmentError(
            f"unexpected vocabulary assignment slot: {slot_id}"
        )
    submission_filename = f"{slot_id}.json"
    receipt_filename = f"{slot_id}_validation.json"
    return {
        "working_copy_filename": submission_filename,
        "validation_receipt_filename": receipt_filename,
        "return_manifest_slot": slot_id,
        "required_actions": [
            "Work only from the byte-identical neutral payload and the bound source-bundle manifest.",
            "Complete all 16 case reviews and all corpus-level policy decisions without viewing the other review.",
            "Use the assigned reviewer role, a stable pseudonymous reviewer ID, a unique submission ID, a qualification summary, and a truthful conflict disclosure.",
            "Cite only locatable evidence IDs from the released source bundles and give a rationale for every coverage judgment or proposal.",
            "Keep model outputs, the other submission, candidate catalogs, and disagreement reports hidden until both submissions and receipts are frozen.",
            "Set the completion attestation true only after personally completing the full-corpus review.",
            "Run validate-discovery and return its exact generated receipt.",
        ],
        "forbidden_actions": [
            "Do not communicate about review content with the other vocabulary reviewer before dual freeze.",
            "Do not edit case identities, evidence catalogs, or bound artifact hashes.",
            "Do not use model outputs or inspect test identities, details, gold, or outcomes.",
            "Do not build or view a candidate catalog or disagreement report before both passing receipts are frozen.",
        ],
        "validator_command_template": [
            "python",
            "-m",
            "high_fidelity_schema_study.ndp50_vocabulary_workflow",
            "validate-discovery",
            "--submission",
            f"<{submission_filename}>",
            "--template",
            (
                "high_fidelity_schema_study/data/experiments/ndp50_v1/"
                "semantic/vocabulary_discovery_neutral_v1.json"
            ),
            "--source-bundle-manifest",
            (
                "high_fidelity_schema_study/data/experiments/ndp50_v1/"
                "semantic/source_bundle_drafts_v1/manifest.json"
            ),
            "--output",
            f"<{receipt_filename}>",
        ],
    }


def _assignment_payloads(
    handoff: Mapping[str, Any],
    *,
    handoff_path: Path,
    study_root: Path,
    output_dir: Path,
) -> Dict[str, Dict[str, Any]]:
    sources = _source_paths(handoff, study_root=study_root)
    common = {
        "schema_version": ASSIGNMENT_SCHEMA_VERSION,
        "release_state": "ready_unassigned",
        "reviewer_id": None,
        "assigned_on": None,
        "handoff": _binding(handoff_path, study_root),
        "test_data_access": "forbidden",
        "model_outputs_visible": False,
    }
    governance = {
        **common,
        "assignment_id": "data_governance_review",
        "stage_id": "data_governance_review",
        "execution_mode": "sequential_review_then_countersignature",
        "payload": _payload_binding(
            slot_id="data_governance_review",
            output_dir=output_dir,
            source_path=sources["governance_template"],
            study_root=study_root,
        ),
        "released_inputs": {
            "audit": _binding(sources["governance_audit"], study_root),
            "workflow": _binding(
                sources["governance_workflow"], study_root
            ),
        },
        "signatory_slots": [
            {
                "slot": "stewardship_review",
                "reviewer_id": None,
                "allowed_roles": [
                    "institutional_data_steward",
                    "research_compliance_reviewer",
                ],
                "developer_participation_required": False,
                "sequence": 1,
            },
            {
                "slot": "accountable_approval",
                "reviewer_id": None,
                "allowed_roles": [
                    "principal_investigator",
                    "institutional_data_controller",
                ],
                "developer_participation_must_be_declared": True,
                "must_differ_from": "stewardship_review",
                "sequence": 2,
            },
        ],
        "custody_contract": [
            "The stewardship reviewer completes the evidence and policy fields first.",
            "The accountable approver receives only that frozen review for countersignature.",
            "The two signatories must use distinct stable pseudonymous IDs.",
            "The validator, not either signatory, determines whether the review passes.",
        ],
        "submission_contract": {
            "working_copy_filename": (
                "completed_data_governance_review.json"
            ),
            "review_validation_receipt_filename": (
                "data_governance_review_validation.json"
            ),
            "derived_approval_filename": "data_governance_approval.json",
            "approval_validation_receipt_filename": (
                "data_governance_approval_validation.json"
            ),
            "return_manifest_slot": "data_governance_review",
            "required_actions": [
                "Work only from the byte-identical neutral payload and the bound governance audit.",
                "Have the stewardship reviewer complete every dataset decision and study-policy field first.",
                "Freeze the completed stewardship review before the distinct accountable approver countersigns it.",
                "Use stable pseudonymous IDs, truthful role declarations, and complete rationales.",
                "Set the completion attestation true only after both signatories have personally completed their assigned checks.",
                "Run validate-review and return its exact generated receipt with the completed review.",
                "Generate the approval only with the approve command, then replay it with verify-approved for the next handoff rebuild.",
            ],
            "forbidden_actions": [
                "Do not edit the bound audit, dataset identities, or neutral-template bindings.",
                "Do not use the same person or stable ID for both signatory slots.",
                "Do not hand-edit the validator-generated approval artifact.",
                "Do not claim that this workflow supplies legal advice.",
                "Do not inspect test identities, details, gold, or outcomes.",
            ],
            "validator_command_templates": {
                "validate_review": [
                    "python",
                    "-m",
                    (
                        "high_fidelity_schema_study."
                        "ndp50_data_governance_review"
                    ),
                    "validate-review",
                    "--review",
                    "<completed_data_governance_review.json>",
                    "--audit",
                    (
                        "high_fidelity_schema_study/data/experiments/"
                        "ndp50_v1/reports/data_governance_v1.json"
                    ),
                    "--study-root",
                    (
                        "high_fidelity_schema_study/data/experiments/"
                        "ndp50_v1"
                    ),
                    "--output",
                    "<data_governance_review_validation.json>",
                ],
                "generate_approval": [
                    "python",
                    "-m",
                    (
                        "high_fidelity_schema_study."
                        "ndp50_data_governance_review"
                    ),
                    "approve",
                    "--review",
                    "<completed_data_governance_review.json>",
                    "--audit",
                    (
                        "high_fidelity_schema_study/data/experiments/"
                        "ndp50_v1/reports/data_governance_v1.json"
                    ),
                    "--study-root",
                    (
                        "high_fidelity_schema_study/data/experiments/"
                        "ndp50_v1"
                    ),
                    "--output",
                    "<data_governance_approval.json>",
                ],
                "verify_approval": [
                    "python",
                    "-m",
                    (
                        "high_fidelity_schema_study."
                        "ndp50_data_governance_review"
                    ),
                    "verify-approved",
                    "--approved",
                    "<data_governance_approval.json>",
                    "--audit",
                    (
                        "high_fidelity_schema_study/data/experiments/"
                        "ndp50_v1/reports/data_governance_v1.json"
                    ),
                    "--study-root",
                    (
                        "high_fidelity_schema_study/data/experiments/"
                        "ndp50_v1"
                    ),
                    "--output",
                    "<data_governance_approval_validation.json>",
                ],
            },
        },
        "expected_submission_schema": (
            "ndp50-data-governance-review/v1"
        ),
        "validator": {
            "module": (
                "high_fidelity_schema_study.ndp50_data_governance_review"
            ),
            "command": "validate-review",
            "implementation": _binding(
                Path(__file__).with_name("ndp50_data_governance_review.py"),
                Path(__file__).parent,
            ),
        },
    }
    vocabulary_common = {
        **common,
        "stage_id": "vocabulary_governance",
        "execution_mode": "independent_full_corpus_review",
        "released_inputs": {
            "draft_vocabulary": _binding(
                sources["draft_vocabulary"], study_root
            ),
            "source_bundle_manifest": _binding(
                sources["source_bundle_manifest"], study_root
            ),
            "workflow": _binding(
                sources["vocabulary_workflow"], study_root
            ),
        },
        "expected_submission_schema": DISCOVERY_SCHEMA_VERSION,
        "validator": {
            "module": (
                "high_fidelity_schema_study.ndp50_vocabulary_workflow"
            ),
            "command": "validate-discovery",
            "implementation": _binding(
                Path(__file__).with_name("ndp50_vocabulary_workflow.py"),
                Path(__file__).parent,
            ),
        },
        "isolation_contract": {
            "other_assignment_visible_before_both_freeze": False,
            "other_submission_visible_before_both_freeze": False,
            "candidate_catalog_visible": False,
            "disagreement_report_visible": False,
            "communication_about_review_content_forbidden": True,
            "full_corpus_completion_required": True,
        },
    }
    vocabulary_a = {
        **vocabulary_common,
        "assignment_id": "vocabulary_discovery_a",
        "reviewer_id": None,
        "assigned_on": None,
        "required_role": "scientific_metadata_curator",
        "must_differ_from_assignment": "vocabulary_discovery_b",
        "payload": _payload_binding(
            slot_id="vocabulary_discovery_a",
            output_dir=output_dir,
            source_path=sources["vocabulary_template"],
            study_root=study_root,
        ),
        "submission_contract": _vocabulary_submission_contract(
            slot_id="vocabulary_discovery_a"
        ),
    }
    vocabulary_b = {
        **vocabulary_common,
        "assignment_id": "vocabulary_discovery_b",
        "reviewer_id": None,
        "assigned_on": None,
        "required_role": "annotation_methodologist",
        "must_differ_from_assignment": "vocabulary_discovery_a",
        "payload": _payload_binding(
            slot_id="vocabulary_discovery_b",
            output_dir=output_dir,
            source_path=sources["vocabulary_template"],
            study_root=study_root,
        ),
        "submission_contract": _vocabulary_submission_contract(
            slot_id="vocabulary_discovery_b"
        ),
    }
    feedback_signoff = {
        **common,
        "assignment_id": "feedback_response_signoff",
        "stage_id": "feedback_response_signoff",
        "execution_mode": "single_collaborator_full_feedback_review",
        "payload": _payload_binding(
            slot_id="feedback_response_signoff",
            output_dir=output_dir,
            source_path=sources["feedback_signoff_template"],
            study_root=study_root,
        ),
        "released_inputs": {
            "publication_gate_workflow": _binding(
                sources["publication_gate_workflow"], study_root
            ),
        },
        "reviewer_contract": {
            "reviewer_id": None,
            "required_role": "postdoctoral_research_collaborator",
            "project_collaborator": True,
            "developer_participation": False,
            "independent_reviewer": False,
            "conflict_of_interest_disclosure_required": True,
            "qualification_summary_required": True,
        },
        "review_contract": {
            "required_feedback_items": [
                f"F{index:02d}" for index in range(1, 17)
            ],
            "frozen_optional_sensitivity_decisions_must_be_preserved": True,
            "every_review_material_binding_must_be_preserved": True,
            "test_outcomes_must_remain_unseen": True,
            "test_release_authorized_by_signoff": False,
            "independent_validation_claimed": False,
        },
        "submission_contract": {
            "working_copy_filename": (
                "completed_feedback_response_signoff.json"
            ),
            "validation_receipt_filename": (
                "feedback_response_signoff_validation.json"
            ),
            "return_manifest_slot": "feedback_response_signoff",
            "required_actions": [
                "Review the response matrix and amendment item by item.",
                "Review every file in the bound review_materials list.",
                "Preserve every content binding, the review-material digest, and all frozen optional-sensitivity decisions.",
                "Record F01 through F16 exactly once and in order.",
                "Provide a stable reviewer ID, qualification summary, and truthful conflict disclosure.",
                "Use one RFC 3339 UTC timestamp for both signature fields.",
                "Set every attestation true only after personally confirming it.",
                "Run the validator and return its exact generated receipt.",
            ],
            "forbidden_actions": [
                "Do not edit any matrix, amendment, or review-material binding.",
                "Do not claim independent validation.",
                "Do not inspect test identities, details, gold, or outcomes.",
                "Do not treat this sign-off as test-release authorization.",
            ],
            "validator_command_template": [
                "python",
                "-m",
                "high_fidelity_schema_study.ndp50_publication_gate",
                "validate-signoff",
                "--artifact",
                "<completed_feedback_response_signoff.json>",
                "--feedback-matrix",
                (
                    "high_fidelity_schema_study/docs/"
                    "swathi_feedback_response_matrix_v1.md"
                ),
                "--amendment",
                (
                    "high_fidelity_schema_study/docs/"
                    "ndp50_feedback_improvement_amendment_v1.md"
                ),
                "--study-root",
                "high_fidelity_schema_study",
                "--output",
                "<feedback_response_signoff_validation.json>",
            ],
        },
        "expected_submission_schema": (
            "ndp50-feedback-response-signoff/v2"
        ),
        "validator": {
            "module": (
                "high_fidelity_schema_study.ndp50_publication_gate"
            ),
            "command": "validate-signoff",
            "implementation": _binding(
                Path(__file__).with_name("ndp50_publication_gate.py"),
                Path(__file__).parent,
            ),
        },
    }
    return {
        "data_governance_review": governance,
        "vocabulary_discovery_a": vocabulary_a,
        "vocabulary_discovery_b": vocabulary_b,
        "feedback_response_signoff": feedback_signoff,
    }


def _build_release(
    handoff: Mapping[str, Any],
    *,
    handoff_path: Path,
    study_root: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    assignments = _assignment_payloads(
        handoff,
        handoff_path=handoff_path,
        study_root=study_root,
        output_dir=output_dir,
    )
    assignment_bindings = {}
    for slot_id, expected in assignments.items():
        path = output_dir / ASSIGNMENT_FILENAMES[slot_id]
        if not path.is_file() or _load_json(path) != expected:
            raise NDPHumanAssignmentError(
                f"assignment wrapper for {slot_id} is missing or stale"
            )
        assignment_bindings[slot_id] = _binding(path, study_root)
    implementation = Path(__file__).resolve()
    handoff_sha256 = _sha256_file(handoff_path)
    release_id = "ndp50-initial-human-release-" + hashlib.sha256(
        (
            RELEASE_SCHEMA_VERSION
            + ":"
            + handoff_sha256
            + ":"
            + _sha256_file(implementation)
        ).encode("utf-8")
    ).hexdigest()[:20]
    return {
        "schema_version": RELEASE_SCHEMA_VERSION,
        "status": "released_unassigned",
        "release_id": release_id,
        "handoff": _binding(handoff_path, study_root),
        "released_stage_ids": [
            "data_governance_review",
            "vocabulary_governance",
            "feedback_response_signoff",
        ],
        "assignments": assignment_bindings,
        "assignment_count": 4,
        "return_manifest_schema": RETURN_SCHEMA_VERSION,
        "pre_submission_roster_contract": {
            "schema_version": "ndp50-human-assignment-roster/v1",
            "neutral_filename": "assignment_roster_neutral_v1.json",
            "completed_filename": "completed_assignment_roster.json",
            "distribution_spec_filename": (
                "assignment_distribution_spec_v1.json"
            ),
            "distribution_receipt_filename": (
                "assignment_distribution_receipt.json"
            ),
            "distribution_validation_receipt_filename": (
                "assignment_distribution_validation.json"
            ),
            "distribution_packet_root_must_be_outside_repository": True,
            "distribution_must_validate_before_roster_freeze": True,
            "distribution_revalidated_from_live_packet_root_by_roster": True,
            "distribution_receipts_bound_by_roster": True,
            "per_role_packet_manifest_and_delivery_attestation_required": True,
            "distribution_validator_module": (
                "high_fidelity_schema_study."
                "ndp50_assignment_distribution"
            ),
            "validation_receipt_filename": (
                "assignment_roster_validation.json"
            ),
            "must_be_frozen_before_human_submissions": True,
            "validator_module": (
                "high_fidelity_schema_study.ndp50_assignment_roster"
            ),
            "validator_command": "validate",
        },
        "phase_graph": {
            "parallel_initial_work": [
                "data_governance_review",
                "vocabulary_discovery_a",
                "vocabulary_discovery_b",
                "feedback_response_signoff",
            ],
            "governance_sequence": [
                "stewardship_review",
                "accountable_approval",
                "validator_review_validation",
                "validator_approval_generation",
            ],
            "vocabulary_sequence": [
                "two_isolated_discovery_submissions",
                "two_validation_receipts",
                "atomic_dual_hash_freeze",
                "candidate_catalog_construction",
            ],
            "feedback_signoff_sequence": [
                "collaborator_reviews_all_f01_through_f16_items",
                "collaboration_and_non_independence_disclosed",
                "optional_sensitivity_decisions_preserved",
                "validator_replays_exact_bound_submission",
            ],
            "locked_until_valid_return_manifest": [
                "vocabulary_candidate_decisions",
                "vocabulary_disagreement_reveal",
                "all_downstream_stages",
            ],
        },
        "independence_controls": {
            "reviewer_ids_present_at_release": False,
            "human_decisions_present_at_release": False,
            "vocabulary_payloads_byte_identical": True,
            "vocabulary_assignment_wrappers_distinct": True,
            "cross_review_visibility_before_dual_freeze": False,
            "collaborator_feedback_review_claimed_independent": False,
            "test_data_access": "forbidden",
        },
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            name: _sha256_file(implementation.with_name(name))
            for name in (
                "ndp50_assignment_distribution.py",
                "ndp50_assignment_roster.py",
                "ndp50_human_handoff.py",
                "ndp50_data_governance_review.py",
                "ndp50_vocabulary_workflow.py",
                "ndp50_cpa_screen_workflow.py",
                "ndp50_publication_gate.py",
            )
        },
    }


def _build_return_template(
    release_path: Path,
    *,
    study_root: Path,
) -> Dict[str, Any]:
    release = _load_json(release_path)
    return {
        "schema_version": RETURN_SCHEMA_VERSION,
        "status": "pending_human_returns",
        "assignment_release": _binding(release_path, study_root),
        "release_id": release["release_id"],
        "assignment_roster": None,
        "assignment_roster_validation_receipt": None,
        "returns": {
            "data_governance_review": {
                "stewardship_reviewer_id": None,
                "accountable_approver_id": None,
                "submission": None,
                "validation_receipt": None,
            },
            "vocabulary_discovery_a": {
                "reviewer_id": None,
                "reviewer_role": None,
                "submission_id": None,
                "submission": None,
                "validation_receipt": None,
            },
            "vocabulary_discovery_b": {
                "reviewer_id": None,
                "reviewer_role": None,
                "submission_id": None,
                "submission": None,
                "validation_receipt": None,
            },
            "feedback_response_signoff": {
                "reviewer_id": None,
                "submission": None,
                "validation_receipt": None,
            },
        },
        "dual_freeze_record": {
            "operator_id": None,
            "frozen_on": None,
            "discovery_a_sha256": None,
            "discovery_b_sha256": None,
            "both_receipts_passed_before_comparison": None,
            "no_cross_review_visibility_before_freeze": None,
            "candidate_catalog_not_built_before_freeze": None,
        },
        "completion_attestation": None,
    }


def prepare_assignment_package(
    *,
    handoff_path: Path,
    study_root: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    study_root = study_root.resolve()
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(study_root):
        raise NDPHumanAssignmentError(
            "assignment output directory must be inside the study root"
        )
    handoff = _verify_handoff(handoff_path, study_root=study_root)
    sources = _source_paths(handoff, study_root=study_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    copy_sources = {
        "data_governance_review": sources["governance_template"],
        "vocabulary_discovery_a": sources["vocabulary_template"],
        "vocabulary_discovery_b": sources["vocabulary_template"],
        "feedback_response_signoff": sources["feedback_signoff_template"],
    }
    for slot_id, source in copy_sources.items():
        shutil.copyfile(source, output_dir / PAYLOAD_FILENAMES[slot_id])
    assignments = _assignment_payloads(
        handoff,
        handoff_path=handoff_path,
        study_root=study_root,
        output_dir=output_dir,
    )
    for slot_id, payload in assignments.items():
        _write_json(output_dir / ASSIGNMENT_FILENAMES[slot_id], payload)
    release = _build_release(
        handoff,
        handoff_path=handoff_path,
        study_root=study_root,
        output_dir=output_dir,
    )
    release_path = output_dir / "assignment_release_v1.json"
    _write_json(release_path, release)
    _write_json(
        output_dir / "assignment_distribution_spec_v1.json",
        build_distribution_spec(
            assignment_release_path=release_path,
            public_manifest_path=(
                study_root
                / "preregistration"
                / "public_package_manifest_v1.json"
            ),
            selection_path=study_root / "selection.json",
            study_root=study_root,
            repo_root=Path(__file__).resolve().parent,
        ),
    )
    distribution_spec_path = (
        output_dir / "assignment_distribution_spec_v1.json"
    )
    _write_json(
        output_dir / "assignment_roster_neutral_v1.json",
        build_roster_template(
            assignment_release_path=release_path,
            handoff_path=handoff_path,
            distribution_spec_path=distribution_spec_path,
            study_root=study_root,
        ),
    )
    _write_json(
        output_dir / "return_manifest_neutral_v1.json",
        _build_return_template(release_path, study_root=study_root),
    )
    return release


def validate_assignment_release(
    release: Mapping[str, Any],
    *,
    release_path: Path,
    handoff_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    distribution_spec_sha256 = None
    try:
        handoff = _verify_handoff(handoff_path, study_root=study_root)
        expected = _build_release(
            handoff,
            handoff_path=handoff_path,
            study_root=study_root,
            output_dir=release_path.parent,
        )
        differing = sorted(
            key
            for key in set(release) | set(expected)
            if release.get(key) != expected.get(key)
        )
        distribution_spec_path = (
            release_path.parent / "assignment_distribution_spec_v1.json"
        )
        expected_distribution_spec = build_distribution_spec(
            assignment_release_path=release_path,
            public_manifest_path=(
                study_root
                / "preregistration"
                / "public_package_manifest_v1.json"
            ),
            selection_path=study_root / "selection.json",
            study_root=study_root,
            repo_root=Path(__file__).resolve().parent,
        )
        if (
            not distribution_spec_path.is_file()
            or _load_json(distribution_spec_path)
            != expected_distribution_spec
        ):
            differing.append("assignment_distribution_spec")
        else:
            distribution_spec_sha256 = _sha256_file(
                distribution_spec_path
            )
        status = "passed" if not differing else "failed"
        detail = None
    except Exception as exc:  # noqa: BLE001
        differing = ["replay"]
        status = "failed"
        detail = str(exc)
    return {
        "schema_version": RELEASE_VALIDATION_SCHEMA_VERSION,
        "status": status,
        "release_sha256": _sha256_file(release_path),
        "distribution_spec_sha256": distribution_spec_sha256,
        "differing_top_level_keys": differing,
        "detail": detail,
    }


def _return_binding(
    value: Any,
    *,
    study_root: Path,
    label: str,
) -> tuple[Path, Dict[str, Any]]:
    if not isinstance(value, Mapping):
        raise NDPHumanAssignmentError(f"{label} binding is missing")
    path = _resolve_binding(value, root=study_root, label=label)
    return path, _load_json(path)


def validate_return_manifest(
    manifest: Mapping[str, Any],
    *,
    manifest_path: Path,
    release_path: Path,
    handoff_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    release = _load_json(release_path)
    release_validation = validate_assignment_release(
        release,
        release_path=release_path,
        handoff_path=handoff_path,
        study_root=study_root,
    )
    if release_validation["status"] != "passed":
        raise NDPHumanAssignmentError("assignment release replay failed")
    if manifest.get("schema_version") != RETURN_SCHEMA_VERSION:
        raise NDPHumanAssignmentError("unexpected assignment-return schema")
    if manifest.get("status") != "completed_pending_validator_acceptance":
        raise NDPHumanAssignmentError(
            "return status must be completed_pending_validator_acceptance"
        )
    if manifest.get("assignment_release") != _binding(
        release_path, study_root
    ):
        raise NDPHumanAssignmentError(
            "return manifest does not bind the exact assignment release"
        )
    if manifest.get("release_id") != release.get("release_id"):
        raise NDPHumanAssignmentError("return manifest release ID mismatch")
    returns = manifest.get("returns")
    expected_slots = set(ASSIGNMENT_FILENAMES)
    if not isinstance(returns, Mapping) or set(returns) != expected_slots:
        raise NDPHumanAssignmentError(
            "return manifest must contain exactly the released assignments"
        )
    handoff = _verify_handoff(handoff_path, study_root=study_root)
    sources = _source_paths(handoff, study_root=study_root)
    roster_path, roster = _return_binding(
        manifest.get("assignment_roster"),
        study_root=study_root,
        label="assignment roster",
    )
    roster_receipt_path, roster_receipt = _return_binding(
        manifest.get("assignment_roster_validation_receipt"),
        study_root=study_root,
        label="assignment roster validation receipt",
    )
    expected_roster_receipt = replay_assignment_roster_validation(
        roster,
        roster_path=roster_path,
        assignment_release_path=release_path,
        handoff_path=handoff_path,
        distribution_spec_path=(
            release_path.parent
            / "assignment_distribution_spec_v1.json"
        ),
        study_root=study_root,
    )
    if (
        roster_receipt != expected_roster_receipt
        or roster_receipt.get("status") != "passed"
        or roster_receipt.get("schema_version")
        != ROSTER_VALIDATION_SCHEMA_VERSION
    ):
        raise NDPHumanAssignmentError(
            "assignment roster receipt is not an exact passing replay"
        )
    roster_ids = expected_roster_receipt["reviewer_ids"]

    governance_return = returns["data_governance_review"]
    if not isinstance(governance_return, Mapping):
        raise NDPHumanAssignmentError("governance return must be an object")
    governance_path, governance = _return_binding(
        governance_return.get("submission"),
        study_root=study_root,
        label="governance submission",
    )
    governance_receipt_path, governance_receipt = _return_binding(
        governance_return.get("validation_receipt"),
        study_root=study_root,
        label="governance validation receipt",
    )
    expected_governance_receipt = validate_review(
        governance,
        template=_load_json(sources["governance_template"]),
        audit=_load_json(sources["governance_audit"]),
    )
    if (
        expected_governance_receipt.get("status") != "passed"
        or governance_receipt != expected_governance_receipt
        or governance_receipt.get("schema_version")
        != GOVERNANCE_VALIDATION_SCHEMA_VERSION
    ):
        raise NDPHumanAssignmentError(
            "governance validation receipt is not an exact passing replay"
        )
    stewardship_id = _identifier(
        governance.get("reviewer_signoff", {}).get("reviewer_id"),
        "governance stewardship reviewer ID",
    )
    approver_id = _identifier(
        governance.get("accountable_approval", {}).get("approver_id"),
        "governance accountable approver ID",
    )
    if stewardship_id == approver_id:
        raise NDPHumanAssignmentError(
            "governance signatories must be distinct"
        )
    if governance_return.get("stewardship_reviewer_id") != stewardship_id:
        raise NDPHumanAssignmentError(
            "governance return stewardship ID mismatch"
        )
    if governance_return.get("accountable_approver_id") != approver_id:
        raise NDPHumanAssignmentError(
            "governance return approver ID mismatch"
        )
    if (
        stewardship_id != roster_ids["governance_stewardship"]
        or approver_id
        != roster_ids["governance_accountable_approval"]
    ):
        raise NDPHumanAssignmentError(
            "governance return identities do not match the frozen roster"
        )

    feedback_return = returns["feedback_response_signoff"]
    if not isinstance(feedback_return, Mapping):
        raise NDPHumanAssignmentError(
            "feedback-response signoff return must be an object"
        )
    feedback_path, feedback_submission = _return_binding(
        feedback_return.get("submission"),
        study_root=study_root,
        label="feedback-response signoff submission",
    )
    feedback_receipt_path, feedback_receipt = _return_binding(
        feedback_return.get("validation_receipt"),
        study_root=study_root,
        label="feedback-response signoff validation receipt",
    )
    try:
        feedback_report = validate_feedback_signoff(
            feedback_submission,
            feedback_matrix_path=FEEDBACK_MATRIX_PATH,
            amendment_path=FEEDBACK_AMENDMENT_PATH,
            study_root=PACKAGE_ROOT,
        )
    except Exception as exc:  # noqa: BLE001
        raise NDPHumanAssignmentError(
            f"feedback-response signoff validation failed: {exc}"
        ) from exc
    if (
        feedback_report.get("status") != "passed"
        or feedback_report.get("schema_version")
        != PUBLICATION_VALIDATION_SCHEMA_VERSION
        or feedback_receipt != feedback_report
    ):
        raise NDPHumanAssignmentError(
            "feedback-response validation receipt is not an exact "
            "passing replay"
        )
    if (
        feedback_return.get("reviewer_id")
        != feedback_report.get("collaborator_id")
    ):
        raise NDPHumanAssignmentError(
            "feedback-response return reviewer ID mismatch"
        )
    if (
        feedback_report.get("collaborator_id")
        != roster_ids["feedback_response_signoff"]
    ):
        raise NDPHumanAssignmentError(
            "feedback-response identity does not match the frozen roster"
        )

    registry, _, _ = load_evidence_registry(
        sources["source_bundle_manifest"],
        require_approved=False,
    )
    vocabulary_reports: Dict[str, Dict[str, Any]] = {}
    vocabulary_submissions: Dict[str, Path] = {}
    for slot_id in ("vocabulary_discovery_a", "vocabulary_discovery_b"):
        returned = returns[slot_id]
        if not isinstance(returned, Mapping):
            raise NDPHumanAssignmentError(f"{slot_id} return must be an object")
        submission_path, submission = _return_binding(
            returned.get("submission"),
            study_root=study_root,
            label=f"{slot_id} submission",
        )
        _, receipt = _return_binding(
            returned.get("validation_receipt"),
            study_root=study_root,
            label=f"{slot_id} validation receipt",
        )
        report = validate_discovery(
            submission,
            _load_json(sources["vocabulary_template"]),
            evidence_registry=registry,
            submission_sha256=_sha256_file(submission_path),
        )
        if receipt != report or report.get("status") != "passed":
            raise NDPHumanAssignmentError(
                f"{slot_id} validation receipt is not an exact passing replay"
            )
        for key in ("reviewer_id", "reviewer_role", "submission_id"):
            if returned.get(key) != report.get(key):
                raise NDPHumanAssignmentError(
                    f"{slot_id} return {key} mismatch"
                )
        if report["reviewer_id"] != roster_ids[slot_id]:
            raise NDPHumanAssignmentError(
                f"{slot_id} identity does not match the frozen roster"
            )
        vocabulary_reports[slot_id] = report
        vocabulary_submissions[slot_id] = submission_path

    report_a = vocabulary_reports["vocabulary_discovery_a"]
    report_b = vocabulary_reports["vocabulary_discovery_b"]
    if report_a["reviewer_id"] == report_b["reviewer_id"]:
        raise NDPHumanAssignmentError(
            "vocabulary discovery reviewers must be distinct"
        )
    if report_a["submission_id"] == report_b["submission_id"]:
        raise NDPHumanAssignmentError(
            "vocabulary discovery submission IDs must be distinct"
        )
    if report_a["submission_sha256"] == report_b["submission_sha256"]:
        raise NDPHumanAssignmentError(
            "vocabulary discovery submissions must be distinct frozen files"
        )
    roles = {report_a["reviewer_role"], report_b["reviewer_role"]}
    if (
        any(role not in REVIEWER_ROLES for role in roles)
        or not roles.intersection(CURATOR_ROLES)
        or "annotation_methodologist" not in roles
    ):
        raise NDPHumanAssignmentError(
            "vocabulary pair lacks required role coverage"
        )
    if (
        report_a["reviewer_role"] != "scientific_metadata_curator"
        or report_b["reviewer_role"] != "annotation_methodologist"
    ):
        raise NDPHumanAssignmentError(
            "vocabulary return roles do not match assigned slots"
        )

    freeze = manifest.get("dual_freeze_record")
    if not isinstance(freeze, Mapping):
        raise NDPHumanAssignmentError("dual-freeze record is missing")
    operator_id = _identifier(freeze.get("operator_id"), "freeze operator ID")
    frozen_on = _iso_date(freeze.get("frozen_on"), "freeze date")
    if freeze.get("discovery_a_sha256") != report_a["submission_sha256"]:
        raise NDPHumanAssignmentError("discovery A freeze hash mismatch")
    if freeze.get("discovery_b_sha256") != report_b["submission_sha256"]:
        raise NDPHumanAssignmentError("discovery B freeze hash mismatch")
    for key in (
        "both_receipts_passed_before_comparison",
        "no_cross_review_visibility_before_freeze",
        "candidate_catalog_not_built_before_freeze",
    ):
        if freeze.get(key) is not True:
            raise NDPHumanAssignmentError(
                f"dual-freeze attestation {key} must be true"
            )
    if manifest.get("completion_attestation") is not True:
        raise NDPHumanAssignmentError(
            "return completion attestation must be true"
        )
    return {
        "schema_version": RETURN_VALIDATION_SCHEMA_VERSION,
        "status": "passed",
        "return_manifest_sha256": _sha256_file(manifest_path),
        "assignment_release_sha256": _sha256_file(release_path),
        "assignment_roster_sha256": _sha256_file(roster_path),
        "assignment_roster_validation_receipt_sha256": _sha256_file(
            roster_receipt_path
        ),
        "assignment_roster_frozen_before_submissions": True,
        "governance_submission_sha256": _sha256_file(governance_path),
        "governance_validation_receipt_sha256": _sha256_file(
            governance_receipt_path
        ),
        "feedback_response_signoff_sha256": _sha256_file(feedback_path),
        "feedback_response_validation_receipt_sha256": _sha256_file(
            feedback_receipt_path
        ),
        "feedback_collaborator_id": feedback_report["collaborator_id"],
        "feedback_review_independence_claimed": False,
        "vocabulary_discovery_a_sha256": report_a["submission_sha256"],
        "vocabulary_discovery_b_sha256": report_b["submission_sha256"],
        "vocabulary_reviewer_ids_distinct": True,
        "vocabulary_submission_ids_distinct": True,
        "required_role_coverage_met": True,
        "dual_freeze_attested": True,
        "freeze_operator_id": operator_id,
        "frozen_on": frozen_on,
        "next_authorized_action": (
            "build_vocabulary_candidate_catalog_from_exact_frozen_submissions"
        ),
    }


def _validated_initial_return(
    *,
    return_manifest_path: Path,
    return_validation_path: Path,
    release_path: Path,
    handoff_path: Path,
    study_root: Path,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    manifest = _load_json(return_manifest_path)
    expected = validate_return_manifest(
        manifest,
        manifest_path=return_manifest_path,
        release_path=release_path,
        handoff_path=handoff_path,
        study_root=study_root,
    )
    receipt = _load_json(return_validation_path)
    if receipt != expected or receipt.get("status") != "passed":
        raise NDPHumanAssignmentError(
            "initial return validation is not an exact passing replay"
        )
    return manifest, receipt


def _decision_transition_inputs(
    manifest: Mapping[str, Any],
    *,
    study_root: Path,
) -> tuple[Path, Path]:
    returns = manifest.get("returns")
    if not isinstance(returns, Mapping):
        raise NDPHumanAssignmentError("initial return manifest lacks returns")
    discovery_paths = []
    for slot_id in ("vocabulary_discovery_a", "vocabulary_discovery_b"):
        returned = returns.get(slot_id)
        if not isinstance(returned, Mapping):
            raise NDPHumanAssignmentError(
                f"initial return lacks {slot_id}"
            )
        path, _ = _return_binding(
            returned.get("submission"),
            study_root=study_root,
            label=f"initial {slot_id} submission",
        )
        discovery_paths.append(path)
    return discovery_paths[0], discovery_paths[1]


def _expected_candidate_catalog(
    *,
    initial_manifest: Mapping[str, Any],
    handoff: Mapping[str, Any],
    study_root: Path,
) -> Dict[str, Any]:
    discovery_a_path, discovery_b_path = _decision_transition_inputs(
        initial_manifest,
        study_root=study_root,
    )
    sources = _source_paths(handoff, study_root=study_root)
    registry, _, _ = load_evidence_registry(
        sources["source_bundle_manifest"],
        require_approved=False,
    )
    return build_candidate_catalog(
        _load_json(discovery_a_path),
        _load_json(discovery_b_path),
        _load_json(sources["vocabulary_template"]),
        evidence_registry=registry,
        discovery_a_sha256=_sha256_file(discovery_a_path),
        discovery_b_sha256=_sha256_file(discovery_b_path),
    )


def _decision_assignment_payloads(
    *,
    handoff: Mapping[str, Any],
    handoff_path: Path,
    initial_return_path: Path,
    initial_return_validation_path: Path,
    initial_release_path: Path,
    candidate_catalog_path: Path,
    decision_template_path: Path,
    output_dir: Path,
    study_root: Path,
) -> Dict[str, Dict[str, Any]]:
    initial_manifest = _load_json(initial_return_path)
    sources = _source_paths(handoff, study_root=study_root)
    discovery_ids = {
        initial_manifest["returns"][slot]["reviewer_id"]
        for slot in ("vocabulary_discovery_a", "vocabulary_discovery_b")
    }
    if len(discovery_ids) != 2:
        raise NDPHumanAssignmentError(
            "initial vocabulary discovery reviewer IDs are not distinct"
        )
    result: Dict[str, Dict[str, Any]] = {}
    for suffix, role in (
        ("a", "scientific_metadata_curator"),
        ("b", "annotation_methodologist"),
    ):
        assignment_id = f"vocabulary_candidate_decision_{suffix}"
        payload_path = output_dir / f"{assignment_id}_payload.json"
        if not payload_path.is_file():
            raise NDPHumanAssignmentError(
                f"missing candidate-decision payload {suffix}"
            )
        if payload_path.read_bytes() != decision_template_path.read_bytes():
            raise NDPHumanAssignmentError(
                f"candidate-decision payload {suffix} is not byte-identical"
            )
        result[assignment_id] = {
            "schema_version": ASSIGNMENT_SCHEMA_VERSION,
            "release_state": "ready_unassigned",
            "assignment_id": assignment_id,
            "stage_id": "vocabulary_governance",
            "substage": "independent_candidate_and_policy_decision",
            "execution_mode": "independent_full_catalog_decision",
            "reviewer_id": None,
            "assigned_on": None,
            "required_role": role,
            "fresh_from_discovery_required": True,
            "excluded_reviewer_ids": sorted(discovery_ids),
            "must_differ_from_assignment": (
                "vocabulary_candidate_decision_b"
                if suffix == "a"
                else "vocabulary_candidate_decision_a"
            ),
            "handoff": _binding(handoff_path, study_root),
            "initial_return": _binding(initial_return_path, study_root),
            "initial_return_validation": _binding(
                initial_return_validation_path, study_root
            ),
            "initial_assignment_release": _binding(
                initial_release_path, study_root
            ),
            "candidate_catalog": _binding(
                candidate_catalog_path, study_root
            ),
            "payload": {
                **_binding(payload_path, study_root),
                "copied_from": _binding(
                    decision_template_path, study_root
                ),
                "copy_integrity": "byte_identical",
            },
            "released_inputs": {
                "source_bundle_manifest": _binding(
                    sources["source_bundle_manifest"], study_root
                ),
                "draft_vocabulary": _binding(
                    sources["draft_vocabulary"], study_root
                ),
            },
            "expected_submission_schema": (
                "ndp50-vocabulary-candidate-decision/v1"
            ),
            "validator": {
                "module": (
                    "high_fidelity_schema_study.ndp50_vocabulary_workflow"
                ),
                "command": "validate-decision",
                "implementation": _binding(
                    Path(__file__).with_name(
                        "ndp50_vocabulary_workflow.py"
                    ),
                    Path(__file__).parent,
                ),
            },
            "isolation_contract": {
                "other_decision_visible_before_both_freeze": False,
                "disagreement_worksheet_visible": False,
                "consensus_visible": False,
                "communication_about_decision_content_forbidden": True,
                "full_candidate_catalog_completion_required": True,
                "model_outputs_visible": False,
                "test_data_access": "forbidden",
            },
        }
    return result


def _build_decision_release(
    *,
    handoff: Mapping[str, Any],
    handoff_path: Path,
    initial_return_path: Path,
    initial_return_validation_path: Path,
    initial_release_path: Path,
    candidate_catalog_path: Path,
    decision_template_path: Path,
    output_dir: Path,
    study_root: Path,
) -> Dict[str, Any]:
    assignments = _decision_assignment_payloads(
        handoff=handoff,
        handoff_path=handoff_path,
        initial_return_path=initial_return_path,
        initial_return_validation_path=initial_return_validation_path,
        initial_release_path=initial_release_path,
        candidate_catalog_path=candidate_catalog_path,
        decision_template_path=decision_template_path,
        output_dir=output_dir,
        study_root=study_root,
    )
    assignment_bindings = {}
    for assignment_id, expected in assignments.items():
        path = output_dir / f"{assignment_id}_assignment.json"
        if not path.is_file() or _load_json(path) != expected:
            raise NDPHumanAssignmentError(
                f"candidate-decision wrapper {assignment_id} is stale"
            )
        assignment_bindings[assignment_id] = _binding(path, study_root)
    initial_manifest = _load_json(initial_return_path)
    discovery_a_path, discovery_b_path = _decision_transition_inputs(
        initial_manifest,
        study_root=study_root,
    )
    implementation = Path(__file__).resolve()
    transition_material = ":".join(
        (
            DECISION_RELEASE_SCHEMA_VERSION,
            _sha256_file(initial_return_path),
            _sha256_file(initial_return_validation_path),
            _sha256_file(candidate_catalog_path),
            _sha256_file(implementation),
        )
    )
    return {
        "schema_version": DECISION_RELEASE_SCHEMA_VERSION,
        "status": "released_unassigned",
        "release_id": (
            "ndp50-vocabulary-decision-release-"
            + hashlib.sha256(transition_material.encode("utf-8")).hexdigest()[
                :20
            ]
        ),
        "handoff": _binding(handoff_path, study_root),
        "initial_assignment_release": _binding(
            initial_release_path, study_root
        ),
        "initial_return": _binding(initial_return_path, study_root),
        "initial_return_validation": _binding(
            initial_return_validation_path, study_root
        ),
        "frozen_discoveries": {
            "discovery_a": {
                "submission": _binding(discovery_a_path, study_root),
                "reviewer_id": initial_manifest["returns"][
                    "vocabulary_discovery_a"
                ]["reviewer_id"],
            },
            "discovery_b": {
                "submission": _binding(discovery_b_path, study_root),
                "reviewer_id": initial_manifest["returns"][
                    "vocabulary_discovery_b"
                ]["reviewer_id"],
            },
        },
        "candidate_catalog": _binding(candidate_catalog_path, study_root),
        "neutral_decision_template": _binding(
            decision_template_path, study_root
        ),
        "assignments": assignment_bindings,
        "assignment_count": 2,
        "return_manifest_schema": DECISION_RETURN_SCHEMA_VERSION,
        "reviewer_continuity_policy": {
            "fresh_pair_required": True,
            "rationale": (
                "A fresh pair reduces proposal-ownership and recall bias "
                "between discovery and candidate acceptance."
            ),
            "required_role_coverage": [
                "scientific_metadata_curator",
                "annotation_methodologist",
            ],
        },
        "independence_controls": {
            "reviewer_ids_present_at_release": False,
            "decision_payloads_byte_identical": True,
            "cross_decision_visibility_before_dual_freeze": False,
            "disagreement_reveal_before_dual_freeze": False,
            "human_candidate_decisions_present_at_release": False,
            "model_outputs_visible": False,
            "test_data_access": "forbidden",
        },
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            name: _sha256_file(implementation.with_name(name))
            for name in (
                "ndp50_human_handoff.py",
                "ndp50_vocabulary_workflow.py",
                "ndp50_cpa_screen_workflow.py",
            )
        },
    }


def _build_decision_return_template(
    release_path: Path,
    *,
    study_root: Path,
) -> Dict[str, Any]:
    release = _load_json(release_path)
    return {
        "schema_version": DECISION_RETURN_SCHEMA_VERSION,
        "status": "pending_human_returns",
        "decision_assignment_release": _binding(
            release_path, study_root
        ),
        "release_id": release["release_id"],
        "returns": {
            assignment_id: {
                "reviewer_id": None,
                "reviewer_role": None,
                "submission_id": None,
                "submission": None,
                "validation_receipt": None,
            }
            for assignment_id in (
                "vocabulary_candidate_decision_a",
                "vocabulary_candidate_decision_b",
            )
        },
        "dual_freeze_record": {
            "operator_id": None,
            "frozen_on": None,
            "decision_a_sha256": None,
            "decision_b_sha256": None,
            "both_receipts_passed_before_comparison": None,
            "no_cross_decision_visibility_before_freeze": None,
            "disagreement_worksheet_not_built_before_freeze": None,
            "consensus_not_started_before_freeze": None,
        },
        "completion_attestation": None,
    }


def prepare_decision_assignment_package(
    *,
    return_manifest_path: Path,
    return_validation_path: Path,
    initial_release_path: Path,
    handoff_path: Path,
    study_root: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    study_root = study_root.resolve()
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(study_root):
        raise NDPHumanAssignmentError(
            "decision-assignment output must be inside the study root"
        )
    initial_manifest, _ = _validated_initial_return(
        return_manifest_path=return_manifest_path,
        return_validation_path=return_validation_path,
        release_path=initial_release_path,
        handoff_path=handoff_path,
        study_root=study_root,
    )
    handoff = _verify_handoff(handoff_path, study_root=study_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    catalog = _expected_candidate_catalog(
        initial_manifest=initial_manifest,
        handoff=handoff,
        study_root=study_root,
    )
    candidate_catalog_path = output_dir / "vocabulary_candidate_catalog.json"
    _write_json(candidate_catalog_path, catalog)
    decision_template_path = output_dir / "decision_template_neutral.json"
    _write_json(decision_template_path, build_decision_template(catalog))
    for suffix in ("a", "b"):
        shutil.copyfile(
            decision_template_path,
            output_dir
            / f"vocabulary_candidate_decision_{suffix}_payload.json",
        )
    assignment_payloads = _decision_assignment_payloads(
        handoff=handoff,
        handoff_path=handoff_path,
        initial_return_path=return_manifest_path,
        initial_return_validation_path=return_validation_path,
        initial_release_path=initial_release_path,
        candidate_catalog_path=candidate_catalog_path,
        decision_template_path=decision_template_path,
        output_dir=output_dir,
        study_root=study_root,
    )
    for assignment_id, payload in assignment_payloads.items():
        _write_json(
            output_dir / f"{assignment_id}_assignment.json",
            payload,
        )
    release = _build_decision_release(
        handoff=handoff,
        handoff_path=handoff_path,
        initial_return_path=return_manifest_path,
        initial_return_validation_path=return_validation_path,
        initial_release_path=initial_release_path,
        candidate_catalog_path=candidate_catalog_path,
        decision_template_path=decision_template_path,
        output_dir=output_dir,
        study_root=study_root,
    )
    release_path = output_dir / "decision_assignment_release_v1.json"
    _write_json(release_path, release)
    _write_json(
        output_dir / "decision_return_manifest_neutral_v1.json",
        _build_decision_return_template(
            release_path,
            study_root=study_root,
        ),
    )
    return release


def validate_decision_assignment_release(
    release: Mapping[str, Any],
    *,
    release_path: Path,
    return_manifest_path: Path,
    return_validation_path: Path,
    initial_release_path: Path,
    handoff_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    try:
        initial_manifest, _ = _validated_initial_return(
            return_manifest_path=return_manifest_path,
            return_validation_path=return_validation_path,
            release_path=initial_release_path,
            handoff_path=handoff_path,
            study_root=study_root,
        )
        handoff = _verify_handoff(handoff_path, study_root=study_root)
        candidate_catalog_path = release_path.parent / (
            "vocabulary_candidate_catalog.json"
        )
        expected_catalog = _expected_candidate_catalog(
            initial_manifest=initial_manifest,
            handoff=handoff,
            study_root=study_root,
        )
        if _load_json(candidate_catalog_path) != expected_catalog:
            raise NDPHumanAssignmentError(
                "candidate catalog does not replay from frozen discoveries"
            )
        decision_template_path = (
            release_path.parent / "decision_template_neutral.json"
        )
        if _load_json(decision_template_path) != build_decision_template(
            expected_catalog
        ):
            raise NDPHumanAssignmentError(
                "candidate-decision template does not replay"
            )
        expected = _build_decision_release(
            handoff=handoff,
            handoff_path=handoff_path,
            initial_return_path=return_manifest_path,
            initial_return_validation_path=return_validation_path,
            initial_release_path=initial_release_path,
            candidate_catalog_path=candidate_catalog_path,
            decision_template_path=decision_template_path,
            output_dir=release_path.parent,
            study_root=study_root,
        )
        differing = sorted(
            key
            for key in set(release) | set(expected)
            if release.get(key) != expected.get(key)
        )
        status = "passed" if not differing else "failed"
        detail = None
    except Exception as exc:  # noqa: BLE001
        differing = ["replay"]
        status = "failed"
        detail = str(exc)
    return {
        "schema_version": DECISION_RELEASE_VALIDATION_SCHEMA_VERSION,
        "status": status,
        "release_sha256": _sha256_file(release_path),
        "differing_top_level_keys": differing,
        "detail": detail,
    }


def validate_decision_return_manifest(
    manifest: Mapping[str, Any],
    *,
    manifest_path: Path,
    release_path: Path,
    initial_return_path: Path,
    initial_return_validation_path: Path,
    initial_release_path: Path,
    handoff_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    release = _load_json(release_path)
    release_validation = validate_decision_assignment_release(
        release,
        release_path=release_path,
        return_manifest_path=initial_return_path,
        return_validation_path=initial_return_validation_path,
        initial_release_path=initial_release_path,
        handoff_path=handoff_path,
        study_root=study_root,
    )
    if release_validation["status"] != "passed":
        raise NDPHumanAssignmentError(
            "candidate-decision assignment release replay failed"
        )
    if manifest.get("schema_version") != DECISION_RETURN_SCHEMA_VERSION:
        raise NDPHumanAssignmentError(
            "unexpected candidate-decision return schema"
        )
    if manifest.get("status") != "completed_pending_validator_acceptance":
        raise NDPHumanAssignmentError(
            "candidate-decision return status is incomplete"
        )
    if manifest.get("decision_assignment_release") != _binding(
        release_path, study_root
    ):
        raise NDPHumanAssignmentError(
            "candidate-decision return binds a different release"
        )
    if manifest.get("release_id") != release.get("release_id"):
        raise NDPHumanAssignmentError(
            "candidate-decision return release ID mismatch"
        )
    returns = manifest.get("returns")
    expected_slots = {
        "vocabulary_candidate_decision_a",
        "vocabulary_candidate_decision_b",
    }
    if not isinstance(returns, Mapping) or set(returns) != expected_slots:
        raise NDPHumanAssignmentError(
            "candidate-decision return slots differ from release"
        )
    candidate_catalog_path = _resolve_binding(
        release["candidate_catalog"],
        root=study_root,
        label="candidate catalog",
    )
    candidate_catalog = _load_json(candidate_catalog_path)
    handoff = _verify_handoff(handoff_path, study_root=study_root)
    sources = _source_paths(handoff, study_root=study_root)
    registry, _, _ = load_evidence_registry(
        sources["source_bundle_manifest"],
        require_approved=False,
    )
    reports: Dict[str, Dict[str, Any]] = {}
    for slot_id in sorted(expected_slots):
        returned = returns[slot_id]
        if not isinstance(returned, Mapping):
            raise NDPHumanAssignmentError(f"{slot_id} return is invalid")
        submission_path, submission = _return_binding(
            returned.get("submission"),
            study_root=study_root,
            label=f"{slot_id} submission",
        )
        _, receipt = _return_binding(
            returned.get("validation_receipt"),
            study_root=study_root,
            label=f"{slot_id} validation receipt",
        )
        report = validate_decision(
            submission,
            candidate_catalog,
            evidence_registry=registry,
            submission_sha256=_sha256_file(submission_path),
        )
        if receipt != report or report.get("status") != "passed":
            raise NDPHumanAssignmentError(
                f"{slot_id} receipt is not an exact passing replay"
            )
        for key in ("reviewer_id", "reviewer_role", "submission_id"):
            if returned.get(key) != report.get(key):
                raise NDPHumanAssignmentError(
                    f"{slot_id} return {key} mismatch"
                )
        reports[slot_id] = report
    report_a = reports["vocabulary_candidate_decision_a"]
    report_b = reports["vocabulary_candidate_decision_b"]
    if report_a["reviewer_id"] == report_b["reviewer_id"]:
        raise NDPHumanAssignmentError(
            "candidate-decision reviewers must be distinct"
        )
    if report_a["submission_id"] == report_b["submission_id"]:
        raise NDPHumanAssignmentError(
            "candidate-decision submission IDs must be distinct"
        )
    if report_a["submission_sha256"] == report_b["submission_sha256"]:
        raise NDPHumanAssignmentError(
            "candidate-decision files must be distinct"
        )
    if (
        report_a["reviewer_role"] != "scientific_metadata_curator"
        or report_b["reviewer_role"] != "annotation_methodologist"
    ):
        raise NDPHumanAssignmentError(
            "candidate-decision roles do not match assigned slots"
        )
    discovery_reviewer_ids = {
        item["reviewer_id"]
        for item in release["frozen_discoveries"].values()
    }
    reused = {
        report_a["reviewer_id"],
        report_b["reviewer_id"],
    }.intersection(discovery_reviewer_ids)
    if reused:
        raise NDPHumanAssignmentError(
            "candidate-decision reviewers must be fresh from discovery"
        )
    freeze = manifest.get("dual_freeze_record")
    if not isinstance(freeze, Mapping):
        raise NDPHumanAssignmentError(
            "candidate-decision dual-freeze record is missing"
        )
    operator_id = _identifier(
        freeze.get("operator_id"), "candidate-decision freeze operator ID"
    )
    frozen_on = _iso_date(
        freeze.get("frozen_on"), "candidate-decision freeze date"
    )
    if freeze.get("decision_a_sha256") != report_a["submission_sha256"]:
        raise NDPHumanAssignmentError("candidate decision A hash mismatch")
    if freeze.get("decision_b_sha256") != report_b["submission_sha256"]:
        raise NDPHumanAssignmentError("candidate decision B hash mismatch")
    for key in (
        "both_receipts_passed_before_comparison",
        "no_cross_decision_visibility_before_freeze",
        "disagreement_worksheet_not_built_before_freeze",
        "consensus_not_started_before_freeze",
    ):
        if freeze.get(key) is not True:
            raise NDPHumanAssignmentError(
                f"candidate-decision freeze attestation {key} must be true"
            )
    if manifest.get("completion_attestation") is not True:
        raise NDPHumanAssignmentError(
            "candidate-decision return completion is not attested"
        )
    return {
        "schema_version": DECISION_RETURN_VALIDATION_SCHEMA_VERSION,
        "status": "passed",
        "return_manifest_sha256": _sha256_file(manifest_path),
        "decision_assignment_release_sha256": _sha256_file(release_path),
        "candidate_catalog_sha256": _sha256_file(candidate_catalog_path),
        "decision_a_sha256": report_a["submission_sha256"],
        "decision_b_sha256": report_b["submission_sha256"],
        "decision_reviewer_ids_distinct": True,
        "decision_reviewers_fresh_from_discovery": True,
        "required_role_coverage_met": True,
        "dual_freeze_attested": True,
        "freeze_operator_id": operator_id,
        "frozen_on": frozen_on,
        "next_authorized_action": (
            "compare_exact_frozen_candidate_decisions_and_reveal_disagreements"
        ),
    }


def _validated_decision_return(
    *,
    decision_return_path: Path,
    decision_return_validation_path: Path,
    decision_release_path: Path,
    initial_return_path: Path,
    initial_return_validation_path: Path,
    initial_release_path: Path,
    handoff_path: Path,
    study_root: Path,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    manifest = _load_json(decision_return_path)
    expected = validate_decision_return_manifest(
        manifest,
        manifest_path=decision_return_path,
        release_path=decision_release_path,
        initial_return_path=initial_return_path,
        initial_return_validation_path=initial_return_validation_path,
        initial_release_path=initial_release_path,
        handoff_path=handoff_path,
        study_root=study_root,
    )
    receipt = _load_json(decision_return_validation_path)
    if receipt != expected or receipt.get("status") != "passed":
        raise NDPHumanAssignmentError(
            "decision return validation is not an exact passing replay"
        )
    return manifest, receipt


def _decision_submission_paths(
    manifest: Mapping[str, Any],
    *,
    study_root: Path,
) -> tuple[Path, Path]:
    returns = manifest.get("returns")
    if not isinstance(returns, Mapping):
        raise NDPHumanAssignmentError("decision return lacks returns")
    paths = []
    for slot_id in (
        "vocabulary_candidate_decision_a",
        "vocabulary_candidate_decision_b",
    ):
        returned = returns.get(slot_id)
        if not isinstance(returned, Mapping):
            raise NDPHumanAssignmentError(
                f"decision return lacks {slot_id}"
            )
        path, _ = _return_binding(
            returned.get("submission"),
            study_root=study_root,
            label=f"{slot_id} submission",
        )
        paths.append(path)
    return paths[0], paths[1]


def _expected_decision_worksheet(
    *,
    decision_return: Mapping[str, Any],
    decision_release: Mapping[str, Any],
    handoff: Mapping[str, Any],
    study_root: Path,
) -> Dict[str, Any]:
    decision_a_path, decision_b_path = _decision_submission_paths(
        decision_return,
        study_root=study_root,
    )
    catalog_path = _resolve_binding(
        decision_release["candidate_catalog"],
        root=study_root,
        label="candidate catalog",
    )
    sources = _source_paths(handoff, study_root=study_root)
    registry, _, _ = load_evidence_registry(
        sources["source_bundle_manifest"],
        require_approved=False,
    )
    return compare_decisions(
        _load_json(decision_a_path),
        _load_json(decision_b_path),
        _load_json(catalog_path),
        evidence_registry=registry,
        decision_a_sha256=_sha256_file(decision_a_path),
        decision_b_sha256=_sha256_file(decision_b_path),
    )


def _consensus_assignment_payload(
    *,
    handoff_path: Path,
    decision_release_path: Path,
    decision_return_path: Path,
    decision_return_validation_path: Path,
    worksheet_path: Path,
    consensus_template_path: Path,
    output_dir: Path,
    study_root: Path,
) -> Dict[str, Any]:
    decision_release = _load_json(decision_release_path)
    decision_return = _load_json(decision_return_path)
    excluded_ids = {
        item["reviewer_id"]
        for item in decision_release["frozen_discoveries"].values()
    }
    excluded_ids.update(
        item["reviewer_id"]
        for item in decision_return["returns"].values()
    )
    payload_path = output_dir / "vocabulary_consensus_payload.json"
    if not payload_path.is_file():
        raise NDPHumanAssignmentError("missing vocabulary consensus payload")
    if payload_path.read_bytes() != consensus_template_path.read_bytes():
        raise NDPHumanAssignmentError(
            "vocabulary consensus payload is not byte-identical"
        )
    return {
        "schema_version": ASSIGNMENT_SCHEMA_VERSION,
        "release_state": "ready_unassigned",
        "assignment_id": "vocabulary_consensus_adjudication",
        "stage_id": "vocabulary_governance",
        "substage": "post_freeze_human_consensus",
        "execution_mode": "independent_evidence_bound_adjudication",
        "adjudicator_id": None,
        "assigned_on": None,
        "allowed_roles": sorted(CONSENSUS_ADJUDICATOR_ROLES),
        "fresh_from_all_prior_vocabulary_reviews_required": True,
        "excluded_reviewer_ids": sorted(excluded_ids),
        "handoff": _binding(handoff_path, study_root),
        "decision_assignment_release": _binding(
            decision_release_path, study_root
        ),
        "decision_return": _binding(decision_return_path, study_root),
        "decision_return_validation": _binding(
            decision_return_validation_path, study_root
        ),
        "disagreement_worksheet": _binding(worksheet_path, study_root),
        "candidate_catalog": decision_release["candidate_catalog"],
        "payload": {
            **_binding(payload_path, study_root),
            "copied_from": _binding(consensus_template_path, study_root),
            "copy_integrity": "byte_identical",
        },
        "expected_submission_schema": "ndp50-vocabulary-consensus/v1",
        "validator": {
            "module": (
                "high_fidelity_schema_study.ndp50_vocabulary_workflow"
            ),
            "command": "validate-consensus",
            "implementation": _binding(
                Path(__file__).with_name("ndp50_vocabulary_workflow.py"),
                Path(__file__).parent,
            ),
        },
        "adjudication_contract": {
            "agreed_slots_immutable": True,
            "every_disagreement_requires_evidence": True,
            "qualification_summary_required": True,
            "negative_conflict_declaration_required": True,
            "non_developer_required": True,
            "automatic_adjudication_forbidden": True,
            "model_outputs_visible": False,
            "test_data_access": "forbidden",
        },
    }


def _build_consensus_release(
    *,
    handoff_path: Path,
    decision_release_path: Path,
    decision_return_path: Path,
    decision_return_validation_path: Path,
    worksheet_path: Path,
    consensus_template_path: Path,
    output_dir: Path,
    study_root: Path,
) -> Dict[str, Any]:
    expected_assignment = _consensus_assignment_payload(
        handoff_path=handoff_path,
        decision_release_path=decision_release_path,
        decision_return_path=decision_return_path,
        decision_return_validation_path=decision_return_validation_path,
        worksheet_path=worksheet_path,
        consensus_template_path=consensus_template_path,
        output_dir=output_dir,
        study_root=study_root,
    )
    assignment_path = output_dir / "vocabulary_consensus_assignment.json"
    if (
        not assignment_path.is_file()
        or _load_json(assignment_path) != expected_assignment
    ):
        raise NDPHumanAssignmentError(
            "vocabulary consensus assignment is missing or stale"
        )
    implementation = Path(__file__).resolve()
    material = ":".join(
        (
            CONSENSUS_RELEASE_SCHEMA_VERSION,
            _sha256_file(decision_return_path),
            _sha256_file(decision_return_validation_path),
            _sha256_file(worksheet_path),
            _sha256_file(implementation),
        )
    )
    return {
        "schema_version": CONSENSUS_RELEASE_SCHEMA_VERSION,
        "status": "released_unassigned",
        "release_id": (
            "ndp50-vocabulary-consensus-release-"
            + hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]
        ),
        "handoff": _binding(handoff_path, study_root),
        "decision_assignment_release": _binding(
            decision_release_path, study_root
        ),
        "decision_return": _binding(decision_return_path, study_root),
        "decision_return_validation": _binding(
            decision_return_validation_path, study_root
        ),
        "candidate_catalog": _load_json(decision_release_path)[
            "candidate_catalog"
        ],
        "disagreement_worksheet": _binding(worksheet_path, study_root),
        "neutral_consensus_template": _binding(
            consensus_template_path, study_root
        ),
        "assignment": _binding(assignment_path, study_root),
        "return_manifest_schema": CONSENSUS_RETURN_SCHEMA_VERSION,
        "adjudicator_policy": {
            "fresh_from_discovery_and_decisions_required": True,
            "qualified_role_required": True,
            "negative_conflict_declaration_required": True,
            "non_developer_required": True,
        },
        "human_consensus_present_at_release": False,
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            name: _sha256_file(implementation.with_name(name))
            for name in (
                "ndp50_human_handoff.py",
                "ndp50_vocabulary_workflow.py",
                "ndp50_cpa_screen_workflow.py",
            )
        },
    }


def _build_consensus_return_template(
    release_path: Path,
    *,
    study_root: Path,
) -> Dict[str, Any]:
    release = _load_json(release_path)
    return {
        "schema_version": CONSENSUS_RETURN_SCHEMA_VERSION,
        "status": "pending_human_return",
        "consensus_assignment_release": _binding(
            release_path, study_root
        ),
        "release_id": release["release_id"],
        "adjudicator_id": None,
        "adjudicator_role": None,
        "submission": None,
        "validation_receipt": None,
        "completion_attestation": None,
    }


def prepare_consensus_assignment_package(
    *,
    decision_return_path: Path,
    decision_return_validation_path: Path,
    decision_release_path: Path,
    initial_return_path: Path,
    initial_return_validation_path: Path,
    initial_release_path: Path,
    handoff_path: Path,
    study_root: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    study_root = study_root.resolve()
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(study_root):
        raise NDPHumanAssignmentError(
            "consensus-assignment output must be inside the study root"
        )
    decision_return, _ = _validated_decision_return(
        decision_return_path=decision_return_path,
        decision_return_validation_path=decision_return_validation_path,
        decision_release_path=decision_release_path,
        initial_return_path=initial_return_path,
        initial_return_validation_path=initial_return_validation_path,
        initial_release_path=initial_release_path,
        handoff_path=handoff_path,
        study_root=study_root,
    )
    decision_release = _load_json(decision_release_path)
    handoff = _verify_handoff(handoff_path, study_root=study_root)
    worksheet = _expected_decision_worksheet(
        decision_return=decision_return,
        decision_release=decision_release,
        handoff=handoff,
        study_root=study_root,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    worksheet_path = output_dir / "vocabulary_disagreement_worksheet.json"
    _write_json(worksheet_path, worksheet)
    consensus_template_path = output_dir / "consensus_template_neutral.json"
    _write_json(
        consensus_template_path,
        build_consensus_template(
            worksheet,
            worksheet_sha256=_sha256_file(worksheet_path),
        ),
    )
    shutil.copyfile(
        consensus_template_path,
        output_dir / "vocabulary_consensus_payload.json",
    )
    assignment = _consensus_assignment_payload(
        handoff_path=handoff_path,
        decision_release_path=decision_release_path,
        decision_return_path=decision_return_path,
        decision_return_validation_path=decision_return_validation_path,
        worksheet_path=worksheet_path,
        consensus_template_path=consensus_template_path,
        output_dir=output_dir,
        study_root=study_root,
    )
    _write_json(
        output_dir / "vocabulary_consensus_assignment.json",
        assignment,
    )
    release = _build_consensus_release(
        handoff_path=handoff_path,
        decision_release_path=decision_release_path,
        decision_return_path=decision_return_path,
        decision_return_validation_path=decision_return_validation_path,
        worksheet_path=worksheet_path,
        consensus_template_path=consensus_template_path,
        output_dir=output_dir,
        study_root=study_root,
    )
    release_path = output_dir / "consensus_assignment_release_v1.json"
    _write_json(release_path, release)
    _write_json(
        output_dir / "consensus_return_manifest_neutral_v1.json",
        _build_consensus_return_template(
            release_path,
            study_root=study_root,
        ),
    )
    return release


def validate_consensus_assignment_release(
    release: Mapping[str, Any],
    *,
    release_path: Path,
    decision_return_path: Path,
    decision_return_validation_path: Path,
    decision_release_path: Path,
    initial_return_path: Path,
    initial_return_validation_path: Path,
    initial_release_path: Path,
    handoff_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    try:
        decision_return, _ = _validated_decision_return(
            decision_return_path=decision_return_path,
            decision_return_validation_path=decision_return_validation_path,
            decision_release_path=decision_release_path,
            initial_return_path=initial_return_path,
            initial_return_validation_path=initial_return_validation_path,
            initial_release_path=initial_release_path,
            handoff_path=handoff_path,
            study_root=study_root,
        )
        decision_release = _load_json(decision_release_path)
        handoff = _verify_handoff(handoff_path, study_root=study_root)
        expected_worksheet = _expected_decision_worksheet(
            decision_return=decision_return,
            decision_release=decision_release,
            handoff=handoff,
            study_root=study_root,
        )
        worksheet_path = (
            release_path.parent / "vocabulary_disagreement_worksheet.json"
        )
        if _load_json(worksheet_path) != expected_worksheet:
            raise NDPHumanAssignmentError(
                "disagreement worksheet does not replay from frozen decisions"
            )
        consensus_template_path = (
            release_path.parent / "consensus_template_neutral.json"
        )
        expected_template = build_consensus_template(
            expected_worksheet,
            worksheet_sha256=_sha256_file(worksheet_path),
        )
        if _load_json(consensus_template_path) != expected_template:
            raise NDPHumanAssignmentError(
                "consensus template does not replay from worksheet"
            )
        expected = _build_consensus_release(
            handoff_path=handoff_path,
            decision_release_path=decision_release_path,
            decision_return_path=decision_return_path,
            decision_return_validation_path=decision_return_validation_path,
            worksheet_path=worksheet_path,
            consensus_template_path=consensus_template_path,
            output_dir=release_path.parent,
            study_root=study_root,
        )
        differing = sorted(
            key
            for key in set(release) | set(expected)
            if release.get(key) != expected.get(key)
        )
        status = "passed" if not differing else "failed"
        detail = None
    except Exception as exc:  # noqa: BLE001
        differing = ["replay"]
        status = "failed"
        detail = str(exc)
    return {
        "schema_version": CONSENSUS_RELEASE_VALIDATION_SCHEMA_VERSION,
        "status": status,
        "release_sha256": _sha256_file(release_path),
        "differing_top_level_keys": differing,
        "detail": detail,
    }


def validate_consensus_return_manifest(
    manifest: Mapping[str, Any],
    *,
    manifest_path: Path,
    release_path: Path,
    decision_return_path: Path,
    decision_return_validation_path: Path,
    decision_release_path: Path,
    initial_return_path: Path,
    initial_return_validation_path: Path,
    initial_release_path: Path,
    handoff_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    release = _load_json(release_path)
    release_validation = validate_consensus_assignment_release(
        release,
        release_path=release_path,
        decision_return_path=decision_return_path,
        decision_return_validation_path=decision_return_validation_path,
        decision_release_path=decision_release_path,
        initial_return_path=initial_return_path,
        initial_return_validation_path=initial_return_validation_path,
        initial_release_path=initial_release_path,
        handoff_path=handoff_path,
        study_root=study_root,
    )
    if release_validation["status"] != "passed":
        raise NDPHumanAssignmentError(
            "consensus assignment release replay failed"
        )
    if manifest.get("schema_version") != CONSENSUS_RETURN_SCHEMA_VERSION:
        raise NDPHumanAssignmentError("unexpected consensus return schema")
    if manifest.get("status") != "completed_pending_validator_acceptance":
        raise NDPHumanAssignmentError("consensus return is incomplete")
    if manifest.get("consensus_assignment_release") != _binding(
        release_path, study_root
    ):
        raise NDPHumanAssignmentError(
            "consensus return binds a different release"
        )
    if manifest.get("release_id") != release.get("release_id"):
        raise NDPHumanAssignmentError("consensus return release ID mismatch")
    consensus_path, consensus = _return_binding(
        manifest.get("submission"),
        study_root=study_root,
        label="consensus submission",
    )
    _, receipt = _return_binding(
        manifest.get("validation_receipt"),
        study_root=study_root,
        label="consensus validation receipt",
    )
    decision_return = _load_json(decision_return_path)
    decision_a_path, decision_b_path = _decision_submission_paths(
        decision_return,
        study_root=study_root,
    )
    decision_release = _load_json(decision_release_path)
    catalog_path = _resolve_binding(
        decision_release["candidate_catalog"],
        root=study_root,
        label="candidate catalog",
    )
    worksheet_path = _resolve_binding(
        release["disagreement_worksheet"],
        root=study_root,
        label="disagreement worksheet",
    )
    handoff = _verify_handoff(handoff_path, study_root=study_root)
    sources = _source_paths(handoff, study_root=study_root)
    registry, _, _ = load_evidence_registry(
        sources["source_bundle_manifest"],
        require_approved=False,
    )
    expected_receipt = validate_consensus(
        consensus,
        _load_json(decision_a_path),
        _load_json(decision_b_path),
        _load_json(catalog_path),
        _load_json(worksheet_path),
        evidence_registry=registry,
        decision_a_sha256=_sha256_file(decision_a_path),
        decision_b_sha256=_sha256_file(decision_b_path),
        worksheet_sha256=_sha256_file(worksheet_path),
        consensus_sha256=_sha256_file(consensus_path),
    )
    if receipt != expected_receipt or receipt.get("status") != "passed":
        raise NDPHumanAssignmentError(
            "consensus receipt is not an exact passing replay"
        )
    for key in ("adjudicator_id", "adjudicator_role"):
        if manifest.get(key) != expected_receipt.get(key):
            raise NDPHumanAssignmentError(
                f"consensus return {key} mismatch"
            )
    if manifest.get("completion_attestation") is not True:
        raise NDPHumanAssignmentError(
            "consensus return completion is not attested"
        )
    return {
        "schema_version": CONSENSUS_RETURN_VALIDATION_SCHEMA_VERSION,
        "status": "passed",
        "return_manifest_sha256": _sha256_file(manifest_path),
        "consensus_assignment_release_sha256": _sha256_file(release_path),
        "candidate_catalog_sha256": _sha256_file(catalog_path),
        "worksheet_sha256": _sha256_file(worksheet_path),
        "consensus_sha256": _sha256_file(consensus_path),
        "adjudicator_id": expected_receipt["adjudicator_id"],
        "adjudicator_role": expected_receipt["adjudicator_role"],
        "adjudicator_independent_of_prior_stages": True,
        "all_required_policies_accepted": expected_receipt[
            "all_required_policies_accepted"
        ],
        "corpus_coverage_accepted": expected_receipt[
            "corpus_coverage_accepted"
        ],
        "next_authorized_action": (
            "build_frozen_vocabulary_from_exact_validated_consensus"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare and validate content-addressed NDP-50 human assignments."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--handoff", type=Path, required=True)
    prepare.add_argument("--study-root", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)

    validate_release = subparsers.add_parser("validate-release")
    validate_release.add_argument("--artifact", type=Path, required=True)
    validate_release.add_argument("--handoff", type=Path, required=True)
    validate_release.add_argument("--study-root", type=Path, required=True)
    validate_release.add_argument("--output", type=Path)

    validate_returns = subparsers.add_parser("validate-returns")
    validate_returns.add_argument("--return-manifest", type=Path, required=True)
    validate_returns.add_argument(
        "--assignment-release", type=Path, required=True
    )
    validate_returns.add_argument("--handoff", type=Path, required=True)
    validate_returns.add_argument("--study-root", type=Path, required=True)
    validate_returns.add_argument("--output", type=Path, required=True)

    prepare_decisions = subparsers.add_parser("prepare-decisions")
    prepare_decisions.add_argument(
        "--initial-return", type=Path, required=True
    )
    prepare_decisions.add_argument(
        "--initial-return-validation", type=Path, required=True
    )
    prepare_decisions.add_argument(
        "--initial-assignment-release", type=Path, required=True
    )
    prepare_decisions.add_argument("--handoff", type=Path, required=True)
    prepare_decisions.add_argument("--study-root", type=Path, required=True)
    prepare_decisions.add_argument("--output-dir", type=Path, required=True)

    validate_decision_release = subparsers.add_parser(
        "validate-decision-release"
    )
    validate_decision_release.add_argument(
        "--artifact", type=Path, required=True
    )
    validate_decision_release.add_argument(
        "--initial-return", type=Path, required=True
    )
    validate_decision_release.add_argument(
        "--initial-return-validation", type=Path, required=True
    )
    validate_decision_release.add_argument(
        "--initial-assignment-release", type=Path, required=True
    )
    validate_decision_release.add_argument(
        "--handoff", type=Path, required=True
    )
    validate_decision_release.add_argument(
        "--study-root", type=Path, required=True
    )
    validate_decision_release.add_argument("--output", type=Path)

    validate_decision_returns = subparsers.add_parser(
        "validate-decision-returns"
    )
    validate_decision_returns.add_argument(
        "--return-manifest", type=Path, required=True
    )
    validate_decision_returns.add_argument(
        "--decision-assignment-release", type=Path, required=True
    )
    validate_decision_returns.add_argument(
        "--initial-return", type=Path, required=True
    )
    validate_decision_returns.add_argument(
        "--initial-return-validation", type=Path, required=True
    )
    validate_decision_returns.add_argument(
        "--initial-assignment-release", type=Path, required=True
    )
    validate_decision_returns.add_argument(
        "--handoff", type=Path, required=True
    )
    validate_decision_returns.add_argument(
        "--study-root", type=Path, required=True
    )
    validate_decision_returns.add_argument("--output", type=Path, required=True)

    prepare_consensus = subparsers.add_parser("prepare-consensus")
    prepare_consensus.add_argument(
        "--decision-return", type=Path, required=True
    )
    prepare_consensus.add_argument(
        "--decision-return-validation", type=Path, required=True
    )
    prepare_consensus.add_argument(
        "--decision-assignment-release", type=Path, required=True
    )
    prepare_consensus.add_argument(
        "--initial-return", type=Path, required=True
    )
    prepare_consensus.add_argument(
        "--initial-return-validation", type=Path, required=True
    )
    prepare_consensus.add_argument(
        "--initial-assignment-release", type=Path, required=True
    )
    prepare_consensus.add_argument("--handoff", type=Path, required=True)
    prepare_consensus.add_argument("--study-root", type=Path, required=True)
    prepare_consensus.add_argument("--output-dir", type=Path, required=True)

    validate_consensus_release = subparsers.add_parser(
        "validate-consensus-release"
    )
    validate_consensus_release.add_argument(
        "--artifact", type=Path, required=True
    )
    validate_consensus_release.add_argument(
        "--decision-return", type=Path, required=True
    )
    validate_consensus_release.add_argument(
        "--decision-return-validation", type=Path, required=True
    )
    validate_consensus_release.add_argument(
        "--decision-assignment-release", type=Path, required=True
    )
    validate_consensus_release.add_argument(
        "--initial-return", type=Path, required=True
    )
    validate_consensus_release.add_argument(
        "--initial-return-validation", type=Path, required=True
    )
    validate_consensus_release.add_argument(
        "--initial-assignment-release", type=Path, required=True
    )
    validate_consensus_release.add_argument(
        "--handoff", type=Path, required=True
    )
    validate_consensus_release.add_argument(
        "--study-root", type=Path, required=True
    )
    validate_consensus_release.add_argument("--output", type=Path)

    validate_consensus_return = subparsers.add_parser(
        "validate-consensus-return"
    )
    validate_consensus_return.add_argument(
        "--return-manifest", type=Path, required=True
    )
    validate_consensus_return.add_argument(
        "--consensus-assignment-release", type=Path, required=True
    )
    validate_consensus_return.add_argument(
        "--decision-return", type=Path, required=True
    )
    validate_consensus_return.add_argument(
        "--decision-return-validation", type=Path, required=True
    )
    validate_consensus_return.add_argument(
        "--decision-assignment-release", type=Path, required=True
    )
    validate_consensus_return.add_argument(
        "--initial-return", type=Path, required=True
    )
    validate_consensus_return.add_argument(
        "--initial-return-validation", type=Path, required=True
    )
    validate_consensus_return.add_argument(
        "--initial-assignment-release", type=Path, required=True
    )
    validate_consensus_return.add_argument(
        "--handoff", type=Path, required=True
    )
    validate_consensus_return.add_argument(
        "--study-root", type=Path, required=True
    )
    validate_consensus_return.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        payload = prepare_assignment_package(
            handoff_path=args.handoff,
            study_root=args.study_root,
            output_dir=args.output_dir,
        )
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "release_id": payload["release_id"],
                    "assignment_count": payload["assignment_count"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "validate-release":
        payload = validate_assignment_release(
            _load_json(args.artifact),
            release_path=args.artifact,
            handoff_path=args.handoff,
            study_root=args.study_root,
        )
        if args.output is not None:
            _write_json(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "passed" else 1
    if args.command == "validate-returns":
        payload = validate_return_manifest(
            _load_json(args.return_manifest),
            manifest_path=args.return_manifest,
            release_path=args.assignment_release,
            handoff_path=args.handoff,
            study_root=args.study_root,
        )
        _write_json(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "prepare-decisions":
        payload = prepare_decision_assignment_package(
            return_manifest_path=args.initial_return,
            return_validation_path=args.initial_return_validation,
            initial_release_path=args.initial_assignment_release,
            handoff_path=args.handoff,
            study_root=args.study_root,
            output_dir=args.output_dir,
        )
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "release_id": payload["release_id"],
                    "assignment_count": payload["assignment_count"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "validate-decision-release":
        payload = validate_decision_assignment_release(
            _load_json(args.artifact),
            release_path=args.artifact,
            return_manifest_path=args.initial_return,
            return_validation_path=args.initial_return_validation,
            initial_release_path=args.initial_assignment_release,
            handoff_path=args.handoff,
            study_root=args.study_root,
        )
        if args.output is not None:
            _write_json(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "passed" else 1
    if args.command == "validate-decision-returns":
        payload = validate_decision_return_manifest(
            _load_json(args.return_manifest),
            manifest_path=args.return_manifest,
            release_path=args.decision_assignment_release,
            initial_return_path=args.initial_return,
            initial_return_validation_path=args.initial_return_validation,
            initial_release_path=args.initial_assignment_release,
            handoff_path=args.handoff,
            study_root=args.study_root,
        )
        _write_json(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "prepare-consensus":
        payload = prepare_consensus_assignment_package(
            decision_return_path=args.decision_return,
            decision_return_validation_path=args.decision_return_validation,
            decision_release_path=args.decision_assignment_release,
            initial_return_path=args.initial_return,
            initial_return_validation_path=args.initial_return_validation,
            initial_release_path=args.initial_assignment_release,
            handoff_path=args.handoff,
            study_root=args.study_root,
            output_dir=args.output_dir,
        )
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "release_id": payload["release_id"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "validate-consensus-release":
        payload = validate_consensus_assignment_release(
            _load_json(args.artifact),
            release_path=args.artifact,
            decision_return_path=args.decision_return,
            decision_return_validation_path=args.decision_return_validation,
            decision_release_path=args.decision_assignment_release,
            initial_return_path=args.initial_return,
            initial_return_validation_path=args.initial_return_validation,
            initial_release_path=args.initial_assignment_release,
            handoff_path=args.handoff,
            study_root=args.study_root,
        )
        if args.output is not None:
            _write_json(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "passed" else 1
    payload = validate_consensus_return_manifest(
        _load_json(args.return_manifest),
        manifest_path=args.return_manifest,
        release_path=args.consensus_assignment_release,
        decision_return_path=args.decision_return,
        decision_return_validation_path=args.decision_return_validation,
        decision_release_path=args.decision_assignment_release,
        initial_return_path=args.initial_return,
        initial_return_validation_path=args.initial_return_validation,
        initial_release_path=args.initial_assignment_release,
        handoff_path=args.handoff,
        study_root=args.study_root,
    )
    _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
