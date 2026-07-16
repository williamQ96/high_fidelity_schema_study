from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import platform
import random
import statistics
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import scipy
from scipy.stats import t as student_t


PLAN_CONFIG_SCHEMA_VERSION = "semantic-blind-analysis-plan-config/v1"
PLAN_SCHEMA_VERSION = "semantic-blind-analysis-plan/v1"
RUN_SCHEMA_VERSION = "semantic-blind-analysis-run/v1"
RESULT_SCHEMA_VERSION = "semantic-blind-inference/v1"
PROTOCOL_VERSION = "semantic-architecture-protocol/v1"
BLIND_REPORT_SCHEMA_VERSION = "minimal-architecture-experiment/v3-blind"
PRIMARY_CONTRASTS = ("A_vs_B", "B_vs_C")
SECONDARY_CONTRASTS = ("C_vs_D",)
PRIMARY_OUTCOME = "correct_accepted_applicable_claim_rate_gain_per_dataset"


class BlindInferenceError(ValueError):
    pass


def sha256_file(path: Path) -> str:
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


def _resolve(owner: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return (owner.parent / candidate).resolve()


def _relative(path: Path, owner: Path) -> str:
    try:
        return os.path.relpath(path.resolve(), owner.resolve().parent)
    except ValueError:
        return str(path.resolve())


def _load(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BlindInferenceError(f"JSON root must be an object: {path}")
    return payload


def _bounded_probability(value: Any, name: str, *, open_lower: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise BlindInferenceError(f"{name} must be numeric")
    normalized = float(value)
    lower_valid = normalized > 0.0 if open_lower else normalized >= 0.0
    if not lower_valid or normalized >= 1.0:
        raise BlindInferenceError(
            f"{name} must be in {'(0, 1)' if open_lower else '[0, 1)'}"
        )
    return normalized


def _positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise BlindInferenceError(f"{name} must be a positive integer")
    return value


def build_analysis_plan(config: Dict[str, Any]) -> Dict[str, Any]:
    if config.get("schema_version") != PLAN_CONFIG_SCHEMA_VERSION:
        raise BlindInferenceError(f"expected {PLAN_CONFIG_SCHEMA_VERSION}")
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise BlindInferenceError(f"expected {PROTOCOL_VERSION}")
    if config.get("status") != "frozen":
        raise BlindInferenceError("analysis plan config status must be frozen")
    if config.get("primary_contrasts") != list(PRIMARY_CONTRASTS):
        raise BlindInferenceError("primary_contrasts must be A_vs_B and B_vs_C")
    if config.get("secondary_contrasts") != list(SECONDARY_CONTRASTS):
        raise BlindInferenceError("secondary_contrasts must contain only C_vs_D")
    alpha = _bounded_probability(
        config.get("familywise_alpha"), "familywise_alpha", open_lower=True
    )
    confidence = _bounded_probability(
        config.get("confidence_level"), "confidence_level", open_lower=True
    )
    if not math.isclose(confidence, 1.0 - alpha, rel_tol=0.0, abs_tol=1e-12):
        raise BlindInferenceError("confidence_level must equal 1 - familywise_alpha")
    exact_max_n = _positive_int(
        config.get("sign_flip_exact_max_n"), "sign_flip_exact_max_n"
    )
    if exact_max_n > 24:
        raise BlindInferenceError("sign_flip_exact_max_n may not exceed 24")
    sign_flip_repetitions = _positive_int(
        config.get("sign_flip_monte_carlo_repetitions"),
        "sign_flip_monte_carlo_repetitions",
    )
    bootstrap_repetitions = _positive_int(
        config.get("bootstrap_repetitions"), "bootstrap_repetitions"
    )
    sign_seed = _positive_int(config.get("sign_flip_seed"), "sign_flip_seed")
    bootstrap_seed = _positive_int(config.get("bootstrap_seed"), "bootstrap_seed")
    for key in (
        "backend_registry_file",
        "backend_registry_sha256",
        "power_analysis_file",
        "power_analysis_sha256",
    ):
        if not isinstance(config.get(key), str) or not config[key]:
            raise BlindInferenceError(f"{key} is required")
    implementation_path = Path(__file__).resolve()
    plan_inputs = {
        key: config[key]
        for key in (
            "schema_version",
            "protocol_version",
            "status",
            "backend_registry_file",
            "backend_registry_sha256",
            "power_analysis_file",
            "power_analysis_sha256",
            "primary_contrasts",
            "secondary_contrasts",
            "familywise_alpha",
            "confidence_level",
            "sign_flip_exact_max_n",
            "sign_flip_monte_carlo_repetitions",
            "sign_flip_seed",
            "bootstrap_repetitions",
            "bootstrap_seed",
        )
    }
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "status": "frozen",
        "primary_statistical_unit": "dataset",
        "primary_outcome": PRIMARY_OUTCOME,
        "primary_contrasts": list(PRIMARY_CONTRASTS),
        "secondary_contrasts": list(SECONDARY_CONTRASTS),
        "multiplicity": {
            "family": list(PRIMARY_CONTRASTS),
            "method": "Holm step-down family-wise error control",
            "familywise_alpha": alpha,
        },
        "estimators": {
            "point": "equal-weight arithmetic mean of comparable dataset-level paired rate effects",
            "primary_test": "two-sided paired t test on dataset-level effects",
            "parametric_interval": f"two-sided {confidence:.1%} Student-t confidence interval",
            "sign_flip_sensitivity": {
                "statistic": "absolute mean paired effect",
                "exact_max_n": exact_max_n,
                "monte_carlo_repetitions": sign_flip_repetitions,
                "seed": sign_seed,
            },
            "dataset_bootstrap_sensitivity": {
                "interval": f"two-sided {confidence:.1%} percentile interval",
                "repetitions": bootstrap_repetitions,
                "seed": bootstrap_seed,
            },
        },
        "missingness_policy": (
            "Use only evaluator-marked comparable rows; report every exclusion. "
            "Do not replace, impute, or add datasets after outcome inspection."
        ),
        "backend_policy": (
            "Holm-confirmatory inference uses the preregistered primary backend only. "
            "Other registered backends are sensitivity conditions; C_vs_D is secondary."
        ),
        "source_artifacts": {
            "backend_registry": {
                "file": config["backend_registry_file"],
                "sha256": config["backend_registry_sha256"],
            },
            "power_analysis": {
                "file": config["power_analysis_file"],
                "sha256": config["power_analysis_sha256"],
            },
        },
        "analysis_implementation": {
            "file": implementation_path.name,
            "sha256": sha256_file(implementation_path),
        },
        "plan_inputs": plan_inputs,
    }


def validate_analysis_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        expected = build_analysis_plan(payload.get("plan_inputs", {}))
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [
                {"code": "analysis_plan_recalculation_failed", "detail": str(exc)}
            ],
        }
    if payload != expected:
        differing = sorted(
            key
            for key in set(payload) | set(expected)
            if payload.get(key) != expected.get(key)
        )
        return {
            "status": "blocked",
            "errors": [
                {
                    "code": "analysis_plan_recalculation_mismatch",
                    "detail": f"recomputed plan differs at keys: {differing}",
                }
            ],
        }
    return {"status": "ready", "errors": []}


def verify_analysis_plan_sources(plan: Dict[str, Any], *, owner: Path) -> None:
    sources = plan.get("source_artifacts", {})
    for label in ("backend_registry", "power_analysis"):
        source = sources.get(label, {})
        path = _resolve(owner, str(source.get("file") or ""))
        if not path.is_file():
            raise BlindInferenceError(f"{label} does not exist: {path}")
        actual = sha256_file(path)
        if actual != source.get("sha256"):
            raise BlindInferenceError(
                f"{label} hash mismatch: expected {source.get('sha256')}, got {actual}"
            )
    registry = _load(_resolve(owner, sources["backend_registry"]["file"]))
    power = _load(_resolve(owner, sources["power_analysis"]["file"]))
    if registry.get("schema_version") != "semantic-backend-registry/v1":
        raise BlindInferenceError("analysis plan backend registry schema is invalid")
    if (
        power.get("schema_version") != "semantic-power-analysis/v2"
        or power.get("status") != "frozen"
    ):
        raise BlindInferenceError(
            "analysis plan requires a frozen semantic-power-analysis/v2 artifact"
        )
    if power.get("primary_contrasts") != list(PRIMARY_CONTRASTS):
        raise BlindInferenceError(
            "power analysis primary contrasts differ from the analysis plan"
        )
    if not math.isclose(
        float(power.get("alpha")),
        float(plan["multiplicity"]["familywise_alpha"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise BlindInferenceError("power-analysis alpha differs from the analysis plan")


def _quantile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        raise BlindInferenceError("quantile requires at least one value")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


def _derived_seed(base_seed: int, *parts: str) -> int:
    material = "\x1f".join([str(base_seed), *parts]).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def paired_t_inference(
    effects: Sequence[float], confidence_level: float
) -> Dict[str, Any]:
    n = len(effects)
    if n < 2:
        return {"status": "insufficient_data", "n": n}
    mean = statistics.mean(effects)
    sd = statistics.stdev(effects)
    if sd == 0.0:
        statistic = 0.0 if mean == 0.0 else math.copysign(math.inf, mean)
        p_value = 1.0 if mean == 0.0 else 0.0
        lower = upper = mean
    else:
        standard_error = sd / math.sqrt(n)
        statistic = mean / standard_error
        p_value = float(2.0 * student_t.sf(abs(statistic), df=n - 1))
        critical = float(student_t.ppf((1.0 + confidence_level) / 2.0, df=n - 1))
        lower = mean - critical * standard_error
        upper = mean + critical * standard_error
    return {
        "status": "ok",
        "n": n,
        "mean": round(mean, 12),
        "sample_sd": round(sd, 12),
        "degrees_of_freedom": n - 1,
        "t_statistic": statistic if math.isinf(statistic) else round(statistic, 12),
        "two_sided_p_value": round(p_value, 12),
        "confidence_level": confidence_level,
        "confidence_interval": [round(lower, 12), round(upper, 12)],
    }


def sign_flip_test(
    effects: Sequence[float],
    *,
    exact_max_n: int,
    monte_carlo_repetitions: int,
    seed: int,
) -> Dict[str, Any]:
    n = len(effects)
    if n < 1:
        return {"status": "insufficient_data", "n": 0}
    observed = abs(statistics.mean(effects))
    tolerance = 1e-15
    if n <= exact_max_n:
        total = 2**n
        extreme = 0
        for signs in itertools.product((-1.0, 1.0), repeat=n):
            permuted = abs(sum(sign * value for sign, value in zip(signs, effects)) / n)
            if permuted + tolerance >= observed:
                extreme += 1
        p_value = extreme / total
        method = "exact"
        repetitions = total
    else:
        rng = random.Random(seed)
        extreme = 0
        for _ in range(monte_carlo_repetitions):
            permuted = abs(
                sum((1.0 if rng.getrandbits(1) else -1.0) * value for value in effects)
                / n
            )
            if permuted + tolerance >= observed:
                extreme += 1
        p_value = (extreme + 1) / (monte_carlo_repetitions + 1)
        method = "monte_carlo"
        repetitions = monte_carlo_repetitions
    return {
        "status": "ok",
        "n": n,
        "method": method,
        "statistic_absolute_mean": round(observed, 12),
        "extreme_count": extreme,
        "repetitions": repetitions,
        "two_sided_p_value": round(p_value, 12),
        "seed": seed if method == "monte_carlo" else None,
    }


def bootstrap_mean_interval(
    effects: Sequence[float],
    *,
    confidence_level: float,
    repetitions: int,
    seed: int,
) -> Dict[str, Any]:
    n = len(effects)
    if n < 1:
        return {"status": "insufficient_data", "n": 0}
    rng = random.Random(seed)
    samples = sorted(
        sum(effects[rng.randrange(n)] for _ in range(n)) / n for _ in range(repetitions)
    )
    tail = (1.0 - confidence_level) / 2.0
    return {
        "status": "ok",
        "n": n,
        "method": "dataset_percentile_bootstrap",
        "repetitions": repetitions,
        "seed": seed,
        "confidence_level": confidence_level,
        "confidence_interval": [
            round(_quantile(samples, tail), 12),
            round(_quantile(samples, 1.0 - tail), 12),
        ],
    }


def holm_adjust(raw_p_values: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
    ordered = sorted(raw_p_values.items(), key=lambda item: (item[1], item[0]))
    adjusted: Dict[str, Dict[str, Any]] = {}
    running = 0.0
    family_size = len(ordered)
    for rank, (contrast, p_value) in enumerate(ordered, start=1):
        running = max(running, min(1.0, (family_size - rank + 1) * p_value))
        adjusted[contrast] = {
            "raw_p_value": round(p_value, 12),
            "holm_rank": rank,
            "holm_adjusted_p_value": round(running, 12),
        }
    return adjusted


def _report_case_ids(report: Dict[str, Any]) -> List[str]:
    design = report.get("case_design")
    if not isinstance(design, list):
        raise BlindInferenceError("evaluation report case_design is required")
    ids = [str(item.get("case_id") or "") for item in design if isinstance(item, dict)]
    if (
        len(ids) != len(design)
        or any(not item for item in ids)
        or len(ids) != len(set(ids))
    ):
        raise BlindInferenceError(
            "evaluation report case IDs must be present and unique"
        )
    return ids


def _validate_report(
    report: Dict[str, Any],
    *,
    backend: Dict[str, Any],
    blind_case_ids: Sequence[str],
) -> None:
    if report.get("schema_version") != BLIND_REPORT_SCHEMA_VERSION:
        raise BlindInferenceError(
            f"evaluation report must use {BLIND_REPORT_SCHEMA_VERSION}"
        )
    if report.get("benchmark_roles") != ["blind_external"]:
        raise BlindInferenceError(
            "evaluation report must contain only blind_external cases"
        )
    if _report_case_ids(report) != list(blind_case_ids):
        raise BlindInferenceError(
            "evaluation report case identity/order differs from blind manifest"
        )
    if set(report.get("variant_summaries", {})) != {"A", "B", "C", "D"}:
        raise BlindInferenceError(
            "evaluation report must contain exactly A/B/C/D summaries"
        )
    identity = report.get("execution_control", {}).get("backend_identity", {})
    if identity.get("backend_registry_sha256") != backend.get("_registry_sha256"):
        raise BlindInferenceError(
            "evaluation report backend registry differs from the analysis plan"
        )
    if identity.get("registered_backend_id") != backend.get("backend_id"):
        raise BlindInferenceError(
            "evaluation report registered backend ID differs from the run manifest"
        )
    if identity.get("registered_backend_role") != backend.get("role"):
        raise BlindInferenceError(
            "evaluation report registered backend role differs from the registry"
        )
    if identity.get("registered_backend_record_sha256") != _canonical_json_hash(
        {key: value for key, value in backend.items() if key != "_registry_sha256"}
    ):
        raise BlindInferenceError(
            "evaluation report registered backend record differs from the registry"
        )
    if identity.get("registered_checkpoint_sha256") != backend.get("checkpoint_sha256"):
        raise BlindInferenceError(
            "evaluation report checkpoint attestation differs from the registry"
        )
    if identity.get("model_identifier") != backend.get("model_identifier"):
        raise BlindInferenceError(
            "evaluation report model identifier differs from backend registry"
        )
    if backend.get("endpoint") is not None and str(
        identity.get("api_base") or ""
    ).rstrip("/") != str(backend["endpoint"]).rstrip("/"):
        raise BlindInferenceError(
            "evaluation report API endpoint differs from backend registry"
        )
    decoding = backend.get("dataset_reasoner_decoding")
    if isinstance(decoding, dict):
        for report_key, registry_key in (
            ("seed", "seed"),
            ("max_tokens", "max_tokens"),
        ):
            if identity.get(report_key) != decoding.get(registry_key):
                raise BlindInferenceError(
                    f"evaluation report {report_key} differs from backend registry"
                )
    opportunity_ids = {
        str(item["case_id"])
        for item in report["case_design"]
        if item.get("dataset_reasoning_opportunity") is True
    }
    opportunity_order = [
        str(item["case_id"])
        for item in report["case_design"]
        if item.get("dataset_reasoning_opportunity") is True
    ]
    comparisons = (
        report.get("predefined_analysis_strata", {})
        .get("dataset_reasoning_opportunity", {})
        .get("dataset_level_comparison")
    )
    if not isinstance(comparisons, dict):
        raise BlindInferenceError("opportunity-stratum comparisons are required")
    for contrast in (*PRIMARY_CONTRASTS, *SECONDARY_CONTRASTS):
        rows = comparisons.get(contrast, {}).get("cases")
        if not isinstance(rows, list):
            raise BlindInferenceError(f"evaluation report lacks {contrast} case rows")
        row_ids = [str(item.get("case_id") or "") for item in rows]
        if row_ids != opportunity_order or len(row_ids) != len(set(row_ids)):
            raise BlindInferenceError(
                f"{contrast} must contain every semantic-opportunity case exactly once in manifest order"
            )
    replay = report.get("execution_control", {}).get("b_c_replay_provenance")
    if not isinstance(replay, list):
        raise BlindInferenceError("B/C replay provenance is required")
    replay_by_case = {str(item.get("case_id") or ""): item for item in replay}
    if len(replay_by_case) != len(replay) or set(replay_by_case) != opportunity_ids:
        raise BlindInferenceError(
            "B/C replay provenance must contain every semantic-opportunity case exactly once"
        )
    for case_id in opportunity_ids:
        record = replay_by_case.get(case_id, {})
        if (
            record.get("valid") is not True
            or record.get("c_semantic_generation_calls") != 0
        ):
            raise BlindInferenceError(f"invalid B/C replay provenance for {case_id}")


def _contrast_result(
    comparison: Dict[str, Any],
    *,
    contrast: str,
    backend_id: str,
    plan: Dict[str, Any],
    required_opportunity_count: int,
    require_complete_comparability: bool = False,
) -> Dict[str, Any]:
    rows = comparison.get("cases")
    if not isinstance(rows, list):
        raise BlindInferenceError(f"{backend_id}/{contrast} dataset rows are required")
    effects: List[float] = []
    exclusions: List[Dict[str, Any]] = []
    descriptive = {
        "coverage_delta": [],
        "selective_risk_delta": [],
        "unsupported_accepted_model_claim_delta": [],
        "correct_accepted_claim_gain": [],
    }
    cases = []
    for row in rows:
        case_id = str(row.get("case_id") or "")
        effect = row.get("correct_accepted_claim_rate_gain")
        if row.get("status") == "comparable":
            if (
                not isinstance(effect, (int, float))
                or isinstance(effect, bool)
                or not -1.0 <= float(effect) <= 1.0
            ):
                raise BlindInferenceError(
                    f"{backend_id}/{contrast}/{case_id} has an invalid paired rate effect"
                )
            effects.append(float(effect))
            for metric in descriptive:
                value = row.get(metric)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    descriptive[metric].append(float(value))
            normalized_effect: float | None = float(effect)
        else:
            if effect is not None:
                raise BlindInferenceError(
                    f"{backend_id}/{contrast}/{case_id} is non-comparable but has an effect"
                )
            exclusions.append(
                {"case_id": case_id, "reasons": list(row.get("reasons") or [])}
            )
            normalized_effect = None
        cases.append(
            {
                "case_id": case_id,
                "status": row.get("status"),
                "effect": normalized_effect,
                "reasons": list(row.get("reasons") or []),
            }
        )
    estimators = plan["estimators"]
    sign_config = estimators["sign_flip_sensitivity"]
    bootstrap_config = estimators["dataset_bootstrap_sensitivity"]
    confidence = 1.0 - float(plan["multiplicity"]["familywise_alpha"])
    interpretation_allowed = not require_complete_comparability or not exclusions
    inferential_effects = effects if interpretation_allowed else []
    enough = (
        interpretation_allowed
        and len(inferential_effects) >= required_opportunity_count
    )
    descriptive_summary = {
        key: {
            "defined_case_count": len(values),
            "mean": round(statistics.mean(values), 12) if values else None,
        }
        for key, values in descriptive.items()
    }
    return {
        "status": (
            "not_comparable"
            if not interpretation_allowed
            else "analyzable"
            if inferential_effects
            else "not_analyzable"
        ),
        "direction": comparison.get("direction"),
        "case_count": len(rows),
        "comparable_case_count": len(effects),
        "excluded_case_count": len(exclusions),
        "required_comparable_opportunity_count": required_opportunity_count,
        "planned_power_count_met": enough,
        "effect_summary": {
            "mean": round(statistics.mean(inferential_effects), 12)
            if inferential_effects
            else None,
            "sample_sd": round(statistics.stdev(inferential_effects), 12)
            if len(inferential_effects) >= 2
            else None,
            "median": round(statistics.median(inferential_effects), 12)
            if inferential_effects
            else None,
            "minimum": round(min(inferential_effects), 12)
            if inferential_effects
            else None,
            "maximum": round(max(inferential_effects), 12)
            if inferential_effects
            else None,
        },
        "paired_t": paired_t_inference(inferential_effects, confidence),
        "sign_flip": sign_flip_test(
            inferential_effects,
            exact_max_n=int(sign_config["exact_max_n"]),
            monte_carlo_repetitions=int(sign_config["monte_carlo_repetitions"]),
            seed=_derived_seed(int(sign_config["seed"]), backend_id, contrast),
        ),
        "dataset_bootstrap": bootstrap_mean_interval(
            inferential_effects,
            confidence_level=confidence,
            repetitions=int(bootstrap_config["repetitions"]),
            seed=_derived_seed(int(bootstrap_config["seed"]), backend_id, contrast),
        ),
        "descriptive_deltas": descriptive_summary,
        "exclusions": exclusions,
        "cases": cases,
    }


def build_inference_artifact(
    *,
    run_manifest: Dict[str, Any],
    run_manifest_path: Path,
    output_path: Path,
) -> Dict[str, Any]:
    if run_manifest.get("schema_version") != RUN_SCHEMA_VERSION:
        raise BlindInferenceError(f"expected {RUN_SCHEMA_VERSION}")
    if run_manifest.get("protocol_version") != PROTOCOL_VERSION:
        raise BlindInferenceError(f"expected {PROTOCOL_VERSION}")
    if run_manifest.get("status") != "complete":
        raise BlindInferenceError("analysis run manifest status must be complete")
    plan_path = _resolve(
        run_manifest_path, str(run_manifest.get("analysis_plan_file") or "")
    )
    blind_path = _resolve(
        run_manifest_path, str(run_manifest.get("blind_manifest_file") or "")
    )
    for label, path, expected in (
        ("analysis plan", plan_path, run_manifest.get("analysis_plan_sha256")),
        ("blind manifest", blind_path, run_manifest.get("blind_manifest_sha256")),
    ):
        if not path.is_file() or sha256_file(path) != expected:
            raise BlindInferenceError(f"{label} is missing or has a hash mismatch")
    plan = _load(plan_path)
    validation = validate_analysis_plan(plan)
    if validation["status"] != "ready":
        raise BlindInferenceError(f"analysis plan is invalid: {validation['errors']}")
    verify_analysis_plan_sources(plan, owner=plan_path)
    blind = _load(blind_path)
    if (
        blind.get("schema_version") != "minimal-architecture-manifest/v2"
        or blind.get("benchmark_role") != "blind_external"
    ):
        raise BlindInferenceError("blind manifest boundary is invalid")
    plan_sources = plan["source_artifacts"]
    if (
        blind.get("backend_registry_sha256")
        != plan_sources["backend_registry"]["sha256"]
    ):
        raise BlindInferenceError(
            "blind manifest and analysis plan bind different backend registries"
        )
    design = blind.get("design", {})
    if design.get("analysis_plan_sha256") != sha256_file(plan_path):
        raise BlindInferenceError(
            "blind manifest does not bind the executing analysis plan"
        )
    if design.get("power_analysis_sha256") != plan_sources["power_analysis"]["sha256"]:
        raise BlindInferenceError(
            "blind manifest and analysis plan bind different power analyses"
        )
    registry_path = _resolve(plan_path, plan_sources["backend_registry"]["file"])
    power_path = _resolve(plan_path, plan_sources["power_analysis"]["file"])
    registry = _load(registry_path)
    power = _load(power_path)
    backends = registry.get("backends")
    if not isinstance(backends, list) or not backends:
        raise BlindInferenceError("backend registry is empty")
    backend_by_id = {
        str(item.get("backend_id") or ""): {
            **item,
            "_registry_sha256": sha256_file(registry_path),
        }
        for item in backends
    }
    primary_backend_id = str(registry.get("primary_backend_id") or "")
    if primary_backend_id not in backend_by_id:
        raise BlindInferenceError("backend registry primary backend is invalid")
    reports = run_manifest.get("evaluation_reports")
    if not isinstance(reports, list) or not reports:
        raise BlindInferenceError("analysis run requires evaluation reports")
    report_by_backend = {str(item.get("backend_id") or ""): item for item in reports}
    if set(report_by_backend) != set(backend_by_id) or len(reports) != len(
        report_by_backend
    ):
        raise BlindInferenceError(
            "analysis run must bind exactly one report per registered backend"
        )
    blind_case_ids = [str(item.get("case_id") or "") for item in blind.get("cases", [])]
    if (
        not blind_case_ids
        or any(not item for item in blind_case_ids)
        or len(blind_case_ids) != len(set(blind_case_ids))
    ):
        raise BlindInferenceError("blind manifest case IDs must be present and unique")
    required_opportunity_count = int(
        power["assumptions"]["required_semantic_opportunity_case_count"]
    )
    backend_results: Dict[str, Any] = {}
    source_reports = []
    for backend_id in sorted(backend_by_id):
        source = report_by_backend[backend_id]
        report_path = _resolve(run_manifest_path, str(source.get("report_file") or ""))
        if not report_path.is_file() or sha256_file(report_path) != source.get(
            "report_sha256"
        ):
            raise BlindInferenceError(
                f"evaluation report is missing or changed for {backend_id}"
            )
        report = _load(report_path)
        _validate_report(
            report, backend=backend_by_id[backend_id], blind_case_ids=blind_case_ids
        )
        comparisons = (
            report.get("predefined_analysis_strata", {})
            .get("dataset_reasoning_opportunity", {})
            .get("dataset_level_comparison")
        )
        if not isinstance(comparisons, dict):
            raise BlindInferenceError(
                f"opportunity comparison is missing for {backend_id}"
            )
        contrast_results = {}
        for contrast in (*PRIMARY_CONTRASTS, *SECONDARY_CONTRASTS):
            if contrast not in comparisons:
                raise BlindInferenceError(f"{backend_id} report lacks {contrast}")
            contrast_results[contrast] = _contrast_result(
                comparisons[contrast],
                contrast=contrast,
                backend_id=backend_id,
                plan=plan,
                required_opportunity_count=required_opportunity_count,
                require_complete_comparability=contrast in SECONDARY_CONTRASTS,
            )
        backend_results[backend_id] = {
            "registered_role": backend_by_id[backend_id].get("role"),
            "model_family": backend_by_id[backend_id].get("model_family"),
            "model_identifier": backend_by_id[backend_id].get("model_identifier"),
            "variant_summaries": report["variant_summaries"],
            "architecture_comparison": report.get("architecture_comparison", {}),
            "contrasts": contrast_results,
        }
        source_reports.append(
            {
                "backend_id": backend_id,
                "file": _relative(report_path, output_path),
                "sha256": sha256_file(report_path),
            }
        )
    primary = backend_results[primary_backend_id]["contrasts"]
    raw_p_values = {}
    for contrast in PRIMARY_CONTRASTS:
        test = primary[contrast]["paired_t"]
        if test.get("status") == "ok":
            raw_p_values[contrast] = float(test["two_sided_p_value"])
    holm = (
        holm_adjust(raw_p_values) if len(raw_p_values) == len(PRIMARY_CONTRASTS) else {}
    )
    alpha = float(plan["multiplicity"]["familywise_alpha"])
    for contrast, item in holm.items():
        item["reject_at_familywise_alpha"] = item["holm_adjusted_p_value"] <= alpha
    power_count_met = all(
        primary[item]["planned_power_count_met"] for item in PRIMARY_CONTRASTS
    )
    confirmatory_status = (
        "complete_as_planned"
        if len(holm) == len(PRIMARY_CONTRASTS) and power_count_met
        else "underpowered_observed_opportunity_or_comparability"
        if len(holm) == len(PRIMARY_CONTRASTS)
        else "not_analyzable"
    )
    implementation_path = Path(__file__).resolve()
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "research_evidence_status": "blind_external_backend_conditional",
        "primary_statistical_unit": "dataset",
        "primary_outcome": PRIMARY_OUTCOME,
        "primary_backend_id": primary_backend_id,
        "confirmatory_status": confirmatory_status,
        "interpretation_boundary": (
            "Primary inference is conditional on the preregistered backend and blind corpus. "
            "Sensitivity backends and C_vs_D do not replace either co-primary contrast."
        ),
        "source_artifacts": {
            "analysis_run_manifest": {
                "file": _relative(run_manifest_path, output_path),
                "sha256": sha256_file(run_manifest_path),
            },
            "analysis_plan": {
                "file": _relative(plan_path, output_path),
                "sha256": sha256_file(plan_path),
            },
            "blind_manifest": {
                "file": _relative(blind_path, output_path),
                "sha256": sha256_file(blind_path),
            },
            "evaluation_reports": source_reports,
        },
        "analysis_implementation": {
            "file": implementation_path.name,
            "sha256": sha256_file(implementation_path),
        },
        "runtime": {"python": platform.python_version(), "scipy": scipy.__version__},
        "required_comparable_opportunity_count": required_opportunity_count,
        "primary_backend_holm": {
            "familywise_alpha": alpha,
            "contrasts": holm,
        },
        "backend_results": backend_results,
    }


def validate_inference_artifact(path: Path) -> Dict[str, Any]:
    try:
        payload = _load(path)
        run_source = payload.get("source_artifacts", {}).get(
            "analysis_run_manifest", {}
        )
        run_path = _resolve(path, str(run_source.get("file") or ""))
        if not run_path.is_file() or sha256_file(run_path) != run_source.get("sha256"):
            raise BlindInferenceError("analysis run manifest is missing or changed")
        rebuilt = build_inference_artifact(
            run_manifest=_load(run_path), run_manifest_path=run_path, output_path=path
        )
        if payload != rebuilt:
            differing = sorted(
                key
                for key in set(payload) | set(rebuilt)
                if payload.get(key) != rebuilt.get(key)
            )
            raise BlindInferenceError(
                f"recomputed inference differs at keys: {differing}"
            )
        return {"status": "ready", "errors": [], "payload": payload}
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [
                {"code": "blind_inference_validation_failed", "detail": str(exc)}
            ],
        }


def _write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _rebase_plan_config_sources(
    config: Dict[str, Any], *, source_owner: Path, plan_path: Path
) -> Dict[str, Any]:
    rebased = dict(config)
    for key in ("backend_registry_file", "power_analysis_file"):
        source_path = _resolve(source_owner, str(config.get(key) or ""))
        rebased[key] = _relative(source_path, plan_path)
    return rebased


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Freeze and execute blind semantic-study inference."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("build-plan")
    plan.add_argument("--config", type=Path, required=True)
    plan.add_argument("--output", type=Path, required=True)
    validate_plan = commands.add_parser("validate-plan")
    validate_plan.add_argument("--plan", type=Path, required=True)
    analyze = commands.add_parser("analyze")
    analyze.add_argument("--run-manifest", type=Path, required=True)
    analyze.add_argument("--output", type=Path, required=True)
    validate = commands.add_parser("validate-result")
    validate.add_argument("--artifact", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build-plan":
        config_path = args.config.resolve()
        output_path = args.output.resolve()
        config = _load(config_path)
        source_plan = build_analysis_plan(config)
        verify_analysis_plan_sources(source_plan, owner=config_path)
        plan = build_analysis_plan(
            _rebase_plan_config_sources(
                config, source_owner=config_path, plan_path=output_path
            )
        )
        verify_analysis_plan_sources(plan, owner=output_path)
        _write(output_path, plan)
        print(
            json.dumps(
                {"status": "frozen", "output": str(args.output.resolve())}, indent=2
            )
        )
        return 0
    if args.command == "validate-plan":
        path = args.plan.resolve()
        payload = _load(path)
        result = validate_analysis_plan(payload)
        if result["status"] == "ready":
            try:
                verify_analysis_plan_sources(payload, owner=path)
            except Exception as exc:  # noqa: BLE001
                result = {
                    "status": "blocked",
                    "errors": [
                        {"code": "analysis_plan_source_invalid", "detail": str(exc)}
                    ],
                }
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "ready" else 1
    if args.command == "analyze":
        run_path = args.run_manifest.resolve()
        artifact = build_inference_artifact(
            run_manifest=_load(run_path),
            run_manifest_path=run_path,
            output_path=args.output.resolve(),
        )
        _write(args.output.resolve(), artifact)
        print(
            json.dumps(
                {
                    "status": artifact["confirmatory_status"],
                    "output": str(args.output.resolve()),
                },
                indent=2,
            )
        )
        return 0
    result = validate_inference_artifact(args.artifact.resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
