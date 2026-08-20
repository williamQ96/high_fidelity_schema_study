from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .ndp50_data_governance_review import (
    verify_approval as verify_governance_approval,
)
from .ndp50_semantic_gold import verify_approval as verify_gold_approval
from .ndp50_execution_freeze import verify_freeze as verify_execution_freeze
from .ndp50_power_freeze import verify_freeze as verify_power_freeze
from .ndp50_test_execution import verify_test_release_receipt
from .semantic_annotator_calibration import (
    validate_annotator_calibration_summary,
)


SCHEMA_VERSION = "ndp50-human-handoff/v1"
VALIDATION_SCHEMA_VERSION = "ndp50-human-handoff-validation/v1"


class NDPHumanHandoffError(ValueError):
    pass


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _study_relative(path: Path, study_root: Path) -> str:
    try:
        relative = path.resolve().relative_to(study_root.resolve())
    except ValueError as exc:
        raise NDPHumanHandoffError(
            f"handoff input must be inside the study root: {path}"
        ) from exc
    return relative.as_posix()


def _binding(path: Path, study_root: Path) -> Dict[str, str]:
    return {
        "file": _study_relative(path, study_root),
        "sha256": _sha256_file(path),
    }


def _bound_path(
    ref: Any,
    *,
    study_root: Path,
    label: str,
) -> Path:
    if not isinstance(ref, dict):
        raise NDPHumanHandoffError(f"{label} binding is missing")
    value = ref.get("file")
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise NDPHumanHandoffError(
            f"{label} must use a study-relative file"
        )
    root = study_root.resolve()
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise NDPHumanHandoffError(
            f"{label} escapes the study root"
        ) from exc
    if not path.is_file() or _sha256_file(path) != ref.get("sha256"):
        raise NDPHumanHandoffError(f"{label} does not verify")
    return path


def _require_readiness_binding(
    readiness: Mapping[str, Any],
    *,
    key: str,
    path: Path,
) -> None:
    expected = readiness.get("artifact_hashes", {}).get(key)
    actual = _sha256_file(path)
    if expected != actual:
        raise NDPHumanHandoffError(
            f"readiness binding mismatch for {key}: expected {expected}, got {actual}"
        )


def _stage(
    *,
    ordinal: int,
    stage_id: str,
    title: str,
    completed: bool,
    prerequisites_met: bool,
    unlock_evidence: list[str],
    required_outputs: list[str],
    prohibitions: list[str],
) -> Dict[str, Any]:
    status = "completed" if completed else (
        "released" if prerequisites_met else "locked"
    )
    return {
        "ordinal": ordinal,
        "stage_id": stage_id,
        "title": title,
        "status": status,
        "unlock_evidence": unlock_evidence,
        "required_outputs": required_outputs,
        "prohibitions": prohibitions,
    }


def _require_neutral_vocabulary_template(payload: Mapping[str, Any]) -> None:
    required_false = (
        "developer_participation",
        "model_outputs_visible",
        "other_review_visible_before_freeze",
    )
    for key in required_false:
        if payload.get(key) is not False:
            raise NDPHumanHandoffError(
                f"neutral vocabulary template requires {key}=false"
            )
    required_null = (
        "qualification_summary",
        "conflict_of_interest_declared",
        "completion_attestation",
        "policy_rationale",
    )
    for key in required_null:
        if payload.get(key) is not None:
            raise NDPHumanHandoffError(
                f"neutral vocabulary template requires {key}=null"
            )
    for key in ("reviewer_id", "reviewer_role", "submission_id"):
        value = str(payload.get(key) or "").casefold()
        if "replace-with" not in value:
            raise NDPHumanHandoffError(
                f"neutral vocabulary template requires a placeholder {key}"
            )
    if payload.get("proposals") != []:
        raise NDPHumanHandoffError(
            "neutral vocabulary template must not contain proposals"
        )
    if any(
        value is not None
        for value in (payload.get("policy_decisions") or {}).values()
    ):
        raise NDPHumanHandoffError(
            "neutral vocabulary template must not contain policy decisions"
        )
    for item in payload.get("case_reviews") or []:
        if (
            item.get("coverage_adequate") is not None
            or item.get("concepts_missing") != []
            or item.get("evidence_refs") != []
            or item.get("rationale") is not None
        ):
            raise NDPHumanHandoffError(
                "neutral vocabulary template contains case-level decisions"
            )


def build_handoff(
    *,
    readiness_path: Path,
    packet_manifest_path: Path,
    vocabulary_path: Path,
    vocabulary_workflow_path: Path,
    vocabulary_template_path: Path,
    source_approval_spec_path: Path,
    source_bundle_manifest_path: Path,
    cpa_workflow_path: Path,
    cpa_screen_path: Path,
    cpa_design_path: Path,
    power_feasibility_path: Path,
    power_policy_template_path: Path,
    power_freeze_workflow_path: Path,
    data_governance_path: Path,
    data_governance_review_template_path: Path,
    data_governance_review_workflow_path: Path,
    semantic_gold_index_template_path: Path,
    semantic_gold_workflow_spec_path: Path,
    demonstration_pool_workflow_spec_path: Path,
    execution_freeze_config_template_path: Path,
    execution_freeze_workflow_path: Path,
    test_execution_workflow_path: Path,
    publication_gate_workflow_path: Path,
    feedback_response_signoff_template_path: Path,
    study_root: Path,
    cpa_consensus_path: Path | None = None,
    data_governance_approval_path: Path | None = None,
    semantic_gold_approval_path: Path | None = None,
    annotator_calibration_summary_path: Path | None = None,
    execution_freeze_path: Path | None = None,
    completed_power_policy_path: Path | None = None,
    development_calibration_report_path: Path | None = None,
    power_freeze_path: Path | None = None,
    test_release_authorization_path: Path | None = None,
    test_release_receipt_path: Path | None = None,
) -> Dict[str, Any]:
    paths = {
        "readiness": readiness_path,
        "packet_manifest": packet_manifest_path,
        "vocabulary": vocabulary_path,
        "vocabulary_review_workflow": vocabulary_workflow_path,
        "vocabulary_review_template": vocabulary_template_path,
        "source_approval_workflow_spec": source_approval_spec_path,
        "source_bundle_manifest": source_bundle_manifest_path,
        "cpa_workflow": cpa_workflow_path,
        "cpa_screen": cpa_screen_path,
        "cpa_design": cpa_design_path,
        "semantic_power_feasibility": power_feasibility_path,
        "power_policy_template": power_policy_template_path,
        "power_freeze_workflow": power_freeze_workflow_path,
        "data_governance": data_governance_path,
        "data_governance_review_template": (
            data_governance_review_template_path
        ),
        "data_governance_review_workflow": (
            data_governance_review_workflow_path
        ),
        "semantic_gold_index_template": semantic_gold_index_template_path,
        "semantic_gold_workflow_spec": semantic_gold_workflow_spec_path,
        "demonstration_pool_workflow_spec": (
            demonstration_pool_workflow_spec_path
        ),
        "execution_freeze_config_template": (
            execution_freeze_config_template_path
        ),
        "execution_freeze_workflow": execution_freeze_workflow_path,
        "test_execution_workflow": test_execution_workflow_path,
        "publication_gate_workflow": publication_gate_workflow_path,
        "feedback_response_signoff_template": (
            feedback_response_signoff_template_path
        ),
    }
    if cpa_consensus_path is not None:
        paths["cpa_consensus"] = cpa_consensus_path
    if data_governance_approval_path is not None:
        paths["data_governance_approval"] = data_governance_approval_path
    if semantic_gold_approval_path is not None:
        paths["semantic_gold_approval"] = semantic_gold_approval_path
    if annotator_calibration_summary_path is not None:
        paths["annotator_calibration_summary"] = (
            annotator_calibration_summary_path
        )
    if execution_freeze_path is not None:
        paths["execution_freeze"] = execution_freeze_path
    power_completion_paths = (
        completed_power_policy_path,
        development_calibration_report_path,
        power_freeze_path,
    )
    if any(path is not None for path in power_completion_paths) and not all(
        path is not None for path in power_completion_paths
    ):
        raise NDPHumanHandoffError(
            "power completion requires policy, calibration report, and freeze"
        )
    if completed_power_policy_path is not None:
        assert development_calibration_report_path is not None
        assert power_freeze_path is not None
        paths["completed_power_policy"] = completed_power_policy_path
        paths["development_calibration_report"] = (
            development_calibration_report_path
        )
        paths["power_freeze"] = power_freeze_path
    release_paths = (
        test_release_authorization_path,
        test_release_receipt_path,
    )
    if any(path is not None for path in release_paths) and not all(
        path is not None for path in release_paths
    ):
        raise NDPHumanHandoffError(
            "test release requires both authorization and validator receipt"
        )
    if test_release_authorization_path is not None:
        assert test_release_receipt_path is not None
        paths["test_release_authorization"] = (
            test_release_authorization_path
        )
        paths["test_release_receipt"] = test_release_receipt_path
    for label, path in paths.items():
        if not path.is_file():
            raise NDPHumanHandoffError(f"{label} does not exist: {path}")

    readiness = _load_json(readiness_path)
    packet_manifest = _load_json(packet_manifest_path)
    vocabulary_workflow = _load_json(vocabulary_workflow_path)
    vocabulary_template = _load_json(vocabulary_template_path)
    source_approval_spec = _load_json(source_approval_spec_path)
    cpa_workflow = _load_json(cpa_workflow_path)
    cpa_screen = _load_json(cpa_screen_path)
    cpa_design = _load_json(cpa_design_path)
    power_feasibility = _load_json(power_feasibility_path)
    power_policy_template = _load_json(power_policy_template_path)
    power_freeze_workflow = _load_json(power_freeze_workflow_path)
    data_governance = _load_json(data_governance_path)
    data_governance_review_template = _load_json(
        data_governance_review_template_path
    )
    data_governance_review_workflow = _load_json(
        data_governance_review_workflow_path
    )
    semantic_gold_index_template = _load_json(
        semantic_gold_index_template_path
    )
    semantic_gold_workflow_spec = _load_json(
        semantic_gold_workflow_spec_path
    )
    demonstration_pool_workflow_spec = _load_json(
        demonstration_pool_workflow_spec_path
    )
    execution_freeze_config_template = _load_json(
        execution_freeze_config_template_path
    )
    execution_freeze_workflow = _load_json(
        execution_freeze_workflow_path
    )
    test_execution_workflow = _load_json(test_execution_workflow_path)
    publication_gate_workflow = _load_json(
        publication_gate_workflow_path
    )
    feedback_response_signoff_template = _load_json(
        feedback_response_signoff_template_path
    )
    governance_approval = (
        _load_json(data_governance_approval_path)
        if data_governance_approval_path is not None
        else None
    )
    semantic_gold_approval = (
        _load_json(semantic_gold_approval_path)
        if semantic_gold_approval_path is not None
        else None
    )
    annotator_calibration_validation = (
        validate_annotator_calibration_summary(
            annotator_calibration_summary_path
        )
        if annotator_calibration_summary_path is not None
        else None
    )
    if (
        annotator_calibration_validation is not None
        and annotator_calibration_validation.get("status") != "ready"
    ):
        raise NDPHumanHandoffError(
            "annotator calibration summary is not reproducible"
        )
    execution_freeze = (
        _load_json(execution_freeze_path)
        if execution_freeze_path is not None
        else None
    )
    power_freeze = (
        _load_json(power_freeze_path)
        if power_freeze_path is not None
        else None
    )
    test_release_receipt = (
        _load_json(test_release_receipt_path)
        if test_release_receipt_path is not None
        else None
    )

    if readiness.get("schema_version") != "ndp50-research-readiness/v1":
        raise NDPHumanHandoffError("unexpected readiness schema")
    if readiness.get("integrity_status") != "passed":
        raise NDPHumanHandoffError("readiness integrity must pass before handoff")
    readiness_implementation = Path(__file__).with_name("ndp50_readiness.py")
    if readiness.get("implementation") != {
        "file": readiness_implementation.name,
        "sha256": _sha256_file(readiness_implementation),
    }:
        raise NDPHumanHandoffError(
            "readiness implementation binding is stale"
        )
    failed_checks = [
        item.get("check_id")
        for item in readiness.get("checks", [])
        if item.get("passed") is not True
    ]
    if failed_checks:
        raise NDPHumanHandoffError(
            f"readiness contains failed checks: {failed_checks}"
        )
    gates = readiness.get("gates")
    if not isinstance(gates, dict):
        raise NDPHumanHandoffError("readiness gates must be an object")
    if gates.get("test_split_unopened") is not True:
        raise NDPHumanHandoffError("test split must remain unopened at handoff")
    if readiness.get("test_ready") is True:
        required_test_release_gates = (
            "structural_validation_complete",
            "test_split_unopened",
            "semantic_preparation_integrity",
            "neutral_packets_ready",
            "vocabulary_frozen",
            "source_bundles_annotation_ready",
            "annotator_calibration_passed",
            "cpa_applicability_consensus_complete",
            "independent_gold_complete",
            "data_governance_policy_frozen",
            "prompt_and_backend_frozen",
            "test_power_plan_frozen",
            "test_design_meets_pretest_assurance",
            "test_execution_workflow_ready",
            "feedback_response_collaborator_signoff_complete",
            "external_preregistration_verified",
        )
        if (
            readiness.get("readiness_status") != "ready"
            or readiness.get("semantic_execution_ready") is not True
            or readiness.get("blockers") != []
            or any(
                gates.get(key) is not True
                for key in required_test_release_gates
            )
            or any(
                not isinstance(
                    (readiness.get("artifact_hashes") or {}).get(key),
                    str,
                )
                or len(
                    (readiness.get("artifact_hashes") or {}).get(key)
                )
                != 64
                for key in (
                    "publication_gate_workflow",
                    "public_package_manifest",
                    "feedback_response_matrix",
                    "feedback_improvement_amendment",
                    "feedback_response_signoff",
                    "external_preregistration_receipt",
                )
            )
            or (
                readiness.get("publication_gate_validation", {})
            ).get("feedback_response_signoff", {}
            ).get("status")
            != "passed"
            or (
                readiness.get("publication_gate_validation", {})
            ).get("external_preregistration_receipt", {}
            ).get("status")
            != "passed"
        ):
            raise NDPHumanHandoffError(
                "test-ready readiness has inconsistent release gates"
            )

    for key, path in (
        ("packet_manifest", packet_manifest_path),
        ("vocabulary", vocabulary_path),
        ("vocabulary_review_workflow", vocabulary_workflow_path),
        ("vocabulary_review_template", vocabulary_template_path),
        ("source_approval_workflow_spec", source_approval_spec_path),
        ("source_bundle_manifest", source_bundle_manifest_path),
        ("cpa_workflow", cpa_workflow_path),
        ("cpa_screen", cpa_screen_path),
        ("cpa_design", cpa_design_path),
        ("semantic_power_feasibility", power_feasibility_path),
        ("power_policy_template", power_policy_template_path),
        ("power_freeze_workflow", power_freeze_workflow_path),
        ("data_governance", data_governance_path),
        (
            "data_governance_review_template",
            data_governance_review_template_path,
        ),
        (
            "data_governance_review_workflow",
            data_governance_review_workflow_path,
        ),
        (
            "semantic_gold_index_template",
            semantic_gold_index_template_path,
        ),
        ("semantic_gold_workflow_spec", semantic_gold_workflow_spec_path),
        (
            "demonstration_pool_workflow_spec",
            demonstration_pool_workflow_spec_path,
        ),
        (
            "execution_freeze_config_template",
            execution_freeze_config_template_path,
        ),
        ("execution_freeze_workflow", execution_freeze_workflow_path),
        ("test_execution_workflow", test_execution_workflow_path),
        ("publication_gate_workflow", publication_gate_workflow_path),
        (
            "feedback_response_signoff_template",
            feedback_response_signoff_template_path,
        ),
    ):
        _require_readiness_binding(readiness, key=key, path=path)
    if data_governance_approval_path is not None:
        _require_readiness_binding(
            readiness,
            key="data_governance_approval",
            path=data_governance_approval_path,
        )
    elif readiness.get("artifact_hashes", {}).get(
        "data_governance_approval"
    ) is not None:
        raise NDPHumanHandoffError(
            "readiness binds a governance approval that was not supplied"
        )
    if semantic_gold_approval_path is not None:
        _require_readiness_binding(
            readiness,
            key="semantic_gold_approval",
            path=semantic_gold_approval_path,
        )
    elif readiness.get("artifact_hashes", {}).get(
        "semantic_gold_approval"
    ) is not None:
        raise NDPHumanHandoffError(
            "readiness binds a semantic-gold approval that was not supplied"
        )
    if annotator_calibration_summary_path is not None:
        _require_readiness_binding(
            readiness,
            key="annotator_calibration_summary",
            path=annotator_calibration_summary_path,
        )
    elif readiness.get("artifact_hashes", {}).get(
        "annotator_calibration_summary"
    ) is not None:
        raise NDPHumanHandoffError(
            "readiness binds an annotator calibration summary that was not "
            "supplied"
        )
    if cpa_consensus_path is not None:
        _require_readiness_binding(
            readiness,
            key="cpa_consensus",
            path=cpa_consensus_path,
        )
    elif readiness.get("artifact_hashes", {}).get("cpa_consensus") is not None:
        raise NDPHumanHandoffError(
            "readiness binds a CPA consensus that was not supplied"
        )
    if execution_freeze_path is not None:
        _require_readiness_binding(
            readiness,
            key="execution_freeze",
            path=execution_freeze_path,
        )
    elif readiness.get("artifact_hashes", {}).get(
        "execution_freeze"
    ) is not None:
        raise NDPHumanHandoffError(
            "readiness binds an execution freeze that was not supplied"
        )
    for key, path in (
        ("completed_power_policy", completed_power_policy_path),
        (
            "development_calibration_report",
            development_calibration_report_path,
        ),
        ("power_freeze", power_freeze_path),
    ):
        if path is not None:
            _require_readiness_binding(readiness, key=key, path=path)
        elif readiness.get("artifact_hashes", {}).get(key) is not None:
            raise NDPHumanHandoffError(
                f"readiness binds {key} but it was not supplied"
            )

    expected_schemas = {
        "packet manifest": (
            packet_manifest,
            "ndp50-semantic-packet-pack/v1",
        ),
        "vocabulary workflow": (
            vocabulary_workflow,
            "ndp50-vocabulary-review-workflow/v1",
        ),
        "vocabulary template": (
            vocabulary_template,
            "ndp50-vocabulary-discovery/v1",
        ),
        "source approval spec": (
            source_approval_spec,
            "ndp50-source-approval-workflow-spec/v1",
        ),
        "CPA workflow": (cpa_workflow, "ndp50-cpa-screen-workflow/v1"),
        "CPA screen": (cpa_screen, "ndp50-cpa-applicability-screen/v1"),
        "CPA design": (cpa_design, "ndp50-cpa-design/v1"),
        "power feasibility": (
            power_feasibility,
            "ndp50-semantic-power-feasibility/v1",
        ),
        "power policy template": (
            power_policy_template,
            "ndp50-power-policy/v1",
        ),
        "power freeze workflow": (
            power_freeze_workflow,
            "ndp50-power-freeze-workflow/v1",
        ),
        "data governance": (
            data_governance,
            "ndp50-data-governance-audit/v1",
        ),
        "data governance review template": (
            data_governance_review_template,
            "ndp50-data-governance-review/v1",
        ),
        "data governance review workflow": (
            data_governance_review_workflow,
            "ndp50-data-governance-review-workflow/v1",
        ),
        "semantic gold index template": (
            semantic_gold_index_template,
            "ndp50-semantic-gold-corpus-index/v1",
        ),
        "semantic gold workflow": (
            semantic_gold_workflow_spec,
            "ndp50-semantic-gold-workflow-spec/v1",
        ),
        "demonstration pool workflow": (
            demonstration_pool_workflow_spec,
            "ndp50-demonstration-pool-workflow/v1",
        ),
        "execution freeze template": (
            execution_freeze_config_template,
            "ndp50-execution-freeze-config/v1",
        ),
        "execution freeze workflow": (
            execution_freeze_workflow,
            "ndp50-execution-freeze-workflow/v1",
        ),
        "publication gate workflow": (
            publication_gate_workflow,
            "ndp50-publication-gate-workflow/v1",
        ),
        "feedback response signoff template": (
            feedback_response_signoff_template,
            "ndp50-feedback-response-signoff/v2",
        ),
    }
    for label, (payload, schema) in expected_schemas.items():
        if payload.get("schema_version") != schema:
            raise NDPHumanHandoffError(f"unexpected {label} schema")

    _require_neutral_vocabulary_template(vocabulary_template)
    if (
        feedback_response_signoff_template.get("status")
        != "pending_human_collaborator_review"
        or feedback_response_signoff_template.get(
            "human_decisions_present"
        )
        is not False
        or feedback_response_signoff_template.get(
            "independence_claimed"
        )
        is not False
    ):
        raise NDPHumanHandoffError(
            "feedback-response signoff template is not neutral"
        )
    if vocabulary_workflow.get("human_decisions_present") is not False:
        raise NDPHumanHandoffError(
            "neutral vocabulary workflow must not claim human decisions"
        )
    if source_approval_spec.get("human_decisions_present") is not False:
        raise NDPHumanHandoffError(
            "source approval specification must not claim human decisions"
        )
    if cpa_workflow.get("human_decisions_present") is not False:
        raise NDPHumanHandoffError(
            "neutral CPA workflow must not claim human decisions"
        )
    if power_feasibility.get("test_state", {}).get(
        "test_detail_snapshot_count"
    ) != 0:
        raise NDPHumanHandoffError("test detail snapshots are forbidden")
    if power_feasibility.get("test_state", {}).get(
        "test_split_unopened"
    ) is not True:
        raise NDPHumanHandoffError("power artifact reports an opened test split")
    if power_feasibility.get("gates", {}).get(
        "test_power_plan_frozen"
    ) != gates.get("test_power_plan_frozen"):
        raise NDPHumanHandoffError(
            "readiness and power artifact disagree on the test power-plan gate"
        )
    if (
        power_policy_template.get("status")
        != "neutral_pending_precalibration_policy"
        or power_policy_template.get("human_decisions_present") is not False
        or power_freeze_workflow.get("status")
        != "implementation_ready_waiting_on_execution_freeze"
        or power_freeze_workflow.get("human_decisions_present") is not False
        or power_freeze_workflow.get("test_outcomes_observed") is not False
        or power_freeze_workflow.get(
            "validation_or_test_outcomes_forbidden"
        )
        is not True
        or gates.get("power_freeze_workflow_ready") is not True
    ):
        raise NDPHumanHandoffError(
            "power-freeze material is not a neutral ready workflow"
        )
    if data_governance.get("status") != (
        "provenance_integrity_passed_governance_review_required"
    ):
        raise NDPHumanHandoffError("unexpected data-governance audit status")
    if (
        data_governance_review_template.get("status")
        != "neutral_pending_human_review"
        or data_governance_review_workflow.get("status")
        != "ready_for_independent_governance_review_and_approval"
        or data_governance_review_workflow.get("human_decisions_present")
        is not False
    ):
        raise NDPHumanHandoffError(
            "data-governance review material is not a neutral ready workflow"
        )
    if (
        semantic_gold_index_template.get("status")
        != "neutral_pending_gold_artifacts"
        or semantic_gold_index_template.get("human_decisions_present")
        is not False
        or semantic_gold_workflow_spec.get("human_decisions_present")
        is not False
        or gates.get("semantic_gold_workflow_ready") is not True
    ):
        raise NDPHumanHandoffError(
            "semantic-gold material is not a neutral ready workflow"
        )
    if (
        demonstration_pool_workflow_spec.get("status")
        != "implementation_ready_waiting_on_semantic_gold"
        or demonstration_pool_workflow_spec.get("human_decisions_present")
        is not False
        or demonstration_pool_workflow_spec.get(
            "candidate_inclusion_policy"
        )
        != "all_approved_development_cases"
        or demonstration_pool_workflow_spec.get(
            "validation_or_test_candidates_forbidden"
        )
        is not True
        or gates.get("demonstration_pool_workflow_ready") is not True
    ):
        raise NDPHumanHandoffError(
            "demonstration-pool material is not a neutral ready workflow"
        )
    if (
        execution_freeze_config_template.get("status")
        != "neutral_pending_execution_configuration"
        or execution_freeze_config_template.get("human_decisions_present")
        is not False
        or execution_freeze_workflow.get("status")
        != "implementation_ready_waiting_on_upstream_human_gates"
        or execution_freeze_workflow.get("human_decisions_present") is not False
        or execution_freeze_workflow.get("automatic_freeze") is not False
        or gates.get("execution_freeze_workflow_ready") is not True
    ):
        raise NDPHumanHandoffError(
            "execution-freeze material is not a neutral ready workflow"
        )
    if (
        test_execution_workflow.get("schema_version")
        != "ndp50-test-execution-workflow/v1"
        or test_execution_workflow.get("status")
        != "implementation_ready_waiting_on_test_release"
        or test_execution_workflow.get("human_decisions_present") is not False
        or test_execution_workflow.get("test_outcomes_observed") is not False
        or test_execution_workflow.get(
            "test_dataset_identities_included"
        )
        is not False
        or test_execution_workflow.get("test_dataset_count") != 25
        or gates.get("test_execution_workflow_ready") is not True
    ):
        raise NDPHumanHandoffError(
            "test-execution material is not a neutral ready workflow"
        )
    governance_gates = data_governance.get("gates", {})
    for key in (
        "detail_snapshot_hashes_verified",
        "dataset_identity_verified",
        "acquired_payload_hashes_complete",
        "test_split_unopened",
    ):
        if governance_gates.get(key) is not True:
            raise NDPHumanHandoffError(
                f"data-governance integrity gate must pass: {key}"
            )
    governance_approval_gates: Mapping[str, Any] = {}
    if governance_approval is not None:
        approval_validation = verify_governance_approval(
            governance_approval,
            audit_path=data_governance_path,
            study_root=study_root,
        )
        if approval_validation.get("status") != "passed":
            raise NDPHumanHandoffError(
                "data-governance approval is not reproducible"
            )
        governance_approval_gates = governance_approval.get(
            "derived_gates", {}
        )
    if semantic_gold_approval is not None:
        gold_validation = verify_gold_approval(
            semantic_gold_approval,
            packet_manifest_path=packet_manifest_path,
            approved_source_manifest_path=source_bundle_manifest_path,
            vocabulary_path=vocabulary_path,
            study_root=study_root,
        )
        if gold_validation.get("status") != "passed":
            raise NDPHumanHandoffError(
                "semantic-gold approval is not reproducible"
            )
    if execution_freeze is not None:
        if (
            cpa_consensus_path is None
            or semantic_gold_approval_path is None
            or data_governance_approval_path is None
        ):
            raise NDPHumanHandoffError(
                "execution freeze requires CPA, gold, and governance approvals"
            )
        freeze_validation = verify_execution_freeze(
            execution_freeze,
            cpa_design_path=cpa_design_path,
            packet_manifest_path=packet_manifest_path,
            vocabulary_path=vocabulary_path,
            approved_source_manifest_path=source_bundle_manifest_path,
            cpa_consensus_path=cpa_consensus_path,
            semantic_gold_approval_path=semantic_gold_approval_path,
            data_governance_audit_path=data_governance_path,
            data_governance_approval_path=data_governance_approval_path,
            study_root=study_root,
        )
        if freeze_validation.get("status") != "passed":
            raise NDPHumanHandoffError(
                "execution freeze is not reproducible"
            )
    if power_freeze is not None:
        if execution_freeze_path is None:
            raise NDPHumanHandoffError(
                "power freeze requires the execution freeze"
            )
        assert completed_power_policy_path is not None
        assert development_calibration_report_path is not None
        power_bindings = power_freeze.get("artifact_bindings", {})
        power_selection_path = _bound_path(
            power_bindings.get("selection"),
            study_root=study_root,
            label="power-freeze selection",
        )
        power_opportunity_path = _bound_path(
            power_bindings.get("opportunity_manifest"),
            study_root=study_root,
            label="power-freeze opportunity manifest",
        )
        bound_cpa_design_path = _bound_path(
            power_bindings.get("cpa_design"),
            study_root=study_root,
            label="power-freeze CPA design",
        )
        if bound_cpa_design_path != cpa_design_path.resolve():
            raise NDPHumanHandoffError(
                "power freeze and handoff bind different CPA designs"
            )
        power_validation = verify_power_freeze(
            power_freeze,
            policy_path=completed_power_policy_path,
            calibration_report_path=development_calibration_report_path,
            selection_path=power_selection_path,
            opportunity_manifest_path=power_opportunity_path,
            cpa_design_path=cpa_design_path,
            execution_freeze_path=execution_freeze_path,
            study_root=study_root,
        )
        if power_validation.get("status") != "passed":
            raise NDPHumanHandoffError(
                "power freeze is not reproducible"
            )

    test_release_authorized = False
    if test_release_receipt is not None:
        if (
            test_release_authorization_path is None
            or test_release_receipt_path is None
            or execution_freeze_path is None
            or power_freeze_path is None
            or readiness.get("test_ready") is not True
        ):
            raise NDPHumanHandoffError(
                "test release requires passing readiness and both freezes"
            )
        release_selection_path = _bound_path(
            test_execution_workflow.get("selection"),
            study_root=study_root,
            label="test-execution selection",
        )
        if readiness.get("artifact_hashes", {}).get(
            "selection"
        ) != _sha256_file(release_selection_path):
            raise NDPHumanHandoffError(
                "test-execution selection differs from readiness"
            )
        release_replay = verify_test_release_receipt(
            test_release_receipt,
            authorization_path=test_release_authorization_path,
            release_readiness_path=readiness_path,
            selection_path=release_selection_path,
            workflow_path=test_execution_workflow_path,
            execution_freeze_path=execution_freeze_path,
            power_freeze_path=power_freeze_path,
            study_root=study_root,
        )
        if release_replay.get("status") != "passed":
            raise NDPHumanHandoffError(
                "test release receipt is not reproducible"
            )
        test_release_authorized = True

    vocabulary_frozen = gates.get("vocabulary_frozen") is True
    sources_ready = gates.get("source_bundles_annotation_ready") is True
    annotator_calibrated = (
        gates.get("annotator_calibration_passed") is True
    )
    if annotator_calibrated != (
        annotator_calibration_summary_path is not None
    ):
        raise NDPHumanHandoffError(
            "readiness annotator-calibration gate and supplied summary "
            "disagree"
        )
    cpa_complete = (
        gates.get("cpa_applicability_consensus_complete") is True
    )
    gold_complete = gates.get("independent_gold_complete") is True
    execution_frozen = gates.get("prompt_and_backend_frozen") is True
    power_frozen = gates.get("test_power_plan_frozen") is True
    feedback_signed = (
        gates.get("feedback_response_collaborator_signoff_complete") is True
    )
    external_registered = (
        gates.get("external_preregistration_verified") is True
    )
    test_ready = readiness.get("test_ready") is True
    governance_policy_frozen = all(
        governance_approval_gates.get(key) is True
        for key in (
            "human_license_and_attribution_review_complete",
            "external_model_data_transfer_policy_frozen",
            "artifact_redistribution_policy_frozen",
            "data_governance_policy_frozen",
        )
    )
    for key in (
        "human_license_and_attribution_review_complete",
        "external_model_data_transfer_policy_frozen",
        "artifact_redistribution_policy_frozen",
        "data_governance_policy_frozen",
    ):
        if (gates.get(key) is True) != (
            governance_approval_gates.get(key) is True
        ):
            raise NDPHumanHandoffError(
                f"readiness and governance approval disagree on {key}"
            )
    if execution_frozen and not governance_policy_frozen:
        raise NDPHumanHandoffError(
            "execution cannot be frozen before data-governance policy"
        )

    stages = [
        _stage(
            ordinal=1,
            stage_id="data_governance_review",
            title="Independent data-steward review and accountable approval",
            completed=governance_policy_frozen,
            prerequisites_met=(
                gates.get("data_governance_review_workflow_ready") is True
                and not governance_policy_frozen
            ),
            unlock_evidence=[
                "readiness.integrity_status=passed",
                "readiness.gates.data_governance_review_workflow_ready=true",
                "one qualified non-developer stewardship reviewer",
                "one distinct institutionally accountable approver",
                "validator-generated and replayed approval artifact",
            ],
            required_outputs=[
                "completed_data_governance_review.json",
                "data_governance_review_validation.json",
                "data_governance_approval.json",
                "data_governance_approval_validation.json",
            ],
            prohibitions=[
                "Do not infer permission from public catalog availability.",
                "Do not include test identities or test-detail evidence.",
                "One person cannot fill both required signatory roles.",
                "The workflow records governance decisions, not legal advice.",
            ],
        ),
        _stage(
            ordinal=2,
            stage_id="vocabulary_governance",
            title="Independent vocabulary discovery, decisions, and consensus",
            completed=vocabulary_frozen,
            prerequisites_met=(
                gates.get("vocabulary_review_workflow_ready") is True
                and not vocabulary_frozen
            ),
            unlock_evidence=[
                "readiness.integrity_status=passed",
                "readiness.gates.vocabulary_review_workflow_ready=true",
                "two independent full-corpus discovery submissions",
                "two independent candidate-policy decisions",
                "validated disagreement worksheet and human consensus",
            ],
            required_outputs=[
                "vocabulary_candidate_catalog.json",
                "vocabulary_decision_a.json",
                "vocabulary_decision_b.json",
                "vocabulary_disagreement_worksheet.json",
                "vocabulary_consensus.json",
                "vocabulary_frozen.json",
            ],
            prohibitions=[
                "No model outputs may be shown to vocabulary reviewers.",
                "Do not treat the neutral template or draft vocabulary as approved.",
                "Do not overwrite either independent submission.",
            ],
        ),
        _stage(
            ordinal=3,
            stage_id="feedback_response_signoff",
            title="Collaborator review and sign-off of feedback incorporation",
            completed=feedback_signed,
            prerequisites_met=(
                gates.get("publication_gate_workflow_ready") is True
                and not feedback_signed
            ),
            unlock_evidence=[
                "readiness.integrity_status=passed",
                "readiness.gates.publication_gate_workflow_ready=true",
                "bound neutral F01--F16 response-signoff template",
                "collaborator review explicitly not independent validation",
            ],
            required_outputs=[
                "completed_feedback_response_signoff.json",
                "feedback_response_signoff_validation.json",
            ],
            prohibitions=[
                "Do not claim that collaborator review is independent validation.",
                "Do not change F01--F16 decisions inside the returned artifact.",
                "Do not inspect test identities, details, gold, or outcomes.",
                "This sign-off does not authorize semantic or test execution.",
            ],
        ),
        _stage(
            ordinal=4,
            stage_id="source_approval",
            title="Rebuild and independently approve evidence bundles",
            completed=sources_ready,
            prerequisites_met=(
                vocabulary_frozen
                and gates.get(
                    "source_approval_workflow_implementation_ready"
                )
                is True
                and not sources_ready
            ),
            unlock_evidence=[
                "readiness.gates.vocabulary_frozen=true",
                "source bundles rebuilt against the exact frozen vocabulary",
                "two independent item-by-purpose reviews",
                "one fresh qualified non-developer source adjudicator",
                "validated disagreement worksheet and human consensus",
            ],
            required_outputs=[
                "source_bundle_frozen_v1/manifest.json",
                "source_review_template.json",
                "source_review_a.json",
                "source_review_a_validation.json",
                "source_review_b.json",
                "source_review_b_validation.json",
                "source_disagreement_worksheet.json",
                "source_consensus.json",
                "source_consensus_validation.json",
                "source_bundle_approved_manifest.json",
                "source_bundle_approved_manifest_validation.json",
            ],
            prohibitions=[
                "Draft bundles cannot authorize annotation or CPA screening.",
                "Every evidence item must be approved for each claimed purpose.",
                "Do not alter agreed review slots during consensus.",
            ],
        ),
        _stage(
            ordinal=5,
            stage_id="annotator_calibration",
            title="Preregister and qualify the semantic-gold annotator pair",
            completed=annotator_calibrated,
            prerequisites_met=(
                sources_ready and not annotator_calibrated
            ),
            unlock_evidence=[
                "readiness.gates.source_bundles_annotation_ready=true",
                "final handbook and frozen NDP vocabulary hashes",
                "at least nine non-NDP calibration cases",
                "external receipt predating both independent submissions",
                "validator-replayed passing calibration summary",
            ],
            required_outputs=[
                "annotator_calibration_design.json",
                "annotator_calibration_design_preflight.json",
                "annotator_calibration_registration_receipt.json",
                "annotator_calibration_submission_a.json",
                "annotator_calibration_submission_b.json",
                "annotator_calibration_disagreement_reports/",
                "annotator_calibration_round_manifest.json",
                "annotator_calibration_summary.json",
                "annotator_calibration_summary_validation.json",
            ],
            prohibitions=[
                "Do not show NDP-50 gold packets before this gate passes.",
                "Do not reuse revealed cases after a failed calibration round.",
                "Do not change handbook, vocabulary, or annotator identities after qualification.",
                "No model output or automatic adjudicator may enter calibration.",
            ],
        ),
        _stage(
            ordinal=6,
            stage_id="cpa_screen_and_semantic_gold",
            title="Parallel blind CPA applicability and semantic-gold review",
            completed=cpa_complete and gold_complete,
            prerequisites_met=(
                sources_ready
                and annotator_calibrated
                and not (cpa_complete and gold_complete)
            ),
            unlock_evidence=[
                "readiness.gates.source_bundles_annotation_ready=true",
                "readiness.gates.annotator_calibration_passed=true",
                "two qualified independent CPA screens and a fresh adjudicator",
                "the exact calibrated semantic-gold pair and joint consensus",
            ],
            required_outputs=[
                "cpa_screen_a.json",
                "cpa_screen_a_validation.json",
                "cpa_screen_b.json",
                "cpa_screen_b_validation.json",
                "cpa_disagreement_worksheet.json",
                "cpa_consensus.json",
                "cpa_consensus_validation.json",
                "semantic_gold_a.json",
                "semantic_gold_b.json",
                "semantic_gold_independent_validation_receipts/",
                "semantic_gold_disagreement_report.json",
                "semantic_gold_consensus.json",
                "semantic_gold_consensus_validation_receipts/",
                "semantic_gold_corpus_validation.json",
                "semantic_gold_approval.json",
                "semantic_gold_approval_validation.json",
            ],
            prohibitions=[
                "Model outputs must remain hidden from applicability and gold reviewers.",
                "Annotators must be distinct and non-developers.",
                "Consensus cannot silently change slots on which reviewers agreed.",
            ],
        ),
        _stage(
            ordinal=7,
            stage_id="execution_freeze",
            title="Freeze prompts, serialization, demonstrations, and backends",
            completed=execution_frozen,
            prerequisites_met=(
                cpa_complete
                and gold_complete
                and annotator_calibrated
                and governance_policy_frozen
                and gates.get("demonstration_pool_workflow_ready") is True
                and gates.get("execution_freeze_workflow_ready") is True
                and not execution_frozen
            ),
            unlock_evidence=[
                "readiness.gates.cpa_applicability_consensus_complete=true",
                "readiness.gates.independent_gold_complete=true",
                "readiness.gates.annotator_calibration_passed=true",
                "readiness.gates.demonstration_pool_workflow_ready=true",
                "readiness.gates.execution_freeze_workflow_ready=true",
                "human license and attribution review complete",
                "model data-transfer and artifact redistribution policies frozen",
                "content-addressed prompts and serialization",
                "development-only demonstrations and ranking",
                "qualified backend registry and decoding parameters",
                "replayed synthetic execution-component qualification receipt",
            ],
            required_outputs=[
                "completed_execution_freeze_config.json",
                "execution_freeze_config_validation.json",
                "execution_implementation_declaration.json",
                "execution_implementation_qualification.json",
                "execution_implementation_qualification_validation.json",
                "execution_freeze.json",
                "execution_freeze_replay.json",
                "semantic_backend_registry.json",
                "development_demonstration_pool.json",
                "development_demonstration_pool_replay.json",
            ],
            prohibitions=[
                "Validation or test cases cannot become demonstrations.",
                "Execution-component qualification cannot use development, validation, or test data.",
                "No prompt, sampler, parser, or backend may be selected from test outcomes.",
                "Any post-freeze change requires a versioned deviation.",
            ],
        ),
        _stage(
            ordinal=8,
            stage_id="power_freeze",
            title="Build non-blind calibration statistics and freeze test power plan",
            completed=power_frozen,
            prerequisites_met=(
                execution_frozen
                and gold_complete
                and gates.get("semantic_power_feasibility_assessed") is True
                and gates.get("power_freeze_workflow_ready") is True
                and not power_frozen
            ),
            unlock_evidence=[
                "reproducible non-blind calibration evaluation report",
                "readiness.gates.power_freeze_workflow_ready=true",
                "signed pre-calibration minimum-effect policy",
                "recomputed dataset-level calibration statistics",
                "frozen minimum meaningful effect and paired-difference SD",
                "multiplicity-adjusted target power and opportunity assurance",
            ],
            required_outputs=[
                "semantic_power_calibration_statistics.json",
                "semantic_power_calibration_statistics_validation.json",
                "completed_power_policy.json",
                "completed_power_policy_validation.json",
                "ndp50_power_freeze.json",
                "ndp50_power_freeze_replay.json",
                "power_feasibility_v1.json rebuilt with the frozen plan",
            ],
            prohibitions=[
                "Test semantic outcomes cannot inform power assumptions.",
                "The exact-sign-flip resolution floor is not sufficient power evidence.",
                "A missed opportunity count must be reported as underpowered.",
            ],
        ),
        _stage(
            ordinal=9,
            stage_id="external_preregistration",
            title=(
                "Register the frozen public package and independently "
                "verify the receipt"
            ),
            completed=external_registered,
            prerequisites_met=(
                feedback_signed
                and execution_frozen
                and power_frozen
                and gates.get("test_design_meets_pretest_assurance") is True
                and gates.get("publication_gate_workflow_ready") is True
                and not external_registered
            ),
            unlock_evidence=[
                (
                    "readiness.gates."
                    "feedback_response_collaborator_signoff_complete=true"
                ),
                "readiness.gates.prompt_and_backend_frozen=true",
                "readiness.gates.test_power_plan_frozen=true",
                "readiness.gates.test_design_meets_pretest_assurance=true",
                "exact final public-package manifest and content digest",
            ],
            required_outputs=[
                "immutable OSF/Zenodo registration record",
                "external registration receipt/export",
                "completed external preregistration receipt artifact",
                "independent registration-verification record",
                "external preregistration receipt validation",
            ],
            prohibitions=[
                "Do not register a package that differs from the frozen manifest.",
                "Do not expose sealed test identities, details, gold, or outcomes.",
                (
                    "The independent verifier cannot be a developer or "
                    "project collaborator."
                ),
                "The external receipt does not itself authorize test opening.",
            ],
        ),
        _stage(
            ordinal=10,
            stage_id="test_release_authorization",
            title="Independently authorize the sealed test release",
            completed=test_release_authorized,
            prerequisites_met=(
                test_ready and not test_release_authorized
            ),
            unlock_evidence=[
                "readiness.test_ready=true",
                "readiness.gates.test_execution_workflow_ready=true",
                (
                    "readiness.gates."
                    "feedback_response_collaborator_signoff_complete=true"
                ),
                "readiness.gates.external_preregistration_verified=true",
                "all artifact hashes and non-human integrity checks pass",
                "all human consensus and freeze gates pass",
            ],
            required_outputs=[
                "distinct study-operator and independent-monitor signatures",
                "completed test release authorization",
                "validator-generated test release receipt and replay",
            ],
            prohibitions=[
                "Do not inspect or acquire test details before the receipt passes.",
                "The release monitor must be a distinct qualified non-developer.",
                "Authorization applies only to the exact bound frozen protocol.",
            ],
        ),
        _stage(
            ordinal=11,
            stage_id="test_execution",
            title="Execute the authorized frozen test protocol",
            completed=False,
            prerequisites_met=test_release_authorized,
            unlock_evidence=[
                "validated test release receipt",
                "distinct signatories and non-developer monitor verified",
                "test split unopened at the bound readiness snapshot",
            ],
            required_outputs=[
                "frozen test case manifest with all 25 dataset dispositions",
                "immutable complete case-by-arm test run manifest",
                "content-addressed test record for every matrix cell",
                "complete deviation registry, including an explicit empty registry",
                "validator-generated test run receipt and replay",
                "case-arm missingness and failure report",
                "frozen inference result, replay, and publication tables",
                "frozen inference replay validation",
            ],
            prohibitions=[
                "Do not inspect test details before the release receipt passes.",
                "Do not add datasets or alter analysis after observing outcomes.",
                "Do not silently delete a dataset, case, failure, or abstention.",
                "The deterministic and response-replay arms cannot make model calls.",
                "Do not promote pilot or exploratory findings to confirmatory claims.",
            ],
        ),
    ]
    released_stage_ids = [
        item["stage_id"] for item in stages if item["status"] == "released"
    ]
    if test_release_authorized:
        overall_status = "test_execution_released"
    elif test_ready:
        overall_status = "test_release_authorization_released"
    elif released_stage_ids:
        overall_status = "human_work_released_downstream_locked"
    else:
        overall_status = "blocked_no_authorized_stage"

    current_release: Dict[str, Any] = {
        "released_stage_ids": released_stage_ids,
        "instruction": (
            "Only released stages may receive human work. Locked-stage inputs "
            "must not be distributed as executable assignments."
        ),
    }
    if "data_governance_review" in released_stage_ids:
        current_release["data_governance_assignment"] = {
            "released_inputs": {
                "audit": _binding(data_governance_path, study_root),
                "neutral_review_template": _binding(
                    data_governance_review_template_path, study_root
                ),
                "workflow": _binding(
                    data_governance_review_workflow_path, study_root
                ),
            },
            "reviewer_slots": [
                {
                    "slot": "stewardship_review",
                    "reviewer_id": None,
                    "required_role": (
                        "institutional_data_steward_or_"
                        "research_compliance_reviewer"
                    ),
                },
                {
                    "slot": "accountable_approval",
                    "reviewer_id": None,
                    "required_role": (
                        "principal_investigator_or_"
                        "institutional_data_controller"
                    ),
                },
            ],
            "submission_rule": (
                "The stewardship reviewer completes the evidence-bound review; "
                "a distinct accountable approver signs it; the validator alone "
                "generates the approval artifact."
            ),
        }
    if "vocabulary_governance" in released_stage_ids:
        current_release["vocabulary_assignment"] = {
            "released_inputs": {
                "neutral_discovery_template": _binding(
                    vocabulary_template_path, study_root
                ),
                "draft_vocabulary": _binding(
                    vocabulary_path, study_root
                ),
                "source_bundle_manifest": _binding(
                    source_bundle_manifest_path, study_root
                ),
            },
            "reviewer_slots": [
                {
                    "slot": "discovery_a",
                    "reviewer_id": None,
                    "required_role": "scientific_metadata_curator",
                },
                {
                    "slot": "discovery_b",
                    "reviewer_id": None,
                    "required_role": "annotation_methodologist",
                },
            ],
            "submission_rule": (
                "Create separate copies, complete the entire corpus independently, "
                "then validate and freeze both content hashes before comparison."
            ),
        }
    if "feedback_response_signoff" in released_stage_ids:
        current_release["feedback_response_signoff_assignment"] = {
            "released_inputs": {
                "neutral_signoff_template": _binding(
                    feedback_response_signoff_template_path, study_root
                ),
                "publication_gate_workflow": _binding(
                    publication_gate_workflow_path, study_root
                ),
            },
            "reviewer_slots": [
                {
                    "slot": "feedback_collaborator",
                    "reviewer_id": None,
                    "required_role": "postdoctoral_research_collaborator",
                    "project_collaborator": True,
                    "independent_reviewer": False,
                }
            ],
            "submission_rule": (
                "The collaborator reviews F01--F16, preserves the frozen "
                "optional-sensitivity decisions, discloses the collaboration "
                "role, and returns the completed bound template. The validator "
                "records collaborator approval, not independent validation."
            ),
        }

    implementation = Path(__file__).resolve()
    return {
        "schema_version": SCHEMA_VERSION,
        "status": overall_status,
        "readiness_status": readiness["readiness_status"],
        "artifact_bindings": {
            key: _binding(path, study_root) for key, path in paths.items()
        },
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            name: _sha256_file(implementation.with_name(name))
            for name in (
                "ndp50_vocabulary_workflow.py",
                "ndp50_source_bundles.py",
                "ndp50_source_approval.py",
                "ndp50_cpa_screen_workflow.py",
                "semantic_gold_workflow.py",
                "semantic_annotator_calibration.py",
                "semantic_power_calibration.py",
                "semantic_power_analysis.py",
                "ndp50_data_governance.py",
                "ndp50_data_governance_review.py",
                "ndp50_demonstration_pool.py",
                "ndp50_semantic_gold.py",
                "ndp50_execution_freeze.py",
                "ndp50_power_freeze.py",
                "ndp50_publication_gate.py",
                "ndp50_test_execution.py",
                "ndp50_test_inference.py",
                "ndp50_readiness.py",
                "ndp50_human_assignments.py",
            )
        },
        "assignment_protocol": {
            "implementation": "ndp50_human_assignments.py",
            "release_schema": "ndp50-human-assignment-release/v1",
            "return_schema": "ndp50-human-assignment-return/v1",
            "feedback_signoff_schema": (
                "ndp50-feedback-response-signoff/v2"
            ),
            "candidate_decision_release_schema": (
                "ndp50-vocabulary-decision-assignment-release/v1"
            ),
            "candidate_decision_return_schema": (
                "ndp50-vocabulary-decision-assignment-return/v1"
            ),
            "consensus_release_schema": (
                "ndp50-vocabulary-consensus-assignment-release/v1"
            ),
            "consensus_return_schema": (
                "ndp50-vocabulary-consensus-assignment-return/v1"
            ),
            "release_rule": (
                "Generate byte-identical neutral payload copies with distinct "
                "slot wrappers only from current_release; reviewer identities "
                "remain null until real assignment."
            ),
            "return_rule": (
                "Accept only validator-replayed submissions and atomically "
                "freeze both vocabulary hashes before any cross-review reveal; "
                "the feedback return must separately replay as collaborator "
                "sign-off without an independence claim."
            ),
            "candidate_decision_rule": (
                "Only a passing initial return replay may generate the "
                "deterministic candidate catalog and two byte-identical "
                "decision assignments; the decision pair must be fresh from "
                "the discovery pair and frozen before disagreement reveal."
            ),
            "consensus_rule": (
                "Only a passing decision dual-freeze replay may reveal the "
                "deterministic disagreement worksheet to a qualified "
                "non-developer adjudicator who is fresh from all discovery "
                "and decision reviews."
            ),
        },
        "role_contract": {
            "pseudonymous_stable_reviewer_ids_required": True,
            "distinct_independent_reviewers_required": True,
            "independent_review_slots_require_non_developers": True,
            "study_operator_may_be_developer_with_disclosure": True,
            "conflict_of_interest_disclosure_required": True,
            "minimum_role_coverage": [
                "domain_or_scientific_metadata_curator",
                "annotation_methodologist",
            ],
            "adjudication_modes": {
                "vocabulary": "fresh_qualified_non_developer_adjudicator",
                "source_approval": (
                    "fresh_qualified_non_developer_adjudicator"
                ),
                "cpa_applicability": (
                    "fresh_qualified_non_developer_adjudicator"
                ),
                "semantic_gold": (
                    "joint_consensus_by_same_qualified_annotator_pair"
                ),
            },
        },
        "safety_invariants": [
            "Template generation is not evidence of a completed human decision.",
            "Test dataset identities, test details, and test outcomes are absent.",
            "Data governance is reviewed before semantic execution is frozen.",
            "Independent submissions are immutable before disagreement reveal.",
            "Assignment wrappers cannot embed reviewer identities or decisions.",
            "Candidate acceptance uses a fresh reviewer pair after discovery.",
            "Vocabulary consensus uses a fresh qualified non-developer adjudicator.",
            "Blind semantic gold requires a replayed passing annotator-calibration summary bound to the final handbook and vocabulary.",
            "Collaborator feedback sign-off is released independently of the later external-registration and test-release stages.",
            "Test release requires collaborator feedback sign-off and an independently verified immutable external preregistration receipt.",
            "All downstream artifacts bind their exact upstream content hashes.",
            "Changing a bound artifact invalidates this handoff.",
        ],
        "current_release": current_release,
        "stages": stages,
    }


def validate_handoff(
    payload: Mapping[str, Any],
    *,
    readiness_path: Path,
    packet_manifest_path: Path,
    vocabulary_path: Path,
    vocabulary_workflow_path: Path,
    vocabulary_template_path: Path,
    source_approval_spec_path: Path,
    source_bundle_manifest_path: Path,
    cpa_workflow_path: Path,
    cpa_screen_path: Path,
    cpa_design_path: Path,
    power_feasibility_path: Path,
    power_policy_template_path: Path,
    power_freeze_workflow_path: Path,
    data_governance_path: Path,
    data_governance_review_template_path: Path,
    data_governance_review_workflow_path: Path,
    semantic_gold_index_template_path: Path,
    semantic_gold_workflow_spec_path: Path,
    demonstration_pool_workflow_spec_path: Path,
    execution_freeze_config_template_path: Path,
    execution_freeze_workflow_path: Path,
    test_execution_workflow_path: Path,
    publication_gate_workflow_path: Path,
    feedback_response_signoff_template_path: Path,
    study_root: Path,
    cpa_consensus_path: Path | None = None,
    data_governance_approval_path: Path | None = None,
    semantic_gold_approval_path: Path | None = None,
    annotator_calibration_summary_path: Path | None = None,
    execution_freeze_path: Path | None = None,
    completed_power_policy_path: Path | None = None,
    development_calibration_report_path: Path | None = None,
    power_freeze_path: Path | None = None,
    test_release_authorization_path: Path | None = None,
    test_release_receipt_path: Path | None = None,
) -> Dict[str, Any]:
    expected = build_handoff(
        readiness_path=readiness_path,
        packet_manifest_path=packet_manifest_path,
        vocabulary_path=vocabulary_path,
        vocabulary_workflow_path=vocabulary_workflow_path,
        vocabulary_template_path=vocabulary_template_path,
        source_approval_spec_path=source_approval_spec_path,
        source_bundle_manifest_path=source_bundle_manifest_path,
        cpa_workflow_path=cpa_workflow_path,
        cpa_screen_path=cpa_screen_path,
        cpa_design_path=cpa_design_path,
        power_feasibility_path=power_feasibility_path,
        power_policy_template_path=power_policy_template_path,
        power_freeze_workflow_path=power_freeze_workflow_path,
        data_governance_path=data_governance_path,
        data_governance_review_template_path=(
            data_governance_review_template_path
        ),
        data_governance_review_workflow_path=(
            data_governance_review_workflow_path
        ),
        semantic_gold_index_template_path=(
            semantic_gold_index_template_path
        ),
        semantic_gold_workflow_spec_path=semantic_gold_workflow_spec_path,
        demonstration_pool_workflow_spec_path=(
            demonstration_pool_workflow_spec_path
        ),
        execution_freeze_config_template_path=(
            execution_freeze_config_template_path
        ),
        execution_freeze_workflow_path=execution_freeze_workflow_path,
        test_execution_workflow_path=test_execution_workflow_path,
        publication_gate_workflow_path=publication_gate_workflow_path,
        feedback_response_signoff_template_path=(
            feedback_response_signoff_template_path
        ),
        study_root=study_root,
        cpa_consensus_path=cpa_consensus_path,
        data_governance_approval_path=data_governance_approval_path,
        semantic_gold_approval_path=semantic_gold_approval_path,
        annotator_calibration_summary_path=(
            annotator_calibration_summary_path
        ),
        execution_freeze_path=execution_freeze_path,
        completed_power_policy_path=completed_power_policy_path,
        development_calibration_report_path=(
            development_calibration_report_path
        ),
        power_freeze_path=power_freeze_path,
        test_release_authorization_path=(
            test_release_authorization_path
        ),
        test_release_receipt_path=test_release_receipt_path,
    )
    differing = sorted(
        key
        for key in set(payload) | set(expected)
        if payload.get(key) != expected.get(key)
    )
    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "status": "passed" if not differing else "failed",
        "differing_top_level_keys": differing,
    }


def _add_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--readiness", type=Path, required=True)
    parser.add_argument("--packet-manifest", type=Path, required=True)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--vocabulary-workflow", type=Path, required=True)
    parser.add_argument("--vocabulary-template", type=Path, required=True)
    parser.add_argument("--source-approval-spec", type=Path, required=True)
    parser.add_argument("--source-bundle-manifest", type=Path, required=True)
    parser.add_argument("--cpa-workflow", type=Path, required=True)
    parser.add_argument("--cpa-screen", type=Path, required=True)
    parser.add_argument("--cpa-design", type=Path, required=True)
    parser.add_argument("--power-feasibility", type=Path, required=True)
    parser.add_argument("--power-policy-template", type=Path, required=True)
    parser.add_argument("--power-freeze-workflow", type=Path, required=True)
    parser.add_argument("--data-governance", type=Path, required=True)
    parser.add_argument(
        "--data-governance-review-template", type=Path, required=True
    )
    parser.add_argument(
        "--data-governance-review-workflow", type=Path, required=True
    )
    parser.add_argument(
        "--semantic-gold-index-template", type=Path, required=True
    )
    parser.add_argument(
        "--semantic-gold-workflow-spec", type=Path, required=True
    )
    parser.add_argument(
        "--demonstration-pool-workflow-spec", type=Path, required=True
    )
    parser.add_argument(
        "--execution-freeze-config-template", type=Path, required=True
    )
    parser.add_argument(
        "--execution-freeze-workflow", type=Path, required=True
    )
    parser.add_argument(
        "--test-execution-workflow", type=Path, required=True
    )
    parser.add_argument(
        "--publication-gate-workflow", type=Path, required=True
    )
    parser.add_argument(
        "--feedback-response-signoff-template", type=Path, required=True
    )
    parser.add_argument("--execution-freeze", type=Path)
    parser.add_argument("--completed-power-policy", type=Path)
    parser.add_argument("--development-calibration-report", type=Path)
    parser.add_argument("--power-freeze", type=Path)
    parser.add_argument("--test-release-authorization", type=Path)
    parser.add_argument("--test-release-receipt", type=Path)
    parser.add_argument("--cpa-consensus", type=Path)
    parser.add_argument("--semantic-gold-approval", type=Path)
    parser.add_argument("--annotator-calibration-summary", type=Path)
    parser.add_argument("--data-governance-approval", type=Path)
    parser.add_argument("--study-root", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or validate the gated NDP-50 human handoff."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    _add_inputs(build)
    build.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate")
    _add_inputs(validate)
    validate.add_argument("--artifact", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kwargs = {
        "readiness_path": args.readiness,
        "packet_manifest_path": args.packet_manifest,
        "vocabulary_path": args.vocabulary,
        "vocabulary_workflow_path": args.vocabulary_workflow,
        "vocabulary_template_path": args.vocabulary_template,
        "source_approval_spec_path": args.source_approval_spec,
        "source_bundle_manifest_path": args.source_bundle_manifest,
        "cpa_workflow_path": args.cpa_workflow,
        "cpa_screen_path": args.cpa_screen,
        "cpa_design_path": args.cpa_design,
        "power_feasibility_path": args.power_feasibility,
        "power_policy_template_path": args.power_policy_template,
        "power_freeze_workflow_path": args.power_freeze_workflow,
        "data_governance_path": args.data_governance,
        "data_governance_review_template_path": (
            args.data_governance_review_template
        ),
        "data_governance_review_workflow_path": (
            args.data_governance_review_workflow
        ),
        "semantic_gold_index_template_path": (
            args.semantic_gold_index_template
        ),
        "semantic_gold_workflow_spec_path": (
            args.semantic_gold_workflow_spec
        ),
        "demonstration_pool_workflow_spec_path": (
            args.demonstration_pool_workflow_spec
        ),
        "execution_freeze_config_template_path": (
            args.execution_freeze_config_template
        ),
        "execution_freeze_workflow_path": args.execution_freeze_workflow,
        "test_execution_workflow_path": args.test_execution_workflow,
        "publication_gate_workflow_path": args.publication_gate_workflow,
        "feedback_response_signoff_template_path": (
            args.feedback_response_signoff_template
        ),
        "study_root": args.study_root,
        "cpa_consensus_path": args.cpa_consensus,
        "data_governance_approval_path": args.data_governance_approval,
        "semantic_gold_approval_path": args.semantic_gold_approval,
        "annotator_calibration_summary_path": (
            args.annotator_calibration_summary
        ),
        "execution_freeze_path": args.execution_freeze,
        "completed_power_policy_path": args.completed_power_policy,
        "development_calibration_report_path": (
            args.development_calibration_report
        ),
        "power_freeze_path": args.power_freeze,
        "test_release_authorization_path": (
            args.test_release_authorization
        ),
        "test_release_receipt_path": args.test_release_receipt,
    }
    if args.command == "build":
        payload = build_handoff(**kwargs)
        _write_json(args.output, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "released_stage_ids": payload["current_release"][
                        "released_stage_ids"
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    payload = _load_json(args.artifact)
    report = validate_handoff(payload, **kwargs)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
