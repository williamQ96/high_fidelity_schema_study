from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .architecture_variants import (
    ExperimentCase,
    MemoizingBackend,
    ModelBackend,
    OpenAICompatibleBackend,
    build_observation_payload,
    load_json,
    run_variant,
)
from .semantic_study_preflight import semantic_contract_hashes, sha256_file
from .semantic_gold_workflow import validate_vocabulary


ROOT = Path(__file__).resolve().parent
SCOPE_ISSUES = {"out_of_scope_field", "out_of_scope_property"}


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _resolve(manifest_path: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    adjacent = (manifest_path.parent / candidate).resolve()
    if adjacent.exists():
        return adjacent
    return (ROOT / candidate).resolve()


def discover_model(api_base: str, requested_model: Optional[str]) -> Dict[str, Any]:
    url = f"{api_base.rstrip('/')}/models"
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read().decode("utf-8")
    payload = json.loads(raw)
    model_ids = [
        str(item["id"])
        for item in payload.get("data", [])
        if isinstance(item, dict) and item.get("id")
    ]
    if requested_model:
        if requested_model not in model_ids:
            raise ValueError(
                f"requested model {requested_model!r} is not exposed by {url}; "
                f"available={model_ids}"
            )
        selected = requested_model
    elif len(model_ids) == 1:
        selected = model_ids[0]
    else:
        raise ValueError(
            "--model is required unless the endpoint exposes exactly one model; "
            f"available={model_ids}"
        )
    return {
        "models_endpoint": url,
        "selected_model_identifier": selected,
        "available_model_identifiers": model_ids,
        "models_response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }


def discover_lm_studio_runtime(
    api_base: str, selected_model: str
) -> Dict[str, Any]:
    """Capture LM Studio's loaded-instance identity when its native API exists."""

    normalized = api_base.rstrip("/")
    server_root = normalized[:-3] if normalized.endswith("/v1") else normalized
    url = f"{server_root}/api/v1/models"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            raw = response.read().decode("utf-8")
        payload = json.loads(raw)
        matches = [
            item
            for item in payload.get("models", [])
            if isinstance(item, dict)
            and str(item.get("key") or item.get("id")) == selected_model
        ]
        if len(matches) != 1:
            return {
                "lm_studio_runtime_metadata_observed": False,
                "lm_studio_models_endpoint": url,
                "lm_studio_runtime_metadata_error": (
                    f"expected one native model record for {selected_model!r}; "
                    f"found {len(matches)}"
                ),
            }
        selected = matches[0]
        loaded_instances = selected.get("loaded_instances", [])
        return {
            "lm_studio_runtime_metadata_observed": True,
            "lm_studio_models_endpoint": url,
            "lm_studio_models_response_sha256": hashlib.sha256(
                raw.encode("utf-8")
            ).hexdigest(),
            "lm_studio_selected_model_record": selected,
            "lm_studio_selected_model_record_sha256": canonical_hash(selected),
            "lm_studio_loaded_instance_observed": bool(loaded_instances),
            "checkpoint_file_sha256": None,
            "checkpoint_file_sha256_observed": False,
            "runtime_version": None,
            "runtime_version_observed": False,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "lm_studio_runtime_metadata_observed": False,
            "lm_studio_models_endpoint": url,
            "lm_studio_runtime_metadata_error": str(exc),
            "checkpoint_file_sha256": None,
            "checkpoint_file_sha256_observed": False,
            "runtime_version": None,
            "runtime_version_observed": False,
        }


def _response_hash(run: Dict[str, Any]) -> Optional[str]:
    responses = run.get("model_responses", [])
    if len(responses) != 1:
        return None
    value = responses[0].get("response_hash")
    return str(value) if value else None


def _issue_codes(run: Dict[str, Any]) -> set[str]:
    return {
        str(item.get("code"))
        for item in run.get("issues", [])
        if isinstance(item, dict) and item.get("code")
    }


def _has_timeout(run: Dict[str, Any]) -> bool:
    text = json.dumps(run.get("issues", []), ensure_ascii=False).lower()
    return "timed out" in text or "timeout" in text


def _finish_reasons(run: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    for response in run.get("model_responses", []):
        model_info = response.get("model_info", {})
        reason = model_info.get("finish_reason")
        if reason is not None:
            reasons.append(str(reason))
    return reasons


def _physical_call_records(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return per-physical-call records, including legacy fallback attempts."""

    records: List[Dict[str, Any]] = []
    for response in run.get("model_responses", []):
        attempts = response.get("model_info", {}).get("attempts")
        if isinstance(attempts, list) and attempts:
            records.extend(item for item in attempts if isinstance(item, dict))
        elif isinstance(response, dict):
            records.append(response)
    return records


def _context_observation(run: Dict[str, Any], context_length: int) -> Dict[str, Any]:
    """Measure context use per physical call rather than from aggregate telemetry."""

    expected_calls = int(run.get("telemetry", {}).get("model_calls", 0) or 0)
    input_values: List[int] = []
    total_values: List[int] = []
    requested_values: List[int] = []
    for record in _physical_call_records(run):
        telemetry = record.get("telemetry", {})
        input_tokens = telemetry.get("input_tokens")
        output_tokens = telemetry.get("output_tokens")
        if not (
            isinstance(input_tokens, int)
            and not isinstance(input_tokens, bool)
            and input_tokens > 0
            and isinstance(output_tokens, int)
            and not isinstance(output_tokens, bool)
            and output_tokens > 0
        ):
            continue
        input_values.append(input_tokens)
        total_values.append(input_tokens + output_tokens)
        max_tokens = record.get("model_info", {}).get("decoding", {}).get(
            "max_tokens"
        )
        if isinstance(max_tokens, int) and not isinstance(max_tokens, bool):
            requested_values.append(input_tokens + max_tokens)

    observed_calls = len(total_values)
    telemetry_complete = expected_calls > 0 and observed_calls == expected_calls
    context_fit = (
        all(value <= context_length for value in total_values)
        if telemetry_complete
        else None
    )
    request_budget_fit = (
        all(value <= context_length for value in requested_values)
        if telemetry_complete and len(requested_values) == expected_calls
        else None
    )
    return {
        "context_fit": context_fit,
        "request_budget_fit": request_budget_fit,
        "context_telemetry_complete": telemetry_complete,
        "context_telemetry_observed_calls": observed_calls,
        "context_telemetry_expected_calls": expected_calls,
        "max_call_input_tokens": max(input_values) if input_values else None,
        "max_call_total_tokens": max(total_values) if total_values else None,
        "max_requested_context_tokens": (
            max(requested_values) if requested_values else None
        ),
    }


def _rate(values: List[bool]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def _mean(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)


def _load_calibration_cases(manifest_path: Path) -> List[Dict[str, Any]]:
    manifest = load_json(manifest_path)
    if manifest.get("benchmark_role") not in {
        "synthetic_development",
        "calibration",
    }:
        raise ValueError("backend qualification must never consume a blind manifest")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("calibration manifest contains no cases")
    result: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for entry in cases:
        case_id = str(entry["case_id"])
        if case_id in seen:
            raise ValueError(f"duplicate calibration case_id: {case_id}")
        seen.add(case_id)
        task_path = _resolve(manifest_path, str(entry["task_file"]))
        task_sha256 = sha256_file(task_path)
        expected_task_sha256 = entry.get("task_sha256")
        if expected_task_sha256 is not None and expected_task_sha256 != task_sha256:
            raise ValueError(
                f"calibration task hash mismatch for {case_id}: "
                f"expected {expected_task_sha256}, found {task_sha256}"
            )
        task_payload = load_json(task_path)
        targets = build_observation_payload(task_payload)["targets"]
        declared_target_count = entry.get("semantic_target_count")
        if declared_target_count is not None and declared_target_count != len(targets):
            raise ValueError(
                f"semantic target count mismatch for {case_id}: "
                f"expected {declared_target_count}, found {len(targets)}"
            )
        result.append(
            {
                "case_id": case_id,
                "task_payload": task_payload,
                "task_sha256": task_sha256,
                "semantic_target_count": len(targets),
            }
        )
    return result


def _dataset_attempt(
    backend: ModelBackend,
    case_record: Dict[str, Any],
    repeat_index: int,
    context_length: int,
) -> Dict[str, Any]:
    case = ExperimentCase(
        case_id=case_record["case_id"],
        task_payload=case_record["task_payload"],
        gold_schema={},
        benchmark_role="calibration",
        annotation_vocabulary=case_record.get("annotation_vocabulary"),
    )
    replay_backend = MemoizingBackend(backend)
    b_run = run_variant("B", case, replay_backend).to_dict()
    c_run = run_variant("C", case, replay_backend).to_dict()
    b_hash = _response_hash(b_run)
    c_hash = _response_hash(c_run)
    b_codes = _issue_codes(b_run)
    c_calls = int(c_run["telemetry"]["model_calls"])
    context = _context_observation(b_run, context_length)
    finish_reasons = _finish_reasons(b_run)
    contract_valid = b_run["status"] == "ok"
    scope_evaluable = b_hash is not None and not bool(
        b_codes
        & {
            "dataset_reasoner_failed",
            "invalid_top_level",
            "invalid_top_level_keys",
            "task_id_mismatch",
            "invalid_claims_container",
        }
    )
    scope_valid = scope_evaluable and not bool(b_codes & SCOPE_ISSUES)
    replay_identity = (
        b_hash is not None
        and b_hash == c_hash
        and c_calls == 0
        and c_run["architecture"].get("reused_response_hash") == b_hash
        and replay_backend.physical_model_calls == 1
    )
    truncated = any(
        reason.lower() in {"length", "max_tokens"} for reason in finish_reasons
    )
    return {
        "case_id": case.case_id,
        "repeat_index": repeat_index,
        "semantic_target_count": case_record["semantic_target_count"],
        "contract_valid": contract_valid,
        "target_scope_evaluable": scope_evaluable,
        "target_scope_valid": scope_valid,
        "replay_identity_valid": replay_identity,
        "timeout": _has_timeout(b_run) or _has_timeout(c_run),
        "truncated": truncated,
        **context,
        "b_response_hash": b_hash,
        "c_response_hash": c_hash,
        "physical_model_calls": replay_backend.physical_model_calls,
        "physical_backend_invocations": replay_backend.physical_backend_invocations,
        "b_run": b_run,
        "c_run": c_run,
    }


def _legacy_attempt(
    backend: ModelBackend,
    case_record: Dict[str, Any],
    repeat_index: int,
    context_length: int,
) -> Dict[str, Any]:
    case = ExperimentCase(
        case_id=case_record["case_id"],
        task_payload=case_record["task_payload"],
        gold_schema={},
        benchmark_role="calibration",
        annotation_vocabulary=case_record.get("annotation_vocabulary"),
    )
    measured_backend = MemoizingBackend(backend)
    d_run = run_variant("D", case, measured_backend).to_dict()
    context = _context_observation(d_run, context_length)
    finish_reasons = _finish_reasons(d_run)
    normalized_model_claims = [
        claim
        for claim in d_run["claims"]
        if claim.get("source") == "legacy_per_field_reasoner"
    ]
    return {
        "case_id": case.case_id,
        "repeat_index": repeat_index,
        "semantic_target_count": case_record["semantic_target_count"],
        "contract_valid": d_run["status"] == "ok",
        "timeout": _has_timeout(d_run),
        "truncated": any(
            reason.lower() in {"length", "max_tokens"} for reason in finish_reasons
        ),
        **context,
        "normalized_claims_sha256": canonical_hash(normalized_model_claims),
        "physical_model_calls": measured_backend.physical_model_calls,
        "physical_backend_invocations": measured_backend.physical_backend_invocations,
        "d_run": d_run,
    }


def _repeatability_by_case(
    attempts: List[Dict[str, Any]], hash_key: str, repeat_count: int
) -> Dict[str, Optional[bool]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for attempt in attempts:
        grouped.setdefault(attempt["case_id"], []).append(attempt)
    if repeat_count < 2:
        return {case_id: None for case_id in grouped}
    return {
        case_id: (
            len(items) == repeat_count
            and all(item.get(hash_key) for item in items)
            and len({item[hash_key] for item in items}) == 1
        )
        for case_id, items in grouped.items()
    }


def qualify_backend(
    *,
    backend: ModelBackend,
    manifest_path: Path,
    backend_identity: Dict[str, Any],
    repeat_count: int,
    legacy_repeat_count: int,
    context_length: int,
    annotation_vocabulary: Optional[Dict[str, Any]] = None,
    annotation_vocabulary_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    if repeat_count < 2:
        raise ValueError("repeat_count must be at least 2 to measure repeatability")
    if legacy_repeat_count < 1:
        raise ValueError("legacy_repeat_count must be positive")
    if context_length <= 0:
        raise ValueError("context_length must be positive")
    cases = _load_calibration_cases(manifest_path)
    for case in cases:
        case["annotation_vocabulary"] = annotation_vocabulary
    opportunity_cases = [item for item in cases if item["semantic_target_count"] > 0]

    dataset_attempts = [
        _dataset_attempt(backend, case, repeat_index, context_length)
        for case in opportunity_cases
        for repeat_index in range(1, repeat_count + 1)
    ]
    legacy_attempts = [
        _legacy_attempt(backend, case, repeat_index, context_length)
        for case in opportunity_cases
        for repeat_index in range(1, legacy_repeat_count + 1)
    ]
    dataset_repeatability = _repeatability_by_case(
        dataset_attempts, "b_response_hash", repeat_count
    )
    legacy_repeatability = _repeatability_by_case(
        legacy_attempts, "normalized_claims_sha256", legacy_repeat_count
    )
    dataset_context_values = [
        item["context_fit"]
        for item in dataset_attempts
        if item["context_fit"] is not None
    ]
    legacy_context_values = [
        item["context_fit"]
        for item in legacy_attempts
        if item["context_fit"] is not None
    ]
    dataset_request_budget_values = [
        item["request_budget_fit"]
        for item in dataset_attempts
        if item["request_budget_fit"] is not None
    ]
    legacy_request_budget_values = [
        item["request_budget_fit"]
        for item in legacy_attempts
        if item["request_budget_fit"] is not None
    ]
    dataset_latency = [
        float(item["b_run"]["telemetry"]["latency_ms"]) for item in dataset_attempts
    ]
    legacy_latency = [
        float(item["d_run"]["telemetry"]["latency_ms"]) for item in legacy_attempts
    ]
    return {
        "schema_version": "semantic-backend-qualification/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_evidence_status": "non_blind_operational_qualification_only",
        "gold_accessed": False,
        "backend_identity": backend_identity,
        "contract_hashes": semantic_contract_hashes(),
        "annotation_vocabulary_sha256": annotation_vocabulary_sha256,
        "calibration_manifest_sha256": sha256_file(manifest_path),
        "calibration_case_count": len(cases),
        "semantic_opportunity_case_count": len(opportunity_cases),
        "semantic_opportunity_case_ids": [
            item["case_id"] for item in opportunity_cases
        ],
        "calibration_cases": [
            {
                "case_id": item["case_id"],
                "task_sha256": item["task_sha256"],
                "semantic_target_count": item["semantic_target_count"],
            }
            for item in cases
        ],
        "dataset_reasoner": {
            "repeat_count": repeat_count,
            "attempt_count": len(dataset_attempts),
            "contract_valid_rate": _rate(
                [item["contract_valid"] for item in dataset_attempts]
            ),
            "target_scope_valid_rate": _rate(
                [item["target_scope_valid"] for item in dataset_attempts]
            ),
            "replay_identity_rate": _rate(
                [item["replay_identity_valid"] for item in dataset_attempts]
            ),
            "exact_repeatability_rate": _rate(list(dataset_repeatability.values())),
            "repeatability_by_case": dataset_repeatability,
            "timeout_rate": _rate([item["timeout"] for item in dataset_attempts]),
            "truncation_rate": _rate([item["truncated"] for item in dataset_attempts]),
            "context_fit_rate": _rate(dataset_context_values),
            "context_fit_observed_fraction": (
                len(dataset_context_values) / len(dataset_attempts)
                if dataset_attempts
                else None
            ),
            "request_budget_fit_rate": _rate(dataset_request_budget_values),
            "request_budget_fit_observed_fraction": (
                len(dataset_request_budget_values) / len(dataset_attempts)
                if dataset_attempts
                else None
            ),
            "mean_latency_ms": _mean(dataset_latency),
            "physical_model_calls": sum(
                item["physical_model_calls"] for item in dataset_attempts
            ),
            "input_tokens": sum(
                int(item["b_run"]["telemetry"]["input_tokens"])
                for item in dataset_attempts
            ),
            "output_tokens": sum(
                int(item["b_run"]["telemetry"]["output_tokens"])
                for item in dataset_attempts
            ),
            "attempts": dataset_attempts,
        },
        "legacy": {
            "repeat_count": legacy_repeat_count,
            "attempt_count": len(legacy_attempts),
            "contract_valid_rate": _rate(
                [item["contract_valid"] for item in legacy_attempts]
            ),
            "exact_output_repeatability_rate": _rate(
                [value for value in legacy_repeatability.values() if value is not None]
            ),
            "repeatability_by_case": legacy_repeatability,
            "timeout_rate": _rate([item["timeout"] for item in legacy_attempts]),
            "truncation_rate": _rate([item["truncated"] for item in legacy_attempts]),
            "context_fit_rate": _rate(legacy_context_values),
            "context_fit_observed_fraction": (
                len(legacy_context_values) / len(legacy_attempts)
                if legacy_attempts
                else None
            ),
            "request_budget_fit_rate": _rate(legacy_request_budget_values),
            "request_budget_fit_observed_fraction": (
                len(legacy_request_budget_values) / len(legacy_attempts)
                if legacy_attempts
                else None
            ),
            "mean_latency_ms": _mean(legacy_latency),
            "physical_model_calls": sum(
                item["physical_model_calls"] for item in legacy_attempts
            ),
            "input_tokens": sum(
                int(item["d_run"]["telemetry"]["input_tokens"])
                for item in legacy_attempts
            ),
            "output_tokens": sum(
                int(item["d_run"]["telemetry"]["output_tokens"])
                for item in legacy_attempts
            ),
            "attempts": legacy_attempts,
        },
    }


def qualification_registry_record(
    report: Dict[str, Any],
    *,
    report_file: str,
    report_sha256: str,
    eligible: Optional[bool] = None,
) -> Dict[str, Any]:
    dataset = report["dataset_reasoner"]
    legacy = report["legacy"]
    return {
        "qualification_report_file": report_file,
        "qualification_report_sha256": report_sha256,
        "calibration_manifest_sha256": report["calibration_manifest_sha256"],
        "qualification_vocabulary_sha256": report["annotation_vocabulary_sha256"],
        "semantic_opportunity_case_count": report["semantic_opportunity_case_count"],
        "repeat_count": dataset["repeat_count"],
        "attempt_count": dataset["attempt_count"],
        "contract_valid_rate": dataset["contract_valid_rate"],
        "target_scope_valid_rate": dataset["target_scope_valid_rate"],
        "replay_identity_rate": dataset["replay_identity_rate"],
        "exact_repeatability_rate": dataset["exact_repeatability_rate"],
        "timeout_rate": dataset["timeout_rate"],
        "truncation_rate": dataset["truncation_rate"],
        "context_fit_rate": dataset["context_fit_rate"],
        "context_fit_observed_fraction": dataset["context_fit_observed_fraction"],
        "legacy_repeat_count": legacy["repeat_count"],
        "legacy_attempt_count": legacy["attempt_count"],
        "legacy_contract_valid_rate": legacy["contract_valid_rate"],
        "legacy_timeout_rate": legacy["timeout_rate"],
        "legacy_truncation_rate": legacy["truncation_rate"],
        "legacy_context_fit_rate": legacy["context_fit_rate"],
        "legacy_context_fit_observed_fraction": legacy["context_fit_observed_fraction"],
        "eligible": eligible,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Qualify one local backend without reading gold or model accuracy."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-base", default="http://127.0.0.1:1234/v1")
    parser.add_argument("--model")
    parser.add_argument("--context-length", type=int, required=True)
    parser.add_argument("--repeat-count", type=int, default=2)
    parser.add_argument("--legacy-repeat-count", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--vocabulary", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    discovery = discover_model(args.api_base, args.model)
    runtime_discovery = discover_lm_studio_runtime(
        args.api_base, discovery["selected_model_identifier"]
    )
    backend = OpenAICompatibleBackend(
        api_base=args.api_base,
        model=discovery["selected_model_identifier"],
        timeout_seconds=args.timeout_seconds,
        seed=args.seed,
        max_tokens=args.max_tokens,
    )
    annotation_vocabulary = None
    annotation_vocabulary_sha256 = None
    if args.vocabulary is not None:
        annotation_vocabulary = load_json(args.vocabulary)
        vocabulary_report = validate_vocabulary(annotation_vocabulary)
        if vocabulary_report["status"] != "ready":
            raise ValueError(
                f"invalid qualification vocabulary: {vocabulary_report['errors']}"
            )
        annotation_vocabulary_sha256 = sha256_file(args.vocabulary)
    report = qualify_backend(
        backend=backend,
        manifest_path=args.manifest.resolve(),
        backend_identity={
            **discovery,
            **runtime_discovery,
            "api_base": args.api_base,
            "context_length": args.context_length,
            "timeout_seconds": args.timeout_seconds,
            "dataset_reasoner_seed": args.seed,
            "dataset_reasoner_max_tokens": args.max_tokens,
        },
        repeat_count=args.repeat_count,
        legacy_repeat_count=args.legacy_repeat_count,
        context_length=args.context_length,
        annotation_vocabulary=annotation_vocabulary,
        annotation_vocabulary_sha256=annotation_vocabulary_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: value
                for key, value in report.items()
                if key not in {"dataset_reasoner", "legacy"}
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    print(
        json.dumps(
            {
                "dataset_reasoner": {
                    key: value
                    for key, value in report["dataset_reasoner"].items()
                    if key != "attempts"
                },
                "legacy": {
                    key: value
                    for key, value in report["legacy"].items()
                    if key != "attempts"
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
