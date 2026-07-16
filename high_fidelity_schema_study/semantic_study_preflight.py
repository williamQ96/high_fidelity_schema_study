from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .architecture_evaluation import EVALUATED_PROPERTIES, gold_slots
from .architecture_variants import (
    DATASET_REASONER_SYSTEM_PROMPT,
    LEGACY_SYSTEM_PROMPT,
    build_observation_payload,
    dataset_reasoner_response_schema,
    load_json,
)
from .semantic_annotator_calibration import (
    validate_annotator_calibration_summary,
)
from .semantic_blind_inference import (
    validate_analysis_plan,
    verify_analysis_plan_sources,
)
from .semantic_blind_sampling import validate_blind_selection
from .semantic_annotate import response_json_schema
from .semantic_gold_workflow import (
    validate_consensus_artifact,
    validate_vocabulary,
)
from .semantic_power_analysis import (
    POWER_SCHEMA_VERSION,
    PRIMARY_OUTCOME as PRIMARY_POWER_OUTCOME,
    validate_power_analysis,
    verify_calibration_sources,
)


ROOT = Path(__file__).resolve().parent
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_BACKEND_FAMILY_COUNT = 3
EVALUATION_IMPLEMENTATION_FILES = {
    "architecture_evaluation": "architecture_evaluation.py",
    "architecture_variants": "architecture_variants.py",
    "unit_normalization": "unit_normalization.py",
}
QUALIFICATION_MINIMUM_RATIOS = {
    "minimum_contract_valid_rate": "contract_valid_rate",
    "minimum_target_scope_valid_rate": "target_scope_valid_rate",
    "minimum_replay_identity_rate": "replay_identity_rate",
    "minimum_exact_repeatability_rate": "exact_repeatability_rate",
    "minimum_context_fit_rate": "context_fit_rate",
    "minimum_context_fit_observed_fraction": "context_fit_observed_fraction",
    "minimum_legacy_contract_valid_rate": "legacy_contract_valid_rate",
    "minimum_legacy_context_fit_rate": "legacy_context_fit_rate",
    "minimum_legacy_context_fit_observed_fraction": (
        "legacy_context_fit_observed_fraction"
    ),
}
QUALIFICATION_MAXIMUM_RATIOS = {
    "maximum_timeout_rate": "timeout_rate",
    "maximum_truncation_rate": "truncation_rate",
    "maximum_legacy_timeout_rate": "legacy_timeout_rate",
    "maximum_legacy_truncation_rate": "legacy_truncation_rate",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json_hash(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def semantic_contract_hashes() -> Dict[str, str]:
    return {
        "dataset_reasoner_prompt_sha256": sha256_text(DATASET_REASONER_SYSTEM_PROMPT),
        "dataset_reasoner_schema_sha256": canonical_json_hash(
            dataset_reasoner_response_schema()
        ),
        "legacy_prompt_sha256": sha256_text(LEGACY_SYSTEM_PROMPT),
        "legacy_schema_sha256": canonical_json_hash(response_json_schema()),
    }


def _resolve(owner: Path, raw_path: Any) -> Path:
    candidate = Path(str(raw_path))
    if candidate.is_absolute():
        return candidate
    adjacent = (owner.parent / candidate).resolve()
    if adjacent.exists():
        return adjacent
    return (ROOT / candidate).resolve()


def _issue(
    issues: List[Dict[str, Any]],
    code: str,
    detail: str,
    *,
    case_id: Optional[str] = None,
    backend_id: Optional[str] = None,
) -> None:
    item: Dict[str, Any] = {"code": code, "detail": detail}
    if case_id is not None:
        item["case_id"] = case_id
    if backend_id is not None:
        item["backend_id"] = backend_id
    issues.append(item)


def _check_file_identity(
    owner: Path,
    raw_path: Any,
    expected_hash: Any,
    issues: List[Dict[str, Any]],
    *,
    label: str,
    case_id: Optional[str] = None,
) -> Optional[Path]:
    if not raw_path:
        _issue(issues, "missing_file_path", f"{label} path is missing", case_id=case_id)
        return None
    path = _resolve(owner, raw_path)
    if not path.is_file():
        _issue(
            issues,
            "file_missing",
            f"{label} does not exist: {path}",
            case_id=case_id,
        )
        return None
    expected = str(expected_hash or "").lower()
    if not SHA256_RE.fullmatch(expected):
        _issue(
            issues,
            "invalid_frozen_hash",
            f"{label} must have a 64-character lowercase SHA-256",
            case_id=case_id,
        )
        return path
    actual = sha256_file(path)
    if actual != expected:
        _issue(
            issues,
            "frozen_hash_mismatch",
            f"{label} expected {expected} but found {actual}",
            case_id=case_id,
        )
    return path


def _valid_ratio(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= float(value) <= 1
    )


def preflight_backend_registry(path: Path) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    try:
        registry = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [{"code": "backend_registry_unreadable", "detail": str(exc)}],
            "warnings": [],
            "summary": {"backend_count": 0, "family_count": 0},
        }

    if registry.get("schema_version") != "semantic-backend-registry/v1":
        _issue(
            errors, "backend_schema_version", "expected semantic-backend-registry/v1"
        )
    if registry.get("protocol_version") != "semantic-architecture-protocol/v1":
        _issue(
            errors,
            "backend_protocol_version",
            "expected semantic-architecture-protocol/v1",
        )
    if not str(registry.get("frozen_at") or ""):
        _issue(errors, "backend_registry_not_frozen", "frozen_at is required")

    qualification_policy = registry.get("qualification_policy")
    if not isinstance(qualification_policy, dict):
        _issue(
            errors,
            "qualification_policy_missing",
            "qualification_policy must be frozen",
        )
        qualification_policy = {}
    for hash_key in (
        "calibration_manifest_sha256",
        "calibration_vocabulary_sha256",
    ):
        if not SHA256_RE.fullmatch(str(qualification_policy.get(hash_key) or "")):
            _issue(
                errors,
                "qualification_policy_hash_invalid",
                f"qualification_policy.{hash_key} must be a frozen SHA-256",
            )
    for key in (
        *QUALIFICATION_MINIMUM_RATIOS,
        *QUALIFICATION_MAXIMUM_RATIOS,
    ):
        if not _valid_ratio(qualification_policy.get(key)):
            _issue(
                errors,
                "qualification_policy_invalid",
                f"qualification_policy.{key} must be in [0, 1]",
            )
    minimum_opportunity_cases = qualification_policy.get(
        "minimum_semantic_opportunity_case_count"
    )
    if (
        not isinstance(minimum_opportunity_cases, int)
        or isinstance(minimum_opportunity_cases, bool)
        or minimum_opportunity_cases <= 0
    ):
        _issue(
            errors,
            "qualification_opportunity_count_invalid",
            "minimum_semantic_opportunity_case_count must be positive",
        )
    repeat_count = qualification_policy.get("repeat_count")
    if (
        not isinstance(repeat_count, int)
        or isinstance(repeat_count, bool)
        or repeat_count < 2
    ):
        _issue(
            errors,
            "qualification_repeat_count_invalid",
            "qualification repeat_count must be at least 2",
        )
    legacy_repeat_count = qualification_policy.get("legacy_repeat_count")
    if (
        not isinstance(legacy_repeat_count, int)
        or isinstance(legacy_repeat_count, bool)
        or legacy_repeat_count <= 0
    ):
        _issue(
            errors,
            "qualification_legacy_repeat_count_invalid",
            "qualification legacy_repeat_count must be positive",
        )
    contract_hashes = semantic_contract_hashes()

    backends = registry.get("backends")
    if not isinstance(backends, list) or not backends:
        _issue(errors, "backend_registry_empty", "at least one backend is required")
        backends = []

    seen: set[str] = set()
    families: set[str] = set()
    backend_by_id: Dict[str, Dict[str, Any]] = {}
    for item in backends:
        if not isinstance(item, dict):
            _issue(errors, "invalid_backend_entry", "backend entry is not an object")
            continue
        backend_id = str(item.get("backend_id") or "")
        if not backend_id:
            _issue(errors, "backend_id_missing", "backend_id is required")
            continue
        if backend_id in seen:
            _issue(
                errors,
                "duplicate_backend_id",
                f"duplicate backend_id {backend_id}",
                backend_id=backend_id,
            )
            continue
        seen.add(backend_id)
        backend_by_id[backend_id] = item
        if item.get("role") not in {"primary", "sensitivity", "ceiling"}:
            _issue(
                errors,
                "backend_role_invalid",
                "role must be primary, sensitivity, or ceiling",
                backend_id=backend_id,
            )
        family = str(item.get("model_family") or "")
        if family:
            families.add(family)
        else:
            _issue(
                errors,
                "model_family_missing",
                "model_family is required",
                backend_id=backend_id,
            )

        for key in (
            "checkpoint",
            "quantization",
            "runtime",
            "runtime_version",
            "endpoint",
            "model_identifier",
        ):
            if not str(item.get(key) or "").strip():
                _issue(
                    errors,
                    "backend_identity_incomplete",
                    f"{key} is required",
                    backend_id=backend_id,
                )
        if not SHA256_RE.fullmatch(str(item.get("checkpoint_sha256") or "")):
            _issue(
                errors,
                "checkpoint_hash_invalid",
                "checkpoint_sha256 must be frozen",
                backend_id=backend_id,
            )

        hardware = item.get("hardware", {})
        context_length = (
            hardware.get("context_length") if isinstance(hardware, dict) else None
        )
        if (
            not isinstance(context_length, int)
            or isinstance(context_length, bool)
            or context_length <= 0
        ):
            _issue(
                errors,
                "hardware_configuration_incomplete",
                "hardware.context_length must be positive",
                backend_id=backend_id,
            )

        for section_name in ("dataset_reasoner_decoding", "legacy_decoding"):
            section = item.get(section_name)
            if not isinstance(section, dict):
                _issue(
                    errors,
                    "decoding_configuration_missing",
                    f"{section_name} is required",
                    backend_id=backend_id,
                )
                continue
            for hash_key in ("prompt_sha256", "response_schema_sha256"):
                if not SHA256_RE.fullmatch(str(section.get(hash_key) or "")):
                    _issue(
                        errors,
                        "prompt_contract_hash_invalid",
                        f"{section_name}.{hash_key} must be frozen",
                        backend_id=backend_id,
                    )
            expected_prompt_hash = contract_hashes[
                "dataset_reasoner_prompt_sha256"
                if section_name == "dataset_reasoner_decoding"
                else "legacy_prompt_sha256"
            ]
            expected_schema_hash = contract_hashes[
                "dataset_reasoner_schema_sha256"
                if section_name == "dataset_reasoner_decoding"
                else "legacy_schema_sha256"
            ]
            if section.get("prompt_sha256") != expected_prompt_hash:
                _issue(
                    errors,
                    "prompt_hash_mismatch",
                    f"{section_name} prompt hash does not match current frozen code",
                    backend_id=backend_id,
                )
            if section.get("response_schema_sha256") != expected_schema_hash:
                _issue(
                    errors,
                    "response_schema_hash_mismatch",
                    f"{section_name} schema hash does not match current frozen code",
                    backend_id=backend_id,
                )
            if (
                not isinstance(section.get("max_tokens"), int)
                or section["max_tokens"] <= 0
            ):
                _issue(
                    errors,
                    "decoding_configuration_invalid",
                    f"{section_name}.max_tokens must be positive",
                    backend_id=backend_id,
                )
            if section.get("thinking_enabled") is not False:
                _issue(
                    errors,
                    "thinking_configuration_invalid",
                    f"{section_name}.thinking_enabled must be false",
                    backend_id=backend_id,
                )
            if section_name == "dataset_reasoner_decoding":
                if section.get("temperature") != 0:
                    _issue(
                        errors,
                        "dataset_reasoner_temperature_invalid",
                        "dataset reasoner temperature must be 0",
                        backend_id=backend_id,
                    )
                seed = section.get("seed")
                if not isinstance(seed, int) or isinstance(seed, bool):
                    _issue(
                        errors,
                        "dataset_reasoner_seed_invalid",
                        "dataset reasoner seed must be an integer",
                        backend_id=backend_id,
                    )
            else:
                if section.get("temperature") != 0.2:
                    _issue(
                        errors,
                        "legacy_temperature_invalid",
                        "legacy temperature must remain 0.2",
                        backend_id=backend_id,
                    )
                if section.get("seed") is not None:
                    _issue(
                        errors,
                        "legacy_seed_invalid",
                        "legacy seed must remain unset",
                        backend_id=backend_id,
                    )
                if section.get("max_tokens") != 1000:
                    _issue(
                        errors,
                        "legacy_max_tokens_invalid",
                        "legacy max_tokens must remain 1000",
                        backend_id=backend_id,
                    )

        qualification = item.get("qualification")
        if not isinstance(qualification, dict):
            _issue(
                errors,
                "qualification_missing",
                "qualification record is required",
                backend_id=backend_id,
            )
        else:
            if qualification.get("eligible") is not True:
                _issue(
                    errors,
                    "backend_not_qualified",
                    "qualification.eligible must be true before freeze",
                    backend_id=backend_id,
                )
            ratio_keys = set(QUALIFICATION_MINIMUM_RATIOS.values()) | set(
                QUALIFICATION_MAXIMUM_RATIOS.values()
            )
            for ratio_key in sorted(ratio_keys):
                if not _valid_ratio(qualification.get(ratio_key)):
                    _issue(
                        errors,
                        "qualification_metric_invalid",
                        f"qualification.{ratio_key} must be in [0, 1]",
                        backend_id=backend_id,
                    )
            for count_key in (
                "semantic_opportunity_case_count",
                "repeat_count",
                "attempt_count",
                "legacy_repeat_count",
                "legacy_attempt_count",
            ):
                value = qualification.get(count_key)
                if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                    _issue(
                        errors,
                        "qualification_count_invalid",
                        f"qualification.{count_key} must be positive",
                        backend_id=backend_id,
                    )
            opportunity_count = qualification.get("semantic_opportunity_case_count")
            minimum_opportunities = qualification_policy.get(
                "minimum_semantic_opportunity_case_count"
            )
            if (
                isinstance(opportunity_count, int)
                and isinstance(minimum_opportunities, int)
                and opportunity_count < minimum_opportunities
            ):
                _issue(
                    errors,
                    "backend_opportunity_count_below_threshold",
                    "semantic-opportunity calibration count is below the frozen policy",
                    backend_id=backend_id,
                )
            if qualification.get("repeat_count") != repeat_count:
                _issue(
                    errors,
                    "backend_repeat_count_mismatch",
                    "dataset repeat count does not match the frozen policy",
                    backend_id=backend_id,
                )
            if qualification.get("legacy_repeat_count") != legacy_repeat_count:
                _issue(
                    errors,
                    "backend_legacy_repeat_count_mismatch",
                    "legacy repeat count does not match the frozen policy",
                    backend_id=backend_id,
                )
            if (
                isinstance(opportunity_count, int)
                and isinstance(repeat_count, int)
                and qualification.get("attempt_count")
                != opportunity_count * repeat_count
            ):
                _issue(
                    errors,
                    "backend_attempt_count_mismatch",
                    "dataset attempt count is not opportunity_count * repeat_count",
                    backend_id=backend_id,
                )
            if (
                isinstance(opportunity_count, int)
                and isinstance(legacy_repeat_count, int)
                and qualification.get("legacy_attempt_count")
                != opportunity_count * legacy_repeat_count
            ):
                _issue(
                    errors,
                    "backend_legacy_attempt_count_mismatch",
                    "legacy attempt count is not opportunity_count * legacy_repeat_count",
                    backend_id=backend_id,
                )

            below_codes = {
                "contract_valid_rate": "backend_contract_rate_below_threshold",
                "target_scope_valid_rate": "backend_target_rate_below_threshold",
            }
            for policy_key, metric_key in QUALIFICATION_MINIMUM_RATIOS.items():
                metric = qualification.get(metric_key)
                threshold = qualification_policy.get(policy_key)
                if _valid_ratio(metric) and _valid_ratio(threshold):
                    if float(metric) < float(threshold):
                        _issue(
                            errors,
                            below_codes.get(
                                metric_key,
                                "backend_qualification_minimum_below_threshold",
                            ),
                            f"{metric_key} is below frozen {policy_key}",
                            backend_id=backend_id,
                        )
            above_codes = {
                "timeout_rate": "backend_timeout_rate_above_threshold",
            }
            for policy_key, metric_key in QUALIFICATION_MAXIMUM_RATIOS.items():
                metric = qualification.get(metric_key)
                threshold = qualification_policy.get(policy_key)
                if _valid_ratio(metric) and _valid_ratio(threshold):
                    if float(metric) > float(threshold):
                        _issue(
                            errors,
                            above_codes.get(
                                metric_key,
                                "backend_qualification_maximum_above_threshold",
                            ),
                            f"{metric_key} exceeds frozen {policy_key}",
                            backend_id=backend_id,
                        )

            report_path = _check_file_identity(
                path,
                qualification.get("qualification_report_file"),
                qualification.get("qualification_report_sha256"),
                errors,
                label=f"qualification report for {backend_id}",
            )
            if report_path is not None and report_path.is_file():
                try:
                    report = load_json(report_path)
                except Exception as exc:  # noqa: BLE001
                    _issue(
                        errors,
                        "qualification_report_unreadable",
                        str(exc),
                        backend_id=backend_id,
                    )
                    report = {}
                if report.get("schema_version") != "semantic-backend-qualification/v1":
                    _issue(
                        errors,
                        "qualification_report_schema_invalid",
                        "expected semantic-backend-qualification/v1",
                        backend_id=backend_id,
                    )
                if report.get("gold_accessed") is not False:
                    _issue(
                        errors,
                        "qualification_report_gold_boundary_invalid",
                        "qualification report must record gold_accessed=false",
                        backend_id=backend_id,
                    )
                if report.get("contract_hashes") != contract_hashes:
                    _issue(
                        errors,
                        "qualification_report_contract_mismatch",
                        "qualification report used different prompt/schema contracts",
                        backend_id=backend_id,
                    )
                selected_model = report.get("backend_identity", {}).get(
                    "selected_model_identifier"
                )
                if selected_model != item.get("model_identifier"):
                    _issue(
                        errors,
                        "qualification_report_model_mismatch",
                        "qualification report model does not match registry identity",
                        backend_id=backend_id,
                    )
                report_dataset = report.get("dataset_reasoner", {})
                report_legacy = report.get("legacy", {})
                report_values = {
                    "calibration_manifest_sha256": report.get(
                        "calibration_manifest_sha256"
                    ),
                    "qualification_vocabulary_sha256": report.get(
                        "annotation_vocabulary_sha256"
                    ),
                    "semantic_opportunity_case_count": report.get(
                        "semantic_opportunity_case_count"
                    ),
                    "repeat_count": report_dataset.get("repeat_count"),
                    "attempt_count": report_dataset.get("attempt_count"),
                    "contract_valid_rate": report_dataset.get("contract_valid_rate"),
                    "target_scope_valid_rate": report_dataset.get(
                        "target_scope_valid_rate"
                    ),
                    "replay_identity_rate": report_dataset.get("replay_identity_rate"),
                    "exact_repeatability_rate": report_dataset.get(
                        "exact_repeatability_rate"
                    ),
                    "timeout_rate": report_dataset.get("timeout_rate"),
                    "truncation_rate": report_dataset.get("truncation_rate"),
                    "context_fit_rate": report_dataset.get("context_fit_rate"),
                    "context_fit_observed_fraction": report_dataset.get(
                        "context_fit_observed_fraction"
                    ),
                    "legacy_repeat_count": report_legacy.get("repeat_count"),
                    "legacy_attempt_count": report_legacy.get("attempt_count"),
                    "legacy_contract_valid_rate": report_legacy.get(
                        "contract_valid_rate"
                    ),
                    "legacy_timeout_rate": report_legacy.get("timeout_rate"),
                    "legacy_truncation_rate": report_legacy.get("truncation_rate"),
                    "legacy_context_fit_rate": report_legacy.get("context_fit_rate"),
                    "legacy_context_fit_observed_fraction": report_legacy.get(
                        "context_fit_observed_fraction"
                    ),
                }
                for summary_key, report_value in report_values.items():
                    if qualification.get(summary_key) != report_value:
                        _issue(
                            errors,
                            "qualification_report_summary_mismatch",
                            f"qualification.{summary_key} differs from report",
                            backend_id=backend_id,
                        )
            if not SHA256_RE.fullmatch(
                str(qualification.get("calibration_manifest_sha256") or "")
            ):
                _issue(
                    errors,
                    "qualification_manifest_hash_invalid",
                    "qualification calibration manifest hash must be frozen",
                    backend_id=backend_id,
                )
            if not SHA256_RE.fullmatch(
                str(qualification.get("qualification_vocabulary_sha256") or "")
            ):
                _issue(
                    errors,
                    "qualification_vocabulary_hash_invalid",
                    "qualification vocabulary hash must be frozen",
                    backend_id=backend_id,
                )
            if qualification.get("calibration_manifest_sha256") != (
                qualification_policy.get("calibration_manifest_sha256")
            ):
                _issue(
                    errors,
                    "backend_calibration_manifest_mismatch",
                    "backend qualification used a different calibration manifest",
                    backend_id=backend_id,
                )
            if qualification.get("qualification_vocabulary_sha256") != (
                qualification_policy.get("calibration_vocabulary_sha256")
            ):
                _issue(
                    errors,
                    "backend_qualification_vocabulary_mismatch",
                    "backend qualification used a different calibration vocabulary",
                    backend_id=backend_id,
                )

    required_families = registry.get("required_model_families")
    valid_required_families = isinstance(required_families, list) and all(
        isinstance(item, str) and bool(item) for item in required_families
    )
    if not valid_required_families or len(set(required_families)) < (
        REQUIRED_BACKEND_FAMILY_COUNT
    ):
        _issue(
            errors,
            "required_model_families_invalid",
            f"list at least {REQUIRED_BACKEND_FAMILY_COUNT} frozen model families",
        )
        required_families = []
    missing_families = sorted(set(required_families) - families)
    if missing_families:
        _issue(
            errors,
            "required_model_families_missing",
            f"unregistered required families: {missing_families}",
        )
    if len(families) < REQUIRED_BACKEND_FAMILY_COUNT:
        _issue(
            errors,
            "backend_panel_too_small",
            f"protocol v1 requires at least {REQUIRED_BACKEND_FAMILY_COUNT} distinct model families",
        )
    primary_id = str(registry.get("primary_backend_id") or "")
    primary = backend_by_id.get(primary_id)
    if primary is None:
        _issue(
            errors, "primary_backend_missing", "primary_backend_id is not registered"
        )
    elif primary.get("role") != "primary":
        _issue(
            errors,
            "primary_backend_role",
            "selected primary backend must have role=primary",
        )
    primary_roles = [
        item
        for item in backends
        if isinstance(item, dict) and item.get("role") == "primary"
    ]
    if len(primary_roles) != 1:
        _issue(
            errors,
            "primary_backend_count",
            "exactly one registered backend must have role=primary",
        )

    ceiling = [
        item
        for item in backends
        if isinstance(item, dict) and item.get("role") == "ceiling"
    ]
    if ceiling:
        warnings.append(
            {
                "code": "ceiling_backend_registered",
                "detail": "ceiling results are confirmatory and may not replace the primary backend",
            }
        )
    return {
        "status": "ready" if not errors else "blocked",
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "backend_count": len(backends),
            "family_count": len(families),
            "primary_backend_id": primary_id or None,
        },
    }


def preflight_power_analysis(
    path: Path,
    *,
    required_dataset_count: Any,
    required_opportunity_count: Any,
) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [{"code": "power_analysis_unreadable", "detail": str(exc)}],
        }
    if payload.get("schema_version") != POWER_SCHEMA_VERSION:
        _issue(errors, "power_schema_version", f"expected {POWER_SCHEMA_VERSION}")
    if payload.get("protocol_version") != "semantic-architecture-protocol/v1":
        _issue(
            errors,
            "power_protocol_version",
            "expected semantic-architecture-protocol/v1",
        )
    if payload.get("status") != "frozen":
        _issue(
            errors, "power_analysis_not_frozen", "power analysis status must be frozen"
        )
    if payload.get("primary_statistical_unit") != "dataset":
        _issue(errors, "power_statistical_unit", "power analysis unit must be dataset")
    if payload.get("primary_outcome") != PRIMARY_POWER_OUTCOME:
        _issue(
            errors,
            "power_primary_outcome_invalid",
            f"primary outcome must be {PRIMARY_POWER_OUTCOME}",
        )
    if not _valid_ratio(payload.get("selective_risk_bound")):
        _issue(
            errors, "power_risk_bound_invalid", "selective risk bound must be in [0, 1]"
        )
    effect = payload.get("minimum_meaningful_effect")
    if (
        not isinstance(effect, (int, float))
        or isinstance(effect, bool)
        or float(effect) <= 0
    ):
        _issue(
            errors,
            "power_effect_invalid",
            "minimum meaningful effect must be positive",
        )
    if not _valid_ratio(payload.get("alpha")) or float(payload.get("alpha") or 0) <= 0:
        _issue(errors, "power_alpha_invalid", "alpha must be in (0, 1]")
    if (
        not _valid_ratio(payload.get("target_power"))
        or float(payload.get("target_power") or 0) <= 0
    ):
        _issue(errors, "power_target_invalid", "target power must be in (0, 1]")
    if not SHA256_RE.fullmatch(str(payload.get("calibration_manifest_sha256") or "")):
        _issue(
            errors,
            "power_calibration_hash_invalid",
            "calibration manifest hash must be frozen",
        )
    if not SHA256_RE.fullmatch(str(payload.get("calibration_statistics_sha256") or "")):
        _issue(
            errors,
            "power_calibration_statistics_hash_invalid",
            "calibration statistics hash must be frozen",
        )
    calibration_sources = payload.get("calibration_sources")
    if not isinstance(calibration_sources, dict) or set(calibration_sources) != {
        "manifest",
        "statistics",
    }:
        _issue(
            errors,
            "power_calibration_sources_invalid",
            "power analysis must bind calibration manifest and statistics files",
        )
    else:
        for source_name, top_hash_key in (
            ("manifest", "calibration_manifest_sha256"),
            ("statistics", "calibration_statistics_sha256"),
        ):
            source = calibration_sources.get(source_name)
            if not isinstance(source, dict):
                _issue(
                    errors,
                    "power_calibration_sources_invalid",
                    f"calibration source {source_name} must be an object",
                )
                continue
            _check_file_identity(
                path,
                source.get("file"),
                source.get("sha256"),
                errors,
                label=f"power calibration {source_name}",
            )
            if source.get("sha256") != payload.get(top_hash_key):
                _issue(
                    errors,
                    "power_calibration_source_hash_mismatch",
                    f"calibration source {source_name} differs from the top-level hash",
                )
    if not str(payload.get("method") or "").strip():
        _issue(errors, "power_method_missing", "cluster-aware method is required")
    assumptions = payload.get("assumptions")
    if not isinstance(assumptions, dict):
        _issue(errors, "power_assumptions_shape", "assumptions must be an object")
    else:
        if assumptions.get("required_dataset_count") != required_dataset_count:
            _issue(
                errors,
                "power_dataset_count_mismatch",
                "power-analysis dataset count differs from manifest design",
            )
        if (
            assumptions.get("required_semantic_opportunity_case_count")
            != required_opportunity_count
        ):
            _issue(
                errors,
                "power_opportunity_count_mismatch",
                "power-analysis opportunity count differs from manifest design",
            )
    recalculation = validate_power_analysis(payload)
    errors.extend(recalculation["errors"])
    planning_inputs = payload.get("planning_inputs")
    if isinstance(planning_inputs, dict):
        try:
            verify_calibration_sources(planning_inputs, owner=path)
        except Exception as exc:  # noqa: BLE001
            _issue(errors, "power_calibration_binding_invalid", str(exc))
    return {"status": "ready" if not errors else "blocked", "errors": errors}


def _check_blind_gold(
    gold: Dict[str, Any],
    errors: List[Dict[str, Any]],
    *,
    case_id: str,
) -> set[str]:
    if gold.get("schema_version") != "blind-semantic-gold/v1":
        _issue(
            errors,
            "gold_schema_version",
            "expected blind-semantic-gold/v1",
            case_id=case_id,
        )
    if gold.get("protocol_version") != "semantic-architecture-protocol/v1":
        _issue(
            errors,
            "gold_protocol_version",
            "expected semantic-architecture-protocol/v1",
            case_id=case_id,
        )
    if gold.get("annotation_stage") != "consensus":
        _issue(
            errors,
            "gold_not_consensus",
            "blind gold must be a consensus artifact",
            case_id=case_id,
        )
    if gold.get("model_outputs_visible") is not False:
        _issue(
            errors,
            "gold_model_visibility",
            "model_outputs_visible must be false",
            case_id=case_id,
        )
    if gold.get("developer_participation") is not False:
        _issue(
            errors,
            "gold_developer_participation",
            "developer_participation must be false",
            case_id=case_id,
        )
    if not str(gold.get("annotator_id") or ""):
        _issue(
            errors,
            "gold_annotator_id_missing",
            "consensus annotator_id is required",
            case_id=case_id,
        )
    if not str(gold.get("submission_id") or ""):
        _issue(
            errors,
            "gold_submission_id_missing",
            "consensus submission_id is required",
            case_id=case_id,
        )
    for key in (
        "source_bundle_sha256",
        "annotation_packet_sha256",
        "vocabulary_sha256",
    ):
        if not SHA256_RE.fullmatch(str(gold.get(key) or "")):
            _issue(
                errors,
                "gold_input_hash_invalid",
                f"{key} must be frozen",
                case_id=case_id,
            )
    adjudication = gold.get("adjudication")
    if not isinstance(adjudication, dict):
        _issue(
            errors,
            "gold_adjudication_missing",
            "consensus gold must retain adjudication provenance",
            case_id=case_id,
        )
    else:
        artifact_ids = adjudication.get("independent_artifact_ids")
        if (
            not isinstance(artifact_ids, list)
            or len(artifact_ids) != 2
            or len(set(str(item) for item in artifact_ids)) != 2
            or any(not isinstance(item, str) or not item for item in artifact_ids)
        ):
            _issue(
                errors,
                "gold_independent_artifacts_invalid",
                "exactly two distinct independent annotation artifact ids are required",
                case_id=case_id,
            )
        disagreement_count = adjudication.get("disagreement_count")
        if (
            not isinstance(disagreement_count, int)
            or isinstance(disagreement_count, bool)
            or disagreement_count < 0
        ):
            _issue(
                errors,
                "gold_disagreement_count_invalid",
                "disagreement_count must be a non-negative integer",
                case_id=case_id,
            )
        if not isinstance(adjudication.get("unresolved_slots"), list):
            _issue(
                errors,
                "gold_unresolved_slots_invalid",
                "unresolved_slots must be a list",
                case_id=case_id,
            )
        independent_artifacts = adjudication.get("independent_artifacts")
        if (
            not isinstance(independent_artifacts, list)
            or len(independent_artifacts) != 2
        ):
            _issue(
                errors,
                "gold_independent_artifact_provenance_invalid",
                "exactly two detailed independent artifact records are required",
                case_id=case_id,
            )
        else:
            for record in independent_artifacts:
                if (
                    not isinstance(record, dict)
                    or any(
                        not str(record.get(key) or "")
                        for key in ("submission_id", "annotator_id")
                    )
                    or not SHA256_RE.fullmatch(str(record.get("artifact_sha256") or ""))
                ):
                    _issue(
                        errors,
                        "gold_independent_artifact_provenance_invalid",
                        "independent artifact identity/hash is incomplete",
                        case_id=case_id,
                    )
        if not SHA256_RE.fullmatch(
            str(adjudication.get("disagreement_report_sha256") or "")
        ):
            _issue(
                errors,
                "gold_disagreement_hash_invalid",
                "disagreement report hash must be frozen",
                case_id=case_id,
            )
        if not isinstance(adjudication.get("resolutions"), list):
            _issue(
                errors,
                "gold_resolutions_invalid",
                "resolutions must be a list",
                case_id=case_id,
            )
    if not SHA256_RE.fullmatch(str(gold.get("source_bundle_sha256") or "")):
        _issue(
            errors,
            "source_bundle_hash_invalid",
            "source bundle hash must be frozen",
            case_id=case_id,
        )

    fields = gold.get("fields")
    if not isinstance(fields, list) or not fields:
        _issue(errors, "gold_fields_empty", "gold must contain fields", case_id=case_id)
        return set()
    paths: set[str] = set()
    for field in fields:
        if not isinstance(field, dict):
            _issue(
                errors,
                "gold_field_shape",
                "gold field is not an object",
                case_id=case_id,
            )
            continue
        field_path = str(field.get("field_path") or "")
        if not field_path:
            _issue(
                errors,
                "gold_field_path_missing",
                "field_path is required",
                case_id=case_id,
            )
            continue
        if field_path in paths:
            _issue(
                errors,
                "duplicate_gold_field",
                f"duplicate field {field_path}",
                case_id=case_id,
            )
            continue
        paths.add(field_path)
        applicability = field.get("applicability")
        if not isinstance(applicability, dict) or set(applicability) != set(
            EVALUATED_PROPERTIES
        ):
            _issue(
                errors,
                "gold_applicability_incomplete",
                f"{field_path} must declare all four applicability properties",
                case_id=case_id,
            )
            continue
        if any(not isinstance(value, bool) for value in applicability.values()):
            _issue(
                errors,
                "gold_applicability_invalid",
                f"{field_path} applicability values must be boolean",
                case_id=case_id,
            )
            continue
        rationales = field.get("rationales")
        if not isinstance(rationales, dict) or set(rationales) != set(
            EVALUATED_PROPERTIES
        ):
            _issue(
                errors,
                "gold_rationales_incomplete",
                f"{field_path} must declare property-level rationales",
                case_id=case_id,
            )
            rationales = {}
        evidence = field.get("gold_evidence")
        if not isinstance(evidence, list):
            _issue(
                errors,
                "gold_evidence_shape",
                f"{field_path} evidence must be a list",
                case_id=case_id,
            )
            evidence = []
        evidence_properties = {
            str(item.get("property")) for item in evidence if isinstance(item, dict)
        }
        evidence_ids: set[str] = set()
        for item in evidence:
            if not isinstance(item, dict):
                _issue(
                    errors,
                    "gold_evidence_item_shape",
                    f"{field_path} evidence item is invalid",
                    case_id=case_id,
                )
                continue
            evidence_id = str(item.get("evidence_id") or "")
            if not evidence_id or evidence_id in evidence_ids:
                _issue(
                    errors,
                    "gold_evidence_id_invalid",
                    f"{field_path} evidence ids must be non-empty and unique",
                    case_id=case_id,
                )
            evidence_ids.add(evidence_id)
            if not str(item.get("catalog_evidence_id") or ""):
                _issue(
                    errors,
                    "gold_catalog_evidence_id_missing",
                    f"{field_path} evidence must reference the frozen catalog",
                    case_id=case_id,
                )
            if item.get("property") not in EVALUATED_PROPERTIES:
                _issue(
                    errors,
                    "gold_evidence_property_invalid",
                    f"{field_path} evidence property is outside the evaluated contract",
                    case_id=case_id,
                )
            if item.get("field_path") != field_path:
                _issue(
                    errors,
                    "gold_evidence_field_mismatch",
                    f"{field_path} evidence points elsewhere",
                    case_id=case_id,
                )
            for key in ("source_type", "selector", "strength", "support"):
                if not str(item.get(key) or "").strip():
                    _issue(
                        errors,
                        "gold_evidence_incomplete",
                        f"{field_path} evidence requires {key}",
                        case_id=case_id,
                    )
            if not SHA256_RE.fullmatch(str(item.get("source_sha256") or "")):
                _issue(
                    errors,
                    "gold_evidence_hash_invalid",
                    f"{field_path} evidence source hash is invalid",
                    case_id=case_id,
                )
        for property_name in EVALUATED_PROPERTIES:
            expected = field.get(
                {
                    "physical_type": "correct_physical_type",
                    "logical_type": "correct_logical_type",
                    "semantic_type": "correct_semantic_type",
                    "unit": "unit",
                }[property_name]
            )
            if applicability[property_name] and expected not in (None, ""):
                if property_name not in evidence_properties:
                    _issue(
                        errors,
                        "gold_known_value_without_evidence",
                        f"{field_path}.{property_name} has a value but no property evidence",
                        case_id=case_id,
                    )
            if not applicability[property_name] and expected not in (None, ""):
                _issue(
                    errors,
                    "gold_na_with_value",
                    f"{field_path}.{property_name} is N/A but has value {expected!r}",
                    case_id=case_id,
                )
            if (
                expected in (None, "")
                and not str(rationales.get(property_name) or "").strip()
            ):
                _issue(
                    errors,
                    "gold_rationale_missing",
                    f"{field_path}.{property_name} unknown/N/A requires a rationale",
                    case_id=case_id,
                )
    try:
        list(gold_slots(gold))
    except ValueError as exc:
        _issue(errors, "gold_semantics_invalid", str(exc), case_id=case_id)
    return paths


def preflight_blind_manifest(path: Path) -> Dict[str, Any]:
    errors: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    try:
        manifest = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [{"code": "manifest_unreadable", "detail": str(exc)}],
            "warnings": [],
            "summary": {"case_count": 0, "semantic_opportunity_case_count": 0},
        }

    if manifest.get("schema_version") != "minimal-architecture-manifest/v2":
        _issue(
            errors,
            "manifest_schema_version",
            "expected minimal-architecture-manifest/v2",
        )
    if manifest.get("protocol_version") != "semantic-architecture-protocol/v1":
        _issue(
            errors,
            "manifest_protocol_version",
            "expected semantic-architecture-protocol/v1",
        )
    if manifest.get("benchmark_role") != "blind_external":
        _issue(
            errors, "manifest_benchmark_role", "benchmark_role must be blind_external"
        )
    if not str(manifest.get("frozen_at") or ""):
        _issue(errors, "manifest_not_frozen", "frozen_at is required")

    policy = manifest.get("annotation_policy", {})
    if not isinstance(policy, dict):
        _issue(errors, "annotation_policy_shape", "annotation_policy must be an object")
        policy = {}
    expected_policy = {
        "independent_annotator_count": 2,
        "developer_participation": False,
        "model_outputs_visible": False,
        "consensus_after_independent_freeze": True,
    }
    for key, expected in expected_policy.items():
        if policy.get(key) != expected:
            _issue(
                errors, "annotation_policy_invalid", f"{key} must equal {expected!r}"
            )
    _check_file_identity(
        path,
        policy.get("handbook_file"),
        policy.get("handbook_sha256"),
        errors,
        label="annotation handbook",
    )
    vocabulary_path = _check_file_identity(
        path,
        policy.get("vocabulary_file"),
        policy.get("vocabulary_sha256"),
        errors,
        label="annotation vocabulary",
    )
    if vocabulary_path is not None and vocabulary_path.is_file():
        try:
            vocabulary_report = validate_vocabulary(load_json(vocabulary_path))
            errors.extend(vocabulary_report["errors"])
        except Exception as exc:  # noqa: BLE001
            _issue(errors, "annotation_vocabulary_unreadable", str(exc))
    calibration_summary_path = _check_file_identity(
        path,
        policy.get("annotator_calibration_summary_file"),
        policy.get("annotator_calibration_summary_sha256"),
        errors,
        label="annotator calibration summary",
    )
    qualified_annotator_ids: set[str] = set()
    if calibration_summary_path is not None and calibration_summary_path.is_file():
        calibration_validation = validate_annotator_calibration_summary(
            calibration_summary_path
        )
        errors.extend(calibration_validation["errors"])
        if calibration_validation["status"] == "ready":
            calibration_summary = calibration_validation["payload"]
            if calibration_summary.get("status") != "passed":
                _issue(
                    errors,
                    "annotator_calibration_not_passed",
                    "annotator calibration gate must pass before blind freeze",
                )
            if calibration_summary.get("qualified_handbook_sha256") != policy.get(
                "handbook_sha256"
            ):
                _issue(
                    errors,
                    "annotator_calibration_handbook_mismatch",
                    "blind handbook differs from the version qualified in calibration",
                )
            if calibration_summary.get("qualified_vocabulary_sha256") != policy.get(
                "vocabulary_sha256"
            ):
                _issue(
                    errors,
                    "annotator_calibration_vocabulary_mismatch",
                    "blind vocabulary differs from the version qualified in calibration",
                )
            summary_ids = calibration_summary.get("annotator_ids")
            if isinstance(summary_ids, list):
                qualified_annotator_ids = {str(item) for item in summary_ids}
            declared_ids = policy.get("qualified_annotator_ids")
            if not isinstance(declared_ids, list) or sorted(
                str(item) for item in declared_ids
            ) != sorted(qualified_annotator_ids):
                _issue(
                    errors,
                    "qualified_annotator_ids_mismatch",
                    "annotation policy must bind the two calibration-qualified annotators",
                )

    design = manifest.get("design", {})
    if not isinstance(design, dict):
        _issue(errors, "design_shape", "design must be an object")
        design = {}
    if design.get("primary_statistical_unit") != "dataset":
        _issue(
            errors,
            "statistical_unit_invalid",
            "primary statistical unit must be dataset",
        )
    required_count = design.get("required_dataset_count")
    required_opportunities = design.get("required_semantic_opportunity_case_count")
    if not isinstance(required_count, int) or required_count <= 0:
        _issue(
            errors,
            "required_dataset_count_invalid",
            "required dataset count must be positive",
        )
    if not isinstance(required_opportunities, int) or required_opportunities <= 0:
        _issue(
            errors,
            "required_opportunity_count_invalid",
            "required semantic opportunity count must be positive",
        )
    power_path = _check_file_identity(
        path,
        design.get("power_analysis_file"),
        design.get("power_analysis_sha256"),
        errors,
        label="power analysis",
    )
    if power_path is not None and power_path.is_file():
        power_report = preflight_power_analysis(
            power_path,
            required_dataset_count=required_count,
            required_opportunity_count=required_opportunities,
        )
        errors.extend(power_report["errors"])

    analysis_plan_path = _check_file_identity(
        path,
        design.get("analysis_plan_file"),
        design.get("analysis_plan_sha256"),
        errors,
        label="blind analysis plan",
    )
    if analysis_plan_path is not None and analysis_plan_path.is_file():
        try:
            analysis_plan = load_json(analysis_plan_path)
            plan_validation = validate_analysis_plan(analysis_plan)
            errors.extend(plan_validation["errors"])
            if plan_validation["status"] == "ready":
                verify_analysis_plan_sources(analysis_plan, owner=analysis_plan_path)
                sources = analysis_plan["source_artifacts"]
                if sources["power_analysis"]["sha256"] != design.get(
                    "power_analysis_sha256"
                ):
                    _issue(
                        errors,
                        "analysis_plan_power_mismatch",
                        "blind manifest and analysis plan bind different power analyses",
                    )
                if sources["backend_registry"]["sha256"] != manifest.get(
                    "backend_registry_sha256"
                ):
                    _issue(
                        errors,
                        "analysis_plan_backend_registry_mismatch",
                        "blind manifest and analysis plan bind different backend registries",
                    )
        except Exception as exc:  # noqa: BLE001
            _issue(errors, "analysis_plan_invalid", str(exc))

    selection_path = _check_file_identity(
        path,
        design.get("sampling_selection_file"),
        design.get("sampling_selection_sha256"),
        errors,
        label="blind corpus selection",
    )
    selection_payload: Dict[str, Any] | None = None
    if selection_path is not None and selection_path.is_file():
        selection_validation = validate_blind_selection(selection_path)
        errors.extend(selection_validation["errors"])
        if selection_validation["status"] == "ready":
            selection_payload = selection_validation["payload"]
            selection_power_hash = selection_payload["source_artifacts"][
                "power_analysis"
            ]["sha256"]
            if selection_power_hash != design.get("power_analysis_sha256"):
                _issue(
                    errors,
                    "sampling_selection_power_mismatch",
                    "blind selection and manifest bind different power analyses",
                )

    implementation = design.get("evaluation_implementation")
    if not isinstance(implementation, dict):
        _issue(
            errors,
            "evaluation_implementation_missing",
            "design.evaluation_implementation must bind the frozen analysis code",
        )
        implementation = {}
    if set(implementation) != set(EVALUATION_IMPLEMENTATION_FILES):
        _issue(
            errors,
            "evaluation_implementation_components_invalid",
            "evaluation implementation must bind architecture evaluation, variants, and unit normalization",
        )
    for component, filename in EVALUATION_IMPLEMENTATION_FILES.items():
        record = implementation.get(component)
        if not isinstance(record, dict):
            continue
        implementation_path = _check_file_identity(
            path,
            record.get("file"),
            record.get("sha256"),
            errors,
            label=f"evaluation implementation {component}",
        )
        expected_path = (ROOT / filename).resolve()
        if implementation_path is not None and (
            implementation_path.resolve() != expected_path
        ):
            _issue(
                errors,
                "evaluation_implementation_path_mismatch",
                f"{component} must bind {expected_path}",
            )
        expected_hash = sha256_file(expected_path)
        if record.get("sha256") != expected_hash:
            _issue(
                errors,
                "evaluation_implementation_hash_mismatch",
                f"{component} hash differs from the executing implementation",
            )

    backend_path = _check_file_identity(
        path,
        manifest.get("backend_registry_file"),
        manifest.get("backend_registry_sha256"),
        errors,
        label="backend registry",
    )
    backend_report = (
        preflight_backend_registry(backend_path)
        if backend_path is not None and backend_path.is_file()
        else {
            "status": "blocked",
            "errors": [],
            "warnings": [],
            "summary": {"backend_count": 0, "family_count": 0},
        }
    )
    errors.extend(backend_report["errors"])
    warnings.extend(backend_report["warnings"])

    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        _issue(errors, "manifest_cases_empty", "blind manifest must contain cases")
        cases = []
    if selection_payload is not None:
        selected_cases = selection_payload.get("selected_cases", [])
        selected_ids = [str(item.get("case_id") or "") for item in selected_cases]
        manifest_ids = [
            str(item.get("case_id") or "") for item in cases if isinstance(item, dict)
        ]
        if manifest_ids != selected_ids:
            _issue(
                errors,
                "sampling_selection_case_mismatch",
                "blind manifest case identity/order differs from frozen selection",
            )
        selected_by_id = {
            str(item.get("case_id") or ""): item for item in selected_cases
        }
        for item in cases:
            if not isinstance(item, dict):
                continue
            case_id = str(item.get("case_id") or "")
            selected = selected_by_id.get(case_id)
            if selected is None:
                continue
            if item.get("task_sha256") != selected.get("task_sha256"):
                _issue(
                    errors,
                    "sampling_selection_task_mismatch",
                    "blind manifest task differs from frozen selection",
                    case_id=case_id,
                )
            if item.get("source_bundle_sha256") != selected.get("source_bundle_sha256"):
                _issue(
                    errors,
                    "sampling_selection_source_bundle_mismatch",
                    "blind manifest source bundle differs from frozen selection",
                    case_id=case_id,
                )
    seen_case_ids: set[str] = set()
    seen_task_paths: set[Path] = set()
    semantic_opportunity_cases = 0
    semantic_target_count = 0
    for item in cases:
        if not isinstance(item, dict):
            _issue(errors, "manifest_case_shape", "case entry is not an object")
            continue
        case_id = str(item.get("case_id") or "")
        if not case_id:
            _issue(errors, "case_id_missing", "case_id is required")
            continue
        if case_id in seen_case_ids:
            _issue(
                errors,
                "duplicate_case_id",
                f"duplicate case {case_id}",
                case_id=case_id,
            )
        seen_case_ids.add(case_id)
        if item.get("split") != "blind_external":
            _issue(
                errors,
                "case_split_invalid",
                "split must be blind_external",
                case_id=case_id,
            )
        for key in ("dataset_family", "file_format", "difficulty"):
            if not str(item.get(key) or ""):
                _issue(
                    errors,
                    "case_stratum_missing",
                    f"{key} is required",
                    case_id=case_id,
                )
        task_path = _check_file_identity(
            path,
            item.get("task_file"),
            item.get("task_sha256"),
            errors,
            label="task file",
            case_id=case_id,
        )
        gold_path = _check_file_identity(
            path,
            item.get("gold_file"),
            item.get("gold_sha256"),
            errors,
            label="gold file",
            case_id=case_id,
        )
        packet_path = _check_file_identity(
            path,
            item.get("annotation_packet_file"),
            item.get("annotation_packet_sha256"),
            errors,
            label="neutral annotation packet",
            case_id=case_id,
        )
        source_bundle_path = _check_file_identity(
            path,
            item.get("source_bundle_file"),
            item.get("source_bundle_sha256"),
            errors,
            label="approved source bundle",
            case_id=case_id,
        )
        disagreement_path = _check_file_identity(
            path,
            item.get("disagreement_report_file"),
            item.get("disagreement_report_sha256"),
            errors,
            label="disagreement report",
            case_id=case_id,
        )
        independent = item.get("independent_annotations")
        independent_paths: List[Path] = []
        if not isinstance(independent, list) or len(independent) != 2:
            _issue(
                errors,
                "independent_annotation_manifest_invalid",
                "exactly two independent annotation artifacts are required",
                case_id=case_id,
            )
        else:
            for index, record in enumerate(independent, start=1):
                if not isinstance(record, dict):
                    _issue(
                        errors,
                        "independent_annotation_manifest_invalid",
                        f"independent annotation {index} is not an object",
                        case_id=case_id,
                    )
                    continue
                independent_path = _check_file_identity(
                    path,
                    record.get("artifact_file"),
                    record.get("artifact_sha256"),
                    errors,
                    label=f"independent annotation {index}",
                    case_id=case_id,
                )
                if independent_path is not None:
                    independent_paths.append(independent_path)
        if len(independent_paths) == 2 and qualified_annotator_ids:
            try:
                blind_annotator_ids = {
                    str(load_json(independent_path).get("annotator_id") or "")
                    for independent_path in independent_paths
                }
            except Exception as exc:  # noqa: BLE001
                _issue(
                    errors,
                    "blind_annotator_identity_unreadable",
                    str(exc),
                    case_id=case_id,
                )
            else:
                if blind_annotator_ids != qualified_annotator_ids:
                    _issue(
                        errors,
                        "blind_annotator_not_calibration_qualified",
                        "blind annotations must use the same two qualified annotators",
                        case_id=case_id,
                    )
        if (
            task_path is None
            or gold_path is None
            or packet_path is None
            or source_bundle_path is None
            or disagreement_path is None
            or vocabulary_path is None
            or len(independent_paths) != 2
        ):
            continue
        if task_path in seen_task_paths:
            _issue(
                errors,
                "duplicate_task_file",
                f"task reused by multiple cases: {task_path}",
                case_id=case_id,
            )
        seen_task_paths.add(task_path)
        try:
            task = load_json(task_path)
            gold = load_json(gold_path)
        except Exception as exc:  # noqa: BLE001
            _issue(errors, "case_artifact_unreadable", str(exc), case_id=case_id)
            continue
        task_dataset_id = str(task.get("task", {}).get("dataset_id") or "")
        gold_dataset_id = str(gold.get("dataset_id") or "")
        if case_id != task_dataset_id or case_id != gold_dataset_id:
            _issue(
                errors,
                "case_identity_mismatch",
                f"case={case_id}, task dataset={task_dataset_id}, gold dataset={gold_dataset_id}",
                case_id=case_id,
            )
        gold_paths = _check_blind_gold(gold, errors, case_id=case_id)
        workflow_report = validate_consensus_artifact(
            gold_path,
            artifact_a_path=independent_paths[0],
            artifact_b_path=independent_paths[1],
            disagreement_report_path=disagreement_path,
            packet_path=packet_path,
            source_bundle_path=source_bundle_path,
            vocabulary_path=vocabulary_path,
        )
        for workflow_error in workflow_report["errors"]:
            errors.append({**workflow_error, "case_id": case_id})
        try:
            targets = build_observation_payload(task)["targets"]
        except Exception as exc:  # noqa: BLE001
            _issue(errors, "task_contract_invalid", str(exc), case_id=case_id)
            continue
        if targets:
            semantic_opportunity_cases += 1
        semantic_target_count += len(targets)
        missing_targets = [
            str(target["field_path"])
            for target in targets
            if str(target["field_path"]) not in gold_paths
        ]
        if missing_targets:
            _issue(
                errors,
                "semantic_targets_missing_from_gold",
                f"unscored targets: {missing_targets}",
                case_id=case_id,
            )

    if isinstance(required_count, int) and len(cases) != required_count:
        _issue(
            errors,
            "frozen_dataset_count_mismatch",
            f"manifest has {len(cases)} cases but design requires {required_count}",
        )
    if (
        isinstance(required_opportunities, int)
        and semantic_opportunity_cases < required_opportunities
    ):
        _issue(
            errors,
            "semantic_opportunity_count_insufficient",
            f"found {semantic_opportunity_cases}, required {required_opportunities}",
        )
    if semantic_opportunity_cases == 0:
        warnings.append(
            {
                "code": "no_semantic_opportunities",
                "detail": "the benchmark cannot estimate semantic architecture effects",
            }
        )

    return {
        "schema_version": "semantic-study-preflight/v1",
        "manifest": str(path.resolve()),
        "status": "ready" if not errors else "blocked",
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "case_count": len(cases),
            "semantic_opportunity_case_count": semantic_opportunity_cases,
            "semantic_target_count": semantic_target_count,
            "backend_count": backend_report["summary"].get("backend_count", 0),
            "backend_family_count": backend_report["summary"].get("family_count", 0),
            "primary_backend_id": backend_report["summary"].get("primary_backend_id"),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a frozen blind semantic-study manifest and backend registry."
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--print-contract-hashes",
        action="store_true",
        help="Print the current B/C and D prompt/schema hashes for backend freeze records.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.print_contract_hashes:
        print(json.dumps(semantic_contract_hashes(), indent=2))
        return
    if args.manifest is None:
        parser.error("--manifest is required unless --print-contract-hashes is used")
    report = preflight_blind_manifest(args.manifest)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if report["status"] != "ready":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
