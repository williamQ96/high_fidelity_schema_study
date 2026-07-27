from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_source_approval import (
    NDPSourceApprovalError,
    PURPOSES,
    build_approved_manifest,
    build_consensus_template,
    build_review_template,
    compare_reviews,
    load_approved_evidence_registry,
    load_pending_bundle_registry,
    validate_consensus,
    validate_review,
)
from high_fidelity_schema_study.ndp50_cpa_screen_workflow import (
    load_evidence_registry,
)


def _write(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    vocabulary = tmp_path / "vocabulary.json"
    vocabulary_hash = _write(
        vocabulary,
        {
            "schema_version": "semantic-annotation-vocabulary/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "frozen",
            "vocabulary_version": "ndp50-v1",
            "physical_types": ["string"],
            "logical_types": [
                "attribute",
                "coordinate",
                "identifier",
                "label",
                "measurement",
                "relationship",
                "time_axis",
                "unknown",
            ],
            "semantic_types": ["record_identifier"],
            "units": ["meter"],
            "unit_aliases": {"m": "meter"},
            "unit_patterns": [],
            "unknown_representation": None,
        },
    )
    bundle = tmp_path / "bundles" / "case-1.source-bundle.json"
    bundle_hash = _write(
        bundle,
        {
            "schema_version": "semantic-source-bundle/v1",
            "dataset_id": "case-1",
            "status": "draft_blocked_on_human_source_approval",
            "vocabulary_sha256": vocabulary_hash,
            "evidence_catalog": [
                {
                    "catalog_evidence_id": "E1",
                    "source_id": "DOC",
                    "source_type": "catalog_documentation",
                    "source_sha256": "s" * 64,
                    "selector": "result.notes",
                    "applicable_field_paths": ["subject"],
                    "strength": "documentation",
                }
            ],
        },
    )
    manifest = tmp_path / "bundles" / "manifest.json"
    _write(
        manifest,
        {
            "schema_version": "ndp50-source-bundle-draft-manifest/v1",
            "status": (
                "draft_bundles_structurally_valid_pending_human_source_approval"
            ),
            "vocabulary": {
                "status": "frozen",
                "sha256": vocabulary_hash,
            },
            "cases": [
                {
                    "case_id": "case-1",
                    "split": "development",
                    "bundle_file": bundle.name,
                    "bundle_sha256": bundle_hash,
                    "annotation_readiness": "blocked_on_human_source_approval",
                }
            ],
        },
    )
    cpa_screen = tmp_path / "cpa-screen.json"
    _write(
        cpa_screen,
        {
            "schema_version": "ndp50-cpa-applicability-screen/v1",
            "cases": [{"case_id": "case-1"}],
        },
    )
    return manifest, cpa_screen, vocabulary


def _review(template: dict, reviewer: str, submission: str) -> dict:
    result = copy.deepcopy(template)
    result["reviewer_id"] = reviewer
    result["reviewer_role"] = (
        "scientific_metadata_curator"
        if reviewer == "reviewer-a"
        else "annotation_methodologist"
    )
    result["qualification_summary"] = "Qualified for the assigned role."
    result["conflict_of_interest_declared"] = False
    result["submission_id"] = submission
    for case in result["cases"]:
        case["additional_documentation_required"] = False
        case["case_rationale"] = "The source set covers every required purpose."
        for evidence in case["evidence_decisions"]:
            evidence["locatable"] = True
            evidence["relevant"] = True
            evidence["approved_purposes"] = sorted(PURPOSES)
            evidence["rationale"] = "The selector is locatable and relevant."
    result["completion_attestation"] = True
    return result


def _consensus(worksheet: dict) -> dict:
    result = build_consensus_template(worksheet)
    result["status"] = "consensus_frozen"
    result["adjudicator_id"] = "adjudicator-c"
    result["adjudicator_role"] = "research_data_governance_lead"
    result["qualification_summary"] = (
        "Senior reviewer for scientific evidence governance."
    )
    result["conflict_of_interest_declared"] = False
    result["developer_participation"] = False
    result["prior_stage_participation"] = False
    for slot_id in result["slot_rationales"]:
        result["slot_rationales"][slot_id] = (
            "Consensus retained the independently agreed decision."
        )
    result["completion_attestation"] = True
    return result


def test_review_requires_frozen_vocabulary_rebuilt_bundles(
    tmp_path: Path,
) -> None:
    manifest, _, _ = _inputs(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["status"] = "ready_for_independent_annotation"
    _write(manifest, payload)

    with pytest.raises(NDPSourceApprovalError, match="requires bundles rebuilt"):
        load_pending_bundle_registry(
            manifest, require_frozen_vocabulary=True
        )


def test_independent_review_rejects_mutated_evidence_identity(
    tmp_path: Path,
) -> None:
    manifest, cpa_screen, vocabulary = _inputs(tmp_path)
    template_path = tmp_path / "review-template.json"
    template = build_review_template(
        source_bundle_manifest_path=manifest,
        cpa_screen_path=cpa_screen,
        frozen_vocabulary_path=vocabulary,
        output_path=template_path,
    )
    review = _review(template, "reviewer-a", "review-a")
    review["cases"][0]["evidence_decisions"][0]["selector"] = "invented"

    with pytest.raises(NDPSourceApprovalError, match="mutates selector"):
        validate_review(review, template)


def test_consensus_cannot_mutate_agreed_source_decision(
    tmp_path: Path,
) -> None:
    manifest, cpa_screen, vocabulary = _inputs(tmp_path)
    template_path = tmp_path / "review-template.json"
    template = build_review_template(
        source_bundle_manifest_path=manifest,
        cpa_screen_path=cpa_screen,
        frozen_vocabulary_path=vocabulary,
        output_path=template_path,
    )
    first = _review(template, "reviewer-a", "review-a")
    second = _review(template, "reviewer-b", "review-b")
    worksheet = compare_reviews(first, second, template)
    consensus = _consensus(worksheet)
    consensus["slot_values"]["evidence:case-1:E1:relevant"] = False

    with pytest.raises(NDPSourceApprovalError, match="mutates agreed"):
        validate_consensus(
            consensus, first, second, template, worksheet
        )


def test_source_adjudicator_must_be_fresh_from_reviews(
    tmp_path: Path,
) -> None:
    manifest, cpa_screen, vocabulary = _inputs(tmp_path)
    template = build_review_template(
        source_bundle_manifest_path=manifest,
        cpa_screen_path=cpa_screen,
        frozen_vocabulary_path=vocabulary,
        output_path=tmp_path / "review-template.json",
    )
    first = _review(template, "reviewer-a", "review-a")
    second = _review(template, "reviewer-b", "review-b")
    worksheet = compare_reviews(first, second, template)
    consensus = _consensus(worksheet)
    consensus["adjudicator_id"] = "reviewer-a"

    with pytest.raises(
        NDPSourceApprovalError,
        match="distinct from prior reviewers",
    ):
        validate_consensus(
            consensus, first, second, template, worksheet
        )


def test_approved_manifest_is_recomputed_from_full_review_chain(
    tmp_path: Path,
) -> None:
    manifest, cpa_screen, vocabulary = _inputs(tmp_path)
    template_path = tmp_path / "approval" / "review-template.json"
    template = build_review_template(
        source_bundle_manifest_path=manifest,
        cpa_screen_path=cpa_screen,
        frozen_vocabulary_path=vocabulary,
        output_path=template_path,
    )
    _write(template_path, template)
    review_a_path = tmp_path / "approval" / "review-a.json"
    review_b_path = tmp_path / "approval" / "review-b.json"
    _write(review_a_path, _review(template, "reviewer-a", "review-a"))
    _write(review_b_path, _review(template, "reviewer-b", "review-b"))
    worksheet_path = tmp_path / "approval" / "worksheet.json"
    worksheet = compare_reviews(
        json.loads(review_a_path.read_text(encoding="utf-8")),
        json.loads(review_b_path.read_text(encoding="utf-8")),
        template,
        review_a_sha256=hashlib.sha256(review_a_path.read_bytes()).hexdigest(),
        review_b_sha256=hashlib.sha256(review_b_path.read_bytes()).hexdigest(),
    )
    _write(worksheet_path, worksheet)
    consensus_path = tmp_path / "approval" / "consensus.json"
    consensus = build_consensus_template(
        worksheet,
        worksheet_sha256=hashlib.sha256(
            worksheet_path.read_bytes()
        ).hexdigest(),
    )
    consensus["status"] = "consensus_frozen"
    consensus["adjudicator_id"] = "adjudicator-c"
    consensus["adjudicator_role"] = "research_data_governance_lead"
    consensus["qualification_summary"] = (
        "Senior reviewer for scientific evidence governance."
    )
    consensus["conflict_of_interest_declared"] = False
    consensus["developer_participation"] = False
    consensus["prior_stage_participation"] = False
    for slot_id in consensus["slot_rationales"]:
        consensus["slot_rationales"][slot_id] = (
            "Consensus retained the independently agreed decision."
        )
    consensus["completion_attestation"] = True
    _write(consensus_path, consensus)
    approved_path = tmp_path / "approval" / "approved.json"
    approved = build_approved_manifest(
        source_bundle_manifest_path=manifest,
        review_template_path=template_path,
        review_a_path=review_a_path,
        review_b_path=review_b_path,
        worksheet_path=worksheet_path,
        consensus_path=consensus_path,
        output_path=approved_path,
    )
    _write(approved_path, approved)

    registry, binding = load_approved_evidence_registry(approved_path)

    assert binding["status"] == "ready_for_independent_annotation"
    assert set(registry) == {"case-1"}
    assert registry["case-1"]["E1"]["approved_purposes"] == sorted(PURPOSES)
    assert approved["automatic_approval"] is False
    cpa_registry, _, is_approved = load_evidence_registry(
        approved_path, require_approved=True
    )
    assert is_approved is True
    assert set(cpa_registry["case-1"]) == {"E1"}
