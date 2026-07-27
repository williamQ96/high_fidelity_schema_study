from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence


SCREEN_SCHEMA_VERSION = "ndp50-cpa-applicability-screen/v1"
VALIDATION_SCHEMA_VERSION = "ndp50-cpa-screen-validation/v1"
DISAGREEMENT_SCHEMA_VERSION = "ndp50-cpa-screen-disagreement/v1"
CONSENSUS_SCHEMA_VERSION = "ndp50-cpa-applicability-consensus/v1"
CONSENSUS_VALIDATION_SCHEMA_VERSION = (
    "ndp50-cpa-consensus-validation/v1"
)
WORKFLOW_SCHEMA_VERSION = "ndp50-cpa-screen-workflow/v1"
BOOLEAN_SLOTS = (
    "relational_table_applicable",
    "single_subject_column_supported",
    "property_annotation_applicable",
)
SUBJECT_SLOT = "subject_column_field_path"
DECISION_SLOTS = (*BOOLEAN_SLOTS, SUBJECT_SLOT)
PLACEHOLDER_TOKENS = ("replace-with", "placeholder", "todo", "tbd")
ANNOTATOR_ROLES = {
    "domain_curator",
    "scientific_metadata_curator",
    "annotation_methodologist",
}
CURATOR_ROLES = {"domain_curator", "scientific_metadata_curator"}
CONSENSUS_ADJUDICATOR_ROLES = {
    "senior_scientific_metadata_curator",
    "cpa_methods_lead",
    "annotation_methods_lead",
}


class NDPCPAScreenWorkflowError(ValueError):
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


def _require_identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NDPCPAScreenWorkflowError(f"{label} must be a non-empty string")
    normalized = value.strip()
    if any(token in normalized.casefold() for token in PLACEHOLDER_TOKENS):
        raise NDPCPAScreenWorkflowError(f"{label} is still a placeholder")
    return normalized


def _require_nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NDPCPAScreenWorkflowError(f"{label} must be non-empty text")
    return value.strip()


def _require_evidence_refs(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise NDPCPAScreenWorkflowError(
            f"{label} must contain at least one non-empty reference"
        )
    refs = [item.strip() for item in value]
    if len(refs) != len(set(refs)):
        raise NDPCPAScreenWorkflowError(f"{label} contains duplicate references")
    return refs


def load_evidence_registry(
    manifest_path: Path,
    *,
    require_approved: bool,
) -> tuple[Dict[str, Dict[str, Mapping[str, Any]]], Dict[str, Any], bool]:
    manifest = _load_json(manifest_path)
    if (
        manifest.get("schema_version")
        == "ndp50-source-bundle-approved-manifest/v1"
    ):
        from .ndp50_source_approval import (
            load_approved_evidence_registry,
        )

        registry, binding = load_approved_evidence_registry(manifest_path)
        return registry, binding, True
    if (
        manifest.get("schema_version")
        != "ndp50-source-bundle-draft-manifest/v1"
    ):
        raise NDPCPAScreenWorkflowError(
            "unexpected source-bundle manifest schema"
        )
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise NDPCPAScreenWorkflowError(
            "source-bundle manifest contains no cases"
        )
    root = manifest_path.parent.resolve()
    registry: Dict[str, Dict[str, Mapping[str, Any]]] = {}
    for item in cases:
        if not isinstance(item, Mapping):
            raise NDPCPAScreenWorkflowError(
                "source-bundle manifest case must be an object"
            )
        case_id = _require_identifier(
            item.get("case_id"), "source-bundle case_id"
        )
        if case_id in registry:
            raise NDPCPAScreenWorkflowError(
                f"duplicate source-bundle case {case_id}"
            )
        bundle_file = item.get("bundle_file")
        if not isinstance(bundle_file, str) or not bundle_file:
            raise NDPCPAScreenWorkflowError(
                f"source-bundle case {case_id} lacks bundle_file"
            )
        bundle_path = (manifest_path.parent / bundle_file).resolve()
        if not bundle_path.is_relative_to(root) or not bundle_path.is_file():
            raise NDPCPAScreenWorkflowError(
                f"source-bundle case {case_id} has an invalid bundle path"
            )
        if _sha256_file(bundle_path) != item.get("bundle_sha256"):
            raise NDPCPAScreenWorkflowError(
                f"source-bundle case {case_id} hash mismatch"
            )
        bundle = _load_json(bundle_path)
        if (
            bundle.get("schema_version") != "semantic-source-bundle/v1"
            or bundle.get("dataset_id") != case_id
        ):
            raise NDPCPAScreenWorkflowError(
                f"source-bundle case {case_id} identity mismatch"
            )
        evidence = bundle.get("evidence_catalog")
        if not isinstance(evidence, list) or not evidence:
            raise NDPCPAScreenWorkflowError(
                f"source-bundle case {case_id} has no evidence catalog"
            )
        indexed: Dict[str, Mapping[str, Any]] = {}
        for evidence_item in evidence:
            if not isinstance(evidence_item, Mapping):
                raise NDPCPAScreenWorkflowError(
                    f"source-bundle case {case_id} has invalid evidence"
                )
            evidence_id = _require_identifier(
                evidence_item.get("catalog_evidence_id"),
                f"source-bundle case {case_id} evidence ID",
            )
            if evidence_id in indexed:
                raise NDPCPAScreenWorkflowError(
                    f"source-bundle case {case_id} has duplicate evidence ID"
                )
            indexed[evidence_id] = evidence_item
        registry[case_id] = indexed
    if require_approved:
        raise NDPCPAScreenWorkflowError(
            "a draft source manifest cannot authorize independent annotation; "
            "a reproducible approved manifest is required"
        )
    binding = {
        "file": manifest_path.name,
        "sha256": _sha256_file(manifest_path),
        "status": manifest.get("status"),
    }
    return registry, binding, False


def _validate_evidence_refs(
    value: Any,
    *,
    label: str,
    case_id: str,
    evidence_registry: Mapping[str, Mapping[str, Mapping[str, Any]]],
    subject_field_path: str | None = None,
    required_purposes: Sequence[str] = (),
) -> list[str]:
    refs = _require_evidence_refs(value, label)
    catalog = evidence_registry.get(case_id)
    if not isinstance(catalog, Mapping):
        raise NDPCPAScreenWorkflowError(
            f"{label} has no bound source-bundle catalog"
        )
    unknown = [ref for ref in refs if ref not in catalog]
    if unknown:
        raise NDPCPAScreenWorkflowError(
            f"{label} contains unknown evidence IDs: {unknown}"
        )
    for purpose in required_purposes:
        if not any(
            purpose in (catalog[ref].get("approved_purposes") or [])
            for ref in refs
        ):
            raise NDPCPAScreenWorkflowError(
                f"{label} lacks evidence approved for purpose {purpose}"
            )
    if subject_field_path is not None and not any(
        subject_field_path
        in (catalog[ref].get("applicable_field_paths") or [])
        for ref in refs
    ):
        raise NDPCPAScreenWorkflowError(
            f"{label} does not locate evidence applicable to the subject field"
        )
    return refs


def _case_map(
    cases: Any,
    *,
    label: str,
) -> tuple[list[str], Dict[str, Mapping[str, Any]]]:
    if not isinstance(cases, list) or not cases:
        raise NDPCPAScreenWorkflowError(f"{label} must contain cases")
    order: list[str] = []
    mapped: Dict[str, Mapping[str, Any]] = {}
    for index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            raise NDPCPAScreenWorkflowError(
                f"{label}[{index}] must be an object"
            )
        case_id = _require_identifier(
            case.get("case_id"), f"{label}[{index}].case_id"
        )
        if case_id in mapped:
            raise NDPCPAScreenWorkflowError(
                f"{label} contains duplicate case_id {case_id}"
            )
        order.append(case_id)
        mapped[case_id] = case
    return order, mapped


def _neutral_contract(
    neutral: Mapping[str, Any],
) -> tuple[list[str], Dict[str, Mapping[str, Any]]]:
    if neutral.get("schema_version") != SCREEN_SCHEMA_VERSION:
        raise NDPCPAScreenWorkflowError("unexpected neutral screen schema")
    if neutral.get("annotation_stage") != "independent_pre_model_screen":
        raise NDPCPAScreenWorkflowError(
            "neutral screen has an unexpected annotation stage"
        )
    if neutral.get("developer_participation") is not False:
        raise NDPCPAScreenWorkflowError(
            "neutral screen must exclude developer participation"
        )
    if neutral.get("model_outputs_visible") is not False:
        raise NDPCPAScreenWorkflowError(
            "neutral screen must keep model outputs hidden"
        )
    opportunity = neutral.get("opportunity_manifest")
    if (
        not isinstance(opportunity, Mapping)
        or not isinstance(opportunity.get("sha256"), str)
        or len(opportunity["sha256"]) != 64
    ):
        raise NDPCPAScreenWorkflowError(
            "neutral screen lacks an opportunity-manifest hash"
        )
    order, mapped = _case_map(neutral.get("cases"), label="neutral.cases")
    for case_id, case in mapped.items():
        field_paths = case.get("field_paths")
        if (
            not isinstance(field_paths, list)
            or len(field_paths) < 2
            or any(
                not isinstance(item, str) or not item
                for item in field_paths
            )
            or len(field_paths) != len(set(field_paths))
        ):
            raise NDPCPAScreenWorkflowError(
                f"neutral case {case_id} has invalid field_paths"
            )
        if any(case.get(slot) is not None for slot in DECISION_SLOTS):
            raise NDPCPAScreenWorkflowError(
                f"neutral case {case_id} contains a decision"
            )
        if case.get("rationale") is not None or case.get("evidence_refs") != []:
            raise NDPCPAScreenWorkflowError(
                f"neutral case {case_id} contains annotation evidence"
            )
        if case.get("split") not in {"development", "validation"}:
            raise NDPCPAScreenWorkflowError(
                f"neutral case {case_id} has a prohibited split"
            )
    return order, mapped


def _validate_case_identity(
    submitted: Mapping[str, Any],
    neutral: Mapping[str, Any],
    *,
    case_id: str,
) -> None:
    for key in ("case_id", "dataset_id", "resource_id", "split", "field_paths"):
        if submitted.get(key) != neutral.get(key):
            raise NDPCPAScreenWorkflowError(
                f"case {case_id} mutates frozen identity field {key}"
            )


def _validate_decisions(
    case: Mapping[str, Any],
    *,
    field_paths: Sequence[str],
    label: str,
) -> None:
    for slot in BOOLEAN_SLOTS:
        if not isinstance(case.get(slot), bool):
            raise NDPCPAScreenWorkflowError(f"{label}.{slot} must be boolean")
    subject_supported = case["single_subject_column_supported"]
    subject = case.get(SUBJECT_SLOT)
    if subject_supported:
        if not isinstance(subject, str) or subject not in field_paths:
            raise NDPCPAScreenWorkflowError(
                f"{label}.{SUBJECT_SLOT} must name a frozen field path"
            )
    elif subject is not None:
        raise NDPCPAScreenWorkflowError(
            f"{label}.{SUBJECT_SLOT} must be null when no single subject is supported"
        )


def validate_independent_screen(
    submission: Mapping[str, Any],
    neutral: Mapping[str, Any],
    *,
    evidence_registry: Mapping[
        str, Mapping[str, Mapping[str, Any]]
    ],
    source_bundle_manifest: Mapping[str, Any],
    submission_sha256: str | None = None,
    neutral_sha256: str | None = None,
) -> Dict[str, Any]:
    neutral_order, neutral_cases = _neutral_contract(neutral)
    if submission.get("schema_version") != SCREEN_SCHEMA_VERSION:
        raise NDPCPAScreenWorkflowError("unexpected submission schema")
    for key in (
        "protocol_version",
        "annotation_stage",
        "developer_participation",
        "model_outputs_visible",
        "opportunity_manifest",
    ):
        if submission.get(key) != neutral.get(key):
            raise NDPCPAScreenWorkflowError(
                f"submission mutates frozen top-level field {key}"
            )
    annotator_id = _require_identifier(
        submission.get("annotator_id"), "annotator_id"
    )
    annotator_role = _require_identifier(
        submission.get("annotator_role"), "annotator_role"
    )
    if annotator_role not in ANNOTATOR_ROLES:
        raise NDPCPAScreenWorkflowError(
            f"unsupported annotator_role {annotator_role!r}"
        )
    _require_nonempty_text(
        submission.get("qualification_summary"),
        "qualification_summary",
    )
    if submission.get("conflict_of_interest_declared") is not False:
        raise NDPCPAScreenWorkflowError(
            "conflict_of_interest_declared must be false"
        )
    submission_id = _require_identifier(
        submission.get("submission_id"), "submission_id"
    )
    submitted_order, submitted_cases = _case_map(
        submission.get("cases"), label="submission.cases"
    )
    if submitted_order != neutral_order:
        raise NDPCPAScreenWorkflowError(
            "submission case order or identity differs from the neutral screen"
        )
    for case_id in neutral_order:
        submitted = submitted_cases[case_id]
        frozen = neutral_cases[case_id]
        _validate_case_identity(submitted, frozen, case_id=case_id)
        _validate_decisions(
            submitted,
            field_paths=frozen["field_paths"],
            label=f"case {case_id}",
        )
        _require_nonempty_text(
            submitted.get("rationale"), f"case {case_id}.rationale"
        )
        _validate_evidence_refs(
            submitted.get("evidence_refs"),
            label=f"case {case_id}.evidence_refs",
            case_id=case_id,
            evidence_registry=evidence_registry,
            subject_field_path=(
                submitted[SUBJECT_SLOT]
                if submitted["single_subject_column_supported"]
                else None
            ),
            required_purposes=(
                "cpa_relational_table_assessment",
                "cpa_subject_column_assessment",
                "cpa_property_annotation_assessment",
            ),
        )
    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "status": "passed",
        "annotation_stage": "independent_pre_model_screen",
        "annotator_id": annotator_id,
        "annotator_role": annotator_role,
        "submission_id": submission_id,
        "submission_sha256": submission_sha256
        or _sha256_payload(submission),
        "neutral_screen_sha256": neutral_sha256 or _sha256_payload(neutral),
        "source_bundle_manifest": dict(source_bundle_manifest),
        "case_count": len(neutral_order),
        "decision_slot_count": len(neutral_order) * len(DECISION_SLOTS),
        "model_outputs_visible": False,
        "developer_participation": False,
    }


def _artifact_ref(
    validation: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "annotator_id": validation["annotator_id"],
        "annotator_role": validation["annotator_role"],
        "submission_id": validation["submission_id"],
        "sha256": validation["submission_sha256"],
    }


def _cohen_kappa(values_a: Sequence[Any], values_b: Sequence[Any]) -> float | None:
    if len(values_a) != len(values_b) or not values_a:
        raise NDPCPAScreenWorkflowError("kappa inputs must be non-empty and aligned")
    observed = sum(a == b for a, b in zip(values_a, values_b)) / len(values_a)
    labels = set(values_a) | set(values_b)
    expected = sum(
        (values_a.count(label) / len(values_a))
        * (values_b.count(label) / len(values_b))
        for label in labels
    )
    if expected == 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def build_disagreement_worksheet(
    submission_a: Mapping[str, Any],
    submission_b: Mapping[str, Any],
    neutral: Mapping[str, Any],
    *,
    evidence_registry: Mapping[
        str, Mapping[str, Mapping[str, Any]]
    ],
    source_bundle_manifest: Mapping[str, Any],
    submission_a_sha256: str | None = None,
    submission_b_sha256: str | None = None,
    neutral_sha256: str | None = None,
) -> Dict[str, Any]:
    validation_a = validate_independent_screen(
        submission_a,
        neutral,
        evidence_registry=evidence_registry,
        source_bundle_manifest=source_bundle_manifest,
        submission_sha256=submission_a_sha256,
        neutral_sha256=neutral_sha256,
    )
    validation_b = validate_independent_screen(
        submission_b,
        neutral,
        evidence_registry=evidence_registry,
        source_bundle_manifest=source_bundle_manifest,
        submission_sha256=submission_b_sha256,
        neutral_sha256=neutral_sha256,
    )
    if validation_a["annotator_id"] == validation_b["annotator_id"]:
        raise NDPCPAScreenWorkflowError(
            "independent submissions require distinct annotators"
        )
    if validation_a["submission_id"] == validation_b["submission_id"]:
        raise NDPCPAScreenWorkflowError(
            "independent submissions require distinct submission IDs"
        )
    roles = {
        validation_a["annotator_role"],
        validation_b["annotator_role"],
    }
    if not roles.intersection(CURATOR_ROLES) or (
        "annotation_methodologist" not in roles
    ):
        raise NDPCPAScreenWorkflowError(
            "CPA screen pair must include a curator and annotation methodologist"
        )
    neutral_order, neutral_cases = _neutral_contract(neutral)
    _, cases_a = _case_map(submission_a["cases"], label="submission_a.cases")
    _, cases_b = _case_map(submission_b["cases"], label="submission_b.cases")
    cases = []
    disagreement_count = 0
    for case_id in neutral_order:
        slots = []
        for slot in DECISION_SLOTS:
            value_a = cases_a[case_id][slot]
            value_b = cases_b[case_id][slot]
            agreed = value_a == value_b
            disagreement_count += int(not agreed)
            slots.append(
                {
                    "slot": slot,
                    "value_a": value_a,
                    "value_b": value_b,
                    "agreed": agreed,
                    "status": (
                        "agreed"
                        if agreed
                        else "pending_human_adjudication"
                    ),
                }
            )
        cases.append(
            {
                "case_id": case_id,
                "dataset_id": neutral_cases[case_id]["dataset_id"],
                "split": neutral_cases[case_id]["split"],
                "slots": slots,
            }
        )
    slot_count = len(neutral_order) * len(DECISION_SLOTS)
    agreement_count = slot_count - disagreement_count
    per_slot_agreement = {}
    for slot in DECISION_SLOTS:
        values_a = [cases_a[case_id][slot] for case_id in neutral_order]
        values_b = [cases_b[case_id][slot] for case_id in neutral_order]
        agreements = sum(a == b for a, b in zip(values_a, values_b))
        kappa = _cohen_kappa(values_a, values_b)
        per_slot_agreement[slot] = {
            "case_count": len(neutral_order),
            "agreement_count": agreements,
            "agreement_rate": agreements / len(neutral_order),
            "cohen_kappa": kappa,
            "cohen_kappa_status": (
                "defined"
                if kappa is not None
                else "undefined_degenerate_marginals"
            ),
        }
    return {
        "schema_version": DISAGREEMENT_SCHEMA_VERSION,
        "status": (
            "ready_for_human_adjudication"
            if disagreement_count
            else "no_disagreements_consensus_documentation_required"
        ),
        "neutral_screen_sha256": validation_a["neutral_screen_sha256"],
        "opportunity_manifest": neutral["opportunity_manifest"],
        "source_bundle_manifest": dict(source_bundle_manifest),
        "submission_a": _artifact_ref(validation_a),
        "submission_b": _artifact_ref(validation_b),
        "decision_slots": list(DECISION_SLOTS),
        "counts": {
            "case_count": len(neutral_order),
            "slot_count": slot_count,
            "agreement_count": agreement_count,
            "disagreement_count": disagreement_count,
            "agreement_rate": agreement_count / slot_count,
        },
        "per_slot_agreement": per_slot_agreement,
        "cases": cases,
        "automatic_adjudication": False,
    }


def build_consensus_template(
    submission_a: Mapping[str, Any],
    submission_b: Mapping[str, Any],
    neutral: Mapping[str, Any],
    worksheet: Mapping[str, Any],
    *,
    evidence_registry: Mapping[
        str, Mapping[str, Mapping[str, Any]]
    ],
    source_bundle_manifest: Mapping[str, Any],
    submission_a_sha256: str | None = None,
    submission_b_sha256: str | None = None,
    neutral_sha256: str | None = None,
    worksheet_sha256: str | None = None,
) -> Dict[str, Any]:
    expected = build_disagreement_worksheet(
        submission_a,
        submission_b,
        neutral,
        evidence_registry=evidence_registry,
        source_bundle_manifest=source_bundle_manifest,
        submission_a_sha256=submission_a_sha256,
        submission_b_sha256=submission_b_sha256,
        neutral_sha256=neutral_sha256,
    )
    if worksheet != expected:
        raise NDPCPAScreenWorkflowError(
            "worksheet does not exactly match the two frozen submissions"
        )
    cases = []
    for item in worksheet["cases"]:
        decisions: Dict[str, Any] = {}
        resolutions = []
        for slot in item["slots"]:
            decisions[slot["slot"]] = (
                slot["value_a"] if slot["agreed"] else None
            )
            if not slot["agreed"]:
                resolutions.append(
                    {
                        "slot": slot["slot"],
                        "selected_value": None,
                        "rationale": None,
                        "evidence_refs": [],
                    }
                )
        cases.append(
            {
                "case_id": item["case_id"],
                **decisions,
                "cpa_applicable": None,
                "consensus_rationale": None,
                "evidence_refs": [],
                "resolutions": resolutions,
            }
        )
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
        "neutral_screen_sha256": expected["neutral_screen_sha256"],
        "opportunity_manifest": expected["opportunity_manifest"],
        "source_bundle_manifest": expected["source_bundle_manifest"],
        "submission_a": expected["submission_a"],
        "submission_b": expected["submission_b"],
        "disagreement_worksheet": {
            "sha256": worksheet_sha256 or _sha256_payload(worksheet)
        },
        "automatic_adjudication": False,
        "cases": cases,
        "completion_attestation": None,
    }


def _worksheet_case_map(
    worksheet: Mapping[str, Any],
) -> Dict[str, Mapping[str, Any]]:
    _, mapped = _case_map(worksheet.get("cases"), label="worksheet.cases")
    return mapped


def validate_consensus(
    consensus: Mapping[str, Any],
    submission_a: Mapping[str, Any],
    submission_b: Mapping[str, Any],
    neutral: Mapping[str, Any],
    worksheet: Mapping[str, Any],
    *,
    evidence_registry: Mapping[
        str, Mapping[str, Mapping[str, Any]]
    ],
    source_bundle_manifest: Mapping[str, Any],
    submission_a_sha256: str | None = None,
    submission_b_sha256: str | None = None,
    neutral_sha256: str | None = None,
    worksheet_sha256: str | None = None,
    consensus_sha256: str | None = None,
) -> Dict[str, Any]:
    expected_worksheet = build_disagreement_worksheet(
        submission_a,
        submission_b,
        neutral,
        evidence_registry=evidence_registry,
        source_bundle_manifest=source_bundle_manifest,
        submission_a_sha256=submission_a_sha256,
        submission_b_sha256=submission_b_sha256,
        neutral_sha256=neutral_sha256,
    )
    if worksheet != expected_worksheet:
        raise NDPCPAScreenWorkflowError(
            "worksheet does not exactly match the two frozen submissions"
        )
    expected_worksheet_hash = worksheet_sha256 or _sha256_payload(worksheet)
    if consensus.get("schema_version") != CONSENSUS_SCHEMA_VERSION:
        raise NDPCPAScreenWorkflowError("unexpected consensus schema")
    if consensus.get("status") != "consensus_frozen":
        raise NDPCPAScreenWorkflowError(
            "consensus status must be consensus_frozen"
        )
    if consensus.get("annotation_stage") != "post_freeze_human_consensus":
        raise NDPCPAScreenWorkflowError("unexpected consensus stage")
    if consensus.get("automatic_adjudication") is not False:
        raise NDPCPAScreenWorkflowError(
            "automatic adjudication must remain false"
        )
    adjudicator_id = _require_identifier(
        consensus.get("adjudicator_id"), "adjudicator_id"
    )
    adjudicator_role = _require_identifier(
        consensus.get("adjudicator_role"), "adjudicator_role"
    )
    if adjudicator_role not in CONSENSUS_ADJUDICATOR_ROLES:
        raise NDPCPAScreenWorkflowError(
            f"unsupported adjudicator_role {adjudicator_role!r}"
        )
    _require_nonempty_text(
        consensus.get("qualification_summary"),
        "qualification_summary",
    )
    if consensus.get("conflict_of_interest_declared") is not False:
        raise NDPCPAScreenWorkflowError(
            "CPA adjudicator must declare no unresolved conflict"
        )
    if consensus.get("developer_participation") is not False:
        raise NDPCPAScreenWorkflowError(
            "CPA adjudicator must be a non-developer"
        )
    if consensus.get("prior_stage_participation") is not False:
        raise NDPCPAScreenWorkflowError(
            "CPA adjudicator must be fresh from independent screens"
        )
    prior_annotator_ids = {
        expected_worksheet.get("submission_a", {}).get("annotator_id"),
        expected_worksheet.get("submission_b", {}).get("annotator_id"),
    }
    if adjudicator_id in prior_annotator_ids:
        raise NDPCPAScreenWorkflowError(
            "CPA adjudicator must be distinct from prior annotators"
        )
    for key in (
        "neutral_screen_sha256",
        "opportunity_manifest",
        "source_bundle_manifest",
        "submission_a",
        "submission_b",
    ):
        if consensus.get(key) != expected_worksheet.get(key):
            raise NDPCPAScreenWorkflowError(
                f"consensus mutates frozen binding {key}"
            )
    if consensus.get("disagreement_worksheet") != {
        "sha256": expected_worksheet_hash
    }:
        raise NDPCPAScreenWorkflowError(
            "consensus does not bind the exact disagreement worksheet"
        )

    neutral_order, neutral_cases = _neutral_contract(neutral)
    consensus_order, consensus_cases = _case_map(
        consensus.get("cases"), label="consensus.cases"
    )
    if consensus_order != neutral_order:
        raise NDPCPAScreenWorkflowError(
            "consensus case order or identity differs from the neutral screen"
        )
    worksheet_cases = _worksheet_case_map(worksheet)
    resolution_count = 0
    applicable_count = 0
    for case_id in neutral_order:
        case = consensus_cases[case_id]
        worksheet_case = worksheet_cases[case_id]
        slot_records = {
            item["slot"]: item for item in worksheet_case["slots"]
        }
        resolutions = case.get("resolutions")
        if not isinstance(resolutions, list):
            raise NDPCPAScreenWorkflowError(
                f"case {case_id}.resolutions must be a list"
            )
        resolution_map: Dict[str, Mapping[str, Any]] = {}
        for resolution in resolutions:
            if not isinstance(resolution, Mapping):
                raise NDPCPAScreenWorkflowError(
                    f"case {case_id} contains an invalid resolution"
                )
            slot = resolution.get("slot")
            if slot in resolution_map or slot not in DECISION_SLOTS:
                raise NDPCPAScreenWorkflowError(
                    f"case {case_id} contains an invalid/duplicate resolution slot"
                )
            resolution_map[str(slot)] = resolution

        expected_resolution_slots = {
            slot
            for slot, record in slot_records.items()
            if not record["agreed"]
        }
        if set(resolution_map) != expected_resolution_slots:
            raise NDPCPAScreenWorkflowError(
                f"case {case_id} must resolve every and only disagreed slot"
            )
        for slot, record in slot_records.items():
            final_value = case.get(slot)
            if record["agreed"]:
                if final_value != record["value_a"]:
                    raise NDPCPAScreenWorkflowError(
                        f"case {case_id} mutates agreed slot {slot}"
                    )
            else:
                resolution = resolution_map[slot]
                if final_value != resolution.get("selected_value"):
                    raise NDPCPAScreenWorkflowError(
                        f"case {case_id} final value differs from resolution for {slot}"
                    )
                _require_nonempty_text(
                    resolution.get("rationale"),
                    f"case {case_id}.resolution[{slot}].rationale",
                )
                _validate_evidence_refs(
                    resolution.get("evidence_refs"),
                    label=(
                        f"case {case_id}.resolution[{slot}].evidence_refs"
                    ),
                    case_id=case_id,
                    evidence_registry=evidence_registry,
                    subject_field_path=(
                        case.get(SUBJECT_SLOT)
                        if slot
                        in {
                            "single_subject_column_supported",
                            SUBJECT_SLOT,
                        }
                        and case.get("single_subject_column_supported")
                        else None
                    ),
                    required_purposes=(
                        (
                            "cpa_relational_table_assessment",
                        )
                        if slot == "relational_table_applicable"
                        else (
                            "cpa_property_annotation_assessment",
                        )
                        if slot == "property_annotation_applicable"
                        else ("cpa_subject_column_assessment",)
                    ),
                )
                resolution_count += 1
        _validate_decisions(
            case,
            field_paths=neutral_cases[case_id]["field_paths"],
            label=f"consensus case {case_id}",
        )
        _require_nonempty_text(
            case.get("consensus_rationale"),
            f"case {case_id}.consensus_rationale",
        )
        _validate_evidence_refs(
            case.get("evidence_refs"),
            label=f"case {case_id}.evidence_refs",
            case_id=case_id,
            evidence_registry=evidence_registry,
            subject_field_path=(
                case[SUBJECT_SLOT]
                if case["single_subject_column_supported"]
                else None
            ),
            required_purposes=(
                "cpa_relational_table_assessment",
                "cpa_subject_column_assessment",
                "cpa_property_annotation_assessment",
            ),
        )
        derived_applicable = all(case[slot] for slot in BOOLEAN_SLOTS) and (
            case[SUBJECT_SLOT] is not None
        )
        if case.get("cpa_applicable") is not derived_applicable:
            raise NDPCPAScreenWorkflowError(
                f"case {case_id}.cpa_applicable is not deterministically derived"
            )
        applicable_count += int(derived_applicable)
    if consensus.get("completion_attestation") is not True:
        raise NDPCPAScreenWorkflowError(
            "consensus completion_attestation must be true"
        )
    return {
        "schema_version": CONSENSUS_VALIDATION_SCHEMA_VERSION,
        "status": "passed",
        "adjudicator_id": adjudicator_id,
        "adjudicator_role": adjudicator_role,
        "adjudicator_independent_of_prior_screens": True,
        "consensus_sha256": consensus_sha256
        or _sha256_payload(consensus),
        "worksheet_sha256": expected_worksheet_hash,
        "case_count": len(neutral_order),
        "resolved_disagreement_count": resolution_count,
        "cpa_applicable_case_count": applicable_count,
        "automatic_adjudication": False,
    }


def build_workflow_manifest(
    neutral: Mapping[str, Any],
    *,
    neutral_sha256: str,
    implementation_file: Path,
    source_bundle_manifest: Mapping[str, Any],
    source_bundle_approved: bool,
    evidence_registry: Mapping[
        str, Mapping[str, Mapping[str, Any]]
    ],
) -> Dict[str, Any]:
    order, cases = _neutral_contract(neutral)
    missing_evidence_cases = [
        case_id for case_id in order if case_id not in evidence_registry
    ]
    if missing_evidence_cases:
        raise NDPCPAScreenWorkflowError(
            "source-bundle manifest lacks CPA cases: "
            f"{missing_evidence_cases}"
        )
    split_counts = Counter(cases[case_id]["split"] for case_id in order)
    return {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "status": (
            "ready_for_independent_screening"
            if source_bundle_approved
            else "workflow_validated_screening_blocked_on_source_approval"
        ),
        "neutral_screen": {
            "sha256": neutral_sha256,
            "schema_version": SCREEN_SCHEMA_VERSION,
        },
        "opportunity_manifest": neutral["opportunity_manifest"],
        "source_bundle_manifest": dict(source_bundle_manifest),
        "implementation": {
            "file": implementation_file.name,
            "sha256": _sha256_file(implementation_file),
        },
        "implementation_dependencies": {
            path.name: _sha256_file(path)
            for path in (
                implementation_file.with_name("ndp50_source_approval.py"),
                implementation_file.with_name("semantic_gold_workflow.py"),
            )
        },
        "case_count": len(order),
        "dataset_cluster_count": len(
            {cases[case_id]["dataset_id"] for case_id in order}
        ),
        "split_case_counts": dict(sorted(split_counts.items())),
        "required_independent_submissions": 2,
        "required_distinct_annotators": 2,
        "required_role_coverage": [
            "one_domain_or_scientific_metadata_curator",
            "one_annotation_methodologist",
        ],
        "annotator_qualification_and_conflict_required": True,
        "required_consensus_adjudicators": 1,
        "consensus_adjudicator_fresh_from_screens": True,
        "consensus_adjudicator_qualification_and_conflict_required": True,
        "model_outputs_visible_during_screening": False,
        "developer_participation": False,
        "sequence": [
            "copy_and_complete_neutral_screen_independently",
            "validate_and_content_hash_each_submission",
            "reveal_deterministic_disagreement_worksheet_only_after_both_freeze",
            "resolve_every_disagreement_by_human_review",
            "validate_and_freeze_consensus",
        ],
        "automatic_adjudication": False,
        "human_decisions_present": False,
        "screening_execution_authorized": source_bundle_approved,
        "evidence_catalog_case_count": len(order),
        "evidence_binding_complete": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and reconcile blind NDP-50 CPA screens."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    independent = subparsers.add_parser("validate-independent")
    independent.add_argument("--screen", type=Path, required=True)
    independent.add_argument("--neutral", type=Path, required=True)
    independent.add_argument("--source-bundle-manifest", type=Path, required=True)
    independent.add_argument("--output", type=Path, required=True)

    compare = subparsers.add_parser("compare")
    compare.add_argument("--screen-a", type=Path, required=True)
    compare.add_argument("--screen-b", type=Path, required=True)
    compare.add_argument("--neutral", type=Path, required=True)
    compare.add_argument("--source-bundle-manifest", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)

    consensus_template = subparsers.add_parser("build-consensus-template")
    consensus_template.add_argument("--screen-a", type=Path, required=True)
    consensus_template.add_argument("--screen-b", type=Path, required=True)
    consensus_template.add_argument("--neutral", type=Path, required=True)
    consensus_template.add_argument(
        "--source-bundle-manifest", type=Path, required=True
    )
    consensus_template.add_argument("--worksheet", type=Path, required=True)
    consensus_template.add_argument("--output", type=Path, required=True)

    consensus = subparsers.add_parser("validate-consensus")
    consensus.add_argument("--screen-a", type=Path, required=True)
    consensus.add_argument("--screen-b", type=Path, required=True)
    consensus.add_argument("--neutral", type=Path, required=True)
    consensus.add_argument("--source-bundle-manifest", type=Path, required=True)
    consensus.add_argument("--worksheet", type=Path, required=True)
    consensus.add_argument("--consensus", type=Path, required=True)
    consensus.add_argument("--output", type=Path, required=True)

    workflow = subparsers.add_parser("build-workflow-manifest")
    workflow.add_argument("--neutral", type=Path, required=True)
    workflow.add_argument("--source-bundle-manifest", type=Path, required=True)
    workflow.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    neutral = _load_json(args.neutral)
    neutral_hash = _sha256_file(args.neutral)
    evidence_registry, source_bundle_binding, source_bundle_approved = (
        load_evidence_registry(
            args.source_bundle_manifest,
            require_approved=args.command != "build-workflow-manifest",
        )
    )
    evidence_kwargs = {
        "evidence_registry": evidence_registry,
        "source_bundle_manifest": source_bundle_binding,
    }
    if args.command == "validate-independent":
        payload = validate_independent_screen(
            _load_json(args.screen),
            neutral,
            **evidence_kwargs,
            submission_sha256=_sha256_file(args.screen),
            neutral_sha256=neutral_hash,
        )
    elif args.command in {"compare", "build-consensus-template"}:
        screen_a = _load_json(args.screen_a)
        screen_b = _load_json(args.screen_b)
        kwargs = {
            "submission_a_sha256": _sha256_file(args.screen_a),
            "submission_b_sha256": _sha256_file(args.screen_b),
            "neutral_sha256": neutral_hash,
            **evidence_kwargs,
        }
        if args.command == "compare":
            payload = build_disagreement_worksheet(
                screen_a, screen_b, neutral, **kwargs
            )
        else:
            worksheet = _load_json(args.worksheet)
            payload = build_consensus_template(
                screen_a,
                screen_b,
                neutral,
                worksheet,
                worksheet_sha256=_sha256_file(args.worksheet),
                **kwargs,
            )
    elif args.command == "validate-consensus":
        screen_a = _load_json(args.screen_a)
        screen_b = _load_json(args.screen_b)
        worksheet = _load_json(args.worksheet)
        payload = validate_consensus(
            _load_json(args.consensus),
            screen_a,
            screen_b,
            neutral,
            worksheet,
            submission_a_sha256=_sha256_file(args.screen_a),
            submission_b_sha256=_sha256_file(args.screen_b),
            neutral_sha256=neutral_hash,
            worksheet_sha256=_sha256_file(args.worksheet),
            consensus_sha256=_sha256_file(args.consensus),
            **evidence_kwargs,
        )
    else:
        payload = build_workflow_manifest(
            neutral,
            neutral_sha256=neutral_hash,
            implementation_file=Path(__file__),
            source_bundle_manifest=source_bundle_binding,
            source_bundle_approved=source_bundle_approved,
            evidence_registry=evidence_registry,
        )
    _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
