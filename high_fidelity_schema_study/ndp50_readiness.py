from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .ndp50_cpa_screen_workflow import (
    load_evidence_registry,
    validate_consensus,
)
from .ndp50_vocabulary_workflow import build_frozen_vocabulary
from .ndp50_power_feasibility import validate_feasibility_report
from .ndp50_power_freeze import (
    build_policy_template as build_power_policy_template,
    build_workflow_spec as build_power_freeze_workflow_spec,
    verify_freeze as verify_power_freeze,
)
from .ndp50_data_governance import validate_audit_file
from .ndp50_data_governance_review import (
    build_review_template,
    verify_approval as verify_governance_approval,
)
from .ndp50_semantic_gold import (
    build_index_template as build_gold_index_template,
    build_workflow_spec as build_gold_workflow_spec,
    verify_approval as verify_gold_approval,
)
from .ndp50_demonstration_pool import (
    build_workflow_spec as build_demonstration_pool_workflow_spec,
)
from .ndp50_execution_freeze import (
    build_config_template as build_execution_config_template,
    build_workflow_spec as build_execution_workflow_spec,
    verify_freeze as verify_execution_freeze,
)
from .ndp50_test_execution import (
    build_workflow_spec as build_test_execution_workflow_spec,
)
from .semantic_gold_workflow import validate_vocabulary
from .semantic_annotator_calibration import (
    validate_annotator_calibration_summary,
)
from .ndp50_publication_gate import (
    build_feedback_signoff_template,
    build_workflow_spec as build_publication_gate_workflow_spec,
    validate_external_preregistration_receipt,
    validate_feedback_signoff,
)


SCHEMA_VERSION = "ndp50-research-readiness/v1"
PACKAGE_ROOT = Path(__file__).resolve().parent


class NDPReadinessError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_readiness_report(
    *,
    selection_path: Path,
    validation_run_path: Path,
    validation_summary_path: Path,
    opportunity_manifest_path: Path,
    packet_manifest_path: Path,
    vocabulary_path: Path,
    vocabulary_draft_path: Path,
    vocabulary_review_template_path: Path,
    vocabulary_review_workflow_path: Path,
    vocabulary_review_source_bundle_manifest_path: Path,
    source_bundle_manifest_path: Path,
    source_approval_workflow_spec_path: Path,
    semantic_power_feasibility_path: Path,
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
    public_package_manifest_path: Path,
    feedback_response_signoff_template_path: Path,
    feedback_matrix_path: Path,
    feedback_amendment_path: Path,
    cpa_design_path: Path,
    cpa_screen_path: Path,
    cpa_workflow_path: Path,
    study_root: Path,
    cpa_submission_a_path: Path | None = None,
    cpa_submission_b_path: Path | None = None,
    cpa_disagreement_worksheet_path: Path | None = None,
    cpa_consensus_path: Path | None = None,
    vocabulary_candidate_catalog_path: Path | None = None,
    vocabulary_decision_a_path: Path | None = None,
    vocabulary_decision_b_path: Path | None = None,
    vocabulary_disagreement_worksheet_path: Path | None = None,
    vocabulary_consensus_path: Path | None = None,
    semantic_power_analysis_path: Path | None = None,
    completed_power_policy_path: Path | None = None,
    development_calibration_report_path: Path | None = None,
    power_freeze_path: Path | None = None,
    data_governance_approval_path: Path | None = None,
    semantic_gold_approval_path: Path | None = None,
    annotator_calibration_summary_path: Path | None = None,
    execution_freeze_path: Path | None = None,
    feedback_response_signoff_path: Path | None = None,
    external_preregistration_receipt_path: Path | None = None,
) -> Dict[str, Any]:
    selection = _load_json(selection_path)
    validation_run = _load_json(validation_run_path)
    validation_summary = _load_json(validation_summary_path)
    opportunity = _load_json(opportunity_manifest_path)
    packets = _load_json(packet_manifest_path)
    vocabulary = _load_json(vocabulary_path)
    vocabulary_draft = _load_json(vocabulary_draft_path)
    vocabulary_review_template = _load_json(vocabulary_review_template_path)
    vocabulary_review_workflow = _load_json(vocabulary_review_workflow_path)
    vocabulary_review_source_bundles = _load_json(
        vocabulary_review_source_bundle_manifest_path
    )
    bundles = _load_json(source_bundle_manifest_path)
    source_approval_workflow_spec = _load_json(
        source_approval_workflow_spec_path
    )
    semantic_power_feasibility = _load_json(
        semantic_power_feasibility_path
    )
    power_policy_template = _load_json(power_policy_template_path)
    power_freeze_workflow = _load_json(power_freeze_workflow_path)
    power_completion_paths = (
        completed_power_policy_path,
        development_calibration_report_path,
        power_freeze_path,
    )
    if any(path is not None for path in power_completion_paths) and not all(
        path is not None for path in power_completion_paths
    ):
        raise NDPReadinessError(
            "NDP power freeze requires the completed policy, development "
            "calibration report, and frozen artifact"
        )
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
    publication_gate_workflow = _load_json(publication_gate_workflow_path)
    public_package_manifest = _load_json(public_package_manifest_path)
    feedback_response_signoff_template = _load_json(
        feedback_response_signoff_template_path
    )
    feedback_matrix_path.read_text(encoding="utf-8")
    feedback_amendment_path.read_text(encoding="utf-8")
    cpa_design = _load_json(cpa_design_path)
    cpa_screen = _load_json(cpa_screen_path)
    cpa_workflow = _load_json(cpa_workflow_path)
    consensus_paths = (
        cpa_submission_a_path,
        cpa_submission_b_path,
        cpa_disagreement_worksheet_path,
        cpa_consensus_path,
    )
    if any(path is not None for path in consensus_paths) and not all(
        path is not None for path in consensus_paths
    ):
        raise NDPReadinessError(
            "CPA consensus readiness requires both submissions, the "
            "disagreement worksheet, and the consensus artifact"
        )
    vocabulary_freeze_paths = (
        vocabulary_candidate_catalog_path,
        vocabulary_decision_a_path,
        vocabulary_decision_b_path,
        vocabulary_disagreement_worksheet_path,
        vocabulary_consensus_path,
    )
    if any(path is not None for path in vocabulary_freeze_paths) and not all(
        path is not None for path in vocabulary_freeze_paths
    ):
        raise NDPReadinessError(
            "vocabulary freeze readiness requires the candidate catalog, "
            "both decisions, disagreement worksheet, and consensus"
        )
    if (
        external_preregistration_receipt_path is not None
        and feedback_response_signoff_path is None
    ):
        raise NDPReadinessError(
            "external preregistration replay requires the collaborator "
            "feedback-response sign-off"
        )

    checks = []

    def check(check_id: str, passed: bool, detail: str) -> None:
        checks.append({"check_id": check_id, "passed": passed, "detail": detail})

    validation_ids = {
        item["dataset_id"]
        for item in selection["selected_datasets"]
        if item["split"] == "validation"
    }
    check(
        "validation_identity",
        validation_run.get("run_role") == "validation"
        and {item["dataset_id"] for item in validation_run["datasets"]}
        == validation_ids
        and validation_summary.get("run_role") == "validation"
        and validation_summary.get("selection_integrity", {}).get(
            "exact_id_match"
        )
        is True,
        f"{len(validation_ids)} frozen validation dataset IDs",
    )
    test_detail_dir = study_root / "acquisition" / "test_details"
    test_detail_count = (
        len(list(test_detail_dir.glob("*.json.gz")))
        if test_detail_dir.exists()
        else 0
    )
    check(
        "test_split_unopened",
        test_detail_count == 0,
        f"{test_detail_count} test detail snapshots",
    )

    opportunity_hash = _sha256_file(opportunity_manifest_path)
    packet_hash = _sha256_file(packet_manifest_path)
    vocabulary_hash = _sha256_file(vocabulary_path)
    vocabulary_draft_hash = _sha256_file(vocabulary_draft_path)
    source_bundle_hash = _sha256_file(source_bundle_manifest_path)
    vocabulary_review_source_bundle_hash = _sha256_file(
        vocabulary_review_source_bundle_manifest_path
    )
    expected_gold_index_template = build_gold_index_template(
        packet_manifest_path=packet_manifest_path,
        study_root=study_root,
    )
    expected_gold_workflow_spec = build_gold_workflow_spec(
        packet_manifest_path=packet_manifest_path,
        index_template_path=semantic_gold_index_template_path,
        study_root=study_root,
    )
    semantic_gold_workflow_ready = (
        semantic_gold_index_template == expected_gold_index_template
        and semantic_gold_workflow_spec == expected_gold_workflow_spec
        and semantic_gold_workflow_spec.get("human_decisions_present")
        is False
        and semantic_gold_workflow_spec.get(
            "model_outputs_visible_during_annotation"
        )
        is False
        and semantic_gold_workflow_spec.get("automatic_adjudication")
        is False
        and semantic_gold_workflow_spec.get(
            "unresolved_consensus_slots_allowed_for_completion"
        )
        is False
    )
    check(
        "semantic_gold_workflow_binding",
        semantic_gold_workflow_ready,
        (
            f"{len(semantic_gold_index_template.get('cases') or [])} "
            "two-annotator gold cases"
        ),
    )
    expected_demonstration_pool_workflow_spec = (
        build_demonstration_pool_workflow_spec(
            packet_manifest_path=packet_manifest_path,
            study_root=study_root,
        )
    )
    demonstration_pool_workflow_ready = (
        demonstration_pool_workflow_spec
        == expected_demonstration_pool_workflow_spec
        and demonstration_pool_workflow_spec.get("human_decisions_present")
        is False
        and demonstration_pool_workflow_spec.get(
            "candidate_inclusion_policy"
        )
        == "all_approved_development_cases"
        and demonstration_pool_workflow_spec.get(
            "validation_or_test_candidates_forbidden"
        )
        is True
        and demonstration_pool_workflow_spec.get(
            "model_outputs_used_for_inclusion"
        )
        is False
    )
    check(
        "demonstration_pool_workflow_binding",
        demonstration_pool_workflow_ready,
        (
            f"{demonstration_pool_workflow_spec.get('development_case_count', 0)} "
            "development-only candidate cases"
        ),
    )
    expected_execution_config_template = build_execution_config_template(
        cpa_design_path=cpa_design_path,
        packet_manifest_path=packet_manifest_path,
        study_root=study_root,
    )
    expected_execution_workflow = build_execution_workflow_spec(
        cpa_design_path=cpa_design_path,
        packet_manifest_path=packet_manifest_path,
        config_template_path=execution_freeze_config_template_path,
        study_root=study_root,
    )
    execution_freeze_workflow_ready = (
        execution_freeze_config_template
        == expected_execution_config_template
        and execution_freeze_workflow == expected_execution_workflow
        and execution_freeze_workflow.get("human_decisions_present")
        is False
        and execution_freeze_workflow.get(
            "model_or_gold_outcomes_observed"
        )
        is False
        and execution_freeze_workflow.get("automatic_freeze") is False
    )
    check(
        "execution_freeze_workflow_binding",
        execution_freeze_workflow_ready,
        "prompt, serialization, demonstrations, backend, and runner freeze",
    )
    source_bundles_annotation_ready = False
    bundle_basis = bundles
    if (
        bundles.get("schema_version")
        == "ndp50-source-bundle-approved-manifest/v1"
    ):
        _, _, source_bundles_annotation_ready = load_evidence_registry(
            source_bundle_manifest_path,
            require_approved=True,
        )
        draft_ref = bundles.get("source_bundle_draft_manifest", {})
        draft_path = (
            source_bundle_manifest_path.parent
            / str(draft_ref.get("file") or "")
        ).resolve()
        if (
            not draft_path.is_file()
            or _sha256_file(draft_path) != draft_ref.get("sha256")
        ):
            raise NDPReadinessError(
                "approved source manifest has an invalid draft-manifest binding"
            )
        bundle_basis = _load_json(draft_path)
    check(
        "packet_opportunity_binding",
        packets.get("opportunity_manifest", {}).get("sha256")
        == opportunity_hash,
        opportunity_hash,
    )
    check(
        "vocabulary_packet_binding",
        vocabulary.get("packet_manifest", {}).get("sha256") == packet_hash,
        packet_hash,
    )
    vocabulary_workflow_implementation = (
        PACKAGE_ROOT / "ndp50_vocabulary_workflow.py"
    )
    vocabulary_workflow_ready = (
        vocabulary_review_source_bundles.get("schema_version")
        == "ndp50-source-bundle-draft-manifest/v1"
        and
        vocabulary_review_template.get("schema_version")
        == "ndp50-vocabulary-discovery/v1"
        and vocabulary_review_template.get("draft_vocabulary", {}).get(
            "sha256"
        )
        == vocabulary_draft_hash
        and vocabulary_review_template.get(
            "source_bundle_manifest", {}
        ).get("sha256")
        == vocabulary_review_source_bundle_hash
        and vocabulary_review_workflow.get("schema_version")
        == "ndp50-vocabulary-review-workflow/v1"
        and vocabulary_review_workflow.get("status")
        == "ready_for_independent_vocabulary_discovery"
        and vocabulary_review_workflow.get("draft_vocabulary", {}).get(
            "sha256"
        )
        == vocabulary_draft_hash
        and vocabulary_review_workflow.get(
            "source_bundle_manifest", {}
        ).get("sha256")
        == vocabulary_review_source_bundle_hash
        and vocabulary_review_workflow.get(
            "neutral_discovery_template", {}
        ).get("sha256")
        == _sha256_file(vocabulary_review_template_path)
        and vocabulary_review_workflow.get("implementation", {}).get("file")
        == vocabulary_workflow_implementation.name
        and vocabulary_review_workflow.get("implementation", {}).get(
            "sha256"
        )
        == _sha256_file(vocabulary_workflow_implementation)
        and vocabulary_review_workflow.get("implementation_dependencies")
        == {
            "ndp50_cpa_screen_workflow.py": _sha256_file(
                PACKAGE_ROOT / "ndp50_cpa_screen_workflow.py"
            ),
            "semantic_gold_workflow.py": _sha256_file(
                PACKAGE_ROOT / "semantic_gold_workflow.py"
            ),
        }
        and vocabulary_review_workflow.get("required_discovery_reviewers") == 2
        and vocabulary_review_workflow.get(
            "required_candidate_decision_reviewers"
        )
        == 2
        and vocabulary_review_workflow.get("required_role_coverage")
        == [
            "one_domain_or_scientific_metadata_curator",
            "one_annotation_methodologist",
        ]
        and vocabulary_review_workflow.get("human_decisions_present") is False
        and vocabulary_review_workflow.get("model_outputs_visible") is False
    )
    check(
        "vocabulary_review_workflow_binding",
        vocabulary_workflow_ready,
        f"{vocabulary_review_workflow.get('case_count', 0)} discovery cases",
    )
    source_approval_implementation = PACKAGE_ROOT / "ndp50_source_approval.py"
    source_approval_workflow_ready = (
        source_approval_workflow_spec.get("schema_version")
        == "ndp50-source-approval-workflow-spec/v1"
        and source_approval_workflow_spec.get("status")
        == "implementation_ready_waiting_on_frozen_vocabulary_and_rebuilt_bundles"
        and source_approval_workflow_spec.get("implementation", {}).get("file")
        == source_approval_implementation.name
        and source_approval_workflow_spec.get("implementation", {}).get(
            "sha256"
        )
        == _sha256_file(source_approval_implementation)
        and source_approval_workflow_spec.get("implementation_dependencies")
        == {
            "semantic_gold_workflow.py": _sha256_file(
                PACKAGE_ROOT / "semantic_gold_workflow.py"
            )
        }
        and source_approval_workflow_spec.get(
            "required_independent_reviewers"
        )
        == 2
        and source_approval_workflow_spec.get("required_role_coverage")
        == [
            "one_domain_or_scientific_metadata_curator",
            "one_annotation_methodologist",
        ]
        and source_approval_workflow_spec.get("automatic_approval") is False
        and source_approval_workflow_spec.get("human_decisions_present")
        is False
    )
    check(
        "source_approval_workflow_implementation",
        source_approval_workflow_ready,
        "item-level evidence-purpose approval",
    )
    power_feasibility_validation = validate_feasibility_report(
        semantic_power_feasibility,
        opportunity_manifest_path=opportunity_manifest_path,
        selection_path=selection_path,
        cpa_design_path=cpa_design_path,
        study_root=study_root,
        power_analysis_path=semantic_power_analysis_path,
        power_freeze_path=power_freeze_path,
    )
    power_feasibility_ready = (
        power_feasibility_validation.get("status") == "passed"
        and semantic_power_feasibility.get("gates", {}).get(
            "feasibility_assessed"
        )
        is True
        and semantic_power_feasibility.get("gates", {}).get(
            "validation_confirmatory_power_established"
        )
        is False
        and semantic_power_feasibility.get("validation_claim_scope", {}).get(
            "confirmatory_no_effect_claim_allowed"
        )
        is False
        and semantic_power_feasibility.get("validation_claim_scope", {}).get(
            "confirmatory_superiority_claim_allowed"
        )
        is False
    )
    feasibility_power_plan_frozen = (
        power_feasibility_ready
        and semantic_power_feasibility.get("gates", {}).get(
            "test_power_plan_frozen"
        )
        is True
    )
    check(
        "semantic_power_feasibility",
        power_feasibility_ready,
        (
            f"{semantic_power_feasibility.get('semantic_opportunity_counts', {}).get('validation', {}).get('dataset_cluster_count', 0)} "
            "validation semantic clusters"
        ),
    )
    expected_power_policy_template = build_power_policy_template(
        selection_path=selection_path,
        opportunity_manifest_path=opportunity_manifest_path,
        cpa_design_path=cpa_design_path,
        study_root=study_root,
    )
    expected_power_freeze_workflow = build_power_freeze_workflow_spec(
        selection_path=selection_path,
        opportunity_manifest_path=opportunity_manifest_path,
        cpa_design_path=cpa_design_path,
        policy_template_path=power_policy_template_path,
        study_root=study_root,
    )
    power_freeze_workflow_ready = (
        power_policy_template == expected_power_policy_template
        and power_freeze_workflow == expected_power_freeze_workflow
        and power_policy_template.get("human_decisions_present") is False
        and power_freeze_workflow.get("human_decisions_present") is False
        and power_freeze_workflow.get("test_outcomes_observed") is False
        and power_freeze_workflow.get(
            "validation_or_test_outcomes_forbidden"
        )
        is True
    )
    check(
        "power_freeze_workflow_binding",
        power_freeze_workflow_ready,
        "pre-calibration policy and development-only power workflow",
    )
    expected_test_execution_workflow = build_test_execution_workflow_spec(
        selection_path=selection_path,
        cpa_design_path=cpa_design_path,
        execution_freeze_workflow_path=execution_freeze_workflow_path,
        power_freeze_workflow_path=power_freeze_workflow_path,
        study_root=study_root,
    )
    test_execution_workflow_ready = (
        test_execution_workflow == expected_test_execution_workflow
        and test_execution_workflow.get("status")
        == "implementation_ready_waiting_on_test_release"
        and test_execution_workflow.get("human_decisions_present") is False
        and test_execution_workflow.get("test_outcomes_observed") is False
        and test_execution_workflow.get(
            "test_dataset_identities_included"
        )
        is False
        and test_execution_workflow.get("test_dataset_count") == 25
    )
    check(
        "test_execution_workflow_binding",
        test_execution_workflow_ready,
        "immutable 25-dataset blind-run workflow; test identities omitted",
    )
    expected_publication_gate_workflow = (
        build_publication_gate_workflow_spec(
            public_package_manifest_path=public_package_manifest_path,
            feedback_matrix_path=feedback_matrix_path,
            amendment_path=feedback_amendment_path,
            study_root=PACKAGE_ROOT,
        )
    )
    expected_feedback_signoff_template = build_feedback_signoff_template(
        feedback_matrix_path=feedback_matrix_path,
        amendment_path=feedback_amendment_path,
        study_root=PACKAGE_ROOT,
    )
    publication_gate_workflow_ready = (
        publication_gate_workflow == expected_publication_gate_workflow
        and feedback_response_signoff_template
        == expected_feedback_signoff_template
        and feedback_response_signoff_template.get(
            "human_decisions_present"
        )
        is False
        and feedback_response_signoff_template.get(
            "independence_claimed"
        )
        is False
        and publication_gate_workflow.get("human_decisions_present") is False
        and publication_gate_workflow.get("test_outcomes_observed") is False
        and publication_gate_workflow.get("test_release_authorized") is False
        and public_package_manifest.get("status")
        == "draft_structurally_valid_not_registered"
        and public_package_manifest.get("authorization", {}).get(
            "external_registration_claimed"
        )
        is False
    )
    check(
        "publication_gate_workflow_binding",
        publication_gate_workflow_ready,
        (
            "collaborator feedback sign-off and independently verified "
            "external preregistration required"
        ),
    )
    data_governance_validation = validate_audit_file(
        data_governance,
        study_root=study_root,
    )
    data_governance_gates = data_governance.get("gates", {})
    data_governance_integrity = (
        data_governance_validation.get("status") == "passed"
        and data_governance.get("status")
        == "provenance_integrity_passed_governance_review_required"
        and data_governance.get("scope", {}).get("test_dataset_detail_count")
        == 0
        and data_governance.get("scope", {}).get(
            "test_dataset_identities_included"
        )
        is False
        and all(
            data_governance_gates.get(key) is True
            for key in (
                "detail_snapshot_hashes_verified",
                "dataset_identity_verified",
                "catalog_resource_transport_https_complete",
                "acquired_payload_hashes_complete",
                "acquired_transport_https_complete",
                "test_split_unopened",
            )
        )
    )
    expected_governance_template = build_review_template(
        audit_path=data_governance_path,
        study_root=study_root,
    )
    governance_workflow_implementation = (
        PACKAGE_ROOT / "ndp50_data_governance_review.py"
    )
    governance_review_workflow_ready = (
        data_governance_integrity
        and data_governance_review_template == expected_governance_template
        and data_governance_review_workflow.get("schema_version")
        == "ndp50-data-governance-review-workflow/v1"
        and data_governance_review_workflow.get("status")
        == "ready_for_independent_governance_review_and_approval"
        and data_governance_review_workflow.get("human_decisions_present")
        is False
        and data_governance_review_workflow.get("legal_advice_claimed")
        is False
        and data_governance_review_workflow.get("audit", {}).get("sha256")
        == _sha256_file(data_governance_path)
        and data_governance_review_workflow.get("neutral_template", {}).get(
            "sha256"
        )
        == _sha256_file(data_governance_review_template_path)
        and data_governance_review_workflow.get(
            "required_distinct_signatories"
        )
        == 2
        and data_governance_review_workflow.get("implementation", {}).get(
            "file"
        )
        == governance_workflow_implementation.name
        and data_governance_review_workflow.get("implementation", {}).get(
            "sha256"
        )
        == _sha256_file(governance_workflow_implementation)
        and data_governance_review_workflow.get("implementation_dependencies")
        == {
            "ndp50_data_governance.py": _sha256_file(
                PACKAGE_ROOT / "ndp50_data_governance.py"
            )
        }
    )
    governance_approval = (
        _load_json(data_governance_approval_path)
        if data_governance_approval_path is not None
        else None
    )
    governance_approval_validation = (
        verify_governance_approval(
            governance_approval,
            audit_path=data_governance_path,
            study_root=study_root,
        )
        if governance_approval is not None
        else None
    )
    approved_governance_gates = (
        governance_approval.get("derived_gates", {})
        if governance_approval is not None
        else {}
    )
    data_governance_policy_frozen = (
        governance_review_workflow_ready
        and governance_approval_validation is not None
        and governance_approval_validation.get("status") == "passed"
        and all(
            approved_governance_gates.get(key) is True
            for key in (
                "human_license_and_attribution_review_complete",
                "external_model_data_transfer_policy_frozen",
                "artifact_redistribution_policy_frozen",
                "data_governance_policy_frozen",
            )
        )
    )
    check(
        "data_governance_provenance",
        data_governance_integrity,
        (
            f"{data_governance.get('counts', {}).get('datasets', 0)} "
            "development/validation datasets audited"
        ),
    )
    check(
        "data_governance_review_workflow",
        governance_review_workflow_ready,
        "two-signatory governance review workflow",
    )
    check(
        "bundle_bindings",
        bundle_basis.get("opportunity_manifest", {}).get("sha256")
        == opportunity_hash
        and bundle_basis.get("packet_manifest", {}).get("sha256") == packet_hash
        and bundle_basis.get("vocabulary", {}).get("sha256") == vocabulary_hash,
        f"{bundle_basis.get('case_count', 0)} source bundles",
    )
    check(
        "cpa_opportunity_bindings",
        cpa_design.get("opportunity_manifest", {}).get("sha256")
        == opportunity_hash
        and cpa_screen.get("opportunity_manifest", {}).get("sha256")
        == opportunity_hash,
        f"{cpa_design.get('candidate_counts', {}).get('resource_cases', 0)} CPA candidates",
    )
    cpa_screen_hash = _sha256_file(cpa_screen_path)
    workflow_implementation_path = (
        PACKAGE_ROOT / "ndp50_cpa_screen_workflow.py"
    )
    workflow_ready = (
        cpa_workflow.get("status")
        in {
            "ready_for_independent_screening",
            "workflow_validated_screening_blocked_on_source_approval",
        }
        and cpa_workflow.get("neutral_screen", {}).get("sha256")
        == cpa_screen_hash
        and cpa_workflow.get("opportunity_manifest", {}).get("sha256")
        == opportunity_hash
        and cpa_workflow.get("implementation", {}).get("file")
        == workflow_implementation_path.name
        and cpa_workflow.get("implementation", {}).get("sha256")
        == _sha256_file(workflow_implementation_path)
        and cpa_workflow.get("implementation_dependencies")
        == {
            "ndp50_source_approval.py": _sha256_file(
                PACKAGE_ROOT / "ndp50_source_approval.py"
            ),
            "semantic_gold_workflow.py": _sha256_file(
                PACKAGE_ROOT / "semantic_gold_workflow.py"
            ),
        }
        and cpa_workflow.get("required_independent_submissions") == 2
        and cpa_workflow.get("required_distinct_annotators") == 2
        and cpa_workflow.get("model_outputs_visible_during_screening")
        is False
        and cpa_workflow.get("automatic_adjudication") is False
        and cpa_workflow.get("human_decisions_present") is False
        and cpa_workflow.get("source_bundle_manifest", {}).get("sha256")
        == source_bundle_hash
        and cpa_workflow.get("evidence_binding_complete") is True
        and cpa_workflow.get("evidence_catalog_case_count")
        == cpa_workflow.get("case_count")
    )
    screening_authorized = (
        workflow_ready
        and cpa_workflow.get("status") == "ready_for_independent_screening"
        and cpa_workflow.get("screening_execution_authorized") is True
        and source_bundles_annotation_ready
    )
    check(
        "cpa_screen_workflow_binding",
        workflow_ready,
        f"{cpa_workflow.get('case_count', 0)} blind-screen cases",
    )
    check(
        "semantic_case_identity",
        packets.get("case_count") == opportunity.get("counts", {}).get("case_count")
        == bundle_basis.get("case_count"),
        f"{packets.get('case_count', 0)} packet cases",
    )
    integrity_passed = all(item["passed"] for item in checks)

    evidence_registry = None
    source_bundle_binding = None
    consensus_validation = None
    if all(path is not None for path in consensus_paths):
        assert cpa_submission_a_path is not None
        assert cpa_submission_b_path is not None
        assert cpa_disagreement_worksheet_path is not None
        assert cpa_consensus_path is not None
        evidence_registry, source_bundle_binding, _ = load_evidence_registry(
            source_bundle_manifest_path,
            require_approved=True,
        )
        consensus_validation = validate_consensus(
            _load_json(cpa_consensus_path),
            _load_json(cpa_submission_a_path),
            _load_json(cpa_submission_b_path),
            cpa_screen,
            _load_json(cpa_disagreement_worksheet_path),
            evidence_registry=evidence_registry,
            source_bundle_manifest=source_bundle_binding,
            submission_a_sha256=_sha256_file(cpa_submission_a_path),
            submission_b_sha256=_sha256_file(cpa_submission_b_path),
            neutral_sha256=cpa_screen_hash,
            worksheet_sha256=_sha256_file(
                cpa_disagreement_worksheet_path
            ),
            consensus_sha256=_sha256_file(cpa_consensus_path),
        )
    vocabulary_frozen = False
    if all(path is not None for path in vocabulary_freeze_paths):
        assert vocabulary_candidate_catalog_path is not None
        assert vocabulary_decision_a_path is not None
        assert vocabulary_decision_b_path is not None
        assert vocabulary_disagreement_worksheet_path is not None
        assert vocabulary_consensus_path is not None
        if evidence_registry is None or source_bundle_binding is None:
            evidence_registry, source_bundle_binding, _ = (
                load_evidence_registry(
                    source_bundle_manifest_path,
                    require_approved=False,
                )
            )
        recomputed_vocabulary = build_frozen_vocabulary(
            vocabulary_draft,
            _load_json(vocabulary_candidate_catalog_path),
            _load_json(vocabulary_consensus_path),
            _load_json(vocabulary_decision_a_path),
            _load_json(vocabulary_decision_b_path),
            _load_json(vocabulary_disagreement_worksheet_path),
            evidence_registry=evidence_registry,
            draft_sha256=vocabulary_draft_hash,
            decision_a_sha256=_sha256_file(vocabulary_decision_a_path),
            decision_b_sha256=_sha256_file(vocabulary_decision_b_path),
            worksheet_sha256=_sha256_file(
                vocabulary_disagreement_worksheet_path
            ),
            consensus_sha256=_sha256_file(vocabulary_consensus_path),
        )
        vocabulary_frozen = (
            vocabulary == recomputed_vocabulary
            and validate_vocabulary(vocabulary).get("status") == "ready"
        )
    consensus_complete = (
        consensus_validation is not None
        and consensus_validation.get("status") == "passed"
        and consensus_validation.get("case_count")
        == cpa_workflow.get("case_count")
    )
    semantic_gold_approval = (
        _load_json(semantic_gold_approval_path)
        if semantic_gold_approval_path is not None
        else None
    )
    semantic_gold_approval_validation = (
        verify_gold_approval(
            semantic_gold_approval,
            packet_manifest_path=packet_manifest_path,
            approved_source_manifest_path=source_bundle_manifest_path,
            vocabulary_path=vocabulary_path,
            study_root=study_root,
        )
        if semantic_gold_approval is not None
        else None
    )
    annotator_calibration_validation = (
        validate_annotator_calibration_summary(
            annotator_calibration_summary_path
        )
        if annotator_calibration_summary_path is not None
        else None
    )
    annotator_calibration = (
        annotator_calibration_validation.get("payload")
        if annotator_calibration_validation is not None
        and annotator_calibration_validation.get("status") == "ready"
        else None
    )
    handbook_path = (
        PACKAGE_ROOT / "docs" / "semantic_gold_annotation_handbook_v1.md"
    )
    annotator_calibration_passed = (
        annotator_calibration is not None
        and annotator_calibration.get("status") == "passed"
        and annotator_calibration.get("qualified_handbook_sha256")
        == _sha256_file(handbook_path)
        and annotator_calibration.get("qualified_vocabulary_sha256")
        == _sha256_file(vocabulary_path)
        and isinstance(annotator_calibration.get("annotator_ids"), list)
        and len(annotator_calibration["annotator_ids"]) == 2
        and len(set(annotator_calibration["annotator_ids"])) == 2
    )
    gold_registry_ids = {
        str(item.get("annotator_id") or "")
        for item in (
            (semantic_gold_approval or {})
            .get("index", {})
            .get("annotator_registry", [])
        )
        if isinstance(item, dict)
    }
    gold_registry_ids.discard("")
    gold_annotator_identity_matches_calibration = (
        annotator_calibration_passed
        and semantic_gold_approval is not None
        and gold_registry_ids
        == set(str(value) for value in annotator_calibration["annotator_ids"])
    )
    independent_gold_complete = (
        semantic_gold_workflow_ready
        and annotator_calibration_passed
        and gold_annotator_identity_matches_calibration
        and semantic_gold_approval_validation is not None
        and semantic_gold_approval_validation.get("status") == "passed"
        and semantic_gold_approval.get("derived_gates", {}).get(
            "independent_gold_complete"
        )
        is True
    )
    feedback_signoff_validation = (
        validate_feedback_signoff(
            _load_json(feedback_response_signoff_path),
            feedback_matrix_path=feedback_matrix_path,
            amendment_path=feedback_amendment_path,
            study_root=PACKAGE_ROOT,
        )
        if feedback_response_signoff_path is not None
        else None
    )
    feedback_response_collaborator_signoff_complete = (
        publication_gate_workflow_ready
        and feedback_signoff_validation is not None
        and feedback_signoff_validation.get("status") == "passed"
        and feedback_signoff_validation.get(
            "independent_validation_claimed"
        )
        is False
    )
    external_preregistration_validation = (
        validate_external_preregistration_receipt(
            _load_json(external_preregistration_receipt_path),
            public_package_manifest_path=public_package_manifest_path,
            feedback_signoff_path=feedback_response_signoff_path,
            feedback_matrix_path=feedback_matrix_path,
            amendment_path=feedback_amendment_path,
            study_root=PACKAGE_ROOT,
        )
        if external_preregistration_receipt_path is not None
        and feedback_response_signoff_path is not None
        else None
    )
    external_preregistration_verified = (
        feedback_response_collaborator_signoff_complete
        and external_preregistration_validation is not None
        and external_preregistration_validation.get("status") == "passed"
        and external_preregistration_validation.get(
            "test_release_authorized"
        )
        is False
    )
    if execution_freeze_path is not None and not all(
        path is not None
        for path in (
            cpa_consensus_path,
            semantic_gold_approval_path,
            data_governance_approval_path,
        )
    ):
        raise NDPReadinessError(
            "execution freeze replay requires CPA consensus, semantic-gold "
            "approval, and data-governance approval"
        )
    execution_freeze = (
        _load_json(execution_freeze_path)
        if execution_freeze_path is not None
        else None
    )
    execution_freeze_validation = None
    if execution_freeze is not None:
        assert cpa_consensus_path is not None
        assert semantic_gold_approval_path is not None
        assert data_governance_approval_path is not None
        execution_freeze_validation = verify_execution_freeze(
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
    prompt_and_backend_frozen = (
        execution_freeze_workflow_ready
        and vocabulary_frozen
        and source_bundles_annotation_ready
        and consensus_complete
        and independent_gold_complete
        and data_governance_policy_frozen
        and execution_freeze_validation is not None
        and execution_freeze_validation.get("status") == "passed"
        and execution_freeze.get("derived_gates", {}).get(
            "prompt_and_backend_frozen"
        )
        is True
    )
    if power_freeze_path is not None and execution_freeze_path is None:
        raise NDPReadinessError(
            "NDP power freeze replay requires the execution freeze"
        )
    power_freeze = (
        _load_json(power_freeze_path)
        if power_freeze_path is not None
        else None
    )
    power_freeze_validation = None
    if power_freeze is not None:
        assert completed_power_policy_path is not None
        assert development_calibration_report_path is not None
        assert execution_freeze_path is not None
        power_freeze_validation = verify_power_freeze(
            power_freeze,
            policy_path=completed_power_policy_path,
            calibration_report_path=development_calibration_report_path,
            selection_path=selection_path,
            opportunity_manifest_path=opportunity_manifest_path,
            cpa_design_path=cpa_design_path,
            execution_freeze_path=execution_freeze_path,
            study_root=study_root,
        )
    test_power_plan_frozen = (
        feasibility_power_plan_frozen
        and power_freeze_workflow_ready
        and execution_freeze_validation is not None
        and execution_freeze_validation.get("status") == "passed"
        and power_freeze_validation is not None
        and power_freeze_validation.get("status") == "passed"
        and power_freeze.get("derived_gates", {}).get(
            "test_power_plan_frozen"
        )
        is True
    )
    test_design_meets_pretest_assurance = (
        test_power_plan_frozen
        and power_freeze.get("derived_gates", {}).get(
            "test_design_meets_pretest_assurance"
        )
        is True
    )
    gates = {
        "structural_validation_complete": checks[0]["passed"],
        "test_split_unopened": checks[1]["passed"],
        "semantic_preparation_integrity": integrity_passed,
        "neutral_packets_ready": packets.get("case_count", 0) > 0,
        "vocabulary_review_workflow_ready": vocabulary_workflow_ready,
        "vocabulary_frozen": vocabulary_frozen,
        "source_approval_workflow_implementation_ready": (
            source_approval_workflow_ready
        ),
        "semantic_power_feasibility_assessed": power_feasibility_ready,
        "power_freeze_workflow_ready": power_freeze_workflow_ready,
        "validation_confirmatory_power_established": False,
        "semantic_pilot_reporting_required": True,
        "test_power_plan_frozen": test_power_plan_frozen,
        "test_design_meets_pretest_assurance": (
            test_design_meets_pretest_assurance
        ),
        "data_governance_provenance_integrity": data_governance_integrity,
        "data_governance_review_workflow_ready": (
            governance_review_workflow_ready
        ),
        "data_governance_policy_frozen": data_governance_policy_frozen,
        "human_license_and_attribution_review_complete": (
            approved_governance_gates.get(
                "human_license_and_attribution_review_complete"
            )
            is True
        ),
        "external_model_data_transfer_policy_frozen": (
            approved_governance_gates.get(
                "external_model_data_transfer_policy_frozen"
            )
            is True
        ),
        "artifact_redistribution_policy_frozen": (
            approved_governance_gates.get(
                "artifact_redistribution_policy_frozen"
            )
            is True
        ),
        "source_bundles_annotation_ready": source_bundles_annotation_ready,
        "cpa_screen_workflow_ready": workflow_ready,
        "cpa_independent_screening_authorized": screening_authorized,
        "cpa_applicability_consensus_complete": consensus_complete,
        "semantic_gold_workflow_ready": semantic_gold_workflow_ready,
        "annotator_calibration_passed": annotator_calibration_passed,
        "gold_annotator_identity_matches_calibration": (
            gold_annotator_identity_matches_calibration
        ),
        "independent_gold_complete": independent_gold_complete,
        "demonstration_pool_workflow_ready": (
            demonstration_pool_workflow_ready
        ),
        "execution_freeze_workflow_ready": execution_freeze_workflow_ready,
        "test_execution_workflow_ready": test_execution_workflow_ready,
        "publication_gate_workflow_ready": publication_gate_workflow_ready,
        "feedback_response_collaborator_signoff_complete": (
            feedback_response_collaborator_signoff_complete
        ),
        "external_preregistration_verified": (
            external_preregistration_verified
        ),
        "prompt_and_backend_frozen": prompt_and_backend_frozen,
    }
    semantic_ready = all(
        gates[key]
        for key in (
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
        )
    )
    test_ready = (
        gates["structural_validation_complete"]
        and gates["test_split_unopened"]
        and semantic_ready
        and gates["feedback_response_collaborator_signoff_complete"]
        and gates["external_preregistration_verified"]
    )
    blockers = [
        label
        for key, label in (
            ("vocabulary_frozen", "corpus-specific vocabulary is not frozen"),
            (
                "source_bundles_annotation_ready",
                "source relevance and bundle readiness lack human approval",
            ),
            (
                "cpa_applicability_consensus_complete",
                "two independent CPA applicability screens and consensus are absent",
            ),
            (
                "annotator_calibration_passed",
                "the semantic-gold annotator pair has not passed a "
                "preregistered calibration bound to the frozen handbook "
                "and vocabulary",
            ),
            (
                "independent_gold_complete",
                "calibration-matched two-annotator independent gold and "
                "consensus are absent",
            ),
            (
                "prompt_and_backend_frozen",
                "prompt, serialization, demonstrations, and backend registry are not frozen",
            ),
            (
                "data_governance_policy_frozen",
                "license, attribution, model data-transfer, and artifact redistribution governance are not frozen",
            ),
            (
                "test_power_plan_frozen",
                "frozen non-blind semantic power plan is absent",
            ),
            (
                "feedback_response_collaborator_signoff_complete",
                "collaborator sign-off on the F01--F16 response matrix is absent",
            ),
            (
                "external_preregistration_verified",
                "independently verified immutable OSF/Zenodo preregistration "
                "receipt is absent",
            ),
        )
        if not gates[key]
    ]
    if (
        gates["test_power_plan_frozen"]
        and not gates["test_design_meets_pretest_assurance"]
    ):
        blockers.append(
            "frozen test design does not meet the predeclared power and "
            "semantic-opportunity assurance"
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "implementation": {
            "file": Path(__file__).name,
            "sha256": _sha256_file(Path(__file__)),
        },
        "implementation_dependencies": {
            name: _sha256_file(PACKAGE_ROOT / name)
            for name in (
                "ndp50_cpa_screen_workflow.py",
                "ndp50_data_governance.py",
                "ndp50_data_governance_review.py",
                "ndp50_demonstration_pool.py",
                "ndp50_execution_freeze.py",
                "ndp50_power_feasibility.py",
                "ndp50_power_freeze.py",
                "ndp50_publication_gate.py",
                "ndp50_semantic_gold.py",
                "ndp50_test_execution.py",
                "ndp50_test_inference.py",
                "ndp50_vocabulary_workflow.py",
                "semantic_annotator_calibration.py",
                "semantic_gold_workflow.py",
            )
        },
        "integrity_status": "passed" if integrity_passed else "failed",
        "readiness_status": "ready" if test_ready else "blocked_as_expected",
        "artifact_hashes": {
            "selection": _sha256_file(selection_path),
            "validation_run": _sha256_file(validation_run_path),
            "validation_summary": _sha256_file(validation_summary_path),
            "opportunity_manifest": opportunity_hash,
            "packet_manifest": packet_hash,
            "vocabulary": vocabulary_hash,
            "vocabulary_draft": vocabulary_draft_hash,
            "vocabulary_review_template": _sha256_file(
                vocabulary_review_template_path
            ),
            "vocabulary_review_workflow": _sha256_file(
                vocabulary_review_workflow_path
            ),
            "vocabulary_review_source_bundle_manifest": (
                vocabulary_review_source_bundle_hash
            ),
            "vocabulary_candidate_catalog": (
                _sha256_file(vocabulary_candidate_catalog_path)
                if vocabulary_candidate_catalog_path is not None
                else None
            ),
            "vocabulary_decision_a": (
                _sha256_file(vocabulary_decision_a_path)
                if vocabulary_decision_a_path is not None
                else None
            ),
            "vocabulary_decision_b": (
                _sha256_file(vocabulary_decision_b_path)
                if vocabulary_decision_b_path is not None
                else None
            ),
            "vocabulary_disagreement_worksheet": (
                _sha256_file(vocabulary_disagreement_worksheet_path)
                if vocabulary_disagreement_worksheet_path is not None
                else None
            ),
            "vocabulary_consensus": (
                _sha256_file(vocabulary_consensus_path)
                if vocabulary_consensus_path is not None
                else None
            ),
            "source_bundle_manifest": source_bundle_hash,
            "source_approval_workflow_spec": _sha256_file(
                source_approval_workflow_spec_path
            ),
            "semantic_power_feasibility": _sha256_file(
                semantic_power_feasibility_path
            ),
            "power_policy_template": _sha256_file(
                power_policy_template_path
            ),
            "power_freeze_workflow": _sha256_file(
                power_freeze_workflow_path
            ),
            "data_governance": _sha256_file(data_governance_path),
            "data_governance_review_template": _sha256_file(
                data_governance_review_template_path
            ),
            "data_governance_review_workflow": _sha256_file(
                data_governance_review_workflow_path
            ),
            "data_governance_approval": (
                _sha256_file(data_governance_approval_path)
                if data_governance_approval_path is not None
                else None
            ),
            "semantic_gold_index_template": _sha256_file(
                semantic_gold_index_template_path
            ),
            "semantic_gold_workflow_spec": _sha256_file(
                semantic_gold_workflow_spec_path
            ),
            "demonstration_pool_workflow_spec": _sha256_file(
                demonstration_pool_workflow_spec_path
            ),
            "semantic_gold_approval": (
                _sha256_file(semantic_gold_approval_path)
                if semantic_gold_approval_path is not None
                else None
            ),
            "annotator_calibration_summary": (
                _sha256_file(annotator_calibration_summary_path)
                if annotator_calibration_summary_path is not None
                else None
            ),
            "execution_freeze_config_template": _sha256_file(
                execution_freeze_config_template_path
            ),
            "execution_freeze_workflow": _sha256_file(
                execution_freeze_workflow_path
            ),
            "test_execution_workflow": _sha256_file(
                test_execution_workflow_path
            ),
            "publication_gate_workflow": _sha256_file(
                publication_gate_workflow_path
            ),
            "public_package_manifest": _sha256_file(
                public_package_manifest_path
            ),
            "feedback_response_signoff_template": _sha256_file(
                feedback_response_signoff_template_path
            ),
            "feedback_response_matrix": _sha256_file(
                feedback_matrix_path
            ),
            "feedback_improvement_amendment": _sha256_file(
                feedback_amendment_path
            ),
            "feedback_response_signoff": (
                _sha256_file(feedback_response_signoff_path)
                if feedback_response_signoff_path is not None
                else None
            ),
            "external_preregistration_receipt": (
                _sha256_file(external_preregistration_receipt_path)
                if external_preregistration_receipt_path is not None
                else None
            ),
            "execution_freeze": (
                _sha256_file(execution_freeze_path)
                if execution_freeze_path is not None
                else None
            ),
            "semantic_power_analysis": (
                _sha256_file(semantic_power_analysis_path)
                if semantic_power_analysis_path is not None
                else None
            ),
            "completed_power_policy": (
                _sha256_file(completed_power_policy_path)
                if completed_power_policy_path is not None
                else None
            ),
            "development_calibration_report": (
                _sha256_file(development_calibration_report_path)
                if development_calibration_report_path is not None
                else None
            ),
            "power_freeze": (
                _sha256_file(power_freeze_path)
                if power_freeze_path is not None
                else None
            ),
            "cpa_design": _sha256_file(cpa_design_path),
            "cpa_screen": cpa_screen_hash,
            "cpa_workflow": _sha256_file(cpa_workflow_path),
            "cpa_submission_a": (
                _sha256_file(cpa_submission_a_path)
                if cpa_submission_a_path is not None
                else None
            ),
            "cpa_submission_b": (
                _sha256_file(cpa_submission_b_path)
                if cpa_submission_b_path is not None
                else None
            ),
            "cpa_disagreement_worksheet": (
                _sha256_file(cpa_disagreement_worksheet_path)
                if cpa_disagreement_worksheet_path is not None
                else None
            ),
            "cpa_consensus": (
                _sha256_file(cpa_consensus_path)
                if cpa_consensus_path is not None
                else None
            ),
        },
        "checks": checks,
        "gates": gates,
        "publication_gate_validation": {
            "feedback_response_signoff": feedback_signoff_validation,
            "external_preregistration_receipt": (
                external_preregistration_validation
            ),
        },
        "semantic_execution_ready": semantic_ready,
        "test_ready": test_ready,
        "blockers": blockers,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the NDP-50 post-validation research readiness report."
    )
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--validation-run", type=Path, required=True)
    parser.add_argument("--validation-summary", type=Path, required=True)
    parser.add_argument("--opportunity-manifest", type=Path, required=True)
    parser.add_argument("--packet-manifest", type=Path, required=True)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--vocabulary-draft", type=Path)
    parser.add_argument(
        "--vocabulary-review-template", type=Path, required=True
    )
    parser.add_argument(
        "--vocabulary-review-workflow", type=Path, required=True
    )
    parser.add_argument(
        "--vocabulary-review-source-bundle-manifest", type=Path
    )
    parser.add_argument("--vocabulary-candidate-catalog", type=Path)
    parser.add_argument("--vocabulary-decision-a", type=Path)
    parser.add_argument("--vocabulary-decision-b", type=Path)
    parser.add_argument("--vocabulary-disagreement-worksheet", type=Path)
    parser.add_argument("--vocabulary-consensus", type=Path)
    parser.add_argument("--source-bundle-manifest", type=Path, required=True)
    parser.add_argument(
        "--source-approval-workflow-spec", type=Path, required=True
    )
    parser.add_argument(
        "--semantic-power-feasibility", type=Path, required=True
    )
    parser.add_argument(
        "--power-policy-template", type=Path, required=True
    )
    parser.add_argument(
        "--power-freeze-workflow", type=Path, required=True
    )
    parser.add_argument("--data-governance", type=Path, required=True)
    parser.add_argument(
        "--data-governance-review-template", type=Path, required=True
    )
    parser.add_argument(
        "--data-governance-review-workflow", type=Path, required=True
    )
    parser.add_argument("--data-governance-approval", type=Path)
    parser.add_argument(
        "--semantic-gold-index-template", type=Path, required=True
    )
    parser.add_argument(
        "--semantic-gold-workflow-spec", type=Path, required=True
    )
    parser.add_argument(
        "--demonstration-pool-workflow-spec", type=Path, required=True
    )
    parser.add_argument("--semantic-gold-approval", type=Path)
    parser.add_argument("--annotator-calibration-summary", type=Path)
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
        "--public-package-manifest", type=Path, required=True
    )
    parser.add_argument(
        "--feedback-response-signoff-template", type=Path, required=True
    )
    parser.add_argument("--feedback-matrix", type=Path, required=True)
    parser.add_argument("--feedback-amendment", type=Path, required=True)
    parser.add_argument("--feedback-response-signoff", type=Path)
    parser.add_argument("--external-preregistration-receipt", type=Path)
    parser.add_argument("--execution-freeze", type=Path)
    parser.add_argument("--semantic-power-analysis", type=Path)
    parser.add_argument("--completed-power-policy", type=Path)
    parser.add_argument("--development-calibration-report", type=Path)
    parser.add_argument("--power-freeze", type=Path)
    parser.add_argument("--cpa-design", type=Path, required=True)
    parser.add_argument("--cpa-screen", type=Path, required=True)
    parser.add_argument("--cpa-workflow", type=Path, required=True)
    parser.add_argument("--cpa-submission-a", type=Path)
    parser.add_argument("--cpa-submission-b", type=Path)
    parser.add_argument("--cpa-disagreement-worksheet", type=Path)
    parser.add_argument("--cpa-consensus", type=Path)
    parser.add_argument("--study-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_readiness_report(
        selection_path=args.selection,
        validation_run_path=args.validation_run,
        validation_summary_path=args.validation_summary,
        opportunity_manifest_path=args.opportunity_manifest,
        packet_manifest_path=args.packet_manifest,
        vocabulary_path=args.vocabulary,
        vocabulary_draft_path=args.vocabulary_draft or args.vocabulary,
        vocabulary_review_template_path=args.vocabulary_review_template,
        vocabulary_review_workflow_path=args.vocabulary_review_workflow,
        vocabulary_review_source_bundle_manifest_path=(
            args.vocabulary_review_source_bundle_manifest
            or args.source_bundle_manifest
        ),
        source_bundle_manifest_path=args.source_bundle_manifest,
        source_approval_workflow_spec_path=(
            args.source_approval_workflow_spec
        ),
        semantic_power_feasibility_path=args.semantic_power_feasibility,
        power_policy_template_path=args.power_policy_template,
        power_freeze_workflow_path=args.power_freeze_workflow,
        data_governance_path=args.data_governance,
        data_governance_review_template_path=(
            args.data_governance_review_template
        ),
        data_governance_review_workflow_path=(
            args.data_governance_review_workflow
        ),
        data_governance_approval_path=args.data_governance_approval,
        semantic_gold_index_template_path=(
            args.semantic_gold_index_template
        ),
        semantic_gold_workflow_spec_path=args.semantic_gold_workflow_spec,
        demonstration_pool_workflow_spec_path=(
            args.demonstration_pool_workflow_spec
        ),
        semantic_gold_approval_path=args.semantic_gold_approval,
        annotator_calibration_summary_path=(
            args.annotator_calibration_summary
        ),
        execution_freeze_config_template_path=(
            args.execution_freeze_config_template
        ),
        execution_freeze_workflow_path=args.execution_freeze_workflow,
        test_execution_workflow_path=args.test_execution_workflow,
        publication_gate_workflow_path=args.publication_gate_workflow,
        public_package_manifest_path=args.public_package_manifest,
        feedback_response_signoff_template_path=(
            args.feedback_response_signoff_template
        ),
        feedback_matrix_path=args.feedback_matrix,
        feedback_amendment_path=args.feedback_amendment,
        feedback_response_signoff_path=args.feedback_response_signoff,
        external_preregistration_receipt_path=(
            args.external_preregistration_receipt
        ),
        execution_freeze_path=args.execution_freeze,
        cpa_design_path=args.cpa_design,
        cpa_screen_path=args.cpa_screen,
        cpa_workflow_path=args.cpa_workflow,
        study_root=args.study_root,
        cpa_submission_a_path=args.cpa_submission_a,
        cpa_submission_b_path=args.cpa_submission_b,
        cpa_disagreement_worksheet_path=args.cpa_disagreement_worksheet,
        cpa_consensus_path=args.cpa_consensus,
        vocabulary_candidate_catalog_path=args.vocabulary_candidate_catalog,
        vocabulary_decision_a_path=args.vocabulary_decision_a,
        vocabulary_decision_b_path=args.vocabulary_decision_b,
        vocabulary_disagreement_worksheet_path=(
            args.vocabulary_disagreement_worksheet
        ),
        vocabulary_consensus_path=args.vocabulary_consensus,
        semantic_power_analysis_path=args.semantic_power_analysis,
        completed_power_policy_path=args.completed_power_policy,
        development_calibration_report_path=(
            args.development_calibration_report
        ),
        power_freeze_path=args.power_freeze,
    )
    _write_json(args.output, report)
    print(
        json.dumps(
            {
                "integrity_status": report["integrity_status"],
                "readiness_status": report["readiness_status"],
                "semantic_execution_ready": report["semantic_execution_ready"],
                "test_ready": report["test_ready"],
                "blocker_count": len(report["blockers"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["integrity_status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
