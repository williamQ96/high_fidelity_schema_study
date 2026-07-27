from __future__ import annotations

import hashlib
import json
from pathlib import Path

from high_fidelity_schema_study.ndp50_cpa_design import (
    registered_analysis_contract,
    registered_metric_contract,
)
from high_fidelity_schema_study.ndp50_readiness import build_readiness_report
from high_fidelity_schema_study.ndp50_power_feasibility import (
    build_feasibility_report,
)
from high_fidelity_schema_study.ndp50_data_governance_review import (
    build_review_template,
    build_workflow_spec as build_governance_workflow_spec,
)
from high_fidelity_schema_study.ndp50_semantic_gold import (
    build_index_template as build_gold_index_template,
    build_workflow_spec as build_gold_workflow_spec,
)
from high_fidelity_schema_study.ndp50_execution_freeze import (
    build_config_template as build_execution_config_template,
    build_workflow_spec as build_execution_workflow_spec,
)


def _write(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_readiness_separates_integrity_from_human_freeze_gates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    selection = tmp_path / "selection.json"
    _write(
        selection,
        {
            "counts": {
                "selected_dataset_count": 3,
                "split_counts": {
                    "development": 1,
                    "validation": 1,
                    "test": 1,
                },
            },
            "selected_datasets": [
                {"dataset_id": "d1", "split": "development"},
                {"dataset_id": "v1", "split": "validation"},
                {"dataset_id": "t1", "split": "test"},
            ]
        },
    )
    run = tmp_path / "validation.json"
    _write(run, {"run_role": "validation", "datasets": [{"dataset_id": "v1"}]})
    summary = tmp_path / "summary.json"
    _write(
        summary,
        {
            "run_role": "validation",
            "selection_integrity": {"exact_id_match": True},
        },
    )
    opportunity = tmp_path / "opportunity.json"
    opportunity_hash = _write(
        opportunity,
        {
            "schema_version": "ndp50-semantic-opportunity-manifest/v1",
            "counts": {
                "case_count": 1,
                "dataset_cluster_count": 1,
                "split_case_counts": {
                    "development": 0,
                    "validation": 1,
                },
            },
            "cases": [
                {
                    "case_id": "case-1",
                    "dataset_id": "v1",
                    "split": "validation",
                    "cpa_applicability_status": (
                        "requires_manual_relation_and_subject_assessment"
                    ),
                }
            ],
        },
    )
    packet_file = tmp_path / "packet_files" / "case-1.json"
    packet_file_hash = _write(packet_file, {"case_id": "case-1"})
    packets = tmp_path / "packets.json"
    packet_hash = _write(
        packets,
        {
            "schema_version": "ndp50-semantic-packet-pack/v1",
            "status": "neutral_packets_ready_source_bundles_blocked",
            "opportunity_manifest": {"sha256": opportunity_hash},
            "case_count": 1,
            "cases": [
                {
                    "case_id": "case-1",
                    "dataset_id": "v1",
                    "split": "validation",
                    "packet_file": "packet_files/case-1.json",
                    "packet_sha256": packet_file_hash,
                }
            ],
        },
    )
    vocabulary = tmp_path / "vocabulary.json"
    vocabulary_hash = _write(
        vocabulary,
        {
            "status": "draft",
            "packet_manifest": {"sha256": packet_hash},
        },
    )
    bundles = tmp_path / "bundles.json"
    bundle_hash = _write(
        bundles,
        {
            "schema_version": "ndp50-source-bundle-draft-manifest/v1",
            "status": "draft_bundles_structurally_valid_not_annotation_ready",
            "opportunity_manifest": {"sha256": opportunity_hash},
            "packet_manifest": {"sha256": packet_hash},
            "vocabulary": {"sha256": vocabulary_hash},
            "case_count": 1,
        },
    )
    source_approval_implementation = (
        Path(__file__).resolve().parents[1] / "ndp50_source_approval.py"
    )
    source_approval_spec = tmp_path / "source_approval_spec.json"
    _write(
        source_approval_spec,
        {
            "schema_version": "ndp50-source-approval-workflow-spec/v1",
            "status": (
                "implementation_ready_waiting_on_frozen_vocabulary_and_rebuilt_bundles"
            ),
            "implementation": {
                "file": source_approval_implementation.name,
                "sha256": hashlib.sha256(
                    source_approval_implementation.read_bytes()
                ).hexdigest(),
            },
            "implementation_dependencies": {
                "semantic_gold_workflow.py": hashlib.sha256(
                    (
                        Path(__file__).resolve().parents[1]
                        / "semantic_gold_workflow.py"
                    ).read_bytes()
                ).hexdigest()
            },
            "required_independent_reviewers": 2,
            "required_role_coverage": [
                "one_domain_or_scientific_metadata_curator",
                "one_annotation_methodologist",
            ],
            "automatic_approval": False,
            "human_decisions_present": False,
        },
    )
    vocabulary_review_template = tmp_path / "vocabulary_review_template.json"
    vocabulary_review_template_hash = _write(
        vocabulary_review_template,
        {
            "schema_version": "ndp50-vocabulary-discovery/v1",
            "draft_vocabulary": {"sha256": vocabulary_hash},
            "source_bundle_manifest": {"sha256": bundle_hash},
        },
    )
    vocabulary_workflow_implementation = (
        Path(__file__).resolve().parents[1]
        / "ndp50_vocabulary_workflow.py"
    )
    vocabulary_review_workflow = tmp_path / "vocabulary_workflow.json"
    _write(
        vocabulary_review_workflow,
        {
            "schema_version": "ndp50-vocabulary-review-workflow/v1",
            "status": "ready_for_independent_vocabulary_discovery",
            "draft_vocabulary": {"sha256": vocabulary_hash},
            "source_bundle_manifest": {"sha256": bundle_hash},
            "neutral_discovery_template": {
                "sha256": vocabulary_review_template_hash
            },
            "implementation": {
                "file": vocabulary_workflow_implementation.name,
                "sha256": hashlib.sha256(
                    vocabulary_workflow_implementation.read_bytes()
                ).hexdigest(),
            },
            "implementation_dependencies": {
                "ndp50_cpa_screen_workflow.py": hashlib.sha256(
                    (
                        Path(__file__).resolve().parents[1]
                        / "ndp50_cpa_screen_workflow.py"
                    ).read_bytes()
                ).hexdigest(),
                "semantic_gold_workflow.py": hashlib.sha256(
                    (
                        Path(__file__).resolve().parents[1]
                        / "semantic_gold_workflow.py"
                    ).read_bytes()
                ).hexdigest(),
            },
            "case_count": 1,
            "required_discovery_reviewers": 2,
            "required_candidate_decision_reviewers": 2,
            "required_role_coverage": [
                "one_domain_or_scientific_metadata_curator",
                "one_annotation_methodologist",
            ],
            "human_decisions_present": False,
            "model_outputs_visible": False,
        },
    )
    cpa_design = tmp_path / "cpa.json"
    _write(
        cpa_design,
        {
            "schema_version": "ndp50-cpa-design/v1",
            "opportunity_manifest": {"sha256": opportunity_hash},
            "planned_arms": [
                "deterministic_only",
                "zero_shot_dataset_level",
                (
                    "zero_shot_byte_identical_response_plus_"
                    "deterministic_verification"
                ),
                "one_shot_development_similarity_selected",
                "five_shot_development_similarity_selected",
            ],
            "row_sampling_sensitivity": [
                "head",
                "fixed_seed_stratified",
                "fixed_seed_adaptive",
            ],
            "analysis": registered_analysis_contract(),
            "metric_contract": registered_metric_contract(),
            "candidate_counts": {
                "resource_cases": 1,
                "dataset_clusters": 1,
                "split_case_counts": {
                    "development": 0,
                    "validation": 1,
                },
            },
        },
    )
    cpa_screen = tmp_path / "screen.json"
    cpa_screen_hash = _write(
        cpa_screen,
        {
            "opportunity_manifest": {"sha256": opportunity_hash},
            "annotation_stage": "independent_pre_model_screen",
            "cases": [
                {
                    "relational_table_applicable": None,
                    "single_subject_column_supported": None,
                    "property_annotation_applicable": None,
                    "rationale": None,
                }
            ],
        },
    )
    workflow_implementation = (
        Path(__file__).resolve().parents[1]
        / "ndp50_cpa_screen_workflow.py"
    )
    cpa_workflow = tmp_path / "workflow.json"
    _write(
        cpa_workflow,
        {
            "status": "workflow_validated_screening_blocked_on_source_approval",
            "neutral_screen": {"sha256": cpa_screen_hash},
            "opportunity_manifest": {"sha256": opportunity_hash},
            "source_bundle_manifest": {
                "sha256": hashlib.sha256(bundles.read_bytes()).hexdigest()
            },
            "implementation": {
                "file": workflow_implementation.name,
                "sha256": hashlib.sha256(
                    workflow_implementation.read_bytes()
                ).hexdigest(),
            },
            "implementation_dependencies": {
                "ndp50_source_approval.py": hashlib.sha256(
                    (
                        Path(__file__).resolve().parents[1]
                        / "ndp50_source_approval.py"
                    ).read_bytes()
                ).hexdigest(),
                "semantic_gold_workflow.py": hashlib.sha256(
                    (
                        Path(__file__).resolve().parents[1]
                        / "semantic_gold_workflow.py"
                    ).read_bytes()
                ).hexdigest(),
            },
            "case_count": 1,
            "required_independent_submissions": 2,
            "required_distinct_annotators": 2,
            "model_outputs_visible_during_screening": False,
            "automatic_adjudication": False,
            "human_decisions_present": False,
            "screening_execution_authorized": False,
            "evidence_binding_complete": True,
            "evidence_catalog_case_count": 1,
        },
    )
    power_feasibility = tmp_path / "power_feasibility.json"
    _write(
        power_feasibility,
        build_feasibility_report(
            opportunity_manifest_path=opportunity,
            selection_path=selection,
            cpa_design_path=cpa_design,
            study_root=tmp_path,
        ),
    )
    power_policy_template = tmp_path / "power_policy_template.json"
    power_freeze_workflow = tmp_path / "power_freeze_workflow.json"
    neutral_power_policy = {
        "schema_version": "ndp50-power-policy/v1",
        "status": "neutral_pending_precalibration_policy",
        "human_decisions_present": False,
    }
    neutral_power_workflow = {
        "schema_version": "ndp50-power-freeze-workflow/v1",
        "status": "implementation_ready_waiting_on_execution_freeze",
        "human_decisions_present": False,
        "test_outcomes_observed": False,
        "validation_or_test_outcomes_forbidden": True,
    }
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_readiness."
        "build_power_policy_template",
        lambda **kwargs: neutral_power_policy,
    )
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_readiness."
        "build_power_freeze_workflow_spec",
        lambda **kwargs: neutral_power_workflow,
    )
    _write(power_policy_template, neutral_power_policy)
    _write(power_freeze_workflow, neutral_power_workflow)
    data_governance = tmp_path / "data_governance.json"
    _write(
        data_governance,
        {
            "schema_version": "ndp50-data-governance-audit/v1",
            "status": (
                "provenance_integrity_passed_governance_review_required"
            ),
            "scope": {
                "test_dataset_detail_count": 0,
                "test_dataset_identities_included": False,
            },
            "counts": {"datasets": 2},
            "datasets": [],
            "gates": {
                "detail_snapshot_hashes_verified": True,
                "dataset_identity_verified": True,
                "catalog_resource_transport_https_complete": True,
                "acquired_payload_hashes_complete": True,
                "acquired_transport_https_complete": True,
                "human_license_and_attribution_review_complete": False,
                "external_model_data_transfer_policy_frozen": False,
                "artifact_redistribution_policy_frozen": False,
                "test_split_unopened": True,
            },
        },
    )
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_readiness.validate_audit_file",
        lambda payload, *, study_root: {
            "status": "passed",
            "differing_top_level_keys": [],
        },
    )
    monkeypatch.setattr(
        (
            "high_fidelity_schema_study.ndp50_data_governance_review."
            "validate_audit_file"
        ),
        lambda payload, *, study_root: {
            "status": "passed",
            "differing_top_level_keys": [],
        },
    )
    data_governance_review_template = (
        tmp_path / "data_governance_review_template.json"
    )
    _write(
        data_governance_review_template,
        build_review_template(
            audit_path=data_governance,
            study_root=tmp_path,
        ),
    )
    data_governance_review_workflow = (
        tmp_path / "data_governance_review_workflow.json"
    )
    _write(
        data_governance_review_workflow,
        build_governance_workflow_spec(
            audit_path=data_governance,
            template_path=data_governance_review_template,
        ),
    )
    semantic_gold_index_template = (
        tmp_path / "semantic_gold_index_template.json"
    )
    _write(
        semantic_gold_index_template,
        build_gold_index_template(
            packet_manifest_path=packets,
            study_root=tmp_path,
        ),
    )
    semantic_gold_workflow_spec = (
        tmp_path / "semantic_gold_workflow_spec.json"
    )
    _write(
        semantic_gold_workflow_spec,
        build_gold_workflow_spec(
            packet_manifest_path=packets,
            index_template_path=semantic_gold_index_template,
            study_root=tmp_path,
        ),
    )
    demonstration_pool_workflow_spec = (
        tmp_path / "demonstration_pool_workflow_spec.json"
    )
    demonstration_pool_workflow = {
        "schema_version": "ndp50-demonstration-pool-workflow/v1",
        "status": "implementation_ready_waiting_on_semantic_gold",
        "human_decisions_present": False,
        "candidate_inclusion_policy": "all_approved_development_cases",
        "development_case_count": 1,
        "validation_or_test_candidates_forbidden": True,
        "model_outputs_used_for_inclusion": False,
    }
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_readiness."
        "build_demonstration_pool_workflow_spec",
        lambda **kwargs: demonstration_pool_workflow,
    )
    _write(
        demonstration_pool_workflow_spec,
        demonstration_pool_workflow,
    )
    execution_freeze_config_template = (
        tmp_path / "execution_freeze_config_template.json"
    )
    _write(
        execution_freeze_config_template,
        build_execution_config_template(
            cpa_design_path=cpa_design,
            packet_manifest_path=packets,
            study_root=tmp_path,
        ),
    )
    execution_freeze_workflow = (
        tmp_path / "execution_freeze_workflow.json"
    )
    _write(
        execution_freeze_workflow,
        build_execution_workflow_spec(
            cpa_design_path=cpa_design,
            packet_manifest_path=packets,
            config_template_path=execution_freeze_config_template,
            study_root=tmp_path,
        ),
    )
    test_execution_workflow = tmp_path / "test_execution_workflow.json"
    test_execution_workflow_payload = {
        "schema_version": "ndp50-test-execution-workflow/v1",
        "status": "implementation_ready_waiting_on_test_release",
        "human_decisions_present": False,
        "test_outcomes_observed": False,
        "test_dataset_identities_included": False,
        "test_dataset_count": 25,
    }
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_readiness."
        "build_test_execution_workflow_spec",
        lambda **kwargs: test_execution_workflow_payload,
    )
    _write(test_execution_workflow, test_execution_workflow_payload)

    readiness_kwargs = {
        "selection_path": selection,
        "validation_run_path": run,
        "validation_summary_path": summary,
        "opportunity_manifest_path": opportunity,
        "packet_manifest_path": packets,
        "vocabulary_path": vocabulary,
        "vocabulary_draft_path": vocabulary,
        "vocabulary_review_template_path": vocabulary_review_template,
        "vocabulary_review_workflow_path": vocabulary_review_workflow,
        "vocabulary_review_source_bundle_manifest_path": bundles,
        "source_bundle_manifest_path": bundles,
        "source_approval_workflow_spec_path": source_approval_spec,
        "semantic_power_feasibility_path": power_feasibility,
        "power_policy_template_path": power_policy_template,
        "power_freeze_workflow_path": power_freeze_workflow,
        "data_governance_path": data_governance,
        "data_governance_review_template_path": (
            data_governance_review_template
        ),
        "data_governance_review_workflow_path": (
            data_governance_review_workflow
        ),
        "semantic_gold_index_template_path": semantic_gold_index_template,
        "semantic_gold_workflow_spec_path": semantic_gold_workflow_spec,
        "demonstration_pool_workflow_spec_path": (
            demonstration_pool_workflow_spec
        ),
        "execution_freeze_config_template_path": (
            execution_freeze_config_template
        ),
        "execution_freeze_workflow_path": execution_freeze_workflow,
        "test_execution_workflow_path": test_execution_workflow,
        "cpa_design_path": cpa_design,
        "cpa_screen_path": cpa_screen,
        "cpa_workflow_path": cpa_workflow,
        "study_root": tmp_path,
    }
    report = build_readiness_report(**readiness_kwargs)

    assert report["integrity_status"] == "passed"
    assert report["readiness_status"] == "blocked_as_expected"
    assert report["semantic_execution_ready"] is False
    assert report["test_ready"] is False
    assert report["gates"]["test_split_unopened"] is True
    assert report["gates"]["vocabulary_review_workflow_ready"] is True
    assert report["gates"]["vocabulary_frozen"] is False
    assert report["gates"][
        "source_approval_workflow_implementation_ready"
    ] is True
    assert report["gates"]["semantic_power_feasibility_assessed"] is True
    assert report["gates"]["power_freeze_workflow_ready"] is True
    assert report["gates"]["validation_confirmatory_power_established"] is False
    assert report["gates"]["test_power_plan_frozen"] is False
    assert report["gates"]["data_governance_provenance_integrity"] is True
    assert report["gates"]["data_governance_review_workflow_ready"] is True
    assert report["gates"]["data_governance_policy_frozen"] is False
    assert report["gates"]["semantic_gold_workflow_ready"] is True
    assert report["gates"]["demonstration_pool_workflow_ready"] is True
    assert report["gates"]["independent_gold_complete"] is False
    assert report["gates"]["execution_freeze_workflow_ready"] is True
    assert report["gates"]["test_execution_workflow_ready"] is True
    assert report["gates"]["prompt_and_backend_frozen"] is False
    assert report["gates"]["cpa_screen_workflow_ready"] is True
    assert report["gates"]["cpa_independent_screening_authorized"] is False
    assert report["gates"]["cpa_applicability_consensus_complete"] is False

    semantic_gold_approval = tmp_path / "semantic_gold_approval.json"
    _write(
        semantic_gold_approval,
        {
            "schema_version": "ndp50-semantic-gold-approval/v1",
            "derived_gates": {"independent_gold_complete": True},
        },
    )
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_readiness.verify_gold_approval",
        lambda *args, **kwargs: {
            "status": "passed",
            "differing_top_level_keys": [],
        },
    )
    report_with_gold = build_readiness_report(
        **readiness_kwargs,
        semantic_gold_approval_path=semantic_gold_approval,
    )

    assert report_with_gold["gates"]["independent_gold_complete"] is True
    assert report_with_gold["artifact_hashes"][
        "semantic_gold_approval"
    ] == hashlib.sha256(semantic_gold_approval.read_bytes()).hexdigest()
