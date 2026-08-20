from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Mapping

from .ndp50_cpa_screen_workflow import load_evidence_registry
from .semantic_gold_workflow import validate_vocabulary


DISCOVERY_SCHEMA_VERSION = "ndp50-vocabulary-discovery/v1"
CANDIDATE_SCHEMA_VERSION = "ndp50-vocabulary-candidate-catalog/v1"
DECISION_SCHEMA_VERSION = "ndp50-vocabulary-candidate-decision/v1"
DISAGREEMENT_SCHEMA_VERSION = "ndp50-vocabulary-disagreement/v1"
CONSENSUS_SCHEMA_VERSION = "ndp50-vocabulary-consensus/v1"
CONSENSUS_VALIDATION_SCHEMA_VERSION = (
    "ndp50-vocabulary-consensus-validation/v1"
)
WORKFLOW_SCHEMA_VERSION = "ndp50-vocabulary-review-workflow/v1"
POLICY_KEYS = (
    "preserve_base_terms",
    "logical_types_fixed",
    "oov_applicable_values_use_null",
    "post_freeze_extensions_forbidden",
    "field_tokens_not_promoted_without_evidence",
)
PROPOSAL_CATEGORIES = {
    "semantic_type",
    "unit",
    "unit_alias",
    "unit_pattern",
}
REVIEWER_ROLES = {
    "domain_curator",
    "scientific_metadata_curator",
    "annotation_methodologist",
}
CURATOR_ROLES = {"domain_curator", "scientific_metadata_curator"}
CONSENSUS_ADJUDICATOR_ROLES = {
    "senior_scientific_metadata_curator",
    "ontology_governance_lead",
    "annotation_methods_lead",
}
PLACEHOLDER_TOKENS = ("replace-with", "placeholder", "todo", "tbd")


class NDPVocabularyWorkflowError(ValueError):
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


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NDPVocabularyWorkflowError(f"{label} must be non-empty")
    result = value.strip()
    if any(token in result.casefold() for token in PLACEHOLDER_TOKENS):
        raise NDPVocabularyWorkflowError(f"{label} is still a placeholder")
    return result


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NDPVocabularyWorkflowError(f"{label} must be non-empty text")
    return value.strip()


def _binding(path: Path) -> Dict[str, Any]:
    return {"file": path.name, "sha256": _sha256_file(path)}


def _evidence_refs(
    value: Any,
    *,
    label: str,
    registry: Mapping[str, Mapping[str, Mapping[str, Any]]],
    required_case_id: str | None = None,
) -> list[Dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise NDPVocabularyWorkflowError(
            f"{label} requires at least one evidence reference"
        )
    result = []
    seen = set()
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise NDPVocabularyWorkflowError(
                f"{label}[{index}] must be an object"
            )
        case_id = str(item.get("case_id") or "")
        evidence_id = str(item.get("catalog_evidence_id") or "")
        key = (case_id, evidence_id)
        if (
            not case_id
            or not evidence_id
            or case_id not in registry
            or evidence_id not in registry[case_id]
        ):
            raise NDPVocabularyWorkflowError(
                f"{label}[{index}] does not resolve to a bound catalog item"
            )
        if required_case_id is not None and case_id != required_case_id:
            raise NDPVocabularyWorkflowError(
                f"{label}[{index}] must reference case {required_case_id}"
            )
        if key in seen:
            raise NDPVocabularyWorkflowError(
                f"{label} contains duplicate references"
            )
        seen.add(key)
        result.append(
            {"case_id": case_id, "catalog_evidence_id": evidence_id}
        )
    return result


def _proposal_payload(item: Mapping[str, Any]) -> Dict[str, str]:
    category = item.get("category")
    if category not in PROPOSAL_CATEGORIES:
        raise NDPVocabularyWorkflowError(
            f"unsupported proposal category {category!r}"
        )
    if category in {"semantic_type", "unit"}:
        term = _identifier(item.get("term"), f"{category}.term")
        if term != term.strip() or any(char.isspace() for char in term):
            raise NDPVocabularyWorkflowError(
                f"{category}.term must be a whitespace-free canonical token"
            )
        return {"category": str(category), "term": term}
    if category == "unit_alias":
        return {
            "category": str(category),
            "alias": _identifier(item.get("alias"), "unit_alias.alias"),
            "canonical_unit": _identifier(
                item.get("canonical_unit"),
                "unit_alias.canonical_unit",
            ),
        }
    pattern = _text(item.get("pattern"), "unit_pattern.pattern")
    try:
        re.compile(pattern)
    except re.error as exc:
        raise NDPVocabularyWorkflowError(
            f"unit_pattern.pattern is invalid: {exc}"
        ) from exc
    return {
        "category": str(category),
        "pattern": pattern,
        "meaning": _text(item.get("meaning"), "unit_pattern.meaning"),
    }


def _candidate_id(payload: Mapping[str, Any]) -> str:
    return "vocab-" + _sha256_payload(payload)[:20]


def build_discovery_template(
    *,
    draft_vocabulary_path: Path,
    source_bundle_manifest_path: Path,
    implementation_file: Path,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    draft = _load_json(draft_vocabulary_path)
    if (
        draft.get("schema_version") != "semantic-annotation-vocabulary/v1"
        or draft.get("status") != "draft"
    ):
        raise NDPVocabularyWorkflowError(
            "vocabulary discovery requires the NDP draft vocabulary"
        )
    registry, bundle_binding, _ = load_evidence_registry(
        source_bundle_manifest_path,
        require_approved=False,
    )
    case_ids = sorted(registry)
    template = {
        "schema_version": DISCOVERY_SCHEMA_VERSION,
        "annotation_stage": "independent_pre_annotation_discovery",
        "reviewer_id": "replace-with-pseudonymous-non-developer-id",
        "reviewer_role": "replace-with-qualified-reviewer-role",
        "qualification_summary": None,
        "conflict_of_interest_declared": None,
        "submission_id": "replace-with-stable-unique-id",
        "developer_participation": False,
        "model_outputs_visible": False,
        "other_review_visible_before_freeze": False,
        "draft_vocabulary": _binding(draft_vocabulary_path),
        "source_bundle_manifest": bundle_binding,
        "existing_vocabulary": {
            "logical_types": draft["logical_types"],
            "semantic_types": draft["semantic_types"],
            "units": draft["units"],
            "unit_aliases": draft["unit_aliases"],
            "unit_patterns": draft["unit_patterns"],
        },
        "policy_decisions": {key: None for key in POLICY_KEYS},
        "policy_rationale": None,
        "case_reviews": [
            {
                "case_id": case_id,
                "coverage_adequate": None,
                "concepts_missing": [],
                "rationale": None,
                "evidence_refs": [],
            }
            for case_id in case_ids
        ],
        "proposals": [],
        "completion_attestation": None,
    }
    workflow = {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "status": "ready_for_independent_vocabulary_discovery",
        "draft_vocabulary": _binding(draft_vocabulary_path),
        "source_bundle_manifest": bundle_binding,
        "neutral_discovery_template_canonical_sha256": _sha256_payload(
            template
        ),
        "implementation": {
            "file": implementation_file.name,
            "sha256": _sha256_file(implementation_file),
        },
        "implementation_dependencies": {
            path.name: _sha256_file(path)
            for path in (
                implementation_file.with_name(
                    "ndp50_cpa_screen_workflow.py"
                ),
                implementation_file.with_name("semantic_gold_workflow.py"),
            )
        },
        "case_count": len(case_ids),
        "required_discovery_reviewers": 2,
        "required_candidate_decision_reviewers": 2,
        "candidate_decision_reviewers_fresh_from_discovery": True,
        "required_consensus_adjudicators": 1,
        "consensus_adjudicator_fresh_from_prior_stages": True,
        "consensus_adjudicator_qualification_and_conflict_required": True,
        "required_role_coverage": [
            "one_domain_or_scientific_metadata_curator",
            "one_annotation_methodologist",
        ],
        "developer_participation": False,
        "model_outputs_visible": False,
        "human_decisions_present": False,
        "sequence": [
            "two_independent_full_corpus_discovery_reviews",
            "deterministic_union_candidate_catalog",
            "two_independent_candidate_and_policy_decisions",
            "disagreement_reveal_after_both_decisions_freeze",
            "human_consensus",
            "validator_generated_frozen_vocabulary",
            "rebuild_source_bundles_against_frozen_vocabulary",
        ],
    }
    return template, workflow


def _case_map(
    value: Any,
    *,
    label: str,
) -> tuple[list[str], Dict[str, Mapping[str, Any]]]:
    if not isinstance(value, list) or not value:
        raise NDPVocabularyWorkflowError(f"{label} must be a non-empty list")
    order = []
    mapped = {}
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise NDPVocabularyWorkflowError(
                f"{label}[{index}] must be an object"
            )
        case_id = _identifier(item.get("case_id"), f"{label}[{index}].case_id")
        if case_id in mapped:
            raise NDPVocabularyWorkflowError(
                f"{label} contains duplicate case {case_id}"
            )
        order.append(case_id)
        mapped[case_id] = item
    return order, mapped


def validate_discovery(
    submission: Mapping[str, Any],
    template: Mapping[str, Any],
    *,
    evidence_registry: Mapping[
        str, Mapping[str, Mapping[str, Any]]
    ],
    submission_sha256: str | None = None,
) -> Dict[str, Any]:
    if template.get("schema_version") != DISCOVERY_SCHEMA_VERSION:
        raise NDPVocabularyWorkflowError("unexpected discovery template schema")
    for key in (
        "schema_version",
        "annotation_stage",
        "developer_participation",
        "model_outputs_visible",
        "other_review_visible_before_freeze",
        "draft_vocabulary",
        "source_bundle_manifest",
        "existing_vocabulary",
    ):
        if submission.get(key) != template.get(key):
            raise NDPVocabularyWorkflowError(
                f"discovery submission mutates frozen field {key}"
            )
    reviewer_id = _identifier(submission.get("reviewer_id"), "reviewer_id")
    reviewer_role = _identifier(
        submission.get("reviewer_role"), "reviewer_role"
    )
    if reviewer_role not in REVIEWER_ROLES:
        raise NDPVocabularyWorkflowError(
            f"unsupported reviewer_role {reviewer_role!r}"
        )
    _text(
        submission.get("qualification_summary"),
        "qualification_summary",
    )
    if submission.get("conflict_of_interest_declared") is not False:
        raise NDPVocabularyWorkflowError(
            "conflict_of_interest_declared must be false"
        )
    submission_id = _identifier(
        submission.get("submission_id"), "submission_id"
    )
    policies = submission.get("policy_decisions")
    if not isinstance(policies, Mapping) or set(policies) != set(POLICY_KEYS):
        raise NDPVocabularyWorkflowError(
            "policy_decisions must contain the exact frozen policy keys"
        )
    if any(not isinstance(policies[key], bool) for key in POLICY_KEYS):
        raise NDPVocabularyWorkflowError("all policy decisions must be boolean")
    _text(submission.get("policy_rationale"), "policy_rationale")

    expected_order, _ = _case_map(
        template.get("case_reviews"), label="template.case_reviews"
    )
    submitted_order, reviews = _case_map(
        submission.get("case_reviews"), label="submission.case_reviews"
    )
    if submitted_order != expected_order:
        raise NDPVocabularyWorkflowError(
            "case-review identity/order differs from the neutral template"
        )
    for case_id in expected_order:
        review = reviews[case_id]
        if not isinstance(review.get("coverage_adequate"), bool):
            raise NDPVocabularyWorkflowError(
                f"case {case_id}.coverage_adequate must be boolean"
            )
        missing = review.get("concepts_missing")
        if (
            not isinstance(missing, list)
            or any(not isinstance(item, str) or not item.strip() for item in missing)
            or len(missing) != len(set(missing))
        ):
            raise NDPVocabularyWorkflowError(
                f"case {case_id}.concepts_missing is invalid"
            )
        if review["coverage_adequate"] and missing:
            raise NDPVocabularyWorkflowError(
                f"case {case_id} cannot be adequate with missing concepts"
            )
        if not review["coverage_adequate"] and not missing:
            raise NDPVocabularyWorkflowError(
                f"case {case_id} needs explicit missing concepts"
            )
        _text(review.get("rationale"), f"case {case_id}.rationale")
        _evidence_refs(
            review.get("evidence_refs"),
            label=f"case {case_id}.evidence_refs",
            registry=evidence_registry,
            required_case_id=case_id,
        )

    proposals = submission.get("proposals")
    if not isinstance(proposals, list):
        raise NDPVocabularyWorkflowError("proposals must be a list")
    proposal_ids = set()
    normalized_proposals = []
    for index, item in enumerate(proposals):
        if not isinstance(item, Mapping):
            raise NDPVocabularyWorkflowError(
                f"proposals[{index}] must be an object"
            )
        payload = _proposal_payload(item)
        existing = template["existing_vocabulary"]
        if (
            payload["category"] == "semantic_type"
            and payload["term"] in existing["semantic_types"]
        ):
            raise NDPVocabularyWorkflowError(
                f"proposal {payload['term']} already exists"
            )
        if (
            payload["category"] == "unit"
            and payload["term"] in existing["units"]
        ):
            raise NDPVocabularyWorkflowError(
                f"proposal {payload['term']} already exists"
            )
        if (
            payload["category"] == "unit_alias"
            and payload["alias"] in existing["unit_aliases"]
        ):
            raise NDPVocabularyWorkflowError(
                f"proposal alias {payload['alias']} already exists"
            )
        if payload["category"] == "unit_pattern" and {
            "pattern": payload["pattern"],
            "meaning": payload["meaning"],
        } in existing["unit_patterns"]:
            raise NDPVocabularyWorkflowError(
                "proposed unit pattern already exists"
            )
        candidate_id = _candidate_id(payload)
        if candidate_id in proposal_ids:
            raise NDPVocabularyWorkflowError("duplicate vocabulary proposal")
        proposal_ids.add(candidate_id)
        normalized_proposals.append(payload)
        _text(item.get("rationale"), f"proposal {candidate_id}.rationale")
        _evidence_refs(
            item.get("evidence_refs"),
            label=f"proposal {candidate_id}.evidence_refs",
            registry=evidence_registry,
        )
    if submission.get("completion_attestation") is not True:
        raise NDPVocabularyWorkflowError(
            "completion_attestation must be true"
        )
    return {
        "schema_version": "ndp50-vocabulary-discovery-validation/v1",
        "status": "passed",
        "reviewer_id": reviewer_id,
        "reviewer_role": reviewer_role,
        "submission_id": submission_id,
        "submission_sha256": submission_sha256
        or _sha256_payload(submission),
        "case_count": len(expected_order),
        "proposal_count": len(proposals),
    }


def build_candidate_catalog(
    discovery_a: Mapping[str, Any],
    discovery_b: Mapping[str, Any],
    template: Mapping[str, Any],
    *,
    evidence_registry: Mapping[
        str, Mapping[str, Mapping[str, Any]]
    ],
    discovery_a_sha256: str | None = None,
    discovery_b_sha256: str | None = None,
) -> Dict[str, Any]:
    report_a = validate_discovery(
        discovery_a,
        template,
        evidence_registry=evidence_registry,
        submission_sha256=discovery_a_sha256,
    )
    report_b = validate_discovery(
        discovery_b,
        template,
        evidence_registry=evidence_registry,
        submission_sha256=discovery_b_sha256,
    )
    if report_a["reviewer_id"] == report_b["reviewer_id"]:
        raise NDPVocabularyWorkflowError(
            "discovery submissions require distinct reviewers"
        )
    if report_a["submission_id"] == report_b["submission_id"]:
        raise NDPVocabularyWorkflowError(
            "discovery submissions require distinct submission IDs"
        )
    roles = {report_a["reviewer_role"], report_b["reviewer_role"]}
    if not (roles & CURATOR_ROLES) or "annotation_methodologist" not in roles:
        raise NDPVocabularyWorkflowError(
            "discovery review pair must include a curator and an annotation methodologist"
        )
    union: Dict[str, Dict[str, Any]] = {}
    for label, discovery, report in (
        ("a", discovery_a, report_a),
        ("b", discovery_b, report_b),
    ):
        for proposal in discovery["proposals"]:
            payload = _proposal_payload(proposal)
            candidate_id = _candidate_id(payload)
            entry = union.setdefault(
                candidate_id,
                {
                    "candidate_id": candidate_id,
                    "proposal": payload,
                    "proposed_by": [],
                    "discovery_evidence_refs": [],
                },
            )
            entry["proposed_by"].append(label)
            for ref in proposal["evidence_refs"]:
                normalized = {
                    "case_id": ref["case_id"],
                    "catalog_evidence_id": ref["catalog_evidence_id"],
                }
                if normalized not in entry["discovery_evidence_refs"]:
                    entry["discovery_evidence_refs"].append(normalized)
    candidates = [
        {
            **entry,
            "proposed_by": sorted(entry["proposed_by"]),
            "discovery_evidence_refs": sorted(
                entry["discovery_evidence_refs"],
                key=lambda item: (
                    item["case_id"],
                    item["catalog_evidence_id"],
                ),
            ),
        }
        for _, entry in sorted(union.items())
    ]
    case_findings = []
    reviews_a = {
        item["case_id"]: item for item in discovery_a["case_reviews"]
    }
    reviews_b = {
        item["case_id"]: item for item in discovery_b["case_reviews"]
    }
    for case_id in sorted(reviews_a):
        case_findings.append(
            {
                "case_id": case_id,
                "review_a": {
                    key: reviews_a[case_id][key]
                    for key in (
                        "coverage_adequate",
                        "concepts_missing",
                        "rationale",
                        "evidence_refs",
                    )
                },
                "review_b": {
                    key: reviews_b[case_id][key]
                    for key in (
                        "coverage_adequate",
                        "concepts_missing",
                        "rationale",
                        "evidence_refs",
                    )
                },
            }
        )
    return {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "status": "ready_for_independent_candidate_decisions",
        "draft_vocabulary": template["draft_vocabulary"],
        "source_bundle_manifest": template["source_bundle_manifest"],
        "discovery_template_sha256": _sha256_payload(template),
        "discovery_a": {
            key: report_a[key]
            for key in (
                "reviewer_id",
                "reviewer_role",
                "submission_id",
                "submission_sha256",
            )
        },
        "discovery_b": {
            key: report_b[key]
            for key in (
                "reviewer_id",
                "reviewer_role",
                "submission_id",
                "submission_sha256",
            )
        },
        "candidate_count": len(candidates),
        "case_count": len(case_findings),
        "case_coverage_findings": case_findings,
        "candidates": candidates,
        "automatic_acceptance": False,
    }


def build_decision_template(catalog: Mapping[str, Any]) -> Dict[str, Any]:
    if catalog.get("schema_version") != CANDIDATE_SCHEMA_VERSION:
        raise NDPVocabularyWorkflowError("unexpected candidate catalog schema")
    return {
        "schema_version": DECISION_SCHEMA_VERSION,
        "annotation_stage": "independent_candidate_and_policy_decision",
        "reviewer_id": "replace-with-pseudonymous-non-developer-id",
        "reviewer_role": "replace-with-qualified-reviewer-role",
        "qualification_summary": None,
        "conflict_of_interest_declared": None,
        "submission_id": "replace-with-stable-unique-id",
        "developer_participation": False,
        "model_outputs_visible": False,
        "other_decision_visible_before_freeze": False,
        "candidate_catalog_sha256": _sha256_payload(catalog),
        "policy_decisions": {key: None for key in POLICY_KEYS},
        "corpus_coverage_adequate_after_decisions": None,
        "policy_rationale": None,
        "candidate_decisions": [
            {
                "candidate_id": item["candidate_id"],
                "approved": None,
                "rationale": None,
                "evidence_refs": [],
            }
            for item in catalog["candidates"]
        ],
        "completion_attestation": None,
    }


def _candidate_map(
    value: Any,
    *,
    label: str,
) -> tuple[list[str], Dict[str, Mapping[str, Any]]]:
    if not isinstance(value, list):
        raise NDPVocabularyWorkflowError(f"{label} must be a list")
    order = []
    mapped = {}
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise NDPVocabularyWorkflowError(
                f"{label}[{index}] must be an object"
            )
        candidate_id = _identifier(
            item.get("candidate_id"),
            f"{label}[{index}].candidate_id",
        )
        if candidate_id in mapped:
            raise NDPVocabularyWorkflowError(
                f"{label} contains duplicate candidate {candidate_id}"
            )
        order.append(candidate_id)
        mapped[candidate_id] = item
    return order, mapped


def validate_decision(
    submission: Mapping[str, Any],
    catalog: Mapping[str, Any],
    *,
    evidence_registry: Mapping[
        str, Mapping[str, Mapping[str, Any]]
    ],
    submission_sha256: str | None = None,
) -> Dict[str, Any]:
    template = build_decision_template(catalog)
    for key in (
        "schema_version",
        "annotation_stage",
        "developer_participation",
        "model_outputs_visible",
        "other_decision_visible_before_freeze",
        "candidate_catalog_sha256",
    ):
        if submission.get(key) != template.get(key):
            raise NDPVocabularyWorkflowError(
                f"decision submission mutates frozen field {key}"
            )
    reviewer_id = _identifier(submission.get("reviewer_id"), "reviewer_id")
    reviewer_role = _identifier(
        submission.get("reviewer_role"), "reviewer_role"
    )
    if reviewer_role not in REVIEWER_ROLES:
        raise NDPVocabularyWorkflowError(
            f"unsupported reviewer_role {reviewer_role!r}"
        )
    _text(
        submission.get("qualification_summary"),
        "qualification_summary",
    )
    if submission.get("conflict_of_interest_declared") is not False:
        raise NDPVocabularyWorkflowError(
            "conflict_of_interest_declared must be false"
        )
    submission_id = _identifier(
        submission.get("submission_id"), "submission_id"
    )
    policies = submission.get("policy_decisions")
    if not isinstance(policies, Mapping) or set(policies) != set(POLICY_KEYS):
        raise NDPVocabularyWorkflowError("decision policy keys differ")
    if any(not isinstance(policies[key], bool) for key in POLICY_KEYS):
        raise NDPVocabularyWorkflowError(
            "decision policies must all be boolean"
        )
    if not isinstance(
        submission.get("corpus_coverage_adequate_after_decisions"), bool
    ):
        raise NDPVocabularyWorkflowError(
            "corpus coverage decision must be boolean"
        )
    _text(submission.get("policy_rationale"), "policy_rationale")
    expected_order = [
        item["candidate_id"] for item in catalog.get("candidates", [])
    ]
    order, decisions = _candidate_map(
        submission.get("candidate_decisions"),
        label="candidate_decisions",
    )
    if order != expected_order:
        raise NDPVocabularyWorkflowError(
            "candidate decision order/identity differs from catalog"
        )
    for candidate_id in order:
        decision = decisions[candidate_id]
        if not isinstance(decision.get("approved"), bool):
            raise NDPVocabularyWorkflowError(
                f"candidate {candidate_id}.approved must be boolean"
            )
        _text(
            decision.get("rationale"),
            f"candidate {candidate_id}.rationale",
        )
        _evidence_refs(
            decision.get("evidence_refs"),
            label=f"candidate {candidate_id}.evidence_refs",
            registry=evidence_registry,
        )
    if submission.get("completion_attestation") is not True:
        raise NDPVocabularyWorkflowError(
            "completion_attestation must be true"
        )
    return {
        "schema_version": "ndp50-vocabulary-decision-validation/v1",
        "status": "passed",
        "reviewer_id": reviewer_id,
        "reviewer_role": reviewer_role,
        "submission_id": submission_id,
        "submission_sha256": submission_sha256
        or _sha256_payload(submission),
        "candidate_count": len(order),
    }


def _decision_slots(
    decision: Mapping[str, Any],
) -> Dict[str, bool]:
    slots = {
        f"policy:{key}": decision["policy_decisions"][key]
        for key in POLICY_KEYS
    }
    slots["coverage:corpus"] = decision[
        "corpus_coverage_adequate_after_decisions"
    ]
    slots.update(
        {
            f"candidate:{item['candidate_id']}": item["approved"]
            for item in decision["candidate_decisions"]
        }
    )
    return slots


def compare_decisions(
    decision_a: Mapping[str, Any],
    decision_b: Mapping[str, Any],
    catalog: Mapping[str, Any],
    *,
    evidence_registry: Mapping[
        str, Mapping[str, Mapping[str, Any]]
    ],
    decision_a_sha256: str | None = None,
    decision_b_sha256: str | None = None,
) -> Dict[str, Any]:
    report_a = validate_decision(
        decision_a,
        catalog,
        evidence_registry=evidence_registry,
        submission_sha256=decision_a_sha256,
    )
    report_b = validate_decision(
        decision_b,
        catalog,
        evidence_registry=evidence_registry,
        submission_sha256=decision_b_sha256,
    )
    if report_a["reviewer_id"] == report_b["reviewer_id"]:
        raise NDPVocabularyWorkflowError(
            "candidate decisions require distinct reviewers"
        )
    if report_a["submission_id"] == report_b["submission_id"]:
        raise NDPVocabularyWorkflowError(
            "candidate decisions require distinct submission IDs"
        )
    discovery_reviewers = {
        catalog.get("discovery_a", {}).get("reviewer_id"),
        catalog.get("discovery_b", {}).get("reviewer_id"),
    }
    decision_reviewers = {
        report_a["reviewer_id"],
        report_b["reviewer_id"],
    }
    reused = {
        reviewer
        for reviewer in discovery_reviewers.intersection(decision_reviewers)
        if reviewer
    }
    if reused:
        raise NDPVocabularyWorkflowError(
            "candidate decisions require reviewers fresh from discovery"
        )
    roles = {report_a["reviewer_role"], report_b["reviewer_role"]}
    if not (roles & CURATOR_ROLES) or "annotation_methodologist" not in roles:
        raise NDPVocabularyWorkflowError(
            "candidate decision pair must include a curator and an annotation methodologist"
        )
    slots_a = _decision_slots(decision_a)
    slots_b = _decision_slots(decision_b)
    if set(slots_a) != set(slots_b):
        raise NDPVocabularyWorkflowError("candidate decision slots differ")
    slots = []
    for slot_id in sorted(slots_a):
        agreed = slots_a[slot_id] == slots_b[slot_id]
        slots.append(
            {
                "slot_id": slot_id,
                "value_a": slots_a[slot_id],
                "value_b": slots_b[slot_id],
                "agreed": agreed,
                "status": (
                    "agreed" if agreed else "pending_human_adjudication"
                ),
            }
        )
    disagreement_count = sum(not item["agreed"] for item in slots)
    return {
        "schema_version": DISAGREEMENT_SCHEMA_VERSION,
        "status": (
            "ready_for_human_adjudication"
            if disagreement_count
            else "no_disagreements_consensus_documentation_required"
        ),
        "candidate_catalog_sha256": _sha256_payload(catalog),
        "decision_a": {
            key: report_a[key]
            for key in (
                "reviewer_id",
                "reviewer_role",
                "submission_id",
                "submission_sha256",
            )
        },
        "decision_b": {
            key: report_b[key]
            for key in (
                "reviewer_id",
                "reviewer_role",
                "submission_id",
                "submission_sha256",
            )
        },
        "slot_count": len(slots),
        "agreement_count": len(slots) - disagreement_count,
        "disagreement_count": disagreement_count,
        "slots": slots,
        "automatic_adjudication": False,
    }


def build_consensus_template(
    worksheet: Mapping[str, Any],
    *,
    worksheet_sha256: str | None = None,
) -> Dict[str, Any]:
    if worksheet.get("schema_version") != DISAGREEMENT_SCHEMA_VERSION:
        raise NDPVocabularyWorkflowError("unexpected disagreement schema")
    values = {
        item["slot_id"]: (
            item["value_a"] if item["agreed"] else None
        )
        for item in worksheet["slots"]
    }
    return {
        "schema_version": CONSENSUS_SCHEMA_VERSION,
        "status": "pending_human_consensus",
        "annotation_stage": "post_freeze_human_consensus",
        "adjudicator_id": "replace-with-pseudonymous-id",
        "adjudicator_role": "replace-with-qualified-adjudicator-role",
        "qualification_summary": None,
        "conflict_of_interest_declared": None,
        "developer_participation": False,
        "prior_stage_participation": False,
        "candidate_catalog_sha256": worksheet[
            "candidate_catalog_sha256"
        ],
        "decision_a": worksheet["decision_a"],
        "decision_b": worksheet["decision_b"],
        "disagreement_worksheet_sha256": worksheet_sha256
        or _sha256_payload(worksheet),
        "automatic_adjudication": False,
        "slot_values": values,
        "slot_rationales": {slot_id: None for slot_id in values},
        "slot_evidence_refs": {slot_id: [] for slot_id in values},
        "resolutions": [
            {
                "slot_id": item["slot_id"],
                "selected_value": None,
                "rationale": None,
                "evidence_refs": [],
            }
            for item in worksheet["slots"]
            if not item["agreed"]
        ],
        "completion_attestation": None,
    }


def validate_consensus(
    consensus: Mapping[str, Any],
    decision_a: Mapping[str, Any],
    decision_b: Mapping[str, Any],
    catalog: Mapping[str, Any],
    worksheet: Mapping[str, Any],
    *,
    evidence_registry: Mapping[
        str, Mapping[str, Mapping[str, Any]]
    ],
    decision_a_sha256: str | None = None,
    decision_b_sha256: str | None = None,
    worksheet_sha256: str | None = None,
    consensus_sha256: str | None = None,
) -> Dict[str, Any]:
    expected = compare_decisions(
        decision_a,
        decision_b,
        catalog,
        evidence_registry=evidence_registry,
        decision_a_sha256=decision_a_sha256,
        decision_b_sha256=decision_b_sha256,
    )
    if worksheet != expected:
        raise NDPVocabularyWorkflowError(
            "worksheet is not the deterministic comparison of submissions"
        )
    if consensus.get("schema_version") != CONSENSUS_SCHEMA_VERSION:
        raise NDPVocabularyWorkflowError("unexpected consensus schema")
    if consensus.get("status") != "consensus_frozen":
        raise NDPVocabularyWorkflowError(
            "consensus status must be consensus_frozen"
        )
    if consensus.get("annotation_stage") != "post_freeze_human_consensus":
        raise NDPVocabularyWorkflowError("unexpected consensus stage")
    if consensus.get("automatic_adjudication") is not False:
        raise NDPVocabularyWorkflowError("automatic adjudication is forbidden")
    adjudicator_id = _identifier(
        consensus.get("adjudicator_id"), "adjudicator_id"
    )
    adjudicator_role = _identifier(
        consensus.get("adjudicator_role"), "adjudicator_role"
    )
    if adjudicator_role not in CONSENSUS_ADJUDICATOR_ROLES:
        raise NDPVocabularyWorkflowError(
            f"unsupported adjudicator_role {adjudicator_role!r}"
        )
    _text(consensus.get("qualification_summary"), "qualification_summary")
    if consensus.get("conflict_of_interest_declared") is not False:
        raise NDPVocabularyWorkflowError(
            "consensus adjudicator must declare no unresolved conflict"
        )
    if consensus.get("developer_participation") is not False:
        raise NDPVocabularyWorkflowError(
            "consensus adjudicator must be a non-developer"
        )
    if consensus.get("prior_stage_participation") is not False:
        raise NDPVocabularyWorkflowError(
            "consensus adjudicator must be fresh from discovery and decisions"
        )
    prior_reviewer_ids = {
        catalog.get("discovery_a", {}).get("reviewer_id"),
        catalog.get("discovery_b", {}).get("reviewer_id"),
        expected.get("decision_a", {}).get("reviewer_id"),
        expected.get("decision_b", {}).get("reviewer_id"),
    }
    if adjudicator_id in prior_reviewer_ids:
        raise NDPVocabularyWorkflowError(
            "consensus adjudicator must be distinct from prior reviewers"
        )
    for key in ("candidate_catalog_sha256", "decision_a", "decision_b"):
        if consensus.get(key) != expected.get(key):
            raise NDPVocabularyWorkflowError(
                f"consensus mutates frozen binding {key}"
            )
    expected_worksheet_hash = worksheet_sha256 or _sha256_payload(worksheet)
    if (
        consensus.get("disagreement_worksheet_sha256")
        != expected_worksheet_hash
    ):
        raise NDPVocabularyWorkflowError(
            "consensus does not bind the exact worksheet"
        )
    values = consensus.get("slot_values")
    rationales = consensus.get("slot_rationales")
    evidence = consensus.get("slot_evidence_refs")
    expected_ids = [item["slot_id"] for item in worksheet["slots"]]
    if (
        not isinstance(values, Mapping)
        or set(values) != set(expected_ids)
        or not isinstance(rationales, Mapping)
        or set(rationales) != set(expected_ids)
        or not isinstance(evidence, Mapping)
        or set(evidence) != set(expected_ids)
    ):
        raise NDPVocabularyWorkflowError(
            "consensus slot maps must cover the exact worksheet slots"
        )
    resolutions = consensus.get("resolutions")
    if not isinstance(resolutions, list):
        raise NDPVocabularyWorkflowError("resolutions must be a list")
    resolution_map = {}
    for item in resolutions:
        if not isinstance(item, Mapping):
            raise NDPVocabularyWorkflowError("resolution must be an object")
        slot_id = str(item.get("slot_id") or "")
        if not slot_id or slot_id in resolution_map:
            raise NDPVocabularyWorkflowError(
                "resolution slot IDs must be unique"
            )
        resolution_map[slot_id] = item
    disagreement_ids = {
        item["slot_id"] for item in worksheet["slots"] if not item["agreed"]
    }
    if set(resolution_map) != disagreement_ids:
        raise NDPVocabularyWorkflowError(
            "every and only disagreement requires a resolution"
        )
    for item in worksheet["slots"]:
        slot_id = item["slot_id"]
        value = values[slot_id]
        if not isinstance(value, bool):
            raise NDPVocabularyWorkflowError(
                f"consensus slot {slot_id} must be boolean"
            )
        if item["agreed"] and value != item["value_a"]:
            raise NDPVocabularyWorkflowError(
                f"consensus mutates agreed slot {slot_id}"
            )
        if not item["agreed"]:
            resolution = resolution_map[slot_id]
            if resolution.get("selected_value") is not value:
                raise NDPVocabularyWorkflowError(
                    f"resolution differs from final slot {slot_id}"
                )
            _text(
                resolution.get("rationale"),
                f"resolution {slot_id}.rationale",
            )
            _evidence_refs(
                resolution.get("evidence_refs"),
                label=f"resolution {slot_id}.evidence_refs",
                registry=evidence_registry,
            )
        _text(rationales[slot_id], f"slot {slot_id}.rationale")
        _evidence_refs(
            evidence[slot_id],
            label=f"slot {slot_id}.evidence_refs",
            registry=evidence_registry,
        )
    if consensus.get("completion_attestation") is not True:
        raise NDPVocabularyWorkflowError(
            "consensus completion_attestation must be true"
        )
    return {
        "schema_version": CONSENSUS_VALIDATION_SCHEMA_VERSION,
        "status": "passed",
        "adjudicator_id": adjudicator_id,
        "adjudicator_role": adjudicator_role,
        "adjudicator_independent_of_prior_stages": True,
        "consensus_sha256": consensus_sha256 or _sha256_payload(consensus),
        "worksheet_sha256": expected_worksheet_hash,
        "slot_count": len(expected_ids),
        "disagreement_count": len(disagreement_ids),
        "all_required_policies_accepted": all(
            values[f"policy:{key}"] for key in POLICY_KEYS
        ),
        "corpus_coverage_accepted": values["coverage:corpus"],
    }


def build_frozen_vocabulary(
    draft: Mapping[str, Any],
    catalog: Mapping[str, Any],
    consensus: Mapping[str, Any],
    decision_a: Mapping[str, Any],
    decision_b: Mapping[str, Any],
    worksheet: Mapping[str, Any],
    *,
    evidence_registry: Mapping[
        str, Mapping[str, Mapping[str, Any]]
    ],
    draft_sha256: str,
    decision_a_sha256: str | None = None,
    decision_b_sha256: str | None = None,
    worksheet_sha256: str | None = None,
    consensus_sha256: str | None = None,
) -> Dict[str, Any]:
    if (
        draft.get("schema_version") != "semantic-annotation-vocabulary/v1"
        or draft.get("status") != "draft"
    ):
        raise NDPVocabularyWorkflowError(
            "freeze requires the bound draft vocabulary"
        )
    if catalog.get("draft_vocabulary", {}).get("sha256") != draft_sha256:
        raise NDPVocabularyWorkflowError(
            "candidate catalog does not bind the supplied draft vocabulary"
        )
    consensus_validation = validate_consensus(
        consensus,
        decision_a,
        decision_b,
        catalog,
        worksheet,
        evidence_registry=evidence_registry,
        decision_a_sha256=decision_a_sha256,
        decision_b_sha256=decision_b_sha256,
        worksheet_sha256=worksheet_sha256,
        consensus_sha256=consensus_sha256,
    )
    if not consensus_validation.get("all_required_policies_accepted"):
        raise NDPVocabularyWorkflowError(
            "all required vocabulary policies must be accepted"
        )
    if not consensus_validation.get("corpus_coverage_accepted"):
        raise NDPVocabularyWorkflowError(
            "corpus coverage must be accepted before vocabulary freeze"
        )
    catalog_sha256 = _sha256_payload(catalog)
    if consensus.get("candidate_catalog_sha256") != catalog_sha256:
        raise NDPVocabularyWorkflowError(
            "consensus does not bind the supplied candidate catalog"
        )
    values = consensus["slot_values"]
    approved = [
        item["proposal"]
        for item in catalog["candidates"]
        if values[f"candidate:{item['candidate_id']}"]
    ]
    frozen = copy.deepcopy(dict(draft))
    frozen["status"] = "frozen"
    frozen["research_evidence_status"] = (
        "ndp50_pre_model_two_reviewer_consensus"
    )
    frozen["vocabulary_version"] = "ndp50-v1"
    frozen.pop("freeze_blockers", None)
    frozen["extension_policy"] = (
        "Frozen before annotation. Applicable out-of-vocabulary values use "
        "JSON null; no post-freeze label invention or extension is permitted."
    )
    frozen["curation_provenance"] = {
        "draft_vocabulary_sha256": draft_sha256,
        "candidate_catalog_sha256": catalog_sha256,
        "consensus_sha256": consensus_validation["consensus_sha256"],
        "worksheet_sha256": consensus_validation["worksheet_sha256"],
        "approved_candidate_count": len(approved),
        "automatic_acceptance": False,
    }
    for proposal in approved:
        category = proposal["category"]
        if category == "semantic_type":
            frozen["semantic_types"].append(proposal["term"])
        elif category == "unit":
            frozen["units"].append(proposal["term"])
        elif category == "unit_alias":
            alias = proposal["alias"]
            if alias in frozen["unit_aliases"]:
                raise NDPVocabularyWorkflowError(
                    f"approved duplicate unit alias {alias}"
                )
            frozen["unit_aliases"][alias] = proposal["canonical_unit"]
        else:
            frozen["unit_patterns"].append(
                {
                    "pattern": proposal["pattern"],
                    "meaning": proposal["meaning"],
                }
            )
    for key in ("semantic_types", "units"):
        frozen[key] = sorted(set(frozen[key]))
    if validate_vocabulary(frozen)["status"] != "ready":
        raise NDPVocabularyWorkflowError(
            f"generated vocabulary is invalid: {validate_vocabulary(frozen)['errors']}"
        )
    return frozen


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and validate the NDP-50 vocabulary freeze workflow."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--draft-vocabulary", type=Path, required=True)
    prepare.add_argument("--source-bundle-manifest", type=Path, required=True)
    prepare.add_argument("--template-output", type=Path, required=True)
    prepare.add_argument("--workflow-output", type=Path, required=True)

    validate_discovery_parser = subparsers.add_parser("validate-discovery")
    validate_discovery_parser.add_argument(
        "--submission", type=Path, required=True
    )
    validate_discovery_parser.add_argument("--template", type=Path, required=True)
    validate_discovery_parser.add_argument(
        "--source-bundle-manifest", type=Path, required=True
    )
    validate_discovery_parser.add_argument("--output", type=Path, required=True)

    candidates = subparsers.add_parser("build-candidates")
    candidates.add_argument("--discovery-a", type=Path, required=True)
    candidates.add_argument("--discovery-b", type=Path, required=True)
    candidates.add_argument("--template", type=Path, required=True)
    candidates.add_argument(
        "--source-bundle-manifest", type=Path, required=True
    )
    candidates.add_argument("--output", type=Path, required=True)

    decision_template = subparsers.add_parser("build-decision-template")
    decision_template.add_argument("--catalog", type=Path, required=True)
    decision_template.add_argument("--output", type=Path, required=True)

    validate_decision_parser = subparsers.add_parser("validate-decision")
    validate_decision_parser.add_argument(
        "--submission", type=Path, required=True
    )
    validate_decision_parser.add_argument("--catalog", type=Path, required=True)
    validate_decision_parser.add_argument(
        "--source-bundle-manifest", type=Path, required=True
    )
    validate_decision_parser.add_argument("--output", type=Path, required=True)

    compare = subparsers.add_parser("compare")
    compare.add_argument("--decision-a", type=Path, required=True)
    compare.add_argument("--decision-b", type=Path, required=True)
    compare.add_argument("--catalog", type=Path, required=True)
    compare.add_argument("--source-bundle-manifest", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)

    consensus_template = subparsers.add_parser("build-consensus-template")
    consensus_template.add_argument("--worksheet", type=Path, required=True)
    consensus_template.add_argument("--output", type=Path, required=True)

    validate_consensus_parser = subparsers.add_parser("validate-consensus")
    validate_consensus_parser.add_argument(
        "--consensus", type=Path, required=True
    )
    validate_consensus_parser.add_argument(
        "--decision-a", type=Path, required=True
    )
    validate_consensus_parser.add_argument(
        "--decision-b", type=Path, required=True
    )
    validate_consensus_parser.add_argument(
        "--catalog", type=Path, required=True
    )
    validate_consensus_parser.add_argument(
        "--worksheet", type=Path, required=True
    )
    validate_consensus_parser.add_argument(
        "--source-bundle-manifest", type=Path, required=True
    )
    validate_consensus_parser.add_argument("--output", type=Path, required=True)

    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("--draft-vocabulary", type=Path, required=True)
    freeze.add_argument("--catalog", type=Path, required=True)
    freeze.add_argument("--decision-a", type=Path, required=True)
    freeze.add_argument("--decision-b", type=Path, required=True)
    freeze.add_argument("--worksheet", type=Path, required=True)
    freeze.add_argument("--consensus", type=Path, required=True)
    freeze.add_argument("--source-bundle-manifest", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        template, workflow = build_discovery_template(
            draft_vocabulary_path=args.draft_vocabulary,
            source_bundle_manifest_path=args.source_bundle_manifest,
            implementation_file=Path(__file__),
        )
        _write_json(args.template_output, template)
        workflow["neutral_discovery_template"] = _binding(
            args.template_output
        )
        _write_json(args.workflow_output, workflow)
        payload = workflow
    elif args.command == "build-decision-template":
        payload = build_decision_template(_load_json(args.catalog))
        _write_json(args.output, payload)
    elif args.command == "build-consensus-template":
        payload = build_consensus_template(
            _load_json(args.worksheet),
            worksheet_sha256=_sha256_file(args.worksheet),
        )
        _write_json(args.output, payload)
    else:
        evidence_registry, _, _ = load_evidence_registry(
            args.source_bundle_manifest,
            require_approved=False,
        )
        if args.command == "validate-discovery":
            payload = validate_discovery(
                _load_json(args.submission),
                _load_json(args.template),
                evidence_registry=evidence_registry,
                submission_sha256=_sha256_file(args.submission),
            )
        elif args.command == "build-candidates":
            payload = build_candidate_catalog(
                _load_json(args.discovery_a),
                _load_json(args.discovery_b),
                _load_json(args.template),
                evidence_registry=evidence_registry,
                discovery_a_sha256=_sha256_file(args.discovery_a),
                discovery_b_sha256=_sha256_file(args.discovery_b),
            )
        elif args.command == "validate-decision":
            payload = validate_decision(
                _load_json(args.submission),
                _load_json(args.catalog),
                evidence_registry=evidence_registry,
                submission_sha256=_sha256_file(args.submission),
            )
        elif args.command == "compare":
            payload = compare_decisions(
                _load_json(args.decision_a),
                _load_json(args.decision_b),
                _load_json(args.catalog),
                evidence_registry=evidence_registry,
                decision_a_sha256=_sha256_file(args.decision_a),
                decision_b_sha256=_sha256_file(args.decision_b),
            )
        elif args.command == "validate-consensus":
            payload = validate_consensus(
                _load_json(args.consensus),
                _load_json(args.decision_a),
                _load_json(args.decision_b),
                _load_json(args.catalog),
                _load_json(args.worksheet),
                evidence_registry=evidence_registry,
                decision_a_sha256=_sha256_file(args.decision_a),
                decision_b_sha256=_sha256_file(args.decision_b),
                worksheet_sha256=_sha256_file(args.worksheet),
                consensus_sha256=_sha256_file(args.consensus),
            )
        else:
            payload = build_frozen_vocabulary(
                _load_json(args.draft_vocabulary),
                _load_json(args.catalog),
                _load_json(args.consensus),
                _load_json(args.decision_a),
                _load_json(args.decision_b),
                _load_json(args.worksheet),
                evidence_registry=evidence_registry,
                draft_sha256=_sha256_file(args.draft_vocabulary),
                decision_a_sha256=_sha256_file(args.decision_a),
                decision_b_sha256=_sha256_file(args.decision_b),
                worksheet_sha256=_sha256_file(args.worksheet),
                consensus_sha256=_sha256_file(args.consensus),
            )
        _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
