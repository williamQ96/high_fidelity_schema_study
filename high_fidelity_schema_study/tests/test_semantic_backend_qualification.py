from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict

import pytest

from high_fidelity_schema_study.architecture_variants import (
    ModelBackendError,
    ModelCompletion,
    ModelTelemetry,
)
from high_fidelity_schema_study.semantic_backend_qualification import qualify_backend
from high_fidelity_schema_study.semantic_backend_qualification import (
    _context_observation,
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def task_payload() -> dict:
    return {
        "task": {
            "task_id": "calibration::case-1",
            "dataset_id": "case-1",
            "file_format": "csv",
            "data_modality": "tabular",
            "deterministic_schema": {
                "fields": [
                    {
                        "field_name": "temp_c",
                        "field_path": "temp_c",
                        "physical_type": "float",
                        "logical_type": "unknown",
                        "semantic_type": "unknown",
                        "unit": None,
                        "shape": None,
                        "description": None,
                        "example_values": ["20.1"],
                        "value_range": [20.1, 20.1],
                        "confidence": 0.8,
                        "uncertainty_reason": "unresolved",
                        "source_evidence": [
                            {
                                "evidence_type": "csv_header",
                                "source": "weather.csv",
                                "detail": "header='temp_c'",
                            }
                        ],
                    }
                ],
                "metadata": {},
            },
            "grounding_snippets": [
                {
                    "source_type": "dataset_readme",
                    "source_name": "README.md",
                    "detail": "line 1",
                    "text": "temp_c is air temperature in Celsius.",
                    "priority": 1,
                }
            ],
            "instructions": [],
        }
    }


def build_manifest(tmp_path: Path, role: str = "calibration") -> Path:
    task_path = tmp_path / "case-1.task.json"
    write_json(task_path, task_payload())
    manifest_path = tmp_path / "manifest.json"
    write_json(
        manifest_path,
        {
            "benchmark_role": role,
            "cases": [
                {
                    "case_id": "case-1",
                    "task_file": task_path.name,
                    "gold_file": "must-not-be-read.gold.json",
                }
            ],
        },
    )
    return manifest_path


class QualificationBackend:
    def __init__(
        self,
        *,
        varying: bool = False,
        out_of_scope: bool = False,
        timeout: bool = False,
    ) -> None:
        self.varying = varying
        self.out_of_scope = out_of_scope
        self.timeout = timeout
        self.dataset_calls = 0
        self.legacy_calls = 0
        self.dataset_payloads: list[dict] = []

    def complete(
        self,
        *,
        system_prompt: str,
        payload: Dict[str, Any],
        response_schema: Dict[str, Any],
        purpose: str,
    ) -> ModelCompletion:
        del system_prompt, response_schema
        self.dataset_calls += 1
        self.dataset_payloads.append(copy.deepcopy(payload))
        if self.timeout:
            raise ModelBackendError(
                "model request timed out",
                telemetry=ModelTelemetry(model_calls=1, failed_calls=1),
            )
        field_path = "outside" if self.out_of_scope else "temp_c"
        value = (
            "air_temperature"
            if not self.varying or self.dataset_calls % 2
            else "surface_temperature"
        )
        evidence_ref = payload["evidence_catalog"][0]["evidence_id"]
        data = {
            "task_id": payload["task_id"],
            "claims": [
                {
                    "field_path": field_path,
                    "property": "semantic_type",
                    "value": value,
                    "evidence_refs": [evidence_ref],
                    "confidence": 0.7,
                    "uncertainty_reason": None,
                }
            ],
            "notes": [],
        }
        return ModelCompletion(
            data=copy.deepcopy(data),
            telemetry=ModelTelemetry(
                model_calls=1,
                input_tokens=100,
                output_tokens=20,
                latency_ms=5,
            ),
            model_info={"model": "fixture", "finish_reason": "stop"},
            raw_text=json.dumps(data, sort_keys=True),
        )


    def complete_legacy(
        self,
        *,
        payload: Dict[str, Any],
        response_schema: Dict[str, Any],
        purpose: str,
    ) -> ModelCompletion:
        del response_schema, purpose
        self.legacy_calls += 1
        target = payload["task"]["annotation_targets"][0]
        data = {
            "task_id": payload["task"]["task_id"],
            "annotations": [
                {
                    "field_path": target["field_path"],
                    "semantic_type": "air_temperature",
                    "logical_type": "measurement",
                    "unit": "degree_Celsius",
                    "description": None,
                    "supporting_evidence": ["F1"],
                    "confidence": 0.7,
                    "uncertainty_reason": None,
                }
            ],
            "conflicts": [],
            "notes": [],
        }
        return ModelCompletion(
            data=data,
            telemetry=ModelTelemetry(
                model_calls=1,
                input_tokens=120,
                output_tokens=25,
                latency_ms=7,
            ),
            model_info={"model": "fixture", "finish_reason": "stop"},
            raw_text=json.dumps(data, sort_keys=True),
        )


class MalformedQualificationBackend(QualificationBackend):
    def complete(
        self,
        *,
        system_prompt: str,
        payload: Dict[str, Any],
        response_schema: Dict[str, Any],
        purpose: str,
    ) -> ModelCompletion:
        del system_prompt, payload, response_schema, purpose
        self.dataset_calls += 1
        raw_text = '{"task_id":"case-1","claims":['
        raise ModelBackendError(
            "model response was not valid contract JSON",
            telemetry=ModelTelemetry(
                model_calls=1,
                input_tokens=100,
                output_tokens=20,
                latency_ms=5,
                failed_calls=1,
            ),
            request_hash="request-hash",
            raw_text=raw_text,
            response_hash="raw-response-hash",
            model_info={"model": "fixture", "finish_reason": "length"},
        )


def run_qualification(tmp_path: Path, backend: QualificationBackend) -> dict:
    return qualify_backend(
        backend=backend,
        manifest_path=build_manifest(tmp_path),
        backend_identity={"model_identifier": "fixture"},
        repeat_count=2,
        legacy_repeat_count=1,
        context_length=4096,
    )


def test_qualification_measures_contract_replay_and_calls_without_gold(
    tmp_path: Path,
) -> None:
    backend = QualificationBackend()

    report = run_qualification(tmp_path, backend)

    dataset = report["dataset_reasoner"]
    legacy = report["legacy"]
    assert report["gold_accessed"] is False
    assert report["semantic_opportunity_case_count"] == 1
    assert dataset["contract_valid_rate"] == 1.0
    assert dataset["target_scope_valid_rate"] == 1.0
    assert dataset["replay_identity_rate"] == 1.0
    assert dataset["exact_repeatability_rate"] == 1.0
    assert dataset["physical_model_calls"] == 2
    assert backend.dataset_calls == 2
    assert all(
        item["c_run"]["telemetry"]["model_calls"] == 0 for item in dataset["attempts"]
    )
    assert legacy["contract_valid_rate"] == 1.0
    assert legacy["exact_output_repeatability_rate"] is None
    assert legacy["physical_model_calls"] == 1
    assert backend.legacy_calls == 1


def test_qualification_detects_nondeterministic_dataset_response(
    tmp_path: Path,
) -> None:
    report = run_qualification(tmp_path, QualificationBackend(varying=True))

    assert report["dataset_reasoner"]["contract_valid_rate"] == 1.0
    assert report["dataset_reasoner"]["replay_identity_rate"] == 1.0
    assert report["dataset_reasoner"]["exact_repeatability_rate"] == 0.0


def test_qualification_treats_out_of_scope_claim_as_contract_failure(
    tmp_path: Path,
) -> None:
    report = run_qualification(tmp_path, QualificationBackend(out_of_scope=True))

    assert report["dataset_reasoner"]["contract_valid_rate"] == 0.0
    assert report["dataset_reasoner"]["target_scope_valid_rate"] == 0.0
    assert report["dataset_reasoner"]["replay_identity_rate"] == 1.0
    assert report["dataset_reasoner"]["exact_repeatability_rate"] == 1.0


def test_qualification_counts_timeout_attempts(tmp_path: Path) -> None:
    report = run_qualification(tmp_path, QualificationBackend(timeout=True))

    dataset = report["dataset_reasoner"]
    assert dataset["contract_valid_rate"] == 0.0
    assert dataset["timeout_rate"] == 1.0
    assert dataset["physical_model_calls"] == 2


def test_contract_invalid_raw_response_replays_with_exact_identity(
    tmp_path: Path,
) -> None:
    report = run_qualification(tmp_path, MalformedQualificationBackend())

    dataset = report["dataset_reasoner"]
    assert dataset["contract_valid_rate"] == 0.0
    assert dataset["target_scope_valid_rate"] == 0.0
    assert dataset["replay_identity_rate"] == 1.0
    assert dataset["exact_repeatability_rate"] == 1.0
    assert dataset["physical_model_calls"] == 2
    for attempt in dataset["attempts"]:
        assert attempt["b_response_hash"] == "raw-response-hash"
        assert attempt["c_response_hash"] == "raw-response-hash"
        assert attempt["c_run"]["telemetry"]["model_calls"] == 0
        assert (
            attempt["c_run"]["architecture"]["reused_response_hash"]
            == "raw-response-hash"
        )


def test_context_fit_uses_input_plus_output_tokens() -> None:
    run = {
        "telemetry": {"model_calls": 1},
        "model_responses": [
            {
                "telemetry": {"input_tokens": 3900, "output_tokens": 300},
                "model_info": {"decoding": {"max_tokens": 500}},
            }
        ],
    }

    observation = _context_observation(run, 4096)

    assert observation["context_fit"] is False
    assert observation["max_call_input_tokens"] == 3900
    assert observation["max_call_total_tokens"] == 4200
    assert observation["request_budget_fit"] is False


def test_context_fit_keeps_legacy_retry_attempts_separate() -> None:
    run = {
        "telemetry": {"model_calls": 2},
        "model_responses": [
            {
                "telemetry": {"input_tokens": 6000, "output_tokens": 300},
                "model_info": {
                    "attempts": [
                        {
                            "telemetry": {
                                "input_tokens": 3000,
                                "output_tokens": 100,
                            },
                            "model_info": {"decoding": {"max_tokens": 1000}},
                        },
                        {
                            "telemetry": {
                                "input_tokens": 3000,
                                "output_tokens": 200,
                            },
                            "model_info": {"decoding": {"max_tokens": 1000}},
                        },
                    ]
                },
            }
        ],
    }

    observation = _context_observation(run, 4096)

    assert observation["context_fit"] is True
    assert observation["context_telemetry_observed_calls"] == 2
    assert observation["max_call_total_tokens"] == 3200
    assert observation["request_budget_fit"] is True


def test_context_fit_is_unknown_when_one_physical_call_lacks_telemetry() -> None:
    run = {
        "telemetry": {"model_calls": 2},
        "model_responses": [
            {
                "model_info": {
                    "attempts": [
                        {
                            "telemetry": {
                                "input_tokens": 100,
                                "output_tokens": 20,
                            }
                        },
                        {"telemetry": {"input_tokens": 0, "output_tokens": 0}},
                    ]
                }
            }
        ],
    }

    observation = _context_observation(run, 4096)

    assert observation["context_fit"] is None
    assert observation["context_telemetry_complete"] is False
    assert observation["context_telemetry_observed_calls"] == 1


def test_qualification_rejects_blind_manifest(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="never consume a blind manifest"):
        qualify_backend(
            backend=QualificationBackend(),
            manifest_path=build_manifest(tmp_path, role="blind_external"),
            backend_identity={"model_identifier": "fixture"},
            repeat_count=2,
            legacy_repeat_count=1,
            context_length=4096,
        )


def test_qualification_requires_two_dataset_repeats(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least 2"):
        qualify_backend(
            backend=QualificationBackend(),
            manifest_path=build_manifest(tmp_path),
            backend_identity={"model_identifier": "fixture"},
            repeat_count=1,
            legacy_repeat_count=1,
            context_length=4096,
        )


def test_qualification_binds_and_supplies_annotation_vocabulary(
    tmp_path: Path,
) -> None:
    backend = QualificationBackend()
    vocabulary = {
        "semantic_types": ["air_temperature"],
        "units": ["Celsius"],
        "unit_aliases": {"C": "Celsius"},
        "unit_patterns": [],
    }

    report = qualify_backend(
        backend=backend,
        manifest_path=build_manifest(tmp_path),
        backend_identity={"model_identifier": "fixture"},
        repeat_count=2,
        legacy_repeat_count=1,
        context_length=4096,
        annotation_vocabulary=vocabulary,
        annotation_vocabulary_sha256="a" * 64,
    )

    assert report["annotation_vocabulary_sha256"] == "a" * 64
    assert all(
        payload["allowed_semantic_types"] == ["air_temperature"]
        and payload["allowed_units"] == ["Celsius"]
        for payload in backend.dataset_payloads
    )


def test_qualification_rejects_stale_task_hash(tmp_path: Path) -> None:
    manifest_path = build_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"][0]["task_sha256"] = "0" * 64
    write_json(manifest_path, manifest)

    with pytest.raises(ValueError, match="task hash mismatch"):
        qualify_backend(
            backend=QualificationBackend(),
            manifest_path=manifest_path,
            backend_identity={"model_identifier": "fixture"},
            repeat_count=2,
            legacy_repeat_count=1,
            context_length=4096,
        )


def test_qualification_rejects_stale_target_count(tmp_path: Path) -> None:
    manifest_path = build_manifest(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"][0]["semantic_target_count"] = 99
    write_json(manifest_path, manifest)

    with pytest.raises(ValueError, match="target count mismatch"):
        qualify_backend(
            backend=QualificationBackend(),
            manifest_path=manifest_path,
            backend_identity={"model_identifier": "fixture"},
            repeat_count=2,
            legacy_repeat_count=1,
            context_length=4096,
        )
