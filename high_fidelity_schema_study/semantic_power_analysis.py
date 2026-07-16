from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from pathlib import Path
from typing import Any, Dict, Iterable, List

import scipy
from scipy.stats import nct, t

from .semantic_power_calibration import validate_calibration_statistics_file


POWER_SCHEMA_VERSION = "semantic-power-analysis/v2"
POWER_CONFIG_SCHEMA_VERSION = "semantic-power-analysis-config/v1"
PROTOCOL_VERSION = "semantic-architecture-protocol/v1"
PRIMARY_OUTCOME = "correct_accepted_applicable_claim_rate_gain_per_dataset"
PRIMARY_CONTRASTS = ("A_vs_B", "B_vs_C")
MULTIPLICITY_POLICY = "holm_fwer_with_bonferroni_worst_case_power_planning"
METHOD = (
    "two-sided paired t-test power from the noncentral t distribution; "
    "each co-primary contrast is planned at familywise alpha/2, and total "
    "datasets are inflated by a binomial assurance calculation"
)
SHA256_RE_LENGTH = 64
MAX_SAMPLE_SIZE = 100_000


class PowerAnalysisError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == SHA256_RE_LENGTH and all(
        character in "0123456789abcdef" for character in text
    )


def _number(
    payload: Dict[str, Any],
    key: str,
    *,
    minimum: float,
    maximum: float,
    minimum_inclusive: bool = True,
    maximum_inclusive: bool = True,
) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise PowerAnalysisError(f"{key} must be numeric")
    number = float(value)
    lower_valid = number >= minimum if minimum_inclusive else number > minimum
    upper_valid = number <= maximum if maximum_inclusive else number < maximum
    if not lower_valid or not upper_valid:
        left = "[" if minimum_inclusive else "("
        right = "]" if maximum_inclusive else ")"
        raise PowerAnalysisError(f"{key} must be in {left}{minimum}, {maximum}{right}")
    return number


def paired_t_power(
    sample_size: int,
    *,
    minimum_effect: float,
    paired_difference_sd: float,
    alpha: float,
) -> float:
    if sample_size < 2:
        return 0.0
    degrees_of_freedom = sample_size - 1
    critical_value = float(t.ppf(1.0 - alpha / 2.0, degrees_of_freedom))
    noncentrality = minimum_effect * math.sqrt(sample_size) / paired_difference_sd
    lower_tail = float(nct.cdf(-critical_value, degrees_of_freedom, noncentrality))
    upper_tail = float(nct.sf(critical_value, degrees_of_freedom, noncentrality))
    return min(1.0, max(0.0, lower_tail + upper_tail))


def required_paired_sample_size(
    *,
    minimum_effect: float,
    paired_difference_sd: float,
    alpha: float,
    target_power: float,
) -> int:
    for sample_size in range(2, MAX_SAMPLE_SIZE + 1):
        power = paired_t_power(
            sample_size,
            minimum_effect=minimum_effect,
            paired_difference_sd=paired_difference_sd,
            alpha=alpha,
        )
        if power >= target_power:
            return sample_size
    raise PowerAnalysisError(
        f"required sample size exceeds the fixed search limit {MAX_SAMPLE_SIZE}"
    )


def _binomial_probability_at_least(
    total_count: int, required_successes: int, success_probability: float
) -> float:
    if required_successes <= 0:
        return 1.0
    if required_successes > total_count:
        return 0.0
    if success_probability == 1.0:
        return 1.0
    if success_probability == 0.0:
        return 0.0
    log_p = math.log(success_probability)
    log_q = math.log1p(-success_probability)
    lower_tail = math.fsum(
        math.exp(
            math.lgamma(total_count + 1)
            - math.lgamma(successes + 1)
            - math.lgamma(total_count - successes + 1)
            + successes * log_p
            + (total_count - successes) * log_q
        )
        for successes in range(required_successes)
    )
    return min(1.0, max(0.0, 1.0 - lower_tail))


def required_total_dataset_count(
    *,
    required_opportunity_count: int,
    effective_scorable_rate: float,
    assurance: float,
    minimum_total_dataset_count: int,
) -> int:
    lower = max(required_opportunity_count, minimum_total_dataset_count)
    if effective_scorable_rate == 1.0:
        return lower
    upper = max(lower, math.ceil(required_opportunity_count / effective_scorable_rate))
    while (
        _binomial_probability_at_least(
            upper, required_opportunity_count, effective_scorable_rate
        )
        < assurance
    ):
        upper *= 2
        if upper > MAX_SAMPLE_SIZE:
            raise PowerAnalysisError(
                f"total dataset count exceeds the fixed search limit {MAX_SAMPLE_SIZE}"
            )
    while lower < upper:
        midpoint = (lower + upper) // 2
        if (
            _binomial_probability_at_least(
                midpoint, required_opportunity_count, effective_scorable_rate
            )
            >= assurance
        ):
            upper = midpoint
        else:
            lower = midpoint + 1
    return lower


def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    if config.get("schema_version") != POWER_CONFIG_SCHEMA_VERSION:
        raise PowerAnalysisError(
            f"schema_version must be {POWER_CONFIG_SCHEMA_VERSION}"
        )
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise PowerAnalysisError(f"protocol_version must be {PROTOCOL_VERSION}")
    if config.get("status") not in {"draft", "frozen"}:
        raise PowerAnalysisError("status must be draft or frozen")
    if list(config.get("primary_contrasts") or []) != list(PRIMARY_CONTRASTS):
        raise PowerAnalysisError(f"primary_contrasts must be {list(PRIMARY_CONTRASTS)}")
    for key in (
        "calibration_manifest_sha256",
        "calibration_statistics_sha256",
    ):
        if not _is_sha256(config.get(key)):
            raise PowerAnalysisError(f"{key} must be a lowercase SHA-256")
    for key in ("calibration_manifest_file", "calibration_statistics_file"):
        if not str(config.get(key) or "").strip():
            raise PowerAnalysisError(f"{key} is required")
    if not str(config.get("sd_estimation_method") or "").strip():
        raise PowerAnalysisError("sd_estimation_method is required")
    if not str(config.get("planning_rationale") or "").strip():
        raise PowerAnalysisError("planning_rationale is required")

    minimum_effect = _number(
        config,
        "minimum_meaningful_effect",
        minimum=0.0,
        maximum=1.0,
        minimum_inclusive=False,
    )
    familywise_alpha = _number(
        config,
        "familywise_alpha",
        minimum=0.0,
        maximum=1.0,
        minimum_inclusive=False,
        maximum_inclusive=False,
    )
    target_power = _number(
        config,
        "target_power",
        minimum=0.0,
        maximum=1.0,
        minimum_inclusive=False,
        maximum_inclusive=False,
    )
    selective_risk_bound = _number(
        config,
        "selective_risk_bound",
        minimum=0.0,
        maximum=1.0,
    )
    planning_sd_inflation = _number(
        config,
        "planning_sd_inflation",
        minimum=1.0,
        maximum=10.0,
        minimum_inclusive=False,
    )
    semantic_opportunity_rate = _number(
        config,
        "semantic_opportunity_rate",
        minimum=0.0,
        maximum=1.0,
        minimum_inclusive=False,
    )
    noncomparability_rate = _number(
        config,
        "noncomparability_rate",
        minimum=0.0,
        maximum=1.0,
        maximum_inclusive=False,
    )
    opportunity_count_assurance = _number(
        config,
        "opportunity_count_assurance",
        minimum=0.0,
        maximum=1.0,
        minimum_inclusive=False,
        maximum_inclusive=False,
    )
    minimum_total_dataset_count = config.get("minimum_total_dataset_count")
    if (
        not isinstance(minimum_total_dataset_count, int)
        or isinstance(minimum_total_dataset_count, bool)
        or minimum_total_dataset_count < 2
    ):
        raise PowerAnalysisError("minimum_total_dataset_count must be at least 2")

    sd_payload = config.get("paired_difference_sd_by_contrast")
    if not isinstance(sd_payload, dict) or set(sd_payload) != set(PRIMARY_CONTRASTS):
        raise PowerAnalysisError(
            "paired_difference_sd_by_contrast must cover exactly A_vs_B and B_vs_C"
        )
    paired_sds = {}
    for contrast in PRIMARY_CONTRASTS:
        value = sd_payload.get(contrast)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not 0.0 < float(value) <= 1.0
        ):
            raise PowerAnalysisError(
                f"paired_difference_sd_by_contrast.{contrast} must be in (0, 1]"
            )
        paired_sds[contrast] = float(value)

    raw_multipliers = config.get("sensitivity_sd_multipliers")
    if not isinstance(raw_multipliers, list) or len(raw_multipliers) < 3:
        raise PowerAnalysisError(
            "sensitivity_sd_multipliers must contain at least three scenarios"
        )
    multipliers: List[float] = []
    for value in raw_multipliers:
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not 0.5 <= float(value) <= 3.0
        ):
            raise PowerAnalysisError(
                "sensitivity SD multipliers must each be in [0.5, 3]"
            )
        multipliers.append(float(value))
    if 1.0 not in multipliers or planning_sd_inflation not in multipliers:
        raise PowerAnalysisError(
            "sensitivity scenarios must include 1.0 and planning_sd_inflation"
        )
    if multipliers != sorted(set(multipliers)):
        raise PowerAnalysisError(
            "sensitivity_sd_multipliers must be unique and ascending"
        )

    return {
        **config,
        "minimum_meaningful_effect": minimum_effect,
        "familywise_alpha": familywise_alpha,
        "target_power": target_power,
        "selective_risk_bound": selective_risk_bound,
        "planning_sd_inflation": planning_sd_inflation,
        "semantic_opportunity_rate": semantic_opportunity_rate,
        "noncomparability_rate": noncomparability_rate,
        "opportunity_count_assurance": opportunity_count_assurance,
        "paired_difference_sd_by_contrast": paired_sds,
        "sensitivity_sd_multipliers": multipliers,
    }


def _scenario(
    config: Dict[str, Any],
    *,
    sd_multiplier: float,
    alpha_per_contrast: float,
    effective_scorable_rate: float,
) -> Dict[str, Any]:
    contrast_results = {}
    for contrast in PRIMARY_CONTRASTS:
        raw_sd = config["paired_difference_sd_by_contrast"][contrast]
        scenario_sd = raw_sd * sd_multiplier
        if scenario_sd > 1.0:
            raise PowerAnalysisError(
                f"{contrast} sensitivity SD exceeds the bounded rate-difference maximum"
            )
        required_count = required_paired_sample_size(
            minimum_effect=config["minimum_meaningful_effect"],
            paired_difference_sd=scenario_sd,
            alpha=alpha_per_contrast,
            target_power=config["target_power"],
        )
        contrast_results[contrast] = {
            "paired_difference_sd": round(scenario_sd, 8),
            "required_opportunity_dataset_count": required_count,
            "achieved_power_at_required_count": round(
                paired_t_power(
                    required_count,
                    minimum_effect=config["minimum_meaningful_effect"],
                    paired_difference_sd=scenario_sd,
                    alpha=alpha_per_contrast,
                ),
                8,
            ),
        }
    required_opportunities = max(
        item["required_opportunity_dataset_count"] for item in contrast_results.values()
    )
    total_count = required_total_dataset_count(
        required_opportunity_count=required_opportunities,
        effective_scorable_rate=effective_scorable_rate,
        assurance=config["opportunity_count_assurance"],
        minimum_total_dataset_count=config["minimum_total_dataset_count"],
    )
    return {
        "sd_multiplier": sd_multiplier,
        "contrasts": contrast_results,
        "required_semantic_opportunity_case_count": required_opportunities,
        "required_dataset_count": total_count,
        "probability_of_at_least_required_opportunities": round(
            _binomial_probability_at_least(
                total_count, required_opportunities, effective_scorable_rate
            ),
            8,
        ),
    }


def build_power_analysis(config: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _validate_config(config)
    alpha_per_contrast = normalized["familywise_alpha"] / len(PRIMARY_CONTRASTS)
    effective_scorable_rate = normalized["semantic_opportunity_rate"] * (
        1.0 - normalized["noncomparability_rate"]
    )
    scenarios = [
        _scenario(
            normalized,
            sd_multiplier=multiplier,
            alpha_per_contrast=alpha_per_contrast,
            effective_scorable_rate=effective_scorable_rate,
        )
        for multiplier in normalized["sensitivity_sd_multipliers"]
    ]
    planning = next(
        item
        for item in scenarios
        if item["sd_multiplier"] == normalized["planning_sd_inflation"]
    )
    implementation_path = Path(__file__).resolve()
    planning_inputs = {
        key: normalized[key]
        for key in (
            "schema_version",
            "protocol_version",
            "status",
            "calibration_manifest_file",
            "calibration_manifest_sha256",
            "calibration_statistics_file",
            "calibration_statistics_sha256",
            "sd_estimation_method",
            "planning_rationale",
            "primary_contrasts",
            "minimum_meaningful_effect",
            "familywise_alpha",
            "target_power",
            "selective_risk_bound",
            "paired_difference_sd_by_contrast",
            "planning_sd_inflation",
            "semantic_opportunity_rate",
            "noncomparability_rate",
            "opportunity_count_assurance",
            "minimum_total_dataset_count",
            "sensitivity_sd_multipliers",
        )
    }
    return {
        "schema_version": POWER_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "status": normalized["status"],
        "primary_statistical_unit": "dataset",
        "primary_outcome": PRIMARY_OUTCOME,
        "primary_contrasts": list(PRIMARY_CONTRASTS),
        "multiplicity_policy": MULTIPLICITY_POLICY,
        "selective_risk_bound": normalized["selective_risk_bound"],
        "minimum_meaningful_effect": normalized["minimum_meaningful_effect"],
        "alpha": normalized["familywise_alpha"],
        "alpha_per_contrast_for_planning": alpha_per_contrast,
        "target_power": normalized["target_power"],
        "calibration_manifest_sha256": normalized["calibration_manifest_sha256"],
        "calibration_statistics_sha256": normalized["calibration_statistics_sha256"],
        "calibration_sources": {
            "manifest": {
                "file": normalized["calibration_manifest_file"],
                "sha256": normalized["calibration_manifest_sha256"],
            },
            "statistics": {
                "file": normalized["calibration_statistics_file"],
                "sha256": normalized["calibration_statistics_sha256"],
            },
        },
        "method": METHOD,
        "analysis_implementation": {
            "file": implementation_path.name,
            "sha256": _sha256_file(implementation_path),
        },
        "runtime": {
            "python": platform.python_version(),
            "scipy": scipy.__version__,
        },
        "planning_inputs": planning_inputs,
        "assumptions": {
            "semantic_opportunity_rate": normalized["semantic_opportunity_rate"],
            "noncomparability_rate": normalized["noncomparability_rate"],
            "effective_scorable_rate": round(effective_scorable_rate, 8),
            "paired_difference_sd_by_contrast": normalized[
                "paired_difference_sd_by_contrast"
            ],
            "planning_sd_inflation": normalized["planning_sd_inflation"],
            "opportunity_count_assurance": normalized["opportunity_count_assurance"],
            "required_dataset_count": planning["required_dataset_count"],
            "required_semantic_opportunity_case_count": planning[
                "required_semantic_opportunity_case_count"
            ],
        },
        "calculation": planning,
        "sensitivity_scenarios": scenarios,
    }


def validate_power_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []
    planning_inputs = payload.get("planning_inputs")
    if not isinstance(planning_inputs, dict):
        return {
            "status": "blocked",
            "errors": [
                {
                    "code": "power_planning_inputs_missing",
                    "detail": "planning_inputs must be an object",
                }
            ],
        }
    try:
        expected = build_power_analysis(planning_inputs)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [
                {
                    "code": "power_recalculation_failed",
                    "detail": str(exc),
                }
            ],
        }
    if payload != expected:
        differing_keys = sorted(
            key
            for key in set(payload) | set(expected)
            if payload.get(key) != expected.get(key)
        )
        errors.append(
            {
                "code": "power_analysis_recalculation_mismatch",
                "detail": f"recomputed artifact differs at keys: {differing_keys}",
            }
        )
    return {"status": "ready" if not errors else "blocked", "errors": errors}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def verify_calibration_sources(config: Dict[str, Any], *, owner: Path) -> None:
    resolved_sources: Dict[str, Path] = {}
    for label, file_key, hash_key in (
        (
            "calibration manifest",
            "calibration_manifest_file",
            "calibration_manifest_sha256",
        ),
        (
            "calibration statistics",
            "calibration_statistics_file",
            "calibration_statistics_sha256",
        ),
    ):
        source_path = Path(str(config.get(file_key) or ""))
        if not source_path.is_absolute():
            source_path = (owner.parent / source_path).resolve()
        if not source_path.is_file():
            raise PowerAnalysisError(f"{label} does not exist: {source_path}")
        actual_hash = _sha256_file(source_path)
        if actual_hash != config.get(hash_key):
            raise PowerAnalysisError(
                f"{label} hash mismatch: expected {config.get(hash_key)}, got {actual_hash}"
            )
        resolved_sources[file_key] = source_path
    statistics_validation = validate_calibration_statistics_file(
        resolved_sources["calibration_statistics_file"]
    )
    if statistics_validation["status"] != "ready":
        raise PowerAnalysisError(
            "calibration statistics are not reproducible: "
            + json.dumps(statistics_validation["errors"], sort_keys=True)
        )
    statistics_payload = statistics_validation["payload"]
    statistics_manifest_hash = statistics_payload["source_artifacts"][
        "calibration_manifest"
    ]["sha256"]
    if statistics_manifest_hash != config.get("calibration_manifest_sha256"):
        raise PowerAnalysisError(
            "power config and calibration statistics bind different manifests"
        )
    recommended = statistics_payload["recommended_power_inputs"]
    for key in (
        "paired_difference_sd_by_contrast",
        "semantic_opportunity_rate",
        "noncomparability_rate",
    ):
        if config.get(key) != recommended.get(key):
            raise PowerAnalysisError(
                f"power config {key} differs from deterministic calibration statistics"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or validate the frozen semantic-study power artifact."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--config", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--artifact", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build":
        config = json.loads(args.config.read_text(encoding="utf-8"))
        verify_calibration_sources(config, owner=args.output)
        report = build_power_analysis(config)
        write_json(args.output, report)
        print(json.dumps(report["assumptions"], sort_keys=True))
        return 0
    payload = json.loads(args.artifact.read_text(encoding="utf-8"))
    report = validate_power_analysis(payload)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
