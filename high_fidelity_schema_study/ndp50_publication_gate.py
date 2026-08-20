from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Mapping
from urllib.parse import urlparse


WORKFLOW_SCHEMA_VERSION = "ndp50-publication-gate-workflow/v1"
FEEDBACK_SIGNOFF_SCHEMA_VERSION = "ndp50-feedback-response-signoff/v2"
PREREGISTRATION_RECEIPT_SCHEMA_VERSION = (
    "ndp50-external-preregistration-receipt/v1"
)
VALIDATION_SCHEMA_VERSION = "ndp50-publication-gate-validation/v1"
PUBLIC_PACKAGE_SCHEMA_VERSION = "ndp50-public-preregistration-package/v1"
PUBLIC_PACKAGE_STATUS = "draft_structurally_valid_not_registered"
ALLOWED_REGISTRIES = {"osf", "zenodo"}
EXPECTED_FEEDBACK_ITEMS = [f"F{index:02d}" for index in range(1, 17)]
EXPECTED_SENSITIVITY_DECISIONS = {
    "evidence_free_single_call": "exclude_from_confirmatory_matrix",
    "heuristic_comparator": "development_validation_diagnostic_only",
    "learned_cta_cpa": "separately_registered_extension_only",
    "second_model_family": "defer_unless_complete_paired_execution_is_frozen",
}
FEEDBACK_REVIEW_MATERIAL_RELATIVE_PATHS = (
    "docs/literature/citation_matrix.md",
    "docs/literature/semantic_architecture_literature_review_2026-07-27.md",
    "docs/ndp50_annotation_and_independence_plan_v1.md",
    "docs/ndp50_feedback_implementation_audit_v1.md",
    "docs/ndp50_human_external_gate_ledger_v1.md",
    "docs/ndp50_methodological_risk_register_v1.md",
    "docs/ndp50_scope_provenance_v1.md",
    "docs/ndp50_statistical_analysis_plan_v1.md",
    "docs/ndp50_swathi_feedback_signoff_guide_v1.md",
    "docs/preregistration/ndp50_osf_zenodo_preregistration_draft_v1.md",
    "docs/semantic_architecture_claim_ledger_v1.md",
    "paper/references.bib",
    "paper/results_macros.tex",
    "paper/semantic_architecture_study_en.tex",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class NDPPublicationGateError(ValueError):
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


def _binding(path: Path, study_root: Path) -> Dict[str, str]:
    try:
        relative = path.resolve().relative_to(study_root.resolve()).as_posix()
    except ValueError as exc:
        raise NDPPublicationGateError(
            "bound artifacts must be inside the study root"
        ) from exc
    if not path.is_file():
        raise NDPPublicationGateError(
            f"bound artifact is missing: {relative}"
        )
    return {"file": relative, "sha256": _sha256_file(path)}


def feedback_review_material_paths(study_root: Path) -> tuple[Path, ...]:
    return tuple(
        study_root / Path(relative)
        for relative in FEEDBACK_REVIEW_MATERIAL_RELATIVE_PATHS
    )


def _review_material_bindings(
    paths: Iterable[Path],
    *,
    study_root: Path,
) -> list[Dict[str, str]]:
    bindings = [_binding(path, study_root) for path in paths]
    files = [item["file"] for item in bindings]
    if len(files) != len(set(files)):
        raise NDPPublicationGateError(
            "feedback review materials must be unique"
        )
    return sorted(bindings, key=lambda item: item["file"])


def _bindings_digest(bindings: Iterable[Mapping[str, str]]) -> str:
    return hashlib.sha256(
        json.dumps(
            list(bindings),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise NDPPublicationGateError(
            f"{label} must be an ISO-8601 UTC timestamp ending in Z"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise NDPPublicationGateError(
            f"{label} must be a valid ISO-8601 UTC timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(
        parsed
    ):
        raise NDPPublicationGateError(f"{label} must be UTC")
    return parsed


def _require_nonplaceholder(value: Any, label: str) -> str:
    text = str(value or "").strip()
    folded = text.casefold()
    if (
        not text
        or "replace-with" in folded
        or "unresolved" in folded
        or text.startswith("<")
    ):
        raise NDPPublicationGateError(
            f"{label} must be completed with a non-placeholder value"
        )
    return text


def _require_https(value: Any, label: str) -> str:
    url = _require_nonplaceholder(value, label)
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise NDPPublicationGateError(f"{label} must be an HTTPS URL")
    return url


def _require_sha256(value: Any, label: str) -> str:
    digest = str(value or "").strip().lower()
    if SHA256_RE.fullmatch(digest) is None:
        raise NDPPublicationGateError(
            f"{label} must be a lowercase SHA-256 digest"
        )
    return digest


def build_workflow_spec(
    *,
    public_package_manifest_path: Path,
    feedback_matrix_path: Path,
    amendment_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    manifest = _load_json(public_package_manifest_path)
    if (
        manifest.get("schema_version") != PUBLIC_PACKAGE_SCHEMA_VERSION
        or manifest.get("status") != PUBLIC_PACKAGE_STATUS
        or manifest.get("authorization", {}).get(
            "external_registration_claimed"
        )
        is not False
        or manifest.get("private_sealing_control", {}).get(
            "sealed_identity_match_count"
        )
        != 0
    ):
        raise NDPPublicationGateError(
            "public package manifest is not a safe replayed draft"
        )
    implementation = Path(__file__).resolve()
    return {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "status": (
            "implementation_ready_waiting_on_collaborator_signoff_and_"
            "external_registration"
        ),
        "human_decisions_present": False,
        "test_outcomes_observed": False,
        "test_release_authorized": False,
        "public_package_manifest": _binding(
            public_package_manifest_path, study_root
        ),
        "public_package_content_digest_sha256": (
            manifest["public_scope"]["content_digest_sha256"]
        ),
        "feedback_response_matrix": _binding(
            feedback_matrix_path, study_root
        ),
        "feedback_improvement_amendment": _binding(
            amendment_path, study_root
        ),
        "required_artifact_schemas": {
            "feedback_response_signoff": FEEDBACK_SIGNOFF_SCHEMA_VERSION,
            "external_preregistration_receipt": (
                PREREGISTRATION_RECEIPT_SCHEMA_VERSION
            ),
        },
        "required_feedback_items": EXPECTED_FEEDBACK_ITEMS,
        "frozen_optional_sensitivity_decisions": (
            EXPECTED_SENSITIVITY_DECISIONS
        ),
        "release_invariants": {
            "collaborator_review_is_not_independent_validation": True,
            "external_receipt_must_bind_exact_public_manifest": True,
            "external_receipt_must_predate_test_release": True,
            "independent_registration_verifier_must_be_non_developer": True,
            "independent_registration_verifier_must_not_be_project_collaborator": (
                True
            ),
            "human_indirect_disclosure_review_required": True,
            "local_manifest_is_not_external_registration": True,
            "test_release_requires_both_validated_artifacts": True,
        },
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            "ndp50_preregistration_package.py": _sha256_file(
                implementation.with_name("ndp50_preregistration_package.py")
            )
        },
    }


def build_feedback_signoff_template(
    *,
    feedback_matrix_path: Path,
    amendment_path: Path,
    study_root: Path,
    review_material_paths: Iterable[Path] | None = None,
) -> Dict[str, Any]:
    if review_material_paths is None:
        review_material_paths = feedback_review_material_paths(study_root)
    review_materials = _review_material_bindings(
        review_material_paths,
        study_root=study_root,
    )
    return {
        "schema_version": FEEDBACK_SIGNOFF_SCHEMA_VERSION,
        "status": "pending_human_collaborator_review",
        "human_decisions_present": False,
        "test_outcomes_observed": False,
        "independence_claimed": False,
        "feedback_response_matrix": _binding(
            feedback_matrix_path, study_root
        ),
        "feedback_improvement_amendment": _binding(
            amendment_path, study_root
        ),
        "review_materials": review_materials,
        "review_materials_digest_sha256": _bindings_digest(
            review_materials
        ),
        "reviewed_feedback_items": [],
        "optional_sensitivity_decisions": (
            EXPECTED_SENSITIVITY_DECISIONS
        ),
        "collaborator": {
            "reviewer_id": None,
            "reviewer_role": "postdoctoral_research_collaborator",
            "qualification_summary": None,
            "project_collaborator": True,
            "developer_participation": False,
            "independent_reviewer": False,
            "conflict_of_interest_disclosure": None,
            "signed_at": None,
        },
        "signed_at": None,
        "attestations": {
            "all_feedback_items_reviewed": False,
            "all_bound_review_materials_reviewed": False,
            "claim_boundaries_accepted": False,
            "inactive_sensitivities_not_presented_as_executed": False,
            "collaborator_review_not_represented_as_independent": False,
            "no_test_outcomes_seen": False,
            "test_release_not_authorized_by_this_signoff": False,
        },
    }


def validate_feedback_signoff(
    payload: Mapping[str, Any],
    *,
    feedback_matrix_path: Path,
    amendment_path: Path,
    study_root: Path,
    review_material_paths: Iterable[Path] | None = None,
) -> Dict[str, Any]:
    if (
        payload.get("schema_version") != FEEDBACK_SIGNOFF_SCHEMA_VERSION
        or payload.get("status") != "approved_with_recorded_boundaries"
        or payload.get("human_decisions_present") is not True
        or payload.get("test_outcomes_observed") is not False
        or payload.get("independence_claimed") is not False
    ):
        raise NDPPublicationGateError(
            "feedback response sign-off state is incomplete or incompatible"
        )
    for key, expected in (
        (
            "feedback_response_matrix",
            _binding(feedback_matrix_path, study_root),
        ),
        (
            "feedback_improvement_amendment",
            _binding(amendment_path, study_root),
        ),
    ):
        if payload.get(key) != expected:
            raise NDPPublicationGateError(
                f"feedback sign-off {key} binding changed"
            )
    if review_material_paths is None:
        review_material_paths = feedback_review_material_paths(study_root)
    expected_review_materials = _review_material_bindings(
        review_material_paths,
        study_root=study_root,
    )
    if payload.get("review_materials") != expected_review_materials:
        raise NDPPublicationGateError(
            "feedback sign-off review-material bindings changed"
        )
    expected_review_digest = _bindings_digest(expected_review_materials)
    if (
        payload.get("review_materials_digest_sha256")
        != expected_review_digest
    ):
        raise NDPPublicationGateError(
            "feedback sign-off review-material digest changed"
        )
    if payload.get("reviewed_feedback_items") != EXPECTED_FEEDBACK_ITEMS:
        raise NDPPublicationGateError(
            "feedback sign-off must review F01 through F16 exactly once"
        )
    if (
        payload.get("optional_sensitivity_decisions")
        != EXPECTED_SENSITIVITY_DECISIONS
    ):
        raise NDPPublicationGateError(
            "feedback sign-off optional sensitivity decisions changed"
        )
    collaborator = payload.get("collaborator")
    if not isinstance(collaborator, dict):
        raise NDPPublicationGateError(
            "feedback sign-off collaborator must be an object"
        )
    collaborator_id = _require_nonplaceholder(
        collaborator.get("reviewer_id"), "collaborator reviewer_id"
    )
    _require_nonplaceholder(
        collaborator.get("qualification_summary"),
        "collaborator qualification_summary",
    )
    _require_nonplaceholder(
        collaborator.get("conflict_of_interest_disclosure"),
        "collaborator conflict_of_interest_disclosure",
    )
    if (
        collaborator.get("reviewer_role")
        != "postdoctoral_research_collaborator"
        or collaborator.get("project_collaborator") is not True
        or collaborator.get("developer_participation") is not False
        or collaborator.get("independent_reviewer") is not False
    ):
        raise NDPPublicationGateError(
            "feedback collaborator role or independence disclosure is invalid"
        )
    signed_at = _parse_utc(payload.get("signed_at"), "signed_at")
    if _parse_utc(
        collaborator.get("signed_at"), "collaborator signed_at"
    ) != signed_at:
        raise NDPPublicationGateError(
            "top-level and collaborator signed_at values must match"
        )
    attestations = payload.get("attestations")
    required_attestations = {
        "all_feedback_items_reviewed": True,
        "all_bound_review_materials_reviewed": True,
        "claim_boundaries_accepted": True,
        "inactive_sensitivities_not_presented_as_executed": True,
        "collaborator_review_not_represented_as_independent": True,
        "no_test_outcomes_seen": True,
        "test_release_not_authorized_by_this_signoff": True,
    }
    if attestations != required_attestations:
        raise NDPPublicationGateError(
            "feedback sign-off attestations are incomplete"
        )
    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "artifact_type": "feedback_response_signoff",
        "status": "passed",
        "collaborator_id": collaborator_id,
        "signed_at": payload["signed_at"],
        "review_material_count": len(expected_review_materials),
        "review_materials_digest_sha256": expected_review_digest,
        "independent_validation_claimed": False,
        "test_release_authorized": False,
    }


def validate_external_preregistration_receipt(
    payload: Mapping[str, Any],
    *,
    public_package_manifest_path: Path,
    feedback_signoff_path: Path,
    feedback_matrix_path: Path,
    amendment_path: Path,
    study_root: Path,
    review_material_paths: Iterable[Path] | None = None,
) -> Dict[str, Any]:
    feedback_payload = _load_json(feedback_signoff_path)
    validate_feedback_signoff(
        feedback_payload,
        feedback_matrix_path=feedback_matrix_path,
        amendment_path=amendment_path,
        study_root=study_root,
        review_material_paths=review_material_paths,
    )
    manifest = _load_json(public_package_manifest_path)
    if (
        manifest.get("schema_version") != PUBLIC_PACKAGE_SCHEMA_VERSION
        or manifest.get("status") != PUBLIC_PACKAGE_STATUS
        or manifest.get("authorization", {}).get(
            "external_registration_claimed"
        )
        is not False
        or manifest.get("private_sealing_control", {}).get(
            "sealed_identity_match_count"
        )
        != 0
    ):
        raise NDPPublicationGateError(
            "external receipt must bind a safe replayed public package draft"
        )
    if (
        payload.get("schema_version")
        != PREREGISTRATION_RECEIPT_SCHEMA_VERSION
        or payload.get("status") != "verified_external_registration"
        or payload.get("human_decisions_present") is not True
        or payload.get("test_outcomes_observed") is not False
        or payload.get("test_release_authorized") is not False
    ):
        raise NDPPublicationGateError(
            "external preregistration receipt state is incomplete"
        )
    expected_bindings = {
        "public_package_manifest": _binding(
            public_package_manifest_path, study_root
        ),
        "feedback_response_signoff": _binding(
            feedback_signoff_path, study_root
        ),
    }
    for key, expected in expected_bindings.items():
        if payload.get(key) != expected:
            raise NDPPublicationGateError(
                f"external preregistration receipt {key} binding changed"
            )
    if (
        payload.get("public_package_content_digest_sha256")
        != manifest["public_scope"]["content_digest_sha256"]
    ):
        raise NDPPublicationGateError(
            "external receipt public package content digest changed"
        )
    registration = payload.get("registration")
    if not isinstance(registration, dict):
        raise NDPPublicationGateError("registration must be an object")
    registry = str(registration.get("registry") or "").casefold()
    if registry not in ALLOWED_REGISTRIES:
        raise NDPPublicationGateError(
            "registration registry must be OSF or Zenodo"
        )
    persistent_identifier = _require_nonplaceholder(
        registration.get("persistent_identifier"),
        "registration persistent_identifier",
    )
    _require_https(registration.get("public_record_url"), "public_record_url")
    registered_at = _parse_utc(
        registration.get("registered_at"), "registered_at"
    )
    if (
        registration.get("immutable_version") is not True
        or registration.get("publicly_accessible") is not True
    ):
        raise NDPPublicationGateError(
            "registration must be immutable and publicly accessible"
        )
    _require_sha256(
        payload.get("external_receipt_export_sha256"),
        "external_receipt_export_sha256",
    )
    verifier = payload.get("independent_verification")
    if not isinstance(verifier, dict):
        raise NDPPublicationGateError(
            "independent_verification must be an object"
        )
    verifier_id = _require_nonplaceholder(
        verifier.get("reviewer_id"), "independent verifier reviewer_id"
    )
    _require_nonplaceholder(
        verifier.get("qualification_summary"),
        "independent verifier qualification_summary",
    )
    if (
        verifier.get("reviewer_role")
        != "independent_registration_verifier"
        or verifier.get("developer_participation") is not False
        or verifier.get("project_collaborator") is not False
        or verifier.get("conflict_of_interest_declared") is not False
        or verifier.get("public_record_access_verified") is not True
        or verifier.get("attachment_hashes_verified") is not True
        or verifier.get("indirect_disclosure_review_complete") is not True
        or verifier.get("sealed_test_identity_disclosed") is not False
    ):
        raise NDPPublicationGateError(
            "independent registration verification is incomplete"
        )
    verified_at = _parse_utc(verifier.get("verified_at"), "verified_at")
    if verified_at < registered_at:
        raise NDPPublicationGateError(
            "registration cannot be verified before it exists"
        )
    attestations = payload.get("attestations")
    required_attestations = {
        "registered_before_test_release": True,
        "exact_manifest_and_content_digest_match": True,
        "all_attachment_hashes_verified": True,
        "no_test_identities_in_uploaded_attachments": True,
        "no_test_outcomes_observed": True,
        "receipt_does_not_itself_authorize_test_release": True,
    }
    if attestations != required_attestations:
        raise NDPPublicationGateError(
            "external preregistration attestations are incomplete"
        )
    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "artifact_type": "external_preregistration_receipt",
        "status": "passed",
        "registry": registry,
        "persistent_identifier": persistent_identifier,
        "registered_at": registration["registered_at"],
        "verified_at": verifier["verified_at"],
        "independent_verifier_id": verifier_id,
        "public_package_manifest_sha256": _sha256_file(
            public_package_manifest_path
        ),
        "public_package_content_digest_sha256": (
            manifest["public_scope"]["content_digest_sha256"]
        ),
        "test_release_authorized": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build and validate the NDP-50 collaborator-feedback and "
            "external-preregistration publication gate."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    workflow = subparsers.add_parser("workflow")
    workflow.add_argument("--public-package-manifest", type=Path, required=True)
    workflow.add_argument("--feedback-matrix", type=Path, required=True)
    workflow.add_argument("--amendment", type=Path, required=True)
    workflow.add_argument("--study-root", type=Path, required=True)
    workflow.add_argument("--output", type=Path, required=True)

    template = subparsers.add_parser("feedback-template")
    template.add_argument("--feedback-matrix", type=Path, required=True)
    template.add_argument("--amendment", type=Path, required=True)
    template.add_argument(
        "--review-material",
        action="append",
        type=Path,
        dest="review_materials",
    )
    template.add_argument("--study-root", type=Path, required=True)
    template.add_argument("--output", type=Path, required=True)

    signoff = subparsers.add_parser("validate-signoff")
    signoff.add_argument("--artifact", type=Path, required=True)
    signoff.add_argument("--feedback-matrix", type=Path, required=True)
    signoff.add_argument("--amendment", type=Path, required=True)
    signoff.add_argument(
        "--review-material",
        action="append",
        type=Path,
        dest="review_materials",
    )
    signoff.add_argument("--study-root", type=Path, required=True)
    signoff.add_argument("--output", type=Path)

    receipt = subparsers.add_parser("validate-receipt")
    receipt.add_argument("--artifact", type=Path, required=True)
    receipt.add_argument("--public-package-manifest", type=Path, required=True)
    receipt.add_argument("--feedback-signoff", type=Path, required=True)
    receipt.add_argument("--feedback-matrix", type=Path, required=True)
    receipt.add_argument("--amendment", type=Path, required=True)
    receipt.add_argument(
        "--review-material",
        action="append",
        type=Path,
        dest="review_materials",
    )
    receipt.add_argument("--study-root", type=Path, required=True)
    receipt.add_argument("--output", type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "workflow":
        payload = build_workflow_spec(
            public_package_manifest_path=args.public_package_manifest,
            feedback_matrix_path=args.feedback_matrix,
            amendment_path=args.amendment,
            study_root=args.study_root,
        )
        _write_json(args.output, payload)
    elif args.command == "feedback-template":
        payload = build_feedback_signoff_template(
            feedback_matrix_path=args.feedback_matrix,
            amendment_path=args.amendment,
            study_root=args.study_root,
            review_material_paths=args.review_materials,
        )
        _write_json(args.output, payload)
    elif args.command == "validate-signoff":
        payload = validate_feedback_signoff(
            _load_json(args.artifact),
            feedback_matrix_path=args.feedback_matrix,
            amendment_path=args.amendment,
            study_root=args.study_root,
            review_material_paths=args.review_materials,
        )
        if args.output is not None:
            _write_json(args.output, payload)
    else:
        payload = validate_external_preregistration_receipt(
            _load_json(args.artifact),
            public_package_manifest_path=args.public_package_manifest,
            feedback_signoff_path=args.feedback_signoff,
            feedback_matrix_path=args.feedback_matrix,
            amendment_path=args.amendment,
            study_root=args.study_root,
            review_material_paths=args.review_materials,
        )
        if args.output is not None:
            _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
