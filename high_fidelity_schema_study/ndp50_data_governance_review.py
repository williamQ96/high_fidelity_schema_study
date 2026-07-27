from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .ndp50_data_governance import validate_audit_file


REVIEW_SCHEMA_VERSION = "ndp50-data-governance-review/v1"
WORKFLOW_SCHEMA_VERSION = "ndp50-data-governance-review-workflow/v1"
APPROVAL_SCHEMA_VERSION = "ndp50-data-governance-approval/v1"
VALIDATION_SCHEMA_VERSION = "ndp50-data-governance-review-validation/v1"
APPROVAL_VALIDATION_SCHEMA_VERSION = (
    "ndp50-data-governance-approval-validation/v1"
)
STEWARDSHIP_ROLES = {
    "institutional_data_steward",
    "research_compliance_reviewer",
}
ACCOUNTABLE_ROLES = {"principal_investigator", "institutional_data_controller"}
TERMS_STATUSES = {
    "verified_permits_planned_use",
    "verified_requires_restrictions",
}
ATTRIBUTION_STATUSES = {"required", "not_required"}
MODEL_PROCESSING_MODES = {
    "local_only",
    "external_provider_approved_all_in_scope",
}
PLACEHOLDER_TOKENS = ("replace-with", "placeholder", "todo", "tbd")


class NDPDataGovernanceReviewError(ValueError):
    pass


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _is_https(value: Any) -> bool:
    return str(value or "").strip().startswith("https://")


def _valid_identifier(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and not any(
        token in text.casefold() for token in PLACEHOLDER_TOKENS
    )


def _valid_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_date(value: Any) -> bool:
    try:
        date.fromisoformat(str(value or ""))
    except ValueError:
        return False
    return True


def _audit_payload(audit_path: Path, study_root: Path) -> Dict[str, Any]:
    audit = _load_json(audit_path)
    validation = validate_audit_file(audit, study_root=study_root)
    if validation.get("status") != "passed":
        raise NDPDataGovernanceReviewError(
            "data-governance audit is not reproducible"
        )
    if audit.get("status") != (
        "provenance_integrity_passed_governance_review_required"
    ):
        raise NDPDataGovernanceReviewError(
            "unexpected data-governance audit status"
        )
    if (
        audit.get("scope", {}).get("test_dataset_detail_count") != 0
        or audit.get("scope", {}).get("test_dataset_identities_included")
        is not False
    ):
        raise NDPDataGovernanceReviewError(
            "governance review must not contain test details or identities"
        )
    return audit


def _template_from_audit(
    audit: Mapping[str, Any],
    *,
    audit_file: str,
    audit_sha256: str,
) -> Dict[str, Any]:
    dataset_reviews = []
    for item in audit.get("datasets") or []:
        dataset_reviews.append(
            {
                "dataset_id": item["dataset_id"],
                "split": item["split"],
                "audit_record_sha256": _sha256_payload(item),
                "observed_license": item["license"],
                "authoritative_license_source_url": None,
                "resolved_license_identifier": None,
                "license_terms_status": None,
                "attribution_status": None,
                "required_attribution_text": None,
                "local_analysis_allowed": None,
                "external_model_transfer_allowed": None,
                "raw_payload_redistribution_allowed": None,
                "metadata_redistribution_allowed": None,
                "derived_schema_redistribution_allowed": None,
                "restrictions_summary": None,
                "rationale": None,
                "evidence_refs": [],
            }
        )
    dataset_reviews.sort(key=lambda item: (item["split"], item["dataset_id"]))
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "status": "neutral_pending_human_review",
        "audit": {"file": audit_file, "sha256": audit_sha256},
        "reviewer_signoff": {
            "reviewer_id": "replace-with-pseudonymous-reviewer-id",
            "reviewer_role": "replace-with-stewardship-role",
            "institution": None,
            "qualification_summary": None,
            "institutional_authority_scope": None,
            "institutional_authority_attested": None,
            "conflict_of_interest_declared": None,
            "developer_participation": False,
            "signed_on": None,
        },
        "accountable_approval": {
            "approver_id": "replace-with-pseudonymous-approver-id",
            "approver_role": "replace-with-accountable-role",
            "institution": None,
            "qualification_summary": None,
            "institutional_authority_scope": None,
            "institutional_authority_attested": None,
            "conflict_of_interest_declared": None,
            "developer_participation": None,
            "signed_on": None,
        },
        "study_policy": {
            "model_processing_mode": None,
            "external_provider_name": None,
            "external_provider_terms_url": None,
            "provider_retention_policy": None,
            "provider_training_use_policy": None,
            "redaction_and_data_minimization_policy": None,
            "artifact_release_policy": None,
            "policy_rationale": None,
        },
        "dataset_reviews": dataset_reviews,
        "completion_attestation": None,
        "legal_advice_claimed": False,
    }


def build_review_template(
    *,
    audit_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    audit = _audit_payload(audit_path, study_root)
    return _template_from_audit(
        audit,
        audit_file=audit_path.name,
        audit_sha256=_sha256_file(audit_path),
    )


def build_workflow_spec(
    *,
    audit_path: Path,
    template_path: Path,
) -> Dict[str, Any]:
    implementation = Path(__file__).resolve()
    return {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "status": "ready_for_independent_governance_review_and_approval",
        "human_decisions_present": False,
        "legal_advice_claimed": False,
        "audit": {
            "file": audit_path.name,
            "sha256": _sha256_file(audit_path),
        },
        "neutral_template": {
            "file": template_path.name,
            "sha256": _sha256_file(template_path),
        },
        "required_distinct_signatories": 2,
        "required_role_coverage": [
            "one_institutional_data_steward_or_research_compliance_reviewer",
            "one_principal_investigator_or_institutional_data_controller",
        ],
        "sequence": [
            "qualified_stewardship_review",
            "accountable_approval",
            "validator_generated_governance_approval",
            "rebuild_readiness_and_handoff",
        ],
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            "ndp50_data_governance.py": _sha256_file(
                implementation.with_name("ndp50_data_governance.py")
            )
        },
    }


def validate_review(
    review: Mapping[str, Any],
    *,
    template: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> Dict[str, Any]:
    errors: list[Dict[str, str]] = []

    def error(code: str, detail: str) -> None:
        errors.append({"code": code, "detail": detail})

    if review.get("schema_version") != REVIEW_SCHEMA_VERSION:
        error("review_schema_invalid", "unexpected governance-review schema")
    if review.get("status") != "completed_pending_validator_approval":
        error(
            "review_status_invalid",
            "completed review status must be completed_pending_validator_approval",
        )
    if review.get("audit") != template.get("audit"):
        error("audit_binding_mismatch", "review changed the audit binding")
    if review.get("legal_advice_claimed") is not False:
        error(
            "legal_advice_claim_invalid",
            "workflow records governance approval, not legal advice",
        )

    reviewer = review.get("reviewer_signoff")
    approver = review.get("accountable_approval")
    if not isinstance(reviewer, dict) or not isinstance(approver, dict):
        error("signoff_missing", "both signoff objects are required")
    else:
        reviewer_id = reviewer.get("reviewer_id")
        approver_id = approver.get("approver_id")
        if not _valid_identifier(reviewer_id):
            error("reviewer_id_invalid", "reviewer_id is missing or a placeholder")
        if not _valid_identifier(approver_id):
            error("approver_id_invalid", "approver_id is missing or a placeholder")
        if reviewer_id == approver_id:
            error(
                "signatories_not_distinct",
                "reviewer and accountable approver must be distinct",
            )
        if reviewer.get("reviewer_role") not in STEWARDSHIP_ROLES:
            error("reviewer_role_invalid", "reviewer lacks a stewardship role")
        if approver.get("approver_role") not in ACCOUNTABLE_ROLES:
            error("approver_role_invalid", "approver lacks an accountable role")
        for label, payload in (("reviewer", reviewer), ("approver", approver)):
            for key in (
                "institution",
                "qualification_summary",
                "institutional_authority_scope",
            ):
                if not _valid_text(payload.get(key)):
                    error(
                        f"{label}_{key}_missing",
                        f"{label}.{key} must be non-empty",
                    )
            if payload.get("institutional_authority_attested") is not True:
                error(
                    f"{label}_authority_not_attested",
                    f"{label} must attest institutional authority",
                )
            if payload.get("conflict_of_interest_declared") is not False:
                error(
                    f"{label}_conflict_not_cleared",
                    f"{label} must declare no unresolved conflict",
                )
            if not _valid_date(payload.get("signed_on")):
                error(
                    f"{label}_signature_date_invalid",
                    f"{label}.signed_on must be an ISO date",
                )
        if reviewer.get("developer_participation") is not False:
            error(
                "stewardship_reviewer_not_independent",
                "stewardship reviewer must be a non-developer",
            )
        if not isinstance(approver.get("developer_participation"), bool):
            error(
                "approver_developer_participation_missing",
                "approver developer participation must be declared",
            )

    expected_reviews = template.get("dataset_reviews") or []
    actual_reviews = review.get("dataset_reviews")
    if not isinstance(actual_reviews, list):
        error("dataset_reviews_missing", "dataset_reviews must be a list")
        actual_reviews = []
    expected_by_id = {
        str(item["dataset_id"]): item for item in expected_reviews
    }
    actual_by_id = {
        str(item.get("dataset_id") or ""): item
        for item in actual_reviews
        if isinstance(item, dict)
    }
    if (
        len(actual_by_id) != len(actual_reviews)
        or set(actual_by_id) != set(expected_by_id)
    ):
        error(
            "dataset_identity_mismatch",
            "review datasets must exactly match the neutral template",
        )
    for dataset_id, expected in expected_by_id.items():
        item = actual_by_id.get(dataset_id)
        if item is None:
            continue
        for key in (
            "dataset_id",
            "split",
            "audit_record_sha256",
            "observed_license",
        ):
            if item.get(key) != expected.get(key):
                error(
                    "dataset_source_slot_changed",
                    f"{dataset_id} changed immutable slot {key}",
                )
        if not _is_https(item.get("authoritative_license_source_url")):
            error(
                "authoritative_license_source_missing",
                f"{dataset_id} requires an HTTPS authoritative source",
            )
        if not _valid_text(item.get("resolved_license_identifier")):
            error(
                "resolved_license_identifier_missing",
                f"{dataset_id} requires a resolved license identifier",
            )
        if item.get("license_terms_status") not in TERMS_STATUSES:
            error(
                "license_terms_unresolved",
                f"{dataset_id} license terms are not resolved",
            )
        attribution = item.get("attribution_status")
        if attribution not in ATTRIBUTION_STATUSES:
            error(
                "attribution_status_unresolved",
                f"{dataset_id} attribution status is unresolved",
            )
        if attribution == "required" and not _valid_text(
            item.get("required_attribution_text")
        ):
            error(
                "required_attribution_missing",
                f"{dataset_id} requires attribution text",
            )
        if attribution == "not_required" and item.get(
            "required_attribution_text"
        ) not in (None, ""):
            error(
                "unexpected_attribution_text",
                f"{dataset_id} has text despite not-required status",
            )
        if item.get("local_analysis_allowed") is not True:
            error(
                "local_analysis_not_authorized",
                f"{dataset_id} is not authorized for planned local analysis",
            )
        for key in (
            "external_model_transfer_allowed",
            "raw_payload_redistribution_allowed",
            "metadata_redistribution_allowed",
            "derived_schema_redistribution_allowed",
        ):
            if not isinstance(item.get(key), bool):
                error(
                    "policy_decision_missing",
                    f"{dataset_id}.{key} must be explicitly true or false",
                )
        for key in ("restrictions_summary", "rationale"):
            if not _valid_text(item.get(key)):
                error(
                    "dataset_rationale_missing",
                    f"{dataset_id}.{key} must be non-empty",
                )
        evidence_refs = item.get("evidence_refs")
        if (
            not isinstance(evidence_refs, list)
            or not evidence_refs
            or not all(_is_https(value) for value in evidence_refs)
        ):
            error(
                "dataset_evidence_invalid",
                f"{dataset_id} requires at least one HTTPS evidence reference",
            )

    policy = review.get("study_policy")
    if not isinstance(policy, dict):
        error("study_policy_missing", "study_policy must be an object")
        policy = {}
    mode = policy.get("model_processing_mode")
    if mode not in MODEL_PROCESSING_MODES:
        error("model_processing_mode_invalid", "processing mode is not frozen")
    if mode == "local_only":
        if policy.get("external_provider_name") not in (None, ""):
            error(
                "local_mode_provider_present",
                "local-only mode cannot name an external provider",
            )
        if policy.get("external_provider_terms_url") not in (None, ""):
            error(
                "local_mode_provider_terms_present",
                "local-only mode cannot bind external provider terms",
            )
        if policy.get("provider_retention_policy") != (
            "not_applicable_local_only"
        ):
            error(
                "local_mode_retention_invalid",
                "local-only retention policy must be not_applicable_local_only",
            )
        if policy.get("provider_training_use_policy") != "not_applicable":
            error(
                "local_mode_training_policy_invalid",
                "local-only training-use policy must be not_applicable",
            )
        if any(
            item.get("external_model_transfer_allowed") is not False
            for item in actual_reviews
            if isinstance(item, dict)
        ):
            error(
                "local_mode_external_transfer_present",
                "local-only mode requires every external-transfer decision false",
            )
    elif mode == "external_provider_approved_all_in_scope":
        if not _valid_text(policy.get("external_provider_name")):
            error(
                "external_provider_missing",
                "approved external mode requires a provider name",
            )
        if not _is_https(policy.get("external_provider_terms_url")):
            error(
                "external_provider_terms_missing",
                "approved external mode requires an HTTPS terms reference",
            )
        if not _valid_text(policy.get("provider_retention_policy")):
            error(
                "external_retention_policy_missing",
                "approved external mode requires a retention policy",
            )
        if policy.get("provider_training_use_policy") not in {
            "prohibited_by_provider_terms",
            "allowed_by_verified_dataset_and_provider_terms",
        }:
            error(
                "external_training_policy_invalid",
                "external provider training-use policy is unresolved",
            )
        if any(
            item.get("external_model_transfer_allowed") is not True
            for item in actual_reviews
            if isinstance(item, dict)
        ):
            error(
                "external_transfer_not_fully_approved",
                "external mode requires approval for every in-scope dataset",
            )
    for key in (
        "redaction_and_data_minimization_policy",
        "artifact_release_policy",
        "policy_rationale",
    ):
        if not _valid_text(policy.get(key)):
            error(
                f"{key}_missing",
                f"study_policy.{key} must be non-empty",
            )
    if review.get("completion_attestation") is not True:
        error(
            "completion_not_attested",
            "review completion must be explicitly attested",
        )

    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "status": "passed" if not errors else "blocked",
        "dataset_count": len(expected_by_id),
        "errors": errors,
    }


def build_approval(
    *,
    review: Mapping[str, Any],
    audit_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    audit = _audit_payload(audit_path, study_root)
    template = _template_from_audit(
        audit,
        audit_file=audit_path.name,
        audit_sha256=_sha256_file(audit_path),
    )
    validation = validate_review(review, template=template, audit=audit)
    if validation["status"] != "passed":
        raise NDPDataGovernanceReviewError(
            "governance review is incomplete: "
            + json.dumps(validation["errors"], sort_keys=True)
        )
    implementation = Path(__file__).resolve()
    dataset_reviews = review["dataset_reviews"]
    return {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "status": "approved_policy_frozen",
        "legal_advice_claimed": False,
        "audit": template["audit"],
        "neutral_template_canonical_sha256": _sha256_payload(template),
        "review_content_sha256": _sha256_payload(review),
        "review": review,
        "derived_gates": {
            "human_license_and_attribution_review_complete": True,
            "external_model_data_transfer_policy_frozen": True,
            "artifact_redistribution_policy_frozen": True,
            "data_governance_policy_frozen": True,
        },
        "counts": {
            "dataset_count": len(dataset_reviews),
            "external_transfer_allowed": sum(
                item["external_model_transfer_allowed"]
                for item in dataset_reviews
            ),
            "raw_payload_redistribution_allowed": sum(
                item["raw_payload_redistribution_allowed"]
                for item in dataset_reviews
            ),
            "metadata_redistribution_allowed": sum(
                item["metadata_redistribution_allowed"]
                for item in dataset_reviews
            ),
            "derived_schema_redistribution_allowed": sum(
                item["derived_schema_redistribution_allowed"]
                for item in dataset_reviews
            ),
        },
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            "ndp50_data_governance.py": _sha256_file(
                implementation.with_name("ndp50_data_governance.py")
            )
        },
    }


def verify_approval(
    approval: Mapping[str, Any],
    *,
    audit_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    review = approval.get("review")
    if not isinstance(review, dict):
        return {
            "schema_version": APPROVAL_VALIDATION_SCHEMA_VERSION,
            "status": "failed",
            "differing_top_level_keys": ["review"],
        }
    try:
        expected = build_approval(
            review=review,
            audit_path=audit_path,
            study_root=study_root,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": APPROVAL_VALIDATION_SCHEMA_VERSION,
            "status": "failed",
            "differing_top_level_keys": ["review"],
            "detail": str(exc),
        }
    differing = sorted(
        key
        for key in set(approval) | set(expected)
        if approval.get(key) != expected.get(key)
    )
    return {
        "schema_version": APPROVAL_VALIDATION_SCHEMA_VERSION,
        "status": "passed" if not differing else "failed",
        "differing_top_level_keys": differing,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare and validate NDP-50 data-governance approval."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--audit", type=Path, required=True)
    prepare.add_argument("--study-root", type=Path, required=True)
    prepare.add_argument("--template-output", type=Path, required=True)
    prepare.add_argument("--workflow-output", type=Path, required=True)
    validate = subparsers.add_parser("validate-review")
    validate.add_argument("--review", type=Path, required=True)
    validate.add_argument("--audit", type=Path, required=True)
    validate.add_argument("--study-root", type=Path, required=True)
    validate.add_argument("--output", type=Path, required=True)
    approve = subparsers.add_parser("approve")
    approve.add_argument("--review", type=Path, required=True)
    approve.add_argument("--audit", type=Path, required=True)
    approve.add_argument("--study-root", type=Path, required=True)
    approve.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify-approved")
    verify.add_argument("--approved", type=Path, required=True)
    verify.add_argument("--audit", type=Path, required=True)
    verify.add_argument("--study-root", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        template = build_review_template(
            audit_path=args.audit, study_root=args.study_root
        )
        _write_json(args.template_output, template)
        workflow = build_workflow_spec(
            audit_path=args.audit,
            template_path=args.template_output,
        )
        _write_json(args.workflow_output, workflow)
        print(
            json.dumps(
                {
                    "status": workflow["status"],
                    "dataset_count": len(template["dataset_reviews"]),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    audit = _audit_payload(args.audit, args.study_root)
    if args.command == "validate-review":
        template = _template_from_audit(
            audit,
            audit_file=args.audit.name,
            audit_sha256=_sha256_file(args.audit),
        )
        report = validate_review(
            _load_json(args.review),
            template=template,
            audit=audit,
        )
        _write_json(args.output, report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "passed" else 1
    if args.command == "approve":
        approval = build_approval(
            review=_load_json(args.review),
            audit_path=args.audit,
            study_root=args.study_root,
        )
        _write_json(args.output, approval)
        print(json.dumps(approval["derived_gates"], indent=2, sort_keys=True))
        return 0
    report = verify_approval(
        _load_json(args.approved),
        audit_path=args.audit,
        study_root=args.study_root,
    )
    _write_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
