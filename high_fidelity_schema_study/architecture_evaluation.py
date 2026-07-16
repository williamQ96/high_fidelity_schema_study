from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .architecture_variants import (
    EVALUATED_PROPERTIES,
    ExperimentCase,
    MemoizingBackend,
    ModelBackend,
    OpenAICompatibleBackend,
    PropertyClaim,
    VariantRun,
    build_observation_payload,
    load_json,
    run_variant,
)
from .unit_normalization import normalize_unit_claim


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
DEFAULT_OUTPUT_ROOT = DATA_ROOT / "experiments" / "minimal_architecture_redesign"
GOLD_KEYS = {
    "physical_type": "correct_physical_type",
    "logical_type": "correct_logical_type",
    "semantic_type": "correct_semantic_type",
    "unit": "unit",
}
NOT_APPLICABLE = {None, ""}
UNKNOWN = {"unknown"}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_hash(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass
class SlotEvaluation:
    field_path: str
    property_name: str
    expected: Any
    predicted: Any
    target_state: str
    applicable: bool
    prediction_made: bool
    correct: Optional[bool]
    confidence: Optional[float]
    claim_id: Optional[str]
    expected_normalized: Any = None
    predicted_normalized: Any = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["property"] = payload.pop("property_name")
        return payload


@dataclass
class EvaluationCounts:
    applicable_slots: int = 0
    accepted_applicable_predictions: int = 0
    correct_applicable_predictions: int = 0
    incorrect_applicable_predictions: int = 0
    abstained_applicable_slots: int = 0
    applicable_unknown_slots: int = 0
    correct_abstentions_on_unknown: int = 0
    false_positive_applicable_unknown: int = 0
    non_applicable_slots: int = 0
    false_positive_non_applicable: int = 0
    predictions_outside_gold_scope: int = 0
    accepted_claims: int = 0
    accepted_model_claims: int = 0
    proposed_model_claims: int = 0
    rejected_model_claims: int = 0
    abstained_model_claims: int = 0
    unsupported_proposed_model_claims: int = 0
    accepted_unverified_model_claims: int = 0
    accepted_unsupported_model_claims: int = 0
    evidence_refs: int = 0
    valid_evidence_refs: int = 0
    model_evidence_refs: int = 0
    valid_model_evidence_refs: int = 0

    def add(self, other: "EvaluationCounts") -> None:
        for key in asdict(self):
            setattr(self, key, getattr(self, key) + getattr(other, key))


def safe_ratio(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def accepted_projection(
    claims: Iterable[PropertyClaim],
) -> Dict[Tuple[str, str], PropertyClaim]:
    projection: Dict[Tuple[str, str], PropertyClaim] = {}
    for claim in claims:
        if claim.decision == "accepted":
            projection[(claim.field_path, claim.property_name)] = claim
    return projection


def comparison_value(property_name: str, value: Any) -> Any:
    if property_name != "unit" or value in (None, ""):
        return value
    return normalize_unit_claim(str(value), [])["canonical_unit"]


def gold_slots(
    gold_schema: Dict[str, Any],
) -> Iterable[Tuple[str, str, Any, str]]:
    for field_schema in gold_schema.get("fields", []):
        field_path = str(field_schema["field_path"])
        explicit_applicability = field_schema.get("applicability", {})
        if not isinstance(explicit_applicability, dict):
            raise ValueError(f"applicability must be an object for {field_path}")
        for property_name in EVALUATED_PROPERTIES:
            expected = field_schema.get(GOLD_KEYS[property_name])
            explicit = explicit_applicability.get(property_name)
            if explicit is not None and not isinstance(explicit, bool):
                raise ValueError(
                    f"applicability for {field_path}.{property_name} must be boolean"
                )
            has_value = expected not in NOT_APPLICABLE and expected not in UNKNOWN
            if explicit is False and has_value:
                raise ValueError(
                    f"gold contradiction: {field_path}.{property_name} is marked N/A but has value {expected!r}"
                )
            if explicit is False:
                target_state = "not_applicable"
            elif has_value:
                target_state = "applicable_value"
            elif explicit is True or property_name != "unit":
                target_state = "applicable_unknown"
            else:
                target_state = "not_applicable"
            yield field_path, property_name, expected, target_state


def _evidence_counts(
    run: VariantRun, projection: Dict[Tuple[str, str], PropertyClaim]
) -> EvaluationCounts:
    counts = EvaluationCounts()
    catalog = {item.evidence_id: item for item in run.evidence_catalog}
    for claim in projection.values():
        counts.accepted_claims += 1
        counts.evidence_refs += len(claim.evidence_refs)
        valid_refs = [
            ref
            for ref in claim.evidence_refs
            if ref in catalog
            and claim.field_path in catalog[ref].applicable_field_paths
        ]
        counts.valid_evidence_refs += len(valid_refs)
    for claim in run.claims:
        if claim.source == "deterministic_baseline":
            continue
        counts.proposed_model_claims += 1
        if claim.decision == "accepted":
            counts.accepted_model_claims += 1
        elif claim.decision == "rejected":
            counts.rejected_model_claims += 1
        elif claim.decision == "abstained":
            counts.abstained_model_claims += 1
        counts.model_evidence_refs += len(claim.evidence_refs)
        valid_refs = [
            ref
            for ref in claim.evidence_refs
            if ref in catalog
            and claim.field_path in catalog[ref].applicable_field_paths
        ]
        counts.valid_model_evidence_refs += len(valid_refs)
        unsupported = (
            not claim.evidence_refs
            or claim.verification_status == "unsupported"
            or len(valid_refs) != len(claim.evidence_refs)
        )
        if unsupported:
            counts.unsupported_proposed_model_claims += 1
            if claim.decision == "accepted":
                counts.accepted_unsupported_model_claims += 1
        if claim.decision == "accepted" and claim.verification_level == "unverified":
            counts.accepted_unverified_model_claims += 1
    return counts


def _selective_curve(slots: Sequence[SlotEvaluation]) -> Dict[str, Any]:
    candidates = [slot for slot in slots if slot.applicable and slot.prediction_made]
    confidence_groups: Dict[float, List[SlotEvaluation]] = {}
    for slot in candidates:
        threshold = float(slot.confidence if slot.confidence is not None else 0.0)
        confidence_groups.setdefault(threshold, []).append(slot)
    total_applicable = sum(1 for slot in slots if slot.applicable)
    points: List[Dict[str, Any]] = [
        {"accepted": 0, "coverage": 0.0, "risk": 0.0, "threshold": None}
    ]
    errors = 0
    area = 0.0
    previous_coverage = 0.0
    accepted = 0
    for threshold in sorted(confidence_groups, reverse=True):
        group = confidence_groups[threshold]
        accepted += len(group)
        errors += sum(1 for slot in group if slot.correct is False)
        coverage = accepted / total_applicable if total_applicable else 0.0
        risk = errors / accepted
        # A confidence threshold admits the whole tie group at once.  Risk is
        # therefore a right-continuous step function, not a linearly
        # interpolated curve through an arbitrary order inside the tie.
        area += (coverage - previous_coverage) * risk
        points.append(
            {
                "accepted": accepted,
                "coverage": round(coverage, 6),
                "risk": round(risk, 6),
                "threshold": threshold,
            }
        )
        previous_coverage = coverage
    achieved = previous_coverage
    return {
        "points": points,
        "achieved_coverage": round(achieved, 6),
        "aurc_over_achieved_coverage": round(area, 6),
        "normalized_aurc": round(area / achieved, 6) if achieved else None,
        "note": "Right-continuous, confidence-tie-grouped AURC integrated only over achieved coverage; abstained slots are not converted into errors.",
    }


def evaluate_run(run: VariantRun, gold_schema: Dict[str, Any]) -> Dict[str, Any]:
    projection = accepted_projection(run.claims)
    slots: List[SlotEvaluation] = []
    counts = _evidence_counts(run, projection)
    per_property: Dict[str, EvaluationCounts] = {
        property_name: EvaluationCounts() for property_name in EVALUATED_PROPERTIES
    }
    evaluated_keys: set[Tuple[str, str]] = set()

    for field_path, property_name, expected, target_state in gold_slots(gold_schema):
        evaluated_keys.add((field_path, property_name))
        claim = projection.get((field_path, property_name))
        prediction_made = claim is not None
        applicable = target_state == "applicable_value"
        expected_normalized = comparison_value(property_name, expected)
        predicted_normalized = comparison_value(
            property_name, claim.value if claim is not None else None
        )
        correct = (
            predicted_normalized == expected_normalized
            if applicable and claim is not None
            else None
        )
        slot = SlotEvaluation(
            field_path=field_path,
            property_name=property_name,
            expected=expected,
            predicted=claim.value if claim is not None else None,
            target_state=target_state,
            applicable=applicable,
            prediction_made=prediction_made,
            correct=correct,
            confidence=claim.confidence if claim is not None else None,
            claim_id=claim.claim_id if claim is not None else None,
            expected_normalized=expected_normalized,
            predicted_normalized=predicted_normalized,
        )
        slots.append(slot)
        property_counts = per_property[property_name]
        if applicable:
            counts.applicable_slots += 1
            property_counts.applicable_slots += 1
            if prediction_made:
                counts.accepted_applicable_predictions += 1
                property_counts.accepted_applicable_predictions += 1
                if correct:
                    counts.correct_applicable_predictions += 1
                    property_counts.correct_applicable_predictions += 1
                else:
                    counts.incorrect_applicable_predictions += 1
                    property_counts.incorrect_applicable_predictions += 1
            else:
                counts.abstained_applicable_slots += 1
                property_counts.abstained_applicable_slots += 1
        elif target_state == "applicable_unknown":
            counts.applicable_unknown_slots += 1
            property_counts.applicable_unknown_slots += 1
            if prediction_made:
                counts.false_positive_applicable_unknown += 1
                property_counts.false_positive_applicable_unknown += 1
            else:
                counts.correct_abstentions_on_unknown += 1
                property_counts.correct_abstentions_on_unknown += 1
        else:
            counts.non_applicable_slots += 1
            property_counts.non_applicable_slots += 1
            if prediction_made:
                counts.false_positive_non_applicable += 1
                property_counts.false_positive_non_applicable += 1

    for (field_path, property_name), claim in projection.items():
        if (
            property_name not in per_property
            or (field_path, property_name) in evaluated_keys
        ):
            continue
        counts.predictions_outside_gold_scope += 1
        per_property[property_name].predictions_outside_gold_scope += 1
        slots.append(
            SlotEvaluation(
                field_path=field_path,
                property_name=property_name,
                expected=None,
                predicted=claim.value,
                target_state="outside_gold_scope",
                applicable=False,
                prediction_made=True,
                correct=None,
                confidence=claim.confidence,
                claim_id=claim.claim_id,
                expected_normalized=None,
                predicted_normalized=comparison_value(property_name, claim.value),
            )
        )

    return {
        "case_id": run.case_id,
        "variant_id": run.variant_id,
        "status": run.status,
        "counts": asdict(counts),
        "metrics": metrics_from_counts(counts),
        "by_property": {
            property_name: {
                "counts": asdict(property_counts),
                "metrics": metrics_from_counts(property_counts),
                "selective_curve": _selective_curve(
                    [slot for slot in slots if slot.property_name == property_name]
                ),
            }
            for property_name, property_counts in per_property.items()
        },
        "selective_curve": _selective_curve(slots),
        "slots": [slot.to_dict() for slot in slots],
        "telemetry": run.telemetry.to_dict(),
        "issues": run.issues,
    }


def metrics_from_counts(counts: EvaluationCounts) -> Dict[str, Optional[float]]:
    return {
        "end_to_end_value_accuracy": safe_ratio(
            counts.correct_applicable_predictions,
            counts.applicable_slots,
        ),
        "value_accuracy_applicable": safe_ratio(
            counts.correct_applicable_predictions,
            counts.applicable_slots,
        ),
        "coverage": safe_ratio(
            counts.accepted_applicable_predictions, counts.applicable_slots
        ),
        "selective_accuracy": safe_ratio(
            counts.correct_applicable_predictions,
            counts.accepted_applicable_predictions,
        ),
        "selective_risk": safe_ratio(
            counts.incorrect_applicable_predictions,
            counts.accepted_applicable_predictions,
        ),
        "abstention_rate": safe_ratio(
            counts.abstained_applicable_slots, counts.applicable_slots
        ),
        "false_positive_rate_non_applicable": safe_ratio(
            counts.false_positive_non_applicable,
            counts.non_applicable_slots,
        ),
        "applicable_unknown_abstention_accuracy": safe_ratio(
            counts.correct_abstentions_on_unknown,
            counts.applicable_unknown_slots,
        ),
        "false_positive_rate_applicable_unknown": safe_ratio(
            counts.false_positive_applicable_unknown,
            counts.applicable_unknown_slots,
        ),
        "evidence_reference_validity": safe_ratio(
            counts.valid_evidence_refs, counts.evidence_refs
        ),
        "unverified_model_claim_rate": safe_ratio(
            counts.accepted_unverified_model_claims,
            counts.accepted_model_claims,
        ),
        "unsupported_model_claim_rate": safe_ratio(
            counts.accepted_unsupported_model_claims,
            counts.accepted_model_claims,
        ),
        "unsupported_proposed_model_claim_rate": safe_ratio(
            counts.unsupported_proposed_model_claims,
            counts.proposed_model_claims,
        ),
        "model_evidence_reference_validity": safe_ratio(
            counts.valid_model_evidence_refs,
            counts.model_evidence_refs,
        ),
        "model_claim_acceptance_rate": safe_ratio(
            counts.accepted_model_claims,
            counts.proposed_model_claims,
        ),
        "model_claim_rejection_rate": safe_ratio(
            counts.rejected_model_claims,
            counts.proposed_model_claims,
        ),
        "model_claim_abstention_rate": safe_ratio(
            counts.abstained_model_claims,
            counts.proposed_model_claims,
        ),
    }


def _aggregate_variant(
    case_results: Sequence[Dict[str, Any]], runs: Sequence[VariantRun]
) -> Dict[str, Any]:
    counts = EvaluationCounts()
    by_property = {
        property_name: EvaluationCounts() for property_name in EVALUATED_PROPERTIES
    }
    telemetry = {
        "model_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "latency_ms": 0.0,
        "cost_usd": 0.0,
        "failed_calls": 0,
        "run_latency_ms": 0.0,
    }
    reused_upstream = {
        "model_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "latency_ms": 0.0,
        "cost_usd": 0.0,
        "failed_calls": 0,
    }
    failed_cases = 0
    issue_count = 0
    all_slots: List[SlotEvaluation] = []
    for result, run in zip(case_results, runs):
        counts.add(EvaluationCounts(**result["counts"]))
        for property_name in EVALUATED_PROPERTIES:
            by_property[property_name].add(
                EvaluationCounts(**result["by_property"][property_name]["counts"])
            )
        for key in telemetry:
            if key == "run_latency_ms":
                continue
            telemetry[key] += result["telemetry"][key]
        telemetry["run_latency_ms"] += run.run_latency_ms
        for response in run.model_responses:
            source = response.get("model_info", {}).get("replay_source_telemetry")
            if not isinstance(source, dict):
                continue
            for key in reused_upstream:
                reused_upstream[key] += source.get(key, 0)
        if run.status != "ok":
            failed_cases += 1
        issue_count += len(run.issues)
        all_slots.extend(
            SlotEvaluation(
                field_path=item["field_path"],
                property_name=item["property"],
                expected=item["expected"],
                predicted=item["predicted"],
                target_state=item["target_state"],
                applicable=item["applicable"],
                prediction_made=item["prediction_made"],
                correct=item["correct"],
                confidence=item["confidence"],
                claim_id=item["claim_id"],
                expected_normalized=item.get("expected_normalized"),
                predicted_normalized=item.get("predicted_normalized"),
            )
            for item in result["slots"]
        )
    telemetry["latency_ms"] = round(float(telemetry["latency_ms"]), 3)
    telemetry["run_latency_ms"] = round(float(telemetry["run_latency_ms"]), 3)
    telemetry["cost_usd"] = round(float(telemetry["cost_usd"]), 8)
    reused_upstream["latency_ms"] = round(float(reused_upstream["latency_ms"]), 3)
    reused_upstream["cost_usd"] = round(float(reused_upstream["cost_usd"]), 8)
    effective_telemetry = {
        key: telemetry[key] + reused_upstream[key] for key in reused_upstream
    }
    effective_telemetry["latency_ms"] = round(
        float(effective_telemetry["latency_ms"]), 3
    )
    effective_telemetry["cost_usd"] = round(float(effective_telemetry["cost_usd"]), 8)
    effective_telemetry["run_latency_ms"] = round(
        telemetry["run_latency_ms"] + reused_upstream["latency_ms"], 3
    )
    return {
        "case_count": len(case_results),
        "failed_case_count": failed_cases,
        "comparable": failed_cases == 0,
        "comparison_note": (
            "complete"
            if failed_cases == 0
            else "contains failed/partial cases; aggregate includes deterministic fallback and must not be used for architecture ranking"
        ),
        "issue_count": issue_count,
        "counts": asdict(counts),
        "metrics": metrics_from_counts(counts),
        "by_property": {
            property_name: {
                "counts": asdict(property_counts),
                "metrics": metrics_from_counts(property_counts),
                "selective_curve": _selective_curve(
                    [slot for slot in all_slots if slot.property_name == property_name]
                ),
            }
            for property_name, property_counts in by_property.items()
        },
        "selective_curve": _selective_curve(all_slots),
        "telemetry": telemetry,
        "reused_upstream_telemetry": reused_upstream,
        "effective_architecture_telemetry": effective_telemetry,
    }


def _architecture_comparison(summaries: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    comparisons: Dict[str, Any] = {}
    for left_id, right_id in (("A", "B"), ("B", "C"), ("C", "D")):
        comparison_id = f"{left_id}_vs_{right_id}"
        left = summaries.get(left_id)
        right = summaries.get(right_id)
        if left is None or right is None:
            continue
        if not left["comparable"] or not right["comparable"]:
            comparisons[comparison_id] = {
                "status": "not_comparable",
                "reason": (
                    f"{left_id} comparable={left['comparable']}; "
                    f"{right_id} comparable={right['comparable']}"
                ),
            }
            continue
        left_telemetry = left["effective_architecture_telemetry"]
        right_telemetry = right["effective_architecture_telemetry"]
        left_calls = left_telemetry["model_calls"]
        right_calls = right_telemetry["model_calls"]
        comparisons[comparison_id] = {
            "status": "comparable",
            "direction": f"{right_id} minus {left_id}",
            "model_call_delta": right_calls - left_calls,
            "coverage_delta": _metric_delta(right, left, "coverage"),
            "end_to_end_value_accuracy_delta": _metric_delta(
                right, left, "end_to_end_value_accuracy"
            ),
            "selective_risk_delta": _metric_delta(right, left, "selective_risk"),
            "unsupported_model_claim_rate_delta": _metric_delta(
                right,
                left,
                "unsupported_model_claim_rate",
            ),
            "unsupported_proposed_model_claim_rate_delta": _metric_delta(
                right,
                left,
                "unsupported_proposed_model_claim_rate",
            ),
            "latency_ms_delta": round(
                right_telemetry["latency_ms"] - left_telemetry["latency_ms"],
                3,
            ),
            "cost_usd_delta": round(
                right_telemetry["cost_usd"] - left_telemetry["cost_usd"], 8
            ),
        }
    return comparisons


def _mean_defined(values: Iterable[Optional[float]]) -> Optional[float]:
    defined = [float(value) for value in values if value is not None]
    if not defined:
        return None
    return round(sum(defined) / len(defined), 6)


def _dataset_level_comparison(
    evaluations_by_variant: Dict[str, List[Dict[str, Any]]],
    case_design: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    design_by_case = {str(item["case_id"]): item for item in case_design}
    indexed = {
        variant_id: {str(item["case_id"]): item for item in evaluations}
        for variant_id, evaluations in evaluations_by_variant.items()
    }
    comparisons: Dict[str, Any] = {}
    for left_id, right_id in (("A", "B"), ("B", "C"), ("C", "D")):
        if left_id not in indexed or right_id not in indexed:
            continue
        rows: List[Dict[str, Any]] = []
        case_ids = [
            str(item["case_id"])
            for item in case_design
            if str(item["case_id"]) in indexed[left_id]
            and str(item["case_id"]) in indexed[right_id]
        ]
        for case_id in case_ids:
            left = indexed[left_id][case_id]
            right = indexed[right_id][case_id]
            unscored_targets = list(
                design_by_case[case_id].get(
                    "unscored_dataset_reasoning_target_paths", []
                )
            )
            reasons = []
            if left["status"] != "ok":
                reasons.append(f"{left_id}_status={left['status']}")
            if right["status"] != "ok":
                reasons.append(f"{right_id}_status={right['status']}")
            if unscored_targets:
                reasons.append("semantic_targets_missing_from_gold")
            comparable = not reasons
            left_correct = int(left["counts"]["correct_applicable_predictions"])
            right_correct = int(right["counts"]["correct_applicable_predictions"])
            rows.append(
                {
                    "case_id": case_id,
                    "status": "comparable" if comparable else "not_comparable",
                    "reasons": reasons,
                    "applicable_slots": {
                        left_id: left["counts"]["applicable_slots"],
                        right_id: right["counts"]["applicable_slots"],
                    },
                    "correct_accepted_applicable_claims": {
                        left_id: left_correct,
                        right_id: right_correct,
                    },
                    "correct_accepted_claim_gain": (
                        right_correct - left_correct if comparable else None
                    ),
                    "correct_accepted_claim_rate_gain": (
                        _metric_delta(right, left, "end_to_end_value_accuracy")
                        if comparable
                        else None
                    ),
                    "coverage_delta": (
                        _metric_delta(right, left, "coverage") if comparable else None
                    ),
                    "selective_risk_delta": (
                        _metric_delta(right, left, "selective_risk")
                        if comparable
                        else None
                    ),
                    "unsupported_accepted_model_claim_delta": (
                        int(right["counts"]["accepted_unsupported_model_claims"])
                        - int(left["counts"]["accepted_unsupported_model_claims"])
                        if comparable
                        else None
                    ),
                }
            )
        comparable_rows = [item for item in rows if item["status"] == "comparable"]
        comparisons[f"{left_id}_vs_{right_id}"] = {
            "status": (
                "comparable"
                if rows and len(comparable_rows) == len(rows)
                else "not_comparable"
            ),
            "direction": f"{right_id} minus {left_id}",
            "statistical_unit": "dataset",
            "dataset_weighting": "equal weight per comparable dataset",
            "case_count": len(rows),
            "comparable_case_count": len(comparable_rows),
            "mean_correct_accepted_claim_gain": _mean_defined(
                item["correct_accepted_claim_gain"] for item in comparable_rows
            ),
            "mean_correct_accepted_claim_rate_gain": _mean_defined(
                item["correct_accepted_claim_rate_gain"] for item in comparable_rows
            ),
            "mean_coverage_delta": _mean_defined(
                item["coverage_delta"] for item in comparable_rows
            ),
            "mean_selective_risk_delta": _mean_defined(
                item["selective_risk_delta"] for item in comparable_rows
            ),
            "mean_unsupported_accepted_model_claim_delta": _mean_defined(
                item["unsupported_accepted_model_claim_delta"]
                for item in comparable_rows
            ),
            "cases": rows,
        }
    return comparisons


def _apply_design_comparability(
    summaries: Dict[str, Dict[str, Any]],
    unscored_target_cases: Sequence[Dict[str, Any]],
) -> None:
    if not unscored_target_cases:
        return
    issue = {
        "code": "semantic_targets_missing_from_gold",
        "cases": list(unscored_target_cases),
    }
    for variant_id in ("B", "C", "D"):
        summary = summaries.get(variant_id)
        if summary is None:
            continue
        summary["comparable"] = False
        summary.setdefault("design_issues", []).append(issue)
        summary["comparison_note"] = (
            "one or more semantic targets are outside gold scope; architecture "
            "effects on those targets cannot be scored"
        )


def _metric_delta(
    left: Dict[str, Any], right: Dict[str, Any], metric: str
) -> Optional[float]:
    left_value = left["metrics"].get(metric)
    right_value = right["metrics"].get(metric)
    if left_value is None or right_value is None:
        return None
    return round(left_value - right_value, 6)


def _mark_replay_violation(run: VariantRun, detail: str) -> None:
    run.status = "partial"
    run.issues.append({"code": "b_c_replay_integrity_failure", "detail": detail})


def _validate_b_c_replay(
    cases: Sequence[ExperimentCase],
    runs_by_variant: Dict[str, List[VariantRun]],
) -> List[Dict[str, Any]]:
    provenance: List[Dict[str, Any]] = []
    if "B" not in runs_by_variant or "C" not in runs_by_variant:
        return provenance
    for case, b_run, c_run in zip(cases, runs_by_variant["B"], runs_by_variant["C"]):
        b_response = b_run.model_responses[0] if b_run.model_responses else None
        c_response = c_run.model_responses[0] if c_run.model_responses else None
        c_calls = c_run.telemetry.model_calls
        replayed_failure = any(issue.get("replayed_failure") for issue in c_run.issues)
        no_targets = (
            not b_response
            and not c_response
            and b_run.status == "ok"
            and c_run.status == "ok"
        )
        hashes_equal = bool(
            b_response
            and c_response
            and b_response.get("response_hash") == c_response.get("response_hash")
        )
        raw_equal = bool(
            b_response
            and c_response
            and b_response.get("raw_text") == c_response.get("raw_text")
        )
        replay_flag = bool(
            c_response
            and c_response.get("model_info", {}).get("shared_reasoner_replay")
        )
        successful_identity = hashes_equal and raw_equal and replay_flag
        shared_failure = (
            b_run.status != "ok"
            and c_run.status != "ok"
            and replayed_failure
            and c_calls == 0
        )
        identical = successful_identity or no_targets
        valid = c_calls == 0 and (identical or shared_failure)
        record = {
            "case_id": case.case_id,
            "b_raw_response_hash": b_response.get("response_hash")
            if b_response
            else None,
            "c_input_response_hash": c_response.get("response_hash")
            if c_response
            else None,
            "raw_content_identical": raw_equal if b_response or c_response else None,
            "response_identity_identical": identical,
            "c_semantic_generation_calls": c_calls,
            "c_replay_flag": replay_flag,
            "shared_upstream_failure": shared_failure,
            "state": (
                "identical_response"
                if successful_identity
                else "no_semantic_targets"
                if no_targets
                else "shared_upstream_failure"
                if shared_failure
                else "invalid"
            ),
            "valid": valid,
        }
        provenance.append(record)
        if not valid:
            detail = json.dumps(record, sort_keys=True)
            _mark_replay_violation(b_run, detail)
            _mark_replay_violation(c_run, detail)
    return provenance


def run_experiment(
    cases: Sequence[ExperimentCase],
    *,
    variant_ids: Sequence[str] = ("A", "B", "C", "D"),
    backend: Optional[ModelBackend] = None,
    include_runs: bool = True,
) -> Dict[str, Any]:
    requested = [variant.upper() for variant in variant_ids]
    invalid = sorted(set(requested) - {"A", "B", "C", "D"})
    if invalid:
        raise ValueError(f"unknown variants: {', '.join(invalid)}")
    if len(requested) != len(set(requested)):
        raise ValueError("variant ids must be unique")
    if "C" in requested and "B" not in requested:
        raise ValueError("variant C requires B in the same run for response replay")
    normalized_variants = [item for item in ("A", "B", "C", "D") if item in requested]
    roles = sorted({case.benchmark_role for case in cases})
    registered_backend = getattr(backend, "registered_backend", None)
    backend_registry_sha256 = getattr(backend, "backend_registry_sha256", None)
    if roles == ["blind_external"] and backend is not None:
        if not isinstance(registered_backend, dict) or not str(
            registered_backend.get("backend_id") or ""
        ):
            raise ValueError(
                "blind model-backed execution requires a frozen registered backend"
            )
        if (
            not isinstance(backend_registry_sha256, str)
            or len(backend_registry_sha256) != 64
        ):
            raise ValueError(
                "blind model-backed execution requires the frozen backend registry hash"
            )
    controlled_backend = MemoizingBackend(backend) if backend is not None else None
    runs_by_variant: Dict[str, List[VariantRun]] = {
        variant: [] for variant in normalized_variants
    }
    for variant_id in normalized_variants:
        for case in cases:
            started = time.perf_counter()
            try:
                run = run_variant(variant_id, case, controlled_backend)
            except Exception as exc:  # noqa: BLE001
                run = VariantRun(
                    variant_id=variant_id,
                    case_id=case.case_id,
                    task_id=case.task_id,
                    status="failed",
                    claims=[],
                    evidence_catalog=[],
                    issues=[{"code": "variant_execution_failed", "detail": str(exc)}],
                )
            run.run_latency_ms = (time.perf_counter() - started) * 1000
            runs_by_variant[variant_id].append(run)

    replay_provenance = _validate_b_c_replay(cases, runs_by_variant)
    evaluations_by_variant: Dict[str, List[Dict[str, Any]]] = {
        variant: [] for variant in normalized_variants
    }
    for variant_id in normalized_variants:
        for case, run in zip(cases, runs_by_variant[variant_id]):
            evaluations_by_variant[variant_id].append(
                evaluate_run(run, case.gold_schema)
            )

    summaries = {
        variant_id: _aggregate_variant(
            evaluations_by_variant[variant_id], runs_by_variant[variant_id]
        )
        for variant_id in normalized_variants
    }
    case_design = []
    opportunity_indices: List[int] = []
    unscored_target_cases: List[Dict[str, Any]] = []
    for index, case in enumerate(cases):
        targets = build_observation_payload(case.task_payload)["targets"]
        target_paths = [str(item["field_path"]) for item in targets]
        gold_paths = {
            str(item["field_path"]) for item in case.gold_schema.get("fields", [])
        }
        unscored_targets = [path for path in target_paths if path not in gold_paths]
        scorable_targets = [path for path in target_paths if path in gold_paths]
        target_count = len(targets)
        if target_count:
            opportunity_indices.append(index)
        if unscored_targets:
            unscored_target_cases.append(
                {"case_id": case.case_id, "field_paths": unscored_targets}
            )
        case_design.append(
            {
                "case_id": case.case_id,
                "dataset_reasoning_target_count": target_count,
                "dataset_reasoning_target_paths": target_paths,
                "scorable_dataset_reasoning_target_count": len(scorable_targets),
                "unscored_dataset_reasoning_target_paths": unscored_targets,
                "dataset_reasoning_opportunity": target_count > 0,
            }
        )
    opportunity_evaluations = {
        variant_id: [evaluations_by_variant[variant_id][i] for i in opportunity_indices]
        for variant_id in normalized_variants
    }
    opportunity_summaries = {
        variant_id: _aggregate_variant(
            opportunity_evaluations[variant_id],
            [runs_by_variant[variant_id][i] for i in opportunity_indices],
        )
        for variant_id in normalized_variants
    }
    opportunity_case_design = [case_design[i] for i in opportunity_indices]
    _apply_design_comparability(summaries, unscored_target_cases)
    opportunity_design_issues = [
        item
        for item in unscored_target_cases
        if item["case_id"] in {cases[i].case_id for i in opportunity_indices}
    ]
    _apply_design_comparability(opportunity_summaries, opportunity_design_issues)
    report_schema_version = (
        "minimal-architecture-experiment/v3-blind"
        if roles == ["blind_external"]
        else "minimal-architecture-experiment/v3-development"
    )
    backend_identity: Dict[str, Any] = {
        "backend_class": type(backend).__name__ if backend is not None else None,
        "model_identifier": getattr(backend, "model", None),
        "api_base": getattr(backend, "api_base", None),
        "timeout_seconds": getattr(backend, "timeout_seconds", None),
        "seed": getattr(backend, "seed", None),
        "max_tokens": getattr(backend, "max_tokens", None),
        "input_price_per_million": getattr(backend, "input_price_per_million", None),
        "output_price_per_million": getattr(backend, "output_price_per_million", None),
        "backend_registry_sha256": backend_registry_sha256,
        "registered_backend_id": registered_backend.get("backend_id")
        if isinstance(registered_backend, dict)
        else None,
        "registered_backend_role": registered_backend.get("role")
        if isinstance(registered_backend, dict)
        else None,
        "registered_backend_record_sha256": _canonical_json_hash(registered_backend)
        if isinstance(registered_backend, dict)
        else None,
        "registered_checkpoint_sha256": registered_backend.get("checkpoint_sha256")
        if isinstance(registered_backend, dict)
        else None,
        "registered_quantization": registered_backend.get("quantization")
        if isinstance(registered_backend, dict)
        else None,
        "registered_runtime": registered_backend.get("runtime")
        if isinstance(registered_backend, dict)
        else None,
        "registration_interpretation": (
            "registry-bound execution selection; checkpoint bytes are attested by the frozen registry and qualification chain, not rehashed through the OpenAI-compatible API"
            if isinstance(registered_backend, dict)
            else None
        ),
    }
    report: Dict[str, Any] = {
        "schema_version": report_schema_version,
        "experiment": "architecture_compression_A_B_C_D",
        "benchmark_roles": roles,
        "claim_boundary": (
            "development/regression scores do not establish external generalization"
            if any(role != "blind_external" for role in roles)
            else "manifest declares blind_external; dataset freeze and annotation independence require external audit"
        ),
        "variants": {
            "A": "deterministic only",
            "B": "deterministic + at most one dataset-level semantic reasoner call",
            "C": "B + deterministic evidence-reference and conflict verifier",
            "D": "existing per-field/manual-group semantic pipeline",
        },
        "evaluated_properties": list(EVALUATED_PROPERTIES),
        "case_design": case_design,
        "metric_policy": {
            "target_states": "applicable_value, applicable_unknown, and not_applicable are evaluated separately",
            "end_to_end_value_accuracy": "correct applicable-value predictions divided by all applicable-value slots; abstentions lower this metric",
            "selective_accuracy": "correct accepted applicable-value predictions divided by accepted applicable-value predictions; abstentions are excluded",
            "non_applicable": "excluded from applicable-value denominators and scored separately for false positives",
            "outside_gold_scope": "predictions for task fields absent from an open-world gold field list are counted but not scored as N/A false positives",
            "unknown": "an applicable_unknown slot rewards abstention and is never silently treated as N/A",
            "confidence": "used only for selective curves; never treated as verification",
            "unit_comparison": "raw unit values are retained in traces; correctness uses the deterministic product unit canonicalization equally for all variants",
            "aurc": "right-continuous risk steps at whole confidence tie groups, integrated only over achieved coverage; also reported per property",
            "statistical_unit": "dataset-level paired effects with equal dataset weights are primary; pooled-slot summaries are descriptive",
        },
        "execution_control": {
            "backend_identity": backend_identity,
            "b_c_reasoner_response_reuse": True,
            "reason": "B and C consume the identical dataset-level model output so C isolates verifier contribution.",
            "physical_backend_invocations": controlled_backend.physical_backend_invocations
            if controlled_backend
            else 0,
            "physical_model_calls_executed": controlled_backend.physical_model_calls
            if controlled_backend
            else 0,
            "shared_response_cache_hits": controlled_backend.cache_hits
            if controlled_backend
            else 0,
            "shared_failure_cache_hits": controlled_backend.failure_cache_hits
            if controlled_backend
            else 0,
            "b_c_replay_provenance": replay_provenance,
            "telemetry_interpretation": "variant telemetry reports calls actually generated for that variant in this run; C reports zero semantic-generation calls because it replays B. Physical calls are recorded separately.",
        },
        "variant_summaries": summaries,
        "architecture_comparison": _architecture_comparison(summaries),
        "dataset_level_comparison": _dataset_level_comparison(
            evaluations_by_variant, case_design
        ),
        "predefined_analysis_strata": {
            "dataset_reasoning_opportunity": {
                "definition": "Cases with at least one unresolved deterministic target before any model output is observed.",
                "case_ids": [cases[i].case_id for i in opportunity_indices],
                "variant_summaries": opportunity_summaries,
                "architecture_comparison": _architecture_comparison(
                    opportunity_summaries
                ),
                "dataset_level_comparison": _dataset_level_comparison(
                    opportunity_evaluations, opportunity_case_design
                ),
            }
        },
        "case_evaluations": evaluations_by_variant,
    }
    if include_runs:
        report["runs"] = {
            variant_id: [run.to_dict() for run in runs]
            for variant_id, runs in runs_by_variant.items()
        }
    return report


def _resolve_manifest_path(manifest_path: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    from_manifest = (manifest_path.parent / candidate).resolve()
    if from_manifest.exists():
        return from_manifest
    return (ROOT / candidate).resolve()


def load_experiment_manifest(
    path: Path, *, replay_legacy: bool = False
) -> List[ExperimentCase]:
    manifest = load_json(path)
    annotation_vocabulary = None
    vocabulary_file = manifest.get("annotation_policy", {}).get("vocabulary_file")
    if vocabulary_file:
        annotation_vocabulary = load_json(
            _resolve_manifest_path(path, str(vocabulary_file))
        )
    cases: List[ExperimentCase] = []
    for item in manifest.get("cases", []):
        task_path = _resolve_manifest_path(path, item["task_file"])
        gold_path = _resolve_manifest_path(path, item["gold_file"])
        legacy_result = None
        if replay_legacy and item.get("legacy_result_file"):
            result_path = _resolve_manifest_path(path, item["legacy_result_file"])
            if result_path.exists():
                legacy_result = load_json(result_path)
        cases.append(
            ExperimentCase(
                case_id=str(
                    item.get("case_id") or load_json(task_path)["task"]["dataset_id"]
                ),
                task_payload=load_json(task_path),
                gold_schema=load_json(gold_path),
                benchmark_role=str(
                    item.get(
                        "benchmark_role", manifest.get("benchmark_role", "development")
                    )
                ),
                annotation_vocabulary=annotation_vocabulary,
                legacy_result=legacy_result,
                legacy_replay_required=replay_legacy,
            )
        )
    if not cases:
        raise ValueError(f"manifest contains no cases: {path}")
    return cases


def discover_internal_cases(*, replay_legacy: bool = False) -> List[ExperimentCase]:
    pilot = load_json(DATA_ROOT / "pilot_corpus_manifest.json")
    grounding = load_json(DATA_ROOT / "semantic_grounding" / "manifest.json")
    tasks_by_dataset = {
        item["dataset_id"]: item["task_file"] for item in grounding["internal_tasks"]
    }
    cases: List[ExperimentCase] = []
    for dataset in pilot["datasets"]:
        dataset_id = dataset["dataset_id"]
        task_path = DATA_ROOT / tasks_by_dataset[dataset_id]
        legacy_path = (
            DATA_ROOT
            / "semantic_annotations"
            / "internal"
            / f"{dataset_id}.result.json"
        )
        cases.append(
            ExperimentCase(
                case_id=dataset_id,
                task_payload=load_json(task_path),
                gold_schema=load_json(DATA_ROOT / dataset["gold_file"]),
                benchmark_role="synthetic_development",
                legacy_result=load_json(legacy_path)
                if replay_legacy and legacy_path.exists()
                else None,
                legacy_replay_required=replay_legacy,
            )
        )
    return cases


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Minimal Architecture Compression Experiment",
        "",
        f"Benchmark roles: `{', '.join(report['benchmark_roles'])}`",
        "",
        f"**Claim boundary:** {report['claim_boundary']}.",
        "",
        "| Variant | Comparable | Coverage | Selective risk | End-to-end value accuracy | Unsupported proposed model claims | Generated calls | Reused upstream calls | Effective calls | Effective model latency ms | Effective run latency ms | Cost USD | Failed cases |",
        "| --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for variant_id, summary in report["variant_summaries"].items():
        metrics = summary["metrics"]
        telemetry = summary["telemetry"]
        reused = summary["reused_upstream_telemetry"]
        effective = summary["effective_architecture_telemetry"]
        lines.append(
            "| {variant} | {comparable} | {coverage} | {risk} | {accuracy} | {unsupported} | {calls} | {reused_calls} | {effective_calls} | {latency:.3f} | {run_latency:.3f} | {cost:.8f} | {failed} |".format(
                variant=variant_id,
                comparable="yes" if summary["comparable"] else "no",
                coverage=_format_metric(metrics["coverage"]),
                risk=_format_metric(metrics["selective_risk"]),
                accuracy=_format_metric(metrics["end_to_end_value_accuracy"]),
                unsupported=_format_metric(
                    metrics["unsupported_proposed_model_claim_rate"]
                ),
                calls=telemetry["model_calls"],
                reused_calls=reused["model_calls"],
                effective_calls=effective["model_calls"],
                latency=effective["latency_ms"],
                run_latency=effective["run_latency_ms"],
                cost=effective["cost_usd"],
                failed=summary["failed_case_count"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation constraints",
            "",
            "- Confidence is used for risk/coverage ordering only; it is not verification.",
            "- N/A properties are excluded from value-accuracy denominators and reported as a separate false-positive rate.",
            "- C validates evidence identity, field scope, and deterministic conflicts. It does not claim semantic entailment or truth verification.",
            "- D intentionally preserves the historical non-empty-string evidence acceptance behavior.",
            "- Use a frozen, independently annotated blind manifest before making generalization claims.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_metric(value: Optional[float]) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def write_report(report: Dict[str, Any], output_dir: Path) -> Tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "report.json"
    markdown_path = output_dir / "report.md"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def _bind_backend_registration(
    backend: OpenAICompatibleBackend,
    *,
    manifest_path: Optional[Path],
    registry_path: Optional[Path],
    backend_id: Optional[str],
    required: bool,
) -> None:
    manifest: Dict[str, Any] = {}
    declared_registry_path: Optional[Path] = None
    declared_registry_hash: Optional[str] = None
    if manifest_path is not None:
        manifest = load_json(manifest_path)
        raw_registry = manifest.get("backend_registry_file")
        if raw_registry:
            declared_registry_path = _resolve_manifest_path(
                manifest_path, str(raw_registry)
            )
            declared_registry_hash = str(manifest.get("backend_registry_sha256") or "")

    selected_registry_path = (
        registry_path.resolve()
        if registry_path is not None
        else declared_registry_path.resolve()
        if declared_registry_path is not None
        else None
    )
    if selected_registry_path is None:
        if required:
            raise ValueError("blind execution manifest must bind a backend registry")
        if backend_id:
            raise ValueError("--backend-id requires --backend-registry")
        return
    if not backend_id:
        raise ValueError("registered backend execution requires --backend-id")
    if not selected_registry_path.is_file():
        raise ValueError(f"backend registry does not exist: {selected_registry_path}")

    registry_hash = _sha256_file(selected_registry_path)
    if declared_registry_hash:
        if registry_hash != declared_registry_hash:
            raise ValueError(
                "selected backend registry hash differs from the blind manifest"
            )
        if (
            declared_registry_path is not None
            and _sha256_file(declared_registry_path) != registry_hash
        ):
            raise ValueError(
                "explicit and manifest-declared backend registries are not identical"
            )
    elif required:
        raise ValueError("blind manifest must freeze backend_registry_sha256")

    registry = load_json(selected_registry_path)
    if registry.get("schema_version") != "semantic-backend-registry/v1":
        raise ValueError("expected semantic-backend-registry/v1")
    matches = [
        item
        for item in registry.get("backends", [])
        if isinstance(item, dict) and item.get("backend_id") == backend_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"backend_id {backend_id!r} must occur exactly once in the registry"
        )
    record = matches[0]
    if record.get("qualification", {}).get("eligible") is not True:
        raise ValueError(f"backend_id {backend_id!r} is not qualification-eligible")
    if record.get("model_identifier") != backend.model:
        raise ValueError("CLI model identifier differs from the registered backend")
    if str(record.get("endpoint") or "").rstrip("/") != backend.api_base.rstrip("/"):
        raise ValueError("CLI API endpoint differs from the registered backend")

    dataset_decoding = record.get("dataset_reasoner_decoding")
    if not isinstance(dataset_decoding, dict):
        raise ValueError("registered dataset_reasoner_decoding is missing")
    expected_dataset_decoding = {
        "temperature": 0,
        "seed": backend.seed,
        "max_tokens": backend.max_tokens,
        "thinking_enabled": False,
    }
    for key, expected in expected_dataset_decoding.items():
        if dataset_decoding.get(key) != expected:
            raise ValueError(
                f"CLI dataset reasoner {key} differs from the registered backend"
            )

    legacy_decoding = record.get("legacy_decoding")
    expected_legacy_decoding = {
        "temperature": 0.2,
        "seed": None,
        "max_tokens": 1000,
        "thinking_enabled": False,
    }
    if not isinstance(legacy_decoding, dict):
        raise ValueError("registered legacy_decoding is missing")
    for key, expected in expected_legacy_decoding.items():
        if legacy_decoding.get(key) != expected:
            raise ValueError(f"legacy {key} differs from the registered backend")

    backend.registered_backend = record
    backend.backend_registry_sha256 = registry_hash


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the minimal A/B/C/D architecture-compression experiment."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Optional experiment manifest; defaults to the 9 internal development cases.",
    )
    parser.add_argument(
        "--variants", default="A,B,C,D", help="Comma-separated subset of A,B,C,D."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--replay-legacy",
        action="store_true",
        help="Use stored D results when available; call telemetry will be unavailable.",
    )
    parser.add_argument("--api-base")
    parser.add_argument("--model")
    parser.add_argument("--api-key")
    parser.add_argument(
        "--backend-registry",
        type=Path,
        help=(
            "Frozen backend registry. Blind manifests already declare this file; "
            "an explicit path must have identical content."
        ),
    )
    parser.add_argument(
        "--backend-id",
        help="Exact backend_id from the frozen registry; required for blind model runs.",
    )
    parser.add_argument("--input-price-per-million", type=float, default=0.0)
    parser.add_argument("--output-price-per-million", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument(
        "--no-runs",
        action="store_true",
        help="Omit full claims/evidence from report.json.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    variant_ids = [
        item.strip().upper() for item in args.variants.split(",") if item.strip()
    ]
    invalid = sorted(set(variant_ids) - {"A", "B", "C", "D"})
    if invalid:
        parser.error(f"unknown variants: {', '.join(invalid)}")
    cases = (
        load_experiment_manifest(args.manifest, replay_legacy=args.replay_legacy)
        if args.manifest
        else discover_internal_cases(replay_legacy=args.replay_legacy)
    )
    blind_execution = sorted({case.benchmark_role for case in cases}) == [
        "blind_external"
    ]
    needs_live_backend = any(variant in {"B", "C"} for variant in variant_ids) or (
        "D" in variant_ids and not args.replay_legacy
    )
    backend: Optional[ModelBackend] = None
    if needs_live_backend:
        if not args.model:
            parser.error(
                "--model is required for B/C and for live D; use --variants A or provide a model"
            )
        backend = OpenAICompatibleBackend(
            api_base=args.api_base,
            model=args.model,
            api_key=args.api_key,
            timeout_seconds=args.timeout,
            input_price_per_million=args.input_price_per_million,
            output_price_per_million=args.output_price_per_million,
            seed=args.seed,
            max_tokens=args.max_tokens,
        )
        try:
            _bind_backend_registration(
                backend,
                manifest_path=args.manifest.resolve() if args.manifest else None,
                registry_path=args.backend_registry,
                backend_id=args.backend_id,
                required=blind_execution,
            )
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    elif args.backend_registry or args.backend_id:
        parser.error("backend registration flags require a model-backed variant")
    report = run_experiment(
        cases,
        variant_ids=variant_ids,
        backend=backend,
        include_runs=not args.no_runs,
    )
    json_path, markdown_path = write_report(report, args.output_dir)
    print(
        json.dumps(
            {"report_json": str(json_path), "report_markdown": str(markdown_path)},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
