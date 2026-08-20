from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping
from urllib.parse import urlparse

from .ndp50_data_governance_review import (
    verify_approval as verify_governance_approval,
)
from .ndp50_cpa_design import (
    registered_analysis_contract,
    registered_metric_contract,
)
from .ndp50_demonstration_pool import verify_pool as verify_demonstration_pool
from .ndp50_execution_qualification import (
    IMPLEMENTATION_SLOTS as QUALIFICATION_IMPLEMENTATION_SLOTS,
    PROBE_SUITE_VERSION,
    interface_version,
    verify_qualification_receipt,
)
from .ndp50_semantic_gold import verify_approval as verify_gold_approval
from .ndp50_source_approval import load_approved_evidence_registry
from .semantic_gold_workflow import validate_vocabulary
from .semantic_study_preflight import preflight_backend_registry


CONFIG_SCHEMA_VERSION = "ndp50-execution-freeze-config/v1"
WORKFLOW_SCHEMA_VERSION = "ndp50-execution-freeze-workflow/v1"
FREEZE_SCHEMA_VERSION = "ndp50-execution-freeze/v1"
VALIDATION_SCHEMA_VERSION = "ndp50-execution-freeze-validation/v1"
FREEZE_VALIDATION_SCHEMA_VERSION = "ndp50-execution-freeze-replay/v1"
ZERO_SHOT_ARM = "zero_shot_dataset_level"
MODEL_ARMS = {
    ZERO_SHOT_ARM: 0,
    "one_shot_development_similarity_selected": 1,
    "five_shot_development_similarity_selected": 5,
}
REPLAY_ARM = "zero_shot_byte_identical_response_plus_deterministic_verification"
ALL_ARMS = {"deterministic_only", REPLAY_ARM, *MODEL_ARMS}
IMPLEMENTATION_SLOTS = set(QUALIFICATION_IMPLEMENTATION_SLOTS)
RESOURCE_ACCOUNTING_BASES = {
    "public_list_price",
    "institutional_contract",
    "local_compute_not_monetized",
}
CONFIDENCE_INTERPRETATIONS = {
    "ordering_score_only",
    "probability_of_exact_correctness",
}
RELIABILITY_BIN_EDGES = [round(index / 10, 1) for index in range(11)]
SIGNOFF_ROLES = {
    "study_operator": {"principal_investigator", "research_engineer"},
    "methods_reviewer": {
        "independent_methods_reviewer",
        "research_compliance_reviewer",
    },
}


class NDPExecutionFreezeError(ValueError):
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


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _study_relative(path: Path, study_root: Path) -> str:
    try:
        return path.resolve().relative_to(study_root.resolve()).as_posix()
    except ValueError as exc:
        raise NDPExecutionFreezeError(
            f"artifact must be inside the study root: {path}"
        ) from exc


def _binding(path: Path, study_root: Path) -> Dict[str, str]:
    if not path.is_file():
        raise NDPExecutionFreezeError(f"artifact does not exist: {path}")
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
        raise NDPExecutionFreezeError(f"{label} binding is missing")
    value = ref.get("file")
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise NDPExecutionFreezeError(
            f"{label} must use a study-relative file"
        )
    root = study_root.resolve()
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise NDPExecutionFreezeError(
            f"{label} escapes the study root"
        ) from exc
    if not path.is_file():
        raise NDPExecutionFreezeError(f"{label} does not exist")
    if _sha256_file(path) != ref.get("sha256"):
        raise NDPExecutionFreezeError(f"{label} hash mismatch")
    return path


def _valid_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_date(value: Any) -> bool:
    try:
        date.fromisoformat(str(value or ""))
    except ValueError:
        return False
    return True


def _check_resource_accounting(
    config: Mapping[str, Any],
    *,
    error: Any,
) -> None:
    contract = config.get("resource_accounting_contract")
    expected_keys = {
        "currency",
        "price_basis",
        "pricing_effective_on",
        "pricing_source",
        "rates_usd",
        "local_compute_cost_included",
        "include_failed_model_calls",
        "include_retries",
        "include_reused_upstream",
        "hardware_runtime_source",
        "model_latency_field",
        "end_to_end_latency_field",
        "cost_scope_note",
    }
    if not isinstance(contract, dict) or set(contract) != expected_keys:
        error(
            "resource_accounting_contract_invalid",
            "resource accounting must contain the exact registered fields",
        )
        return
    if contract.get("currency") != "USD":
        error(
            "resource_accounting_currency_invalid",
            "resource accounting currency must be USD",
        )
    basis = contract.get("price_basis")
    if basis not in RESOURCE_ACCOUNTING_BASES:
        error(
            "resource_accounting_price_basis_invalid",
            "price basis must be frozen to a registered value",
        )
    if not _valid_date(contract.get("pricing_effective_on")):
        error(
            "resource_accounting_price_date_invalid",
            "pricing_effective_on must be an ISO date",
        )
    source = contract.get("pricing_source")
    if basis == "public_list_price":
        parsed = urlparse(str(source or ""))
        if parsed.scheme != "https" or not parsed.netloc:
            error(
                "resource_accounting_price_source_invalid",
                "public list pricing requires an HTTPS source",
            )
    elif basis == "institutional_contract":
        if not _valid_text(source):
            error(
                "resource_accounting_price_source_invalid",
                "institutional pricing requires a frozen source identifier",
            )
    elif basis == "local_compute_not_monetized" and (
        source != "not_applicable_local_compute"
    ):
        error(
            "resource_accounting_price_source_invalid",
            "unmonetized local compute requires its explicit source marker",
        )

    rates = contract.get("rates_usd")
    rate_keys = {
        "per_call",
        "input_per_million_tokens",
        "output_per_million_tokens",
    }
    if not isinstance(rates, dict) or set(rates) != rate_keys:
        error(
            "resource_accounting_rates_invalid",
            "the exact per-call and token price fields are required",
        )
        rates = {}
    numeric_rates = []
    for key in sorted(rate_keys):
        value = rates.get(key)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or float(value) < 0
        ):
            error(
                "resource_accounting_rates_invalid",
                f"rates_usd.{key} must be finite and nonnegative",
            )
        else:
            numeric_rates.append(float(value))
    local_cost_included = contract.get("local_compute_cost_included")
    if not isinstance(local_cost_included, bool):
        error(
            "resource_accounting_local_cost_invalid",
            "local_compute_cost_included must be boolean",
        )
    if basis == "local_compute_not_monetized":
        if any(value != 0 for value in numeric_rates):
            error(
                "resource_accounting_local_rates_invalid",
                "unmonetized local compute must freeze all monetary rates at zero",
            )
        if local_cost_included is not False:
            error(
                "resource_accounting_local_cost_invalid",
                "unmonetized local compute cannot claim local cost inclusion",
            )
    elif len(numeric_rates) == len(rate_keys) and not any(
        value > 0 for value in numeric_rates
    ):
        error(
            "resource_accounting_rates_invalid",
            "a nonlocal price schedule must contain at least one positive rate",
        )
    for key in (
        "include_failed_model_calls",
        "include_retries",
        "include_reused_upstream",
    ):
        if contract.get(key) is not True:
            error(
                "resource_accounting_scope_invalid",
                f"{key} must be true",
            )
    if (
        contract.get("hardware_runtime_source")
        != "selected_backend_registry_record"
    ):
        error(
            "resource_accounting_hardware_source_invalid",
            "hardware/runtime must come from the selected backend registry",
        )
    if contract.get("model_latency_field") != "model_latency_seconds":
        error(
            "resource_accounting_latency_fields_invalid",
            "model latency field is not frozen to the score contract",
        )
    if (
        contract.get("end_to_end_latency_field")
        != "end_to_end_latency_seconds"
    ):
        error(
            "resource_accounting_latency_fields_invalid",
            "end-to-end latency field is not frozen to the score contract",
        )
    if not _valid_text(contract.get("cost_scope_note")):
        error(
            "resource_accounting_scope_note_missing",
            "cost inclusions and exclusions require a non-empty scope note",
        )


def _check_confidence_reporting(
    config: Mapping[str, Any],
    *,
    error: Any,
) -> None:
    contract = config.get("confidence_reporting_contract")
    expected_keys = {
        "score_field",
        "score_minimum",
        "score_maximum",
        "accepted_known_requires_score",
        "nonaccepted_requires_null",
        "calibration_target",
        "grouping_field",
        "pooling_across_labels_permitted",
        "pooling_across_arms_permitted",
        "reliability_bin_edges",
        "minimum_group_support_for_calibration_claim",
        "risk_coverage_tie_rule",
        "aurc_interval",
        "confidence_source_by_arm",
        "confidence_interpretation_by_arm",
    }
    if not isinstance(contract, dict) or set(contract) != expected_keys:
        error(
            "confidence_reporting_contract_invalid",
            "confidence reporting must contain the exact registered fields",
        )
        return
    if (
        contract.get("score_field") != "confidence_score"
        or contract.get("score_minimum") != 0
        or contract.get("score_maximum") != 1
        or contract.get("accepted_known_requires_score") is not True
        or contract.get("nonaccepted_requires_null") is not True
    ):
        error(
            "confidence_score_contract_invalid",
            "accepted predictions require confidence_score in [0,1]",
        )
    if (
        contract.get("calibration_target")
        != "exact_canonical_correctness_on_applicable_known_slots"
        or contract.get("grouping_field") != "label_id"
    ):
        error(
            "confidence_calibration_target_invalid",
            "calibration target and grouping must match the registered scorer",
        )
    if (
        contract.get("pooling_across_labels_permitted") is not False
        or contract.get("pooling_across_arms_permitted") is not False
    ):
        error(
            "confidence_pooling_invalid",
            "confidence scales cannot be pooled across labels or arms",
        )
    if contract.get("reliability_bin_edges") != RELIABILITY_BIN_EDGES:
        error(
            "confidence_reliability_bins_invalid",
            "reliability bins must be fixed deciles over [0,1]",
        )
    support = contract.get("minimum_group_support_for_calibration_claim")
    if (
        not isinstance(support, int)
        or isinstance(support, bool)
        or support < 30
    ):
        error(
            "confidence_support_threshold_invalid",
            "calibration claims require at least 30 accepted predictions per arm-label group",
        )
    if (
        contract.get("risk_coverage_tie_rule")
        != "whole_confidence_tie_groups_right_continuous"
        or contract.get("aurc_interval") != "achieved_coverage_only"
    ):
        error(
            "confidence_aurc_contract_invalid",
            "AURC tie handling and achieved-coverage interval must be frozen",
        )
    sources = contract.get("confidence_source_by_arm")
    interpretations = contract.get("confidence_interpretation_by_arm")
    if (
        not isinstance(sources, dict)
        or set(sources) != ALL_ARMS
        or any(not _valid_text(value) for value in sources.values())
    ):
        error(
            "confidence_sources_invalid",
            "every registered arm requires a non-empty confidence source",
        )
    if (
        not isinstance(interpretations, dict)
        or set(interpretations) != ALL_ARMS
        or any(
            value not in CONFIDENCE_INTERPRETATIONS
            for value in interpretations.values()
        )
    ):
        error(
            "confidence_interpretations_invalid",
            "every registered arm requires a frozen confidence interpretation",
        )


def _is_loopback_url(value: Any) -> bool:
    try:
        host = urlparse(str(value or "")).hostname
    except ValueError:
        return False
    return host in {"127.0.0.1", "localhost", "::1"}


def _inputs(
    cpa_design_path: Path,
    packet_manifest_path: Path,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    design = _load_json(cpa_design_path)
    packets = _load_json(packet_manifest_path)
    if design.get("schema_version") != "ndp50-cpa-design/v1":
        raise NDPExecutionFreezeError("unexpected CPA design schema")
    if (
        packets.get("schema_version") != "ndp50-semantic-packet-pack/v1"
        or packets.get("status")
        != "neutral_packets_ready_source_bundles_blocked"
    ):
        raise NDPExecutionFreezeError("unexpected packet manifest")
    cases = packets.get("cases")
    if not isinstance(cases, list) or not cases:
        raise NDPExecutionFreezeError("packet manifest has no cases")
    if any(
        item.get("split") not in {"development", "validation"}
        for item in cases
    ):
        raise NDPExecutionFreezeError(
            "execution-freeze preparation cannot contain test cases"
        )
    planned_arms = design.get("planned_arms")
    expected_arms = {"deterministic_only", REPLAY_ARM, *MODEL_ARMS}
    if (
        not isinstance(planned_arms, list)
        or set(planned_arms) != expected_arms
        or len(planned_arms) != len(expected_arms)
    ):
        raise NDPExecutionFreezeError(
            "CPA planned arms do not match the registered design"
        )
    if design.get("analysis") != registered_analysis_contract():
        raise NDPExecutionFreezeError(
            "CPA analysis contract does not match the registered contract"
        )
    if design.get("metric_contract") != registered_metric_contract():
        raise NDPExecutionFreezeError(
            "CPA metric contract does not match the registered contract"
        )
    return design, packets


def build_config_template(
    *,
    cpa_design_path: Path,
    packet_manifest_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    design, _ = _inputs(cpa_design_path, packet_manifest_path)
    samplers = [
        {
            "sampler_id": sampler_id,
            "implementation": None,
            "seed": None,
            "parameters": None,
        }
        for sampler_id in design["row_sampling_sensitivity"]
    ]
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "status": "neutral_pending_execution_configuration",
        "human_decisions_present": False,
        "model_or_gold_outcomes_observed_before_freeze": False,
        "cpa_design": _binding(cpa_design_path, study_root),
        "packet_manifest": _binding(packet_manifest_path, study_root),
        "upstream_bindings": {
            "frozen_vocabulary": None,
            "approved_source_manifest": None,
            "cpa_consensus": None,
            "semantic_gold_approval": None,
            "data_governance_audit": None,
            "data_governance_approval": None,
        },
        "signoffs": [
            {
                "slot": "study_operator",
                "signatory_id": None,
                "role": None,
                "institution": None,
                "qualification_summary": None,
                "conflict_of_interest_declared": None,
                "developer_participation": None,
                "signed_on": None,
            },
            {
                "slot": "methods_reviewer",
                "signatory_id": None,
                "role": None,
                "institution": None,
                "qualification_summary": None,
                "conflict_of_interest_declared": None,
                "developer_participation": False,
                "signed_on": None,
            },
        ],
        "planned_arms": list(design["planned_arms"]),
        "analysis_contract": {
            **deepcopy(design["analysis"]),
            "metric_contract_sha256": _sha256_json(
                design["metric_contract"]
            ),
            "prompt_variants_role": "descriptive_sensitivity_only",
            "row_sampling_variants_role": "descriptive_sensitivity_only",
            "fine_tuning_in_primary_study": False,
        },
        "prompt_contracts": [],
        "prompt_sensitivity_contracts": [],
        "response_reuse_contract": {
            "source_arm": "zero_shot_dataset_level",
            "consumer_arm": REPLAY_ARM,
            "byte_identical_response_required": True,
            "additional_physical_model_calls": 0,
        },
        "serialization_contract": {
            "table_format": None,
            "column_order_policy": None,
            "row_order_policy": None,
            "missing_value_rendering": None,
            "missing_display_cell_fill_policy": None,
            "value_escaping_policy": None,
            "max_cell_characters": None,
            "truncation_marker": None,
            "metadata_fields": [],
        },
        "row_sampling_contract": {
            "primary_sampler_id": None,
            "sensitivity_samplers": samplers,
        },
        "demonstration_contract": {
            "candidate_pool_split": "development_only",
            "validation_or_test_as_demonstration": False,
            "candidate_pool_manifest": None,
            "selection_method": None,
            "ranking_implementation": None,
            "target_gold_or_model_outcomes_used_for_ranking": False,
            "tie_breaker": "case_id_ascending",
            "similarity_model": None,
            "one_shot_count": 1,
            "five_shot_count": 5,
        },
        "backend_contract": {
            "registry": None,
            "primary_backend_id": None,
            "external_service_used": None,
            "temperature": 0,
            "seed": None,
            "max_tokens": None,
            "thinking_enabled": False,
            "selection_uses_semantic_accuracy": False,
        },
        "resource_accounting_contract": {
            "currency": "USD",
            "price_basis": None,
            "pricing_effective_on": None,
            "pricing_source": None,
            "rates_usd": {
                "per_call": None,
                "input_per_million_tokens": None,
                "output_per_million_tokens": None,
            },
            "local_compute_cost_included": None,
            "include_failed_model_calls": True,
            "include_retries": True,
            "include_reused_upstream": True,
            "hardware_runtime_source": "selected_backend_registry_record",
            "model_latency_field": "model_latency_seconds",
            "end_to_end_latency_field": "end_to_end_latency_seconds",
            "cost_scope_note": None,
        },
        "confidence_reporting_contract": {
            "score_field": "confidence_score",
            "score_minimum": 0,
            "score_maximum": 1,
            "accepted_known_requires_score": True,
            "nonaccepted_requires_null": True,
            "calibration_target": (
                "exact_canonical_correctness_on_applicable_known_slots"
            ),
            "grouping_field": "label_id",
            "pooling_across_labels_permitted": False,
            "pooling_across_arms_permitted": False,
            "reliability_bin_edges": RELIABILITY_BIN_EDGES,
            "minimum_group_support_for_calibration_claim": 30,
            "risk_coverage_tie_rule": (
                "whole_confidence_tie_groups_right_continuous"
            ),
            "aurc_interval": "achieved_coverage_only",
            "confidence_source_by_arm": {
                arm_id: None for arm_id in sorted(ALL_ARMS)
            },
            "confidence_interpretation_by_arm": {
                arm_id: None for arm_id in sorted(ALL_ARMS)
            },
        },
        "execution_implementations": {
            key: None for key in sorted(IMPLEMENTATION_SLOTS)
        },
        "execution_qualification": {
            "declaration": None,
            "receipt": None,
        },
        "execution_order": {
            "case_order_policy": None,
            "case_order_seed": None,
            "arm_interleaving_policy": None,
            "arm_order_seed": None,
            "retry_policy": None,
            "request_timeout_seconds": None,
            "maximum_attempts_per_call": None,
        },
        "completion_attestation": None,
    }


def build_workflow_spec(
    *,
    cpa_design_path: Path,
    packet_manifest_path: Path,
    config_template_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    expected = build_config_template(
        cpa_design_path=cpa_design_path,
        packet_manifest_path=packet_manifest_path,
        study_root=study_root,
    )
    if _load_json(config_template_path) != expected:
        raise NDPExecutionFreezeError(
            "execution config is not the canonical neutral template"
        )
    implementation = Path(__file__).resolve()
    return {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "status": "implementation_ready_waiting_on_upstream_human_gates",
        "human_decisions_present": False,
        "model_or_gold_outcomes_observed": False,
        "cpa_design": _binding(cpa_design_path, study_root),
        "packet_manifest": _binding(packet_manifest_path, study_root),
        "neutral_config_template": _binding(
            config_template_path, study_root
        ),
        "required_prompt_contract_arms": sorted(MODEL_ARMS),
        "minimum_prompt_sensitivity_variants": 2,
        "maximum_prompt_sensitivity_variants": 4,
        "primary_prompt_sensitivity_anchor_required": True,
        "primary_row_sampler_anchor_required": True,
        "sensitivity_single_factor_at_a_time_required": True,
        "required_row_samplers": [
            item["sampler_id"]
            for item in expected["row_sampling_contract"][
                "sensitivity_samplers"
            ]
        ],
        "byte_identical_replay_required": True,
        "backend_operational_preflight_required": True,
        "implementation_qualification_required": True,
        "implementation_qualification_probe_suite": PROBE_SUITE_VERSION,
        "implementation_qualification_synthetic_only": True,
        "required_implementation_interfaces": {
            slot: interface_version(slot)
            for slot in sorted(IMPLEMENTATION_SLOTS)
        },
        "automatic_freeze": False,
        "sequence": [
            "complete_all_upstream_human_gates",
            "freeze_prompts_response_schema_and_serialization",
            "freeze_development_only_demonstration_pool_and_ranking",
            "freeze_all_row_samplers_and_seeds",
            "freeze_operationally_qualified_backend_registry",
            "freeze_runner_parser_scorer_and_execution_order",
            "run_synthetic_execution_implementation_qualification",
            "independent_methods_review",
            "validator_generate_execution_freeze",
            "rebuild_readiness_and_handoff",
        ],
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            name: _sha256_file(implementation.with_name(name))
            for name in (
                "ndp50_data_governance_review.py",
                "ndp50_demonstration_pool.py",
                "ndp50_execution_qualification.py",
                "ndp50_semantic_gold.py",
                "ndp50_source_approval.py",
                "semantic_gold_workflow.py",
                "semantic_study_preflight.py",
            )
        },
    }


def _check_signoffs(config: Mapping[str, Any], error) -> None:
    items = config.get("signoffs")
    if not isinstance(items, list):
        error("signoffs_missing", "two signoffs are required")
        return
    by_slot = {
        str(item.get("slot") or ""): item
        for item in items
        if isinstance(item, dict)
    }
    if (
        len(by_slot) != len(items)
        or set(by_slot) != set(SIGNOFF_ROLES)
    ):
        error(
            "signoff_slots_invalid",
            "signoffs must contain exactly operator and methods reviewer",
        )
        return
    identifiers = []
    for slot, item in by_slot.items():
        identifier = str(item.get("signatory_id") or "")
        if not identifier:
            error("signatory_id_missing", f"{slot} signatory id is required")
        identifiers.append(identifier)
        if item.get("role") not in SIGNOFF_ROLES[slot]:
            error("signatory_role_invalid", f"{slot} role is invalid")
        for key in ("institution", "qualification_summary"):
            if not _valid_text(item.get(key)):
                error(
                    f"signatory_{key}_missing",
                    f"{slot}.{key} must be non-empty",
                )
        if item.get("conflict_of_interest_declared") is not False:
            error(
                "signatory_conflict_not_cleared",
                f"{slot} must declare no unresolved conflict",
            )
        if not isinstance(item.get("developer_participation"), bool):
            error(
                "developer_participation_missing",
                f"{slot} developer participation must be declared",
            )
        if slot == "methods_reviewer" and item.get(
            "developer_participation"
        ) is not False:
            error(
                "methods_reviewer_not_independent",
                "methods reviewer must be a non-developer",
            )
        if not _valid_date(item.get("signed_on")):
            error(
                "signatory_date_invalid",
                f"{slot}.signed_on must be an ISO date",
            )
    if len(identifiers) == 2 and identifiers[0] == identifiers[1]:
        error(
            "signatories_not_distinct",
            "operator and methods reviewer must be distinct",
        )


def _check_prompt_contracts(
    config: Mapping[str, Any],
    *,
    study_root: Path,
    error,
) -> None:
    contracts = config.get("prompt_contracts")
    if not isinstance(contracts, list):
        contracts = []
        error("prompt_contracts_missing", "prompt contracts must be a list")
    by_arm = {
        str(item.get("arm_id") or ""): item
        for item in contracts
        if isinstance(item, dict)
    }
    if (
        len(by_arm) != len(contracts)
        or set(by_arm) != set(MODEL_ARMS)
    ):
        error(
            "prompt_arm_coverage",
            "prompt contracts must exactly cover all model-call arms",
        )
    for arm_id, item in by_arm.items():
        if item.get("shot_count") != MODEL_ARMS[arm_id]:
            error("prompt_shot_count", f"{arm_id} shot count is invalid")
        for key in ("prompt", "response_schema"):
            try:
                bound = _bound_path(
                    item.get(key),
                    study_root=study_root,
                    label=f"{arm_id}.{key}",
                )
                if key == "prompt":
                    prompt_text = bound.read_text(encoding="utf-8")
                    required_tokens = {
                        "{{candidate_vocabulary}}",
                        "{{target_table}}",
                    }
                    if item.get("shot_count", 0) > 0:
                        required_tokens.add("{{demonstrations}}")
                    if not required_tokens.issubset(set(
                        token
                        for token in required_tokens
                        if token in prompt_text
                    )):
                        error(
                            "prompt_placeholder_missing",
                            f"{arm_id} prompt lacks a required bound slot",
                        )
                else:
                    schema = _load_json(bound)
                    if schema.get("type") != "object":
                        error(
                            "response_schema_invalid",
                            f"{arm_id} response schema must be an object",
                        )
                    slots_schema = (
                        schema.get("properties", {}).get("slots", {})
                        if isinstance(schema.get("properties"), dict)
                        else {}
                    )
                    item_schema = (
                        slots_schema.get("items", {})
                        if isinstance(slots_schema, dict)
                        else {}
                    )
                    item_properties = (
                        item_schema.get("properties", {})
                        if isinstance(item_schema, dict)
                        else {}
                    )
                    confidence_schema = (
                        item_properties.get("confidence_score", {})
                        if isinstance(item_properties, dict)
                        else {}
                    )
                    required = (
                        item_schema.get("required", [])
                        if isinstance(item_schema, dict)
                        else []
                    )
                    if (
                        not isinstance(confidence_schema, dict)
                        or confidence_schema.get("type")
                        != ["number", "null"]
                        or confidence_schema.get("minimum") != 0
                        or confidence_schema.get("maximum") != 1
                        or "confidence_score" not in required
                    ):
                        error(
                            "response_schema_confidence_invalid",
                            (
                                f"{arm_id} response schema must require "
                                "confidence_score as number-or-null in [0,1]"
                            ),
                        )
            except Exception as exc:  # noqa: BLE001
                error("prompt_binding_invalid", str(exc))
        factors = item.get("paper_factorization")
        if not isinstance(factors, dict) or not all(
            _valid_text(factors.get(key))
            for key in (
                "task_description_variant",
                "instruction_variant",
                "classification_wording",
            )
        ):
            error(
                "prompt_factorization_missing",
                f"{arm_id} must freeze all three paper prompt factors",
            )
        if item.get("candidate_vocabulary_in_prompt") is not True:
            error(
                "prompt_vocabulary_missing",
                f"{arm_id} must expose the frozen candidate vocabulary",
            )
        if item.get("output_candidate_or_oov_only") is not True:
            error(
                "prompt_output_contract_missing",
                f"{arm_id} must freeze candidate-or-OOV output behavior",
            )
        order = item.get("message_order")
        expected_order = ["system"]
        expected_order.extend(
            [
                value
                for _ in range(MODEL_ARMS[arm_id])
                for value in (
                    "user_demonstration",
                    "assistant_demonstration",
                )
            ]
        )
        expected_order.append("user_target")
        if order != expected_order:
            error(
                "prompt_message_order_invalid",
                f"{arm_id} message order must match its shot count",
            )
    sensitivity = config.get("prompt_sensitivity_contracts")
    if (
        not isinstance(sensitivity, list)
        or not 2 <= len(sensitivity) <= 4
    ):
        error(
            "prompt_sensitivity_count_invalid",
            "two to four frozen descriptive prompt variants are required",
        )
        return
    variant_ids = {
        str(item.get("variant_id") or "")
        for item in sensitivity
        if isinstance(item, dict)
    }
    if len(variant_ids) != len(sensitivity) or "" in variant_ids:
        error(
            "prompt_sensitivity_ids_invalid",
            "prompt sensitivity variant ids must be unique and non-empty",
        )
    factor_triples = set()
    primary_variants = []
    for item in sensitivity:
        if not isinstance(item, dict):
            continue
        if not isinstance(item.get("is_primary"), bool):
            error(
                "prompt_sensitivity_primary_flag_missing",
                "every prompt sensitivity variant must declare is_primary",
            )
        elif item["is_primary"]:
            primary_variants.append(item)
        try:
            prompt_path = _bound_path(
                item.get("prompt"),
                study_root=study_root,
                label=f"prompt sensitivity {item.get('variant_id')}",
            )
            prompt_text = prompt_path.read_text(encoding="utf-8")
            if not {
                "{{candidate_vocabulary}}",
                "{{target_table}}",
            }.issubset(
                {
                    token
                    for token in (
                        "{{candidate_vocabulary}}",
                        "{{target_table}}",
                    )
                    if token in prompt_text
                }
            ):
                error(
                    "prompt_sensitivity_placeholder_missing",
                    "sensitivity prompt lacks a required bound slot",
                )
        except Exception as exc:  # noqa: BLE001
            error("prompt_sensitivity_binding_invalid", str(exc))
        factors = item.get("paper_factorization") or {}
        triple = tuple(
            str(factors.get(key) or "")
            for key in (
                "task_description_variant",
                "instruction_variant",
                "classification_wording",
            )
        )
        if not all(triple):
            error(
                "prompt_sensitivity_factors_missing",
                "every prompt sensitivity variant must freeze all factors",
            )
        factor_triples.add(triple)
        if item.get("analysis_role") != "descriptive_sensitivity_only":
            error(
                "prompt_sensitivity_role_invalid",
                "prompt variants cannot become unadjusted primary tests",
            )
    if len(factor_triples) < 2:
        error(
            "prompt_sensitivity_no_contrast",
            "prompt sensitivity variants must differ in a declared factor",
        )
    if len(primary_variants) != 1:
        error(
            "prompt_sensitivity_primary_anchor_invalid",
            "exactly one prompt sensitivity variant must anchor the primary zero-shot prompt",
        )
    elif ZERO_SHOT_ARM in by_arm:
        primary = primary_variants[0]
        zero = by_arm[ZERO_SHOT_ARM]
        if (
            primary.get("prompt", {}).get("sha256")
            != zero.get("prompt", {}).get("sha256")
            or primary.get("paper_factorization")
            != zero.get("paper_factorization")
        ):
            error(
                "prompt_sensitivity_primary_anchor_mismatch",
                "primary prompt sensitivity variant must match the frozen zero-shot prompt and factorization",
            )


def _check_demonstrations(
    config: Mapping[str, Any],
    *,
    packets: Mapping[str, Any],
    semantic_gold_approval: Mapping[str, Any],
    semantic_gold_approval_path: Path,
    packet_manifest_path: Path,
    study_root: Path,
    local_only: bool,
    error,
) -> None:
    contract = config.get("demonstration_contract")
    if not isinstance(contract, dict):
        error(
            "demonstration_contract_missing",
            "demonstration contract is required",
        )
        return
    if (
        contract.get("candidate_pool_split") != "development_only"
        or contract.get("validation_or_test_as_demonstration") is not False
        or contract.get("target_gold_or_model_outcomes_used_for_ranking")
        is not False
        or contract.get("tie_breaker") != "case_id_ascending"
        or contract.get("one_shot_count") != 1
        or contract.get("five_shot_count") != 5
    ):
        error(
            "demonstration_policy_invalid",
            "demonstrations must use the frozen development-only policy",
        )
    try:
        pool_path = _bound_path(
            contract.get("candidate_pool_manifest"),
            study_root=study_root,
            label="demonstration candidate pool",
        )
        ranking_path = _bound_path(
            contract.get("ranking_implementation"),
            study_root=study_root,
            label="demonstration ranking implementation",
        )
        del ranking_path
        pool = _load_json(pool_path)
        pool_validation = verify_demonstration_pool(
            pool,
            semantic_gold_approval_path=semantic_gold_approval_path,
            packet_manifest_path=packet_manifest_path,
            study_root=study_root,
        )
    except Exception as exc:  # noqa: BLE001
        error("demonstration_binding_invalid", str(exc))
        return
    if pool_validation.get("status") != "passed":
        error(
            "demonstration_pool_replay_failed",
            "demonstration pool was not generated from the bound "
            "development packets and approved consensus gold",
        )
    if (
        pool.get("schema_version") != "ndp50-demonstration-pool/v2"
        or pool.get("status") != "validator_generated_development_only"
        or pool.get("source_split") != "development"
        or pool.get("candidate_inclusion_policy")
        != "all_approved_development_cases"
        or pool.get("model_outputs_used_for_inclusion") is not False
        or pool.get("validation_or_test_candidates_included") is not False
    ):
        error(
            "demonstration_pool_invalid",
            "demonstration pool policy is invalid",
        )
    development_ids = {
        str(item["case_id"])
        for item in packets["cases"]
        if item["split"] == "development"
    }
    gold_cases = {
        str(item["case_id"]): item
        for item in semantic_gold_approval.get("index", {}).get("cases", [])
    }
    pool_cases = pool.get("cases")
    if not isinstance(pool_cases, list) or len(pool_cases) < 5:
        error(
            "demonstration_pool_too_small",
            "at least five development demonstrations are required",
        )
        pool_cases = []
    seen = set()
    for item in pool_cases:
        if not isinstance(item, dict):
            error(
                "demonstration_pool_item_invalid",
                "pool case must be an object",
            )
            continue
        case_id = str(item.get("case_id") or "")
        if not case_id or case_id in seen or case_id not in development_ids:
            error(
                "demonstration_case_invalid",
                "pool cases must be unique development cases",
            )
            continue
        seen.add(case_id)
        gold_case = gold_cases.get(case_id)
        if (
            gold_case is None
            or item.get("gold_consensus") != gold_case.get("consensus")
        ):
            error(
                "demonstration_gold_binding_mismatch",
                f"{case_id} does not bind approved development gold",
            )
        if (
            not isinstance(item.get("input_projection"), dict)
            or not isinstance(item.get("gold_projection"), dict)
        ):
            error(
                "demonstration_projection_missing",
                f"{case_id} lacks canonical input or gold projection",
            )
    method = contract.get("selection_method")
    similarity = contract.get("similarity_model")
    if method not in {"deterministic_lexical", "frozen_embedding_cosine"}:
        error(
            "demonstration_selection_method_invalid",
            "selection method must be deterministic lexical or frozen cosine",
        )
    if method == "frozen_embedding_cosine":
        if not isinstance(similarity, dict) or not all(
            _valid_text(similarity.get(key))
            for key in ("model_identifier", "runtime", "runtime_version")
        ):
            error(
                "similarity_model_identity_missing",
                "embedding similarity requires exact model/runtime identity",
            )
        elif not isinstance(similarity.get("checkpoint_sha256"), str) or len(
            similarity["checkpoint_sha256"]
        ) != 64:
            error(
                "similarity_checkpoint_hash_invalid",
                "embedding checkpoint SHA-256 is required",
            )
        if similarity.get("metric") != "cosine":
            error(
                "similarity_metric_invalid",
                "embedding ranking metric must be cosine",
            )
        if similarity.get("normalization") not in {"l2", "none"}:
            error(
                "similarity_normalization_invalid",
                "embedding normalization must be frozen",
            )
        if local_only and similarity.get("external_service_used") is not False:
            error(
                "local_policy_similarity_transfer",
                "local-only governance forbids external embedding transfer",
            )
    elif similarity not in (None, {}):
        error(
            "lexical_similarity_model_present",
            "deterministic lexical ranking cannot bind an embedding model",
        )


def validate_config(
    config: Mapping[str, Any],
    *,
    cpa_design_path: Path,
    packet_manifest_path: Path,
    vocabulary_path: Path,
    approved_source_manifest_path: Path,
    cpa_consensus_path: Path,
    semantic_gold_approval_path: Path,
    data_governance_audit_path: Path,
    data_governance_approval_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    errors: list[Dict[str, str]] = []

    def error(code: str, detail: str) -> None:
        errors.append({"code": code, "detail": detail})

    try:
        design, packets = _inputs(cpa_design_path, packet_manifest_path)
        vocabulary = _load_json(vocabulary_path)
        if validate_vocabulary(vocabulary).get("status") != "ready":
            error("vocabulary_invalid", "frozen vocabulary did not validate")
        load_approved_evidence_registry(approved_source_manifest_path)
        cpa_consensus = _load_json(cpa_consensus_path)
        if (
            cpa_consensus.get("schema_version")
            != "ndp50-cpa-applicability-consensus/v1"
        ):
            error("cpa_consensus_invalid", "unexpected CPA consensus schema")
        governance = _load_json(data_governance_approval_path)
        governance_validation = verify_governance_approval(
            governance,
            audit_path=data_governance_audit_path,
            study_root=study_root,
        )
        if governance_validation.get("status") != "passed":
            error(
                "governance_approval_invalid",
                "data-governance approval did not replay",
            )
        semantic_gold = _load_json(semantic_gold_approval_path)
        gold_validation = verify_gold_approval(
            semantic_gold,
            packet_manifest_path=packet_manifest_path,
            approved_source_manifest_path=approved_source_manifest_path,
            vocabulary_path=vocabulary_path,
            study_root=study_root,
        )
        if gold_validation.get("status") != "passed":
            error(
                "semantic_gold_approval_invalid",
                "semantic-gold approval did not replay",
            )
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": VALIDATION_SCHEMA_VERSION,
            "status": "blocked",
            "errors": [{"code": "upstream_invalid", "detail": str(exc)}],
        }

    if config.get("schema_version") != CONFIG_SCHEMA_VERSION:
        error("config_schema_invalid", "unexpected execution config schema")
    if config.get("status") != "completed_pending_validator_freeze":
        error(
            "config_status_invalid",
            "completed config must await validator freeze",
        )
    if config.get("human_decisions_present") is not True:
        error(
            "human_decisions_missing",
            "completed configuration must acknowledge research decisions",
        )
    if config.get("model_or_gold_outcomes_observed_before_freeze") is not False:
        error(
            "outcome_blinding_violated",
            "model and gold outcomes cannot be observed before freeze",
        )
    if config.get("cpa_design") != _binding(cpa_design_path, study_root):
        error("cpa_design_binding_mismatch", "CPA design binding changed")
    if config.get("packet_manifest") != _binding(
        packet_manifest_path, study_root
    ):
        error("packet_binding_mismatch", "packet manifest binding changed")
    expected_upstream = {
        "frozen_vocabulary": _binding(vocabulary_path, study_root),
        "approved_source_manifest": _binding(
            approved_source_manifest_path, study_root
        ),
        "cpa_consensus": _binding(cpa_consensus_path, study_root),
        "semantic_gold_approval": _binding(
            semantic_gold_approval_path, study_root
        ),
        "data_governance_audit": _binding(
            data_governance_audit_path, study_root
        ),
        "data_governance_approval": _binding(
            data_governance_approval_path, study_root
        ),
    }
    if config.get("upstream_bindings") != expected_upstream:
        error("upstream_binding_mismatch", "upstream bindings changed")
    _check_signoffs(config, error)

    if config.get("planned_arms") != design["planned_arms"]:
        error("planned_arms_changed", "planned arms differ from CPA design")
    analysis = config.get("analysis_contract")
    if not isinstance(analysis, dict):
        analysis = {}
        error("analysis_contract_missing", "analysis contract is required")
    contrasts = analysis.get("primary_contrasts")
    valid_arm_ids = set(design["planned_arms"])
    contrast_ids = set()
    if not isinstance(contrasts, list) or len(contrasts) != 2:
        error(
            "primary_contrasts_missing",
            "exactly two co-primary contrasts must be frozen",
        )
        if not isinstance(contrasts, list):
            contrasts = []
    for item in contrasts:
        if not isinstance(item, dict):
            error("primary_contrast_invalid", "contrast must be an object")
            continue
        contrast_id = str(item.get("contrast_id") or "")
        if not contrast_id or contrast_id in contrast_ids:
            error(
                "primary_contrast_id_invalid",
                "contrast ids must be unique and non-empty",
            )
        contrast_ids.add(contrast_id)
        if (
            item.get("arm_a") not in valid_arm_ids
            or item.get("arm_b") not in valid_arm_ids
            or item.get("arm_a") == item.get("arm_b")
        ):
            error(
                "primary_contrast_arms_invalid",
                "contrast arms must be distinct registered arms",
            )
    expected_analysis = {
        **deepcopy(design["analysis"]),
        "metric_contract_sha256": _sha256_json(
            design["metric_contract"]
        ),
        "prompt_variants_role": "descriptive_sensitivity_only",
        "row_sampling_variants_role": "descriptive_sensitivity_only",
        "fine_tuning_in_primary_study": False,
    }
    for key, expected in expected_analysis.items():
        if analysis.get(key) != expected:
            error(
                "analysis_contract_changed",
                f"analysis_contract.{key} differs from registered design",
            )
    _check_prompt_contracts(config, study_root=study_root, error=error)
    _check_confidence_reporting(config, error=error)

    reuse = config.get("response_reuse_contract") or {}
    if reuse != {
        "source_arm": "zero_shot_dataset_level",
        "consumer_arm": REPLAY_ARM,
        "byte_identical_response_required": True,
        "additional_physical_model_calls": 0,
    }:
        error(
            "response_reuse_contract_invalid",
            "verification arm must consume the byte-identical zero-shot response",
        )
    serialization = config.get("serialization_contract")
    if not isinstance(serialization, dict):
        serialization = {}
        error(
            "serialization_contract_missing",
            "serialization contract is required",
        )
    if serialization.get("table_format") not in {
        "markdown",
        "json_records",
        "csv_text",
    }:
        error("table_format_invalid", "table format must be frozen")
    for key in (
        "column_order_policy",
        "row_order_policy",
        "missing_value_rendering",
        "missing_display_cell_fill_policy",
        "value_escaping_policy",
        "truncation_marker",
    ):
        if not _valid_text(serialization.get(key)):
            error(
                "serialization_slot_missing",
                f"serialization_contract.{key} must be non-empty",
            )
    if (
        not isinstance(serialization.get("max_cell_characters"), int)
        or isinstance(serialization.get("max_cell_characters"), bool)
        or serialization["max_cell_characters"] <= 0
    ):
        error(
            "serialization_limit_invalid",
            "max_cell_characters must be positive",
        )
    metadata_fields = serialization.get("metadata_fields")
    if not isinstance(metadata_fields, list):
        error(
            "serialization_metadata_invalid",
            "metadata_fields must be an explicit list",
        )

    row_contract = config.get("row_sampling_contract") or {}
    primary_sampler = row_contract.get("primary_sampler_id")
    required_samplers = list(design["row_sampling_sensitivity"])
    if primary_sampler not in required_samplers:
        error(
            "primary_sampler_invalid",
            "primary sampler must be a registered row sampler",
        )
    sampler_items = row_contract.get("sensitivity_samplers")
    if not isinstance(sampler_items, list):
        sampler_items = []
        error(
            "row_sampler_contracts_missing",
            "all row sampler contracts are required",
        )
    sampler_by_id = {
        str(item.get("sampler_id") or ""): item
        for item in sampler_items
        if isinstance(item, dict)
    }
    if (
        len(sampler_by_id) != len(sampler_items)
        or set(sampler_by_id) != set(required_samplers)
    ):
        error(
            "row_sampler_coverage_invalid",
            "row sampler contracts must exactly cover the design",
        )
    for sampler_id, item in sampler_by_id.items():
        try:
            _bound_path(
                item.get("implementation"),
                study_root=study_root,
                label=f"{sampler_id} implementation",
            )
        except Exception as exc:  # noqa: BLE001
            error("row_sampler_binding_invalid", str(exc))
        seed = item.get("seed")
        if sampler_id == "head":
            if seed is not None:
                error(
                    "head_sampler_seed_invalid",
                    "head sampler seed must be null",
                )
        elif not isinstance(seed, int) or isinstance(seed, bool):
            error(
                "row_sampler_seed_invalid",
                f"{sampler_id} requires an integer seed",
            )
        if not isinstance(item.get("parameters"), dict):
            error(
                "row_sampler_parameters_missing",
                f"{sampler_id} parameters must be frozen",
            )

    governance_review = governance.get("review", {})
    local_only = (
        governance_review.get("study_policy", {}).get(
            "model_processing_mode"
        )
        == "local_only"
    )
    _check_demonstrations(
        config,
        packets=packets,
        semantic_gold_approval=semantic_gold,
        semantic_gold_approval_path=semantic_gold_approval_path,
        packet_manifest_path=packet_manifest_path,
        study_root=study_root,
        local_only=local_only,
        error=error,
    )

    backend = config.get("backend_contract")
    if not isinstance(backend, dict):
        backend = {}
        error("backend_contract_missing", "backend contract is required")
    try:
        registry_path = _bound_path(
            backend.get("registry"),
            study_root=study_root,
            label="backend registry",
        )
        registry = _load_json(registry_path)
        backend_validation = preflight_backend_registry(registry_path)
        if backend_validation.get("status") != "ready":
            error(
                "backend_registry_not_ready",
                "backend registry did not pass operational preflight",
            )
    except Exception as exc:  # noqa: BLE001
        registry = {}
        error("backend_registry_invalid", str(exc))
    primary_backend_id = backend.get("primary_backend_id")
    if (
        primary_backend_id != registry.get("primary_backend_id")
        or primary_backend_id
        not in {
            item.get("backend_id")
            for item in registry.get("backends") or []
            if isinstance(item, dict)
        }
    ):
        error(
            "primary_backend_invalid",
            "primary backend must match the qualified registry",
        )
    if (
        backend.get("temperature") != 0
        or not isinstance(backend.get("seed"), int)
        or isinstance(backend.get("seed"), bool)
        or not isinstance(backend.get("max_tokens"), int)
        or isinstance(backend.get("max_tokens"), bool)
        or int(backend.get("max_tokens") or 0) <= 0
        or backend.get("thinking_enabled") is not False
        or backend.get("selection_uses_semantic_accuracy") is not False
    ):
        error(
            "backend_decoding_invalid",
            "backend decoding and accuracy-independent selection are not frozen",
        )
    if not isinstance(backend.get("external_service_used"), bool):
        error(
            "backend_transfer_declaration_missing",
            "external service use must be declared",
        )
    if local_only and backend.get("external_service_used") is not False:
        error(
            "local_policy_backend_transfer",
            "local-only governance forbids external backend transfer",
        )
    if local_only:
        selected = next(
            (
                item
                for item in registry.get("backends") or []
                if item.get("backend_id") == primary_backend_id
            ),
            {},
        )
        if selected and not _is_loopback_url(selected.get("endpoint")):
            error(
                "local_policy_backend_endpoint",
                "local-only backend endpoint must be loopback",
            )
    _check_resource_accounting(config, error=error)

    implementations = config.get("execution_implementations")
    if not isinstance(implementations, dict) or set(
        implementations
    ) != IMPLEMENTATION_SLOTS:
        error(
            "execution_implementation_coverage",
            "all execution implementation slots must be bound",
        )
    qualification = config.get("execution_qualification")
    if not isinstance(qualification, dict) or set(qualification) != {
        "declaration",
        "receipt",
    }:
        error(
            "execution_qualification_missing",
            "implementation declaration and qualification receipt are required",
        )
    else:
        try:
            declaration_path = _bound_path(
                qualification.get("declaration"),
                study_root=study_root,
                label="execution implementation declaration",
            )
            receipt_path = _bound_path(
                qualification.get("receipt"),
                study_root=study_root,
                label="execution implementation qualification receipt",
            )
            declaration = _load_json(declaration_path)
            receipt = _load_json(receipt_path)
            replay = verify_qualification_receipt(
                receipt,
                declaration_path=declaration_path,
                study_root=study_root,
            )
            if replay.get("status") != "passed":
                raise NDPExecutionFreezeError(
                    "execution implementation qualification did not replay"
                )
            if implementations != declaration.get("implementations"):
                error(
                    "execution_implementation_declaration_mismatch",
                    "config implementations differ from the qualified declaration",
                )
            declared = declaration.get("implementations") or {}
            qualified_row_sampler = (
                declared.get("row_sampler", {}).get("artifact")
            )
            for item in row_contract.get("sensitivity_samplers") or []:
                if item.get("implementation") != qualified_row_sampler:
                    error(
                        "qualified_component_binding_mismatch",
                        "row-sampler contract does not use the qualified artifact",
                    )
                    break
            qualified_ranker = (
                declared.get("demonstration_ranker", {}).get("artifact")
            )
            if (
                (config.get("demonstration_contract") or {}).get(
                    "ranking_implementation"
                )
                != qualified_ranker
            ):
                error(
                    "qualified_component_binding_mismatch",
                    "demonstration contract does not use the qualified ranker",
                )
        except Exception as exc:  # noqa: BLE001
            error("execution_qualification_invalid", str(exc))

    order = config.get("execution_order")
    if not isinstance(order, dict):
        order = {}
        error("execution_order_missing", "execution order is required")
    if order.get("case_order_policy") not in {
        "case_id_ascending",
        "fixed_seed_hash_rank",
    }:
        error("case_order_policy_invalid", "case order policy is invalid")
    if order.get("case_order_policy") == "fixed_seed_hash_rank" and (
        not isinstance(order.get("case_order_seed"), int)
        or isinstance(order.get("case_order_seed"), bool)
    ):
        error("case_order_seed_invalid", "shuffle requires an integer seed")
    if order.get("case_order_policy") == "case_id_ascending" and order.get(
        "case_order_seed"
    ) is not None:
        error(
            "case_order_seed_unexpected",
            "ascending order must not declare a seed",
        )
    if (
        order.get("arm_interleaving_policy")
        != "case_major_seeded_cyclic_execution_blocks"
    ):
        error(
            "arm_interleaving_policy_invalid",
            "arm interleaving must use seeded cyclic execution blocks",
        )
    if (
        not isinstance(order.get("arm_order_seed"), int)
        or isinstance(order.get("arm_order_seed"), bool)
    ):
        error(
            "arm_order_seed_invalid",
            "cyclic execution blocks require an integer arm-order seed",
        )
    if not _valid_text(order.get("retry_policy")):
        error(
            "execution_order_slot_missing",
            "retry_policy must be non-empty",
        )
    for key in ("request_timeout_seconds", "maximum_attempts_per_call"):
        value = order.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            error("execution_limit_invalid", f"{key} must be positive")
    if config.get("completion_attestation") is not True:
        error(
            "completion_not_attested",
            "execution configuration completion must be attested",
        )

    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "status": "passed" if not errors else "blocked",
        "error_count": len(errors),
        "errors": errors,
    }


def build_freeze(
    *,
    config: Mapping[str, Any],
    cpa_design_path: Path,
    packet_manifest_path: Path,
    vocabulary_path: Path,
    approved_source_manifest_path: Path,
    cpa_consensus_path: Path,
    semantic_gold_approval_path: Path,
    data_governance_audit_path: Path,
    data_governance_approval_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    validation = validate_config(
        config,
        cpa_design_path=cpa_design_path,
        packet_manifest_path=packet_manifest_path,
        vocabulary_path=vocabulary_path,
        approved_source_manifest_path=approved_source_manifest_path,
        cpa_consensus_path=cpa_consensus_path,
        semantic_gold_approval_path=semantic_gold_approval_path,
        data_governance_audit_path=data_governance_audit_path,
        data_governance_approval_path=data_governance_approval_path,
        study_root=study_root,
    )
    if validation["status"] != "passed":
        raise NDPExecutionFreezeError(
            "execution configuration is incomplete: "
            + json.dumps(validation["errors"], sort_keys=True)
        )
    implementation = Path(__file__).resolve()
    canonical = json.dumps(
        config,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "schema_version": FREEZE_SCHEMA_VERSION,
        "status": "frozen_ready_for_power_calibration",
        "config": config,
        "config_content_sha256": hashlib.sha256(canonical).hexdigest(),
        "validation": validation,
        "derived_gates": {"prompt_and_backend_frozen": True},
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            name: _sha256_file(implementation.with_name(name))
            for name in (
                "ndp50_data_governance_review.py",
                "ndp50_demonstration_pool.py",
                "ndp50_execution_qualification.py",
                "ndp50_semantic_gold.py",
                "ndp50_source_approval.py",
                "semantic_gold_workflow.py",
                "semantic_study_preflight.py",
            )
        },
    }


def verify_freeze(
    freeze: Mapping[str, Any],
    *,
    cpa_design_path: Path,
    packet_manifest_path: Path,
    vocabulary_path: Path,
    approved_source_manifest_path: Path,
    cpa_consensus_path: Path,
    semantic_gold_approval_path: Path,
    data_governance_audit_path: Path,
    data_governance_approval_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    config = freeze.get("config")
    if not isinstance(config, dict):
        return {
            "schema_version": FREEZE_VALIDATION_SCHEMA_VERSION,
            "status": "failed",
            "differing_top_level_keys": ["config"],
        }
    try:
        expected = build_freeze(
            config=config,
            cpa_design_path=cpa_design_path,
            packet_manifest_path=packet_manifest_path,
            vocabulary_path=vocabulary_path,
            approved_source_manifest_path=approved_source_manifest_path,
            cpa_consensus_path=cpa_consensus_path,
            semantic_gold_approval_path=semantic_gold_approval_path,
            data_governance_audit_path=data_governance_audit_path,
            data_governance_approval_path=data_governance_approval_path,
            study_root=study_root,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": FREEZE_VALIDATION_SCHEMA_VERSION,
            "status": "failed",
            "differing_top_level_keys": ["config"],
            "detail": str(exc),
        }
    differing = sorted(
        key
        for key in set(freeze) | set(expected)
        if freeze.get(key) != expected.get(key)
    )
    return {
        "schema_version": FREEZE_VALIDATION_SCHEMA_VERSION,
        "status": "passed" if not differing else "failed",
        "differing_top_level_keys": differing,
    }


def _add_freeze_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cpa-design", type=Path, required=True)
    parser.add_argument("--packet-manifest", type=Path, required=True)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument(
        "--approved-source-manifest", type=Path, required=True
    )
    parser.add_argument("--cpa-consensus", type=Path, required=True)
    parser.add_argument(
        "--semantic-gold-approval", type=Path, required=True
    )
    parser.add_argument(
        "--data-governance-audit", type=Path, required=True
    )
    parser.add_argument(
        "--data-governance-approval", type=Path, required=True
    )
    parser.add_argument("--study-root", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare and validate the NDP-50 execution freeze."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--cpa-design", type=Path, required=True)
    prepare.add_argument("--packet-manifest", type=Path, required=True)
    prepare.add_argument("--study-root", type=Path, required=True)
    prepare.add_argument("--config-output", type=Path, required=True)
    prepare.add_argument("--workflow-output", type=Path, required=True)
    validate = subparsers.add_parser("validate-config")
    _add_freeze_inputs(validate)
    validate.add_argument("--output", type=Path, required=True)
    freeze = subparsers.add_parser("freeze")
    _add_freeze_inputs(freeze)
    freeze.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify-frozen")
    verify.add_argument("--frozen", type=Path, required=True)
    verify.add_argument("--cpa-design", type=Path, required=True)
    verify.add_argument("--packet-manifest", type=Path, required=True)
    verify.add_argument("--vocabulary", type=Path, required=True)
    verify.add_argument(
        "--approved-source-manifest", type=Path, required=True
    )
    verify.add_argument("--cpa-consensus", type=Path, required=True)
    verify.add_argument(
        "--semantic-gold-approval", type=Path, required=True
    )
    verify.add_argument(
        "--data-governance-audit", type=Path, required=True
    )
    verify.add_argument(
        "--data-governance-approval", type=Path, required=True
    )
    verify.add_argument("--study-root", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        config = build_config_template(
            cpa_design_path=args.cpa_design,
            packet_manifest_path=args.packet_manifest,
            study_root=args.study_root,
        )
        _write_json(args.config_output, config)
        workflow = build_workflow_spec(
            cpa_design_path=args.cpa_design,
            packet_manifest_path=args.packet_manifest,
            config_template_path=args.config_output,
            study_root=args.study_root,
        )
        _write_json(args.workflow_output, workflow)
        print(
            json.dumps(
                {
                    "status": workflow["status"],
                    "planned_arm_count": len(config["planned_arms"]),
                    "row_sampler_count": len(
                        config["row_sampling_contract"][
                            "sensitivity_samplers"
                        ]
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    kwargs = {
        "cpa_design_path": args.cpa_design,
        "packet_manifest_path": args.packet_manifest,
        "vocabulary_path": args.vocabulary,
        "approved_source_manifest_path": args.approved_source_manifest,
        "cpa_consensus_path": args.cpa_consensus,
        "semantic_gold_approval_path": args.semantic_gold_approval,
        "data_governance_audit_path": args.data_governance_audit,
        "data_governance_approval_path": args.data_governance_approval,
        "study_root": args.study_root,
    }
    if args.command == "validate-config":
        payload = validate_config(_load_json(args.config), **kwargs)
        _write_json(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] == "passed" else 1
    if args.command == "freeze":
        payload = build_freeze(config=_load_json(args.config), **kwargs)
        _write_json(args.output, payload)
        print(json.dumps(payload["derived_gates"], indent=2, sort_keys=True))
        return 0
    payload = verify_freeze(_load_json(args.frozen), **kwargs)
    _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
