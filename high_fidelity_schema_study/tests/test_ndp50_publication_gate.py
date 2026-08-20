from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_publication_gate import (
    EXPECTED_FEEDBACK_ITEMS,
    FEEDBACK_REVIEW_MATERIAL_RELATIVE_PATHS,
    NDPPublicationGateError,
    build_feedback_signoff_template,
    build_workflow_spec,
    main,
    validate_external_preregistration_receipt,
    validate_feedback_signoff,
)


ROOT = Path("high_fidelity_schema_study")


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


def _fixture(tmp_path: Path) -> dict:
    matrix = tmp_path / "docs" / "feedback.md"
    amendment = tmp_path / "docs" / "amendment.md"
    matrix.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_text("feedback matrix\n", encoding="utf-8")
    amendment.write_text("amendment\n", encoding="utf-8")
    for relative in FEEDBACK_REVIEW_MATERIAL_RELATIVE_PATHS:
        material = tmp_path / relative
        material.parent.mkdir(parents=True, exist_ok=True)
        material.write_text(
            f"bound review material: {relative}\n",
            encoding="utf-8",
        )
    manifest = tmp_path / "manifest.json"
    _write(
        manifest,
        {
            "schema_version": "ndp50-public-preregistration-package/v1",
            "status": "draft_structurally_valid_not_registered",
            "authorization": {"external_registration_claimed": False},
            "private_sealing_control": {
                "sealed_identity_match_count": 0,
            },
            "public_scope": {
                "content_digest_sha256": "a" * 64,
            },
        },
    )
    signoff = build_feedback_signoff_template(
        feedback_matrix_path=matrix,
        amendment_path=amendment,
        study_root=tmp_path,
    )
    signoff.update(
        {
            "status": "approved_with_recorded_boundaries",
            "human_decisions_present": True,
            "reviewed_feedback_items": EXPECTED_FEEDBACK_ITEMS,
            "collaborator": {
                "reviewer_id": "collaborator-01",
                "reviewer_role": "postdoctoral_research_collaborator",
                "qualification_summary": (
                    "Postdoctoral metadata researcher"
                ),
                "project_collaborator": True,
                "developer_participation": False,
                "independent_reviewer": False,
                "conflict_of_interest_disclosure": (
                    "Active project collaborator; review is not independent."
                ),
                "signed_at": "2026-07-27T20:00:00Z",
            },
            "signed_at": "2026-07-27T20:00:00Z",
            "attestations": {
                "all_feedback_items_reviewed": True,
                "all_bound_review_materials_reviewed": True,
                "claim_boundaries_accepted": True,
                "inactive_sensitivities_not_presented_as_executed": True,
                "collaborator_review_not_represented_as_independent": True,
                "no_test_outcomes_seen": True,
                "test_release_not_authorized_by_this_signoff": True,
            },
        }
    )
    signoff_path = tmp_path / "feedback_signoff.json"
    _write(signoff_path, signoff)
    receipt = {
        "schema_version": "ndp50-external-preregistration-receipt/v1",
        "status": "verified_external_registration",
        "human_decisions_present": True,
        "test_outcomes_observed": False,
        "test_release_authorized": False,
        "public_package_manifest": _binding(manifest, tmp_path),
        "public_package_content_digest_sha256": "a" * 64,
        "feedback_response_signoff": _binding(signoff_path, tmp_path),
        "registration": {
            "registry": "osf",
            "persistent_identifier": "osf.io/abc12",
            "public_record_url": "https://osf.io/abc12",
            "registered_at": "2026-07-27T21:00:00Z",
            "immutable_version": True,
            "publicly_accessible": True,
        },
        "external_receipt_export_sha256": "b" * 64,
        "independent_verification": {
            "reviewer_id": "registration-verifier-01",
            "reviewer_role": "independent_registration_verifier",
            "qualification_summary": "Independent reproducibility reviewer",
            "developer_participation": False,
            "project_collaborator": False,
            "conflict_of_interest_declared": False,
            "verified_at": "2026-07-27T22:00:00Z",
            "public_record_access_verified": True,
            "attachment_hashes_verified": True,
            "indirect_disclosure_review_complete": True,
            "sealed_test_identity_disclosed": False,
        },
        "attestations": {
            "registered_before_test_release": True,
            "exact_manifest_and_content_digest_match": True,
            "all_attachment_hashes_verified": True,
            "no_test_identities_in_uploaded_attachments": True,
            "no_test_outcomes_observed": True,
            "receipt_does_not_itself_authorize_test_release": True,
        },
    }
    return {
        "matrix": matrix,
        "amendment": amendment,
        "manifest": manifest,
        "signoff": signoff,
        "signoff_path": signoff_path,
        "receipt": receipt,
    }


def test_production_publication_gate_workflow_replays() -> None:
    workflow_path = (
        ROOT
        / "data/experiments/ndp50_v1/preregistration/"
        "publication_gate_workflow_v1.json"
    )
    observed = json.loads(workflow_path.read_text(encoding="utf-8"))
    expected = build_workflow_spec(
        public_package_manifest_path=(
            ROOT
            / "data/experiments/ndp50_v1/preregistration/"
            "public_package_manifest_v1.json"
        ),
        feedback_matrix_path=(
            ROOT / "docs/swathi_feedback_response_matrix_v1.md"
        ),
        amendment_path=(
            ROOT / "docs/ndp50_feedback_improvement_amendment_v1.md"
        ),
        study_root=ROOT,
    )
    assert observed == expected
    assert observed["test_release_authorized"] is False


def test_production_feedback_signoff_template_replays() -> None:
    artifact = (
        ROOT
        / "data/experiments/ndp50_v1/preregistration/"
        "feedback_response_signoff_neutral_v1.json"
    )
    observed = json.loads(artifact.read_text(encoding="utf-8"))
    expected = build_feedback_signoff_template(
        feedback_matrix_path=(
            ROOT / "docs/swathi_feedback_response_matrix_v1.md"
        ),
        amendment_path=(
            ROOT / "docs/ndp50_feedback_improvement_amendment_v1.md"
        ),
        study_root=ROOT,
    )
    assert observed == expected
    assert observed["human_decisions_present"] is False
    assert observed["independence_claimed"] is False


def test_feedback_signoff_and_external_receipt_validate(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    signoff_report = validate_feedback_signoff(
        fixture["signoff"],
        feedback_matrix_path=fixture["matrix"],
        amendment_path=fixture["amendment"],
        study_root=tmp_path,
    )
    assert signoff_report["status"] == "passed"
    assert signoff_report["independent_validation_claimed"] is False

    receipt_report = validate_external_preregistration_receipt(
        fixture["receipt"],
        public_package_manifest_path=fixture["manifest"],
        feedback_signoff_path=fixture["signoff_path"],
        feedback_matrix_path=fixture["matrix"],
        amendment_path=fixture["amendment"],
        study_root=tmp_path,
    )
    assert receipt_report["status"] == "passed"
    assert receipt_report["test_release_authorized"] is False


def test_validate_signoff_cli_writes_replayable_receipt(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    output = tmp_path / "feedback_signoff_validation.json"

    assert (
        main(
            [
                "validate-signoff",
                "--artifact",
                str(fixture["signoff_path"]),
                "--feedback-matrix",
                str(fixture["matrix"]),
                "--amendment",
                str(fixture["amendment"]),
                "--study-root",
                str(tmp_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )
    observed = json.loads(output.read_text(encoding="utf-8"))
    expected = validate_feedback_signoff(
        fixture["signoff"],
        feedback_matrix_path=fixture["matrix"],
        amendment_path=fixture["amendment"],
        study_root=tmp_path,
    )
    assert observed == expected

    external_output = tmp_path / "external_receipt_validation.json"
    external_artifact = tmp_path / "external_receipt.json"
    _write(external_artifact, fixture["receipt"])
    assert (
        main(
            [
                "validate-receipt",
                "--artifact",
                str(external_artifact),
                "--public-package-manifest",
                str(fixture["manifest"]),
                "--feedback-signoff",
                str(fixture["signoff_path"]),
                "--feedback-matrix",
                str(fixture["matrix"]),
                "--amendment",
                str(fixture["amendment"]),
                "--study-root",
                str(tmp_path),
                "--output",
                str(external_output),
            ]
        )
        == 0
    )
    observed_external = json.loads(
        external_output.read_text(encoding="utf-8")
    )
    expected_external = validate_external_preregistration_receipt(
        fixture["receipt"],
        public_package_manifest_path=fixture["manifest"],
        feedback_signoff_path=fixture["signoff_path"],
        feedback_matrix_path=fixture["matrix"],
        amendment_path=fixture["amendment"],
        study_root=tmp_path,
    )
    assert observed_external == expected_external


def test_feedback_signoff_rejects_missing_item_or_independence_claim(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    fixture["signoff"]["reviewed_feedback_items"] = EXPECTED_FEEDBACK_ITEMS[:-1]
    with pytest.raises(NDPPublicationGateError):
        validate_feedback_signoff(
            fixture["signoff"],
            feedback_matrix_path=fixture["matrix"],
            amendment_path=fixture["amendment"],
            study_root=tmp_path,
        )

    fixture = _fixture(tmp_path)
    fixture["signoff"]["independence_claimed"] = True
    with pytest.raises(NDPPublicationGateError):
        validate_feedback_signoff(
            fixture["signoff"],
            feedback_matrix_path=fixture["matrix"],
            amendment_path=fixture["amendment"],
            study_root=tmp_path,
        )


def test_feedback_signoff_rejects_review_material_tampering(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    fixture["signoff"]["review_materials"][0]["sha256"] = "0" * 64

    with pytest.raises(
        NDPPublicationGateError,
        match="review-material bindings changed",
    ):
        validate_feedback_signoff(
            fixture["signoff"],
            feedback_matrix_path=fixture["matrix"],
            amendment_path=fixture["amendment"],
            study_root=tmp_path,
        )


def test_external_receipt_rejects_tampering_and_nonindependent_verifier(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    fixture["receipt"]["public_package_content_digest_sha256"] = "c" * 64
    with pytest.raises(NDPPublicationGateError):
        validate_external_preregistration_receipt(
            fixture["receipt"],
            public_package_manifest_path=fixture["manifest"],
            feedback_signoff_path=fixture["signoff_path"],
            feedback_matrix_path=fixture["matrix"],
            amendment_path=fixture["amendment"],
            study_root=tmp_path,
        )

    fixture = _fixture(tmp_path)
    fixture["receipt"]["independent_verification"][
        "project_collaborator"
    ] = True
    with pytest.raises(NDPPublicationGateError):
        validate_external_preregistration_receipt(
            fixture["receipt"],
            public_package_manifest_path=fixture["manifest"],
            feedback_signoff_path=fixture["signoff_path"],
            feedback_matrix_path=fixture["matrix"],
            amendment_path=fixture["amendment"],
            study_root=tmp_path,
        )


def test_external_receipt_rejects_invalid_time_and_non_https_record(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    fixture["receipt"]["independent_verification"][
        "verified_at"
    ] = "2026-07-27T20:00:00Z"
    with pytest.raises(NDPPublicationGateError):
        validate_external_preregistration_receipt(
            fixture["receipt"],
            public_package_manifest_path=fixture["manifest"],
            feedback_signoff_path=fixture["signoff_path"],
            feedback_matrix_path=fixture["matrix"],
            amendment_path=fixture["amendment"],
            study_root=tmp_path,
        )

    fixture = _fixture(tmp_path)
    fixture["receipt"]["registration"][
        "public_record_url"
    ] = "http://osf.io/abc12"
    with pytest.raises(NDPPublicationGateError):
        validate_external_preregistration_receipt(
            fixture["receipt"],
            public_package_manifest_path=fixture["manifest"],
            feedback_signoff_path=fixture["signoff_path"],
            feedback_matrix_path=fixture["matrix"],
            amendment_path=fixture["amendment"],
            study_root=tmp_path,
        )
