from __future__ import annotations

import copy
import json
from pathlib import Path

from high_fidelity_schema_study.ndp50_data_governance_review import (
    build_approval,
    build_review_template,
    build_workflow_spec,
    validate_review,
    verify_approval,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _fixture(tmp_path: Path, monkeypatch) -> tuple[Path, Path, dict]:
    root = tmp_path / "ndp50"
    audit_path = root / "reports" / "audit.json"
    audit = {
        "schema_version": "ndp50-data-governance-audit/v1",
        "status": "provenance_integrity_passed_governance_review_required",
        "scope": {
            "test_dataset_detail_count": 0,
            "test_dataset_identities_included": False,
        },
        "datasets": [
            {
                "dataset_id": "dev-id",
                "split": "development",
                "license": {
                    "license_id": "CC0-1.0",
                    "license_title": "CC0-1.0",
                    "license_url": None,
                    "category": "standard_or_public_domain_identifier",
                },
            },
            {
                "dataset_id": "val-id",
                "split": "validation",
                "license": {
                    "license_id": None,
                    "license_title": None,
                    "license_url": None,
                    "category": "missing",
                },
            },
        ],
    }
    _write(audit_path, audit)
    monkeypatch.setattr(
        (
            "high_fidelity_schema_study.ndp50_data_governance_review."
            "validate_audit_file"
        ),
        lambda payload, *, study_root: {
            "status": "passed",
            "differing_top_level_keys": [],
        },
    )
    template = build_review_template(
        audit_path=audit_path,
        study_root=root,
    )
    return root, audit_path, template


def _completed_review(template: dict) -> dict:
    review = copy.deepcopy(template)
    review["status"] = "completed_pending_validator_approval"
    review["reviewer_signoff"] = {
        "reviewer_id": "steward-01",
        "reviewer_role": "institutional_data_steward",
        "institution": "Example University",
        "qualification_summary": "Institutional research data steward.",
        "institutional_authority_scope": "Research data governance review.",
        "institutional_authority_attested": True,
        "conflict_of_interest_declared": False,
        "developer_participation": False,
        "signed_on": "2026-07-27",
    }
    review["accountable_approval"] = {
        "approver_id": "pi-01",
        "approver_role": "principal_investigator",
        "institution": "Example University",
        "qualification_summary": "Accountable principal investigator.",
        "institutional_authority_scope": "Study execution and publication.",
        "institutional_authority_attested": True,
        "conflict_of_interest_declared": False,
        "developer_participation": True,
        "signed_on": "2026-07-27",
    }
    review["study_policy"] = {
        "model_processing_mode": "local_only",
        "external_provider_name": None,
        "external_provider_terms_url": None,
        "provider_retention_policy": "not_applicable_local_only",
        "provider_training_use_policy": "not_applicable",
        "redaction_and_data_minimization_policy": (
            "Use only the minimum locally required bounded samples."
        ),
        "artifact_release_policy": (
            "Release metadata and derived schemas only where approved."
        ),
        "policy_rationale": (
            "Local-only processing avoids unresolved external-transfer terms."
        ),
    }
    for item in review["dataset_reviews"]:
        item.update(
            {
                "authoritative_license_source_url": (
                    f"https://example.test/licenses/{item['dataset_id']}"
                ),
                "resolved_license_identifier": "resolved-restricted-use",
                "license_terms_status": "verified_requires_restrictions",
                "attribution_status": "not_required",
                "required_attribution_text": None,
                "local_analysis_allowed": True,
                "external_model_transfer_allowed": False,
                "raw_payload_redistribution_allowed": False,
                "metadata_redistribution_allowed": True,
                "derived_schema_redistribution_allowed": True,
                "restrictions_summary": (
                    "No raw redistribution and no external model transfer."
                ),
                "rationale": "Authoritative terms reviewed for planned use.",
                "evidence_refs": [
                    f"https://example.test/licenses/{item['dataset_id']}"
                ],
            }
        )
    review["completion_attestation"] = True
    return review


def test_prepare_is_neutral_and_binds_audited_cases(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, audit_path, template = _fixture(tmp_path, monkeypatch)
    template_path = root / "semantic" / "governance_review.json"
    _write(template_path, template)
    workflow = build_workflow_spec(
        audit_path=audit_path,
        template_path=template_path,
    )

    assert workflow["human_decisions_present"] is False
    assert workflow["required_distinct_signatories"] == 2
    assert len(template["dataset_reviews"]) == 2
    assert all(
        item["license_terms_status"] is None
        for item in template["dataset_reviews"]
    )
    assert "sealed-test-id" not in json.dumps(template, sort_keys=True)


def test_completed_local_only_review_builds_replayable_approval(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, audit_path, template = _fixture(tmp_path, monkeypatch)
    review = _completed_review(template)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    assert validate_review(review, template=template, audit=audit)[
        "status"
    ] == "passed"
    approval = build_approval(
        review=review,
        audit_path=audit_path,
        study_root=root,
    )

    assert approval["derived_gates"]["data_governance_policy_frozen"] is True
    assert approval["counts"]["external_transfer_allowed"] == 0
    assert verify_approval(
        approval,
        audit_path=audit_path,
        study_root=root,
    )["status"] == "passed"


def test_duplicate_signatories_are_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _, audit_path, template = _fixture(tmp_path, monkeypatch)
    review = _completed_review(template)
    review["accountable_approval"]["approver_id"] = "steward-01"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    validation = validate_review(review, template=template, audit=audit)

    assert validation["status"] == "blocked"
    assert "signatories_not_distinct" in {
        item["code"] for item in validation["errors"]
    }


def test_unresolved_license_terms_are_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _, audit_path, template = _fixture(tmp_path, monkeypatch)
    review = _completed_review(template)
    review["dataset_reviews"][0]["license_terms_status"] = (
        "unable_to_resolve"
    )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    validation = validate_review(review, template=template, audit=audit)

    assert "license_terms_unresolved" in {
        item["code"] for item in validation["errors"]
    }


def test_external_mode_requires_every_dataset_transfer_approval(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _, audit_path, template = _fixture(tmp_path, monkeypatch)
    review = _completed_review(template)
    review["study_policy"].update(
        {
            "model_processing_mode": (
                "external_provider_approved_all_in_scope"
            ),
            "external_provider_name": "Example Provider",
            "external_provider_terms_url": "https://example.test/terms",
            "provider_retention_policy": "Zero retention.",
            "provider_training_use_policy": "prohibited_by_provider_terms",
        }
    )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    validation = validate_review(review, template=template, audit=audit)

    assert "external_transfer_not_fully_approved" in {
        item["code"] for item in validation["errors"]
    }


def test_tampered_approval_is_detected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, audit_path, template = _fixture(tmp_path, monkeypatch)
    approval = build_approval(
        review=_completed_review(template),
        audit_path=audit_path,
        study_root=root,
    )
    approval["derived_gates"]["artifact_redistribution_policy_frozen"] = False

    validation = verify_approval(
        approval,
        audit_path=audit_path,
        study_root=root,
    )

    assert validation["status"] == "failed"
    assert validation["differing_top_level_keys"] == ["derived_gates"]
