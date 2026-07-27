from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

from .semantic_gold_workflow import validate_vocabulary


REVIEW_SCHEMA_VERSION = "ndp50-source-evidence-review/v1"
DISAGREEMENT_SCHEMA_VERSION = "ndp50-source-evidence-disagreement/v1"
CONSENSUS_SCHEMA_VERSION = "ndp50-source-evidence-consensus/v1"
CONSENSUS_VALIDATION_SCHEMA_VERSION = (
    "ndp50-source-evidence-consensus-validation/v1"
)
APPROVED_MANIFEST_SCHEMA_VERSION = (
    "ndp50-source-bundle-approved-manifest/v1"
)
WORKFLOW_SPEC_SCHEMA_VERSION = "ndp50-source-approval-workflow-spec/v1"
PURPOSES = (
    "general_semantic_annotation",
    "cpa_relational_table_assessment",
    "cpa_subject_column_assessment",
    "cpa_property_annotation_assessment",
)
REVIEWER_ROLES = {
    "domain_curator",
    "scientific_metadata_curator",
    "annotation_methodologist",
}
CURATOR_ROLES = {"domain_curator", "scientific_metadata_curator"}
CONSENSUS_ADJUDICATOR_ROLES = {
    "senior_scientific_metadata_curator",
    "research_data_governance_lead",
    "annotation_methods_lead",
}
PLACEHOLDER_TOKENS = ("replace-with", "placeholder", "todo", "tbd")


class NDPSourceApprovalError(ValueError):
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
        raise NDPSourceApprovalError(f"{label} must be non-empty")
    result = value.strip()
    if any(token in result.casefold() for token in PLACEHOLDER_TOKENS):
        raise NDPSourceApprovalError(f"{label} is still a placeholder")
    return result


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NDPSourceApprovalError(f"{label} must be non-empty text")
    return value.strip()


def _binding(path: Path, *, owner_dir: Path | None = None) -> Dict[str, Any]:
    file_value = (
        Path(path.resolve().relative_to(owner_dir.resolve())).as_posix()
        if owner_dir is not None and path.resolve().is_relative_to(owner_dir.resolve())
        else path.name
    )
    return {"file": file_value, "sha256": _sha256_file(path)}


def _safe_child(owner: Path, relative: Any, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise NDPSourceApprovalError(f"{label} file is missing")
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise NDPSourceApprovalError(f"{label} must use a relative path")
    candidate = (owner.parent / relative_path).resolve()
    if not candidate.is_file():
        raise NDPSourceApprovalError(f"{label} file does not exist")
    return candidate


def load_pending_bundle_registry(
    manifest_path: Path,
    *,
    require_frozen_vocabulary: bool,
) -> tuple[
    Dict[str, Dict[str, Any]],
    Dict[str, Any],
]:
    manifest = _load_json(manifest_path)
    if (
        manifest.get("schema_version")
        != "ndp50-source-bundle-draft-manifest/v1"
    ):
        raise NDPSourceApprovalError("unexpected draft source manifest schema")
    vocabulary_status = manifest.get("vocabulary", {}).get("status")
    expected_status = (
        "draft_bundles_structurally_valid_pending_human_source_approval"
    )
    if require_frozen_vocabulary and (
        vocabulary_status != "frozen"
        or manifest.get("status") != expected_status
    ):
        raise NDPSourceApprovalError(
            "source approval requires bundles rebuilt against a frozen vocabulary"
        )
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise NDPSourceApprovalError("draft source manifest has no cases")
    registry: Dict[str, Dict[str, Any]] = {}
    for item in cases:
        if not isinstance(item, Mapping):
            raise NDPSourceApprovalError("draft manifest case must be an object")
        case_id = _identifier(item.get("case_id"), "case_id")
        if case_id in registry:
            raise NDPSourceApprovalError(f"duplicate source case {case_id}")
        bundle_path = _safe_child(
            manifest_path,
            item.get("bundle_file"),
            f"bundle {case_id}",
        )
        if _sha256_file(bundle_path) != item.get("bundle_sha256"):
            raise NDPSourceApprovalError(
                f"bundle {case_id} hash does not match the manifest"
            )
        bundle = _load_json(bundle_path)
        if (
            bundle.get("schema_version") != "semantic-source-bundle/v1"
            or bundle.get("dataset_id") != case_id
            or bundle.get("vocabulary_sha256")
            != manifest.get("vocabulary", {}).get("sha256")
        ):
            raise NDPSourceApprovalError(
                f"bundle {case_id} identity is invalid"
            )
        if require_frozen_vocabulary and (
            bundle.get("status") != "draft_blocked_on_human_source_approval"
            or item.get("annotation_readiness")
            != "blocked_on_human_source_approval"
        ):
            raise NDPSourceApprovalError(
                f"bundle {case_id} is not at the source-approval gate"
            )
        evidence = bundle.get("evidence_catalog")
        if not isinstance(evidence, list) or not evidence:
            raise NDPSourceApprovalError(
                f"bundle {case_id} has no evidence catalog"
            )
        evidence_map = {}
        evidence_order = []
        for evidence_item in evidence:
            if not isinstance(evidence_item, Mapping):
                raise NDPSourceApprovalError(
                    f"bundle {case_id} has invalid evidence"
                )
            evidence_id = _identifier(
                evidence_item.get("catalog_evidence_id"),
                f"bundle {case_id} evidence_id",
            )
            if evidence_id in evidence_map:
                raise NDPSourceApprovalError(
                    f"bundle {case_id} has duplicate evidence {evidence_id}"
                )
            evidence_order.append(evidence_id)
            evidence_map[evidence_id] = dict(evidence_item)
        registry[case_id] = {
            "manifest_entry": dict(item),
            "bundle_path": bundle_path,
            "bundle": bundle,
            "evidence_order": evidence_order,
            "evidence": evidence_map,
        }
    return registry, {
        "file": manifest_path.name,
        "sha256": _sha256_file(manifest_path),
        "status": manifest.get("status"),
        "vocabulary_sha256": manifest.get("vocabulary", {}).get("sha256"),
    }


def _cpa_case_ids(cpa_screen: Mapping[str, Any]) -> list[str]:
    if (
        cpa_screen.get("schema_version")
        != "ndp50-cpa-applicability-screen/v1"
    ):
        raise NDPSourceApprovalError("unexpected CPA screen schema")
    cases = cpa_screen.get("cases")
    if not isinstance(cases, list):
        raise NDPSourceApprovalError("CPA screen cases must be a list")
    result = [str(item.get("case_id") or "") for item in cases]
    if any(not item for item in result) or len(result) != len(set(result)):
        raise NDPSourceApprovalError("CPA screen case identity is invalid")
    return result


def build_review_template(
    *,
    source_bundle_manifest_path: Path,
    cpa_screen_path: Path,
    frozen_vocabulary_path: Path,
    output_path: Path | None = None,
) -> Dict[str, Any]:
    registry, manifest_binding = load_pending_bundle_registry(
        source_bundle_manifest_path,
        require_frozen_vocabulary=True,
    )
    cpa_screen = _load_json(cpa_screen_path)
    vocabulary = _load_json(frozen_vocabulary_path)
    if (
        validate_vocabulary(vocabulary).get("status") != "ready"
        or _sha256_file(frozen_vocabulary_path)
        != manifest_binding["vocabulary_sha256"]
    ):
        raise NDPSourceApprovalError(
            "source approval requires the exact valid frozen vocabulary "
            "bound by the source bundles"
        )
    cpa_ids = set(_cpa_case_ids(cpa_screen))
    if not cpa_ids.issubset(registry):
        raise NDPSourceApprovalError(
            "CPA cases are not covered by the source-bundle manifest"
        )
    cases = []
    for case_id in sorted(registry):
        record = registry[case_id]
        evidence_decisions = []
        for evidence_id in record["evidence_order"]:
            evidence = record["evidence"][evidence_id]
            evidence_decisions.append(
                {
                    "catalog_evidence_id": evidence_id,
                    "source_id": evidence.get("source_id"),
                    "source_type": evidence.get("source_type"),
                    "source_sha256": evidence.get("source_sha256"),
                    "selector": evidence.get("selector"),
                    "applicable_field_paths": evidence.get(
                        "applicable_field_paths"
                    ),
                    "strength": evidence.get("strength"),
                    "locatable": None,
                    "relevant": None,
                    "approved_purposes": [],
                    "rationale": None,
                }
            )
        cases.append(
            {
                "case_id": case_id,
                "split": record["manifest_entry"].get("split"),
                "bundle_sha256": record["manifest_entry"]["bundle_sha256"],
                "cpa_candidate": case_id in cpa_ids,
                "additional_documentation_required": None,
                "case_rationale": None,
                "evidence_decisions": evidence_decisions,
            }
        )
    if output_path is None:
        source_manifest_ref = manifest_binding
        cpa_screen_ref = _binding(cpa_screen_path)
        vocabulary_ref = _binding(frozen_vocabulary_path)
    else:
        source_manifest_ref = {
            **_artifact_ref(
                source_bundle_manifest_path, owner_dir=output_path.parent
            ),
            "status": manifest_binding["status"],
            "vocabulary_sha256": manifest_binding["vocabulary_sha256"],
        }
        cpa_screen_ref = _artifact_ref(
            cpa_screen_path, owner_dir=output_path.parent
        )
        vocabulary_ref = _artifact_ref(
            frozen_vocabulary_path, owner_dir=output_path.parent
        )
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "annotation_stage": "independent_pre_annotation_source_review",
        "reviewer_id": "replace-with-pseudonymous-non-developer-id",
        "reviewer_role": "replace-with-qualified-reviewer-role",
        "qualification_summary": None,
        "conflict_of_interest_declared": None,
        "submission_id": "replace-with-stable-unique-id",
        "developer_participation": False,
        "model_outputs_visible": False,
        "other_review_visible_before_freeze": False,
        "source_bundle_draft_manifest": source_manifest_ref,
        "cpa_screen": cpa_screen_ref,
        "frozen_vocabulary": vocabulary_ref,
        "purpose_taxonomy": list(PURPOSES),
        "cases": cases,
        "completion_attestation": None,
    }


def _case_map(
    value: Any,
    *,
    label: str,
) -> tuple[list[str], Dict[str, Mapping[str, Any]]]:
    if not isinstance(value, list) or not value:
        raise NDPSourceApprovalError(f"{label} must be a non-empty list")
    order = []
    mapped = {}
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise NDPSourceApprovalError(f"{label}[{index}] must be an object")
        case_id = _identifier(item.get("case_id"), f"{label}[{index}].case_id")
        if case_id in mapped:
            raise NDPSourceApprovalError(
                f"{label} contains duplicate case {case_id}"
            )
        order.append(case_id)
        mapped[case_id] = item
    return order, mapped


def _evidence_map(
    value: Any,
    *,
    label: str,
) -> tuple[list[str], Dict[str, Mapping[str, Any]]]:
    if not isinstance(value, list) or not value:
        raise NDPSourceApprovalError(f"{label} must be a non-empty list")
    order = []
    mapped = {}
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise NDPSourceApprovalError(f"{label}[{index}] must be an object")
        evidence_id = _identifier(
            item.get("catalog_evidence_id"),
            f"{label}[{index}].catalog_evidence_id",
        )
        if evidence_id in mapped:
            raise NDPSourceApprovalError(
                f"{label} contains duplicate evidence {evidence_id}"
            )
        order.append(evidence_id)
        mapped[evidence_id] = item
    return order, mapped


def _required_purposes(cpa_candidate: bool) -> set[str]:
    result = {"general_semantic_annotation"}
    if cpa_candidate:
        result.update(PURPOSES[1:])
    return result


def _derive_case_readiness(case: Mapping[str, Any]) -> Dict[str, Any]:
    approved = set()
    for item in case["evidence_decisions"]:
        approved.update(item["approved_purposes"])
    required = _required_purposes(bool(case["cpa_candidate"]))
    missing = sorted(required - approved)
    ready = (
        case["additional_documentation_required"] is False and not missing
    )
    return {
        "ready": ready,
        "required_purposes": sorted(required),
        "approved_purposes": sorted(approved),
        "missing_purposes": missing,
    }


def validate_review(
    submission: Mapping[str, Any],
    template: Mapping[str, Any],
    *,
    submission_sha256: str | None = None,
) -> Dict[str, Any]:
    if template.get("schema_version") != REVIEW_SCHEMA_VERSION:
        raise NDPSourceApprovalError("unexpected source-review template schema")
    for key in (
        "schema_version",
        "annotation_stage",
        "developer_participation",
        "model_outputs_visible",
        "other_review_visible_before_freeze",
        "source_bundle_draft_manifest",
        "cpa_screen",
        "frozen_vocabulary",
        "purpose_taxonomy",
    ):
        if submission.get(key) != template.get(key):
            raise NDPSourceApprovalError(
                f"source review mutates frozen field {key}"
            )
    reviewer_id = _identifier(submission.get("reviewer_id"), "reviewer_id")
    reviewer_role = _identifier(
        submission.get("reviewer_role"), "reviewer_role"
    )
    if reviewer_role not in REVIEWER_ROLES:
        raise NDPSourceApprovalError(
            f"unsupported reviewer role {reviewer_role!r}"
        )
    _text(submission.get("qualification_summary"), "qualification_summary")
    if submission.get("conflict_of_interest_declared") is not False:
        raise NDPSourceApprovalError(
            "conflict_of_interest_declared must be false"
        )
    submission_id = _identifier(
        submission.get("submission_id"), "submission_id"
    )
    template_order, template_cases = _case_map(
        template.get("cases"), label="template.cases"
    )
    order, cases = _case_map(submission.get("cases"), label="submission.cases")
    if order != template_order:
        raise NDPSourceApprovalError(
            "source review case order/identity differs from template"
        )
    ready_count = 0
    evidence_count = 0
    for case_id in order:
        case = cases[case_id]
        frozen = template_cases[case_id]
        for key in ("case_id", "split", "bundle_sha256", "cpa_candidate"):
            if case.get(key) != frozen.get(key):
                raise NDPSourceApprovalError(
                    f"case {case_id} mutates frozen field {key}"
                )
        if not isinstance(case.get("additional_documentation_required"), bool):
            raise NDPSourceApprovalError(
                f"case {case_id}.additional_documentation_required must be boolean"
            )
        _text(case.get("case_rationale"), f"case {case_id}.case_rationale")
        frozen_order, frozen_evidence = _evidence_map(
            frozen.get("evidence_decisions"),
            label=f"template case {case_id}.evidence",
        )
        evidence_order, evidence = _evidence_map(
            case.get("evidence_decisions"),
            label=f"case {case_id}.evidence",
        )
        if evidence_order != frozen_order:
            raise NDPSourceApprovalError(
                f"case {case_id} evidence order/identity differs from template"
            )
        for evidence_id in evidence_order:
            item = evidence[evidence_id]
            frozen_item = frozen_evidence[evidence_id]
            for key in (
                "catalog_evidence_id",
                "source_id",
                "source_type",
                "source_sha256",
                "selector",
                "applicable_field_paths",
                "strength",
            ):
                if item.get(key) != frozen_item.get(key):
                    raise NDPSourceApprovalError(
                        f"case {case_id} evidence {evidence_id} mutates {key}"
                    )
            if not isinstance(item.get("locatable"), bool) or not isinstance(
                item.get("relevant"), bool
            ):
                raise NDPSourceApprovalError(
                    f"case {case_id} evidence {evidence_id} decisions must be boolean"
                )
            purposes = item.get("approved_purposes")
            if (
                not isinstance(purposes, list)
                or purposes != sorted(set(purposes))
                or any(purpose not in PURPOSES for purpose in purposes)
            ):
                raise NDPSourceApprovalError(
                    f"case {case_id} evidence {evidence_id} purposes are invalid"
                )
            if (not item["locatable"] or not item["relevant"]) and purposes:
                raise NDPSourceApprovalError(
                    f"case {case_id} evidence {evidence_id} cannot authorize purposes"
                )
            if item["relevant"] != bool(purposes):
                raise NDPSourceApprovalError(
                    f"case {case_id} evidence {evidence_id} relevance/purpose mismatch"
                )
            if (
                "cpa_subject_column_assessment" in purposes
                and not item.get("applicable_field_paths")
            ):
                raise NDPSourceApprovalError(
                    f"case {case_id} evidence {evidence_id} lacks subject field scope"
                )
            _text(
                item.get("rationale"),
                f"case {case_id} evidence {evidence_id}.rationale",
            )
            evidence_count += 1
        ready_count += int(_derive_case_readiness(case)["ready"])
    if submission.get("completion_attestation") is not True:
        raise NDPSourceApprovalError("completion_attestation must be true")
    return {
        "schema_version": "ndp50-source-evidence-review-validation/v1",
        "status": "passed",
        "reviewer_id": reviewer_id,
        "reviewer_role": reviewer_role,
        "submission_id": submission_id,
        "submission_sha256": submission_sha256
        or _sha256_payload(submission),
        "case_count": len(order),
        "evidence_count": evidence_count,
        "ready_case_count": ready_count,
    }


def _review_slots(review: Mapping[str, Any]) -> Dict[str, Any]:
    slots: Dict[str, Any] = {}
    for case in review["cases"]:
        case_id = case["case_id"]
        slots[f"case:{case_id}:additional_documentation_required"] = case[
            "additional_documentation_required"
        ]
        for item in case["evidence_decisions"]:
            prefix = f"evidence:{case_id}:{item['catalog_evidence_id']}"
            slots[f"{prefix}:locatable"] = item["locatable"]
            slots[f"{prefix}:relevant"] = item["relevant"]
            slots[f"{prefix}:approved_purposes"] = item[
                "approved_purposes"
            ]
    return slots


def compare_reviews(
    review_a: Mapping[str, Any],
    review_b: Mapping[str, Any],
    template: Mapping[str, Any],
    *,
    review_a_sha256: str | None = None,
    review_b_sha256: str | None = None,
) -> Dict[str, Any]:
    report_a = validate_review(
        review_a, template, submission_sha256=review_a_sha256
    )
    report_b = validate_review(
        review_b, template, submission_sha256=review_b_sha256
    )
    if report_a["reviewer_id"] == report_b["reviewer_id"]:
        raise NDPSourceApprovalError("reviews require distinct reviewers")
    if report_a["submission_id"] == report_b["submission_id"]:
        raise NDPSourceApprovalError("reviews require distinct submission IDs")
    roles = {report_a["reviewer_role"], report_b["reviewer_role"]}
    if not (roles & CURATOR_ROLES) or "annotation_methodologist" not in roles:
        raise NDPSourceApprovalError(
            "review pair must include a curator and an annotation methodologist"
        )
    slots_a = _review_slots(review_a)
    slots_b = _review_slots(review_b)
    if set(slots_a) != set(slots_b):
        raise NDPSourceApprovalError("source review slots differ")
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
    refs = []
    for report in (report_a, report_b):
        refs.append(
            {
                key: report[key]
                for key in (
                    "reviewer_id",
                    "reviewer_role",
                    "submission_id",
                    "submission_sha256",
                )
            }
        )
    return {
        "schema_version": DISAGREEMENT_SCHEMA_VERSION,
        "status": (
            "ready_for_human_adjudication"
            if disagreement_count
            else "no_disagreements_consensus_documentation_required"
        ),
        "review_template_sha256": _sha256_payload(template),
        "independent_reviews": refs,
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
        raise NDPSourceApprovalError("unexpected disagreement schema")
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
        "review_template_sha256": worksheet["review_template_sha256"],
        "independent_reviews": worksheet["independent_reviews"],
        "disagreement_worksheet_sha256": worksheet_sha256
        or _sha256_payload(worksheet),
        "automatic_adjudication": False,
        "slot_values": values,
        "slot_rationales": {slot_id: None for slot_id in values},
        "resolutions": [
            {
                "slot_id": item["slot_id"],
                "selected_value": None,
                "rationale": None,
            }
            for item in worksheet["slots"]
            if not item["agreed"]
        ],
        "completion_attestation": None,
    }


def _apply_slot_values(
    template: Mapping[str, Any],
    values: Mapping[str, Any],
) -> Dict[str, Any]:
    resolved = copy.deepcopy(dict(template))
    for case in resolved["cases"]:
        case_id = case["case_id"]
        case["additional_documentation_required"] = values[
            f"case:{case_id}:additional_documentation_required"
        ]
        for item in case["evidence_decisions"]:
            prefix = f"evidence:{case_id}:{item['catalog_evidence_id']}"
            item["locatable"] = values[f"{prefix}:locatable"]
            item["relevant"] = values[f"{prefix}:relevant"]
            item["approved_purposes"] = values[
                f"{prefix}:approved_purposes"
            ]
    return resolved


def validate_consensus(
    consensus: Mapping[str, Any],
    review_a: Mapping[str, Any],
    review_b: Mapping[str, Any],
    template: Mapping[str, Any],
    worksheet: Mapping[str, Any],
    *,
    review_a_sha256: str | None = None,
    review_b_sha256: str | None = None,
    worksheet_sha256: str | None = None,
    consensus_sha256: str | None = None,
) -> Dict[str, Any]:
    expected = compare_reviews(
        review_a,
        review_b,
        template,
        review_a_sha256=review_a_sha256,
        review_b_sha256=review_b_sha256,
    )
    if worksheet != expected:
        raise NDPSourceApprovalError(
            "worksheet is not the deterministic comparison of reviews"
        )
    if consensus.get("schema_version") != CONSENSUS_SCHEMA_VERSION:
        raise NDPSourceApprovalError("unexpected consensus schema")
    if consensus.get("status") != "consensus_frozen":
        raise NDPSourceApprovalError("consensus status must be consensus_frozen")
    if consensus.get("annotation_stage") != "post_freeze_human_consensus":
        raise NDPSourceApprovalError("unexpected consensus stage")
    if consensus.get("automatic_adjudication") is not False:
        raise NDPSourceApprovalError("automatic adjudication is forbidden")
    adjudicator_id = _identifier(
        consensus.get("adjudicator_id"), "adjudicator_id"
    )
    adjudicator_role = _identifier(
        consensus.get("adjudicator_role"), "adjudicator_role"
    )
    if adjudicator_role not in CONSENSUS_ADJUDICATOR_ROLES:
        raise NDPSourceApprovalError(
            f"unsupported adjudicator role {adjudicator_role!r}"
        )
    _text(consensus.get("qualification_summary"), "qualification_summary")
    if consensus.get("conflict_of_interest_declared") is not False:
        raise NDPSourceApprovalError(
            "source adjudicator must declare no unresolved conflict"
        )
    if consensus.get("developer_participation") is not False:
        raise NDPSourceApprovalError(
            "source adjudicator must be a non-developer"
        )
    if consensus.get("prior_stage_participation") is not False:
        raise NDPSourceApprovalError(
            "source adjudicator must be fresh from independent reviews"
        )
    prior_reviewer_ids = {
        item.get("reviewer_id")
        for item in expected.get("independent_reviews", [])
        if isinstance(item, Mapping)
    }
    if adjudicator_id in prior_reviewer_ids:
        raise NDPSourceApprovalError(
            "source adjudicator must be distinct from prior reviewers"
        )
    for key in ("review_template_sha256", "independent_reviews"):
        if consensus.get(key) != expected.get(key):
            raise NDPSourceApprovalError(
                f"consensus mutates frozen binding {key}"
            )
    expected_worksheet_hash = worksheet_sha256 or _sha256_payload(worksheet)
    if (
        consensus.get("disagreement_worksheet_sha256")
        != expected_worksheet_hash
    ):
        raise NDPSourceApprovalError(
            "consensus does not bind the exact worksheet"
        )
    values = consensus.get("slot_values")
    rationales = consensus.get("slot_rationales")
    expected_ids = [item["slot_id"] for item in worksheet["slots"]]
    if (
        not isinstance(values, Mapping)
        or set(values) != set(expected_ids)
        or not isinstance(rationales, Mapping)
        or set(rationales) != set(expected_ids)
    ):
        raise NDPSourceApprovalError(
            "consensus slot maps must cover the exact worksheet"
        )
    resolutions = consensus.get("resolutions")
    if not isinstance(resolutions, list):
        raise NDPSourceApprovalError("resolutions must be a list")
    resolution_map = {}
    for item in resolutions:
        if not isinstance(item, Mapping):
            raise NDPSourceApprovalError("resolution must be an object")
        slot_id = str(item.get("slot_id") or "")
        if not slot_id or slot_id in resolution_map:
            raise NDPSourceApprovalError("resolution IDs must be unique")
        resolution_map[slot_id] = item
    disagreement_ids = {
        item["slot_id"] for item in worksheet["slots"] if not item["agreed"]
    }
    if set(resolution_map) != disagreement_ids:
        raise NDPSourceApprovalError(
            "every and only disagreement requires a resolution"
        )
    for item in worksheet["slots"]:
        slot_id = item["slot_id"]
        value = values[slot_id]
        if slot_id.endswith(":approved_purposes"):
            if (
                not isinstance(value, list)
                or value != sorted(set(value))
                or any(purpose not in PURPOSES for purpose in value)
            ):
                raise NDPSourceApprovalError(
                    f"consensus slot {slot_id} has invalid purposes"
                )
        elif not isinstance(value, bool):
            raise NDPSourceApprovalError(
                f"consensus slot {slot_id} must be boolean"
            )
        if item["agreed"] and value != item["value_a"]:
            raise NDPSourceApprovalError(
                f"consensus mutates agreed slot {slot_id}"
            )
        if not item["agreed"]:
            resolution = resolution_map[slot_id]
            if resolution.get("selected_value") != value:
                raise NDPSourceApprovalError(
                    f"resolution differs from final slot {slot_id}"
                )
            _text(
                resolution.get("rationale"),
                f"resolution {slot_id}.rationale",
            )
        _text(rationales[slot_id], f"slot {slot_id}.rationale")
    resolved = _apply_slot_values(template, values)
    _, cases = _case_map(resolved["cases"], label="resolved.cases")
    for case_id, case in cases.items():
        for item in case["evidence_decisions"]:
            if (
                (not item["locatable"] or not item["relevant"])
                and item["approved_purposes"]
            ) or item["relevant"] != bool(item["approved_purposes"]):
                raise NDPSourceApprovalError(
                    f"consensus creates inconsistent evidence decision in {case_id}"
                )
            if (
                "cpa_subject_column_assessment"
                in item["approved_purposes"]
                and not item.get("applicable_field_paths")
            ):
                raise NDPSourceApprovalError(
                    f"consensus approves unscoped subject evidence in {case_id}"
                )
    readiness = {
        case_id: _derive_case_readiness(case)
        for case_id, case in cases.items()
    }
    ready_count = sum(item["ready"] for item in readiness.values())
    if consensus.get("completion_attestation") is not True:
        raise NDPSourceApprovalError(
            "consensus completion_attestation must be true"
        )
    return {
        "schema_version": CONSENSUS_VALIDATION_SCHEMA_VERSION,
        "status": "passed",
        "adjudicator_id": adjudicator_id,
        "adjudicator_role": adjudicator_role,
        "adjudicator_independent_of_prior_reviews": True,
        "consensus_sha256": consensus_sha256
        or _sha256_payload(consensus),
        "worksheet_sha256": expected_worksheet_hash,
        "case_count": len(cases),
        "ready_case_count": ready_count,
        "all_cases_ready": ready_count == len(cases),
        "case_readiness": readiness,
    }


def _artifact_ref(path: Path, *, owner_dir: Path) -> Dict[str, Any]:
    relative = Path(
        __import__("os").path.relpath(path.resolve(), owner_dir.resolve())
    ).as_posix()
    return {"file": relative, "sha256": _sha256_file(path)}


def build_approved_manifest(
    *,
    source_bundle_manifest_path: Path,
    review_template_path: Path,
    review_a_path: Path,
    review_b_path: Path,
    worksheet_path: Path,
    consensus_path: Path,
    output_path: Path,
) -> Dict[str, Any]:
    registry, draft_binding = load_pending_bundle_registry(
        source_bundle_manifest_path,
        require_frozen_vocabulary=True,
    )
    template = _load_json(review_template_path)
    bound_source_manifest = _bound_path(
        review_template_path,
        template["source_bundle_draft_manifest"],
        "review-template draft source manifest",
    )
    if bound_source_manifest != source_bundle_manifest_path.resolve():
        raise NDPSourceApprovalError(
            "review template binds a different draft source manifest"
        )
    bound_cpa_screen = _bound_path(
        review_template_path,
        template["cpa_screen"],
        "review-template CPA screen",
    )
    bound_vocabulary = _bound_path(
        review_template_path,
        template["frozen_vocabulary"],
        "review-template frozen vocabulary",
    )
    expected_template = build_review_template(
        source_bundle_manifest_path=source_bundle_manifest_path,
        cpa_screen_path=bound_cpa_screen,
        frozen_vocabulary_path=bound_vocabulary,
        output_path=review_template_path,
    )
    if template != expected_template:
        raise NDPSourceApprovalError(
            "review template is not reproducible from its frozen inputs"
        )
    review_a = _load_json(review_a_path)
    review_b = _load_json(review_b_path)
    worksheet = _load_json(worksheet_path)
    consensus = _load_json(consensus_path)
    validation = validate_consensus(
        consensus,
        review_a,
        review_b,
        template,
        worksheet,
        review_a_sha256=_sha256_file(review_a_path),
        review_b_sha256=_sha256_file(review_b_path),
        worksheet_sha256=_sha256_file(worksheet_path),
        consensus_sha256=_sha256_file(consensus_path),
    )
    if not validation["all_cases_ready"]:
        raise NDPSourceApprovalError(
            "approved manifest requires every case to satisfy all required purposes"
        )
    resolved = _apply_slot_values(template, consensus["slot_values"])
    resolved_cases = {
        item["case_id"]: item for item in resolved["cases"]
    }
    cases = []
    for case_id in sorted(registry):
        record = registry[case_id]
        decisions = {
            item["catalog_evidence_id"]: item
            for item in resolved_cases[case_id]["evidence_decisions"]
        }
        approved_evidence = []
        for evidence_id in record["evidence_order"]:
            decision = decisions[evidence_id]
            if decision["approved_purposes"]:
                approved_evidence.append(
                    {
                        **record["evidence"][evidence_id],
                        "approved_purposes": decision[
                            "approved_purposes"
                        ],
                    }
                )
        cases.append(
            {
                "case_id": case_id,
                "split": record["manifest_entry"].get("split"),
                "draft_bundle_file": record["manifest_entry"]["bundle_file"],
                "draft_bundle_sha256": record["manifest_entry"][
                    "bundle_sha256"
                ],
                "cpa_candidate": resolved_cases[case_id]["cpa_candidate"],
                "required_purposes": validation["case_readiness"][case_id][
                    "required_purposes"
                ],
                "approved_evidence_count": len(approved_evidence),
                "approved_evidence": approved_evidence,
            }
        )
    owner = output_path.parent
    return {
        "schema_version": APPROVED_MANIFEST_SCHEMA_VERSION,
        "status": "ready_for_independent_annotation",
        "source_bundle_draft_manifest": {
            **_artifact_ref(source_bundle_manifest_path, owner_dir=owner),
            "vocabulary_sha256": draft_binding["vocabulary_sha256"],
        },
        "review_template": _artifact_ref(
            review_template_path, owner_dir=owner
        ),
        "review_a": _artifact_ref(review_a_path, owner_dir=owner),
        "review_b": _artifact_ref(review_b_path, owner_dir=owner),
        "disagreement_worksheet": _artifact_ref(
            worksheet_path, owner_dir=owner
        ),
        "consensus": _artifact_ref(consensus_path, owner_dir=owner),
        "consensus_validation": validation,
        "case_count": len(cases),
        "cases": cases,
        "automatic_approval": False,
    }


def _bound_path(
    manifest_path: Path,
    ref: Mapping[str, Any],
    label: str,
) -> Path:
    path = _safe_child(manifest_path, ref.get("file"), label)
    if _sha256_file(path) != ref.get("sha256"):
        raise NDPSourceApprovalError(f"{label} hash mismatch")
    return path


def load_approved_evidence_registry(
    approved_manifest_path: Path,
) -> tuple[
    Dict[str, Dict[str, Mapping[str, Any]]],
    Dict[str, Any],
]:
    manifest = _load_json(approved_manifest_path)
    if (
        manifest.get("schema_version")
        != APPROVED_MANIFEST_SCHEMA_VERSION
        or manifest.get("status") != "ready_for_independent_annotation"
        or manifest.get("automatic_approval") is not False
    ):
        raise NDPSourceApprovalError("approved source manifest is invalid")
    refs = {
        "source_bundle_manifest_path": _bound_path(
            approved_manifest_path,
            manifest["source_bundle_draft_manifest"],
            "draft source manifest",
        ),
        "review_template_path": _bound_path(
            approved_manifest_path,
            manifest["review_template"],
            "review template",
        ),
        "review_a_path": _bound_path(
            approved_manifest_path, manifest["review_a"], "review A"
        ),
        "review_b_path": _bound_path(
            approved_manifest_path, manifest["review_b"], "review B"
        ),
        "worksheet_path": _bound_path(
            approved_manifest_path,
            manifest["disagreement_worksheet"],
            "disagreement worksheet",
        ),
        "consensus_path": _bound_path(
            approved_manifest_path,
            manifest["consensus"],
            "consensus",
        ),
    }
    expected = build_approved_manifest(
        **refs,
        output_path=approved_manifest_path,
    )
    if manifest != expected:
        raise NDPSourceApprovalError(
            "approved source manifest is not reproducible from its review chain"
        )
    registry = {}
    for case in manifest["cases"]:
        registry[case["case_id"]] = {
            item["catalog_evidence_id"]: item
            for item in case["approved_evidence"]
        }
    return registry, {
        "file": approved_manifest_path.name,
        "sha256": _sha256_file(approved_manifest_path),
        "status": manifest["status"],
    }


def build_workflow_spec(implementation_file: Path) -> Dict[str, Any]:
    return {
        "schema_version": WORKFLOW_SPEC_SCHEMA_VERSION,
        "status": "implementation_ready_waiting_on_frozen_vocabulary_and_rebuilt_bundles",
        "implementation": {
            "file": implementation_file.name,
            "sha256": _sha256_file(implementation_file),
        },
        "implementation_dependencies": {
            implementation_file.with_name("semantic_gold_workflow.py").name: (
                _sha256_file(
                    implementation_file.with_name(
                        "semantic_gold_workflow.py"
                    )
                )
            )
        },
        "purpose_taxonomy": list(PURPOSES),
        "required_independent_reviewers": 2,
        "required_role_coverage": [
            "one_domain_or_scientific_metadata_curator",
            "one_annotation_methodologist",
        ],
        "required_consensus_adjudicators": 1,
        "consensus_adjudicator_fresh_from_reviews": True,
        "consensus_adjudicator_qualification_and_conflict_required": True,
        "consensus_adjudicator_non_developer_required": True,
        "requires_frozen_vocabulary": True,
        "requires_rebuilt_source_bundles": True,
        "automatic_approval": False,
        "human_decisions_present": False,
        "sequence": [
            "prepare_exact_item_level_review_template",
            "two_independent_qualified_reviews",
            "reveal_deterministic_disagreements_after_both_freeze",
            "human_consensus_without_changing_agreements",
            "validator_generated_approved_manifest",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review and approve NDP-50 source evidence."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    spec = subparsers.add_parser("build-spec")
    spec.add_argument("--output", type=Path, required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--source-bundle-manifest", type=Path, required=True)
    prepare.add_argument("--cpa-screen", type=Path, required=True)
    prepare.add_argument("--frozen-vocabulary", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate-review")
    validate.add_argument("--review", type=Path, required=True)
    validate.add_argument("--template", type=Path, required=True)
    validate.add_argument("--output", type=Path, required=True)
    compare = subparsers.add_parser("compare")
    compare.add_argument("--review-a", type=Path, required=True)
    compare.add_argument("--review-b", type=Path, required=True)
    compare.add_argument("--template", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)
    consensus_template = subparsers.add_parser("build-consensus-template")
    consensus_template.add_argument("--worksheet", type=Path, required=True)
    consensus_template.add_argument("--output", type=Path, required=True)
    validate_consensus_parser = subparsers.add_parser("validate-consensus")
    validate_consensus_parser.add_argument(
        "--consensus", type=Path, required=True
    )
    validate_consensus_parser.add_argument("--review-a", type=Path, required=True)
    validate_consensus_parser.add_argument("--review-b", type=Path, required=True)
    validate_consensus_parser.add_argument("--template", type=Path, required=True)
    validate_consensus_parser.add_argument(
        "--worksheet", type=Path, required=True
    )
    validate_consensus_parser.add_argument("--output", type=Path, required=True)
    approve = subparsers.add_parser("approve")
    approve.add_argument("--source-bundle-manifest", type=Path, required=True)
    approve.add_argument("--template", type=Path, required=True)
    approve.add_argument("--review-a", type=Path, required=True)
    approve.add_argument("--review-b", type=Path, required=True)
    approve.add_argument("--worksheet", type=Path, required=True)
    approve.add_argument("--consensus", type=Path, required=True)
    approve.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify-approved")
    verify.add_argument("--approved-manifest", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build-spec":
        payload = build_workflow_spec(Path(__file__))
    elif args.command == "prepare":
        payload = build_review_template(
            source_bundle_manifest_path=args.source_bundle_manifest,
            cpa_screen_path=args.cpa_screen,
            frozen_vocabulary_path=args.frozen_vocabulary,
            output_path=args.output,
        )
    elif args.command == "validate-review":
        payload = validate_review(
            _load_json(args.review),
            _load_json(args.template),
            submission_sha256=_sha256_file(args.review),
        )
    elif args.command == "compare":
        payload = compare_reviews(
            _load_json(args.review_a),
            _load_json(args.review_b),
            _load_json(args.template),
            review_a_sha256=_sha256_file(args.review_a),
            review_b_sha256=_sha256_file(args.review_b),
        )
    elif args.command == "build-consensus-template":
        payload = build_consensus_template(
            _load_json(args.worksheet),
            worksheet_sha256=_sha256_file(args.worksheet),
        )
    elif args.command == "validate-consensus":
        payload = validate_consensus(
            _load_json(args.consensus),
            _load_json(args.review_a),
            _load_json(args.review_b),
            _load_json(args.template),
            _load_json(args.worksheet),
            review_a_sha256=_sha256_file(args.review_a),
            review_b_sha256=_sha256_file(args.review_b),
            worksheet_sha256=_sha256_file(args.worksheet),
            consensus_sha256=_sha256_file(args.consensus),
        )
    elif args.command == "approve":
        payload = build_approved_manifest(
            source_bundle_manifest_path=args.source_bundle_manifest,
            review_template_path=args.template,
            review_a_path=args.review_a,
            review_b_path=args.review_b,
            worksheet_path=args.worksheet,
            consensus_path=args.consensus,
            output_path=args.output,
        )
    else:
        registry, binding = load_approved_evidence_registry(
            args.approved_manifest
        )
        payload = {
            "schema_version": "ndp50-approved-source-validation/v1",
            "status": "passed",
            "approved_manifest": binding,
            "case_count": len(registry),
            "evidence_count": sum(len(items) for items in registry.values()),
        }
    _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
