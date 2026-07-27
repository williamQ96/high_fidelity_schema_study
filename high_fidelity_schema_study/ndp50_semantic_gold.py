from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .ndp50_source_approval import load_approved_evidence_registry
from .semantic_gold_workflow import (
    validate_consensus_artifact,
    validate_vocabulary,
)


INDEX_SCHEMA_VERSION = "ndp50-semantic-gold-corpus-index/v1"
WORKFLOW_SCHEMA_VERSION = "ndp50-semantic-gold-workflow-spec/v1"
APPROVAL_SCHEMA_VERSION = "ndp50-semantic-gold-approval/v1"
VALIDATION_SCHEMA_VERSION = "ndp50-semantic-gold-validation/v1"
APPROVAL_VALIDATION_SCHEMA_VERSION = (
    "ndp50-semantic-gold-approval-validation/v1"
)
REQUIRED_ARTIFACT_KEYS = (
    "annotation_a",
    "annotation_b",
    "disagreement_report",
    "consensus",
)
ANNOTATOR_ROLES = {
    "domain_curator",
    "scientific_metadata_curator",
    "annotation_methodologist",
}
CURATOR_ROLES = {"domain_curator", "scientific_metadata_curator"}


class NDPSemanticGoldError(ValueError):
    pass


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_date(value: Any) -> bool:
    try:
        date.fromisoformat(str(value or ""))
    except ValueError:
        return False
    return True


def _study_relative(path: Path, study_root: Path) -> str:
    try:
        return path.resolve().relative_to(study_root.resolve()).as_posix()
    except ValueError as exc:
        raise NDPSemanticGoldError(
            f"artifact must be inside the study root: {path}"
        ) from exc


def _binding(path: Path, study_root: Path) -> Dict[str, str]:
    if not path.is_file():
        raise NDPSemanticGoldError(f"artifact does not exist: {path}")
    return {
        "file": _study_relative(path, study_root),
        "sha256": _sha256_file(path),
    }


def _bound_path(
    ref: Mapping[str, Any],
    *,
    study_root: Path,
    label: str,
) -> Path:
    value = ref.get("file")
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise NDPSemanticGoldError(f"{label} must use a study-relative file")
    root = study_root.resolve()
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise NDPSemanticGoldError(
            f"{label} escapes the study root"
        ) from exc
    if not path.is_file():
        raise NDPSemanticGoldError(f"{label} does not exist")
    if _sha256_file(path) != ref.get("sha256"):
        raise NDPSemanticGoldError(f"{label} hash mismatch")
    return path


def _owner_bound_path(
    ref: Mapping[str, Any],
    *,
    owner_path: Path,
    study_root: Path,
    label: str,
) -> Path:
    value = ref.get("file")
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise NDPSemanticGoldError(f"{label} must use a relative file")
    root = study_root.resolve()
    path = (owner_path.parent / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise NDPSemanticGoldError(
            f"{label} escapes the study root"
        ) from exc
    if not path.is_file():
        raise NDPSemanticGoldError(f"{label} does not exist")
    if _sha256_file(path) != ref.get("sha256"):
        raise NDPSemanticGoldError(f"{label} hash mismatch")
    return path


def _packet_manifest(path: Path) -> Dict[str, Any]:
    payload = _load_json(path)
    if (
        payload.get("schema_version") != "ndp50-semantic-packet-pack/v1"
        or payload.get("status")
        != "neutral_packets_ready_source_bundles_blocked"
    ):
        raise NDPSemanticGoldError("unexpected packet manifest")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise NDPSemanticGoldError("packet manifest has no cases")
    case_ids = [str(item.get("case_id") or "") for item in cases]
    if (
        any(not value for value in case_ids)
        or len(case_ids) != len(set(case_ids))
        or any(item.get("split") not in {"development", "validation"} for item in cases)
    ):
        raise NDPSemanticGoldError(
            "packet cases must be unique development/validation cases"
        )
    if payload.get("case_count") != len(cases):
        raise NDPSemanticGoldError("packet case count mismatch")
    return payload


def build_index_template(
    *,
    packet_manifest_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    packet_manifest = _packet_manifest(packet_manifest_path)
    cases = [
        {
            "case_id": item["case_id"],
            "split": item["split"],
            "packet_sha256": item["packet_sha256"],
            **{key: None for key in REQUIRED_ARTIFACT_KEYS},
        }
        for item in packet_manifest["cases"]
    ]
    cases.sort(key=lambda item: (item["split"], item["case_id"]))
    return {
        "schema_version": INDEX_SCHEMA_VERSION,
        "status": "neutral_pending_gold_artifacts",
        "human_decisions_present": False,
        "model_outputs_visible_to_annotators": False,
        "packet_manifest": _binding(packet_manifest_path, study_root),
        "approved_source_manifest": None,
        "frozen_vocabulary": None,
        "required_stable_annotator_count": 2,
        "annotator_registry": [
            {
                "slot": "annotation_a",
                "annotator_id": None,
                "reviewer_role": None,
                "institution": None,
                "qualification_summary": None,
                "conflict_of_interest_declared": None,
                "developer_participation": False,
                "signed_on": None,
            },
            {
                "slot": "annotation_b",
                "annotator_id": None,
                "reviewer_role": None,
                "institution": None,
                "qualification_summary": None,
                "conflict_of_interest_declared": None,
                "developer_participation": False,
                "signed_on": None,
            },
        ],
        "consensus_panel": {
            "member_ids": [],
            "joint_human_consensus_attested": None,
            "automatic_adjudication": False,
        },
        "cases": cases,
        "completion_attestation": None,
    }


def build_workflow_spec(
    *,
    packet_manifest_path: Path,
    index_template_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    expected_template = build_index_template(
        packet_manifest_path=packet_manifest_path,
        study_root=study_root,
    )
    if _load_json(index_template_path) != expected_template:
        raise NDPSemanticGoldError(
            "gold index template is not the canonical neutral template"
        )
    implementation = Path(__file__).resolve()
    return {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "status": (
            "implementation_ready_waiting_on_frozen_vocabulary_and_"
            "approved_sources"
        ),
        "human_decisions_present": False,
        "model_outputs_visible_during_annotation": False,
        "packet_manifest": _binding(packet_manifest_path, study_root),
        "neutral_index_template": _binding(index_template_path, study_root),
        "required_stable_annotator_count": 2,
        "required_distinct_annotators": True,
        "automatic_adjudication": False,
        "consensus_governance": {
            "mode": "joint_consensus_by_same_qualified_annotator_pair",
            "panel_member_ids_must_equal_annotator_registry": True,
            "separate_adjudicator_required": False,
            "rationale": (
                "Semantic gold consensus reconciles the same blind field-level "
                "judgments; both panel members are already role-qualified, "
                "conflict-cleared non-developers across the full corpus."
            ),
        },
        "unresolved_consensus_slots_allowed_for_completion": False,
        "required_evidence_purpose": "general_semantic_annotation",
        "sequence": [
            "freeze_vocabulary",
            "approve_source_evidence",
            "prepare_two_independent_full_corpus_assignments",
            "freeze_both_submission_hashes",
            "generate_deterministic_disagreement_reports",
            "human_consensus_without_model_outputs",
            "validator_generate_gold_approval",
            "rebuild_readiness_and_handoff",
        ],
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            name: _sha256_file(implementation.with_name(name))
            for name in (
                "ndp50_source_approval.py",
                "semantic_gold_workflow.py",
            )
        },
    }


def _artifact_evidence_ids(payload: Mapping[str, Any]) -> set[str]:
    result: set[str] = set()
    for field in payload.get("fields") or []:
        if not isinstance(field, dict):
            continue
        for evidence in field.get("gold_evidence") or []:
            if isinstance(evidence, dict):
                evidence_id = str(
                    evidence.get("catalog_evidence_id") or ""
                )
                if evidence_id:
                    result.add(evidence_id)
    return result


def validate_corpus_index(
    index: Mapping[str, Any],
    *,
    packet_manifest_path: Path,
    approved_source_manifest_path: Path,
    vocabulary_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    errors: list[Dict[str, str]] = []

    def error(code: str, detail: str) -> None:
        errors.append({"code": code, "detail": detail})

    try:
        packet_manifest = _packet_manifest(packet_manifest_path)
        vocabulary = _load_json(vocabulary_path)
        vocabulary_validation = validate_vocabulary(vocabulary)
        if vocabulary_validation.get("status") != "ready":
            error("vocabulary_invalid", "frozen vocabulary did not validate")
        evidence_registry, approved_manifest = (
            load_approved_evidence_registry(approved_source_manifest_path)
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": VALIDATION_SCHEMA_VERSION,
            "status": "blocked",
            "case_count": 0,
            "errors": [
                {"code": "upstream_artifact_invalid", "detail": str(exc)}
            ],
        }

    if index.get("schema_version") != INDEX_SCHEMA_VERSION:
        error("index_schema_invalid", "unexpected corpus-index schema")
    if index.get("status") != "completed_pending_validator_approval":
        error(
            "index_status_invalid",
            "completed index must await validator approval",
        )
    if index.get("human_decisions_present") is not True:
        error(
            "human_decisions_missing",
            "completed gold index must acknowledge human decisions",
        )
    if index.get("model_outputs_visible_to_annotators") is not False:
        error(
            "model_visibility_invalid",
            "model outputs must remain hidden from gold annotators",
        )
    expected_packet_binding = _binding(packet_manifest_path, study_root)
    if index.get("packet_manifest") != expected_packet_binding:
        error("packet_binding_mismatch", "packet manifest binding changed")
    if index.get("approved_source_manifest") != _binding(
        approved_source_manifest_path, study_root
    ):
        error("source_binding_mismatch", "approved source binding changed")
    if index.get("frozen_vocabulary") != _binding(
        vocabulary_path, study_root
    ):
        error("vocabulary_binding_mismatch", "vocabulary binding changed")
    if draft_ref := approved_manifest.get(
        "source_bundle_draft_manifest"
    ):
        if draft_ref.get("vocabulary_sha256") != _sha256_file(
            vocabulary_path
        ):
            error(
                "approved_source_vocabulary_mismatch",
                "approved sources bind a different frozen vocabulary",
            )
    if index.get("required_stable_annotator_count") != 2:
        error(
            "annotator_count_invalid",
            "exactly two stable annotators are required",
        )
    if index.get("completion_attestation") is not True:
        error(
            "completion_not_attested",
            "corpus completion must be explicitly attested",
        )
    registry_items = index.get("annotator_registry")
    if not isinstance(registry_items, list):
        registry_items = []
        error(
            "annotator_registry_missing",
            "annotator_registry must contain both stable slots",
        )
    registry_by_slot = {
        str(item.get("slot") or ""): item
        for item in registry_items
        if isinstance(item, dict)
    }
    if (
        len(registry_by_slot) != len(registry_items)
        or set(registry_by_slot) != {"annotation_a", "annotation_b"}
    ):
        error(
            "annotator_registry_slots_invalid",
            "annotator registry must contain exactly A and B",
        )
    declared_ids: Dict[str, str] = {}
    declared_roles: set[str] = set()
    for slot, item in registry_by_slot.items():
        annotator_id = str(item.get("annotator_id") or "")
        role = str(item.get("reviewer_role") or "")
        if not annotator_id:
            error("annotator_id_missing", f"{slot} annotator_id is required")
        else:
            declared_ids[slot] = annotator_id
        if role not in ANNOTATOR_ROLES:
            error("annotator_role_invalid", f"{slot} reviewer role is invalid")
        else:
            declared_roles.add(role)
        for key in ("institution", "qualification_summary"):
            if not _valid_text(item.get(key)):
                error(
                    f"annotator_{key}_missing",
                    f"{slot}.{key} must be non-empty",
                )
        if item.get("conflict_of_interest_declared") is not False:
            error(
                "annotator_conflict_not_cleared",
                f"{slot} must declare no unresolved conflict",
            )
        if item.get("developer_participation") is not False:
            error(
                "annotator_not_independent",
                f"{slot} must be a non-developer",
            )
        if not _valid_date(item.get("signed_on")):
            error(
                "annotator_signature_date_invalid",
                f"{slot}.signed_on must be an ISO date",
            )
    if declared_ids.get("annotation_a") == declared_ids.get("annotation_b"):
        error(
            "declared_annotators_not_distinct",
            "declared annotators A and B must be distinct",
        )
    if (
        not (declared_roles & CURATOR_ROLES)
        or "annotation_methodologist" not in declared_roles
    ):
        error(
            "annotator_role_coverage_missing",
            "the pair must cover curator and annotation-methodologist roles",
        )
    consensus_panel = index.get("consensus_panel")
    if not isinstance(consensus_panel, dict):
        consensus_panel = {}
        error(
            "consensus_panel_missing",
            "consensus_panel must be an object",
        )
    panel_ids = consensus_panel.get("member_ids")
    if (
        not isinstance(panel_ids, list)
        or len(panel_ids) != 2
        or len(set(str(value) for value in panel_ids)) != 2
    ):
        error(
            "consensus_panel_identity_invalid",
            "consensus panel must contain two distinct member ids",
        )
    if consensus_panel.get("joint_human_consensus_attested") is not True:
        error(
            "consensus_panel_not_attested",
            "joint human consensus must be attested",
        )
    if consensus_panel.get("automatic_adjudication") is not False:
        error(
            "automatic_adjudication_forbidden",
            "automatic adjudication is forbidden",
        )

    expected_cases = {
        str(item["case_id"]): item for item in packet_manifest["cases"]
    }
    actual_cases = index.get("cases")
    if not isinstance(actual_cases, list):
        actual_cases = []
        error("cases_missing", "index cases must be a list")
    actual_by_id = {
        str(item.get("case_id") or ""): item
        for item in actual_cases
        if isinstance(item, dict)
    }
    if (
        len(actual_by_id) != len(actual_cases)
        or set(actual_by_id) != set(expected_cases)
    ):
        error(
            "case_identity_mismatch",
            "gold cases must exactly match the neutral packet manifest",
        )

    approved_cases = {
        str(item["case_id"]): item
        for item in approved_manifest.get("cases") or []
    }
    draft_ref = approved_manifest.get("source_bundle_draft_manifest") or {}
    try:
        draft_manifest_path = _owner_bound_path(
            draft_ref,
            owner_path=approved_source_manifest_path,
            study_root=study_root,
            label="draft source manifest",
        )
    except Exception as exc:  # noqa: BLE001
        error("draft_source_manifest_invalid", str(exc))
        draft_manifest_path = approved_source_manifest_path

    annotator_a_ids: set[str] = set()
    annotator_b_ids: set[str] = set()
    valid_case_count = 0
    unresolved_total = 0
    for case_id in sorted(expected_cases):
        expected = expected_cases[case_id]
        item = actual_by_id.get(case_id)
        if item is None:
            continue
        if item.get("split") != expected.get("split"):
            error("case_split_changed", f"{case_id} changed split")
        if item.get("packet_sha256") != expected.get("packet_sha256"):
            error("packet_hash_changed", f"{case_id} changed packet hash")
        paths: Dict[str, Path] = {}
        for key in REQUIRED_ARTIFACT_KEYS:
            ref = item.get(key)
            if not isinstance(ref, dict):
                error("artifact_binding_missing", f"{case_id}.{key} is missing")
                continue
            try:
                paths[key] = _bound_path(
                    ref,
                    study_root=study_root,
                    label=f"{case_id}.{key}",
                )
            except Exception as exc:  # noqa: BLE001
                error("artifact_binding_invalid", str(exc))
        approved_case = approved_cases.get(case_id)
        if approved_case is None:
            error(
                "approved_source_case_missing",
                f"{case_id} is absent from approved sources",
            )
            continue
        packet_path = (
            packet_manifest_path.parent / str(expected["packet_file"])
        ).resolve()
        bundle_path = (
            draft_manifest_path.parent
            / str(approved_case["draft_bundle_file"])
        ).resolve()
        if (
            not packet_path.is_file()
            or _sha256_file(packet_path) != expected["packet_sha256"]
        ):
            error("packet_file_invalid", f"{case_id} packet does not verify")
            continue
        if (
            not bundle_path.is_file()
            or _sha256_file(bundle_path)
            != approved_case["draft_bundle_sha256"]
        ):
            error(
                "source_bundle_file_invalid",
                f"{case_id} source bundle does not verify",
            )
            continue
        if len(paths) != len(REQUIRED_ARTIFACT_KEYS):
            continue
        consensus_validation = validate_consensus_artifact(
            paths["consensus"],
            artifact_a_path=paths["annotation_a"],
            artifact_b_path=paths["annotation_b"],
            disagreement_report_path=paths["disagreement_report"],
            packet_path=packet_path,
            source_bundle_path=bundle_path,
            vocabulary_path=vocabulary_path,
        )
        if consensus_validation.get("status") != "ready":
            error(
                "consensus_invalid",
                f"{case_id} consensus did not replay",
            )
            continue
        unresolved = consensus_validation.get("summary", {}).get(
            "unresolved_count"
        )
        if unresolved != 0:
            error(
                "consensus_unresolved",
                f"{case_id} has unresolved consensus slots",
            )
            unresolved_total += int(unresolved or 0)
            continue
        annotation_a = _load_json(paths["annotation_a"])
        annotation_b = _load_json(paths["annotation_b"])
        annotator_a = str(annotation_a.get("annotator_id") or "")
        annotator_b = str(annotation_b.get("annotator_id") or "")
        if not annotator_a or not annotator_b or annotator_a == annotator_b:
            error(
                "annotators_not_distinct",
                f"{case_id} lacks two distinct annotators",
            )
            continue
        annotator_a_ids.add(annotator_a)
        annotator_b_ids.add(annotator_b)
        allowed = {
            evidence_id
            for evidence_id, evidence in evidence_registry.get(
                case_id, {}
            ).items()
            if "general_semantic_annotation"
            in (evidence.get("approved_purposes") or [])
        }
        evidence_ok = True
        for key in ("annotation_a", "annotation_b", "consensus"):
            used = _artifact_evidence_ids(_load_json(paths[key]))
            unapproved = used - allowed
            if unapproved:
                error(
                    "unapproved_gold_evidence",
                    f"{case_id}.{key} uses evidence not approved for gold",
                )
                evidence_ok = False
        if evidence_ok:
            valid_case_count += 1

    if len(annotator_a_ids) != 1 or len(annotator_b_ids) != 1:
        error(
            "annotator_identity_not_stable",
            "annotator A and B identities must each remain stable across the corpus",
        )
    elif annotator_a_ids == annotator_b_ids:
        error(
            "annotator_roles_not_distinct",
            "the two stable corpus annotators must be distinct",
        )
    else:
        observed = {
            "annotation_a": next(iter(annotator_a_ids)),
            "annotation_b": next(iter(annotator_b_ids)),
        }
        if declared_ids != observed:
            error(
                "annotator_registry_identity_mismatch",
                "declared annotator registry differs from artifact identities",
            )
        if set(str(value) for value in panel_ids or []) != set(
            observed.values()
        ):
            error(
                "consensus_panel_identity_mismatch",
                "consensus panel must be the same two corpus annotators",
            )

    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "status": "passed" if not errors else "blocked",
        "case_count": len(expected_cases),
        "valid_case_count": valid_case_count,
        "stable_annotator_count": len(annotator_a_ids | annotator_b_ids),
        "unresolved_slot_count": unresolved_total,
        "errors": errors,
    }


def build_approval(
    *,
    index: Mapping[str, Any],
    packet_manifest_path: Path,
    approved_source_manifest_path: Path,
    vocabulary_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    validation = validate_corpus_index(
        index,
        packet_manifest_path=packet_manifest_path,
        approved_source_manifest_path=approved_source_manifest_path,
        vocabulary_path=vocabulary_path,
        study_root=study_root,
    )
    if validation["status"] != "passed":
        raise NDPSemanticGoldError(
            "semantic gold corpus is incomplete: "
            + json.dumps(validation["errors"], sort_keys=True)
        )
    implementation = Path(__file__).resolve()
    return {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "status": "approved_independent_gold_complete",
        "index": index,
        "index_content_sha256": hashlib.sha256(
            json.dumps(
                index,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest(),
        "packet_manifest": _binding(packet_manifest_path, study_root),
        "approved_source_manifest": _binding(
            approved_source_manifest_path, study_root
        ),
        "frozen_vocabulary": _binding(vocabulary_path, study_root),
        "validation": validation,
        "derived_gates": {"independent_gold_complete": True},
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            name: _sha256_file(implementation.with_name(name))
            for name in (
                "ndp50_source_approval.py",
                "semantic_gold_workflow.py",
            )
        },
    }


def verify_approval(
    approval: Mapping[str, Any],
    *,
    packet_manifest_path: Path,
    approved_source_manifest_path: Path,
    vocabulary_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    index = approval.get("index")
    if not isinstance(index, dict):
        return {
            "schema_version": APPROVAL_VALIDATION_SCHEMA_VERSION,
            "status": "failed",
            "differing_top_level_keys": ["index"],
        }
    try:
        expected = build_approval(
            index=index,
            packet_manifest_path=packet_manifest_path,
            approved_source_manifest_path=approved_source_manifest_path,
            vocabulary_path=vocabulary_path,
            study_root=study_root,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": APPROVAL_VALIDATION_SCHEMA_VERSION,
            "status": "failed",
            "differing_top_level_keys": ["index"],
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
        description="Prepare and validate NDP-50 corpus-level semantic gold."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--packet-manifest", type=Path, required=True)
    prepare.add_argument("--study-root", type=Path, required=True)
    prepare.add_argument("--index-output", type=Path, required=True)
    prepare.add_argument("--workflow-output", type=Path, required=True)
    for command in ("validate-corpus", "approve-corpus"):
        item = subparsers.add_parser(command)
        item.add_argument("--index", type=Path, required=True)
        item.add_argument("--packet-manifest", type=Path, required=True)
        item.add_argument(
            "--approved-source-manifest", type=Path, required=True
        )
        item.add_argument("--vocabulary", type=Path, required=True)
        item.add_argument("--study-root", type=Path, required=True)
        item.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify-approved")
    verify.add_argument("--approved", type=Path, required=True)
    verify.add_argument("--packet-manifest", type=Path, required=True)
    verify.add_argument(
        "--approved-source-manifest", type=Path, required=True
    )
    verify.add_argument("--vocabulary", type=Path, required=True)
    verify.add_argument("--study-root", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        index = build_index_template(
            packet_manifest_path=args.packet_manifest,
            study_root=args.study_root,
        )
        _write_json(args.index_output, index)
        workflow = build_workflow_spec(
            packet_manifest_path=args.packet_manifest,
            index_template_path=args.index_output,
            study_root=args.study_root,
        )
        _write_json(args.workflow_output, workflow)
        print(
            json.dumps(
                {
                    "status": workflow["status"],
                    "case_count": len(index["cases"]),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    kwargs = {
        "packet_manifest_path": args.packet_manifest,
        "approved_source_manifest_path": args.approved_source_manifest,
        "vocabulary_path": args.vocabulary,
        "study_root": args.study_root,
    }
    if args.command == "validate-corpus":
        payload = validate_corpus_index(_load_json(args.index), **kwargs)
        _write_json(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "passed" else 1
    if args.command == "approve-corpus":
        payload = build_approval(index=_load_json(args.index), **kwargs)
        _write_json(args.output, payload)
        print(json.dumps(payload["derived_gates"], indent=2, sort_keys=True))
        return 0
    payload = verify_approval(_load_json(args.approved), **kwargs)
    _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
