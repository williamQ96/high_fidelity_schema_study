from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

from high_fidelity_schema_study.architecture_evaluation import (
    SlotEvaluation,
    _dataset_level_comparison,
    _bind_backend_registration,
    _sha256_file,
    _selective_curve,
    _validate_b_c_replay,
    accepted_projection,
    evaluate_run,
    gold_slots,
    run_experiment,
)
from high_fidelity_schema_study.architecture_variants import (
    ALLOWED_LOGICAL_TYPES,
    DATASET_REASONER_SYSTEM_PROMPT,
    ExperimentCase,
    ModelBackendError,
    ModelCompletion,
    ModelTelemetry,
    OpenAICompatibleBackend,
    PropertyClaim,
    VariantRun,
    build_observation_payload,
    run_variant,
)


def build_case() -> ExperimentCase:
    task = {
        "task_id": "internal::architecture_demo",
        "dataset_id": "architecture_demo",
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
                    "confidence": 0.8,
                    "source_evidence": [
                        {
                            "evidence_type": "csv_header",
                            "source": "demo.csv",
                            "detail": "header='temp_c'",
                        }
                    ],
                },
                {
                    "field_name": "note",
                    "field_path": "note",
                    "physical_type": "string",
                    "logical_type": "unknown",
                    "semantic_type": "unknown",
                    "unit": None,
                    "confidence": 0.8,
                    "source_evidence": [
                        {
                            "evidence_type": "csv_header",
                            "source": "demo.csv",
                            "detail": "header='note'",
                        }
                    ],
                },
            ],
            "metadata": {},
        },
        "grounding_snippets": [
            {
                "source_type": "dataset_readme",
                "source_name": "README.md",
                "detail": "demo documentation",
                "text": "temp_c is air temperature in Celsius; note is free text.",
                "priority": 1,
            }
        ],
        "instructions": [],
    }
    gold = {
        "dataset_id": "architecture_demo",
        "fields": [
            {
                "field_path": "temp_c",
                "correct_physical_type": "float",
                "correct_logical_type": "measurement",
                "correct_semantic_type": "air_temperature",
                "unit": None,
            },
            {
                "field_path": "note",
                "correct_physical_type": "string",
                "correct_logical_type": "label",
                "correct_semantic_type": "free_text_note",
                "unit": None,
            },
        ],
    }
    return ExperimentCase(
        case_id="architecture_demo",
        task_payload={"task": task},
        gold_schema=gold,
        benchmark_role="test_fixture",
    )


class ScriptedBackend:
    def __init__(
        self, *, invalid_evidence: bool = False, add_unit: bool = False
    ) -> None:
        self.invalid_evidence = invalid_evidence
        self.add_unit = add_unit
        self.purposes: List[str] = []

    def complete(
        self,
        *,
        system_prompt: str,
        payload: Dict[str, Any],
        response_schema: Dict[str, Any],
        purpose: str,
    ) -> ModelCompletion:
        self.purposes.append(purpose)
        telemetry = ModelTelemetry(
            model_calls=1, input_tokens=10, output_tokens=5, latency_ms=2.5
        )
        if purpose.startswith("dataset_reasoner"):
            evidence = ["DOES_NOT_EXIST"] if self.invalid_evidence else ["S1"]
            claims: List[Dict[str, Any]] = [
                {
                    "field_path": "temp_c",
                    "property": "logical_type",
                    "value": "measurement",
                    "evidence_refs": evidence,
                    "confidence": 0.0,
                    "uncertainty_reason": None,
                },
                {
                    "field_path": "temp_c",
                    "property": "semantic_type",
                    "value": "air_temperature",
                    "evidence_refs": evidence,
                    "confidence": 0.0,
                    "uncertainty_reason": None,
                },
                {
                    "field_path": "note",
                    "property": "logical_type",
                    "value": "label",
                    "evidence_refs": evidence,
                    "confidence": 0.0,
                    "uncertainty_reason": None,
                },
                {
                    "field_path": "note",
                    "property": "semantic_type",
                    "value": "free_text_note",
                    "evidence_refs": evidence,
                    "confidence": 0.0,
                    "uncertainty_reason": None,
                },
            ]
            if self.add_unit:
                claims.append(
                    {
                        "field_path": "temp_c",
                        "property": "unit",
                        "value": "Celsius",
                        "evidence_refs": evidence,
                        "confidence": 0.0,
                        "uncertainty_reason": None,
                    }
                )
            return ModelCompletion(
                data={"task_id": payload["task_id"], "claims": claims, "notes": []},
                telemetry=telemetry,
                model_info={"model": "scripted"},
            )

        target = payload["task"]["annotation_targets"][0]["field_path"]
        semantic = "air_temperature" if target == "temp_c" else "free_text_note"
        logical = "measurement" if target == "temp_c" else "label"
        evidence = ["DOES_NOT_EXIST"] if self.invalid_evidence else ["S1"]
        return ModelCompletion(
            data={
                "task_id": payload["task"]["task_id"],
                "annotations": [
                    {
                        "field_path": target,
                        "semantic_type": semantic,
                        "logical_type": logical,
                        "unit": None,
                        "description": None,
                        "supporting_evidence": evidence,
                        "confidence": 0.0,
                        "uncertainty_reason": None,
                    }
                ],
                "conflicts": [],
                "notes": [],
            },
            telemetry=telemetry,
            model_info={"model": "scripted"},
        )


class DatasetResponseBackend(ScriptedBackend):
    def __init__(
        self,
        response: Dict[str, Any] | None = None,
        *,
        model_calls: int = 1,
        exception: Exception | None = None,
    ) -> None:
        super().__init__()
        self.response = response
        self.model_calls = model_calls
        self.exception = exception

    def complete(
        self,
        *,
        system_prompt: str,
        payload: Dict[str, Any],
        response_schema: Dict[str, Any],
        purpose: str,
    ) -> ModelCompletion:
        if not purpose.startswith("dataset_reasoner"):
            return super().complete(
                system_prompt=system_prompt,
                payload=payload,
                response_schema=response_schema,
                purpose=purpose,
            )
        self.purposes.append(purpose)
        if self.exception is not None:
            raise self.exception
        response = self.response
        if response is None:
            response = {"task_id": payload["task_id"], "claims": [], "notes": []}
        return ModelCompletion(
            data=copy.deepcopy(response),
            telemetry=ModelTelemetry(model_calls=self.model_calls),
            model_info={"model": "scripted-response"},
            raw_text=json.dumps(response, sort_keys=True),
        )


def run_bc(
    case: ExperimentCase, backend: Any
) -> tuple[VariantRun, VariantRun, Dict[str, Any]]:
    report = run_experiment(
        [case], variant_ids=["B", "C"], backend=backend, include_runs=True
    )
    b = report["runs"]["B"][0]
    c = report["runs"]["C"][0]

    def restore(item: Dict[str, Any]) -> VariantRun:
        live = run_variant("A", case)
        live.variant_id = item["variant_id"]
        live.status = item["status"]
        live.telemetry = ModelTelemetry(**item["telemetry"])
        live.issues = item["issues"]
        live.model_info = item["model_info"]
        live.model_responses = item["model_responses"]
        live.claims = []
        for claim in item["claims"]:
            claim = dict(claim)
            claim["property_name"] = claim.pop("property")
            live.claims.append(PropertyClaim(**claim))
        return live

    return restore(b), restore(c), report


class ArchitectureVariantTests(unittest.TestCase):
    def test_dataset_reasoner_contract_exposes_logical_type_vocabulary(self) -> None:
        vocabulary = {
            "semantic_types": ["air_temperature"],
            "units": ["Celsius"],
            "unit_aliases": {"C": "Celsius"},
            "unit_patterns": [],
        }
        observation = build_observation_payload(build_case().task_payload, vocabulary)

        self.assertEqual(
            observation["allowed_logical_types"], sorted(ALLOWED_LOGICAL_TYPES)
        )
        self.assertEqual(observation["allowed_semantic_types"], ["air_temperature"])
        self.assertEqual(observation["allowed_units"], ["Celsius"])
        self.assertEqual(observation["unit_aliases"], {"C": "Celsius"})
        self.assertIn("allowed_logical_types", DATASET_REASONER_SYSTEM_PROMPT)
        self.assertIn("allowed_semantic_types", DATASET_REASONER_SYSTEM_PROMPT)

    def test_openai_backend_records_usage_latency_and_cost(self) -> None:
        response_payload = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {"task_id": "demo", "claims": [], "notes": []}
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        }

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(response_payload).encode("utf-8")

        backend = OpenAICompatibleBackend(
            model="test-model",
            input_price_per_million=2.0,
            output_price_per_million=4.0,
        )
        with patch(
            "high_fidelity_schema_study.architecture_variants.urllib.request.urlopen",
            return_value=FakeResponse(),
        ):
            completion = backend.complete(
                system_prompt="strict JSON",
                payload={"task_id": "demo"},
                response_schema={"type": "object"},
                purpose="test",
            )

        self.assertEqual(completion.data["task_id"], "demo")
        self.assertEqual(completion.telemetry.model_calls, 1)
        self.assertEqual(completion.telemetry.input_tokens, 100)
        self.assertEqual(completion.telemetry.output_tokens, 20)
        self.assertAlmostEqual(completion.telemetry.cost_usd, 0.00028)

    def test_legacy_contract_fallback_counts_failed_attempt_tokens(self) -> None:
        first = {
            "id": "first",
            "choices": [{"message": {"content": '{"id":"F1"}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3},
        }
        second_data = {
            "task_id": "demo",
            "annotations": [],
            "conflicts": [],
            "notes": [],
        }
        second = {
            "id": "second",
            "choices": [{"message": {"content": json.dumps(second_data)}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 5},
        }

        class FakeResponse:
            def __init__(self, payload: Dict[str, Any]) -> None:
                self.payload = payload

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(self.payload).encode("utf-8")

        backend = OpenAICompatibleBackend(model="test-model")
        with patch(
            "high_fidelity_schema_study.architecture_variants.urllib.request.urlopen",
            side_effect=[FakeResponse(first), FakeResponse(second)],
        ):
            completion = backend.complete_legacy(
                payload={"task": {"task_id": "demo"}},
                response_schema={"type": "object"},
                purpose="legacy:test",
            )

        self.assertEqual(completion.telemetry.model_calls, 2)
        self.assertEqual(completion.telemetry.input_tokens, 30)
        self.assertEqual(completion.telemetry.output_tokens, 8)
        self.assertEqual(completion.telemetry.failed_calls, 1)
        self.assertEqual(
            completion.model_info["attempts"][0]["contract_error"],
            "JSON did not match the annotation-result shape",
        )

    def test_legacy_total_failure_preserves_both_attempt_records(self) -> None:
        invalid = {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"content": '{"wrong":"shape"}'},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3},
        }

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(invalid).encode("utf-8")

        backend = OpenAICompatibleBackend(model="test-model")
        with patch(
            "high_fidelity_schema_study.architecture_variants.urllib.request.urlopen",
            side_effect=[FakeResponse(), FakeResponse()],
        ):
            with self.assertRaises(ModelBackendError) as captured:
                backend.complete_legacy(
                    payload={"task": {"task_id": "demo"}},
                    response_schema={"type": "object"},
                    purpose="legacy:test",
                )

        error = captured.exception
        self.assertEqual(error.telemetry.model_calls, 2)
        self.assertEqual(len(error.response_records), 2)
        self.assertEqual(
            [item["model_info"]["finish_reason"] for item in error.response_records],
            ["length", "length"],
        )

    def test_architecture_call_counts_and_shared_contract(self) -> None:
        case = build_case()
        report = run_experiment([case], backend=ScriptedBackend(), include_runs=True)

        summaries = report["variant_summaries"]
        self.assertEqual(summaries["A"]["telemetry"]["model_calls"], 0)
        self.assertEqual(summaries["B"]["telemetry"]["model_calls"], 1)
        self.assertEqual(summaries["C"]["telemetry"]["model_calls"], 0)
        self.assertEqual(summaries["C"]["reused_upstream_telemetry"]["model_calls"], 1)
        self.assertEqual(
            summaries["C"]["effective_architecture_telemetry"]["model_calls"], 1
        )
        self.assertEqual(summaries["D"]["telemetry"]["model_calls"], 2)
        provenance = report["execution_control"]["b_c_replay_provenance"][0]
        self.assertTrue(provenance["response_identity_identical"])
        self.assertTrue(provenance["raw_content_identical"])
        self.assertEqual(provenance["c_semantic_generation_calls"], 0)

    def test_c_verifies_evidence_independently_of_confidence(self) -> None:
        case = build_case()
        _, run, _ = run_bc(case, ScriptedBackend())
        claim = accepted_projection(run.claims)[("temp_c", "semantic_type")]

        self.assertEqual(claim.confidence, 0.0)
        self.assertEqual(claim.verification_level, "evidence_grounded")
        self.assertEqual(claim.verification_status, "supported")
        self.assertEqual(claim.decision, "accepted")

    def test_nonexistent_evidence_separates_b_c_and_legacy_d(self) -> None:
        case = build_case()
        backend = ScriptedBackend(invalid_evidence=True)

        b_run, c_run, _ = run_bc(case, backend)
        d_run = run_variant("D", case, backend)

        self.assertIn(("temp_c", "semantic_type"), accepted_projection(b_run.claims))
        self.assertNotIn(("temp_c", "semantic_type"), accepted_projection(c_run.claims))
        self.assertIn(("temp_c", "semantic_type"), accepted_projection(d_run.claims))
        rejected_c = next(
            claim
            for claim in c_run.claims
            if claim.source == "dataset_reasoner"
            and claim.property_name == "semantic_type"
        )
        self.assertEqual(rejected_c.verification_status, "unsupported")
        self.assertEqual(rejected_c.decision, "abstained")

    def test_c_rejects_real_but_field_irrelevant_evidence(self) -> None:
        case = copy.deepcopy(build_case())
        case.task_payload["task"]["grounding_snippets"][0]["text"] = (
            "Generic dataset documentation without field references."
        )

        _, run, _ = run_bc(case, ScriptedBackend())

        self.assertNotIn(("temp_c", "semantic_type"), accepted_projection(run.claims))
        rejected = next(
            claim
            for claim in run.claims
            if claim.source == "dataset_reasoner"
            and claim.property_name == "semantic_type"
        )
        self.assertEqual(rejected.verification_status, "unsupported")

    def test_c_rejects_correct_document_but_wrong_span(self) -> None:
        case = copy.deepcopy(build_case())
        case.task_payload["task"]["grounding_snippets"] = [
            {
                "source_type": "dataset_readme",
                "source_name": "README.md",
                "detail": "correct span",
                "text": "temp_c is air temperature in Celsius.",
            },
            {
                "source_type": "dataset_readme",
                "source_name": "README.md",
                "detail": "wrong span",
                "text": "This dataset was published in 2024.",
            },
        ]
        response = self._response(case, evidence=["S2"])
        _, c_run, _ = run_bc(case, DatasetResponseBackend(response))

        semantic = next(
            claim
            for claim in c_run.claims
            if claim.source == "dataset_reasoner"
            and claim.field_path == "temp_c"
            and claim.property_name == "semantic_type"
        )
        self.assertEqual(semantic.decision, "abstained")
        self.assertEqual(semantic.verification_status, "unsupported")

    def test_c_rejects_claim_contradicting_deterministic_value(self) -> None:
        case = copy.deepcopy(build_case())
        case.task_payload["task"]["deterministic_schema"]["fields"][0]["unit"] = "K"
        response = self._response(
            case,
            claims=[self._claim("temp_c", "unit", "Celsius", ["S1"], 0.9)],
        )
        _, c_run, _ = run_bc(case, DatasetResponseBackend(response))
        unit = next(
            claim
            for claim in c_run.claims
            if claim.source == "dataset_reasoner" and claim.property_name == "unit"
        )
        self.assertEqual(unit.decision, "rejected")
        self.assertEqual(unit.verification_status, "contradicted")

    def test_c_compares_equivalent_unit_aliases_canonically(self) -> None:
        case = copy.deepcopy(build_case())
        case.task_payload["task"]["deterministic_schema"]["fields"][0]["unit"] = (
            "Celsius"
        )
        response = self._response(
            case,
            claims=[self._claim("temp_c", "unit", "C", ["S1"], 0.9)],
        )

        _, c_run, _ = run_bc(case, DatasetResponseBackend(response))

        unit = next(
            claim
            for claim in c_run.claims
            if claim.source == "dataset_reasoner" and claim.property_name == "unit"
        )
        self.assertEqual(unit.decision, "accepted")
        self.assertEqual(unit.verification_status, "verified")

    def test_evaluator_retains_raw_unit_but_scores_canonical_alias(self) -> None:
        case = copy.deepcopy(build_case())
        case.gold_schema["fields"][0]["unit"] = "Celsius"
        run = run_variant("A", case)
        unit_claim = next(
            claim
            for claim in run.claims
            if claim.field_path == "temp_c" and claim.property_name == "unit"
        )
        unit_claim.value = "C"
        unit_claim.decision = "accepted"

        evaluation = evaluate_run(run, case.gold_schema)
        slot = next(
            item
            for item in evaluation["slots"]
            if item["field_path"] == "temp_c" and item["property"] == "unit"
        )

        self.assertEqual(slot["predicted"], "C")
        self.assertEqual(slot["predicted_normalized"], "Celsius")
        self.assertEqual(slot["expected_normalized"], "Celsius")
        self.assertTrue(slot["correct"])

    def test_empty_evidence_is_abstained_by_c(self) -> None:
        case = build_case()
        response = self._response(
            case,
            claims=[self._claim("temp_c", "semantic_type", "air_temperature", [], 0.8)],
        )
        _, c_run, _ = run_bc(case, DatasetResponseBackend(response))
        model_claim = next(c for c in c_run.claims if c.source == "dataset_reasoner")
        self.assertEqual(model_claim.decision, "abstained")
        self.assertEqual(model_claim.verification_status, "unsupported")

    def test_confidence_zero_assertion_can_be_verified(self) -> None:
        _, c_run, _ = run_bc(build_case(), ScriptedBackend())
        model_claim = next(
            c
            for c in c_run.claims
            if c.source == "dataset_reasoner"
            and c.field_path == "temp_c"
            and c.property_name == "semantic_type"
        )
        self.assertEqual(model_claim.confidence, 0.0)
        self.assertEqual(model_claim.decision, "accepted")

    def test_confidence_one_does_not_verify_unsupported_claim(self) -> None:
        case = build_case()
        response = self._response(
            case,
            claims=[
                self._claim(
                    "temp_c", "semantic_type", "air_temperature", ["MISSING"], 1.0
                )
            ],
        )
        _, c_run, _ = run_bc(case, DatasetResponseBackend(response))
        model_claim = next(c for c in c_run.claims if c.source == "dataset_reasoner")
        self.assertEqual(model_claim.decision, "abstained")

    def test_c_never_promotes_reasoner_abstention(self) -> None:
        case = build_case()
        response = self._response(
            case,
            claims=[self._claim("temp_c", "logical_type", "unknown", ["S1"], 0.95)],
        )
        response["claims"][0]["uncertainty_reason"] = "insufficient evidence"
        b_run, c_run, _ = run_bc(case, DatasetResponseBackend(response))
        b_claim = next(c for c in b_run.claims if c.source == "dataset_reasoner")
        c_claim = next(c for c in c_run.claims if c.source == "dataset_reasoner")
        self.assertEqual(b_claim.decision, "abstained")
        self.assertEqual(c_claim.decision, "abstained")
        self.assertEqual(c_claim.verification_status, "not_checked")

    def test_malformed_model_output_is_fail_closed_and_non_comparable(self) -> None:
        case = build_case()
        malformed = {"task_id": case.task_id, "notes": []}
        report = run_experiment(
            [case],
            variant_ids=["B", "C"],
            backend=DatasetResponseBackend(malformed),
            include_runs=True,
        )
        self.assertFalse(report["variant_summaries"]["B"]["comparable"])
        self.assertFalse(report["variant_summaries"]["C"]["comparable"])
        self.assertEqual(report["runs"]["B"][0]["status"], "partial")

    def test_duplicate_claims_are_fail_closed(self) -> None:
        case = build_case()
        claim = self._claim("temp_c", "semantic_type", "air_temperature", ["S1"], 0.8)
        response = self._response(case, claims=[claim, copy.deepcopy(claim)])
        report = run_experiment(
            [case], variant_ids=["B", "C"], backend=DatasetResponseBackend(response)
        )
        self.assertFalse(report["variant_summaries"]["B"]["comparable"])
        self.assertFalse(report["variant_summaries"]["C"]["comparable"])

    def test_mutually_conflicting_claims_are_abstained_by_c(self) -> None:
        case = build_case()
        response = self._response(
            case,
            claims=[
                self._claim("temp_c", "logical_type", "identifier", ["S1"], 0.8),
                self._claim("temp_c", "semantic_type", "air_temperature", ["S1"], 0.8),
            ],
        )
        _, c_run, _ = run_bc(case, DatasetResponseBackend(response))
        model_claims = [c for c in c_run.claims if c.source == "dataset_reasoner"]
        self.assertEqual({c.decision for c in model_claims}, {"abstained"})
        self.assertEqual({c.verification_status for c in model_claims}, {"conflicted"})

    def test_evaluation_excludes_na_and_reports_false_positive(self) -> None:
        case = build_case()
        run = run_variant("B", case, ScriptedBackend(add_unit=True))

        result = evaluate_run(run, case.gold_schema)

        unit = result["by_property"]["unit"]
        self.assertEqual(unit["counts"]["applicable_slots"], 0)
        self.assertEqual(unit["counts"]["non_applicable_slots"], 2)
        self.assertEqual(unit["counts"]["false_positive_non_applicable"], 1)
        self.assertEqual(unit["metrics"]["value_accuracy_applicable"], None)
        self.assertEqual(unit["metrics"]["false_positive_rate_non_applicable"], 0.5)

    def test_field_absent_from_open_world_gold_is_not_treated_as_na(self) -> None:
        case = build_case()
        case.gold_schema["fields"] = [case.gold_schema["fields"][0]]
        result = evaluate_run(run_variant("A", case), case.gold_schema)

        self.assertEqual(result["counts"]["predictions_outside_gold_scope"], 1)
        self.assertEqual(result["counts"]["false_positive_non_applicable"], 0)
        outside = [
            slot
            for slot in result["slots"]
            if slot["target_state"] == "outside_gold_scope"
        ]
        self.assertEqual(outside[0]["field_path"], "note")

    def test_unscored_semantic_target_invalidates_architecture_comparison(self) -> None:
        case = build_case()
        case.gold_schema["fields"] = [case.gold_schema["fields"][0]]
        report = run_experiment(
            [case], variant_ids=["A", "B", "C"], backend=ScriptedBackend()
        )

        design = report["case_design"][0]
        self.assertEqual(design["unscored_dataset_reasoning_target_paths"], ["note"])
        self.assertFalse(report["variant_summaries"]["B"]["comparable"])
        self.assertEqual(
            report["architecture_comparison"]["A_vs_B"]["status"],
            "not_comparable",
        )
        self.assertEqual(
            report["dataset_level_comparison"]["A_vs_B"]["status"],
            "not_comparable",
        )
        self.assertEqual(
            report["dataset_level_comparison"]["A_vs_B"]["cases"][0]["reasons"],
            ["semantic_targets_missing_from_gold"],
        )

    def test_dataset_level_estimand_weights_datasets_equally(self) -> None:
        def evaluation(
            case_id: str,
            *,
            correct: int,
            applicable: int,
            accuracy: float,
        ) -> Dict[str, Any]:
            return {
                "case_id": case_id,
                "status": "ok",
                "counts": {
                    "correct_applicable_predictions": correct,
                    "applicable_slots": applicable,
                    "accepted_unsupported_model_claims": 0,
                },
                "metrics": {
                    "end_to_end_value_accuracy": accuracy,
                    "coverage": 1.0,
                    "selective_risk": 1.0 - accuracy,
                },
            }

        comparisons = _dataset_level_comparison(
            {
                "A": [
                    evaluation("small", correct=0, applicable=1, accuracy=0.0),
                    evaluation("large", correct=50, applicable=100, accuracy=0.5),
                ],
                "B": [
                    evaluation("small", correct=1, applicable=1, accuracy=1.0),
                    evaluation("large", correct=50, applicable=100, accuracy=0.5),
                ],
            },
            [
                {
                    "case_id": "small",
                    "unscored_dataset_reasoning_target_paths": [],
                },
                {
                    "case_id": "large",
                    "unscored_dataset_reasoning_target_paths": [],
                },
            ],
        )

        result = comparisons["A_vs_B"]
        self.assertEqual(result["status"], "comparable")
        self.assertEqual(result["comparable_case_count"], 2)
        self.assertEqual(result["mean_correct_accepted_claim_rate_gain"], 0.5)
        self.assertEqual(result["mean_correct_accepted_claim_gain"], 0.5)

    def test_gold_rejects_na_marked_applicable_value(self) -> None:
        gold = copy.deepcopy(build_case().gold_schema)
        gold["fields"][0]["applicability"] = {"logical_type": False}
        with self.assertRaisesRegex(ValueError, "gold contradiction"):
            list(gold_slots(gold))

    def test_applicable_unknown_is_not_treated_as_na(self) -> None:
        case = build_case()
        case.gold_schema["fields"][0]["unit"] = None
        case.gold_schema["fields"][0]["applicability"] = {"unit": True}
        result = evaluate_run(run_variant("A", case), case.gold_schema)
        unit = result["by_property"]["unit"]
        self.assertEqual(unit["counts"]["applicable_unknown_slots"], 1)
        self.assertEqual(unit["counts"]["correct_abstentions_on_unknown"], 1)
        self.assertEqual(unit["counts"]["non_applicable_slots"], 1)

    def test_c_without_b_is_rejected_as_missing_replay(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires B"):
            run_experiment([build_case()], variant_ids=["C"], backend=ScriptedBackend())

    def test_replay_validator_detects_different_responses(self) -> None:
        case = build_case()
        b, c, _ = run_bc(case, ScriptedBackend())
        c.model_responses[0]["response_hash"] = "tampered"
        provenance = _validate_b_c_replay([case], {"B": [b], "C": [c]})
        self.assertFalse(provenance[0]["valid"])
        self.assertEqual(b.status, "partial")
        self.assertEqual(c.status, "partial")

    def test_backend_retry_count_invalidates_b(self) -> None:
        case = build_case()
        response = self._response(case, claims=[])
        report = run_experiment(
            [case],
            variant_ids=["B", "C"],
            backend=DatasetResponseBackend(response, model_calls=2),
        )
        self.assertFalse(report["variant_summaries"]["B"]["comparable"])
        self.assertEqual(
            report["variant_summaries"]["B"]["telemetry"]["model_calls"], 2
        )

    def test_partial_model_output_is_non_comparable(self) -> None:
        case = build_case()
        partial = self._response(
            case,
            claims=[{"field_path": "temp_c", "property": "semantic_type"}],
        )
        report = run_experiment(
            [case], variant_ids=["B", "C"], backend=DatasetResponseBackend(partial)
        )
        self.assertFalse(report["variant_summaries"]["B"]["comparable"])

    def test_timeout_is_cached_and_c_does_not_retry(self) -> None:
        case = build_case()
        backend = DatasetResponseBackend(exception=TimeoutError("deadline"))
        report = run_experiment(
            [case],
            variant_ids=["B", "C"],
            backend=backend,
            include_runs=True,
        )
        self.assertEqual(report["execution_control"]["physical_backend_invocations"], 1)
        self.assertEqual(report["execution_control"]["shared_failure_cache_hits"], 1)
        self.assertEqual(report["runs"]["C"][0]["telemetry"]["model_calls"], 0)
        self.assertEqual(
            report["execution_control"]["b_c_replay_provenance"][0]["state"],
            "shared_upstream_failure",
        )

    def test_zero_accepted_claims_selective_metrics_are_defined(self) -> None:
        case = build_case()
        run = VariantRun(
            variant_id="test",
            case_id=case.case_id,
            task_id=case.task_id,
            status="ok",
            claims=[],
            evidence_catalog=[],
        )
        result = evaluate_run(run, case.gold_schema)
        self.assertEqual(result["selective_curve"]["achieved_coverage"], 0.0)
        self.assertIsNone(result["metrics"]["selective_risk"])

    def test_all_applicable_claims_accepted(self) -> None:
        case = build_case()
        _, c_run, _ = run_bc(case, ScriptedBackend())
        result = evaluate_run(c_run, case.gold_schema)
        self.assertEqual(result["metrics"]["coverage"], 1.0)
        self.assertEqual(result["metrics"]["selective_risk"], 0.0)

    def test_tied_confidence_aurc_is_order_independent(self) -> None:
        slots = [
            SlotEvaluation(
                "a",
                "logical_type",
                "x",
                "x",
                "applicable_value",
                True,
                True,
                True,
                0.5,
                "1",
            ),
            SlotEvaluation(
                "b",
                "logical_type",
                "x",
                "y",
                "applicable_value",
                True,
                True,
                False,
                0.5,
                "2",
            ),
        ]
        forward = _selective_curve(slots)
        reverse = _selective_curve(list(reversed(slots)))
        self.assertEqual(forward, reverse)
        self.assertEqual(forward["aurc_over_achieved_coverage"], 0.5)

    def test_empty_evidence_on_accepted_b_claim_is_unsupported(self) -> None:
        case = build_case()
        run = run_variant("B", case, ScriptedBackend())
        model_claim = next(
            claim for claim in run.claims if claim.source == "dataset_reasoner"
        )
        model_claim.evidence_refs = []

        result = evaluate_run(run, case.gold_schema)

        self.assertEqual(result["counts"]["accepted_unsupported_model_claims"], 1)

    def test_unified_harness_runs_all_variants(self) -> None:
        case = build_case()
        report = run_experiment([case], backend=ScriptedBackend(), include_runs=False)

        self.assertEqual(set(report["variant_summaries"]), {"A", "B", "C", "D"})
        self.assertEqual(
            report["variant_summaries"]["B"]["telemetry"]["model_calls"], 1
        )
        self.assertEqual(
            report["variant_summaries"]["D"]["telemetry"]["model_calls"], 2
        )
        self.assertEqual(
            report["variant_summaries"]["C"]["telemetry"]["model_calls"], 0
        )
        self.assertEqual(
            report["execution_control"]["physical_model_calls_executed"], 3
        )
        self.assertEqual(report["case_design"][0]["dataset_reasoning_target_count"], 2)
        self.assertEqual(report["execution_control"]["shared_response_cache_hits"], 1)
        self.assertEqual(
            report["metric_policy"]["confidence"],
            "used only for selective curves; never treated as verification",
        )

    def test_blind_report_has_distinct_schema_and_backend_identity(self) -> None:
        case = build_case()
        case.benchmark_role = "blind_external"
        backend = ScriptedBackend()
        backend.model = "frozen-local-model"
        backend.api_base = "http://127.0.0.1:1234/v1"
        backend.registered_backend = {
            "backend_id": "frozen-backend",
            "role": "primary",
            "model_identifier": "frozen-local-model",
        }
        backend.backend_registry_sha256 = "a" * 64

        report = run_experiment([case], backend=backend, include_runs=False)

        self.assertEqual(
            report["schema_version"],
            "minimal-architecture-experiment/v3-blind",
        )
        self.assertEqual(report["benchmark_roles"], ["blind_external"])
        self.assertEqual(
            report["execution_control"]["backend_identity"]["model_identifier"],
            "frozen-local-model",
        )
        self.assertEqual(
            report["execution_control"]["backend_identity"]["registered_backend_id"],
            "frozen-backend",
        )

    def test_blind_model_run_rejects_unregistered_backend(self) -> None:
        case = build_case()
        case.benchmark_role = "blind_external"

        with self.assertRaisesRegex(ValueError, "frozen registered backend"):
            run_experiment([case], backend=ScriptedBackend(), include_runs=False)

    def test_blind_backend_registration_binds_exact_registry_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry_path = root / "backends.json"
            record = {
                "backend_id": "registered-local",
                "role": "primary",
                "model_identifier": "served-model",
                "endpoint": "http://127.0.0.1:1234/v1",
                "checkpoint_sha256": "b" * 64,
                "dataset_reasoner_decoding": {
                    "temperature": 0,
                    "seed": 7,
                    "max_tokens": 2048,
                    "thinking_enabled": False,
                },
                "legacy_decoding": {
                    "temperature": 0.2,
                    "seed": None,
                    "max_tokens": 1000,
                    "thinking_enabled": False,
                },
                "qualification": {"eligible": True},
            }
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": "semantic-backend-registry/v1",
                        "backends": [record],
                    }
                ),
                encoding="utf-8",
            )
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "backend_registry_file": registry_path.name,
                        "backend_registry_sha256": _sha256_file(registry_path),
                    }
                ),
                encoding="utf-8",
            )
            backend = OpenAICompatibleBackend(
                model="served-model",
                api_base="http://127.0.0.1:1234/v1",
                seed=7,
                max_tokens=2048,
            )

            _bind_backend_registration(
                backend,
                manifest_path=manifest_path,
                registry_path=None,
                backend_id="registered-local",
                required=True,
            )

            self.assertEqual(backend.registered_backend, record)
            self.assertEqual(
                backend.backend_registry_sha256, _sha256_file(registry_path)
            )

            backend.seed = 8
            with self.assertRaisesRegex(ValueError, "seed differs"):
                _bind_backend_registration(
                    backend,
                    manifest_path=manifest_path,
                    registry_path=None,
                    backend_id="registered-local",
                    required=True,
                )

    def test_gold_never_enters_model_payload(self) -> None:
        case = build_case()
        case.gold_schema["secret_evaluation_only_marker"] = "SECRET_GOLD_SENTINEL"

        class GoldLeakDetectingBackend(ScriptedBackend):
            def complete(self, **kwargs: Any) -> ModelCompletion:
                self.assert_no_gold(kwargs["payload"])
                return super().complete(**kwargs)

            @staticmethod
            def assert_no_gold(payload: Dict[str, Any]) -> None:
                encoded = json.dumps(payload, sort_keys=True)
                if "SECRET_GOLD_SENTINEL" in encoded:
                    raise AssertionError("gold leaked into a model request")

        report = run_experiment(
            [case], backend=GoldLeakDetectingBackend(), include_runs=False
        )

        self.assertEqual(report["variant_summaries"]["B"]["failed_case_count"], 0)
        self.assertEqual(report["variant_summaries"]["D"]["failed_case_count"], 0)

    def test_missing_legacy_replay_is_not_ranked_as_comparable(self) -> None:
        case = build_case()
        case.legacy_replay_required = True

        report = run_experiment([case], variant_ids=["D"], include_runs=False)

        self.assertEqual(report["variant_summaries"]["D"]["failed_case_count"], 1)
        self.assertEqual(report["variant_summaries"]["D"]["comparable"], False)
        self.assertEqual(report["architecture_comparison"], {})

    @staticmethod
    def _claim(
        field_path: str,
        property_name: str,
        value: Any,
        evidence: List[str],
        confidence: float,
    ) -> Dict[str, Any]:
        return {
            "field_path": field_path,
            "property": property_name,
            "value": value,
            "evidence_refs": evidence,
            "confidence": confidence,
            "uncertainty_reason": None,
        }

    def _response(
        self,
        case: ExperimentCase,
        *,
        claims: List[Dict[str, Any]] | None = None,
        evidence: List[str] | None = None,
    ) -> Dict[str, Any]:
        if claims is None:
            refs = ["S1"] if evidence is None else evidence
            claims = [
                self._claim("temp_c", "logical_type", "measurement", refs, 0.8),
                self._claim("temp_c", "semantic_type", "air_temperature", refs, 0.8),
            ]
        return {"task_id": case.task_id, "claims": claims, "notes": []}


if __name__ == "__main__":
    unittest.main()
