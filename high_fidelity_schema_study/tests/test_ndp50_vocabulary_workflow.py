from __future__ import annotations

import copy

import pytest

from high_fidelity_schema_study.ndp50_vocabulary_workflow import (
    NDPVocabularyWorkflowError,
    build_candidate_catalog,
    build_consensus_template,
    build_decision_template,
    build_frozen_vocabulary,
    compare_decisions,
    validate_consensus,
    validate_discovery,
)
from high_fidelity_schema_study.semantic_gold_workflow import validate_vocabulary


def _registry() -> dict:
    return {
        "case-1": {
            "E1": {
                "catalog_evidence_id": "E1",
                "applicable_field_paths": ["temperature"],
            }
        }
    }


def _template() -> dict:
    return {
        "schema_version": "ndp50-vocabulary-discovery/v1",
        "annotation_stage": "independent_pre_annotation_discovery",
        "reviewer_id": "replace-with-pseudonymous-non-developer-id",
        "reviewer_role": "replace-with-qualified-reviewer-role",
        "qualification_summary": None,
        "conflict_of_interest_declared": None,
        "submission_id": "replace-with-stable-unique-id",
        "developer_participation": False,
        "model_outputs_visible": False,
        "other_review_visible_before_freeze": False,
        "draft_vocabulary": {"file": "draft.json", "sha256": "a" * 64},
        "source_bundle_manifest": {
            "file": "manifest.json",
            "sha256": "b" * 64,
            "status": "draft_bundles_structurally_valid_not_annotation_ready",
        },
        "existing_vocabulary": {
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
            "semantic_types": ["air_temperature"],
            "units": ["Celsius"],
            "unit_aliases": {"C": "Celsius"},
            "unit_patterns": [],
        },
        "policy_decisions": {
            "preserve_base_terms": None,
            "logical_types_fixed": None,
            "oov_applicable_values_use_null": None,
            "post_freeze_extensions_forbidden": None,
            "field_tokens_not_promoted_without_evidence": None,
        },
        "policy_rationale": None,
        "case_reviews": [
            {
                "case_id": "case-1",
                "coverage_adequate": None,
                "concepts_missing": [],
                "rationale": None,
                "evidence_refs": [],
            }
        ],
        "proposals": [],
        "completion_attestation": None,
    }


def _discovery(
    reviewer: str,
    submission: str,
    *,
    propose: bool,
) -> dict:
    result = copy.deepcopy(_template())
    result["reviewer_id"] = reviewer
    result["reviewer_role"] = (
        "scientific_metadata_curator"
        if reviewer == "reviewer-a"
        else "annotation_methodologist"
    )
    result["qualification_summary"] = "Qualified for the assigned review role."
    result["conflict_of_interest_declared"] = False
    result["submission_id"] = submission
    result["policy_decisions"] = {
        key: True for key in result["policy_decisions"]
    }
    result["policy_rationale"] = "The frozen policies prevent label drift."
    result["case_reviews"][0].update(
        {
            "coverage_adequate": not propose,
            "concepts_missing": ["soil_moisture"] if propose else [],
            "rationale": "Reviewed the complete case evidence.",
            "evidence_refs": [
                {"case_id": "case-1", "catalog_evidence_id": "E1"}
            ],
        }
    )
    if propose:
        result["proposals"] = [
            {
                "category": "semantic_type",
                "term": "soil_moisture",
                "rationale": "The source explicitly documents this concept.",
                "evidence_refs": [
                    {"case_id": "case-1", "catalog_evidence_id": "E1"}
                ],
            }
        ]
    result["completion_attestation"] = True
    return result


def _decision(catalog: dict, reviewer: str, submission: str) -> dict:
    result = build_decision_template(catalog)
    result["reviewer_id"] = reviewer
    result["reviewer_role"] = (
        "scientific_metadata_curator"
        if reviewer in {"reviewer-a", "decision-curator"}
        else "annotation_methodologist"
    )
    result["qualification_summary"] = "Qualified for the assigned review role."
    result["conflict_of_interest_declared"] = False
    result["submission_id"] = submission
    result["policy_decisions"] = {
        key: True for key in result["policy_decisions"]
    }
    result["corpus_coverage_adequate_after_decisions"] = True
    result["policy_rationale"] = "All frozen policies are required."
    for item in result["candidate_decisions"]:
        item.update(
            {
                "approved": True,
                "rationale": "The proposal is supported and non-duplicative.",
                "evidence_refs": [
                    {"case_id": "case-1", "catalog_evidence_id": "E1"}
                ],
            }
        )
    result["completion_attestation"] = True
    return result


def _freeze_consensus(template: dict) -> dict:
    result = copy.deepcopy(template)
    result["status"] = "consensus_frozen"
    result["adjudicator_id"] = "adjudicator-c"
    result["adjudicator_role"] = "ontology_governance_lead"
    result["qualification_summary"] = (
        "Senior ontology governance reviewer with annotation experience."
    )
    result["conflict_of_interest_declared"] = False
    result["developer_participation"] = False
    result["prior_stage_participation"] = False
    reference = [{"case_id": "case-1", "catalog_evidence_id": "E1"}]
    for slot_id in result["slot_values"]:
        if result["slot_values"][slot_id] is None:
            result["slot_values"][slot_id] = True
        result["slot_rationales"][slot_id] = "Supported by the reviewed source."
        result["slot_evidence_refs"][slot_id] = reference
    for resolution in result["resolutions"]:
        resolution.update(
            {
                "selected_value": result["slot_values"][
                    resolution["slot_id"]
                ],
                "rationale": "Human adjudication selected this value.",
                "evidence_refs": reference,
            }
        )
    result["completion_attestation"] = True
    return result


def _draft_vocabulary() -> dict:
    return {
        "schema_version": "semantic-annotation-vocabulary/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "status": "draft",
        "vocabulary_version": "ndp50-draft-v1",
        "physical_types": ["string"],
        "logical_types": _template()["existing_vocabulary"]["logical_types"],
        "semantic_types": ["air_temperature"],
        "units": ["Celsius"],
        "unit_aliases": {"C": "Celsius"},
        "unit_patterns": [],
        "unknown_representation": None,
        "freeze_blockers": ["human review absent"],
    }


def test_discovery_rejects_placeholders_and_incomplete_decisions() -> None:
    with pytest.raises(NDPVocabularyWorkflowError, match="placeholder"):
        validate_discovery(
            _template(), _template(), evidence_registry=_registry()
        )


def test_discovery_rejects_existing_term_as_new_proposal() -> None:
    discovery = _discovery("reviewer-a", "discovery-a", propose=True)
    discovery["proposals"][0]["term"] = "air_temperature"

    with pytest.raises(NDPVocabularyWorkflowError, match="already exists"):
        validate_discovery(
            discovery, _template(), evidence_registry=_registry()
        )


def test_two_discoveries_form_deterministic_union_without_auto_acceptance() -> None:
    first = _discovery("reviewer-a", "discovery-a", propose=True)
    second = _discovery("reviewer-b", "discovery-b", propose=False)

    catalog = build_candidate_catalog(
        first,
        second,
        _template(),
        evidence_registry=_registry(),
    )

    assert catalog["candidate_count"] == 1
    assert catalog["candidates"][0]["proposal"] == {
        "category": "semantic_type",
        "term": "soil_moisture",
    }
    assert catalog["candidates"][0]["proposed_by"] == ["a"]
    assert catalog["automatic_acceptance"] is False


def test_candidate_decisions_require_distinct_reviewers() -> None:
    catalog = build_candidate_catalog(
        _discovery("reviewer-a", "discovery-a", propose=True),
        _discovery("reviewer-b", "discovery-b", propose=False),
        _template(),
        evidence_registry=_registry(),
    )
    first = _decision(catalog, "reviewer-a", "decision-a")
    second = _decision(catalog, "reviewer-a", "decision-b")

    with pytest.raises(NDPVocabularyWorkflowError, match="distinct reviewers"):
        compare_decisions(
            first, second, catalog, evidence_registry=_registry()
        )


def test_candidate_decisions_require_reviewers_fresh_from_discovery() -> None:
    catalog = build_candidate_catalog(
        _discovery("reviewer-a", "discovery-a", propose=True),
        _discovery("reviewer-b", "discovery-b", propose=False),
        _template(),
        evidence_registry=_registry(),
    )
    first = _decision(catalog, "reviewer-a", "decision-a")
    second = _decision(catalog, "decision-methodologist", "decision-b")

    with pytest.raises(NDPVocabularyWorkflowError, match="fresh from discovery"):
        compare_decisions(
            first, second, catalog, evidence_registry=_registry()
        )


def test_consensus_cannot_mutate_agreed_policy() -> None:
    catalog = build_candidate_catalog(
        _discovery("reviewer-a", "discovery-a", propose=True),
        _discovery("reviewer-b", "discovery-b", propose=False),
        _template(),
        evidence_registry=_registry(),
    )
    first = _decision(catalog, "decision-curator", "decision-a")
    second = _decision(
        catalog, "decision-methodologist", "decision-b"
    )
    worksheet = compare_decisions(
        first, second, catalog, evidence_registry=_registry()
    )
    consensus = _freeze_consensus(build_consensus_template(worksheet))
    consensus["slot_values"]["policy:logical_types_fixed"] = False

    with pytest.raises(NDPVocabularyWorkflowError, match="mutates agreed"):
        validate_consensus(
            consensus,
            first,
            second,
            catalog,
            worksheet,
            evidence_registry=_registry(),
        )


def test_valid_consensus_is_only_path_to_frozen_vocabulary() -> None:
    catalog = build_candidate_catalog(
        _discovery("reviewer-a", "discovery-a", propose=True),
        _discovery("reviewer-b", "discovery-b", propose=False),
        _template(),
        evidence_registry=_registry(),
    )
    first = _decision(catalog, "decision-curator", "decision-a")
    second = _decision(
        catalog, "decision-methodologist", "decision-b"
    )
    worksheet = compare_decisions(
        first, second, catalog, evidence_registry=_registry()
    )
    consensus = _freeze_consensus(build_consensus_template(worksheet))
    validation = validate_consensus(
        consensus,
        first,
        second,
        catalog,
        worksheet,
        evidence_registry=_registry(),
    )
    assert validation["status"] == "passed"
    assert catalog["case_coverage_findings"][0]["review_a"][
        "coverage_adequate"
    ] is False

    frozen = build_frozen_vocabulary(
        _draft_vocabulary(),
        catalog,
        consensus,
        first,
        second,
        worksheet,
        evidence_registry=_registry(),
        draft_sha256="a" * 64,
    )

    assert frozen["status"] == "frozen"
    assert "soil_moisture" in frozen["semantic_types"]
    assert "freeze_blockers" not in frozen
    assert validate_vocabulary(frozen)["status"] == "ready"


def test_consensus_requires_fresh_qualified_adjudicator() -> None:
    catalog = build_candidate_catalog(
        _discovery("reviewer-a", "discovery-a", propose=True),
        _discovery("reviewer-b", "discovery-b", propose=False),
        _template(),
        evidence_registry=_registry(),
    )
    first = _decision(catalog, "decision-curator", "decision-a")
    second = _decision(
        catalog, "decision-methodologist", "decision-b"
    )
    worksheet = compare_decisions(
        first, second, catalog, evidence_registry=_registry()
    )
    consensus = _freeze_consensus(build_consensus_template(worksheet))
    consensus["adjudicator_id"] = "decision-curator"

    with pytest.raises(
        NDPVocabularyWorkflowError,
        match="distinct from prior reviewers",
    ):
        validate_consensus(
            consensus,
            first,
            second,
            catalog,
            worksheet,
            evidence_registry=_registry(),
        )
