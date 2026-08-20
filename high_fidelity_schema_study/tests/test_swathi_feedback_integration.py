import argparse
import hashlib
import json
from pathlib import Path

from high_fidelity_schema_study import ndp50_demonstration_pool
from high_fidelity_schema_study import ndp50_execution_qualification
from high_fidelity_schema_study import ndp50_test_inference
from high_fidelity_schema_study import semantic_annotator_calibration
from high_fidelity_schema_study import semantic_gold_workflow
from high_fidelity_schema_study import semantic_power_analysis


ROOT = Path("high_fidelity_schema_study")


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def normalized(relative_path: str) -> str:
    return " ".join(read_text(relative_path).split())


def sha256(relative_path: str) -> str:
    return hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()


def subcommand_options(parser, command: str) -> set[str]:
    subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    child = subparsers.choices[command]
    return {
        option
        for action in child._actions
        for option in action.option_strings
    }


def test_feedback_matrix_covers_every_review_item_and_decision_class():
    text = read_text("docs/swathi_feedback_response_matrix_v1.md")

    for item_number in range(1, 17):
        assert f"F{item_number:02d}" in text

    for decision in (
        "**Accept**",
        "**Accept with boundary**",
        "**Pre-freeze decision gate**",
        "**Do not adopt as stated**",
    ):
        assert decision in text


def test_amendment_preserves_freeze_and_authorization_boundaries():
    text = normalized("docs/ndp50_feedback_improvement_amendment_v1.md")
    lower_text = text.lower()

    assert "does not authorize semantic validation or test opening" in text
    assert "Changes requiring a new executable design version" in text
    assert "do not include in the confirmatory test matrix" in text
    assert "test execution: not authorized" in text
    assert "human consensus is a reference standard" in lower_text


def test_collaborator_role_is_disjoint_from_independent_roles():
    amendment = normalized("docs/ndp50_feedback_improvement_amendment_v1.md")
    protocol = normalized("docs/ndp50_protocol_v1.md")
    guide = normalized("docs/ndp50_swathi_feedback_signoff_guide_v1.md")

    assert "Swathi / postdoctoral research collaborator" in amendment
    assert "Cannot fill a slot whose validity depends on being blind and independent" in amendment
    assert "cannot fill a slot whose validity depends on being blind and" in protocol
    assert "independent of the project" in protocol
    assert "this review is not independent validation" in guide
    assert "does not validate empirical results" in guide
    assert "does not" in guide and "authorize test access" in guide


def test_literature_review_records_scope_boundaries_and_identifiers():
    text = normalized(
        "docs/literature/semantic_architecture_literature_review_2026-07-27.md"
    )

    for identifier in (
        "10.1145/3514221.3517906",
        "10.14778/3665844.3665857",
        "10.1007/978-3-031-78952-6_6",
        "10.14778/3476311.3476346",
        "10.52202/079017-0076",
        "10.1145/3786626",
        "2407.01032",
        "10.18653/v1/2023.findings-emnlp.722",
        "10.18653/v1/D16-1239",
        "10.1177/001316446002000104",
        "2305.05176",
        "2502.01050",
        "2510.22251",
    ):
        assert identifier in text

    assert "do not make it a full-file schema-extraction baseline" in text
    assert "not a direct primary baseline" in text
    assert "Gold standard, not an upper bound" in text
    assert "does not compare row-sampling policies or report macro- and per-label F1" in text
    assert "bibliographic identity only" in text
    assert "prohibition against plausible but unentailed extrapolation" in text
    assert "Recovering the Semantics of Tables on the Web" in text
    assert "Khan (2025), Prompting Inversion" in text
    assert "validation of Model Capability Debt" in text


def test_feedback_sources_distinguish_korini_from_khan():
    matrix = normalized("docs/swathi_feedback_response_matrix_v1.md")
    bibliography = read_text("paper/references.bib")

    assert (
        "10.1007/978-3-031-78952-6_6` resolves to Korini and "
        "Bizer's *Column Property Annotation Using Large Language Models*, "
        "not to Khan's prompting-inversion paper"
    ) in matrix
    assert "Khan's separate arXiv preprint `2510.22251`" in matrix
    assert "Neither source validates Model Capability Debt" in matrix
    assert "@article{khan2025promptinginversion" in bibliography
    assert "doi={10.48550/arXiv.2510.22251}" in bibliography


def test_english_manuscript_contains_feedback_guardrails():
    text = read_text("paper/semantic_architecture_study_en.tex")

    assert "A Replay-Controlled Evaluation Protocol" in text
    assert "\\section{Related Work and Evaluation Position}" in text
    assert "\\subsection{NDP-50 operationalization}" in text
    assert "External preregistration DOI/receipt and timestamp" in text
    assert "Human consensus is" in text
    assert "not a human upper bound" in text
    assert "Active collaborators and developers cannot be counted" in text
    assert "\\cite{khan2025promptinginversion}" in text
    assert "That preprint does not validate our construct" in text
    assert "Causally Controlled" not in text
    assert "causal contribution" not in text


def test_claim_ledger_covers_current_fact_and_unresolved_boundaries():
    text = normalized("docs/semantic_architecture_claim_ledger_v1.md")

    for claim_number in range(1, 46):
        assert f"CL{claim_number:02d}" in text

    for boundary in (
        "not an architecture winner",
        "not a human upper bound",
        "not active in design v1",
        "no DOI/receipt currently exists",
        "cannot prove absence from model pretraining",
        "not scientific truth",
    ):
        assert boundary in text


def test_preregistration_draft_binds_current_public_hashes():
    text = read_text(
        "docs/preregistration/ndp50_osf_zenodo_preregistration_draft_v1.md"
    )

    expected_bindings = {
        "data/experiments/ndp50_v1/candidate_frame.json",
        "data/experiments/ndp50_v1/selection.json",
        "data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json",
        "docs/ndp50_structural_validation_report_v1.md",
            "docs/ndp50_feedback_implementation_audit_v1.md",
            "docs/ndp50_feedback_improvement_amendment_v1.md",
            "docs/ndp50_human_external_gate_ledger_v1.md",
            "docs/ndp50_initial_human_assignment_guide_v1.md",
        "docs/ndp50_scope_provenance_v1.md",
        "docs/ndp50_statistical_analysis_plan_v1.md",
        "docs/ndp50_annotation_and_independence_plan_v1.md",
        "docs/ndp50_power_policy_review_guide_v1.md",
        "docs/ndp50_methodological_risk_register_v1.md",
        "docs/ndp50_swathi_feedback_signoff_guide_v1.md",
        "docs/semantic_annotator_calibration_protocol_v1.md",
        "docs/semantic_architecture_claim_ledger_v1.md",
        "docs/semantic_gold_workflow_protocol_v1.md",
        "docs/semantic_power_analysis_protocol_v1.md",
        "docs/preregistration/public_package_files_v1.txt",
        "ndp50_assignment_distribution.py",
        "ndp50_assignment_roster.py",
        "ndp50_human_assignments.py",
        "ndp50_preregistration_package.py",
        "ndp50_publication_gate.py",
        "templates/ndp50_external_preregistration_receipt_template.json",
    }

    for relative_path in expected_bindings:
        assert sha256(relative_path) in text

    assert "**DRAFT — NOT SUBMITTED OR REGISTERED**" in text
    assert "Registration DOI/immutable receipt: `<UNRESOLVED>`" in text
    assert "Attestation status: `<UNRESOLVED — DRAFT ONLY>`" in text


def test_public_preregistration_draft_does_not_leak_sealed_test_cases():
    text = read_text(
        "docs/preregistration/ndp50_osf_zenodo_preregistration_draft_v1.md"
    )
    selection = json.loads(
        read_text("data/experiments/ndp50_v1/selection.json")
    )
    sealed_cases = [
        case
        for case in selection["selected_datasets"]
        if case["split"] == "test"
    ]

    assert len(sealed_cases) == 25
    for case in sealed_cases:
        assert case["dataset_id"] not in text
        assert case["title"] not in text


def test_ndp50_statistical_plan_matches_machine_readable_primary_analysis():
    design = json.loads(
        read_text(
            "data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json"
        )
    )
    plan = normalized("docs/ndp50_statistical_analysis_plan_v1.md")
    prereg = normalized(
        "docs/preregistration/ndp50_osf_zenodo_preregistration_draft_v1.md"
    )
    analysis = design["analysis"]

    assert analysis["primary_unit"] == "dataset"
    assert analysis["primary_test"]["method"] == (
        "two_sided_paired_sign_flip_on_dataset_level_mean_difference"
    )
    assert analysis["multiplicity"]["method"] == "holm_step_down"
    assert analysis["primary_test"]["exact_max_nonzero_pairs"] == 24
    assert analysis["dataset_bootstrap_repetitions"] == 10_000
    for term in (
        "sign exchangeability",
        "quota-weighted NDP-50",
        "not a distribution-free test of the mean-null",
        "1,000,000 fixed-seed Monte Carlo",
        "10,000-repetition percentile bootstrap",
    ):
        assert term in plan
    assert "sign exchangeability" in prereg
    assert "not prevalence-weighted estimates" in prereg
    legacy = normalized("docs/semantic_blind_inference_protocol_v1.md")
    assert "does not govern the NDP-50 named-arm analysis" in legacy
    power = normalized("docs/ndp50_power_policy_review_guide_v1.md")
    assert "no policy values selected" in power
    assert "before development-only calibration outcomes are inspected" in power
    risks = normalized("docs/ndp50_methodological_risk_register_v1.md")
    for risk_id in range(1, 35):
        assert f"MR{risk_id:02d}" in risks
    assert "no Critical risk remains `open`" in risks
    audit = normalized("docs/ndp50_feedback_implementation_audit_v1.md")
    for feedback_id in range(1, 17):
        assert f"F{feedback_id:02d}" in audit
    for evidence_class in (
        "machine implemented",
        "documented boundary",
        "inactive by design",
        "human/external pending",
    ):
        assert evidence_class in audit
    assert "AUGRC has no frozen machine implementation" in audit


def test_ndp50_scope_provenance_does_not_overstate_collaborator_request():
    provenance = normalized("docs/ndp50_scope_provenance_v1.md")
    amendment = normalized(
        "docs/ndp50_feedback_improvement_amendment_v1.md"
    )
    claims = normalized("docs/semantic_architecture_claim_ledger_v1.md")
    risks = normalized("docs/ndp50_methodological_risk_register_v1.md")

    for boundary in (
        "No accessible message in the audited conversation contained an explicit "
        "Swathi-authored statement equivalent to “run exactly 50 NDP datasets.”",
        "investigator-defined protocol choice",
        "not evidence that 50 is statistically sufficient",
        "must not cite the audited Slack conversation as direct evidence for that exact number",
    ):
        assert boundary in provenance
    assert "investigator-defined protocol choices" in amendment
    assert "CL45" in claims
    assert "MR34" in risks


def test_initial_human_assignment_guide_preserves_execution_boundaries():
    guide = normalized(
        "docs/ndp50_initial_human_assignment_guide_v1.md"
    )

    for assignment_id in (
        "data_governance_review",
        "vocabulary_discovery_a",
        "vocabulary_discovery_b",
        "feedback_response_signoff",
    ):
        assert assignment_id in guide
    for command in (
        "validate-release",
        "validate-review",
        "verify-approved",
        "validate-returns",
    ):
        assert command in guide
    assert "not independent validation" in guide
    assert "does not imply frozen vocabulary" in guide


def test_human_external_gate_ledger_covers_live_machine_state():
    ledger = normalized("docs/ndp50_human_external_gate_ledger_v1.md")
    readiness = json.loads(
        read_text(
            "data/experiments/ndp50_v1/semantic/readiness_report_v1.json"
        )
    )
    handoff = json.loads(
        read_text(
            "data/experiments/ndp50_v1/semantic/human_handoff_v1.json"
        )
    )

    assert len(readiness["blockers"]) == 10
    for blocker in readiness["blockers"]:
        assert f"`{blocker}`" in ledger
    for stage in handoff["stages"]:
        assert f"`{stage['stage_id']}`" in ledger
    for gate_number in range(1, 13):
        assert f"H{gate_number:02d}" in ledger
    for boundary in (
        "not completion evidence",
        "neutral template",
        "test_ready=true",
        "Local public-package validation is not external preregistration",
    ):
        assert boundary in ledger


def test_downstream_replay_commands_can_persist_receipts_and_handoff_lists_them():
    parser_commands = (
        (
            semantic_annotator_calibration.build_parser(),
            ("preflight-design", "validate"),
        ),
        (
            semantic_gold_workflow.build_parser(),
            ("validate-independent", "validate-consensus"),
        ),
        (ndp50_execution_qualification.build_parser(), ("verify",)),
        (ndp50_demonstration_pool.build_parser(), ("verify",)),
        (semantic_power_analysis.build_parser(), ("validate",)),
        (ndp50_test_inference.build_parser(), ("verify",)),
    )
    for parser, commands in parser_commands:
        for command in commands:
            assert "--output" in subcommand_options(parser, command)

    handoff = json.loads(
        read_text(
            "data/experiments/ndp50_v1/semantic/human_handoff_v1.json"
        )
    )
    outputs = {
        stage["stage_id"]: set(stage["required_outputs"])
        for stage in handoff["stages"]
    }
    required_receipts = {
        "source_approval": {
            "source_review_a_validation.json",
            "source_review_b_validation.json",
            "source_consensus_validation.json",
            "source_bundle_approved_manifest_validation.json",
        },
        "annotator_calibration": {
            "annotator_calibration_design_preflight.json",
            "annotator_calibration_summary_validation.json",
        },
        "cpa_screen_and_semantic_gold": {
            "cpa_screen_a_validation.json",
            "cpa_screen_b_validation.json",
            "cpa_consensus_validation.json",
            "semantic_gold_corpus_validation.json",
            "semantic_gold_approval_validation.json",
        },
        "execution_freeze": {
            "execution_implementation_qualification_validation.json",
            "development_demonstration_pool_replay.json",
            "execution_freeze_replay.json",
        },
        "power_freeze": {
            "semantic_power_calibration_statistics_validation.json",
            "completed_power_policy_validation.json",
            "ndp50_power_freeze_replay.json",
        },
        "test_execution": {
            "validator-generated test run receipt and replay",
            "frozen inference replay validation",
        },
    }
    for stage_id, receipts in required_receipts.items():
        assert receipts <= outputs[stage_id]


def test_publication_governance_is_machine_enforced_before_test_release():
    readiness = normalized("ndp50_readiness.py")
    release = normalized("ndp50_test_execution.py")
    amendment = normalized("docs/ndp50_feedback_improvement_amendment_v1.md")

    for gate in (
        "feedback_response_collaborator_signoff_complete",
        "external_preregistration_verified",
    ):
        assert gate in readiness
        assert gate in release
    assert "publication gate is executable rather than advisory" in amendment
    assert "Neither artifact authorizes test release by itself" in amendment


def test_feedback_registration_and_test_release_are_non_circular_stages():
    handoff = json.loads(
        read_text(
            "data/experiments/ndp50_v1/semantic/human_handoff_v1.json"
        )
    )
    release = json.loads(
        read_text(
            "data/experiments/ndp50_v1/semantic/human_assignments_v1/"
            "assignment_release_v1.json"
        )
    )
    stage_ids = [item["stage_id"] for item in handoff["stages"]]

    assert len(stage_ids) == 11
    assert stage_ids.index("feedback_response_signoff") < stage_ids.index(
        "external_preregistration"
    )
    assert stage_ids.index("external_preregistration") < stage_ids.index(
        "test_release_authorization"
    )
    assert "feedback_response_signoff" in handoff["current_release"][
        "released_stage_ids"
    ]
    assert "feedback_response_signoff" in release["assignments"]
    feedback = json.loads(
        read_text(
            "data/experiments/ndp50_v1/semantic/human_assignments_v1/"
            "feedback_response_signoff_assignment.json"
        )
    )
    assert feedback["reviewer_contract"]["project_collaborator"] is True
    assert feedback["reviewer_contract"]["independent_reviewer"] is False
    assert feedback["review_contract"]["test_release_authorized_by_signoff"] is False


def test_annotator_calibration_is_a_machine_enforced_pre_gold_gate():
    readiness = json.loads(
        read_text(
            "data/experiments/ndp50_v1/semantic/readiness_report_v1.json"
        )
    )
    handoff = json.loads(
        read_text(
            "data/experiments/ndp50_v1/semantic/human_handoff_v1.json"
        )
    )
    plan = normalized("docs/ndp50_annotation_and_independence_plan_v1.md")

    assert readiness["gates"]["annotator_calibration_passed"] is False
    assert readiness["gates"][
        "gold_annotator_identity_matches_calibration"
    ] is False
    assert readiness["gates"]["independent_gold_complete"] is False
    stage_ids = [item["stage_id"] for item in handoff["stages"]]
    assert stage_ids.index("annotator_calibration") < stage_ids.index(
        "cpa_screen_and_semantic_gold"
    )
    calibration = next(
        item
        for item in handoff["stages"]
        if item["stage_id"] == "annotator_calibration"
    )
    assert calibration["status"] == "locked"
    assert "annotator_calibration_summary.json" in calibration[
        "required_outputs"
    ]
    for term in (
        "exact final handbook and NDP vocabulary hashes",
        "valid pre-submission registration receipt",
        "exact two-person annotator-ID match",
        "Swathi",
    ):
        assert term in plan
