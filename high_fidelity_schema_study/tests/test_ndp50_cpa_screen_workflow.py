from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_cpa_screen_workflow import (
    NDPCPAScreenWorkflowError,
    build_consensus_template,
    build_disagreement_worksheet,
    build_workflow_manifest,
    load_evidence_registry,
    validate_consensus,
    validate_independent_screen,
)


def _neutral() -> dict:
    return {
        "schema_version": "ndp50-cpa-applicability-screen/v1",
        "protocol_version": "ndp50-external-validation-protocol/v1",
        "annotation_stage": "independent_pre_model_screen",
        "annotator_id": "replace-with-pseudonymous-non-developer-id",
        "annotator_role": "replace-with-qualified-annotator-role",
        "qualification_summary": None,
        "conflict_of_interest_declared": None,
        "submission_id": "replace-with-stable-unique-id",
        "developer_participation": False,
        "model_outputs_visible": False,
        "opportunity_manifest": {
            "file": "opportunities.json",
            "sha256": "a" * 64,
        },
        "cases": [
            {
                "case_id": "case-1",
                "dataset_id": "dataset-1",
                "resource_id": "resource-1",
                "split": "development",
                "field_paths": ["subject", "value"],
                "relational_table_applicable": None,
                "single_subject_column_supported": None,
                "subject_column_field_path": None,
                "property_annotation_applicable": None,
                "rationale": None,
                "evidence_refs": [],
            },
            {
                "case_id": "case-2",
                "dataset_id": "dataset-2",
                "resource_id": "resource-2",
                "split": "validation",
                "field_paths": ["time", "reading"],
                "relational_table_applicable": None,
                "single_subject_column_supported": None,
                "subject_column_field_path": None,
                "property_annotation_applicable": None,
                "rationale": None,
                "evidence_refs": [],
            },
        ],
    }


def _submission(
    annotator_id: str,
    submission_id: str,
    *,
    disagree: bool = False,
) -> dict:
    payload = copy.deepcopy(_neutral())
    payload["annotator_id"] = annotator_id
    payload["annotator_role"] = (
        "scientific_metadata_curator"
        if annotator_id == "annotator-a"
        else "annotation_methodologist"
    )
    payload["qualification_summary"] = (
        "Qualified for CPA applicability screening."
    )
    payload["conflict_of_interest_declared"] = False
    payload["submission_id"] = submission_id
    for case in payload["cases"]:
        case.update(
            {
                "relational_table_applicable": True,
                "single_subject_column_supported": True,
                "subject_column_field_path": case["field_paths"][0],
                "property_annotation_applicable": True,
                "rationale": "The approved source supports this decision.",
                "evidence_refs": ["E1"],
            }
        )
    if disagree:
        payload["cases"][0]["single_subject_column_supported"] = False
        payload["cases"][0]["subject_column_field_path"] = None
        payload["cases"][0]["rationale"] = (
            "The approved source does not support one subject."
        )
    return payload


def _evidence_kwargs() -> dict:
    return {
        "evidence_registry": {
            case["case_id"]: {
                "E1": {
                    "applicable_field_paths": case["field_paths"],
                    "source_id": "APPROVED_SOURCE",
                    "approved_purposes": [
                        "cpa_property_annotation_assessment",
                        "cpa_relational_table_assessment",
                        "cpa_subject_column_assessment",
                    ],
                }
            }
            for case in _neutral()["cases"]
        },
        "source_bundle_manifest": {
            "file": "manifest.json",
            "sha256": "b" * 64,
            "status": "ready_for_independent_annotation",
        },
    }


def _freeze_consensus(template: dict) -> dict:
    consensus = copy.deepcopy(template)
    consensus["status"] = "consensus_frozen"
    consensus["adjudicator_id"] = "adjudicator-c"
    consensus["adjudicator_role"] = "cpa_methods_lead"
    consensus["qualification_summary"] = (
        "Senior methodologist for CPA applicability adjudication."
    )
    consensus["conflict_of_interest_declared"] = False
    consensus["developer_participation"] = False
    consensus["prior_stage_participation"] = False
    for case in consensus["cases"]:
        for resolution in case["resolutions"]:
            if resolution["slot"] == "single_subject_column_supported":
                resolution["selected_value"] = True
            elif resolution["slot"] == "subject_column_field_path":
                resolution["selected_value"] = "subject"
            resolution["rationale"] = "Resolved from the approved source."
            resolution["evidence_refs"] = ["E1"]
            case[resolution["slot"]] = resolution["selected_value"]
        case["consensus_rationale"] = "Consensus based on approved evidence."
        case["evidence_refs"] = ["E1"]
        case["cpa_applicable"] = all(
            case[key]
            for key in (
                "relational_table_applicable",
                "single_subject_column_supported",
                "property_annotation_applicable",
            )
        ) and case["subject_column_field_path"] is not None
    consensus["completion_attestation"] = True
    return consensus


def test_independent_screen_rejects_neutral_placeholders_and_nulls() -> None:
    with pytest.raises(NDPCPAScreenWorkflowError, match="placeholder"):
        validate_independent_screen(
            _neutral(), _neutral(), **_evidence_kwargs()
        )


def test_independent_screen_rejects_mutated_case_identity() -> None:
    submission = _submission("annotator-a", "submission-a")
    submission["cases"][0]["field_paths"].append("invented")
    with pytest.raises(NDPCPAScreenWorkflowError, match="mutates"):
        validate_independent_screen(
            submission, _neutral(), **_evidence_kwargs()
        )


def test_independent_screen_rejects_unlocatable_evidence() -> None:
    submission = _submission("annotator-a", "submission-a")
    submission["cases"][0]["evidence_refs"] = ["NOT-IN-CATALOG"]

    with pytest.raises(NDPCPAScreenWorkflowError, match="unknown evidence"):
        validate_independent_screen(
            submission, _neutral(), **_evidence_kwargs()
        )


def test_independent_screen_rejects_evidence_without_approved_purpose() -> None:
    submission = _submission("annotator-a", "submission-a")
    evidence = _evidence_kwargs()
    for catalog in evidence["evidence_registry"].values():
        catalog["E1"]["approved_purposes"].remove(
            "cpa_property_annotation_assessment"
        )

    with pytest.raises(NDPCPAScreenWorkflowError, match="approved for purpose"):
        validate_independent_screen(
            submission, _neutral(), **evidence
        )


def test_comparison_requires_distinct_annotators() -> None:
    first = _submission("annotator-a", "submission-a")
    second = _submission("annotator-a", "submission-b")
    with pytest.raises(NDPCPAScreenWorkflowError, match="distinct annotators"):
        build_disagreement_worksheet(
            first, second, _neutral(), **_evidence_kwargs()
        )


def test_valid_submissions_produce_only_deterministic_disagreements() -> None:
    first = _submission("annotator-a", "submission-a")
    second = _submission(
        "annotator-b", "submission-b", disagree=True
    )
    worksheet = build_disagreement_worksheet(
        first, second, _neutral(), **_evidence_kwargs()
    )

    assert worksheet["counts"] == {
        "case_count": 2,
        "slot_count": 8,
        "agreement_count": 6,
        "disagreement_count": 2,
        "agreement_rate": 0.75,
    }
    assert worksheet["automatic_adjudication"] is False
    assert [
        item["slot"]
        for item in worksheet["cases"][0]["slots"]
        if not item["agreed"]
    ] == [
        "single_subject_column_supported",
        "subject_column_field_path",
    ]


def test_screen_pair_requires_curator_and_methodologist() -> None:
    first = _submission("annotator-a", "submission-a")
    second = _submission("annotator-b", "submission-b")
    first["annotator_role"] = "annotation_methodologist"

    with pytest.raises(NDPCPAScreenWorkflowError, match="include a curator"):
        build_disagreement_worksheet(
            first, second, _neutral(), **_evidence_kwargs()
        )


def test_consensus_rejects_mutation_of_agreed_slot() -> None:
    first = _submission("annotator-a", "submission-a")
    second = _submission(
        "annotator-b", "submission-b", disagree=True
    )
    worksheet = build_disagreement_worksheet(
        first, second, _neutral(), **_evidence_kwargs()
    )
    template = build_consensus_template(
        first, second, _neutral(), worksheet, **_evidence_kwargs()
    )
    consensus = _freeze_consensus(template)
    consensus["cases"][0]["relational_table_applicable"] = False

    with pytest.raises(NDPCPAScreenWorkflowError, match="mutates agreed"):
        validate_consensus(
            consensus,
            first,
            second,
            _neutral(),
            worksheet,
            **_evidence_kwargs(),
        )


def test_consensus_requires_resolution_for_every_disagreement() -> None:
    first = _submission("annotator-a", "submission-a")
    second = _submission(
        "annotator-b", "submission-b", disagree=True
    )
    worksheet = build_disagreement_worksheet(
        first, second, _neutral(), **_evidence_kwargs()
    )
    template = build_consensus_template(
        first, second, _neutral(), worksheet, **_evidence_kwargs()
    )
    consensus = _freeze_consensus(template)
    consensus["cases"][0]["resolutions"].pop()

    with pytest.raises(NDPCPAScreenWorkflowError, match="every and only"):
        validate_consensus(
            consensus,
            first,
            second,
            _neutral(),
            worksheet,
            **_evidence_kwargs(),
        )


def test_completed_consensus_is_validated_and_derived() -> None:
    first = _submission("annotator-a", "submission-a")
    second = _submission(
        "annotator-b", "submission-b", disagree=True
    )
    worksheet = build_disagreement_worksheet(
        first, second, _neutral(), **_evidence_kwargs()
    )
    template = build_consensus_template(
        first, second, _neutral(), worksheet, **_evidence_kwargs()
    )
    consensus = _freeze_consensus(template)

    report = validate_consensus(
        consensus,
        first,
        second,
        _neutral(),
        worksheet,
        **_evidence_kwargs(),
    )

    assert report["status"] == "passed"
    assert report["resolved_disagreement_count"] == 2
    assert report["cpa_applicable_case_count"] == 2


def test_consensus_adjudicator_must_be_fresh_from_screens() -> None:
    first = _submission("annotator-a", "submission-a")
    second = _submission(
        "annotator-b", "submission-b", disagree=True
    )
    worksheet = build_disagreement_worksheet(
        first, second, _neutral(), **_evidence_kwargs()
    )
    consensus = _freeze_consensus(
        build_consensus_template(
            first, second, _neutral(), worksheet, **_evidence_kwargs()
        )
    )
    consensus["adjudicator_id"] = "annotator-a"

    with pytest.raises(
        NDPCPAScreenWorkflowError,
        match="distinct from prior annotators",
    ):
        validate_consensus(
            consensus,
            first,
            second,
            _neutral(),
            worksheet,
            **_evidence_kwargs(),
        )


def test_workflow_manifest_contains_no_human_decisions() -> None:
    implementation = (
        Path(__file__).resolve().parents[1]
        / "ndp50_cpa_screen_workflow.py"
    )
    neutral = _neutral()
    neutral_hash = hashlib.sha256(
        json.dumps(neutral, sort_keys=True).encode()
    ).hexdigest()

    manifest = build_workflow_manifest(
        neutral,
        neutral_sha256=neutral_hash,
        implementation_file=implementation,
        source_bundle_manifest=_evidence_kwargs()[
            "source_bundle_manifest"
        ],
        source_bundle_approved=False,
        evidence_registry=_evidence_kwargs()["evidence_registry"],
    )

    assert (
        manifest["status"]
        == "workflow_validated_screening_blocked_on_source_approval"
    )
    assert manifest["case_count"] == 2
    assert manifest["required_independent_submissions"] == 2
    assert manifest["human_decisions_present"] is False
    assert manifest["screening_execution_authorized"] is False
    assert manifest["evidence_binding_complete"] is True


def test_draft_source_bundles_cannot_authorize_screening(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "case-1.source-bundle.json"
    bundle.write_text(
        json.dumps(
            {
                "schema_version": "semantic-source-bundle/v1",
                "dataset_id": "case-1",
                "status": "draft_blocked_on_human_approval",
                "evidence_catalog": [
                    {
                        "catalog_evidence_id": "E1",
                        "applicable_field_paths": ["subject"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": (
                    "ndp50-source-bundle-draft-manifest/v1"
                ),
                "status": (
                    "draft_bundles_structurally_valid_not_annotation_ready"
                ),
                "cases": [
                    {
                        "case_id": "case-1",
                        "bundle_file": bundle.name,
                        "bundle_sha256": hashlib.sha256(
                            bundle.read_bytes()
                        ).hexdigest(),
                        "annotation_readiness": (
                            "blocked_on_frozen_vocabulary_and_human_approval"
                        ),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    _, _, approved = load_evidence_registry(
        manifest, require_approved=False
    )
    assert approved is False
    with pytest.raises(NDPCPAScreenWorkflowError, match="cannot authorize"):
        load_evidence_registry(manifest, require_approved=True)
