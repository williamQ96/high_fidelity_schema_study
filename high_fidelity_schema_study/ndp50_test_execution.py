from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Mapping

from .ndp50_cpa_design import (
    registered_analysis_contract,
    registered_metric_contract,
)
from .ndp50_execution_qualification import (
    interface_version,
    load_qualified_entrypoint,
)


WORKFLOW_SCHEMA_VERSION = "ndp50-test-execution-workflow/v1"
RELEASE_AUTHORIZATION_SCHEMA_VERSION = (
    "ndp50-test-release-authorization/v1"
)
RELEASE_RECEIPT_SCHEMA_VERSION = "ndp50-test-release-receipt/v1"
RELEASE_REPLAY_SCHEMA_VERSION = "ndp50-test-release-receipt-replay/v1"
CASE_MANIFEST_SCHEMA_VERSION = "ndp50-test-case-manifest/v1"
RUN_MANIFEST_SCHEMA_VERSION = "ndp50-test-run-manifest/v1"
RUN_RECORD_SCHEMA_VERSION = "ndp50-test-run-record/v1"
SCORE_ARTIFACT_SCHEMA_VERSION = "ndp50-test-score/v1"
GOLD_ARTIFACT_SCHEMA_VERSION = "ndp50-test-gold/v1"
PARSED_OUTPUT_SCHEMA_VERSION = "ndp50-test-parsed-output/v1"
DEVIATION_SCHEMA_VERSION = "ndp50-test-deviation-registry/v1"
RECEIPT_SCHEMA_VERSION = "ndp50-test-run-receipt/v1"
REPLAY_SCHEMA_VERSION = "ndp50-test-run-receipt-replay/v1"
MISSINGNESS_SCHEMA_VERSION = "ndp50-test-missingness-report/v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RECORD_STATUSES = {
    "completed",
    "structured_abstention",
    "execution_failure",
}
DATASET_DISPOSITIONS = {
    "included_with_cases",
    "no_semantic_opportunity",
    "acquisition_failure",
    "predeclared_governance_exclusion",
}
DEVIATION_CATEGORIES = {
    "infrastructure",
    "transport",
    "backend",
    "artifact_integrity",
    "operator_error",
}
DEVIATION_DISPOSITIONS = {
    "continue_as_registered",
    "mark_affected_records_missing",
    "terminate_without_protocol_change",
}
DETERMINISTIC_ARM = "deterministic_only"
ZERO_SHOT_ARM = "zero_shot_dataset_level"
REPLAY_ARM = (
    "zero_shot_byte_identical_response_plus_deterministic_verification"
)
MODEL_ARMS = {
    ZERO_SHOT_ARM,
    "one_shot_development_similarity_selected",
    "five_shot_development_similarity_selected",
}
SENSITIVITY_CONDITION_ID_RE = re.compile(
    r"^sensitivity_(prompt|sampler)__[a-z0-9][a-z0-9._-]*$"
)


class NDPTestExecutionError(ValueError):
    pass


def derive_sensitivity_conditions(
    execution_config: Mapping[str, Any],
) -> list[Dict[str, Any]]:
    prompt_contracts = execution_config.get("prompt_contracts")
    prompt_variants = execution_config.get(
        "prompt_sensitivity_contracts"
    )
    row_contract = execution_config.get("row_sampling_contract")
    if (
        not isinstance(prompt_contracts, list)
        or not isinstance(prompt_variants, list)
        or not isinstance(row_contract, dict)
    ):
        raise NDPTestExecutionError(
            "frozen sensitivity contracts are missing"
        )
    zero_contracts = [
        item
        for item in prompt_contracts
        if isinstance(item, dict) and item.get("arm_id") == ZERO_SHOT_ARM
    ]
    primary_variants = [
        item
        for item in prompt_variants
        if isinstance(item, dict) and item.get("is_primary") is True
    ]
    if len(zero_contracts) != 1 or len(primary_variants) != 1:
        raise NDPTestExecutionError(
            "frozen prompt sensitivity anchor is invalid"
        )
    zero_contract = zero_contracts[0]
    primary_variant = primary_variants[0]
    if (
        primary_variant.get("prompt", {}).get("sha256")
        != zero_contract.get("prompt", {}).get("sha256")
        or primary_variant.get("paper_factorization")
        != zero_contract.get("paper_factorization")
    ):
        raise NDPTestExecutionError(
            "frozen prompt sensitivity anchor differs from zero-shot"
        )
    primary_sampler = str(
        row_contract.get("primary_sampler_id") or ""
    )
    samplers = row_contract.get("sensitivity_samplers")
    if not primary_sampler or not isinstance(samplers, list):
        raise NDPTestExecutionError(
            "frozen row-sampler sensitivity anchor is invalid"
        )
    sampler_by_id = {
        str(item.get("sampler_id") or ""): item
        for item in samplers
        if isinstance(item, dict)
    }
    if (
        len(sampler_by_id) != len(samplers)
        or "" in sampler_by_id
        or primary_sampler not in sampler_by_id
    ):
        raise NDPTestExecutionError(
            "frozen row-sampler registry is invalid"
        )
    variant_ids = {
        str(item.get("variant_id") or "")
        for item in prompt_variants
        if isinstance(item, dict)
    }
    if (
        len(variant_ids) != len(prompt_variants)
        or "" in variant_ids
        or any(
            item.get("analysis_role")
            != "descriptive_sensitivity_only"
            or not isinstance(item.get("is_primary"), bool)
            for item in prompt_variants
            if isinstance(item, dict)
        )
    ):
        raise NDPTestExecutionError(
            "frozen prompt sensitivity registry is invalid"
        )
    conditions: list[Dict[str, Any]] = []
    for item in sorted(
        (
            item
            for item in prompt_variants
            if isinstance(item, dict) and item.get("is_primary") is False
        ),
        key=lambda item: str(item["variant_id"]),
    ):
        condition_id = (
            f"sensitivity_prompt__{str(item['variant_id']).lower()}"
        )
        if SENSITIVITY_CONDITION_ID_RE.fullmatch(condition_id) is None:
            raise NDPTestExecutionError(
                "prompt sensitivity variant ID is not execution-safe"
            )
        conditions.append(
            {
                "condition_id": condition_id,
                "changed_factor": "prompt_variant",
                "base_arm_id": ZERO_SHOT_ARM,
                "prompt_variant_id": str(item["variant_id"]),
                "primary_prompt_variant_id": str(
                    primary_variant["variant_id"]
                ),
                "row_sampler_id": primary_sampler,
                "analysis_role": "descriptive_sensitivity_only",
                "single_factor_change": True,
            }
        )
    for sampler_id in sorted(
        value for value in sampler_by_id if value != primary_sampler
    ):
        condition_id = f"sensitivity_sampler__{sampler_id.lower()}"
        if SENSITIVITY_CONDITION_ID_RE.fullmatch(condition_id) is None:
            raise NDPTestExecutionError(
                "row-sampler sensitivity ID is not execution-safe"
            )
        conditions.append(
            {
                "condition_id": condition_id,
                "changed_factor": "row_sampler",
                "base_arm_id": ZERO_SHOT_ARM,
                "prompt_variant_id": str(
                    primary_variant["variant_id"]
                ),
                "primary_prompt_variant_id": str(
                    primary_variant["variant_id"]
                ),
                "row_sampler_id": sampler_id,
                "analysis_role": "descriptive_sensitivity_only",
                "single_factor_change": True,
            }
        )
    if not conditions:
        raise NDPTestExecutionError(
            "at least one non-primary sensitivity condition is required"
        )
    return conditions


def build_execution_blocks(
    planned_arms: Iterable[str],
    sensitivity_conditions: Iterable[Mapping[str, Any]],
) -> list[list[str]]:
    arms = [str(value) for value in planned_arms]
    required = {DETERMINISTIC_ARM, ZERO_SHOT_ARM, REPLAY_ARM}
    if (
        len(arms) != len(set(arms))
        or not required.issubset(set(arms))
    ):
        raise NDPTestExecutionError(
            "planned arms cannot form registered execution blocks"
        )
    condition_ids = sorted(
        str(item.get("condition_id") or "")
        for item in sensitivity_conditions
    )
    if (
        not condition_ids
        or "" in condition_ids
        or len(condition_ids) != len(set(condition_ids))
        or set(condition_ids).intersection(arms)
    ):
        raise NDPTestExecutionError(
            "sensitivity conditions cannot form registered execution blocks"
        )
    blocks = [
        [ZERO_SHOT_ARM, REPLAY_ARM],
        [DETERMINISTIC_ARM],
    ]
    blocks.extend(
        [arm_id]
        for arm_id in arms
        if arm_id not in required
    )
    blocks.extend([condition_id] for condition_id in condition_ids)
    return blocks


def build_execution_schedule_request(
    *,
    execution_config: Mapping[str, Any],
    case_ids: Iterable[str],
    sensitivity_conditions: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:
    order = execution_config.get("execution_order")
    arms = execution_config.get("planned_arms")
    if not isinstance(order, dict) or not isinstance(arms, list):
        raise NDPTestExecutionError(
            "frozen execution ordering contract is missing"
        )
    return {
        "interface_version": interface_version("runner"),
        "operation": "plan_registered_execution",
        "case_ids": [str(value) for value in case_ids],
        "case_order_policy": order.get("case_order_policy"),
        "case_order_seed": order.get("case_order_seed"),
        "arm_interleaving_policy": order.get(
            "arm_interleaving_policy"
        ),
        "arm_order_seed": order.get("arm_order_seed"),
        "execution_blocks": build_execution_blocks(
            arms, sensitivity_conditions
        ),
    }


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise NDPTestExecutionError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_canonical(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _study_relative(path: Path, study_root: Path) -> str:
    try:
        return path.resolve().relative_to(study_root.resolve()).as_posix()
    except ValueError as exc:
        raise NDPTestExecutionError(
            f"artifact must be inside the study root: {path}"
        ) from exc


def _binding(path: Path, study_root: Path) -> Dict[str, str]:
    if not path.is_file():
        raise NDPTestExecutionError(f"artifact does not exist: {path}")
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
        raise NDPTestExecutionError(f"{label} binding is missing")
    value = ref.get("file")
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise NDPTestExecutionError(
            f"{label} must use a study-relative file"
        )
    root = study_root.resolve()
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise NDPTestExecutionError(f"{label} escapes the study root") from exc
    if not path.is_file():
        raise NDPTestExecutionError(f"{label} does not exist")
    if _sha256_file(path) != ref.get("sha256"):
        raise NDPTestExecutionError(f"{label} hash mismatch")
    return path


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _parse_timestamp(value: Any, label: str) -> datetime:
    if not _valid_timestamp(value):
        raise NDPTestExecutionError(f"{label} timestamp is invalid")
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _selection(path: Path) -> tuple[Dict[str, Any], list[str]]:
    selection = _load_json(path)
    selected = selection.get("selected_datasets")
    if not isinstance(selected, list):
        raise NDPTestExecutionError("selection has no selected datasets")
    split_counts = Counter(str(item.get("split") or "") for item in selected)
    if split_counts != {
        "development": 15,
        "validation": 10,
        "test": 25,
    }:
        raise NDPTestExecutionError(
            "test workflow requires the frozen 15/10/25 selection"
        )
    test_ids = [
        str(item.get("dataset_id") or "")
        for item in selected
        if item.get("split") == "test"
    ]
    if (
        len(test_ids) != 25
        or any(not value for value in test_ids)
        or len(test_ids) != len(set(test_ids))
    ):
        raise NDPTestExecutionError("test dataset identities are invalid")
    return selection, test_ids


def build_workflow_spec(
    *,
    selection_path: Path,
    cpa_design_path: Path,
    execution_freeze_workflow_path: Path,
    power_freeze_workflow_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    _, test_ids = _selection(selection_path)
    design = _load_json(cpa_design_path)
    execution = _load_json(execution_freeze_workflow_path)
    power = _load_json(power_freeze_workflow_path)
    if (
        design.get("schema_version") != "ndp50-cpa-design/v1"
        or design.get("analysis") != registered_analysis_contract()
        or design.get("metric_contract") != registered_metric_contract()
    ):
        raise NDPTestExecutionError("CPA design contract is incompatible")
    if (
        execution.get("schema_version")
        != "ndp50-execution-freeze-workflow/v1"
        or execution.get("status")
        != "implementation_ready_waiting_on_upstream_human_gates"
        or execution.get("implementation_qualification_required") is not True
    ):
        raise NDPTestExecutionError(
            "execution-freeze workflow is incompatible"
        )
    maximum_prompt_variants = execution.get(
        "maximum_prompt_sensitivity_variants"
    )
    required_row_samplers = execution.get("required_row_samplers")
    if (
        not isinstance(maximum_prompt_variants, int)
        or isinstance(maximum_prompt_variants, bool)
        or maximum_prompt_variants < 2
        or not isinstance(required_row_samplers, list)
        or len(required_row_samplers) < 2
    ):
        raise NDPTestExecutionError(
            "execution-freeze sensitivity bounds are incompatible"
        )
    maximum_sensitivity_conditions = (
        maximum_prompt_variants - 1
        + len(required_row_samplers) - 1
    )
    if (
        power.get("schema_version") != "ndp50-power-freeze-workflow/v1"
        or power.get("status")
        != "implementation_ready_waiting_on_execution_freeze"
    ):
        raise NDPTestExecutionError("power-freeze workflow is incompatible")
    implementation = Path(__file__).resolve()
    return {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "status": "implementation_ready_waiting_on_test_release",
        "human_decisions_present": False,
        "test_outcomes_observed": False,
        "test_dataset_identities_included": False,
        "test_dataset_count": len(test_ids),
        "selection": _binding(selection_path, study_root),
        "cpa_design": _binding(cpa_design_path, study_root),
        "execution_freeze_workflow": _binding(
            execution_freeze_workflow_path, study_root
        ),
        "power_freeze_workflow": _binding(
            power_freeze_workflow_path, study_root
        ),
        "required_upstream_gates": [
            "readiness.integrity_status=passed",
            "readiness.test_ready=true",
            "execution_freeze.derived_gates.prompt_and_backend_frozen=true",
            "power_freeze.derived_gates.test_power_plan_frozen=true",
        ],
        "required_artifact_schemas": {
            "test_release_authorization": (
                RELEASE_AUTHORIZATION_SCHEMA_VERSION
            ),
            "test_release_receipt": RELEASE_RECEIPT_SCHEMA_VERSION,
            "test_case_manifest": CASE_MANIFEST_SCHEMA_VERSION,
            "test_run_manifest": RUN_MANIFEST_SCHEMA_VERSION,
            "test_run_record": RUN_RECORD_SCHEMA_VERSION,
            "test_gold": GOLD_ARTIFACT_SCHEMA_VERSION,
            "test_parsed_output": PARSED_OUTPUT_SCHEMA_VERSION,
            "test_score": SCORE_ARTIFACT_SCHEMA_VERSION,
            "deviation_registry": DEVIATION_SCHEMA_VERSION,
            "test_run_receipt": RECEIPT_SCHEMA_VERSION,
            "missingness_report": MISSINGNESS_SCHEMA_VERSION,
            "test_inference": "ndp50-test-inference/v1",
            "test_inference_replay": "ndp50-test-inference-replay/v1",
        },
        "dataset_disposition_policy": {
            "every_selected_test_dataset_required_exactly_once": True,
            "allowed_dispositions": sorted(DATASET_DISPOSITIONS),
            "silent_dataset_deletion_forbidden": True,
        },
        "execution_matrix_policy": {
            "every_frozen_case_x_every_registered_arm_required": True,
            "allowed_record_statuses": sorted(RECORD_STATUSES),
            "failure_and_abstention_retained_in_denominators": True,
            "unique_contiguous_execution_sequence_required": True,
            "qualified_runner_schedule_replay_required": True,
            "record_timestamps_must_follow_schedule_without_overlap": True,
            "zero_shot_and_replay_must_share_an_ordered_execution_block": True,
            "record_artifact_hash_and_identity_replay_required": True,
            "raw_response_artifact_binding_required_when_response_exists": True,
            "qualified_parser_actual_response_replay_required": True,
            "parsed_output_artifact_binding_required": True,
            "score_artifact_hash_identity_and_count_validation_required": True,
            "qualified_scorer_actual_case_replay_required": True,
        },
        "descriptive_sensitivity_execution_policy": {
            "anchor_arm": ZERO_SHOT_ARM,
            "every_frozen_case_x_every_derived_condition_required": True,
            "prompt_conditions": (
                "every frozen non-primary prompt variant with the primary row sampler"
            ),
            "row_sampler_conditions": (
                "every frozen non-primary row sampler with the primary prompt variant"
            ),
            "single_factor_at_a_time": True,
            "unregistered_factorial_interactions_forbidden": True,
            "post_outcome_condition_addition_or_deletion_forbidden": True,
            "analysis_role": "descriptive_sensitivity_only",
            "confirmatory_p_values_or_claims_forbidden": True,
            "maximum_prompt_variant_count": maximum_prompt_variants,
            "registered_row_sampler_count": len(required_row_samplers),
            "maximum_derived_condition_count": (
                maximum_sensitivity_conditions
            ),
            "physical_call_budget": (
                "frozen_case_count_x_derived_condition_count_x_"
                "maximum_attempts_per_call"
            ),
        },
        "response_reuse_policy": {
            "source_arm": ZERO_SHOT_ARM,
            "consumer_arm": REPLAY_ARM,
            "response_sha256_must_match": True,
            "consumer_physical_model_calls": 0,
        },
        "deviation_policy": {
            "registry_required_even_when_empty": True,
            "protocol_or_analysis_change_after_outcome_forbidden": True,
            "affected_record_ids_required": True,
            "nonempty_entries_require_independent_review": True,
        },
        "publication_reporting_contract": {
            "dataset_flow_and_all_dispositions_required": True,
            "case_arm_missingness_and_failure_codes_required": True,
            "co_primary_effects_intervals_raw_and_holm_p_values_required": True,
            "metric_numerators_denominators_and_undefined_counts_required": True,
            "cost_latency_calls_and_tokens_required": True,
            "prompt_sampler_and_few_shot_results_labeled_descriptive": True,
            "unexecuted_sensitivity_or_transfer_effects_must_be_reported_as_not_estimable": True,
            "underpowered_or_nonalysable_status_cannot_be_reworded_as_no_effect": True,
            "deviations_and_protocol_version_required": True,
            "registered_inference_replay_required": True,
        },
        "sequence": [
            "snapshot_passing_test_release_readiness",
            "obtain_distinct_operator_and_independent_monitor_signatures",
            "validator_generate_and_replay_test_release_receipt",
            "authorize_and_log_test_opening",
            "freeze_complete_test_case_manifest_and_dataset_dispositions",
            "execute_exact_case_by_arm_matrix",
            "execute_exact_case_by_derived_sensitivity_condition_matrix",
            "write_content_addressed_record_for_every_matrix_cell",
            "complete_deviation_registry_without_analysis_changes",
            "validator_generate_test_run_receipt",
            "validator_generate_missingness_report",
            "execute_frozen_inference_and_publication_reporting",
            "validator_replay_frozen_inference",
        ],
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            name: _sha256_file(implementation.with_name(name))
            for name in (
                "ndp50_cpa_design.py",
                "ndp50_execution_freeze.py",
                "ndp50_execution_qualification.py",
                "ndp50_power_freeze.py",
                "ndp50_test_inference.py",
            )
        },
    }


def _validate_release_readiness(
    readiness: Mapping[str, Any],
    *,
    readiness_path: Path,
    selection_path: Path,
    workflow_path: Path,
    execution_freeze_path: Path,
    power_freeze_path: Path,
) -> None:
    required_gates = (
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
    gates = readiness.get("gates")
    if (
        readiness.get("integrity_status") != "passed"
        or readiness.get("readiness_status") != "ready"
        or readiness.get("test_ready") is not True
        or readiness.get("semantic_execution_ready") is not True
        or not isinstance(gates, dict)
        or any(gates.get(key) is not True for key in required_gates)
        or readiness.get("blockers") != []
    ):
        raise NDPTestExecutionError(
            "test release readiness must pass before test opening"
        )
    hashes = readiness.get("artifact_hashes") or {}
    for key, path in (
        ("selection", selection_path),
        ("test_execution_workflow", workflow_path),
        ("execution_freeze", execution_freeze_path),
        ("power_freeze", power_freeze_path),
    ):
        if hashes.get(key) != _sha256_file(path):
            raise NDPTestExecutionError(
                f"release readiness {key} hash mismatch"
            )
    readiness_implementation = Path(__file__).with_name(
        "ndp50_readiness.py"
    )
    if readiness.get("implementation") != {
        "file": readiness_implementation.name,
        "sha256": _sha256_file(readiness_implementation),
    }:
        raise NDPTestExecutionError(
            "release readiness implementation binding is stale"
        )
    if not readiness_path.is_file():
        raise NDPTestExecutionError("release readiness artifact is missing")


def build_test_release_receipt(
    *,
    authorization_path: Path,
    release_readiness_path: Path,
    selection_path: Path,
    workflow_path: Path,
    execution_freeze_path: Path,
    power_freeze_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    authorization = _load_json(authorization_path)
    readiness = _load_json(release_readiness_path)
    _validate_release_readiness(
        readiness,
        readiness_path=release_readiness_path,
        selection_path=selection_path,
        workflow_path=workflow_path,
        execution_freeze_path=execution_freeze_path,
        power_freeze_path=power_freeze_path,
    )
    if (
        authorization.get("schema_version")
        != RELEASE_AUTHORIZATION_SCHEMA_VERSION
        or authorization.get("status")
        != "completed_authorized_pending_validator_receipt"
        or authorization.get("human_decisions_present") is not True
        or authorization.get("release_decision")
        != "authorize_once_for_frozen_test_execution"
        or authorization.get("test_outcomes_observed") is not False
        or authorization.get("readiness_review_attested") is not True
        or authorization.get("test_split_unopened_attested") is not True
        or authorization.get(
            "post_outcome_change_forbidden_attested"
        )
        is not True
        or authorization.get("completion_attestation") is not True
    ):
        raise NDPTestExecutionError(
            "test release authorization is incomplete"
        )
    expected_bindings = {
        "release_readiness": _binding(
            release_readiness_path, study_root
        ),
        "selection": _binding(selection_path, study_root),
        "workflow": _binding(workflow_path, study_root),
        "execution_freeze": _binding(execution_freeze_path, study_root),
        "power_freeze": _binding(power_freeze_path, study_root),
    }
    for key, expected in expected_bindings.items():
        if authorization.get(key) != expected:
            raise NDPTestExecutionError(
                f"test release authorization {key} binding changed"
            )
    signatories = authorization.get("signatories")
    if not isinstance(signatories, dict) or set(signatories) != {
        "study_operator",
        "independent_release_monitor",
    }:
        raise NDPTestExecutionError(
            "test release requires exactly two signatory roles"
        )
    identities: Dict[str, str] = {}
    signed_times: list[datetime] = []
    for role, item in signatories.items():
        if not isinstance(item, dict):
            raise NDPTestExecutionError(
                "test release signatory is malformed"
            )
        reviewer_id = str(item.get("reviewer_id") or "").strip()
        qualification = str(
            item.get("qualification_summary") or ""
        ).strip()
        if (
            not reviewer_id
            or "replace-with" in reviewer_id.casefold()
            or not qualification
            or item.get("reviewer_role") != role
            or item.get("conflict_of_interest_declared") is not False
            or not isinstance(item.get("developer_participation"), bool)
        ):
            raise NDPTestExecutionError(
                "test release signatory qualification is invalid"
            )
        if (
            role == "independent_release_monitor"
            and item["developer_participation"] is not False
        ):
            raise NDPTestExecutionError(
                "independent release monitor must be a non-developer"
            )
        identities[role] = reviewer_id
        signed_times.append(
            _parse_timestamp(item.get("signed_at"), f"{role} signed_at")
        )
    if len(set(identities.values())) != 2:
        raise NDPTestExecutionError(
            "test release signatories must be distinct"
        )
    authorized_at = _parse_timestamp(
        authorization.get("authorized_at"), "authorized_at"
    )
    if authorized_at < max(signed_times):
        raise NDPTestExecutionError(
            "test release cannot precede either signature"
        )
    implementation = Path(__file__).resolve()
    return {
        "schema_version": RELEASE_RECEIPT_SCHEMA_VERSION,
        "status": "passed_authorized_test_opening",
        "authorization": _binding(authorization_path, study_root),
        "source_artifacts": expected_bindings,
        "authorized_at": str(authorization["authorized_at"]),
        "study_operator_id": identities["study_operator"],
        "independent_release_monitor_id": identities[
            "independent_release_monitor"
        ],
        "distinct_signatories_verified": True,
        "independent_non_developer_monitor_verified": True,
        "test_split_unopened_at_bound_readiness": True,
        "test_outcomes_observed_before_authorization": False,
        "single_frozen_protocol_release": True,
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
    }


def verify_test_release_receipt(
    receipt: Mapping[str, Any],
    **kwargs: Any,
) -> Dict[str, Any]:
    try:
        expected = build_test_release_receipt(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": RELEASE_REPLAY_SCHEMA_VERSION,
            "status": "failed",
            "detail": str(exc),
            "differing_top_level_keys": [],
        }
    differing = sorted(
        key
        for key in set(expected) | set(receipt)
        if expected.get(key) != receipt.get(key)
    )
    return {
        "schema_version": RELEASE_REPLAY_SCHEMA_VERSION,
        "status": "passed" if not differing else "failed",
        "detail": None,
        "differing_top_level_keys": differing,
    }


def _validate_case_manifest(
    payload: Mapping[str, Any],
    *,
    selection_path: Path,
    readiness_path: Path,
    release_receipt_path: Path,
    release_receipt: Mapping[str, Any],
    study_root: Path,
) -> tuple[
    list[Dict[str, Any]],
    Dict[str, Dict[str, Any]],
    datetime,
]:
    _, test_ids = _selection(selection_path)
    if payload.get("schema_version") != CASE_MANIFEST_SCHEMA_VERSION:
        raise NDPTestExecutionError("unexpected test case manifest schema")
    if payload.get("status") != "frozen_after_authorized_test_opening":
        raise NDPTestExecutionError("test case manifest is not frozen")
    if payload.get("authorized_test_opening") is not True:
        raise NDPTestExecutionError("test opening was not authorized")
    if payload.get("test_outcomes_used_for_case_selection") is not False:
        raise NDPTestExecutionError(
            "test outcomes cannot select test cases"
        )
    if payload.get("selection") != _binding(selection_path, study_root):
        raise NDPTestExecutionError(
            "test case manifest selection binding changed"
        )
    if payload.get("release_readiness") != _binding(
        readiness_path, study_root
    ):
        raise NDPTestExecutionError(
            "test case manifest readiness binding changed"
        )
    if (
        release_receipt.get("schema_version")
        != RELEASE_RECEIPT_SCHEMA_VERSION
        or release_receipt.get("status")
        != "passed_authorized_test_opening"
        or payload.get("test_release_receipt")
        != _binding(release_receipt_path, study_root)
    ):
        raise NDPTestExecutionError(
            "test case manifest release receipt binding changed"
        )
    opening = payload.get("opening_event")
    if (
        not isinstance(opening, dict)
        or opening.get("opened_by_operator_id")
        != release_receipt.get("study_operator_id")
        or opening.get("witnessed_by_monitor_id")
        != release_receipt.get("independent_release_monitor_id")
        or opening.get("test_outcomes_observed_before_case_freeze")
        is not False
    ):
        raise NDPTestExecutionError(
            "test case manifest opening event is invalid"
        )
    opened_at = _parse_timestamp(
        opening.get("opened_at"), "test opened_at"
    )
    authorized_at = _parse_timestamp(
        release_receipt.get("authorized_at"), "release authorized_at"
    )
    frozen_at = _parse_timestamp(
        payload.get("frozen_at"), "test case manifest frozen_at"
    )
    if opened_at < authorized_at or frozen_at < opened_at:
        raise NDPTestExecutionError(
            "test opening and case-freeze timestamps are out of order"
        )
    datasets = payload.get("datasets")
    if not isinstance(datasets, list) or len(datasets) != len(test_ids):
        raise NDPTestExecutionError(
            "every selected test dataset must have one disposition"
        )
    dataset_by_id: Dict[str, Dict[str, Any]] = {}
    for item in datasets:
        if not isinstance(item, dict):
            raise NDPTestExecutionError("dataset disposition is malformed")
        dataset_id = str(item.get("dataset_id") or "")
        if dataset_id in dataset_by_id:
            raise NDPTestExecutionError("duplicate dataset disposition")
        if item.get("disposition") not in DATASET_DISPOSITIONS:
            raise NDPTestExecutionError("dataset disposition is invalid")
        case_ids = item.get("case_ids")
        if not isinstance(case_ids, list) or len(case_ids) != len(
            set(case_ids)
        ):
            raise NDPTestExecutionError("dataset case IDs are invalid")
        reasons = item.get("reasons")
        if not isinstance(reasons, list):
            raise NDPTestExecutionError("dataset reasons must be a list")
        if item["disposition"] == "included_with_cases":
            if not case_ids or reasons:
                raise NDPTestExecutionError(
                    "included dataset requires cases and no exclusion reason"
                )
        elif case_ids or not reasons:
            raise NDPTestExecutionError(
                "nonincluded dataset requires reasons and no cases"
            )
        dataset_by_id[dataset_id] = item
    if set(dataset_by_id) != set(test_ids):
        raise NDPTestExecutionError(
            "dataset dispositions differ from frozen test selection"
        )
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise NDPTestExecutionError("test cases must be a list")
    case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise NDPTestExecutionError("test case is malformed")
        case_id = str(case.get("case_id") or "")
        dataset_id = str(case.get("dataset_id") or "")
        if (
            not case_id
            or case_id in case_ids
            or dataset_id not in dataset_by_id
            or case.get("split") != "test"
            or not isinstance(case.get("cpa_applicable"), bool)
        ):
            raise NDPTestExecutionError("test case identity is invalid")
        _bound_path(
            case.get("gold_artifact"),
            study_root=study_root,
            label=f"test gold for {case_id}",
        )
        if (
            dataset_by_id[dataset_id]["disposition"]
            != "included_with_cases"
            or case_id not in dataset_by_id[dataset_id]["case_ids"]
        ):
            raise NDPTestExecutionError(
                "test case is not declared by its dataset disposition"
            )
        case_ids.add(case_id)
    declared_case_ids = {
        str(case_id)
        for item in datasets
        for case_id in item.get("case_ids") or []
    }
    if case_ids != declared_case_ids:
        raise NDPTestExecutionError(
            "dataset dispositions and case manifest differ"
        )
    if payload.get("case_count") != len(cases):
        raise NDPTestExecutionError("test case count mismatch")
    if payload.get("completion_attestation") is not True:
        raise NDPTestExecutionError(
            "test case manifest completion is not attested"
        )
    return list(cases), dataset_by_id, frozen_at


def _validate_deviations(
    payload: Mapping[str, Any],
    *,
    selection_path: Path,
    execution_freeze_path: Path,
    power_freeze_path: Path,
    record_ids: set[str],
    study_root: Path,
) -> list[Dict[str, Any]]:
    if payload.get("schema_version") != DEVIATION_SCHEMA_VERSION:
        raise NDPTestExecutionError("unexpected deviation registry schema")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise NDPTestExecutionError("deviation entries must be a list")
    expected_status = (
        "complete_no_deviations"
        if not entries
        else "complete_with_documented_deviations"
    )
    if payload.get("status") != expected_status:
        raise NDPTestExecutionError("deviation registry status mismatch")
    if (
        payload.get("protocol_or_analysis_changed_after_outcome") is not False
        or payload.get("post_outcome_case_addition_or_deletion") is not False
    ):
        raise NDPTestExecutionError(
            "post-outcome protocol or case changes are forbidden"
        )
    expected_bindings = {
        "selection": _binding(selection_path, study_root),
        "execution_freeze": _binding(execution_freeze_path, study_root),
        "power_freeze": _binding(power_freeze_path, study_root),
    }
    for key, expected in expected_bindings.items():
        if payload.get(key) != expected:
            raise NDPTestExecutionError(
                f"deviation registry {key} binding changed"
            )
    seen: set[str] = set()
    for item in entries:
        if not isinstance(item, dict):
            raise NDPTestExecutionError("deviation entry is malformed")
        deviation_id = str(item.get("deviation_id") or "")
        affected = item.get("affected_record_ids")
        if (
            not deviation_id
            or deviation_id in seen
            or not _valid_timestamp(item.get("detected_at"))
            or item.get("category") not in DEVIATION_CATEGORIES
            or not str(item.get("description") or "").strip()
            or item.get("disposition") not in DEVIATION_DISPOSITIONS
            or item.get("analysis_impact")
            != "none_registered_missingness_only"
            or not isinstance(affected, list)
            or not affected
            or not set(str(value) for value in affected).issubset(record_ids)
            or not str(item.get("reviewer_id") or "").strip()
            or item.get("reviewer_role")
            not in {
                "independent_methods_reviewer",
                "research_compliance_reviewer",
            }
            or item.get("conflict_of_interest_declared") is not False
            or item.get("developer_participation") is not False
        ):
            raise NDPTestExecutionError("deviation entry is invalid")
        seen.add(deviation_id)
    if payload.get("completion_attestation") is not True:
        raise NDPTestExecutionError(
            "deviation registry completion is not attested"
        )
    return list(entries)


def _record_projection(record: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        key: record.get(key)
        for key in (
            "record_id",
            "case_id",
            "dataset_id",
            "arm_id",
            "status",
            "execution_sequence",
        )
    }


def _validate_record(
    payload: Mapping[str, Any],
    *,
    case: Mapping[str, Any],
    arm_id: str,
    maximum_attempts: int,
    study_root: Path,
    not_before: datetime,
    execution_mode: str,
    response_parser: Any,
    scorer: Any,
) -> None:
    if execution_mode not in {"deterministic", "model", "replay"}:
        raise NDPTestExecutionError("test record execution mode is invalid")
    if payload.get("schema_version") != RUN_RECORD_SCHEMA_VERSION:
        raise NDPTestExecutionError("unexpected test run record schema")
    if (
        payload.get("case_id") != case["case_id"]
        or payload.get("dataset_id") != case["dataset_id"]
        or payload.get("arm_id") != arm_id
        or payload.get("status") not in RECORD_STATUSES
    ):
        raise NDPTestExecutionError("test run record identity is invalid")
    if (
        not str(payload.get("record_id") or "").strip()
        or not isinstance(payload.get("execution_sequence"), int)
        or isinstance(payload.get("execution_sequence"), bool)
        or payload["execution_sequence"] <= 0
        or not _valid_timestamp(payload.get("started_at"))
        or not _valid_timestamp(payload.get("completed_at"))
    ):
        raise NDPTestExecutionError("test run record metadata is invalid")
    started_at = _parse_timestamp(
        payload.get("started_at"), "test record started_at"
    )
    completed_at = _parse_timestamp(
        payload.get("completed_at"), "test record completed_at"
    )
    if started_at < not_before or completed_at < started_at:
        raise NDPTestExecutionError(
            "test record timestamps precede case freeze or are out of order"
        )
    attempts = payload.get("attempt_count")
    calls = payload.get("physical_model_calls")
    if (
        not isinstance(attempts, int)
        or isinstance(attempts, bool)
        or not 0 <= attempts <= maximum_attempts
        or not isinstance(calls, int)
        or isinstance(calls, bool)
        or not 0 <= calls <= attempts
    ):
        raise NDPTestExecutionError("test run attempt accounting is invalid")
    if execution_mode in {"deterministic", "replay"} and (
        attempts != 0 or calls != 0
    ):
        raise NDPTestExecutionError(
            "deterministic and replay arms cannot make model calls"
        )
    if execution_mode == "model" and payload["status"] != "execution_failure":
        if attempts < 1 or calls < 1:
            raise NDPTestExecutionError(
                "completed model arm must record a physical call"
            )
    for key in ("parsed_output_sha256", "score_sha256"):
        if not _is_sha256(payload.get(key)):
            raise NDPTestExecutionError(
                f"test run record {key} is invalid"
            )
    response = payload.get("response_sha256")
    response_artifact = payload.get("response_artifact")
    response_text: str | None = None
    if execution_mode == "deterministic":
        if response is not None or response_artifact is not None:
            raise NDPTestExecutionError(
                "deterministic arm cannot contain a model response artifact"
            )
    elif payload["status"] == "execution_failure":
        if response is not None and not _is_sha256(response):
            raise NDPTestExecutionError(
                "failed record response hash is invalid"
            )
        if (response is None) != (response_artifact is None):
            raise NDPTestExecutionError(
                "failed record response hash and artifact must coexist"
            )
    elif not _is_sha256(response):
        raise NDPTestExecutionError("model response hash is invalid")
    if response is not None:
        response_path = _bound_path(
            response_artifact,
            study_root=study_root,
            label=f"raw response {case['case_id']}/{arm_id}",
        )
        if response != _sha256_file(response_path):
            raise NDPTestExecutionError(
                "raw-response hash and artifact binding differ"
            )
        try:
            response_text = response_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise NDPTestExecutionError(
                "raw response artifact is not valid UTF-8"
            ) from exc
    failure_code = payload.get("failure_code")
    if payload["status"] == "execution_failure":
        if not str(failure_code or "").strip():
            raise NDPTestExecutionError(
                "execution failure requires a failure code"
            )
    elif failure_code is not None:
        raise NDPTestExecutionError(
            "nonfailure record cannot contain a failure code"
        )
    if payload.get("completion_attestation") is not True:
        raise NDPTestExecutionError(
            "test run record completion is not attested"
        )
    parsed_path = _bound_path(
        payload.get("parsed_output_artifact"),
        study_root=study_root,
        label=f"parsed output {case['case_id']}/{arm_id}",
    )
    if payload["parsed_output_sha256"] != _sha256_file(parsed_path):
        raise NDPTestExecutionError(
            "parsed-output hash and artifact binding differ"
        )
    parsed_output = _load_json(parsed_path)
    if (
        parsed_output.get("schema_version")
        != PARSED_OUTPUT_SCHEMA_VERSION
        or parsed_output.get("case_id") != case["case_id"]
        or parsed_output.get("dataset_id") != case["dataset_id"]
        or parsed_output.get("arm_id") != arm_id
        or parsed_output.get("record_status") != payload["status"]
        or not isinstance(parsed_output.get("slots"), list)
        or parsed_output.get("completion_attestation") is not True
    ):
        raise NDPTestExecutionError(
            "parsed-output artifact identity is invalid"
        )
    if (
        execution_mode != "deterministic"
        and payload["status"] != "execution_failure"
    ):
        parsing_request = {
            "interface_version": interface_version("response_parser"),
            "operation": "parse_registered_response",
            "case_id": case["case_id"],
            "dataset_id": case["dataset_id"],
            "arm_id": arm_id,
            "response_text": response_text,
        }
        try:
            replayed_parse = response_parser(deepcopy(parsing_request))
        except Exception as exc:  # noqa: BLE001
            raise NDPTestExecutionError(
                f"qualified response-parser replay failed: {exc}"
            ) from exc
        if (
            not isinstance(replayed_parse, dict)
            or replayed_parse.get("parse_status") != "parsed"
            or replayed_parse.get("slots") != parsed_output["slots"]
        ):
            raise NDPTestExecutionError(
                "parsed output differs from qualified response-parser replay"
            )
    gold_path = _bound_path(
        case.get("gold_artifact"),
        study_root=study_root,
        label=f"test gold for {case['case_id']}",
    )
    gold = _load_json(gold_path)
    if (
        gold.get("schema_version") != GOLD_ARTIFACT_SCHEMA_VERSION
        or gold.get("case_id") != case["case_id"]
        or gold.get("dataset_id") != case["dataset_id"]
        or not isinstance(gold.get("slots"), list)
        or gold.get("completion_attestation") is not True
    ):
        raise NDPTestExecutionError("test gold artifact is invalid")
    score_path = _bound_path(
        payload.get("score_artifact"),
        study_root=study_root,
        label=f"test score {case['case_id']}/{arm_id}",
    )
    if payload["score_sha256"] != _sha256_file(score_path):
        raise NDPTestExecutionError(
            "test run score hash and artifact binding differ"
        )
    score = _load_json(score_path)
    if (
        score.get("schema_version") != SCORE_ARTIFACT_SCHEMA_VERSION
        or score.get("case_id") != case["case_id"]
        or score.get("dataset_id") != case["dataset_id"]
        or score.get("arm_id") != arm_id
        or score.get("record_status") != payload["status"]
        or score.get("completion_attestation") is not True
    ):
        raise NDPTestExecutionError("test score identity is invalid")
    count_keys = (
        "applicable_known_slot_count",
        "applicable_unknown_or_oov_slot_count",
        "correct_accepted_claim_count",
        "accepted_known_claim_count",
        "incorrect_accepted_known_claim_count",
        "unsupported_accepted_claim_count",
        "valid_evidence_reference_claim_count",
        "verified_correct_accepted_claim_count",
    )
    if any(
        not isinstance(score.get(key), int)
        or isinstance(score.get(key), bool)
        or score[key] < 0
        for key in count_keys
    ):
        raise NDPTestExecutionError("test score counts are invalid")
    known = score["applicable_known_slot_count"]
    correct = score["correct_accepted_claim_count"]
    accepted = score["accepted_known_claim_count"]
    incorrect = score["incorrect_accepted_known_claim_count"]
    if (
        correct > known
        or correct > accepted
        or accepted != correct + incorrect
        or score["unsupported_accepted_claim_count"] > accepted
        or score["valid_evidence_reference_claim_count"] > accepted
        or score["verified_correct_accepted_claim_count"] > correct
    ):
        raise NDPTestExecutionError(
            "test score count relationships are invalid"
        )
    labels = score.get("label_confusion_counts")
    if not isinstance(labels, list):
        raise NDPTestExecutionError(
            "test score label confusion counts are required"
        )
    label_ids: set[str] = set()
    for item in labels:
        if not isinstance(item, dict):
            raise NDPTestExecutionError(
                "test score label confusion entry is invalid"
            )
        label_id = str(item.get("label_id") or "")
        counts = [item.get(key) for key in ("tp", "fp", "fn")]
        if (
            not label_id
            or label_id in label_ids
            or any(
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
                for value in counts
            )
            or item.get("gold_support") != counts[0] + counts[2]
            or item.get("prediction_support") != counts[0] + counts[1]
        ):
            raise NDPTestExecutionError(
                "test score label confusion entry is invalid"
            )
        label_ids.add(label_id)
    if (
        sum(int(item["tp"]) for item in labels) != correct
        or sum(int(item["gold_support"]) for item in labels) != known
        or sum(int(item["prediction_support"]) for item in labels)
        != accepted
    ):
        raise NDPTestExecutionError(
            "test score confusion counts do not reconcile"
        )
    scoring_request = {
        "interface_version": interface_version("scorer"),
        "operation": "score_registered_case",
        "case_id": case["case_id"],
        "dataset_id": case["dataset_id"],
        "arm_id": arm_id,
        "record_status": payload["status"],
        "gold": {"slots": gold["slots"]},
        "prediction": {"slots": parsed_output["slots"]},
    }
    try:
        replayed_score = scorer(deepcopy(scoring_request))
    except Exception as exc:  # noqa: BLE001
        raise NDPTestExecutionError(
            f"qualified scorer replay failed: {exc}"
        ) from exc
    observed_score = {
        key: score[key] for key in (*count_keys, "label_confusion_counts")
    }
    if replayed_score != observed_score:
        raise NDPTestExecutionError(
            "test score differs from qualified scorer replay"
        )
    usage = score.get("resource_usage")
    if not isinstance(usage, dict):
        raise NDPTestExecutionError("test score resource usage is required")
    for key in (
        "physical_model_calls",
        "input_tokens",
        "output_tokens",
    ):
        if (
            not isinstance(usage.get(key), int)
            or isinstance(usage.get(key), bool)
            or usage[key] < 0
        ):
            raise NDPTestExecutionError(
                "test score integer resource usage is invalid"
            )
    for key in ("latency_seconds", "cost_usd"):
        value = usage.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or float(value) < 0
        ):
            raise NDPTestExecutionError(
                "test score numeric resource usage is invalid"
            )
    if usage["physical_model_calls"] != calls:
        raise NDPTestExecutionError(
            "test score and record model-call counts differ"
        )
    if payload["status"] in {
        "structured_abstention",
        "execution_failure",
    } and any(
        score[key] != 0
        for key in (
            "correct_accepted_claim_count",
            "accepted_known_claim_count",
            "incorrect_accepted_known_claim_count",
            "unsupported_accepted_claim_count",
            "valid_evidence_reference_claim_count",
            "verified_correct_accepted_claim_count",
        )
    ):
        raise NDPTestExecutionError(
            "failure or abstention cannot contain accepted claims"
        )


def build_run_receipt(
    *,
    run_manifest_path: Path,
    selection_path: Path,
    release_readiness_path: Path,
    workflow_path: Path,
    execution_freeze_path: Path,
    power_freeze_path: Path,
    release_authorization_path: Path,
    release_receipt_path: Path,
    case_manifest_path: Path,
    deviation_registry_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    run = _load_json(run_manifest_path)
    readiness = _load_json(release_readiness_path)
    workflow = _load_json(workflow_path)
    execution = _load_json(execution_freeze_path)
    power = _load_json(power_freeze_path)
    release_receipt = _load_json(release_receipt_path)
    case_manifest = _load_json(case_manifest_path)
    deviations = _load_json(deviation_registry_path)
    _validate_release_readiness(
        readiness,
        readiness_path=release_readiness_path,
        selection_path=selection_path,
        workflow_path=workflow_path,
        execution_freeze_path=execution_freeze_path,
        power_freeze_path=power_freeze_path,
    )
    release_replay = verify_test_release_receipt(
        release_receipt,
        authorization_path=release_authorization_path,
        release_readiness_path=release_readiness_path,
        selection_path=selection_path,
        workflow_path=workflow_path,
        execution_freeze_path=execution_freeze_path,
        power_freeze_path=power_freeze_path,
        study_root=study_root,
    )
    if release_replay["status"] != "passed":
        raise NDPTestExecutionError(
            "test release receipt does not replay"
        )
    if workflow.get("selection") != _binding(selection_path, study_root):
        raise NDPTestExecutionError(
            "test execution workflow selection binding changed"
        )
    design_path = _bound_path(
        workflow.get("cpa_design"),
        study_root=study_root,
        label="test workflow CPA design",
    )
    execution_workflow_path = _bound_path(
        workflow.get("execution_freeze_workflow"),
        study_root=study_root,
        label="test workflow execution-freeze workflow",
    )
    power_workflow_path = _bound_path(
        workflow.get("power_freeze_workflow"),
        study_root=study_root,
        label="test workflow power-freeze workflow",
    )
    expected_workflow = build_workflow_spec(
        selection_path=selection_path,
        cpa_design_path=design_path,
        execution_freeze_workflow_path=execution_workflow_path,
        power_freeze_workflow_path=power_workflow_path,
        study_root=study_root,
    )
    if workflow != expected_workflow:
        raise NDPTestExecutionError(
            "test execution workflow is not the canonical workflow"
        )
    if (
        execution.get("schema_version") != "ndp50-execution-freeze/v1"
        or execution.get("status") != "frozen_ready_for_power_calibration"
        or execution.get("derived_gates", {}).get(
            "prompt_and_backend_frozen"
        )
        is not True
    ):
        raise NDPTestExecutionError("execution freeze is invalid")
    if (
        power.get("schema_version") != "ndp50-power-freeze/v1"
        or power.get("status") != "frozen_before_test_semantic_execution"
        or power.get("derived_gates", {}).get("test_power_plan_frozen")
        is not True
    ):
        raise NDPTestExecutionError("power freeze is invalid")
    try:
        runner = load_qualified_entrypoint(
            execution,
            slot="runner",
            study_root=study_root,
        )
        response_parser = load_qualified_entrypoint(
            execution,
            slot="response_parser",
            study_root=study_root,
        )
        scorer = load_qualified_entrypoint(
            execution,
            slot="scorer",
            study_root=study_root,
        )
    except Exception as exc:  # noqa: BLE001
        raise NDPTestExecutionError(
            f"qualified runner, parser, or scorer is unavailable: {exc}"
        ) from exc
    cases, dataset_by_id, case_frozen_at = _validate_case_manifest(
        case_manifest,
        selection_path=selection_path,
        readiness_path=release_readiness_path,
        release_receipt_path=release_receipt_path,
        release_receipt=release_receipt,
        study_root=study_root,
    )
    if run.get("schema_version") != RUN_MANIFEST_SCHEMA_VERSION:
        raise NDPTestExecutionError("unexpected test run manifest schema")
    if run.get("status") != "complete":
        raise NDPTestExecutionError("test run manifest is incomplete")
    if run.get("post_outcome_case_addition_or_deletion") is not False:
        raise NDPTestExecutionError(
            "post-outcome case addition or deletion is forbidden"
        )
    if (
        run.get(
            "post_outcome_sensitivity_condition_addition_or_deletion"
        )
        is not False
    ):
        raise NDPTestExecutionError(
            "post-outcome sensitivity condition addition or deletion is forbidden"
        )
    expected_bindings = {
        "selection": _binding(selection_path, study_root),
        "release_readiness": _binding(
            release_readiness_path, study_root
        ),
        "workflow": _binding(workflow_path, study_root),
        "execution_freeze": _binding(execution_freeze_path, study_root),
        "power_freeze": _binding(power_freeze_path, study_root),
        "test_release_authorization": _binding(
            release_authorization_path, study_root
        ),
        "test_release_receipt": _binding(
            release_receipt_path, study_root
        ),
        "test_case_manifest": _binding(case_manifest_path, study_root),
        "deviation_registry": _binding(
            deviation_registry_path, study_root
        ),
    }
    for key, expected in expected_bindings.items():
        if run.get(key) != expected:
            raise NDPTestExecutionError(f"test run {key} binding changed")
    arms = execution.get("config", {}).get("planned_arms")
    if (
        not isinstance(arms, list)
        or not arms
        or len(arms) != len(set(arms))
        or run.get("planned_arms") != arms
    ):
        raise NDPTestExecutionError("test run planned arms changed")
    records = run.get("records")
    if not isinstance(records, list):
        raise NDPTestExecutionError("test run records must be a list")
    expected_pairs = {
        (str(case["case_id"]), str(arm_id))
        for case in cases
        for arm_id in arms
    }
    if len(records) != len(expected_pairs):
        raise NDPTestExecutionError(
            "test run must contain the complete case-by-arm matrix"
        )
    case_by_id = {str(case["case_id"]): case for case in cases}
    observed_pairs: set[tuple[str, str]] = set()
    record_ids: set[str] = set()
    record_payloads: list[Dict[str, Any]] = []
    maximum_attempts = execution.get("config", {}).get(
        "execution_order", {}
    ).get("maximum_attempts_per_call")
    if (
        not isinstance(maximum_attempts, int)
        or isinstance(maximum_attempts, bool)
        or maximum_attempts <= 0
    ):
        raise NDPTestExecutionError(
            "execution freeze maximum attempts is invalid"
        )
    for entry in records:
        if not isinstance(entry, dict) or set(entry) != {
            "record_id",
            "case_id",
            "dataset_id",
            "arm_id",
            "status",
            "execution_sequence",
            "artifact",
        }:
            raise NDPTestExecutionError("test run record entry is malformed")
        case_id = str(entry.get("case_id") or "")
        arm_id = str(entry.get("arm_id") or "")
        pair = (case_id, arm_id)
        if pair in observed_pairs or pair not in expected_pairs:
            raise NDPTestExecutionError(
                "test run record matrix identity is invalid"
            )
        record_path = _bound_path(
            entry.get("artifact"),
            study_root=study_root,
            label=f"test run record {case_id}/{arm_id}",
        )
        payload = _load_json(record_path)
        _validate_record(
            payload,
            case=case_by_id[case_id],
            arm_id=arm_id,
            maximum_attempts=maximum_attempts,
            study_root=study_root,
            not_before=case_frozen_at,
            execution_mode=(
                "deterministic"
                if arm_id == DETERMINISTIC_ARM
                else "replay"
                if arm_id == REPLAY_ARM
                else "model"
            ),
            response_parser=response_parser,
            scorer=scorer,
        )
        if _record_projection(payload) != {
            key: entry[key]
            for key in (
                "record_id",
                "case_id",
                "dataset_id",
                "arm_id",
                "status",
                "execution_sequence",
            )
        }:
            raise NDPTestExecutionError(
                "run manifest and record artifact identity differ"
            )
        record_id = str(payload["record_id"])
        if record_id in record_ids:
            raise NDPTestExecutionError("duplicate test run record ID")
        observed_pairs.add(pair)
        record_ids.add(record_id)
        record_payloads.append(payload)
    if observed_pairs != expected_pairs:
        raise NDPTestExecutionError(
            "test run case-by-arm matrix is incomplete"
        )
    sensitivity_conditions = derive_sensitivity_conditions(
        execution["config"]
    )
    maximum_sensitivity_conditions = (
        workflow.get("descriptive_sensitivity_execution_policy", {})
        .get("maximum_derived_condition_count")
    )
    if (
        not isinstance(maximum_sensitivity_conditions, int)
        or isinstance(maximum_sensitivity_conditions, bool)
        or len(sensitivity_conditions) > maximum_sensitivity_conditions
    ):
        raise NDPTestExecutionError(
            "derived sensitivity conditions exceed the frozen bound"
        )
    if run.get("sensitivity_conditions") != sensitivity_conditions:
        raise NDPTestExecutionError(
            "test run sensitivity condition registry changed"
        )
    condition_ids = {
        str(item["condition_id"]) for item in sensitivity_conditions
    }
    expected_sensitivity_pairs = {
        (str(case["case_id"]), condition_id)
        for case in cases
        for condition_id in condition_ids
    }
    sensitivity_entries = run.get("sensitivity_records")
    if (
        not isinstance(sensitivity_entries, list)
        or len(sensitivity_entries) != len(expected_sensitivity_pairs)
    ):
        raise NDPTestExecutionError(
            "test run must contain the complete case-by-sensitivity-condition matrix"
        )
    observed_sensitivity_pairs: set[tuple[str, str]] = set()
    sensitivity_payloads: list[Dict[str, Any]] = []
    for entry in sensitivity_entries:
        if not isinstance(entry, dict) or set(entry) != {
            "record_id",
            "case_id",
            "dataset_id",
            "arm_id",
            "status",
            "execution_sequence",
            "artifact",
        }:
            raise NDPTestExecutionError(
                "test sensitivity record entry is malformed"
            )
        case_id = str(entry.get("case_id") or "")
        condition_id = str(entry.get("arm_id") or "")
        pair = (case_id, condition_id)
        if (
            pair in observed_sensitivity_pairs
            or pair not in expected_sensitivity_pairs
        ):
            raise NDPTestExecutionError(
                "test sensitivity record matrix identity is invalid"
            )
        record_path = _bound_path(
            entry.get("artifact"),
            study_root=study_root,
            label=(
                f"test sensitivity record {case_id}/{condition_id}"
            ),
        )
        payload = _load_json(record_path)
        _validate_record(
            payload,
            case=case_by_id[case_id],
            arm_id=condition_id,
            maximum_attempts=maximum_attempts,
            study_root=study_root,
            not_before=case_frozen_at,
            execution_mode="model",
            response_parser=response_parser,
            scorer=scorer,
        )
        if _record_projection(payload) != {
            key: entry[key]
            for key in (
                "record_id",
                "case_id",
                "dataset_id",
                "arm_id",
                "status",
                "execution_sequence",
            )
        }:
            raise NDPTestExecutionError(
                "sensitivity manifest and record artifact identity differ"
            )
        record_id = str(payload["record_id"])
        if record_id in record_ids:
            raise NDPTestExecutionError("duplicate test run record ID")
        observed_sensitivity_pairs.add(pair)
        record_ids.add(record_id)
        sensitivity_payloads.append(payload)
    if observed_sensitivity_pairs != expected_sensitivity_pairs:
        raise NDPTestExecutionError(
            "test run case-by-sensitivity-condition matrix is incomplete"
        )
    maximum_sensitivity_physical_calls = (
        len(expected_sensitivity_pairs) * maximum_attempts
    )
    observed_sensitivity_physical_calls = sum(
        int(item["physical_model_calls"])
        for item in sensitivity_payloads
    )
    if (
        observed_sensitivity_physical_calls
        > maximum_sensitivity_physical_calls
    ):
        raise NDPTestExecutionError(
            "sensitivity physical-call budget was exceeded"
        )
    all_record_payloads = sorted(
        record_payloads + sensitivity_payloads,
        key=lambda item: int(item["execution_sequence"]),
    )
    sequence = [
        int(item["execution_sequence"]) for item in all_record_payloads
    ]
    if sequence != list(range(1, len(sequence) + 1)):
        raise NDPTestExecutionError(
            "execution sequence must be unique and contiguous"
        )
    schedule_request = build_execution_schedule_request(
        execution_config=execution["config"],
        case_ids=[str(case["case_id"]) for case in cases],
        sensitivity_conditions=sensitivity_conditions,
    )
    try:
        schedule_replay = runner(deepcopy(schedule_request))
    except Exception as exc:  # noqa: BLE001
        raise NDPTestExecutionError(
            f"qualified runner schedule replay failed: {exc}"
        ) from exc
    expected_schedule = (
        schedule_replay.get("schedule")
        if isinstance(schedule_replay, dict)
        else None
    )
    observed_schedule = [
        {
            "execution_sequence": int(item["execution_sequence"]),
            "case_id": str(item["case_id"]),
            "arm_id": str(item["arm_id"]),
        }
        for item in all_record_payloads
    ]
    if (
        not isinstance(expected_schedule, list)
        or expected_schedule != observed_schedule
    ):
        raise NDPTestExecutionError(
            "test execution order differs from qualified frozen schedule"
        )
    for previous, current in zip(
        all_record_payloads, all_record_payloads[1:]
    ):
        previous_completed = _parse_timestamp(
            previous["completed_at"],
            "previous test record completed_at",
        )
        current_started = _parse_timestamp(
            current["started_at"],
            "current test record started_at",
        )
        if current_started < previous_completed:
            raise NDPTestExecutionError(
                "test execution timestamps overlap or contradict the frozen schedule"
            )
    by_pair = {
        (str(item["case_id"]), str(item["arm_id"])): item
        for item in record_payloads
    }
    for case in cases:
        source = by_pair[(str(case["case_id"]), ZERO_SHOT_ARM)]
        replay = by_pair[(str(case["case_id"]), REPLAY_ARM)]
        if (
            replay["physical_model_calls"] != 0
            or replay["attempt_count"] != 0
            or replay["response_sha256"] != source["response_sha256"]
        ):
            raise NDPTestExecutionError(
                "verification arm violates byte-identical zero-call replay"
            )
    deviation_entries = _validate_deviations(
        deviations,
        selection_path=selection_path,
        execution_freeze_path=execution_freeze_path,
        power_freeze_path=power_freeze_path,
        record_ids=record_ids,
        study_root=study_root,
    )
    if run.get("completion_attestation") is not True:
        raise NDPTestExecutionError(
            "test run manifest completion is not attested"
        )
    status_counts = Counter(
        str(item["status"]) for item in all_record_payloads
    )
    primary_status_counts = Counter(
        str(item["status"]) for item in record_payloads
    )
    sensitivity_record_status_counts = Counter(
        str(item["status"]) for item in sensitivity_payloads
    )
    arm_status_counts = {
        arm_id: dict(
            sorted(
                Counter(
                    str(item["status"])
                    for item in record_payloads
                    if item["arm_id"] == arm_id
                ).items()
            )
        )
        for arm_id in arms
    }
    failure_counts = Counter(
        str(item["failure_code"])
        for item in all_record_payloads
        if item["status"] == "execution_failure"
    )
    sensitivity_status_counts = {
        condition_id: dict(
            sorted(
                Counter(
                    str(item["status"])
                    for item in sensitivity_payloads
                    if item["arm_id"] == condition_id
                ).items()
            )
        )
        for condition_id in sorted(condition_ids)
    }
    disposition_counts = Counter(
        str(item["disposition"]) for item in dataset_by_id.values()
    )
    implementation = Path(__file__).resolve()
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": (
            "passed_with_documented_deviations"
            if deviation_entries
            else "passed"
        ),
        "test_run_manifest": _binding(run_manifest_path, study_root),
        "source_artifacts": expected_bindings,
        "test_dataset_count": len(dataset_by_id),
        "test_case_count": len(cases),
        "planned_arm_count": len(arms),
        "sensitivity_condition_count": len(sensitivity_conditions),
        "sensitivity_conditions": sensitivity_conditions,
        "expected_primary_record_count": len(expected_pairs),
        "validated_primary_record_count": len(record_payloads),
        "expected_sensitivity_record_count": len(
            expected_sensitivity_pairs
        ),
        "validated_sensitivity_record_count": len(
            sensitivity_payloads
        ),
        "maximum_sensitivity_physical_calls": (
            maximum_sensitivity_physical_calls
        ),
        "observed_sensitivity_physical_calls": (
            observed_sensitivity_physical_calls
        ),
        "sensitivity_physical_call_budget_respected": True,
        "expected_record_count": (
            len(expected_pairs) + len(expected_sensitivity_pairs)
        ),
        "validated_record_count": len(all_record_payloads),
        "complete_case_by_arm_matrix": True,
        "complete_case_by_sensitivity_condition_matrix": True,
        "qualified_execution_schedule_verified": True,
        "execution_chronology_verified": True,
        "execution_schedule_sha256": _sha256_canonical(
            expected_schedule
        ),
        "execution_block_count": len(
            schedule_request["execution_blocks"]
        ),
        "dataset_disposition_counts": dict(sorted(disposition_counts.items())),
        "record_status_counts": dict(sorted(status_counts.items())),
        "primary_record_status_counts": dict(
            sorted(primary_status_counts.items())
        ),
        "sensitivity_record_status_counts": dict(
            sorted(sensitivity_record_status_counts.items())
        ),
        "arm_status_counts": arm_status_counts,
        "sensitivity_status_counts": sensitivity_status_counts,
        "failure_reason_counts": dict(sorted(failure_counts.items())),
        "deviation_count": len(deviation_entries),
        "byte_identical_zero_call_replay_verified": True,
        "post_outcome_case_addition_or_deletion": False,
        "post_outcome_sensitivity_condition_addition_or_deletion": False,
        "failure_and_abstention_retained_in_denominators": True,
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
    }


def verify_run_receipt(
    receipt: Mapping[str, Any],
    **kwargs: Any,
) -> Dict[str, Any]:
    try:
        expected = build_run_receipt(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": REPLAY_SCHEMA_VERSION,
            "status": "failed",
            "detail": str(exc),
            "differing_top_level_keys": [],
        }
    differing = sorted(
        key
        for key in set(expected) | set(receipt)
        if expected.get(key) != receipt.get(key)
    )
    return {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "status": "passed" if not differing else "failed",
        "detail": None,
        "differing_top_level_keys": differing,
    }


def build_missingness_report(
    *,
    receipt_path: Path,
    run_manifest_path: Path,
    selection_path: Path,
    release_readiness_path: Path,
    workflow_path: Path,
    execution_freeze_path: Path,
    power_freeze_path: Path,
    release_authorization_path: Path,
    release_receipt_path: Path,
    case_manifest_path: Path,
    deviation_registry_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    receipt = _load_json(receipt_path)
    replay = verify_run_receipt(
        receipt,
        run_manifest_path=run_manifest_path,
        selection_path=selection_path,
        release_readiness_path=release_readiness_path,
        workflow_path=workflow_path,
        execution_freeze_path=execution_freeze_path,
        power_freeze_path=power_freeze_path,
        release_authorization_path=release_authorization_path,
        release_receipt_path=release_receipt_path,
        case_manifest_path=case_manifest_path,
        deviation_registry_path=deviation_registry_path,
        study_root=study_root,
    )
    if replay["status"] != "passed":
        raise NDPTestExecutionError(
            "test run receipt does not replay"
        )
    implementation = Path(__file__).resolve()
    return {
        "schema_version": MISSINGNESS_SCHEMA_VERSION,
        "status": "complete",
        "test_run_receipt": _binding(receipt_path, study_root),
        "test_dataset_count": receipt["test_dataset_count"],
        "test_case_count": receipt["test_case_count"],
        "sensitivity_condition_count": receipt[
            "sensitivity_condition_count"
        ],
        "sensitivity_conditions": receipt["sensitivity_conditions"],
        "expected_primary_record_count": receipt[
            "expected_primary_record_count"
        ],
        "validated_primary_record_count": receipt[
            "validated_primary_record_count"
        ],
        "expected_sensitivity_record_count": receipt[
            "expected_sensitivity_record_count"
        ],
        "validated_sensitivity_record_count": receipt[
            "validated_sensitivity_record_count"
        ],
        "maximum_sensitivity_physical_calls": receipt[
            "maximum_sensitivity_physical_calls"
        ],
        "observed_sensitivity_physical_calls": receipt[
            "observed_sensitivity_physical_calls"
        ],
        "sensitivity_physical_call_budget_respected": receipt[
            "sensitivity_physical_call_budget_respected"
        ],
        "expected_record_count": receipt["expected_record_count"],
        "validated_record_count": receipt["validated_record_count"],
        "qualified_execution_schedule_verified": receipt[
            "qualified_execution_schedule_verified"
        ],
        "execution_chronology_verified": receipt[
            "execution_chronology_verified"
        ],
        "execution_schedule_sha256": receipt[
            "execution_schedule_sha256"
        ],
        "dataset_disposition_counts": receipt[
            "dataset_disposition_counts"
        ],
        "record_status_counts": receipt["record_status_counts"],
        "primary_record_status_counts": receipt[
            "primary_record_status_counts"
        ],
        "sensitivity_record_status_counts": receipt[
            "sensitivity_record_status_counts"
        ],
        "arm_status_counts": receipt["arm_status_counts"],
        "sensitivity_status_counts": receipt[
            "sensitivity_status_counts"
        ],
        "failure_reason_counts": receipt["failure_reason_counts"],
        "deviation_count": receipt["deviation_count"],
        "silent_dataset_deletion": False,
        "silent_case_or_arm_deletion": False,
        "silent_sensitivity_condition_deletion": False,
        "post_outcome_imputation": False,
        "failure_and_abstention_retained_in_denominators": True,
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and validate the immutable NDP-50 test run."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare-workflow")
    prepare.add_argument("--selection", type=Path, required=True)
    prepare.add_argument("--cpa-design", type=Path, required=True)
    prepare.add_argument(
        "--execution-freeze-workflow", type=Path, required=True
    )
    prepare.add_argument(
        "--power-freeze-workflow", type=Path, required=True
    )
    prepare.add_argument("--study-root", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    for command in ("build-release", "verify-release"):
        child = subparsers.add_parser(command)
        child.add_argument("--authorization", type=Path, required=True)
        child.add_argument(
            "--release-readiness", type=Path, required=True
        )
        child.add_argument("--selection", type=Path, required=True)
        child.add_argument("--workflow", type=Path, required=True)
        child.add_argument("--execution-freeze", type=Path, required=True)
        child.add_argument("--power-freeze", type=Path, required=True)
        child.add_argument("--study-root", type=Path, required=True)
        if command == "build-release":
            child.add_argument("--output", type=Path, required=True)
        else:
            child.add_argument("--receipt", type=Path, required=True)
    for command in ("build-receipt", "verify-receipt", "build-missingness"):
        child = subparsers.add_parser(command)
        child.add_argument("--run-manifest", type=Path, required=True)
        child.add_argument("--selection", type=Path, required=True)
        child.add_argument(
            "--release-readiness", type=Path, required=True
        )
        child.add_argument("--workflow", type=Path, required=True)
        child.add_argument("--execution-freeze", type=Path, required=True)
        child.add_argument("--power-freeze", type=Path, required=True)
        child.add_argument(
            "--release-authorization", type=Path, required=True
        )
        child.add_argument(
            "--release-receipt", type=Path, required=True
        )
        child.add_argument("--case-manifest", type=Path, required=True)
        child.add_argument(
            "--deviation-registry", type=Path, required=True
        )
        child.add_argument("--study-root", type=Path, required=True)
        if command == "verify-receipt":
            child.add_argument("--receipt", type=Path, required=True)
        else:
            child.add_argument("--output", type=Path, required=True)
        if command == "build-missingness":
            child.add_argument("--receipt", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare-workflow":
        payload = build_workflow_spec(
            selection_path=args.selection,
            cpa_design_path=args.cpa_design,
            execution_freeze_workflow_path=(
                args.execution_freeze_workflow
            ),
            power_freeze_workflow_path=args.power_freeze_workflow,
            study_root=args.study_root,
        )
        _write_json(args.output, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "test_dataset_count": payload[
                        "test_dataset_count"
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    release_common = {
        "authorization_path": args.authorization,
        "release_readiness_path": args.release_readiness,
        "selection_path": args.selection,
        "workflow_path": args.workflow,
        "execution_freeze_path": args.execution_freeze,
        "power_freeze_path": args.power_freeze,
        "study_root": args.study_root,
    } if args.command in {"build-release", "verify-release"} else None
    if args.command == "build-release":
        assert release_common is not None
        payload = build_test_release_receipt(**release_common)
        _write_json(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "verify-release":
        assert release_common is not None
        payload = verify_test_release_receipt(
            _load_json(args.receipt), **release_common
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "passed" else 1
    common = {
        "run_manifest_path": args.run_manifest,
        "selection_path": args.selection,
        "release_readiness_path": args.release_readiness,
        "workflow_path": args.workflow,
        "execution_freeze_path": args.execution_freeze,
        "power_freeze_path": args.power_freeze,
        "release_authorization_path": args.release_authorization,
        "release_receipt_path": args.release_receipt,
        "case_manifest_path": args.case_manifest,
        "deviation_registry_path": args.deviation_registry,
        "study_root": args.study_root,
    }
    if args.command == "build-receipt":
        payload = build_run_receipt(**common)
        _write_json(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "verify-receipt":
        payload = verify_run_receipt(_load_json(args.receipt), **common)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "passed" else 1
    payload = build_missingness_report(
        receipt_path=args.receipt,
        **common,
    )
    _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
