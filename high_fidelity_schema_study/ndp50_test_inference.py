from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import random
import statistics
from typing import Any, Dict, Iterable, Mapping, Sequence

from .ndp50_cpa_design import (
    PRIMARY_OUTCOME_ID,
    registered_analysis_contract,
    registered_metric_contract,
)
from .ndp50_test_execution import (
    MISSINGNESS_SCHEMA_VERSION,
    RECEIPT_SCHEMA_VERSION,
    RUN_MANIFEST_SCHEMA_VERSION,
    SCORE_ARTIFACT_SCHEMA_VERSION,
    RESOURCE_USAGE_FLOAT_KEYS,
    RESOURCE_USAGE_INT_KEYS,
    ZERO_SHOT_ARM,
    build_missingness_report,
    verify_run_receipt,
)


RESULT_SCHEMA_VERSION = "ndp50-test-inference/v1"
REPLAY_SCHEMA_VERSION = "ndp50-test-inference-replay/v1"


class NDPTestInferenceError(ValueError):
    pass


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise NDPTestInferenceError(f"JSON root must be an object: {path}")
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


def _study_relative(path: Path, study_root: Path) -> str:
    try:
        return path.resolve().relative_to(study_root.resolve()).as_posix()
    except ValueError as exc:
        raise NDPTestInferenceError(
            f"artifact must be inside the study root: {path}"
        ) from exc


def _binding(path: Path, study_root: Path) -> Dict[str, str]:
    if not path.is_file():
        raise NDPTestInferenceError(f"artifact does not exist: {path}")
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
        raise NDPTestInferenceError(f"{label} binding is missing")
    value = ref.get("file")
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise NDPTestInferenceError(
            f"{label} must use a study-relative file"
        )
    root = study_root.resolve()
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise NDPTestInferenceError(
            f"{label} escapes the study root"
        ) from exc
    if not path.is_file() or _sha256_file(path) != ref.get("sha256"):
        raise NDPTestInferenceError(f"{label} does not verify")
    return path


def _derived_seed(seed_text: str, contrast_id: str) -> int:
    material = f"{seed_text}\x1f{contrast_id}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise NDPTestInferenceError("quantile requires values")
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(values[lower])
    weight = position - lower
    return float(
        values[lower] * (1.0 - weight) + values[upper] * weight
    )


def sign_flip_test(
    effects: Sequence[float],
    *,
    exact_max_nonzero_pairs: int,
    monte_carlo_repetitions: int,
    seed: int,
) -> Dict[str, Any]:
    total_count = len(effects)
    if total_count == 0:
        return {
            "status": "insufficient_data",
            "total_pair_count": 0,
            "nonzero_pair_count": 0,
            "two_sided_p_value": None,
        }
    observed = abs(statistics.mean(effects))
    nonzero = [float(value) for value in effects if value != 0.0]
    if not nonzero:
        return {
            "status": "ok",
            "total_pair_count": total_count,
            "nonzero_pair_count": 0,
            "zero_pair_count": total_count,
            "method": "degenerate_all_zero",
            "statistic_absolute_mean": 0.0,
            "extreme_count": 1,
            "repetitions": 1,
            "two_sided_p_value": 1.0,
            "seed": None,
        }
    tolerance = 1e-15
    if len(nonzero) <= exact_max_nonzero_pairs:
        repetitions = 2 ** len(nonzero)
        extreme = 0
        for signs in itertools.product((-1.0, 1.0), repeat=len(nonzero)):
            permuted = abs(
                sum(
                    sign * value
                    for sign, value in zip(signs, nonzero)
                )
                / total_count
            )
            if permuted + tolerance >= observed:
                extreme += 1
        p_value = extreme / repetitions
        method = "exact"
        reported_seed = None
    else:
        rng = random.Random(seed)
        repetitions = monte_carlo_repetitions
        extreme = 0
        for _ in range(repetitions):
            permuted = abs(
                sum(
                    (1.0 if rng.getrandbits(1) else -1.0) * value
                    for value in nonzero
                )
                / total_count
            )
            if permuted + tolerance >= observed:
                extreme += 1
        p_value = (extreme + 1) / (repetitions + 1)
        method = "monte_carlo"
        reported_seed = seed
    return {
        "status": "ok",
        "total_pair_count": total_count,
        "nonzero_pair_count": len(nonzero),
        "zero_pair_count": total_count - len(nonzero),
        "method": method,
        "statistic_absolute_mean": round(observed, 12),
        "extreme_count": extreme,
        "repetitions": repetitions,
        "two_sided_p_value": round(p_value, 12),
        "seed": reported_seed,
    }


def bootstrap_mean_interval(
    effects: Sequence[float],
    *,
    confidence_level: float,
    repetitions: int,
    seed: int,
) -> Dict[str, Any]:
    if not effects:
        return {
            "status": "insufficient_data",
            "dataset_count": 0,
            "confidence_interval": None,
        }
    rng = random.Random(seed)
    count = len(effects)
    samples = sorted(
        sum(effects[rng.randrange(count)] for _ in range(count)) / count
        for _ in range(repetitions)
    )
    tail = (1.0 - confidence_level) / 2.0
    return {
        "status": "ok",
        "dataset_count": count,
        "method": "fixed_seed_nonparametric_dataset_bootstrap_percentile",
        "repetitions": repetitions,
        "seed": seed,
        "confidence_level": confidence_level,
        "confidence_interval": [
            round(_quantile(samples, tail), 12),
            round(_quantile(samples, 1.0 - tail), 12),
        ],
    }


def holm_adjust(
    raw_p_values: Mapping[str, float],
) -> Dict[str, Dict[str, Any]]:
    ordered = sorted(
        raw_p_values.items(), key=lambda item: (item[1], item[0])
    )
    adjusted: Dict[str, Dict[str, Any]] = {}
    running = 0.0
    family_size = len(ordered)
    for rank, (contrast_id, p_value) in enumerate(ordered, start=1):
        running = max(
            running,
            min(1.0, (family_size - rank + 1) * p_value),
        )
        adjusted[contrast_id] = {
            "raw_p_value": round(p_value, 12),
            "holm_rank": rank,
            "holm_adjusted_p_value": round(running, 12),
        }
    return adjusted


def _rate(numerator: int, denominator: int) -> float | None:
    return (
        round(numerator / denominator, 12)
        if denominator > 0
        else None
    )


def _confidence_group_diagnostics(
    observations: Sequence[Mapping[str, Any]],
    *,
    applicable_known_slot_count: int,
    bin_edges: Sequence[float],
    minimum_support: int,
) -> Dict[str, Any]:
    ordered = sorted(
        observations,
        key=lambda item: (
            -float(item["confidence_score"]),
            str(item["slot_id"]),
        ),
    )
    bins = []
    for index, (lower, upper) in enumerate(
        zip(bin_edges, bin_edges[1:])
    ):
        members = [
            item
            for item in ordered
            if (
                float(item["confidence_score"]) >= lower
                and (
                    float(item["confidence_score"]) < upper
                    or (
                        index == len(bin_edges) - 2
                        and float(item["confidence_score"]) <= upper
                    )
                )
            )
        ]
        if not members:
            continue
        bins.append(
            {
                "lower_inclusive": lower,
                "upper": upper,
                "upper_inclusive": index == len(bin_edges) - 2,
                "support": len(members),
                "mean_confidence": round(
                    statistics.mean(
                        float(item["confidence_score"])
                        for item in members
                    ),
                    12,
                ),
                "empirical_accuracy": _rate(
                    sum(int(item["correct"]) for item in members),
                    len(members),
                ),
            }
        )
    support = len(ordered)
    adequate = support >= minimum_support
    brier_score = (
        round(
            statistics.mean(
                (
                    float(item["confidence_score"])
                    - int(item["correct"])
                )
                ** 2
                for item in ordered
            ),
            12,
        )
        if adequate
        else None
    )
    expected_calibration_error = (
        round(
            sum(
                int(item["support"])
                / support
                * abs(
                    float(item["mean_confidence"])
                    - float(item["empirical_accuracy"])
                )
                for item in bins
            ),
            12,
        )
        if adequate and support
        else None
    )
    curve = []
    cumulative = 0
    cumulative_errors = 0
    previous_coverage = 0.0
    aurc = 0.0
    for confidence, group in itertools.groupby(
        ordered, key=lambda item: float(item["confidence_score"])
    ):
        tied = list(group)
        cumulative += len(tied)
        cumulative_errors += sum(
            int(not item["correct"]) for item in tied
        )
        coverage = (
            cumulative / applicable_known_slot_count
            if applicable_known_slot_count
            else 0.0
        )
        risk = cumulative_errors / cumulative
        aurc += risk * (coverage - previous_coverage)
        previous_coverage = coverage
        curve.append(
            {
                "confidence_threshold": confidence,
                "tie_group_size": len(tied),
                "cumulative_accepted": cumulative,
                "cumulative_errors": cumulative_errors,
                "coverage": round(coverage, 12),
                "selective_risk": round(risk, 12),
            }
        )
    return {
        "accepted_prediction_support": support,
        "applicable_known_slot_count": applicable_known_slot_count,
        "calibration_claim_minimum_support": minimum_support,
        "calibration_claim_permitted": adequate,
        "calibration_status": (
            "adequate_for_descriptive_calibration"
            if adequate
            else "insufficient_support_no_calibration_claim"
        ),
        "reliability_bins": bins,
        "brier_score": brier_score,
        "expected_calibration_error_fixed_deciles": (
            expected_calibration_error
        ),
        "risk_coverage_curve": curve,
        "aurc_over_achieved_coverage": (
            round(aurc, 12) if curve else None
        ),
        "achieved_coverage_interval": [
            0.0,
            round(previous_coverage, 12),
        ],
        "tie_group_count": len(curve),
    }


def _confidence_diagnostics(
    scores: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any],
) -> Dict[str, Any]:
    observations_by_label: Dict[str, list[Mapping[str, Any]]] = defaultdict(
        list
    )
    applicable_by_label: Dict[str, int] = defaultdict(int)
    for score in scores:
        for item in score["confidence_observations"]:
            observations_by_label[str(item["label_id"])].append(item)
        for item in score["label_confusion_counts"]:
            applicable_by_label[str(item["label_id"])] += int(
                item["gold_support"]
            )
    labels = sorted(
        set(applicable_by_label) | set(observations_by_label)
    )
    return {
        "analysis_role": "secondary_descriptive_only",
        "calibration_target": contract["calibration_target"],
        "confidence_score_field": contract["score_field"],
        "pooling_across_labels_performed": False,
        "pooling_across_arms_performed": False,
        "risk_coverage_tie_rule": contract["risk_coverage_tie_rule"],
        "aurc_interval": contract["aurc_interval"],
        "per_label": {
            label_id: _confidence_group_diagnostics(
                observations_by_label[label_id],
                applicable_known_slot_count=applicable_by_label[label_id],
                bin_edges=[
                    float(value)
                    for value in contract["reliability_bin_edges"]
                ],
                minimum_support=int(
                    contract[
                        "minimum_group_support_for_calibration_claim"
                    ]
                ),
            )
            for label_id in labels
        },
    }


def _aggregate_arm_metrics(
    scores: Sequence[Mapping[str, Any]],
    *,
    confidence_contract: Mapping[str, Any],
) -> Dict[str, Any]:
    sums = {
        key: sum(int(item[key]) for item in scores)
        for key in (
            "applicable_known_slot_count",
            "applicable_unknown_or_oov_slot_count",
            "correct_accepted_claim_count",
            "accepted_known_claim_count",
            "incorrect_accepted_known_claim_count",
            "unsupported_accepted_claim_count",
            "valid_evidence_reference_claim_count",
            "verified_correct_accepted_claim_count",
        )
    }
    label_counts: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"tp": 0, "fp": 0, "fn": 0}
    )
    for score in scores:
        for item in score["label_confusion_counts"]:
            counts = label_counts[str(item["label_id"])]
            for key in ("tp", "fp", "fn"):
                counts[key] += int(item[key])
    per_label = []
    for label_id in sorted(label_counts):
        counts = label_counts[label_id]
        gold_support = counts["tp"] + counts["fn"]
        prediction_support = counts["tp"] + counts["fp"]
        denominator = 2 * counts["tp"] + counts["fp"] + counts["fn"]
        per_label.append(
            {
                "label_id": label_id,
                **counts,
                "gold_support": gold_support,
                "prediction_support": prediction_support,
                "f1": _rate(2 * counts["tp"], denominator),
            }
        )
    micro_tp = sum(item["tp"] for item in per_label)
    micro_fp = sum(item["fp"] for item in per_label)
    micro_fn = sum(item["fn"] for item in per_label)
    defined_f1 = [
        float(item["f1"])
        for item in per_label
        if item["gold_support"] > 0 and item["f1"] is not None
    ]
    known = sums["applicable_known_slot_count"]
    unknown = sums["applicable_unknown_or_oov_slot_count"]
    accepted = sums["accepted_known_claim_count"]
    return {
        "support_counts": sums,
        "metrics": {
            "correct_accepted_claim_rate": _rate(
                sums["correct_accepted_claim_count"], known
            ),
            "micro_f1": _rate(
                2 * micro_tp,
                2 * micro_tp + micro_fp + micro_fn,
            ),
            "macro_f1": (
                round(statistics.mean(defined_f1), 12)
                if defined_f1
                else None
            ),
            "out_of_vocabulary_rate": _rate(unknown, known + unknown),
            "verified_coverage": _rate(
                sums["verified_correct_accepted_claim_count"], known
            ),
            "selective_risk": _rate(
                sums["incorrect_accepted_known_claim_count"], accepted
            ),
            "unsupported_claim_rate": _rate(
                sums["unsupported_accepted_claim_count"], accepted
            ),
            "evidence_reference_validity": _rate(
                sums["valid_evidence_reference_claim_count"], accepted
            ),
        },
        "undefined_metric_count": sum(
            value is None
            for value in (
                _rate(sums["correct_accepted_claim_count"], known),
                _rate(2 * micro_tp, 2 * micro_tp + micro_fp + micro_fn),
                (
                    round(statistics.mean(defined_f1), 12)
                    if defined_f1
                    else None
                ),
                _rate(unknown, known + unknown),
                _rate(sums["verified_correct_accepted_claim_count"], known),
                _rate(sums["incorrect_accepted_known_claim_count"], accepted),
                _rate(sums["unsupported_accepted_claim_count"], accepted),
                _rate(sums["valid_evidence_reference_claim_count"], accepted),
            )
        ),
        "per_label_f1": per_label,
        "confidence_diagnostics": _confidence_diagnostics(
            scores,
            contract=confidence_contract,
        ),
    }


def build_inference_result(
    *,
    receipt_path: Path,
    missingness_path: Path,
    cpa_design_path: Path,
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
    receipt_kwargs = {
        "run_manifest_path": run_manifest_path,
        "selection_path": selection_path,
        "release_readiness_path": release_readiness_path,
        "workflow_path": workflow_path,
        "execution_freeze_path": execution_freeze_path,
        "power_freeze_path": power_freeze_path,
        "release_authorization_path": release_authorization_path,
        "release_receipt_path": release_receipt_path,
        "case_manifest_path": case_manifest_path,
        "deviation_registry_path": deviation_registry_path,
        "study_root": study_root,
    }
    receipt = _load_json(receipt_path)
    if (
        receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION
        or verify_run_receipt(receipt, **receipt_kwargs).get("status")
        != "passed"
    ):
        raise NDPTestInferenceError("test run receipt does not replay")
    missingness = _load_json(missingness_path)
    expected_missingness = build_missingness_report(
        receipt_path=receipt_path,
        **receipt_kwargs,
    )
    if (
        missingness.get("schema_version") != MISSINGNESS_SCHEMA_VERSION
        or missingness != expected_missingness
    ):
        raise NDPTestInferenceError(
            "test missingness report does not replay"
        )
    design = _load_json(cpa_design_path)
    analysis = registered_analysis_contract()
    metric_contract = registered_metric_contract()
    if (
        design.get("schema_version") != "ndp50-cpa-design/v1"
        or design.get("analysis") != analysis
        or design.get("metric_contract") != metric_contract
    ):
        raise NDPTestInferenceError("CPA design contract changed")
    workflow = _load_json(workflow_path)
    if workflow.get("cpa_design") != _binding(
        cpa_design_path, study_root
    ):
        raise NDPTestInferenceError(
            "test workflow and inference bind different CPA designs"
        )
    run = _load_json(run_manifest_path)
    case_manifest = _load_json(case_manifest_path)
    execution = _load_json(execution_freeze_path)
    power = _load_json(power_freeze_path)
    confidence_contract = execution.get("config", {}).get(
        "confidence_reporting_contract"
    )
    if (
        not isinstance(confidence_contract, dict)
        or confidence_contract.get("score_field") != "confidence_score"
        or confidence_contract.get("grouping_field") != "label_id"
        or confidence_contract.get("pooling_across_labels_permitted")
        is not False
        or confidence_contract.get("pooling_across_arms_permitted")
        is not False
        or confidence_contract.get("risk_coverage_tie_rule")
        != "whole_confidence_tie_groups_right_continuous"
        or confidence_contract.get("aurc_interval")
        != "achieved_coverage_only"
    ):
        raise NDPTestInferenceError(
            "frozen confidence reporting contract is invalid"
        )
    if run.get("schema_version") != RUN_MANIFEST_SCHEMA_VERSION:
        raise NDPTestInferenceError("unexpected test run schema")
    arms = execution.get("config", {}).get("planned_arms")
    if not isinstance(arms, list) or run.get("planned_arms") != arms:
        raise NDPTestInferenceError("frozen arm registry changed")
    cases = case_manifest.get("cases")
    if not isinstance(cases, list):
        raise NDPTestInferenceError("test cases are missing")
    case_by_id = {str(item["case_id"]): item for item in cases}
    eligible_case_ids = {
        case_id
        for case_id, item in case_by_id.items()
        if item.get("cpa_applicable") is True
    }
    scores_by_pair: Dict[tuple[str, str], Dict[str, Any]] = {}
    usage_by_arm: Dict[str, Dict[str, float]] = {
        arm: {
            **{key: 0 for key in RESOURCE_USAGE_INT_KEYS},
            **{key: 0.0 for key in RESOURCE_USAGE_FLOAT_KEYS},
        }
        for arm in arms
    }
    for entry in run["records"]:
        record_path = _bound_path(
            entry["artifact"],
            study_root=study_root,
            label=f"record {entry['record_id']}",
        )
        record = _load_json(record_path)
        score_path = _bound_path(
            record["score_artifact"],
            study_root=study_root,
            label=f"score {entry['record_id']}",
        )
        score = _load_json(score_path)
        if score.get("schema_version") != SCORE_ARTIFACT_SCHEMA_VERSION:
            raise NDPTestInferenceError("unexpected score schema")
        pair = (str(entry["case_id"]), str(entry["arm_id"]))
        scores_by_pair[pair] = score
        usage = score["resource_usage"]
        arm_usage = usage_by_arm[str(entry["arm_id"])]
        for key in RESOURCE_USAGE_INT_KEYS:
            arm_usage[key] += int(usage[key])
        for key in RESOURCE_USAGE_FLOAT_KEYS:
            arm_usage[key] += float(usage[key])
    sensitivity_conditions = receipt.get("sensitivity_conditions")
    if (
        not isinstance(sensitivity_conditions, list)
        or run.get("sensitivity_conditions") != sensitivity_conditions
    ):
        raise NDPTestInferenceError(
            "sensitivity condition registry changed after receipt"
        )
    condition_by_id = {
        str(item["condition_id"]): item
        for item in sensitivity_conditions
        if isinstance(item, dict)
    }
    if len(condition_by_id) != len(sensitivity_conditions):
        raise NDPTestInferenceError(
            "sensitivity condition registry is invalid"
        )
    sensitivity_scores_by_pair: Dict[
        tuple[str, str], Dict[str, Any]
    ] = {}
    sensitivity_usage: Dict[str, Dict[str, float]] = {
        condition_id: {
            **{key: 0 for key in RESOURCE_USAGE_INT_KEYS},
            **{key: 0.0 for key in RESOURCE_USAGE_FLOAT_KEYS},
        }
        for condition_id in condition_by_id
    }
    sensitivity_records = run.get("sensitivity_records")
    if not isinstance(sensitivity_records, list):
        raise NDPTestInferenceError("sensitivity records are missing")
    for entry in sensitivity_records:
        condition_id = str(entry["arm_id"])
        if condition_id not in condition_by_id:
            raise NDPTestInferenceError(
                "unregistered sensitivity condition encountered"
            )
        record_path = _bound_path(
            entry["artifact"],
            study_root=study_root,
            label=f"sensitivity record {entry['record_id']}",
        )
        record = _load_json(record_path)
        score_path = _bound_path(
            record["score_artifact"],
            study_root=study_root,
            label=f"sensitivity score {entry['record_id']}",
        )
        score = _load_json(score_path)
        if score.get("schema_version") != SCORE_ARTIFACT_SCHEMA_VERSION:
            raise NDPTestInferenceError(
                "unexpected sensitivity score schema"
            )
        pair = (str(entry["case_id"]), condition_id)
        sensitivity_scores_by_pair[pair] = score
        usage = score["resource_usage"]
        condition_usage = sensitivity_usage[condition_id]
        for key in RESOURCE_USAGE_INT_KEYS:
            condition_usage[key] += int(usage[key])
        for key in RESOURCE_USAGE_FLOAT_KEYS:
            condition_usage[key] += float(usage[key])
    eligible_scores_by_arm = {
        arm: [
            scores_by_pair[(case_id, arm)]
            for case_id in sorted(eligible_case_ids)
        ]
        for arm in arms
    }
    eligible_sensitivity_scores = {
        condition_id: [
            sensitivity_scores_by_pair[(case_id, condition_id)]
            for case_id in sorted(eligible_case_ids)
        ]
        for condition_id in condition_by_id
    }
    dataset_arm_counts: Dict[
        str, Dict[str, Dict[str, int]]
    ] = defaultdict(
        lambda: defaultdict(
            lambda: {"denominator": 0, "numerator": 0}
        )
    )
    for case_id in sorted(eligible_case_ids):
        dataset_id = str(case_by_id[case_id]["dataset_id"])
        for arm in arms:
            score = scores_by_pair[(case_id, arm)]
            counts = dataset_arm_counts[dataset_id][arm]
            counts["denominator"] += int(
                score["applicable_known_slot_count"]
            )
            counts["numerator"] += int(
                score["correct_accepted_claim_count"]
            )
    dataset_sensitivity_counts: Dict[
        str, Dict[str, Dict[str, int]]
    ] = defaultdict(
        lambda: defaultdict(
            lambda: {"denominator": 0, "numerator": 0}
        )
    )
    for case_id in sorted(eligible_case_ids):
        dataset_id = str(case_by_id[case_id]["dataset_id"])
        for condition_id in condition_by_id:
            score = sensitivity_scores_by_pair[(case_id, condition_id)]
            counts = dataset_sensitivity_counts[dataset_id][condition_id]
            counts["denominator"] += int(
                score["applicable_known_slot_count"]
            )
            counts["numerator"] += int(
                score["correct_accepted_claim_count"]
            )
    descriptive_sensitivity_results: Dict[str, Dict[str, Any]] = {}
    for condition_id, condition in sorted(condition_by_id.items()):
        rows = []
        paired_effects = []
        for dataset_id in sorted(dataset_arm_counts):
            anchor = dataset_arm_counts[dataset_id][ZERO_SHOT_ARM]
            observed = dataset_sensitivity_counts[dataset_id][
                condition_id
            ]
            if anchor["denominator"] != observed["denominator"]:
                raise NDPTestInferenceError(
                    f"{condition_id}/{dataset_id} anchor denominator differs"
                )
            denominator = anchor["denominator"]
            if denominator == 0:
                rows.append(
                    {
                        "dataset_id": dataset_id,
                        "status": "noncomparable",
                        "reason": (
                            "zero_applicable_known_slot_denominator"
                        ),
                        "denominator": 0,
                        "anchor_rate": None,
                        "condition_rate": None,
                        "paired_difference": None,
                    }
                )
                continue
            anchor_rate = anchor["numerator"] / denominator
            condition_rate = observed["numerator"] / denominator
            difference = condition_rate - anchor_rate
            paired_effects.append(difference)
            rows.append(
                {
                    "dataset_id": dataset_id,
                    "status": "comparable",
                    "reason": None,
                    "denominator": denominator,
                    "anchor_rate": round(anchor_rate, 12),
                    "condition_rate": round(condition_rate, 12),
                    "paired_difference": round(difference, 12),
                }
            )
        descriptive_sensitivity_results[condition_id] = {
            "condition": condition,
            "anchor_arm": ZERO_SHOT_ARM,
            "analysis_role": "descriptive_sensitivity_only",
            "confirmatory_test_performed": False,
            "multiplicity_adjusted_claim_permitted": False,
            "dataset_rows": rows,
            "comparable_dataset_count": len(paired_effects),
            "mean_paired_difference": (
                round(statistics.mean(paired_effects), 12)
                if paired_effects
                else None
            ),
            "arm_metrics_for_frozen_cpa_population": (
                _aggregate_arm_metrics(
                    eligible_sensitivity_scores[condition_id],
                    confidence_contract=confidence_contract,
                )
            ),
            "resource_usage_all_test_cases": {
                key: (
                    round(value, 12)
                    if key in RESOURCE_USAGE_FLOAT_KEYS
                    else int(value)
                )
                for key, value in sensitivity_usage[
                    condition_id
                ].items()
            },
        }
    contrast_results: Dict[str, Dict[str, Any]] = {}
    raw_p_values: Dict[str, float] = {}
    primary_test = analysis["primary_test"]
    required_by_contrast = (
        power.get("power_calculation", {})
        .get("planning_scenario", {})
        .get("contrasts", {})
    )
    for contrast in analysis["primary_contrasts"]:
        contrast_id = str(contrast["contrast_id"])
        arm_a = str(contrast["arm_a"])
        arm_b = str(contrast["arm_b"])
        rows = []
        effects = []
        exclusion_counts: Dict[str, int] = defaultdict(int)
        for dataset_id in sorted(dataset_arm_counts):
            counts_a = dataset_arm_counts[dataset_id][arm_a]
            counts_b = dataset_arm_counts[dataset_id][arm_b]
            if counts_a["denominator"] != counts_b["denominator"]:
                raise NDPTestInferenceError(
                    f"{contrast_id}/{dataset_id} arm denominators differ"
                )
            denominator = counts_a["denominator"]
            if denominator == 0:
                exclusion_counts[
                    "zero_applicable_known_slot_denominator"
                ] += 1
                rows.append(
                    {
                        "dataset_id": dataset_id,
                        "status": "noncomparable",
                        "reason": (
                            "zero_applicable_known_slot_denominator"
                        ),
                        "denominator": 0,
                        "arm_a_rate": None,
                        "arm_b_rate": None,
                        "paired_effect": None,
                    }
                )
                continue
            rate_a = counts_a["numerator"] / denominator
            rate_b = counts_b["numerator"] / denominator
            effect = rate_b - rate_a
            effects.append(effect)
            rows.append(
                {
                    "dataset_id": dataset_id,
                    "status": "comparable",
                    "reason": None,
                    "denominator": denominator,
                    "arm_a_rate": round(rate_a, 12),
                    "arm_b_rate": round(rate_b, 12),
                    "paired_effect": round(effect, 12),
                }
            )
        sign_flip = sign_flip_test(
            effects,
            exact_max_nonzero_pairs=int(
                primary_test["exact_max_nonzero_pairs"]
            ),
            monte_carlo_repetitions=int(
                primary_test[
                    "monte_carlo_repetitions_above_exact_max"
                ]
            ),
            seed=_derived_seed(
                str(primary_test["monte_carlo_seed_text"]),
                contrast_id,
            ),
        )
        bootstrap = bootstrap_mean_interval(
            effects,
            confidence_level=float(
                analysis["confidence_interval"]["level"]
            ),
            repetitions=int(analysis["dataset_bootstrap_repetitions"]),
            seed=_derived_seed(
                str(analysis["bootstrap_seed_text"]), contrast_id
            ),
        )
        required = (
            required_by_contrast.get(contrast_id, {}).get(
                "required_opportunity_dataset_count"
            )
        )
        if (
            not isinstance(required, int)
            or isinstance(required, bool)
            or required <= 0
        ):
            raise NDPTestInferenceError(
                f"frozen power requirement missing for {contrast_id}"
            )
        raw_p = sign_flip["two_sided_p_value"]
        if raw_p is not None:
            raw_p_values[contrast_id] = float(raw_p)
        contrast_results[contrast_id] = {
            "arm_a": arm_a,
            "arm_b": arm_b,
            "effect_direction": "arm_b_minus_arm_a",
            "dataset_rows": rows,
            "eligible_dataset_count": len(dataset_arm_counts),
            "comparable_dataset_count": len(effects),
            "noncomparable_dataset_count": (
                len(dataset_arm_counts) - len(effects)
            ),
            "noncomparability_reason_counts": dict(
                sorted(exclusion_counts.items())
            ),
            "mean_paired_effect": (
                round(statistics.mean(effects), 12)
                if effects
                else None
            ),
            "primary_sign_flip_test": sign_flip,
            "bootstrap_confidence_interval": bootstrap,
            "frozen_required_opportunity_dataset_count": required,
            "realized_count_meets_frozen_requirement": (
                len(effects) >= required
            ),
        }
    family_complete = len(raw_p_values) == len(
        analysis["primary_contrasts"]
    )
    holm = holm_adjust(raw_p_values) if family_complete else {}
    alpha = float(analysis["familywise_alpha"])
    for contrast_id, item in contrast_results.items():
        adjustment = holm.get(contrast_id)
        item["holm"] = adjustment
        item["reject_at_familywise_alpha"] = (
            adjustment is not None
            and adjustment["holm_adjusted_p_value"] <= alpha
        )
    any_underpowered = any(
        not item["realized_count_meets_frozen_requirement"]
        for item in contrast_results.values()
    )
    if not family_complete:
        inferential_status = "nonanalysable_missing_comparable_datasets"
    elif any_underpowered:
        inferential_status = "analysable_underpowered_as_registered"
    else:
        inferential_status = "analysable_frozen_requirement_realized"
    arm_metrics = {
        arm: _aggregate_arm_metrics(
            eligible_scores_by_arm[arm],
            confidence_contract=confidence_contract,
        )
        for arm in arms
    }
    usage_report = {
        arm: {
            key: (
                round(value, 12)
                if key in RESOURCE_USAGE_FLOAT_KEYS
                else int(value)
            )
            for key, value in usage.items()
        }
        for arm, usage in usage_by_arm.items()
    }
    implementation = Path(__file__).resolve()
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "status": inferential_status,
        "primary_statistical_unit": "dataset",
        "primary_outcome_id": PRIMARY_OUTCOME_ID,
        "source_artifacts": {
            "test_run_receipt": _binding(receipt_path, study_root),
            "missingness_report": _binding(missingness_path, study_root),
            "cpa_design": _binding(cpa_design_path, study_root),
            "test_run_manifest": _binding(
                run_manifest_path, study_root
            ),
            "test_case_manifest": _binding(
                case_manifest_path, study_root
            ),
            "execution_freeze": _binding(
                execution_freeze_path, study_root
            ),
            "power_freeze": _binding(power_freeze_path, study_root),
            "test_release_authorization": _binding(
                release_authorization_path, study_root
            ),
            "test_release_receipt": _binding(
                release_receipt_path, study_root
            ),
        },
        "dataset_flow": {
            "selected_test_dataset_count": receipt["test_dataset_count"],
            "frozen_test_case_count": receipt["test_case_count"],
            "cpa_applicable_case_count": len(eligible_case_ids),
            "cpa_applicable_dataset_count": len(dataset_arm_counts),
            "dataset_disposition_counts": receipt[
                "dataset_disposition_counts"
            ],
        },
        "case_arm_execution": {
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
            "qualified_execution_schedule_verified": receipt[
                "qualified_execution_schedule_verified"
            ],
            "execution_chronology_verified": receipt[
                "execution_chronology_verified"
            ],
            "execution_schedule_sha256": receipt[
                "execution_schedule_sha256"
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
            "failure_reason_counts": receipt["failure_reason_counts"],
        },
        "arm_metrics_for_frozen_cpa_population": arm_metrics,
        "resource_usage_all_test_cases": usage_report,
        "descriptive_sensitivity_results": (
            descriptive_sensitivity_results
        ),
        "co_primary_contrasts": contrast_results,
        "holm_family": {
            "family_complete": family_complete,
            "familywise_alpha": alpha,
            "method": "holm_step_down",
            "contrasts": holm,
        },
        "deviation_count": receipt["deviation_count"],
        "claim_scope": {
            "confirmatory_interpretation_permitted": (
                family_complete and not any_underpowered
            ),
            "underpowered": any_underpowered,
            "nonanalysable": not family_complete,
            "null_result_establishes_no_effect": False,
            "pilot_or_descriptive_arms_are_confirmatory": False,
            "random_vs_similarity_demonstration_selection_estimable": False,
            "prompt_variant_effect_estimable_from_primary_matrix": False,
            "row_sampler_effect_estimable_from_primary_matrix": False,
            "registered_prompt_variant_descriptive_contrasts_available": any(
                item["changed_factor"] == "prompt_variant"
                for item in sensitivity_conditions
            ),
            "registered_row_sampler_descriptive_contrasts_available": any(
                item["changed_factor"] == "row_sampler"
                for item in sensitivity_conditions
            ),
            "sensitivity_contrasts_are_confirmatory": False,
            "cross_domain_transfer_effect_identified": False,
        },
        "primary_publication_reporting_payload_complete": True,
        "descriptive_estimability_limits": {
            "few_shot_arms": (
                "descriptive architecture-arm results only; demonstration "
                "count and selection method are not separately identified"
            ),
            "prompt_variants": (
                "registered single-factor descriptive conditions anchored "
                "to the primary zero-shot row sampler; no confirmatory test"
            ),
            "row_samplers": (
                "registered single-factor descriptive conditions anchored "
                "to the primary zero-shot prompt; no confirmatory test"
            ),
            "cross_domain_transfer": (
                "not identified without a preregistered held-out-domain "
                "contrast; any family-stratified summary is descriptive"
            ),
        },
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            name: _sha256_file(implementation.with_name(name))
            for name in (
                "ndp50_cpa_design.py",
                "ndp50_test_execution.py",
            )
        },
    }


def verify_inference_result(
    payload: Mapping[str, Any],
    **kwargs: Any,
) -> Dict[str, Any]:
    try:
        expected = build_inference_result(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": REPLAY_SCHEMA_VERSION,
            "status": "failed",
            "detail": str(exc),
            "differing_top_level_keys": [],
        }
    differing = sorted(
        key
        for key in set(payload) | set(expected)
        if payload.get(key) != expected.get(key)
    )
    return {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "status": "passed" if not differing else "failed",
        "detail": None,
        "differing_top_level_keys": differing,
    }


def _add_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--missingness", type=Path, required=True)
    parser.add_argument("--cpa-design", type=Path, required=True)
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--release-readiness", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--execution-freeze", type=Path, required=True)
    parser.add_argument("--power-freeze", type=Path, required=True)
    parser.add_argument(
        "--release-authorization", type=Path, required=True
    )
    parser.add_argument("--release-receipt", type=Path, required=True)
    parser.add_argument("--case-manifest", type=Path, required=True)
    parser.add_argument("--deviation-registry", type=Path, required=True)
    parser.add_argument("--study-root", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or replay NDP-50 registered test inference."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    _add_inputs(build)
    build.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    _add_inputs(verify)
    verify.add_argument("--artifact", type=Path, required=True)
    verify.add_argument("--output", type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    kwargs = {
        "receipt_path": args.receipt,
        "missingness_path": args.missingness,
        "cpa_design_path": args.cpa_design,
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
    if args.command == "build":
        payload = build_inference_result(**kwargs)
        _write_json(args.output, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "family_complete": payload["holm_family"][
                        "family_complete"
                    ],
                    "underpowered": payload["claim_scope"][
                        "underpowered"
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    payload = _load_json(args.artifact)
    replay = verify_inference_result(payload, **kwargs)
    if args.output is not None:
        _write_json(args.output, replay)
    print(json.dumps(replay, indent=2, sort_keys=True))
    return 0 if replay["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
