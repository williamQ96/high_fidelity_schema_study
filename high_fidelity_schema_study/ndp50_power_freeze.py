from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
import statistics
from datetime import date
from pathlib import Path
from typing import Any, Dict, Mapping

from .ndp50_cpa_design import (
    PRIMARY_OUTCOME_ID,
    registered_analysis_contract,
    registered_metric_contract,
)
from .semantic_power_analysis import (
    paired_t_power,
    required_paired_sample_size,
    required_total_dataset_count,
)


POLICY_SCHEMA_VERSION = "ndp50-power-policy/v1"
WORKFLOW_SCHEMA_VERSION = "ndp50-power-freeze-workflow/v1"
CALIBRATION_SCHEMA_VERSION = "ndp50-development-calibration-report/v1"
FREEZE_SCHEMA_VERSION = "ndp50-power-freeze/v1"
POLICY_VALIDATION_SCHEMA_VERSION = "ndp50-power-policy-validation/v1"
FREEZE_REPLAY_SCHEMA_VERSION = "ndp50-power-freeze-replay/v1"
PRIMARY_OUTCOME = PRIMARY_OUTCOME_ID
FAMILYWISE_ALPHA = 0.05
METHOD = (
    "two-sided paired-t planning approximation with development-calibrated "
    "dataset-level paired-difference SD, prespecified SD inflation, "
    "Holm worst-case alpha allocation, and binomial opportunity assurance"
)


class NDPPowerFreezeError(ValueError):
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


def _study_relative(path: Path, study_root: Path) -> str:
    try:
        return path.resolve().relative_to(study_root.resolve()).as_posix()
    except ValueError as exc:
        raise NDPPowerFreezeError(
            f"artifact must be inside the study root: {path}"
        ) from exc


def _binding(path: Path, study_root: Path) -> Dict[str, str]:
    if not path.is_file():
        raise NDPPowerFreezeError(f"artifact does not exist: {path}")
    return {
        "file": _study_relative(path, study_root),
        "sha256": _sha256_file(path),
    }


def _valid_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_date(value: Any) -> bool:
    try:
        date.fromisoformat(str(value or ""))
    except ValueError:
        return False
    return True


def _number(
    payload: Mapping[str, Any],
    key: str,
    *,
    minimum: float,
    maximum: float,
    minimum_inclusive: bool = True,
    maximum_inclusive: bool = True,
) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise NDPPowerFreezeError(f"{key} must be numeric")
    result = float(value)
    lower = result >= minimum if minimum_inclusive else result > minimum
    upper = result <= maximum if maximum_inclusive else result < maximum
    if not lower or not upper:
        raise NDPPowerFreezeError(
            f"{key} is outside the registered bounds"
        )
    return result


def _inputs(
    *,
    selection_path: Path,
    opportunity_manifest_path: Path,
    cpa_design_path: Path,
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    selection = _load_json(selection_path)
    opportunity = _load_json(opportunity_manifest_path)
    design = _load_json(cpa_design_path)
    selected = selection.get("selected_datasets")
    if not isinstance(selected, list) or not selected:
        raise NDPPowerFreezeError("selection has no datasets")
    counts = {
        split: sum(item.get("split") == split for item in selected)
        for split in ("development", "validation", "test")
    }
    if (
        counts != {"development": 15, "validation": 10, "test": 25}
        or selection.get("counts", {}).get("split_counts") != counts
        or selection.get("counts", {}).get("selected_dataset_count") != 50
    ):
        raise NDPPowerFreezeError(
            "power workflow requires the frozen 15/10/25 NDP selection"
        )
    selected_ids = [str(item.get("dataset_id") or "") for item in selected]
    if any(not value for value in selected_ids) or len(selected_ids) != len(
        set(selected_ids)
    ):
        raise NDPPowerFreezeError("selection dataset identities are invalid")
    if (
        opportunity.get("schema_version")
        != "ndp50-semantic-opportunity-manifest/v1"
    ):
        raise NDPPowerFreezeError("unexpected opportunity manifest schema")
    cases = opportunity.get("cases")
    if not isinstance(cases, list) or not cases:
        raise NDPPowerFreezeError("opportunity manifest has no cases")
    if any(
        item.get("split") not in {"development", "validation"}
        for item in cases
    ):
        raise NDPPowerFreezeError(
            "power preparation cannot contain test cases"
        )
    if design.get("schema_version") != "ndp50-cpa-design/v1":
        raise NDPPowerFreezeError("unexpected CPA design schema")
    if (
        design.get("analysis") != registered_analysis_contract()
        or design.get("metric_contract") != registered_metric_contract()
    ):
        raise NDPPowerFreezeError("CPA analysis contract is incompatible")
    return selection, opportunity, design


def build_policy_template(
    *,
    selection_path: Path,
    opportunity_manifest_path: Path,
    cpa_design_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    _, _, design = _inputs(
        selection_path=selection_path,
        opportunity_manifest_path=opportunity_manifest_path,
        cpa_design_path=cpa_design_path,
    )
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "status": "neutral_pending_precalibration_policy",
        "human_decisions_present": False,
        "calibration_outcomes_observed_before_policy_signoff": False,
        "selection": _binding(selection_path, study_root),
        "opportunity_manifest": _binding(
            opportunity_manifest_path, study_root
        ),
        "cpa_design": _binding(cpa_design_path, study_root),
        "execution_freeze": None,
        "primary_statistical_unit": "dataset",
        "primary_outcome": PRIMARY_OUTCOME,
        "primary_contrasts": deepcopy(
            design["analysis"]["primary_contrasts"]
        ),
        "familywise_alpha": FAMILYWISE_ALPHA,
        "multiplicity_policy": (
            "holm_fwer_with_bonferroni_worst_case_power_planning"
        ),
        "minimum_meaningful_effect": None,
        "minimum_meaningful_effect_rationale": None,
        "target_power": None,
        "selective_risk_bound": None,
        "planning_sd_inflation": None,
        "sd_floor": None,
        "opportunity_count_assurance": None,
        "sensitivity_sd_multipliers": [],
        "planning_method_scope": (
            "sample_size_planning_approximation_not_primary_test_definition"
        ),
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
                "slot": "independent_methods_reviewer",
                "signatory_id": None,
                "role": None,
                "institution": None,
                "qualification_summary": None,
                "conflict_of_interest_declared": None,
                "developer_participation": False,
                "signed_on": None,
            },
        ],
        "completion_attestation": None,
    }


def build_workflow_spec(
    *,
    selection_path: Path,
    opportunity_manifest_path: Path,
    cpa_design_path: Path,
    policy_template_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    expected = build_policy_template(
        selection_path=selection_path,
        opportunity_manifest_path=opportunity_manifest_path,
        cpa_design_path=cpa_design_path,
        study_root=study_root,
    )
    if _load_json(policy_template_path) != expected:
        raise NDPPowerFreezeError(
            "power policy is not the canonical neutral template"
        )
    implementation = Path(__file__).resolve()
    return {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "status": "implementation_ready_waiting_on_execution_freeze",
        "human_decisions_present": False,
        "test_outcomes_observed": False,
        "selection": _binding(selection_path, study_root),
        "opportunity_manifest": _binding(
            opportunity_manifest_path, study_root
        ),
        "cpa_design": _binding(cpa_design_path, study_root),
        "neutral_policy_template": _binding(
            policy_template_path, study_root
        ),
        "sequence": [
            "complete_and_replay_execution_freeze",
            "complete_power_policy_without_calibration_outcomes",
            "freeze_policy_signatures_and_content_hash",
            "execute_development_only_calibration",
            "validate_equal_weight_dataset_level_effects",
            "derive_inflated_sd_and_opportunity_assurance",
            "validator_generate_power_freeze",
            "rebuild_power_feasibility_readiness_and_handoff",
        ],
        "required_calibration_split": "development_only",
        "validation_or_test_outcomes_forbidden": True,
        "all_development_opportunity_datasets_required": True,
        "primary_statistical_unit": "dataset",
        "familywise_alpha": FAMILYWISE_ALPHA,
        "primary_contrast_count": 2,
        "minimum_sensitivity_scenarios": 3,
        "automatic_policy_decisions": False,
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            "semantic_power_analysis.py": _sha256_file(
                implementation.with_name("semantic_power_analysis.py")
            )
        },
    }


def _execution_contract(
    execution_freeze_path: Path,
) -> tuple[Dict[str, Any], list[Dict[str, str]]]:
    freeze = _load_json(execution_freeze_path)
    if (
        freeze.get("schema_version") != "ndp50-execution-freeze/v1"
        or freeze.get("status") != "frozen_ready_for_power_calibration"
        or freeze.get("derived_gates", {}).get(
            "prompt_and_backend_frozen"
        )
        is not True
    ):
        raise NDPPowerFreezeError(
            "execution freeze is not ready for power calibration"
        )
    contrasts = freeze.get("config", {}).get(
        "analysis_contract", {}
    ).get("primary_contrasts")
    if not isinstance(contrasts, list) or len(contrasts) != 2:
        raise NDPPowerFreezeError(
            "execution freeze must contain two co-primary contrasts"
        )
    normalized = []
    seen: set[str] = set()
    arms = set(freeze.get("config", {}).get("planned_arms") or [])
    for item in contrasts:
        if not isinstance(item, dict):
            raise NDPPowerFreezeError("primary contrast must be an object")
        contrast_id = str(item.get("contrast_id") or "")
        arm_a = str(item.get("arm_a") or "")
        arm_b = str(item.get("arm_b") or "")
        if (
            not contrast_id
            or contrast_id in seen
            or arm_a not in arms
            or arm_b not in arms
            or arm_a == arm_b
        ):
            raise NDPPowerFreezeError(
                "execution-freeze primary contrasts are invalid"
            )
        seen.add(contrast_id)
        normalized.append(
            {
                "contrast_id": contrast_id,
                "arm_a": arm_a,
                "arm_b": arm_b,
            }
        )
    return freeze, normalized


def _validate_signoffs(policy: Mapping[str, Any], error) -> None:
    signoffs = policy.get("signoffs")
    if not isinstance(signoffs, list) or len(signoffs) != 2:
        error("signoffs_invalid", "exactly two signoffs are required")
        return
    by_slot = {
        str(item.get("slot") or ""): item
        for item in signoffs
        if isinstance(item, dict)
    }
    if set(by_slot) != {
        "study_operator",
        "independent_methods_reviewer",
    }:
        error("signoff_slots_invalid", "signoff slots are incomplete")
        return
    identities = []
    for slot, item in by_slot.items():
        for key in (
            "signatory_id",
            "role",
            "institution",
            "qualification_summary",
        ):
            if not _valid_text(item.get(key)):
                error(
                    "signoff_field_missing",
                    f"{slot}.{key} must be non-empty",
                )
        if not isinstance(
            item.get("conflict_of_interest_declared"), bool
        ):
            error(
                "signoff_conflict_missing",
                f"{slot} must declare conflicts",
            )
        if not _valid_date(item.get("signed_on")):
            error("signoff_date_invalid", f"{slot} date is invalid")
        identities.append(str(item.get("signatory_id") or ""))
    if len(set(identities)) != 2:
        error("signatories_not_distinct", "signatories must be distinct")
    reviewer = by_slot["independent_methods_reviewer"]
    if (
        reviewer.get("developer_participation") is not False
        or reviewer.get("role")
        not in {
            "independent_methods_reviewer",
            "research_compliance_reviewer",
            "statistical_methods_reviewer",
        }
    ):
        error(
            "methods_reviewer_not_independent",
            "methods reviewer must be a qualified non-developer",
        )
    if not isinstance(
        by_slot["study_operator"].get("developer_participation"), bool
    ):
        error(
            "operator_participation_undisclosed",
            "study operator must disclose developer participation",
        )


def validate_policy(
    policy: Mapping[str, Any],
    *,
    selection_path: Path,
    opportunity_manifest_path: Path,
    cpa_design_path: Path,
    execution_freeze_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    errors: list[Dict[str, str]] = []

    def error(code: str, detail: str) -> None:
        errors.append({"code": code, "detail": detail})

    try:
        _, _, design = _inputs(
            selection_path=selection_path,
            opportunity_manifest_path=opportunity_manifest_path,
            cpa_design_path=cpa_design_path,
        )
        _, contrasts = _execution_contract(execution_freeze_path)
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": POLICY_VALIDATION_SCHEMA_VERSION,
            "status": "blocked",
            "errors": [{"code": "upstream_invalid", "detail": str(exc)}],
        }
    if contrasts != design["analysis"]["primary_contrasts"]:
        error(
            "execution_primary_contrasts_changed",
            "execution contrasts differ from the registered CPA design",
        )
    if policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        error("policy_schema_invalid", "unexpected policy schema")
    if policy.get("status") != "completed_precalibration_policy":
        error(
            "policy_status_invalid",
            "completed policy must precede calibration",
        )
    if policy.get("human_decisions_present") is not True:
        error("human_decisions_missing", "policy decisions are required")
    if (
        policy.get(
            "calibration_outcomes_observed_before_policy_signoff"
        )
        is not False
    ):
        error(
            "calibration_timing_violated",
            "calibration outcomes cannot precede policy signoff",
        )
    expected_bindings = {
        "selection": _binding(selection_path, study_root),
        "opportunity_manifest": _binding(
            opportunity_manifest_path, study_root
        ),
        "cpa_design": _binding(cpa_design_path, study_root),
        "execution_freeze": _binding(execution_freeze_path, study_root),
    }
    for key, expected in expected_bindings.items():
        if policy.get(key) != expected:
            error("policy_binding_mismatch", f"{key} binding changed")
    if policy.get("primary_statistical_unit") != "dataset":
        error("primary_unit_invalid", "dataset is the primary unit")
    if policy.get("primary_outcome") != PRIMARY_OUTCOME:
        error("primary_outcome_invalid", "primary outcome changed")
    if policy.get("primary_contrasts") != contrasts:
        error(
            "primary_contrasts_changed",
            "contrasts must equal the execution freeze",
        )
    if policy.get("familywise_alpha") != FAMILYWISE_ALPHA:
        error("familywise_alpha_changed", "familywise alpha must be 0.05")
    if policy.get("multiplicity_policy") != (
        "holm_fwer_with_bonferroni_worst_case_power_planning"
    ):
        error("multiplicity_policy_invalid", "Holm planning is required")
    try:
        _number(
            policy,
            "minimum_meaningful_effect",
            minimum=0,
            maximum=1,
            minimum_inclusive=False,
        )
        _number(
            policy,
            "target_power",
            minimum=0,
            maximum=1,
            minimum_inclusive=False,
            maximum_inclusive=False,
        )
        _number(
            policy,
            "selective_risk_bound",
            minimum=0,
            maximum=1,
        )
        inflation = _number(
            policy,
            "planning_sd_inflation",
            minimum=1,
            maximum=3,
            minimum_inclusive=False,
        )
        _number(
            policy,
            "sd_floor",
            minimum=0,
            maximum=1,
            minimum_inclusive=False,
        )
        _number(
            policy,
            "opportunity_count_assurance",
            minimum=0,
            maximum=1,
            minimum_inclusive=False,
            maximum_inclusive=False,
        )
    except Exception as exc:  # noqa: BLE001
        error("numeric_policy_invalid", str(exc))
        inflation = None
    if not _valid_text(policy.get("minimum_meaningful_effect_rationale")):
        error(
            "effect_rationale_missing",
            "minimum meaningful effect requires substantive rationale",
        )
    multipliers = policy.get("sensitivity_sd_multipliers")
    if (
        not isinstance(multipliers, list)
        or len(multipliers) < 3
        or any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not 0.5 <= float(value) <= 3.0
            for value in multipliers
        )
        or multipliers != sorted(set(multipliers))
        or 1.0 not in multipliers
        or inflation not in multipliers
    ):
        error(
            "sensitivity_scenarios_invalid",
            "unique ascending scenarios must include 1.0 and inflation",
        )
    if policy.get("planning_method_scope") != (
        "sample_size_planning_approximation_not_primary_test_definition"
    ):
        error(
            "planning_scope_invalid",
            "planning approximation cannot redefine the primary test",
        )
    _validate_signoffs(policy, error)
    if policy.get("completion_attestation") is not True:
        error(
            "completion_not_attested",
            "policy completion must be attested",
        )
    return {
        "schema_version": POLICY_VALIDATION_SCHEMA_VERSION,
        "status": "passed" if not errors else "blocked",
        "errors": errors,
    }


def _calibration_statistics(
    report: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    selection: Mapping[str, Any],
    opportunity: Mapping[str, Any],
    execution_freeze_path: Path,
    policy_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    if (
        report.get("schema_version") != CALIBRATION_SCHEMA_VERSION
        or report.get("status")
        != "completed_development_only_calibration"
    ):
        raise NDPPowerFreezeError("unexpected calibration report")
    if (
        report.get("source_split") != "development"
        or report.get("validation_outcomes_used") is not False
        or report.get("test_outcomes_used") is not False
        or report.get("gold_used_for_scoring") is not True
        or report.get("primary_statistical_unit") != "dataset"
    ):
        raise NDPPowerFreezeError(
            "calibration report violates the development-only boundary"
        )
    if report.get("execution_freeze") != _binding(
        execution_freeze_path, study_root
    ) or report.get("power_policy") != _binding(policy_path, study_root):
        raise NDPPowerFreezeError(
            "calibration report upstream bindings changed"
        )
    development_selected = {
        str(item["dataset_id"])
        for item in selection["selected_datasets"]
        if item["split"] == "development"
    }
    development_opportunities = {
        str(item["dataset_id"])
        for item in opportunity["cases"]
        if item["split"] == "development"
    }
    if not development_opportunities <= development_selected:
        raise NDPPowerFreezeError(
            "development opportunities are outside the frozen selection"
        )
    contrasts = report.get("contrasts")
    if not isinstance(contrasts, list):
        raise NDPPowerFreezeError("calibration contrasts are missing")
    expected_contrasts = policy["primary_contrasts"]
    by_id = {
        str(item.get("contrast_id") or ""): item
        for item in contrasts
        if isinstance(item, dict)
    }
    expected_ids = {
        str(item["contrast_id"]) for item in expected_contrasts
    }
    if set(by_id) != expected_ids or len(by_id) != len(contrasts):
        raise NDPPowerFreezeError(
            "calibration contrasts differ from the power policy"
        )
    result: Dict[str, Any] = {}
    for expected in expected_contrasts:
        contrast_id = str(expected["contrast_id"])
        item = by_id[contrast_id]
        if (
            item.get("arm_a") != expected["arm_a"]
            or item.get("arm_b") != expected["arm_b"]
        ):
            raise NDPPowerFreezeError(
                f"{contrast_id} arm identities changed"
            )
        rows = item.get("datasets")
        if not isinstance(rows, list):
            raise NDPPowerFreezeError(
                f"{contrast_id} dataset rows are missing"
            )
        row_by_id = {
            str(row.get("dataset_id") or ""): row
            for row in rows
            if isinstance(row, dict)
        }
        if (
            set(row_by_id) != development_opportunities
            or len(row_by_id) != len(rows)
        ):
            raise NDPPowerFreezeError(
                f"{contrast_id} must cover every development "
                "opportunity dataset exactly once"
            )
        effects = []
        normalized_rows = []
        for dataset_id in sorted(development_opportunities):
            row = row_by_id[dataset_id]
            status = row.get("status")
            effect = row.get("paired_rate_effect")
            reasons = row.get("reasons")
            if not isinstance(reasons, list):
                raise NDPPowerFreezeError(
                    f"{contrast_id}/{dataset_id} reasons must be a list"
                )
            if status == "comparable":
                if (
                    not isinstance(effect, (int, float))
                    or isinstance(effect, bool)
                    or not -1 <= float(effect) <= 1
                ):
                    raise NDPPowerFreezeError(
                        f"{contrast_id}/{dataset_id} effect is invalid"
                    )
                value = float(effect)
                effects.append(value)
            elif status == "noncomparable":
                if effect is not None or not reasons:
                    raise NDPPowerFreezeError(
                        f"{contrast_id}/{dataset_id} noncomparability "
                        "requires reasons and a null effect"
                    )
                value = None
            else:
                raise NDPPowerFreezeError(
                    f"{contrast_id}/{dataset_id} status is invalid"
                )
            normalized_rows.append(
                {
                    "dataset_id": dataset_id,
                    "status": status,
                    "paired_rate_effect": value,
                    "reasons": reasons,
                }
            )
        if len(effects) < 2:
            raise NDPPowerFreezeError(
                f"{contrast_id} needs at least two comparable datasets"
            )
        result[contrast_id] = {
            "arm_a": expected["arm_a"],
            "arm_b": expected["arm_b"],
            "opportunity_dataset_count": len(
                development_opportunities
            ),
            "comparable_dataset_count": len(effects),
            "noncomparability_rate": round(
                1 - len(effects) / len(development_opportunities), 8
            ),
            "mean_paired_rate_effect": round(
                statistics.mean(effects), 8
            ),
            "sample_sd_paired_rate_effect": round(
                statistics.stdev(effects), 8
            ),
            "datasets": normalized_rows,
        }
    return {
        "development_selected_dataset_count": len(development_selected),
        "development_opportunity_dataset_count": len(
            development_opportunities
        ),
        "semantic_opportunity_rate": round(
            len(development_opportunities) / len(development_selected), 8
        ),
        "contrasts": result,
    }


def _binomial_probability_at_least(
    total_count: int,
    required_count: int,
    probability: float,
) -> float:
    if required_count <= 0:
        return 1.0
    if required_count > total_count:
        return 0.0
    return min(
        1.0,
        max(
            0.0,
            math.fsum(
                math.comb(total_count, successes)
                * probability**successes
                * (1 - probability) ** (total_count - successes)
                for successes in range(required_count, total_count + 1)
            ),
        ),
    )


def _power_calculation(
    *,
    policy: Mapping[str, Any],
    statistics_payload: Mapping[str, Any],
    maximum_test_dataset_count: int,
) -> Dict[str, Any]:
    alpha_per_contrast = FAMILYWISE_ALPHA / 2
    opportunity_rate = statistics_payload["semantic_opportunity_rate"]
    noncomparability_rate = max(
        item["noncomparability_rate"]
        for item in statistics_payload["contrasts"].values()
    )
    effective_rate = opportunity_rate * (1 - noncomparability_rate)
    if effective_rate <= 0:
        raise NDPPowerFreezeError(
            "development calibration yields no effective scorable rate"
        )
    scenarios = []
    for multiplier in policy["sensitivity_sd_multipliers"]:
        contrast_results = {}
        for contrast_id, item in statistics_payload["contrasts"].items():
            base_sd = max(
                item["sample_sd_paired_rate_effect"],
                float(policy["sd_floor"]),
            )
            scenario_sd = base_sd * float(multiplier)
            if scenario_sd > 1:
                raise NDPPowerFreezeError(
                    f"{contrast_id} sensitivity SD exceeds 1"
                )
            required = required_paired_sample_size(
                minimum_effect=float(
                    policy["minimum_meaningful_effect"]
                ),
                paired_difference_sd=scenario_sd,
                alpha=alpha_per_contrast,
                target_power=float(policy["target_power"]),
            )
            contrast_results[contrast_id] = {
                "calibration_sd": item[
                    "sample_sd_paired_rate_effect"
                ],
                "sd_floor": float(policy["sd_floor"]),
                "planned_sd": round(scenario_sd, 8),
                "required_opportunity_dataset_count": required,
                "achieved_power_at_required_count": round(
                    paired_t_power(
                        required,
                        minimum_effect=float(
                            policy["minimum_meaningful_effect"]
                        ),
                        paired_difference_sd=scenario_sd,
                        alpha=alpha_per_contrast,
                    ),
                    8,
                ),
            }
        required_opportunities = max(
            item["required_opportunity_dataset_count"]
            for item in contrast_results.values()
        )
        required_total = required_total_dataset_count(
            required_opportunity_count=required_opportunities,
            effective_scorable_rate=effective_rate,
            assurance=float(policy["opportunity_count_assurance"]),
            minimum_total_dataset_count=2,
        )
        scenarios.append(
            {
                "sd_multiplier": float(multiplier),
                "contrasts": contrast_results,
                "required_semantic_opportunity_dataset_count": (
                    required_opportunities
                ),
                "required_total_dataset_count": required_total,
                "assurance_at_required_total": round(
                    _binomial_probability_at_least(
                        required_total,
                        required_opportunities,
                        effective_rate,
                    ),
                    8,
                ),
                "assurance_at_frozen_test_count": round(
                    _binomial_probability_at_least(
                        maximum_test_dataset_count,
                        required_opportunities,
                        effective_rate,
                    ),
                    8,
                ),
            }
        )
    planning = next(
        item
        for item in scenarios
        if item["sd_multiplier"]
        == float(policy["planning_sd_inflation"])
    )
    return {
        "method": METHOD,
        "method_scope": policy["planning_method_scope"],
        "familywise_alpha": FAMILYWISE_ALPHA,
        "alpha_per_contrast_for_worst_case_planning": (
            alpha_per_contrast
        ),
        "minimum_meaningful_effect": float(
            policy["minimum_meaningful_effect"]
        ),
        "target_power": float(policy["target_power"]),
        "semantic_opportunity_rate": opportunity_rate,
        "maximum_noncomparability_rate": noncomparability_rate,
        "effective_scorable_rate": round(effective_rate, 8),
        "opportunity_count_assurance": float(
            policy["opportunity_count_assurance"]
        ),
        "maximum_frozen_test_dataset_count": maximum_test_dataset_count,
        "planning_scenario": planning,
        "sensitivity_scenarios": scenarios,
        "frozen_test_count_meets_planning_dataset_requirement": (
            maximum_test_dataset_count
            >= planning["required_total_dataset_count"]
        ),
        "frozen_test_count_meets_requested_opportunity_assurance": (
            planning["assurance_at_frozen_test_count"]
            >= float(policy["opportunity_count_assurance"])
        ),
    }


def build_freeze(
    *,
    policy: Mapping[str, Any],
    policy_path: Path,
    calibration_report_path: Path,
    selection_path: Path,
    opportunity_manifest_path: Path,
    cpa_design_path: Path,
    execution_freeze_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    policy_validation = validate_policy(
        policy,
        selection_path=selection_path,
        opportunity_manifest_path=opportunity_manifest_path,
        cpa_design_path=cpa_design_path,
        execution_freeze_path=execution_freeze_path,
        study_root=study_root,
    )
    if policy_validation["status"] != "passed":
        raise NDPPowerFreezeError(
            "power policy is incomplete: "
            + json.dumps(policy_validation["errors"], sort_keys=True)
        )
    if _load_json(policy_path) != policy:
        raise NDPPowerFreezeError(
            "policy payload differs from the bound policy file"
        )
    selection, opportunity, _ = _inputs(
        selection_path=selection_path,
        opportunity_manifest_path=opportunity_manifest_path,
        cpa_design_path=cpa_design_path,
    )
    report = _load_json(calibration_report_path)
    statistics_payload = _calibration_statistics(
        report,
        policy=policy,
        selection=selection,
        opportunity=opportunity,
        execution_freeze_path=execution_freeze_path,
        policy_path=policy_path,
        study_root=study_root,
    )
    test_count = sum(
        item["split"] == "test"
        for item in selection["selected_datasets"]
    )
    calculation = _power_calculation(
        policy=policy,
        statistics_payload=statistics_payload,
        maximum_test_dataset_count=test_count,
    )
    test_detail_dir = study_root / "acquisition" / "test_details"
    detail_count = (
        len(list(test_detail_dir.glob("*.json.gz")))
        if test_detail_dir.exists()
        else 0
    )
    if detail_count:
        raise NDPPowerFreezeError(
            "test details must remain unopened during power freeze"
        )
    implementation = Path(__file__).resolve()
    return {
        "schema_version": FREEZE_SCHEMA_VERSION,
        "status": "frozen_before_test_semantic_execution",
        "test_outcomes_observed": False,
        "test_detail_snapshot_count": 0,
        "artifact_bindings": {
            "selection": _binding(selection_path, study_root),
            "opportunity_manifest": _binding(
                opportunity_manifest_path, study_root
            ),
            "cpa_design": _binding(cpa_design_path, study_root),
            "execution_freeze": _binding(
                execution_freeze_path, study_root
            ),
            "power_policy": _binding(policy_path, study_root),
            "development_calibration_report": _binding(
                calibration_report_path, study_root
            ),
        },
        "policy": policy,
        "policy_validation": policy_validation,
        "development_calibration_statistics": statistics_payload,
        "power_calculation": calculation,
        "post_test_conditional_rules": [
            "Use dataset clusters as independent units.",
            "Apply Holm adjustment to the two frozen co-primary contrasts.",
            "If the realized comparable-opportunity count is below the frozen requirement, report the test as underpowered.",
            "Do not interpret a null result as evidence of no effect when the frozen requirement is missed.",
            "Do not add datasets or alter contrasts after test outcomes are observed.",
            "The paired-t calculation is a planning approximation and does not redefine the registered primary analysis.",
        ],
        "derived_gates": {
            "test_power_plan_frozen": True,
            "test_design_meets_pretest_assurance": calculation[
                "frozen_test_count_meets_requested_opportunity_assurance"
            ],
        },
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            "semantic_power_analysis.py": _sha256_file(
                implementation.with_name("semantic_power_analysis.py")
            )
        },
    }


def verify_freeze(
    freeze: Mapping[str, Any],
    *,
    policy_path: Path,
    calibration_report_path: Path,
    selection_path: Path,
    opportunity_manifest_path: Path,
    cpa_design_path: Path,
    execution_freeze_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    policy = freeze.get("policy")
    if not isinstance(policy, dict):
        return {
            "schema_version": FREEZE_REPLAY_SCHEMA_VERSION,
            "status": "failed",
            "differing_top_level_keys": ["policy"],
        }
    try:
        expected = build_freeze(
            policy=policy,
            policy_path=policy_path,
            calibration_report_path=calibration_report_path,
            selection_path=selection_path,
            opportunity_manifest_path=opportunity_manifest_path,
            cpa_design_path=cpa_design_path,
            execution_freeze_path=execution_freeze_path,
            study_root=study_root,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": FREEZE_REPLAY_SCHEMA_VERSION,
            "status": "failed",
            "differing_top_level_keys": ["inputs"],
            "detail": str(exc),
        }
    differing = sorted(
        key
        for key in set(freeze) | set(expected)
        if freeze.get(key) != expected.get(key)
    )
    return {
        "schema_version": FREEZE_REPLAY_SCHEMA_VERSION,
        "status": "passed" if not differing else "failed",
        "differing_top_level_keys": differing,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare or replay the NDP-50 pre-test power freeze."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--selection", type=Path, required=True)
    prepare.add_argument("--opportunity-manifest", type=Path, required=True)
    prepare.add_argument("--cpa-design", type=Path, required=True)
    prepare.add_argument("--study-root", type=Path, required=True)
    prepare.add_argument("--policy-output", type=Path, required=True)
    prepare.add_argument("--workflow-output", type=Path, required=True)
    for command in ("validate-policy", "freeze", "verify"):
        item = subparsers.add_parser(command)
        item.add_argument("--policy", type=Path, required=True)
        item.add_argument("--selection", type=Path, required=True)
        item.add_argument(
            "--opportunity-manifest", type=Path, required=True
        )
        item.add_argument("--cpa-design", type=Path, required=True)
        item.add_argument("--execution-freeze", type=Path, required=True)
        item.add_argument("--study-root", type=Path, required=True)
        if command == "validate-policy":
            item.add_argument("--output", type=Path, required=True)
        else:
            item.add_argument(
                "--calibration-report", type=Path, required=True
            )
            if command == "freeze":
                item.add_argument("--output", type=Path, required=True)
            else:
                item.add_argument("--frozen", type=Path, required=True)
                item.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "prepare":
        template = build_policy_template(
            selection_path=args.selection,
            opportunity_manifest_path=args.opportunity_manifest,
            cpa_design_path=args.cpa_design,
            study_root=args.study_root,
        )
        _write_json(args.policy_output, template)
        workflow = build_workflow_spec(
            selection_path=args.selection,
            opportunity_manifest_path=args.opportunity_manifest,
            cpa_design_path=args.cpa_design,
            policy_template_path=args.policy_output,
            study_root=args.study_root,
        )
        _write_json(args.workflow_output, workflow)
        payload = workflow
    elif args.command == "validate-policy":
        payload = validate_policy(
            _load_json(args.policy),
            selection_path=args.selection,
            opportunity_manifest_path=args.opportunity_manifest,
            cpa_design_path=args.cpa_design,
            execution_freeze_path=args.execution_freeze,
            study_root=args.study_root,
        )
        _write_json(args.output, payload)
    elif args.command == "freeze":
        payload = build_freeze(
            policy=_load_json(args.policy),
            policy_path=args.policy,
            calibration_report_path=args.calibration_report,
            selection_path=args.selection,
            opportunity_manifest_path=args.opportunity_manifest,
            cpa_design_path=args.cpa_design,
            execution_freeze_path=args.execution_freeze,
            study_root=args.study_root,
        )
        _write_json(args.output, payload)
    else:
        payload = verify_freeze(
            _load_json(args.frozen),
            policy_path=args.policy,
            calibration_report_path=args.calibration_report,
            selection_path=args.selection,
            opportunity_manifest_path=args.opportunity_manifest,
            cpa_design_path=args.cpa_design,
            execution_freeze_path=args.execution_freeze,
            study_root=args.study_root,
        )
        _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
