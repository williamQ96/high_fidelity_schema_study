from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_cpa_design import (
    registered_analysis_contract,
    registered_metric_contract,
)
from high_fidelity_schema_study.ndp50_test_execution import (
    CASE_MANIFEST_SCHEMA_VERSION,
    DEVIATION_SCHEMA_VERSION,
    GOLD_ARTIFACT_SCHEMA_VERSION,
    PARSED_OUTPUT_SCHEMA_VERSION,
    REPLAY_ARM,
    RELEASE_AUTHORIZATION_SCHEMA_VERSION,
    RUN_MANIFEST_SCHEMA_VERSION,
    RUN_RECORD_SCHEMA_VERSION,
    SCORE_ARTIFACT_SCHEMA_VERSION,
    NDPTestExecutionError,
    ZERO_SHOT_ARM,
    build_missingness_report,
    build_run_receipt,
    build_test_release_receipt,
    build_workflow_spec,
    build_execution_schedule_request,
    derive_sensitivity_conditions,
    verify_test_release_receipt,
    verify_run_receipt,
)
from high_fidelity_schema_study.ndp50_execution_qualification import (
    IMPLEMENTATION_SLOTS,
    build_qualification_receipt,
    interface_version,
    reference_registered_case_score,
    reference_registered_execution_schedule,
)
from high_fidelity_schema_study.ndp50_test_inference import (
    build_inference_result,
    sign_flip_test,
    verify_inference_result,
)


ARMS = [
    "deterministic_only",
    "zero_shot_dataset_level",
    REPLAY_ARM,
    "one_shot_development_similarity_selected",
    "five_shot_development_similarity_selected",
]


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, dict):
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    else:
        text = str(payload)
    path.write_text(text, encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(path: Path, root: Path) -> dict[str, str]:
    return {
        "file": path.relative_to(root).as_posix(),
        "sha256": _sha(path),
    }


def _record_times(sequence: int) -> tuple[str, str]:
    base = datetime(2026, 8, 2, tzinfo=timezone.utc)
    started = base + timedelta(seconds=(sequence - 1) * 2)
    completed = started + timedelta(seconds=1)
    return (
        started.isoformat().replace("+00:00", "Z"),
        completed.isoformat().replace("+00:00", "Z"),
    )


def _fixture(tmp_path: Path) -> dict:
    root = tmp_path / "ndp50"
    selection_path = root / "selection.json"
    selected = [
        *[
            {"dataset_id": f"dev-{index}", "split": "development"}
            for index in range(1, 16)
        ],
        *[
            {"dataset_id": f"val-{index}", "split": "validation"}
            for index in range(1, 11)
        ],
        *[
            {"dataset_id": f"test-{index}", "split": "test"}
            for index in range(1, 26)
        ],
    ]
    _write(selection_path, {"selected_datasets": selected})
    design_path = root / "semantic" / "cpa-design.json"
    _write(
        design_path,
        {
            "schema_version": "ndp50-cpa-design/v1",
            "analysis": registered_analysis_contract(),
            "metric_contract": registered_metric_contract(),
        },
    )
    execution_workflow_path = (
        root / "semantic" / "execution-freeze-workflow.json"
    )
    _write(
        execution_workflow_path,
        {
            "schema_version": "ndp50-execution-freeze-workflow/v1",
            "status": (
                "implementation_ready_waiting_on_upstream_human_gates"
            ),
            "implementation_qualification_required": True,
            "maximum_prompt_sensitivity_variants": 4,
            "required_row_samplers": [
                "head",
                "fixed_seed_stratified",
            ],
        },
    )
    power_workflow_path = (
        root / "semantic" / "power-freeze-workflow.json"
    )
    _write(
        power_workflow_path,
        {
            "schema_version": "ndp50-power-freeze-workflow/v1",
            "status": "implementation_ready_waiting_on_execution_freeze",
        },
    )
    workflow_path = root / "semantic" / "test-execution-workflow.json"
    _write(
        workflow_path,
        build_workflow_spec(
            selection_path=selection_path,
            cpa_design_path=design_path,
            execution_freeze_workflow_path=execution_workflow_path,
            power_freeze_workflow_path=power_workflow_path,
            study_root=root,
        ),
    )
    component_path = root / "semantic" / "qualified-components.py"
    _write(
        component_path,
        "from high_fidelity_schema_study.ndp50_execution_qualification "
        "import reference_probe_response\n\n"
        "def ndp50_qualification_probe(request):\n"
        "    return reference_probe_response(request)\n",
    )
    declaration_path = (
        root / "semantic" / "execution-implementation-declaration.json"
    )
    implementations = {
        slot: {
            "artifact": _ref(component_path, root),
            "entrypoint": "ndp50_qualification_probe",
            "interface_version": interface_version(slot),
        }
        for slot in IMPLEMENTATION_SLOTS
    }
    _write(
        declaration_path,
        {
            "schema_version": (
                "ndp50-execution-implementation-declaration/v1"
            ),
            "status": "complete_pending_qualification",
            "synthetic_probes_only": True,
            "development_validation_or_test_data_used": False,
            "implementations": implementations,
            "completion_attestation": True,
        },
    )
    qualification_receipt_path = (
        root / "semantic" / "execution-qualification-receipt.json"
    )
    _write(
        qualification_receipt_path,
        build_qualification_receipt(
            declaration_path=declaration_path,
            study_root=root,
        ),
    )
    primary_prompt_path = root / "semantic" / "primary-prompt.txt"
    alternative_prompt_path = (
        root / "semantic" / "alternative-prompt.txt"
    )
    _write(primary_prompt_path, "primary prompt")
    _write(alternative_prompt_path, "alternative prompt")
    primary_factors = {
        "task_description_variant": "explicit_cpa",
        "instruction_variant": "bounded_steps",
        "classification_wording": "relationships",
    }
    prompt_contracts = [
        {
            "arm_id": ZERO_SHOT_ARM,
            "prompt": _ref(primary_prompt_path, root),
            "paper_factorization": primary_factors,
        }
    ]
    prompt_sensitivity_contracts = [
        {
            "variant_id": "primary-relationships",
            "prompt": _ref(primary_prompt_path, root),
            "paper_factorization": primary_factors,
            "analysis_role": "descriptive_sensitivity_only",
            "is_primary": True,
        },
        {
            "variant_id": "alternative-classify",
            "prompt": _ref(alternative_prompt_path, root),
            "paper_factorization": {
                **primary_factors,
                "classification_wording": "classify",
            },
            "analysis_role": "descriptive_sensitivity_only",
            "is_primary": False,
        },
    ]
    row_sampling_contract = {
        "primary_sampler_id": "head",
        "sensitivity_samplers": [
            {
                "sampler_id": "head",
                "implementation": _ref(component_path, root),
                "seed": None,
                "parameters": {"row_count": 5},
            },
            {
                "sampler_id": "fixed_seed_stratified",
                "implementation": _ref(component_path, root),
                "seed": 1729,
                "parameters": {"row_count": 5},
            },
        ],
    }
    execution_freeze_path = (
        root / "semantic" / "execution-freeze.json"
    )
    _write(
        execution_freeze_path,
        {
            "schema_version": "ndp50-execution-freeze/v1",
            "status": "frozen_ready_for_power_calibration",
            "config": {
                "planned_arms": ARMS,
                "prompt_contracts": prompt_contracts,
                "prompt_sensitivity_contracts": (
                    prompt_sensitivity_contracts
                ),
                "row_sampling_contract": row_sampling_contract,
                "execution_implementations": implementations,
                "execution_qualification": {
                    "declaration": _ref(declaration_path, root),
                    "receipt": _ref(qualification_receipt_path, root),
                },
                "execution_order": {
                    "case_order_policy": "fixed_seed_hash_rank",
                    "case_order_seed": 99173,
                    "arm_interleaving_policy": (
                        "case_major_seeded_cyclic_execution_blocks"
                    ),
                    "arm_order_seed": 37,
                    "maximum_attempts_per_call": 2,
                },
            },
            "derived_gates": {"prompt_and_backend_frozen": True},
        },
    )
    power_freeze_path = root / "semantic" / "power-freeze.json"
    _write(
        power_freeze_path,
        {
            "schema_version": "ndp50-power-freeze/v1",
            "status": "frozen_before_test_semantic_execution",
            "derived_gates": {"test_power_plan_frozen": True},
            "power_calculation": {
                "planning_scenario": {
                    "contrasts": {
                        "deterministic-vs-zero": {
                            "required_opportunity_dataset_count": 1,
                        },
                        "zero-vs-verified": {
                            "required_opportunity_dataset_count": 1,
                        },
                    }
                }
            },
        },
    )
    readiness_path = root / "semantic" / "release-readiness.json"
    _write(
        readiness_path,
        {
            "implementation": {
                "file": "ndp50_readiness.py",
                "sha256": _sha(
                    Path(__file__).resolve().parents[1]
                    / "ndp50_readiness.py"
                ),
            },
            "integrity_status": "passed",
            "readiness_status": "ready",
            "test_ready": True,
            "semantic_execution_ready": True,
            "gates": {
                key: True
                for key in (
                    "structural_validation_complete",
                    "test_split_unopened",
                    "semantic_preparation_integrity",
                    "neutral_packets_ready",
                    "vocabulary_frozen",
                    "source_bundles_annotation_ready",
                    "cpa_applicability_consensus_complete",
                    "independent_gold_complete",
                    "data_governance_policy_frozen",
                    "prompt_and_backend_frozen",
                    "test_power_plan_frozen",
                    "test_design_meets_pretest_assurance",
                    "test_execution_workflow_ready",
                )
            },
            "blockers": [],
            "artifact_hashes": {
                "selection": _sha(selection_path),
                "test_execution_workflow": _sha(workflow_path),
                "execution_freeze": _sha(execution_freeze_path),
                "power_freeze": _sha(power_freeze_path),
            },
        },
    )
    authorization_path = (
        root / "semantic" / "test-release-authorization.json"
    )
    _write(
        authorization_path,
        {
            "schema_version": RELEASE_AUTHORIZATION_SCHEMA_VERSION,
            "status": "completed_authorized_pending_validator_receipt",
            "human_decisions_present": True,
            "release_decision": (
                "authorize_once_for_frozen_test_execution"
            ),
            "release_readiness": _ref(readiness_path, root),
            "selection": _ref(selection_path, root),
            "workflow": _ref(workflow_path, root),
            "execution_freeze": _ref(execution_freeze_path, root),
            "power_freeze": _ref(power_freeze_path, root),
            "test_outcomes_observed": False,
            "readiness_review_attested": True,
            "test_split_unopened_attested": True,
            "post_outcome_change_forbidden_attested": True,
            "signatories": {
                "study_operator": {
                    "reviewer_id": "operator-1",
                    "reviewer_role": "study_operator",
                    "qualification_summary": "qualified study operator",
                    "conflict_of_interest_declared": False,
                    "developer_participation": True,
                    "signed_at": "2026-07-31T00:00:00Z",
                },
                "independent_release_monitor": {
                    "reviewer_id": "monitor-1",
                    "reviewer_role": "independent_release_monitor",
                    "qualification_summary": (
                        "independent statistical methods reviewer"
                    ),
                    "conflict_of_interest_declared": False,
                    "developer_participation": False,
                    "signed_at": "2026-07-31T01:00:00Z",
                },
            },
            "authorized_at": "2026-08-01T00:00:00Z",
            "completion_attestation": True,
        },
    )
    release_receipt_path = (
        root / "semantic" / "test-release-receipt.json"
    )
    release_kwargs = {
        "authorization_path": authorization_path,
        "release_readiness_path": readiness_path,
        "selection_path": selection_path,
        "workflow_path": workflow_path,
        "execution_freeze_path": execution_freeze_path,
        "power_freeze_path": power_freeze_path,
        "study_root": root,
    }
    _write(
        release_receipt_path,
        build_test_release_receipt(**release_kwargs),
    )
    gold_a = root / "semantic" / "test-gold-a.json"
    gold_b = root / "semantic" / "test-gold-b.json"
    gold_slots = [
        *[
            {
                "slot_id": f"slot-{index}",
                "label_id": "label-a",
                "gold_state": "applicable_known",
                "gold_value": f"value-{index}",
            }
            for index in range(1, 5)
        ],
        {
            "slot_id": "slot-5",
            "label_id": "label-a",
            "gold_state": "applicable_unknown_or_oov",
            "gold_value": None,
        },
    ]
    _write(
        gold_a,
        {
            "schema_version": GOLD_ARTIFACT_SCHEMA_VERSION,
            "case_id": "case-test-1",
            "dataset_id": "test-1",
            "slots": gold_slots,
            "completion_attestation": True,
        },
    )
    _write(
        gold_b,
        {
            "schema_version": GOLD_ARTIFACT_SCHEMA_VERSION,
            "case_id": "case-test-2",
            "dataset_id": "test-2",
            "slots": gold_slots,
            "completion_attestation": True,
        },
    )
    cases = [
        {
            "case_id": "case-test-1",
            "dataset_id": "test-1",
            "split": "test",
            "cpa_applicable": True,
            "gold_artifact": _ref(gold_a, root),
        },
        {
            "case_id": "case-test-2",
            "dataset_id": "test-2",
            "split": "test",
            "cpa_applicable": False,
            "gold_artifact": _ref(gold_b, root),
        },
    ]
    datasets = []
    for index in range(1, 26):
        dataset_id = f"test-{index}"
        if index <= 2:
            datasets.append(
                {
                    "dataset_id": dataset_id,
                    "disposition": "included_with_cases",
                    "case_ids": [f"case-test-{index}"],
                    "reasons": [],
                }
            )
        else:
            datasets.append(
                {
                    "dataset_id": dataset_id,
                    "disposition": "no_semantic_opportunity",
                    "case_ids": [],
                    "reasons": ["no_registered_semantic_opportunity"],
                }
            )
    case_manifest_path = root / "semantic" / "test-case-manifest.json"
    _write(
        case_manifest_path,
        {
            "schema_version": CASE_MANIFEST_SCHEMA_VERSION,
            "status": "frozen_after_authorized_test_opening",
            "authorized_test_opening": True,
            "test_outcomes_used_for_case_selection": False,
            "selection": _ref(selection_path, root),
            "release_readiness": _ref(readiness_path, root),
            "test_release_receipt": _ref(
                release_receipt_path, root
            ),
            "opening_event": {
                "opened_at": "2026-08-01T01:00:00Z",
                "opened_by_operator_id": "operator-1",
                "witnessed_by_monitor_id": "monitor-1",
                "test_outcomes_observed_before_case_freeze": False,
            },
            "frozen_at": "2026-08-01T02:00:00Z",
            "dataset_count": 25,
            "case_count": len(cases),
            "datasets": datasets,
            "cases": cases,
            "completion_attestation": True,
        },
    )
    deviation_path = root / "semantic" / "test-deviations.json"
    _write(
        deviation_path,
        {
            "schema_version": DEVIATION_SCHEMA_VERSION,
            "status": "complete_no_deviations",
            "selection": _ref(selection_path, root),
            "execution_freeze": _ref(execution_freeze_path, root),
            "power_freeze": _ref(power_freeze_path, root),
            "protocol_or_analysis_changed_after_outcome": False,
            "post_outcome_case_addition_or_deletion": False,
            "entries": [],
            "completion_attestation": True,
        },
    )
    record_entries = []
    execution_freeze = json.loads(
        execution_freeze_path.read_text(encoding="utf-8")
    )
    sensitivity_conditions = derive_sensitivity_conditions(
        execution_freeze["config"]
    )
    schedule_request = build_execution_schedule_request(
        execution_config=execution_freeze["config"],
        case_ids=[case["case_id"] for case in cases],
        sensitivity_conditions=sensitivity_conditions,
    )
    schedule = reference_registered_execution_schedule(
        schedule_request
    )["schedule"]
    sequence_by_pair = {
        (item["case_id"], item["arm_id"]): item["execution_sequence"]
        for item in schedule
    }
    zero_response_by_case: dict[str, Path] = {}
    for case in cases:
        for arm in ARMS:
            sequence = sequence_by_pair[(case["case_id"], arm)]
            started_at, completed_at = _record_times(sequence)
            model_call = arm not in {
                "deterministic_only",
                REPLAY_ARM,
            }
            record_id = f"record-{sequence}"
            correct_by_arm = {
                "deterministic_only": 1,
                "zero_shot_dataset_level": 3,
                REPLAY_ARM: 3,
                "one_shot_development_similarity_selected": 2,
                "five_shot_development_similarity_selected": 4,
            }
            correct = correct_by_arm[arm]
            prediction_slots = []
            for index in range(1, 5):
                if index <= correct:
                    prediction_slots.append(
                        {
                            "slot_id": f"slot-{index}",
                            "prediction_state": "accepted_known",
                            "prediction_value": f"value-{index}",
                            "verified": True,
                            "support_valid": True,
                            "evidence_reference_valid": True,
                        }
                    )
                elif index == correct + 1:
                    prediction_slots.append(
                        {
                            "slot_id": f"slot-{index}",
                            "prediction_state": "accepted_known",
                            "prediction_value": "wrong-value",
                            "verified": False,
                            "support_valid": False,
                            "evidence_reference_valid": False,
                        }
                    )
                else:
                    prediction_slots.append(
                        {
                            "slot_id": f"slot-{index}",
                            "prediction_state": (
                                "explicit_oov_or_abstention"
                            ),
                            "prediction_value": None,
                            "verified": False,
                            "support_valid": False,
                            "evidence_reference_valid": False,
                        }
                    )
            prediction_slots.append(
                {
                    "slot_id": "slot-5",
                    "prediction_state": "explicit_oov_or_abstention",
                    "prediction_value": None,
                    "verified": False,
                    "support_valid": False,
                    "evidence_reference_valid": False,
                }
            )
            response_path: Path | None
            if arm == "deterministic_only":
                response_path = None
            elif arm == REPLAY_ARM:
                response_path = zero_response_by_case[case["case_id"]]
            else:
                response_path = (
                    root
                    / "semantic"
                    / "test-responses"
                    / f"{record_id}.json"
                )
                _write(response_path, {"slots": prediction_slots})
                if arm == "zero_shot_dataset_level":
                    zero_response_by_case[case["case_id"]] = response_path
            response = _sha(response_path) if response_path else None
            response_artifact = (
                _ref(response_path, root) if response_path else None
            )
            parsed_output = {
                "schema_version": PARSED_OUTPUT_SCHEMA_VERSION,
                "case_id": case["case_id"],
                "dataset_id": case["dataset_id"],
                "arm_id": arm,
                "record_status": "completed",
                "slots": prediction_slots,
                "completion_attestation": True,
            }
            parsed_path = (
                root
                / "semantic"
                / "test-parsed"
                / f"{record_id}.json"
            )
            _write(parsed_path, parsed_output)
            replayed_counts = reference_registered_case_score(
                {
                    "interface_version": interface_version("scorer"),
                    "operation": "score_registered_case",
                    "case_id": case["case_id"],
                    "dataset_id": case["dataset_id"],
                    "arm_id": arm,
                    "record_status": "completed",
                    "gold": {"slots": gold_slots},
                    "prediction": {"slots": prediction_slots},
                }
            )
            score = {
                "schema_version": SCORE_ARTIFACT_SCHEMA_VERSION,
                "case_id": case["case_id"],
                "dataset_id": case["dataset_id"],
                "arm_id": arm,
                "record_status": "completed",
                **replayed_counts,
                "resource_usage": {
                    "physical_model_calls": 1 if model_call else 0,
                    "input_tokens": 10 if model_call else 0,
                    "output_tokens": 5 if model_call else 0,
                    "latency_seconds": 0.25 if model_call else 0,
                    "cost_usd": 0.001 if model_call else 0,
                },
                "completion_attestation": True,
            }
            score_path = (
                root / "semantic" / "test-scores" / f"{record_id}.json"
            )
            _write(score_path, score)
            record = {
                "schema_version": RUN_RECORD_SCHEMA_VERSION,
                "record_id": record_id,
                "case_id": case["case_id"],
                "dataset_id": case["dataset_id"],
                "arm_id": arm,
                "status": "completed",
                "execution_sequence": sequence,
                "started_at": started_at,
                "completed_at": completed_at,
                "attempt_count": 1 if model_call else 0,
                "physical_model_calls": 1 if model_call else 0,
                "response_sha256": response,
                "response_artifact": response_artifact,
                "parsed_output_sha256": _sha(parsed_path),
                "parsed_output_artifact": _ref(parsed_path, root),
                "score_sha256": _sha(score_path),
                "score_artifact": _ref(score_path, root),
                "failure_code": None,
                "completion_attestation": True,
            }
            record_path = (
                root / "semantic" / "test-records" / f"{record_id}.json"
            )
            _write(record_path, record)
            record_entries.append(
                {
                    "record_id": record_id,
                    "case_id": case["case_id"],
                    "dataset_id": case["dataset_id"],
                    "arm_id": arm,
                    "status": "completed",
                    "execution_sequence": sequence,
                    "artifact": _ref(record_path, root),
                }
            )
    sensitivity_record_entries = []
    for case in cases:
        for condition in sensitivity_conditions:
            condition_id = condition["condition_id"]
            sequence = sequence_by_pair[
                (case["case_id"], condition_id)
            ]
            started_at, completed_at = _record_times(sequence)
            record_id = f"sensitivity-record-{sequence}"
            correct = (
                2
                if condition["changed_factor"] == "prompt_variant"
                else 4
            )
            prediction_slots = []
            for index in range(1, 5):
                if index <= correct:
                    prediction_slots.append(
                        {
                            "slot_id": f"slot-{index}",
                            "prediction_state": "accepted_known",
                            "prediction_value": f"value-{index}",
                            "verified": True,
                            "support_valid": True,
                            "evidence_reference_valid": True,
                        }
                    )
                elif index == correct + 1:
                    prediction_slots.append(
                        {
                            "slot_id": f"slot-{index}",
                            "prediction_state": "accepted_known",
                            "prediction_value": "wrong-value",
                            "verified": False,
                            "support_valid": False,
                            "evidence_reference_valid": False,
                        }
                    )
                else:
                    prediction_slots.append(
                        {
                            "slot_id": f"slot-{index}",
                            "prediction_state": (
                                "explicit_oov_or_abstention"
                            ),
                            "prediction_value": None,
                            "verified": False,
                            "support_valid": False,
                            "evidence_reference_valid": False,
                        }
                    )
            prediction_slots.append(
                {
                    "slot_id": "slot-5",
                    "prediction_state": "explicit_oov_or_abstention",
                    "prediction_value": None,
                    "verified": False,
                    "support_valid": False,
                    "evidence_reference_valid": False,
                }
            )
            response_path = (
                root
                / "semantic"
                / "test-responses"
                / f"{record_id}.json"
            )
            _write(response_path, {"slots": prediction_slots})
            parsed_path = (
                root
                / "semantic"
                / "test-parsed"
                / f"{record_id}.json"
            )
            _write(
                parsed_path,
                {
                    "schema_version": PARSED_OUTPUT_SCHEMA_VERSION,
                    "case_id": case["case_id"],
                    "dataset_id": case["dataset_id"],
                    "arm_id": condition_id,
                    "record_status": "completed",
                    "slots": prediction_slots,
                    "completion_attestation": True,
                },
            )
            replayed_counts = reference_registered_case_score(
                {
                    "interface_version": interface_version("scorer"),
                    "operation": "score_registered_case",
                    "case_id": case["case_id"],
                    "dataset_id": case["dataset_id"],
                    "arm_id": condition_id,
                    "record_status": "completed",
                    "gold": {"slots": gold_slots},
                    "prediction": {"slots": prediction_slots},
                }
            )
            score_path = (
                root / "semantic" / "test-scores" / f"{record_id}.json"
            )
            _write(
                score_path,
                {
                    "schema_version": SCORE_ARTIFACT_SCHEMA_VERSION,
                    "case_id": case["case_id"],
                    "dataset_id": case["dataset_id"],
                    "arm_id": condition_id,
                    "record_status": "completed",
                    **replayed_counts,
                    "resource_usage": {
                        "physical_model_calls": 1,
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "latency_seconds": 0.25,
                        "cost_usd": 0.001,
                    },
                    "completion_attestation": True,
                },
            )
            record = {
                "schema_version": RUN_RECORD_SCHEMA_VERSION,
                "record_id": record_id,
                "case_id": case["case_id"],
                "dataset_id": case["dataset_id"],
                "arm_id": condition_id,
                "status": "completed",
                "execution_sequence": sequence,
                "started_at": started_at,
                "completed_at": completed_at,
                "attempt_count": 1,
                "physical_model_calls": 1,
                "response_sha256": _sha(response_path),
                "response_artifact": _ref(response_path, root),
                "parsed_output_sha256": _sha(parsed_path),
                "parsed_output_artifact": _ref(parsed_path, root),
                "score_sha256": _sha(score_path),
                "score_artifact": _ref(score_path, root),
                "failure_code": None,
                "completion_attestation": True,
            }
            record_path = (
                root / "semantic" / "test-records" / f"{record_id}.json"
            )
            _write(record_path, record)
            sensitivity_record_entries.append(
                {
                    "record_id": record_id,
                    "case_id": case["case_id"],
                    "dataset_id": case["dataset_id"],
                    "arm_id": condition_id,
                    "status": "completed",
                    "execution_sequence": sequence,
                    "artifact": _ref(record_path, root),
                }
            )
    record_entries.sort(key=lambda item: item["execution_sequence"])
    sensitivity_record_entries.sort(
        key=lambda item: item["execution_sequence"]
    )
    run_path = root / "semantic" / "test-run.json"
    _write(
        run_path,
        {
            "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
            "status": "complete",
            "selection": _ref(selection_path, root),
            "release_readiness": _ref(readiness_path, root),
            "workflow": _ref(workflow_path, root),
            "execution_freeze": _ref(execution_freeze_path, root),
            "power_freeze": _ref(power_freeze_path, root),
            "test_release_authorization": _ref(
                authorization_path, root
            ),
            "test_release_receipt": _ref(
                release_receipt_path, root
            ),
            "test_case_manifest": _ref(case_manifest_path, root),
            "deviation_registry": _ref(deviation_path, root),
            "planned_arms": ARMS,
            "post_outcome_case_addition_or_deletion": False,
            "post_outcome_sensitivity_condition_addition_or_deletion": False,
            "records": record_entries,
            "sensitivity_conditions": sensitivity_conditions,
            "sensitivity_records": sensitivity_record_entries,
            "completion_attestation": True,
        },
    )
    return {
        "root": root,
        "selection_path": selection_path,
        "design_path": design_path,
        "execution_workflow_path": execution_workflow_path,
        "power_workflow_path": power_workflow_path,
        "workflow_path": workflow_path,
        "execution_freeze_path": execution_freeze_path,
        "power_freeze_path": power_freeze_path,
        "readiness_path": readiness_path,
        "authorization_path": authorization_path,
        "release_receipt_path": release_receipt_path,
        "release_kwargs": release_kwargs,
        "case_manifest_path": case_manifest_path,
        "deviation_path": deviation_path,
        "run_path": run_path,
    }


def _receipt_kwargs(inputs: dict) -> dict:
    return {
        "run_manifest_path": inputs["run_path"],
        "selection_path": inputs["selection_path"],
        "release_readiness_path": inputs["readiness_path"],
        "workflow_path": inputs["workflow_path"],
        "execution_freeze_path": inputs["execution_freeze_path"],
        "power_freeze_path": inputs["power_freeze_path"],
        "release_authorization_path": inputs["authorization_path"],
        "release_receipt_path": inputs["release_receipt_path"],
        "case_manifest_path": inputs["case_manifest_path"],
        "deviation_registry_path": inputs["deviation_path"],
        "study_root": inputs["root"],
    }


def test_neutral_workflow_contains_no_test_identities(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    workflow_text = inputs["workflow_path"].read_text(encoding="utf-8")

    assert '"test_dataset_count": 25' in workflow_text
    assert '"test_dataset_identities_included": false' in workflow_text
    assert all(
        f"test-{index}" not in workflow_text for index in range(1, 26)
    )


def test_signed_test_release_receipt_replays(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    receipt = json.loads(
        inputs["release_receipt_path"].read_text(encoding="utf-8")
    )

    replay = verify_test_release_receipt(
        receipt, **inputs["release_kwargs"]
    )

    assert receipt["status"] == "passed_authorized_test_opening"
    assert receipt["distinct_signatories_verified"] is True
    assert replay["status"] == "passed"


def test_same_person_cannot_authorize_and_monitor_release(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    authorization = json.loads(
        inputs["authorization_path"].read_text(encoding="utf-8")
    )
    authorization["signatories"][
        "independent_release_monitor"
    ]["reviewer_id"] = "operator-1"
    _write(inputs["authorization_path"], authorization)

    with pytest.raises(NDPTestExecutionError, match="must be distinct"):
        build_test_release_receipt(**inputs["release_kwargs"])


def test_release_rejects_unmet_pretest_assurance(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    readiness = json.loads(
        inputs["readiness_path"].read_text(encoding="utf-8")
    )
    readiness["gates"]["test_design_meets_pretest_assurance"] = False
    _write(inputs["readiness_path"], readiness)

    with pytest.raises(
        NDPTestExecutionError,
        match="readiness must pass",
    ):
        build_test_release_receipt(**inputs["release_kwargs"])


def test_case_freeze_cannot_predate_release_authorization(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    case_manifest = json.loads(
        inputs["case_manifest_path"].read_text(encoding="utf-8")
    )
    case_manifest["opening_event"][
        "opened_at"
    ] = "2026-07-30T00:00:00Z"
    _write(inputs["case_manifest_path"], case_manifest)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    run["test_case_manifest"] = _ref(
        inputs["case_manifest_path"], inputs["root"]
    )
    _write(inputs["run_path"], run)

    with pytest.raises(NDPTestExecutionError, match="out of order"):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_complete_run_builds_replays_and_reports_missingness(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    kwargs = _receipt_kwargs(inputs)
    receipt = build_run_receipt(**kwargs)
    receipt_path = inputs["root"] / "semantic" / "test-run-receipt.json"
    _write(receipt_path, receipt)

    replay = verify_run_receipt(receipt, **kwargs)
    missingness = build_missingness_report(
        receipt_path=receipt_path,
        **kwargs,
    )

    assert receipt["complete_case_by_arm_matrix"] is True
    assert receipt["complete_case_by_sensitivity_condition_matrix"] is True
    assert receipt["validated_primary_record_count"] == 10
    assert receipt["validated_sensitivity_record_count"] == 4
    assert receipt["validated_record_count"] == 14
    assert receipt["qualified_execution_schedule_verified"] is True
    assert receipt["execution_chronology_verified"] is True
    assert receipt["maximum_sensitivity_physical_calls"] == 8
    assert receipt["observed_sensitivity_physical_calls"] == 4
    assert receipt["sensitivity_physical_call_budget_respected"] is True
    assert receipt["byte_identical_zero_call_replay_verified"] is True
    assert replay["status"] == "passed"
    assert missingness["silent_dataset_deletion"] is False
    assert missingness["silent_case_or_arm_deletion"] is False


def test_incomplete_case_arm_matrix_is_rejected(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    run["records"].pop()
    _write(inputs["run_path"], run)

    with pytest.raises(NDPTestExecutionError, match="complete case-by-arm"):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_incomplete_sensitivity_matrix_is_rejected(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    run["sensitivity_records"].pop()
    _write(inputs["run_path"], run)

    with pytest.raises(
        NDPTestExecutionError,
        match="complete case-by-sensitivity-condition",
    ):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_unregistered_sensitivity_interaction_is_rejected(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    unregistered = dict(run["sensitivity_records"][0])
    unregistered["record_id"] = "unregistered-factorial-interaction"
    unregistered["arm_id"] = "sensitivity_prompt_sampler__unregistered"
    run["sensitivity_records"].append(unregistered)
    _write(inputs["run_path"], run)

    with pytest.raises(
        NDPTestExecutionError,
        match="complete case-by-sensitivity-condition",
    ):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_post_outcome_sensitivity_condition_change_is_rejected(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    run[
        "post_outcome_sensitivity_condition_addition_or_deletion"
    ] = True
    _write(inputs["run_path"], run)

    with pytest.raises(
        NDPTestExecutionError,
        match="post-outcome sensitivity condition",
    ):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_execution_sequence_permutation_is_rejected(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    entries = sorted(
        run["records"] + run["sensitivity_records"],
        key=lambda item: item["execution_sequence"],
    )
    first, second = entries[:2]
    first_path = inputs["root"] / first["artifact"]["file"]
    second_path = inputs["root"] / second["artifact"]["file"]
    first_record = json.loads(first_path.read_text(encoding="utf-8"))
    second_record = json.loads(second_path.read_text(encoding="utf-8"))
    first_sequence = first_record["execution_sequence"]
    second_sequence = second_record["execution_sequence"]
    first_record["execution_sequence"] = second_sequence
    second_record["execution_sequence"] = first_sequence
    first["execution_sequence"] = second_sequence
    second["execution_sequence"] = first_sequence
    _write(first_path, first_record)
    _write(second_path, second_record)
    first["artifact"] = _ref(first_path, inputs["root"])
    second["artifact"] = _ref(second_path, inputs["root"])
    _write(inputs["run_path"], run)

    with pytest.raises(
        NDPTestExecutionError,
        match="qualified frozen schedule",
    ):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_execution_timestamp_overlap_is_rejected(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    entries = sorted(
        run["records"] + run["sensitivity_records"],
        key=lambda item: item["execution_sequence"],
    )
    first, second = entries[:2]
    first_path = inputs["root"] / first["artifact"]["file"]
    second_path = inputs["root"] / second["artifact"]["file"]
    first_record = json.loads(first_path.read_text(encoding="utf-8"))
    second_record = json.loads(second_path.read_text(encoding="utf-8"))
    second_record["started_at"] = first_record["started_at"]
    second_record["completed_at"] = first_record["completed_at"]
    _write(second_path, second_record)
    second["artifact"] = _ref(second_path, inputs["root"])
    _write(inputs["run_path"], run)

    with pytest.raises(
        NDPTestExecutionError,
        match="timestamps overlap",
    ):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_replay_response_substitution_is_rejected(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    replay_entry = next(
        item
        for item in run["records"]
        if item["case_id"] == "case-test-1" and item["arm_id"] == REPLAY_ARM
    )
    record_path = inputs["root"] / replay_entry["artifact"]["file"]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["response_sha256"] = "f" * 64
    _write(record_path, record)
    replay_entry["artifact"] = _ref(record_path, inputs["root"])
    _write(inputs["run_path"], run)

    with pytest.raises(NDPTestExecutionError, match="raw-response hash"):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_silent_dataset_omission_is_rejected(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    case_manifest = json.loads(
        inputs["case_manifest_path"].read_text(encoding="utf-8")
    )
    case_manifest["datasets"].pop()
    _write(inputs["case_manifest_path"], case_manifest)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    run["test_case_manifest"] = _ref(
        inputs["case_manifest_path"], inputs["root"]
    )
    _write(inputs["run_path"], run)

    with pytest.raises(
        NDPTestExecutionError,
        match="every selected test dataset",
    ):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_post_outcome_protocol_change_is_rejected(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    deviations = json.loads(
        inputs["deviation_path"].read_text(encoding="utf-8")
    )
    deviations["protocol_or_analysis_changed_after_outcome"] = True
    _write(inputs["deviation_path"], deviations)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    run["deviation_registry"] = _ref(
        inputs["deviation_path"], inputs["root"]
    )
    _write(inputs["run_path"], run)

    with pytest.raises(NDPTestExecutionError, match="protocol or case"):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_unbound_score_substitution_is_rejected(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    entry = run["records"][0]
    record_path = inputs["root"] / entry["artifact"]["file"]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    score_path = inputs["root"] / record["score_artifact"]["file"]
    score = json.loads(score_path.read_text(encoding="utf-8"))
    score["correct_accepted_claim_count"] = 0
    _write(score_path, score)

    with pytest.raises(NDPTestExecutionError, match="hash mismatch"):
        build_run_receipt(**_receipt_kwargs(inputs))


def _inference_fixture(inputs: dict) -> tuple[Path, Path]:
    kwargs = _receipt_kwargs(inputs)
    receipt = build_run_receipt(**kwargs)
    receipt_path = inputs["root"] / "semantic" / "test-run-receipt.json"
    _write(receipt_path, receipt)
    missingness = build_missingness_report(
        receipt_path=receipt_path,
        **kwargs,
    )
    missingness_path = inputs["root"] / "semantic" / "missingness.json"
    _write(missingness_path, missingness)
    return receipt_path, missingness_path


def _inference_kwargs(
    inputs: dict,
    receipt_path: Path,
    missingness_path: Path,
) -> dict:
    return {
        "receipt_path": receipt_path,
        "missingness_path": missingness_path,
        "cpa_design_path": inputs["design_path"],
        **_receipt_kwargs(inputs),
    }


def test_registered_inference_replays_and_uses_sign_flip_primary(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    receipt_path, missingness_path = _inference_fixture(inputs)
    kwargs = _inference_kwargs(
        inputs, receipt_path, missingness_path
    )
    result = build_inference_result(**kwargs)

    assert result["status"] == "analysable_frozen_requirement_realized"
    assert result["holm_family"]["family_complete"] is True
    assert result["co_primary_contrasts"][
        "deterministic-vs-zero"
    ]["mean_paired_effect"] == 0.5
    assert result["co_primary_contrasts"][
        "zero-vs-verified"
    ]["primary_sign_flip_test"]["method"] == "degenerate_all_zero"
    assert result["claim_scope"]["null_result_establishes_no_effect"] is False
    assert (
        result["claim_scope"][
            "random_vs_similarity_demonstration_selection_estimable"
        ]
        is False
    )
    assert (
        result["claim_scope"][
            "prompt_variant_effect_estimable_from_primary_matrix"
        ]
        is False
    )
    assert (
        result["claim_scope"][
            "cross_domain_transfer_effect_identified"
        ]
        is False
    )
    assert result["primary_publication_reporting_payload_complete"] is True
    assert result["arm_metrics_for_frozen_cpa_population"][
        "zero_shot_dataset_level"
    ]["support_counts"]["applicable_known_slot_count"] == 4
    sensitivity = result["descriptive_sensitivity_results"]
    assert len(sensitivity) == 2
    prompt_result = next(
        item
        for item in sensitivity.values()
        if item["condition"]["changed_factor"] == "prompt_variant"
    )
    sampler_result = next(
        item
        for item in sensitivity.values()
        if item["condition"]["changed_factor"] == "row_sampler"
    )
    assert prompt_result["mean_paired_difference"] == -0.25
    assert sampler_result["mean_paired_difference"] == 0.25
    assert prompt_result["confirmatory_test_performed"] is False
    assert (
        result["claim_scope"][
            "registered_prompt_variant_descriptive_contrasts_available"
        ]
        is True
    )
    assert verify_inference_result(result, **kwargs)["status"] == "passed"


def test_sign_flip_excludes_zeros_from_patterns_but_retains_pairs() -> None:
    result = sign_flip_test(
        [0.5, 0.0, 0.0],
        exact_max_nonzero_pairs=24,
        monte_carlo_repetitions=100,
        seed=1,
    )

    assert result["total_pair_count"] == 3
    assert result["nonzero_pair_count"] == 1
    assert result["repetitions"] == 2


def test_qualified_scorer_replay_rejects_self_consistent_score_forgery(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    entry = next(
        item
        for item in run["records"]
        if item["case_id"] == "case-test-1"
        and item["arm_id"] == "zero_shot_dataset_level"
    )
    record_path = inputs["root"] / entry["artifact"]["file"]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    score_path = inputs["root"] / record["score_artifact"]["file"]
    score = json.loads(score_path.read_text(encoding="utf-8"))
    score["applicable_known_slot_count"] = 5
    score["label_confusion_counts"][0]["fn"] = 2
    score["label_confusion_counts"][0]["gold_support"] = 5
    _write(score_path, score)
    record["score_sha256"] = _sha(score_path)
    record["score_artifact"] = _ref(score_path, inputs["root"])
    _write(record_path, record)
    entry["artifact"] = _ref(record_path, inputs["root"])
    _write(inputs["run_path"], run)

    with pytest.raises(
        NDPTestExecutionError,
        match="qualified scorer replay",
    ):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_qualified_scorer_replay_rejects_parsed_output_substitution(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    entry = run["records"][0]
    record_path = inputs["root"] / entry["artifact"]["file"]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    parsed_path = (
        inputs["root"] / record["parsed_output_artifact"]["file"]
    )
    parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
    parsed["slots"][0]["prediction_value"] = "substituted-value"
    _write(parsed_path, parsed)
    record["parsed_output_sha256"] = _sha(parsed_path)
    record["parsed_output_artifact"] = _ref(
        parsed_path, inputs["root"]
    )
    _write(record_path, record)
    entry["artifact"] = _ref(record_path, inputs["root"])
    _write(inputs["run_path"], run)

    with pytest.raises(
        NDPTestExecutionError,
        match="qualified scorer replay",
    ):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_qualified_parser_replay_rejects_raw_response_substitution(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    entry = next(
        item
        for item in run["records"]
        if item["case_id"] == "case-test-1"
        and item["arm_id"] == "zero_shot_dataset_level"
    )
    record_path = inputs["root"] / entry["artifact"]["file"]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    response_path = inputs["root"] / record["response_artifact"]["file"]
    response = json.loads(response_path.read_text(encoding="utf-8"))
    response["slots"][0]["prediction_value"] = "raw-substitution"
    _write(response_path, response)
    record["response_sha256"] = _sha(response_path)
    record["response_artifact"] = _ref(response_path, inputs["root"])
    _write(record_path, record)
    entry["artifact"] = _ref(record_path, inputs["root"])
    _write(inputs["run_path"], run)

    with pytest.raises(
        NDPTestExecutionError,
        match="qualified response-parser replay",
    ):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_qualified_parser_replay_covers_sensitivity_records(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    entry = run["sensitivity_records"][0]
    record_path = inputs["root"] / entry["artifact"]["file"]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    response_path = inputs["root"] / record["response_artifact"]["file"]
    response = json.loads(response_path.read_text(encoding="utf-8"))
    response["slots"][0]["prediction_value"] = (
        "sensitivity-raw-substitution"
    )
    _write(response_path, response)
    record["response_sha256"] = _sha(response_path)
    record["response_artifact"] = _ref(response_path, inputs["root"])
    _write(record_path, record)
    entry["artifact"] = _ref(record_path, inputs["root"])
    _write(inputs["run_path"], run)

    with pytest.raises(
        NDPTestExecutionError,
        match="qualified response-parser replay",
    ):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_qualified_parser_rejects_coordinated_parsed_and_score_substitution(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    entry = next(
        item
        for item in run["records"]
        if item["case_id"] == "case-test-1"
        and item["arm_id"] == "zero_shot_dataset_level"
    )
    record_path = inputs["root"] / entry["artifact"]["file"]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    parsed_path = (
        inputs["root"] / record["parsed_output_artifact"]["file"]
    )
    parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
    parsed["slots"][0]["prediction_value"] = "coordinated-substitution"
    _write(parsed_path, parsed)

    case_manifest = json.loads(
        inputs["case_manifest_path"].read_text(encoding="utf-8")
    )
    case = next(
        item
        for item in case_manifest["cases"]
        if item["case_id"] == entry["case_id"]
    )
    gold_path = inputs["root"] / case["gold_artifact"]["file"]
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    replayed_counts = reference_registered_case_score(
        {
            "interface_version": interface_version("scorer"),
            "operation": "score_registered_case",
            "case_id": entry["case_id"],
            "dataset_id": entry["dataset_id"],
            "arm_id": entry["arm_id"],
            "record_status": entry["status"],
            "gold": {"slots": gold["slots"]},
            "prediction": {"slots": parsed["slots"]},
        }
    )
    score_path = inputs["root"] / record["score_artifact"]["file"]
    score = json.loads(score_path.read_text(encoding="utf-8"))
    score.update(replayed_counts)
    _write(score_path, score)

    record["parsed_output_sha256"] = _sha(parsed_path)
    record["parsed_output_artifact"] = _ref(
        parsed_path, inputs["root"]
    )
    record["score_sha256"] = _sha(score_path)
    record["score_artifact"] = _ref(score_path, inputs["root"])
    _write(record_path, record)
    entry["artifact"] = _ref(record_path, inputs["root"])
    _write(inputs["run_path"], run)

    with pytest.raises(
        NDPTestExecutionError,
        match="qualified response-parser replay",
    ):
        build_run_receipt(**_receipt_kwargs(inputs))


def test_qualified_scorer_replay_rejects_gold_substitution(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    case_manifest = json.loads(
        inputs["case_manifest_path"].read_text(encoding="utf-8")
    )
    case = next(
        item
        for item in case_manifest["cases"]
        if item["case_id"] == "case-test-1"
    )
    gold_path = inputs["root"] / case["gold_artifact"]["file"]
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    gold["slots"][0]["gold_value"] = "substituted-gold"
    _write(gold_path, gold)
    case["gold_artifact"] = _ref(gold_path, inputs["root"])
    _write(inputs["case_manifest_path"], case_manifest)
    run = json.loads(inputs["run_path"].read_text(encoding="utf-8"))
    run["test_case_manifest"] = _ref(
        inputs["case_manifest_path"], inputs["root"]
    )
    _write(inputs["run_path"], run)

    with pytest.raises(
        NDPTestExecutionError,
        match="qualified scorer replay",
    ):
        build_run_receipt(**_receipt_kwargs(inputs))
