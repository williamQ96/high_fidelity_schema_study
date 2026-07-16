from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from high_fidelity_schema_study.architecture_variants import (
    ALLOWED_LOGICAL_TYPES,
    build_observation_payload,
)
import high_fidelity_schema_study.semantic_catalog_acquisition as catalog_adapter
from high_fidelity_schema_study.semantic_gold_workflow import (
    build_packet_source_bundle,
    compare_independent_artifacts,
)
from high_fidelity_schema_study.semantic_blind_inference import build_analysis_plan
from high_fidelity_schema_study.semantic_blind_sampling import (
    build_blind_selection,
    canonical_source_identity,
)
from high_fidelity_schema_study.semantic_annotator_calibration import (
    build_annotator_calibration_summary,
)
from high_fidelity_schema_study.semantic_power_analysis import build_power_analysis
from high_fidelity_schema_study.semantic_power_calibration import (
    build_calibration_statistics_from_paths,
)
from high_fidelity_schema_study.semantic_study_preflight import (
    preflight_blind_manifest,
    semantic_contract_hashes,
    sha256_file,
)
from high_fidelity_schema_study.tests.test_semantic_annotator_calibration import (
    build_round as build_annotator_calibration_round,
)


HASH = "a" * 64


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def evidence(
    field_path: str,
    property_name: str,
    ordinal: int,
    *,
    source_sha256: str = HASH,
) -> dict:
    return {
        "evidence_id": f"E{ordinal}",
        "catalog_evidence_id": "S1",
        "property": property_name,
        "source_type": "approved_documentation",
        "source_sha256": source_sha256,
        "selector": "approved_evidence:S1",
        "field_path": field_path,
        "strength": "documentation",
        "support": "Test evidence.",
    }


def qualification_report(model_identifier: str) -> dict:
    return {
        "schema_version": "semantic-backend-qualification/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "research_evidence_status": "non_blind_operational_qualification_only",
        "gold_accessed": False,
        "backend_identity": {"selected_model_identifier": model_identifier},
        "contract_hashes": semantic_contract_hashes(),
        "calibration_manifest_sha256": HASH,
        "annotation_vocabulary_sha256": HASH,
        "semantic_opportunity_case_count": 1,
        "dataset_reasoner": {
            "repeat_count": 3,
            "attempt_count": 3,
            "contract_valid_rate": 1.0,
            "target_scope_valid_rate": 1.0,
            "replay_identity_rate": 1.0,
            "exact_repeatability_rate": 1.0,
            "timeout_rate": 0.0,
            "truncation_rate": 0.0,
            "context_fit_rate": 1.0,
            "context_fit_observed_fraction": 1.0,
        },
        "legacy": {
            "repeat_count": 1,
            "attempt_count": 1,
            "contract_valid_rate": 1.0,
            "timeout_rate": 0.0,
            "truncation_rate": 0.0,
            "context_fit_rate": 1.0,
            "context_fit_observed_fraction": 1.0,
        },
    }


def backend(
    backend_id: str,
    family: str,
    role: str,
    qualification_file: str,
    qualification_sha256: str,
) -> dict:
    contracts = semantic_contract_hashes()
    decoding = {
        "temperature": 0,
        "seed": 0,
        "max_tokens": 4096,
        "thinking_enabled": False,
        "prompt_sha256": contracts["dataset_reasoner_prompt_sha256"],
        "response_schema_sha256": contracts["dataset_reasoner_schema_sha256"],
    }
    legacy = {
        **decoding,
        "temperature": 0.2,
        "seed": None,
        "max_tokens": 1000,
        "prompt_sha256": contracts["legacy_prompt_sha256"],
        "response_schema_sha256": contracts["legacy_schema_sha256"],
    }
    return {
        "backend_id": backend_id,
        "role": role,
        "model_family": family,
        "checkpoint": f"{family}-fixture",
        "checkpoint_sha256": HASH,
        "parameter_scale": "test",
        "quantization": "Q4-test",
        "runtime": "fixture-runtime",
        "runtime_version": "1.0",
        "endpoint": "http://127.0.0.1:1234/v1",
        "model_identifier": backend_id,
        "hardware": {
            "gpu": "test-gpu",
            "gpu_count": 1,
            "offload_configuration": "all",
            "context_length": 32768,
        },
        "dataset_reasoner_decoding": decoding,
        "legacy_decoding": legacy,
        "qualification": {
            "qualification_report_file": qualification_file,
            "qualification_report_sha256": qualification_sha256,
            "calibration_manifest_sha256": HASH,
            "qualification_vocabulary_sha256": HASH,
            "semantic_opportunity_case_count": 1,
            "repeat_count": 3,
            "attempt_count": 3,
            "contract_valid_rate": 1.0,
            "target_scope_valid_rate": 1.0,
            "replay_identity_rate": 1.0,
            "exact_repeatability_rate": 1.0,
            "timeout_rate": 0.0,
            "truncation_rate": 0.0,
            "context_fit_rate": 1.0,
            "context_fit_observed_fraction": 1.0,
            "legacy_repeat_count": 1,
            "legacy_attempt_count": 1,
            "legacy_contract_valid_rate": 1.0,
            "legacy_timeout_rate": 0.0,
            "legacy_truncation_rate": 0.0,
            "legacy_context_fit_rate": 1.0,
            "legacy_context_fit_observed_fraction": 1.0,
            "eligible": True,
        },
    }


def build_fixture(root: Path) -> Path:
    task = {
        "task": {
            "task_id": "blind::blind_demo",
            "dataset_id": "blind_demo",
            "file_format": "csv",
            "data_modality": "tabular",
            "deterministic_schema": {
                "fields": [
                    {
                        "field_name": "temperature",
                        "field_path": "temperature",
                        "physical_type": "float32",
                        "logical_type": "unknown",
                        "semantic_type": "unknown",
                        "unit": None,
                        "confidence": 1.0,
                        "source_evidence": [
                            {
                                "evidence_type": "csv_header",
                                "source": "blind.csv",
                                "detail": "header='temperature'",
                            }
                        ],
                    }
                ],
                "metadata": {},
            },
            "grounding_snippets": [],
            "instructions": [],
        }
    }
    task_path = root / "task.json"
    gold_path = root / "gold.json"
    packet_path = root / "packet.json"
    vocabulary_path = root / "vocabulary.json"
    source_bundle_path = root / "source-bundle.json"
    annotation_a_path = root / "annotation-a.json"
    annotation_b_path = root / "annotation-b.json"
    disagreement_path = root / "disagreement.json"
    write_json(task_path, task)
    write_json(
        packet_path,
        {
            "schema_version": "semantic-annotation-packet/v1",
            "purpose": "blind_annotation",
            "research_evidence_status": "blind_external",
            "case_id": "blind_demo",
            "task_id": "blind::blind_demo",
            "dataset_id": "blind_demo",
            "file_format": "csv",
            "data_modality": "tabular",
            "field_inventory": [
                {
                    "field_name": "temperature",
                    "field_path": "temperature",
                    "physical_type": "float32",
                    "source_evidence": [],
                }
            ],
            "approved_evidence": [
                {
                    "evidence_id": "S1",
                    "source_type": "approved_documentation",
                    "source_name": "README.md",
                    "detail": "variables:temperature",
                    "text": "temperature is an air temperature measurement",
                    "applicable_field_paths": ["temperature"],
                }
            ],
        },
    )
    write_json(
        vocabulary_path,
        {
            "schema_version": "semantic-annotation-vocabulary/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "frozen",
            "vocabulary_version": "fixture-v1",
            "physical_types": ["float32"],
            "logical_types": sorted(ALLOWED_LOGICAL_TYPES),
            "semantic_types": ["air_temperature"],
            "units": ["degree_Celsius"],
            "unit_aliases": {"C": "degree_Celsius"},
            "unit_patterns": [],
            "unknown_representation": None,
        },
    )
    write_json(
        source_bundle_path,
        build_packet_source_bundle(packet_path, vocabulary_path),
    )

    def annotation(annotator_id: str, submission_id: str) -> dict:
        packet_hash = sha256_file(packet_path)
        return {
            "schema_version": "blind-semantic-gold/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "dataset_id": "blind_demo",
            "annotation_stage": "independent",
            "annotator_id": annotator_id,
            "submission_id": submission_id,
            "source_bundle_sha256": sha256_file(source_bundle_path),
            "annotation_packet_sha256": packet_hash,
            "vocabulary_sha256": sha256_file(vocabulary_path),
            "model_outputs_visible": False,
            "developer_participation": False,
            "fields": [
                {
                    "field_name": "temperature",
                    "field_path": "temperature",
                    "correct_physical_type": "float32",
                    "correct_logical_type": "measurement",
                    "correct_semantic_type": "air_temperature",
                    "unit": None,
                    "applicability": {
                        "physical_type": True,
                        "logical_type": True,
                        "semantic_type": True,
                        "unit": False,
                    },
                    "rationales": {
                        "physical_type": None,
                        "logical_type": None,
                        "semantic_type": None,
                        "unit": "The label field has no applicable measurement unit.",
                    },
                    "gold_evidence": [
                        evidence(
                            "temperature",
                            "physical_type",
                            1,
                            source_sha256=packet_hash,
                        ),
                        evidence(
                            "temperature",
                            "logical_type",
                            2,
                            source_sha256=packet_hash,
                        ),
                        evidence(
                            "temperature",
                            "semantic_type",
                            3,
                            source_sha256=packet_hash,
                        ),
                    ],
                    "notes": None,
                }
            ],
        }

    write_json(annotation_a_path, annotation("annotator-a", "ann-1"))
    write_json(annotation_b_path, annotation("annotator-b", "ann-2"))
    disagreement = compare_independent_artifacts(
        annotation_a_path,
        annotation_b_path,
        packet_path=packet_path,
        source_bundle_path=source_bundle_path,
        vocabulary_path=vocabulary_path,
    )
    write_json(disagreement_path, disagreement)
    gold = annotation("consensus-panel", "consensus-1")
    gold["annotation_stage"] = "consensus"
    gold["adjudication"] = {
        "independent_artifact_ids": ["ann-1", "ann-2"],
        "independent_artifacts": disagreement["independent_artifacts"],
        "disagreement_report_sha256": sha256_file(disagreement_path),
        "disagreement_count": 0,
        "unresolved_slots": [],
        "resolutions": [],
    }

    task_2_path = root / "task-2.json"
    packet_2_path = root / "packet-2.json"
    source_bundle_2_path = root / "source-bundle-2.json"
    annotation_2_a_path = root / "annotation-2-a.json"
    annotation_2_b_path = root / "annotation-2-b.json"
    disagreement_2_path = root / "disagreement-2.json"
    gold_2_path = root / "gold-2.json"
    task_2 = copy.deepcopy(task)
    task_2["task"]["task_id"] = "blind::blind_demo_2"
    task_2["task"]["dataset_id"] = "blind_demo_2"
    write_json(task_2_path, task_2)
    packet_2 = json.loads(packet_path.read_text(encoding="utf-8"))
    packet_2["case_id"] = "blind_demo_2"
    packet_2["task_id"] = "blind::blind_demo_2"
    packet_2["dataset_id"] = "blind_demo_2"
    write_json(packet_2_path, packet_2)
    write_json(
        source_bundle_2_path,
        build_packet_source_bundle(packet_2_path, vocabulary_path),
    )

    def second_annotation(annotator_id: str, submission_id: str) -> dict:
        payload = annotation(annotator_id, submission_id)
        payload["dataset_id"] = "blind_demo_2"
        payload["source_bundle_sha256"] = sha256_file(source_bundle_2_path)
        payload["annotation_packet_sha256"] = sha256_file(packet_2_path)
        for item in payload["fields"][0]["gold_evidence"]:
            item["source_sha256"] = sha256_file(packet_2_path)
        return payload

    write_json(annotation_2_a_path, second_annotation("annotator-a", "ann-2-1"))
    write_json(annotation_2_b_path, second_annotation("annotator-b", "ann-2-2"))
    disagreement_2 = compare_independent_artifacts(
        annotation_2_a_path,
        annotation_2_b_path,
        packet_path=packet_2_path,
        source_bundle_path=source_bundle_2_path,
        vocabulary_path=vocabulary_path,
    )
    write_json(disagreement_2_path, disagreement_2)
    gold_2 = second_annotation("consensus-panel", "consensus-2")
    gold_2["annotation_stage"] = "consensus"
    gold_2["adjudication"] = {
        "independent_artifact_ids": ["ann-2-1", "ann-2-2"],
        "independent_artifacts": disagreement_2["independent_artifacts"],
        "disagreement_report_sha256": sha256_file(disagreement_2_path),
        "disagreement_count": 0,
        "unresolved_slots": [],
        "resolutions": [],
    }
    backend_specs = [
        ("qwen-primary", "Qwen3.6", "primary"),
        ("glm-sensitivity", "GLM5.2", "sensitivity"),
        ("llama-sensitivity", "Llama 3.3", "sensitivity"),
    ]
    backend_entries = []
    for backend_id, family, role in backend_specs:
        report_path = root / f"{backend_id}.qualification.json"
        write_json(report_path, qualification_report(backend_id))
        backend_entries.append(
            backend(
                backend_id,
                family,
                role,
                report_path.name,
                sha256_file(report_path),
            )
        )
    registry = {
        "schema_version": "semantic-backend-registry/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "frozen_at": "2026-07-15T00:00:00Z",
        "primary_backend_id": "qwen-primary",
        "required_model_families": ["Qwen3.6", "GLM5.2", "Llama 3.3"],
        "qualification_policy": {
            "calibration_manifest_sha256": HASH,
            "calibration_vocabulary_sha256": HASH,
            "minimum_semantic_opportunity_case_count": 1,
            "minimum_contract_valid_rate": 0.95,
            "minimum_target_scope_valid_rate": 0.95,
            "minimum_replay_identity_rate": 1.0,
            "minimum_exact_repeatability_rate": 0.95,
            "maximum_timeout_rate": 0.05,
            "maximum_truncation_rate": 0.0,
            "minimum_context_fit_rate": 1.0,
            "minimum_context_fit_observed_fraction": 1.0,
            "minimum_legacy_contract_valid_rate": 0.95,
            "maximum_legacy_timeout_rate": 0.05,
            "maximum_legacy_truncation_rate": 0.0,
            "minimum_legacy_context_fit_rate": 1.0,
            "minimum_legacy_context_fit_observed_fraction": 1.0,
            "repeat_count": 3,
            "legacy_repeat_count": 1,
        },
        "backends": backend_entries,
    }
    task_path = root / "task.json"
    gold_path = root / "gold.json"
    registry_path = root / "backends.json"
    handbook_path = root / "handbook.md"
    power_path = root / "power.json"
    analysis_plan_path = root / "analysis-plan.json"
    known_resources_path = root / "known-nonblind-resources.json"
    acquisition_path = root / "blind-acquisition.json"
    acquisition_adapter_path = Path(catalog_adapter.__file__).resolve()
    acquisition_snapshot_paths = {
        "zenodo": root / "zenodo-catalog-snapshot.json",
        "dryad": root / "dryad-catalog-snapshot.json",
    }
    candidate_frame_path = root / "candidate-frame.json"
    sampling_design_path = root / "sampling-design.json"
    sampling_receipt_path = root / "sampling-receipt.json"
    sampling_selection_path = root / "sampling-selection.json"
    calibration_manifest_path = root / "calibration-manifest.json"
    calibration_evaluation_path = root / "calibration-evaluation.json"
    calibration_statistics_path = root / "calibration-statistics.json"
    write_json(task_path, task)
    write_json(gold_path, gold)
    write_json(gold_2_path, gold_2)
    write_json(registry_path, registry)
    handbook_path.write_text("# Frozen handbook\n", encoding="utf-8")
    annotator_calibration_paths = build_annotator_calibration_round(
        root / "annotator-calibration",
        vocabulary_path_override=vocabulary_path,
        handbook_path_override=handbook_path,
    )
    annotator_calibration_summary = build_annotator_calibration_summary(
        round_manifest_path=annotator_calibration_paths["round"],
        output_path=annotator_calibration_paths["summary"],
    )
    write_json(annotator_calibration_paths["summary"], annotator_calibration_summary)
    write_json(
        calibration_manifest_path,
        {
            "schema_version": "minimal-architecture-manifest/v1",
            "cases": [{"case_id": "cal-1"}, {"case_id": "cal-2"}],
        },
    )

    def calibration_comparison(effects: list[float]) -> dict:
        return {
            "status": "comparable",
            "cases": [
                {
                    "case_id": case_id,
                    "status": "comparable",
                    "reasons": [],
                    "correct_accepted_claim_rate_gain": effect,
                }
                for case_id, effect in zip(("cal-1", "cal-2"), effects)
            ],
        }

    write_json(
        calibration_evaluation_path,
        {
            "schema_version": "minimal-architecture-experiment/v3-development",
            "benchmark_roles": ["calibration"],
            "case_design": [
                {"case_id": "cal-1", "dataset_reasoning_opportunity": True},
                {"case_id": "cal-2", "dataset_reasoning_opportunity": True},
            ],
            "execution_control": {
                "b_c_replay_provenance": [
                    {"case_id": "cal-1", "valid": True},
                    {"case_id": "cal-2", "valid": True},
                ]
            },
            "predefined_analysis_strata": {
                "dataset_reasoning_opportunity": {
                    "dataset_level_comparison": {
                        "A_vs_B": calibration_comparison([0.99, 1.0]),
                        "B_vs_C": calibration_comparison([0.98, 1.0]),
                    }
                }
            },
        },
    )
    calibration_statistics = build_calibration_statistics_from_paths(
        evaluation_report_path=calibration_evaluation_path,
        calibration_manifest_path=calibration_manifest_path,
        output_path=calibration_statistics_path,
    )
    write_json(calibration_statistics_path, calibration_statistics)
    recommended = calibration_statistics["recommended_power_inputs"]
    power = build_power_analysis(
        {
            "schema_version": "semantic-power-analysis-config/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "frozen",
            "calibration_manifest_file": calibration_manifest_path.name,
            "calibration_manifest_sha256": sha256_file(calibration_manifest_path),
            "calibration_statistics_file": calibration_statistics_path.name,
            "calibration_statistics_sha256": sha256_file(calibration_statistics_path),
            "sd_estimation_method": "fixture paired dataset-level SD",
            "planning_rationale": "minimal valid two-dataset test fixture",
            "primary_contrasts": ["A_vs_B", "B_vs_C"],
            "minimum_meaningful_effect": 1.0,
            "familywise_alpha": 0.05,
            "target_power": 0.8,
            "selective_risk_bound": 0.05,
            "paired_difference_sd_by_contrast": recommended[
                "paired_difference_sd_by_contrast"
            ],
            "planning_sd_inflation": 1.25,
            "semantic_opportunity_rate": recommended["semantic_opportunity_rate"],
            "noncomparability_rate": recommended["noncomparability_rate"],
            "opportunity_count_assurance": 0.9,
            "minimum_total_dataset_count": 2,
            "sensitivity_sd_multipliers": [1.0, 1.25, 1.5],
        }
    )
    assert power["assumptions"]["required_dataset_count"] == 2
    assert power["assumptions"]["required_semantic_opportunity_case_count"] == 2
    write_json(power_path, power)
    analysis_plan = build_analysis_plan(
        {
            "schema_version": "semantic-blind-analysis-plan-config/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "frozen",
            "backend_registry_file": registry_path.name,
            "backend_registry_sha256": sha256_file(registry_path),
            "power_analysis_file": power_path.name,
            "power_analysis_sha256": sha256_file(power_path),
            "primary_contrasts": ["A_vs_B", "B_vs_C"],
            "secondary_contrasts": ["C_vs_D"],
            "familywise_alpha": 0.05,
            "confidence_level": 0.95,
            "sign_flip_exact_max_n": 20,
            "sign_flip_monte_carlo_repetitions": 1000,
            "sign_flip_seed": 101,
            "bootstrap_repetitions": 1000,
            "bootstrap_seed": 102,
        }
    )
    write_json(analysis_plan_path, analysis_plan)
    known_source_identity = canonical_source_identity(
        "known-repository", "known-record", "known-resource"
    )
    write_json(
        known_resources_path,
        {
            "schema_version": "semantic-known-nonblind-resources/v1",
            "status": "frozen_before_candidate_frame",
            "source_identity_algorithm": "canonical_source_tuple_sha256/v1",
            "frozen_at": "2026-07-15T00:00:00Z",
            "construction_sources": [
                {
                    "file": registry_path.name,
                    "sha256": sha256_file(registry_path),
                }
            ],
            "generator": {
                "file": registry_path.name,
                "sha256": sha256_file(registry_path),
            },
            "coverage": {
                "total_record_count": 1,
                "resource_hash_available_count": 0,
                "source_identity_count": 1,
            },
            "source_identities": [known_source_identity],
            "task_sha256s": [sha256_file(registry_path)],
            "resource_sha256s": [],
            "records": [
                {
                    "source_identity": known_source_identity,
                    "source_repository": "known-repository",
                    "source_record_id": "known-record",
                    "source_resource_id": "known-resource",
                    "task": {
                        "file": registry_path.name,
                        "sha256": sha256_file(registry_path),
                    },
                    "resource_available_at_freeze": False,
                    "resource": None,
                    "resource_absence_reason": "not retained in fixture",
                }
            ],
        },
    )
    sampling_candidates = []
    acquisition_records = []
    acquisition_specs = (
        (
            "blind_demo",
            "zenodo",
            "record_301",
            "zenodo::concept::401",
            "blind_demo.csv",
            task_path,
            packet_path,
            source_bundle_path,
        ),
        (
            "blind_demo_2",
            "dryad",
            "10.5061_dryad.fixture2",
            "dryad::10.5061_dryad.fixture2",
            "blind_demo_2.csv",
            task_2_path,
            packet_2_path,
            source_bundle_2_path,
        ),
    )
    for (
        case_id,
        source_repository,
        source_record_id,
        dataset_group_id,
        source_resource_id,
        task_file,
        resource_file,
        bundle_file,
    ) in acquisition_specs:
        task_payload = json.loads(task_file.read_text(encoding="utf-8"))
        source_url = (
            f"https://zenodo.org/api/records/301/files/{source_resource_id}/content"
            if source_repository == "zenodo"
            else f"https://datadryad.org/api/v2/files/{case_id}/download"
        )
        provider_checksum = (
            f"md5:{hashlib.md5(resource_file.read_bytes()).hexdigest()}"
            if source_repository == "zenodo"
            else f"sha-256:{sha256_file(resource_file)}"
        )
        sampling_candidates.append(
            {
                "candidate_id": case_id,
                "dataset_group_id": dataset_group_id,
                "source_identity": canonical_source_identity(
                    source_repository, source_record_id, source_resource_id
                ),
                "source_repository": source_repository,
                "source_record_id": source_record_id,
                "source_resource_id": source_resource_id,
                "source_url": source_url,
                "acquired_at": "2026-07-15T00:00:00Z",
                "scientific_family": "atmosphere",
                "file_format": "csv",
                "selection_stratum": "csv",
                "license": "CC-BY-4.0",
                "resource": {
                    "file": resource_file.name,
                    "sha256": sha256_file(resource_file),
                },
                "task": {
                    "file": task_file.name,
                    "sha256": sha256_file(task_file),
                },
                "source_bundle": {
                    "file": bundle_file.name,
                    "sha256": sha256_file(bundle_file),
                },
                "semantic_opportunity_target_count": len(
                    build_observation_payload(task_payload)["targets"]
                ),
                "eligibility": {
                    "eligible": True,
                    "reasons": [],
                    "criterion_results": {
                        "supported_fixture_format": True,
                        "known_nonblind_overlap": False,
                    },
                },
            }
        )
        acquisition_records.append(
            {
                "candidate_id": case_id,
                "dataset_group_id": dataset_group_id,
                "source_identity": canonical_source_identity(
                    source_repository, source_record_id, source_resource_id
                ),
                "source_repository": source_repository,
                "source_record_id": source_record_id,
                "source_resource_id": source_resource_id,
                "source_url": source_url,
                "source_size_bytes": resource_file.stat().st_size,
                "provider_checksum": provider_checksum,
                "discovered_at": "2026-07-15T00:00:00Z",
                "scientific_family": "atmosphere",
                "file_format": "csv",
                "selection_stratum": "csv",
                "license": "CC-BY-4.0",
                "catalog_snapshot_id": f"snapshot::{source_repository}",
                "criterion_results": {
                    "supported_fixture_resource": True,
                    "oversize_resource": False,
                },
                "eligible_for_acquisition": True,
                "reasons": [],
                "acquisition_status": "acquired",
                "acquired_at": "2026-07-15T00:00:00Z",
                "resource": {
                    "file": resource_file.name,
                    "sha256": sha256_file(resource_file),
                },
                "failure": None,
            }
        )
    write_json(
        acquisition_snapshot_paths["zenodo"],
        {
            "schema_version": "semantic-catalog-snapshot/v1",
            "adapter_id": catalog_adapter.ADAPTER_ID,
            "source_repository": "zenodo",
            "page_ordinal": 1,
            "request_url": "https://zenodo.org/api/records?page=1",
            "retrieved_at": "2026-07-15T00:00:00Z",
            "raw_catalog_response": {
                "hits": {
                    "hits": [
                        {
                            "id": "301",
                            "conceptrecid": "401",
                            "metadata": {
                                "rights": [{"id": "CC-BY-4.0"}],
                                "subjects": [{"subject": "atmosphere"}],
                            },
                            "files": [
                                {
                                    "key": "blind_demo.csv",
                                    "size": packet_path.stat().st_size,
                                    "checksum": f"md5:{hashlib.md5(packet_path.read_bytes()).hexdigest()}",
                                    "links": {
                                        "self": "https://zenodo.org/api/records/301/files/blind_demo.csv/content"
                                    },
                                }
                            ],
                        }
                    ]
                }
            },
        },
    )
    write_json(
        acquisition_snapshot_paths["dryad"],
        {
            "schema_version": "semantic-catalog-snapshot/v1",
            "adapter_id": catalog_adapter.ADAPTER_ID,
            "source_repository": "dryad",
            "page_ordinal": 1,
            "request_url": "https://datadryad.org/api/v2/search?page=1",
            "retrieved_at": "2026-07-15T00:00:00Z",
            "raw_catalog_response": {
                "_embedded": {
                    "stash:datasets": [
                        {
                            "identifier": "doi:10.5061/dryad.fixture2",
                            "license": "CC-BY-4.0",
                            "fieldOfScience": "atmosphere",
                        }
                    ]
                }
            },
            "dataset_expansions": [
                {
                    "identifier": "doi:10.5061/dryad.fixture2",
                    "files_response": {
                        "_embedded": {
                            "stash:files": [
                                {
                                    "path": "blind_demo_2.csv",
                                    "size": packet_2_path.stat().st_size,
                                    "digest": sha256_file(packet_2_path),
                                    "digestType": "sha-256",
                                    "_links": {
                                        "stash:download": {
                                            "href": "/api/v2/files/blind_demo_2/download"
                                        }
                                    },
                                }
                            ]
                        }
                    },
                }
            ],
        },
    )
    acquisition_repositories = ["zenodo", "dryad"]
    write_json(
        acquisition_path,
        {
            "schema_version": "semantic-blind-acquisition-log/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "frozen_before_candidate_frame",
            "frozen_at": "2026-07-15T00:00:00Z",
            "construction_boundary": {
                "model_outputs_consulted": False,
                "architecture_results_consulted": False,
                "gold_labels_created": False,
            },
            "enumeration": {
                "adapter": {
                    "adapter_id": catalog_adapter.ADAPTER_ID,
                    "implementation": {
                        "file": str(acquisition_adapter_path),
                        "sha256": sha256_file(acquisition_adapter_path),
                    },
                },
                "retrieval_cutoff": "2026-07-15T00:00:00Z",
                "source_repositories": acquisition_repositories,
                "catalog_snapshots": [
                    {
                        "snapshot_id": f"snapshot::{repository}",
                        "source_repository": repository,
                        "page_ordinal": 1,
                        "request_url": (
                            "https://zenodo.org/api/records?page=1"
                            if repository == "zenodo"
                            else "https://datadryad.org/api/v2/search?page=1"
                        ),
                        "retrieved_at": "2026-07-15T00:00:00Z",
                        "returned_dataset_record_count": 1,
                        "enumerated_resource_count": 1,
                        "response": {
                            "file": acquisition_snapshot_paths[repository].name,
                            "sha256": sha256_file(
                                acquisition_snapshot_paths[repository]
                            ),
                        },
                    }
                    for repository in acquisition_repositories
                ],
                "repository_boundaries": [
                    {
                        "source_repository": repository,
                        "last_page_ordinal": 1,
                        "termination_reason": "frozen_page_cap_reached",
                    }
                    for repository in acquisition_repositories
                ],
            },
            "acquisition_criteria": {
                "inclusion": [
                    {
                        "criterion_id": "supported_fixture_resource",
                        "description": "resource is supported by the fixture",
                        "assessment_method": "deterministic fixture check",
                    }
                ],
                "exclusion": [
                    {
                        "criterion_id": "oversize_resource",
                        "description": "resource exceeds the fixture cap",
                        "assessment_method": "deterministic byte-size check",
                    }
                ],
            },
            "counts": {
                "enumerated_resource_count": 2,
                "eligible_for_acquisition_count": 2,
                "acquired_count": 2,
                "download_failed_count": 0,
                "excluded_before_download_count": 0,
            },
            "records": acquisition_records,
        },
    )
    write_json(
        candidate_frame_path,
        {
            "schema_version": "semantic-blind-candidate-frame/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "frozen_before_selection",
            "frozen_at": "2026-07-15T00:00:00Z",
            "construction_boundary": {
                "model_outputs_consulted": False,
                "architecture_results_consulted": False,
                "gold_labels_created": False,
                "eligibility_decided_before_selection": True,
            },
            "frame_definition": {
                "source_identity_algorithm": "canonical_source_tuple_sha256/v1",
                "scope_statement": "All resources in the two-record fixture frame.",
                "candidate_unit": "one local fixture resource",
                "enumeration_method": "enumerate both fixture records",
                "retrieval_cutoff": "2026-07-15T00:00:00Z",
                "source_repositories": [
                    "zenodo",
                    "dryad",
                ],
                "inclusion_criteria": [
                    {
                        "criterion_id": "supported_fixture_format",
                        "description": "resource has the supported fixture format",
                        "assessment_method": "deterministic fixture check",
                    }
                ],
                "exclusion_criteria": [
                    {
                        "criterion_id": "known_nonblind_overlap",
                        "description": "resource hash or source identity is known non-blind",
                        "assessment_method": "deterministic hash or identity membership",
                    }
                ],
            },
            "known_nonblind_resources": {
                "file": known_resources_path.name,
                "sha256": sha256_file(known_resources_path),
            },
            "acquisition_log": {
                "file": acquisition_path.name,
                "sha256": sha256_file(acquisition_path),
            },
            "candidates": sampling_candidates,
        },
    )
    write_json(
        sampling_design_path,
        {
            "schema_version": "semantic-blind-sampling-design/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "frozen_before_selection",
            "design_id": "fixture-blind-selection",
            "candidate_frame": {
                "file": candidate_frame_path.name,
                "sha256": sha256_file(candidate_frame_path),
            },
            "power_analysis": {
                "file": power_path.name,
                "sha256": sha256_file(power_path),
            },
            "selection_algorithm": "stratum_ordered_sha256_priority_with_frozen_caps/v1",
            "selection_seed": "fixture-selection-seed",
            "seed_provenance": {
                "method": "externally registered literal",
                "source": "fixture append-only registry",
                "committed_before_selection": True,
            },
            "required_dataset_count": 2,
            "required_semantic_opportunity_case_count": 2,
            "stratum_quotas": {"csv": 2},
            "minimum_scientific_family_count": 1,
            "maximum_cases_per_dataset_group": 1,
            "maximum_cases_per_source_repository": 1,
        },
    )
    write_json(
        sampling_receipt_path,
        {
            "schema_version": "semantic-sampling-registration-receipt/v1",
            "design_sha256": sha256_file(sampling_design_path),
            "registered_at": "2026-07-15T01:00:00Z",
            "registry": "fixture append-only registry",
            "registration_identifier": "fixture-selection-registration",
            "frozen_before_selection": True,
            "selection_not_executed_at_registration": True,
        },
    )
    sampling_selection = build_blind_selection(
        design_path=sampling_design_path,
        receipt_path=sampling_receipt_path,
        output_path=sampling_selection_path,
    )
    write_json(sampling_selection_path, sampling_selection)

    manifest = {
        "schema_version": "minimal-architecture-manifest/v2",
        "protocol_version": "semantic-architecture-protocol/v1",
        "benchmark_role": "blind_external",
        "frozen_at": "2026-07-15T00:00:00Z",
        "annotation_policy": {
            "independent_annotator_count": 2,
            "developer_participation": False,
            "model_outputs_visible": False,
            "consensus_after_independent_freeze": True,
            "handbook_file": "handbook.md",
            "handbook_sha256": sha256_file(handbook_path),
            "vocabulary_file": "vocabulary.json",
            "vocabulary_sha256": sha256_file(vocabulary_path),
            "annotator_calibration_summary_file": str(
                annotator_calibration_paths["summary"].relative_to(root)
            ),
            "annotator_calibration_summary_sha256": sha256_file(
                annotator_calibration_paths["summary"]
            ),
            "qualified_annotator_ids": ["annotator-a", "annotator-b"],
        },
        "design": {
            "primary_statistical_unit": "dataset",
            "required_dataset_count": power["assumptions"]["required_dataset_count"],
            "required_semantic_opportunity_case_count": power["assumptions"][
                "required_semantic_opportunity_case_count"
            ],
            "power_analysis_file": "power.json",
            "power_analysis_sha256": sha256_file(power_path),
            "analysis_plan_file": "analysis-plan.json",
            "analysis_plan_sha256": sha256_file(analysis_plan_path),
            "sampling_selection_file": "sampling-selection.json",
            "sampling_selection_sha256": sha256_file(sampling_selection_path),
            "evaluation_implementation": {
                "architecture_evaluation": {
                    "file": "architecture_evaluation.py",
                    "sha256": sha256_file(
                        Path(__file__).parents[1] / "architecture_evaluation.py"
                    ),
                },
                "architecture_variants": {
                    "file": "architecture_variants.py",
                    "sha256": sha256_file(
                        Path(__file__).parents[1] / "architecture_variants.py"
                    ),
                },
                "unit_normalization": {
                    "file": "unit_normalization.py",
                    "sha256": sha256_file(
                        Path(__file__).parents[1] / "unit_normalization.py"
                    ),
                },
            },
        },
        "backend_registry_file": "backends.json",
        "backend_registry_sha256": sha256_file(registry_path),
        "cases": [
            {
                "case_id": "blind_demo",
                "dataset_family": "atmosphere",
                "file_format": "csv",
                "difficulty": "calibrated",
                "task_file": "task.json",
                "task_sha256": sha256_file(task_path),
                "annotation_packet_file": "packet.json",
                "annotation_packet_sha256": sha256_file(packet_path),
                "source_bundle_file": "source-bundle.json",
                "source_bundle_sha256": sha256_file(source_bundle_path),
                "independent_annotations": [
                    {
                        "artifact_file": "annotation-a.json",
                        "artifact_sha256": sha256_file(annotation_a_path),
                    },
                    {
                        "artifact_file": "annotation-b.json",
                        "artifact_sha256": sha256_file(annotation_b_path),
                    },
                ],
                "disagreement_report_file": "disagreement.json",
                "disagreement_report_sha256": sha256_file(disagreement_path),
                "gold_file": "gold.json",
                "gold_sha256": sha256_file(gold_path),
                "split": "blind_external",
            },
            {
                "case_id": "blind_demo_2",
                "dataset_family": "atmosphere",
                "file_format": "csv",
                "difficulty": "calibrated",
                "task_file": "task-2.json",
                "task_sha256": sha256_file(task_2_path),
                "annotation_packet_file": "packet-2.json",
                "annotation_packet_sha256": sha256_file(packet_2_path),
                "source_bundle_file": "source-bundle-2.json",
                "source_bundle_sha256": sha256_file(source_bundle_2_path),
                "independent_annotations": [
                    {
                        "artifact_file": "annotation-2-a.json",
                        "artifact_sha256": sha256_file(annotation_2_a_path),
                    },
                    {
                        "artifact_file": "annotation-2-b.json",
                        "artifact_sha256": sha256_file(annotation_2_b_path),
                    },
                ],
                "disagreement_report_file": "disagreement-2.json",
                "disagreement_report_sha256": sha256_file(disagreement_2_path),
                "gold_file": "gold-2.json",
                "gold_sha256": sha256_file(gold_2_path),
                "split": "blind_external",
            },
        ],
    }
    manifest_cases_by_id = {item["case_id"]: item for item in manifest["cases"]}
    manifest["cases"] = [
        manifest_cases_by_id[item["case_id"]]
        for item in sampling_selection["selected_cases"]
    ]
    manifest_path = root / "manifest.json"
    write_json(manifest_path, manifest)
    return manifest_path


def refresh_manifest_hash(manifest_path: Path, key: str, artifact: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[key] = sha256_file(artifact)
    write_json(manifest_path, manifest)


def test_valid_blind_freeze_passes_preflight(tmp_path: Path) -> None:
    report = preflight_blind_manifest(build_fixture(tmp_path))

    assert report["status"] == "ready"
    assert report["errors"] == []
    assert report["summary"] == {
        "case_count": 2,
        "semantic_opportunity_case_count": 2,
        "semantic_target_count": 2,
        "backend_count": 3,
        "backend_family_count": 3,
        "primary_backend_id": "qwen-primary",
    }


def test_blind_manifest_requires_untampered_analysis_plan(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plan_path = manifest_path.parent / manifest["design"]["analysis_plan_file"]
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["multiplicity"]["familywise_alpha"] = 0.1
    write_json(plan_path, plan)
    manifest["design"]["analysis_plan_sha256"] = sha256_file(plan_path)
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "analysis_plan_recalculation_mismatch" in {
        item["code"] for item in report["errors"]
    }


def test_blind_manifest_order_must_match_registered_selection(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"].reverse()
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "sampling_selection_case_mismatch" in {
        item["code"] for item in report["errors"]
    }


def test_semantic_contract_hashes_are_complete_and_stable_shape() -> None:
    hashes = semantic_contract_hashes()

    assert set(hashes) == {
        "dataset_reasoner_prompt_sha256",
        "dataset_reasoner_schema_sha256",
        "legacy_prompt_sha256",
        "legacy_schema_sha256",
    }
    assert all(len(value) == 64 for value in hashes.values())


def test_missing_semantic_target_gold_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    gold_path = tmp_path / "gold.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    gold["fields"][0]["field_path"] = "different_field"
    for item in gold["fields"][0]["gold_evidence"]:
        item["field_path"] = "different_field"
    write_json(gold_path, gold)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"][0]["gold_sha256"] = sha256_file(gold_path)
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "semantic_targets_missing_from_gold" in {
        item["code"] for item in report["errors"]
    }


def test_frozen_artifact_hash_mismatch_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    (tmp_path / "task.json").write_text("{}\n", encoding="utf-8")

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "frozen_hash_mismatch" in {item["code"] for item in report["errors"]}


def test_incomplete_gold_applicability_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    gold_path = tmp_path / "gold.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    del gold["fields"][0]["applicability"]["unit"]
    write_json(gold_path, gold)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"][0]["gold_sha256"] = sha256_file(gold_path)
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "gold_applicability_incomplete" in {
        item["code"] for item in report["errors"]
    }


def test_missing_property_rationale_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    gold_path = tmp_path / "gold.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    gold["fields"][0]["rationales"]["unit"] = None
    write_json(gold_path, gold)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"][0]["gold_sha256"] = sha256_file(gold_path)
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "gold_rationale_missing" in {item["code"] for item in report["errors"]}


def test_tampered_independent_annotation_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    annotation_path = tmp_path / "annotation-a.json"
    annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
    annotation["fields"][0]["notes"] = "post-freeze change"
    write_json(annotation_path, annotation)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "frozen_hash_mismatch" in {item["code"] for item in report["errors"]}


def test_missing_frozen_vocabulary_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["annotation_policy"]["vocabulary_file"]
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "missing_file_path" in {item["code"] for item in report["errors"]}


def test_failed_annotator_calibration_gate_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    vocabulary_path = tmp_path / "vocabulary.json"
    handbook_path = tmp_path / "handbook.md"
    failed_paths = build_annotator_calibration_round(
        tmp_path / "failed-annotator-calibration",
        disagreement_case="case-1",
        exact_thresholds=True,
        vocabulary_path_override=vocabulary_path,
        handbook_path_override=handbook_path,
    )
    failed_summary = build_annotator_calibration_summary(
        round_manifest_path=failed_paths["round"],
        output_path=failed_paths["summary"],
    )
    assert failed_summary["status"] == "failed"
    write_json(failed_paths["summary"], failed_summary)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["annotation_policy"]["annotator_calibration_summary_file"] = str(
        failed_paths["summary"].relative_to(tmp_path)
    )
    manifest["annotation_policy"]["annotator_calibration_summary_sha256"] = sha256_file(
        failed_paths["summary"]
    )
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "annotator_calibration_not_passed" in {
        item["code"] for item in report["errors"]
    }


def test_unqualified_blind_annotator_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    annotation_path = tmp_path / "annotation-a.json"
    annotation = json.loads(annotation_path.read_text(encoding="utf-8"))
    annotation["annotator_id"] = "unqualified-annotator"
    write_json(annotation_path, annotation)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"][0]["independent_annotations"][0]["artifact_sha256"] = sha256_file(
        annotation_path
    )
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "blind_annotator_not_calibration_qualified" in {
        item["code"] for item in report["errors"]
    }


def test_declared_qualified_annotators_must_match_gate(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["annotation_policy"]["qualified_annotator_ids"] = [
        "annotator-a",
        "someone-else",
    ]
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "qualified_annotator_ids_mismatch" in {
        item["code"] for item in report["errors"]
    }


def test_backend_panel_below_three_families_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    registry_path = tmp_path / "backends.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["backends"] = registry["backends"][:2]
    write_json(registry_path, registry)
    refresh_manifest_hash(manifest_path, "backend_registry_sha256", registry_path)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "backend_panel_too_small" in {item["code"] for item in report["errors"]}


def test_unfrozen_power_analysis_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    power_path = tmp_path / "power.json"
    power = json.loads(power_path.read_text(encoding="utf-8"))
    power["status"] = "draft"
    write_json(power_path, power)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["design"]["power_analysis_sha256"] = sha256_file(power_path)
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "power_analysis_not_frozen" in {item["code"] for item in report["errors"]}


def test_wrong_power_estimand_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    power_path = tmp_path / "power.json"
    power = json.loads(power_path.read_text(encoding="utf-8"))
    power["primary_outcome"] = "pooled_field_accuracy"
    write_json(power_path, power)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["design"]["power_analysis_sha256"] = sha256_file(power_path)
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "power_primary_outcome_invalid" in {
        item["code"] for item in report["errors"]
    }


def test_tampered_power_calculation_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    power_path = tmp_path / "power.json"
    power = json.loads(power_path.read_text(encoding="utf-8"))
    power["calculation"]["probability_of_at_least_required_opportunities"] = 0.5
    write_json(power_path, power)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["design"]["power_analysis_sha256"] = sha256_file(power_path)
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "power_analysis_recalculation_mismatch" in {
        item["code"] for item in report["errors"]
    }


def test_missing_power_calibration_statistics_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    (tmp_path / "calibration-statistics.json").unlink()

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "file_missing" in {item["code"] for item in report["errors"]}


def test_power_config_cannot_override_deterministic_calibration_rates(
    tmp_path: Path,
) -> None:
    manifest_path = build_fixture(tmp_path)
    power_path = tmp_path / "power.json"
    power = json.loads(power_path.read_text(encoding="utf-8"))
    config = power["planning_inputs"]
    config["noncomparability_rate"] = 0.1
    rebuilt = build_power_analysis(config)
    write_json(power_path, rebuilt)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["design"]["power_analysis_sha256"] = sha256_file(power_path)
    manifest["design"]["required_dataset_count"] = rebuilt["assumptions"][
        "required_dataset_count"
    ]
    manifest["design"]["required_semantic_opportunity_case_count"] = rebuilt[
        "assumptions"
    ]["required_semantic_opportunity_case_count"]
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "power_calibration_binding_invalid" in {
        item["code"] for item in report["errors"]
    }


def test_evaluator_implementation_hash_mismatch_blocks_freeze(
    tmp_path: Path,
) -> None:
    manifest_path = build_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["design"]["evaluation_implementation"]["architecture_evaluation"][
        "sha256"
    ] = "b" * 64
    write_json(manifest_path, manifest)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "evaluation_implementation_hash_mismatch" in {
        item["code"] for item in report["errors"]
    }


def test_backend_below_frozen_qualification_threshold_blocks_freeze(
    tmp_path: Path,
) -> None:
    manifest_path = build_fixture(tmp_path)
    registry_path = tmp_path / "backends.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["backends"][0]["qualification"]["contract_valid_rate"] = 0.5
    write_json(registry_path, registry)
    refresh_manifest_hash(manifest_path, "backend_registry_sha256", registry_path)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "backend_contract_rate_below_threshold" in {
        item["code"] for item in report["errors"]
    }


def test_qualification_report_hash_mismatch_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    report_path = tmp_path / "qwen-primary.qualification.json"
    report_path.write_text("{}\n", encoding="utf-8")

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "frozen_hash_mismatch" in {item["code"] for item in report["errors"]}


def test_backend_qualification_vocabulary_mismatch_blocks_freeze(
    tmp_path: Path,
) -> None:
    manifest_path = build_fixture(tmp_path)
    registry_path = tmp_path / "backends.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["backends"][0]["qualification"]["qualification_vocabulary_sha256"] = (
        "b" * 64
    )
    write_json(registry_path, registry)
    refresh_manifest_hash(manifest_path, "backend_registry_sha256", registry_path)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "backend_qualification_vocabulary_mismatch" in {
        item["code"] for item in report["errors"]
    }


def test_backend_calibration_manifest_mismatch_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    registry_path = tmp_path / "backends.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["backends"][0]["qualification"]["calibration_manifest_sha256"] = "b" * 64
    write_json(registry_path, registry)
    refresh_manifest_hash(manifest_path, "backend_registry_sha256", registry_path)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "backend_calibration_manifest_mismatch" in {
        item["code"] for item in report["errors"]
    }


def test_replay_identity_below_frozen_threshold_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    report_path = tmp_path / "qwen-primary.qualification.json"
    qualification_report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    qualification_report_payload["dataset_reasoner"]["replay_identity_rate"] = 0.5
    write_json(report_path, qualification_report_payload)

    registry_path = tmp_path / "backends.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["backends"][0]["qualification"]["replay_identity_rate"] = 0.5
    registry["backends"][0]["qualification"]["qualification_report_sha256"] = (
        sha256_file(report_path)
    )
    write_json(registry_path, registry)
    refresh_manifest_hash(manifest_path, "backend_registry_sha256", registry_path)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "backend_qualification_minimum_below_threshold" in {
        item["code"] for item in report["errors"]
    }


def test_qualification_summary_mismatch_blocks_freeze(tmp_path: Path) -> None:
    manifest_path = build_fixture(tmp_path)
    registry_path = tmp_path / "backends.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["backends"][0]["qualification"]["context_fit_rate"] = 0.99
    registry["qualification_policy"]["minimum_context_fit_rate"] = 0.9
    write_json(registry_path, registry)
    refresh_manifest_hash(manifest_path, "backend_registry_sha256", registry_path)

    report = preflight_blind_manifest(manifest_path)

    assert report["status"] == "blocked"
    assert "qualification_report_summary_mismatch" in {
        item["code"] for item in report["errors"]
    }
