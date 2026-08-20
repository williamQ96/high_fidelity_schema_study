from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_cpa_design import (
    registered_analysis_contract,
    registered_metric_contract,
)
from high_fidelity_schema_study.ndp50_execution_freeze import (
    NDPExecutionFreezeError,
    build_config_template,
    build_freeze,
    build_workflow_spec,
    validate_config,
    verify_freeze,
)
from high_fidelity_schema_study.ndp50_execution_qualification import (
    DECLARATION_SCHEMA_VERSION,
    build_qualification_receipt,
    interface_version,
)


ARMS = [
    "deterministic_only",
    "zero_shot_dataset_level",
    "zero_shot_byte_identical_response_plus_deterministic_verification",
    "one_shot_development_similarity_selected",
    "five_shot_development_similarity_selected",
]


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, dict):
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    else:
        text = str(payload)
    path.write_text(text, encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(path: Path, root: Path) -> dict[str, str]:
    return {
        "file": path.relative_to(root).as_posix(),
        "sha256": _sha(path),
    }


def _fixture(tmp_path: Path, monkeypatch) -> dict:
    root = tmp_path / "ndp50"
    design_path = root / "semantic" / "cpa_design.json"
    design = {
        "schema_version": "ndp50-cpa-design/v1",
        "planned_arms": ARMS,
        "row_sampling_sensitivity": [
            "head",
            "fixed_seed_stratified",
            "fixed_seed_adaptive",
        ],
        "analysis": registered_analysis_contract(),
        "metric_contract": registered_metric_contract(),
    }
    _write(design_path, design)
    packet_manifest_path = root / "semantic" / "packets.json"
    packet_cases = [
        {
            "case_id": f"case-dev-{index}",
            "split": "development",
        }
        for index in range(1, 6)
    ] + [{"case_id": "case-val-1", "split": "validation"}]
    _write(
        packet_manifest_path,
        {
            "schema_version": "ndp50-semantic-packet-pack/v1",
            "status": "neutral_packets_ready_source_bundles_blocked",
            "case_count": len(packet_cases),
            "cases": packet_cases,
        },
    )
    vocabulary_path = root / "semantic" / "vocabulary.json"
    approved_source_path = root / "semantic" / "approved_sources.json"
    cpa_consensus_path = root / "semantic" / "cpa_consensus.json"
    gold_approval_path = root / "semantic" / "gold_approval.json"
    governance_audit_path = root / "reports" / "governance.json"
    governance_approval_path = root / "governance" / "approval.json"
    _write(vocabulary_path, {"status": "frozen"})
    _write(approved_source_path, {"status": "ready_for_independent_annotation"})
    _write(
        cpa_consensus_path,
        {"schema_version": "ndp50-cpa-applicability-consensus/v1"},
    )
    _write(governance_audit_path, {"status": "audit"})
    governance_approval = {
        "review": {
            "study_policy": {"model_processing_mode": "local_only"}
        }
    }
    _write(governance_approval_path, governance_approval)
    gold_cases = []
    for item in packet_cases:
        consensus = root / "semantic" / "gold" / f"{item['case_id']}.json"
        _write(consensus, {"case_id": item["case_id"]})
        gold_cases.append(
            {"case_id": item["case_id"], "consensus": _ref(consensus, root)}
        )
    gold_approval = {"index": {"cases": gold_cases}}
    _write(gold_approval_path, gold_approval)

    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_execution_freeze."
        "validate_vocabulary",
        lambda payload: {"status": "ready", "errors": []},
    )
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_execution_freeze."
        "load_approved_evidence_registry",
        lambda path: ({}, {}),
    )
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_execution_freeze."
        "verify_governance_approval",
        lambda *args, **kwargs: {"status": "passed"},
    )
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_execution_freeze."
        "verify_gold_approval",
        lambda *args, **kwargs: {"status": "passed"},
    )
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_execution_freeze."
        "verify_demonstration_pool",
        lambda *args, **kwargs: {"status": "passed"},
    )
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_execution_freeze."
        "preflight_backend_registry",
        lambda path: {"status": "ready", "errors": []},
    )

    common_code = root / "freeze" / "implementation.py"
    _write(
        common_code,
        "from high_fidelity_schema_study."
        "ndp50_execution_qualification import reference_probe_response\n\n"
        "def ndp50_qualification_probe(request):\n"
        "    return reference_probe_response(request)\n",
    )
    prompt_zero = root / "freeze" / "prompt-zero.txt"
    prompt_one = root / "freeze" / "prompt-one.txt"
    prompt_five = root / "freeze" / "prompt-five.txt"
    prompt_sensitivity_a = root / "freeze" / "prompt-sensitivity-a.txt"
    prompt_sensitivity_b = root / "freeze" / "prompt-sensitivity-b.txt"
    response_schema = root / "freeze" / "response-schema.json"
    for path, text in (
        (
            prompt_zero,
            "Vocabulary: {{candidate_vocabulary}}\nTable: {{target_table}}",
        ),
        (
            prompt_one,
            "Vocabulary: {{candidate_vocabulary}}\n"
            "Examples: {{demonstrations}}\nTable: {{target_table}}",
        ),
        (
            prompt_five,
            "Vocabulary: {{candidate_vocabulary}}\n"
            "Examples: {{demonstrations}}\nTable: {{target_table}}",
        ),
        (
            prompt_sensitivity_a,
            "Vocabulary: {{candidate_vocabulary}}\nTable: {{target_table}}",
        ),
        (
            prompt_sensitivity_b,
            "Vocabulary: {{candidate_vocabulary}}\nTable: {{target_table}}",
        ),
    ):
        _write(path, text)
    _write(
        response_schema,
        {
            "type": "object",
            "properties": {
                "slots": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "confidence_score": {
                                "type": ["number", "null"],
                                "minimum": 0,
                                "maximum": 1,
                            }
                        },
                        "required": ["confidence_score"],
                    },
                }
            },
        },
    )

    registry_path = root / "freeze" / "backend-registry.json"
    _write(
        registry_path,
        {
            "primary_backend_id": "local-primary",
            "backends": [
                {
                    "backend_id": "local-primary",
                    "endpoint": "http://127.0.0.1:1234/v1",
                }
            ],
        },
    )
    pool_path = root / "freeze" / "demonstration-pool.json"
    pool_cases = []
    gold_by_id = {item["case_id"]: item for item in gold_cases}
    for item in packet_cases[:5]:
        pool_cases.append(
            {
                "case_id": item["case_id"],
                "source_split": "development",
                "gold_consensus": gold_by_id[item["case_id"]]["consensus"],
                "input_projection": {"case_id": item["case_id"]},
                "gold_projection": {"case_id": item["case_id"]},
            }
        )
    _write(
        pool_path,
        {
            "schema_version": "ndp50-demonstration-pool/v2",
            "status": "validator_generated_development_only",
            "source_split": "development",
            "candidate_inclusion_policy": "all_approved_development_cases",
            "model_outputs_used_for_inclusion": False,
            "validation_or_test_candidates_included": False,
            "cases": pool_cases,
        },
    )

    config = build_config_template(
        cpa_design_path=design_path,
        packet_manifest_path=packet_manifest_path,
        study_root=root,
    )
    upstream_paths = {
        "frozen_vocabulary": vocabulary_path,
        "approved_source_manifest": approved_source_path,
        "cpa_consensus": cpa_consensus_path,
        "semantic_gold_approval": gold_approval_path,
        "data_governance_audit": governance_audit_path,
        "data_governance_approval": governance_approval_path,
    }
    config.update(
        {
            "status": "completed_pending_validator_freeze",
            "human_decisions_present": True,
            "upstream_bindings": {
                key: _ref(path, root) for key, path in upstream_paths.items()
            },
            "signoffs": [
                {
                    "slot": "study_operator",
                    "signatory_id": "operator-1",
                    "role": "research_engineer",
                    "institution": "Example University",
                    "qualification_summary": "Runs frozen study infrastructure.",
                    "conflict_of_interest_declared": False,
                    "developer_participation": True,
                    "signed_on": "2026-07-26",
                },
                {
                    "slot": "methods_reviewer",
                    "signatory_id": "reviewer-1",
                    "role": "independent_methods_reviewer",
                    "institution": "Example University",
                    "qualification_summary": "Reviews experimental methods.",
                    "conflict_of_interest_declared": False,
                    "developer_participation": False,
                    "signed_on": "2026-07-26",
                },
            ],
            "completion_attestation": True,
        }
    )
    config["analysis_contract"]["primary_contrasts"] = [
        {
            "contrast_id": "deterministic-vs-zero",
            "arm_a": "deterministic_only",
            "arm_b": "zero_shot_dataset_level",
        },
        {
            "contrast_id": "zero-vs-verified",
            "arm_a": "zero_shot_dataset_level",
            "arm_b": (
                "zero_shot_byte_identical_response_plus_"
                "deterministic_verification"
            ),
        },
    ]
    prompt_paths = {
        "zero_shot_dataset_level": (prompt_zero, 0),
        "one_shot_development_similarity_selected": (prompt_one, 1),
        "five_shot_development_similarity_selected": (prompt_five, 5),
    }
    config["prompt_contracts"] = [
        {
            "arm_id": arm_id,
            "shot_count": shot_count,
            "prompt": _ref(path, root),
            "response_schema": _ref(response_schema, root),
            "paper_factorization": {
                "task_description_variant": "explicit_cpa",
                "instruction_variant": "bounded_steps",
                "classification_wording": "relationships",
            },
            "candidate_vocabulary_in_prompt": True,
            "output_candidate_or_oov_only": True,
            "message_order": (
                ["system", "user_target"]
                if shot_count == 0
                else ["system"]
                + [
                    value
                    for _ in range(shot_count)
                    for value in (
                        "user_demonstration",
                        "assistant_demonstration",
                    )
                ]
                + ["user_target"]
            ),
        }
        for arm_id, (path, shot_count) in prompt_paths.items()
    ]
    config["prompt_sensitivity_contracts"] = [
        {
            "variant_id": "classification-classify",
            "prompt": _ref(prompt_sensitivity_a, root),
            "is_primary": False,
            "paper_factorization": {
                "task_description_variant": "explicit_cpa",
                "instruction_variant": "bounded_steps",
                "classification_wording": "classify",
            },
            "analysis_role": "descriptive_sensitivity_only",
        },
        {
            "variant_id": "classification-relationships",
            "prompt": _ref(prompt_sensitivity_b, root),
            "is_primary": True,
            "paper_factorization": {
                "task_description_variant": "explicit_cpa",
                "instruction_variant": "bounded_steps",
                "classification_wording": "relationships",
            },
            "analysis_role": "descriptive_sensitivity_only",
        },
    ]
    config["serialization_contract"] = {
        "table_format": "markdown",
        "column_order_policy": "source_order",
        "row_order_policy": "sampler_output_order",
        "missing_value_rendering": "explicit_NA_token",
        "missing_display_cell_fill_policy": "no_cross_row_imputation",
        "value_escaping_policy": "markdown_pipe_and_newline_escape",
        "max_cell_characters": 256,
        "truncation_marker": "<TRUNCATED>",
        "metadata_fields": ["dataset_title", "column_headers"],
    }
    config["row_sampling_contract"]["primary_sampler_id"] = (
        "fixed_seed_stratified"
    )
    for item in config["row_sampling_contract"]["sensitivity_samplers"]:
        item["implementation"] = _ref(common_code, root)
        item["seed"] = None if item["sampler_id"] == "head" else 1729
        item["parameters"] = {"row_count": 5}
    config["demonstration_contract"].update(
        {
            "candidate_pool_manifest": _ref(pool_path, root),
            "selection_method": "deterministic_lexical",
            "ranking_implementation": _ref(common_code, root),
            "similarity_model": None,
        }
    )
    config["backend_contract"].update(
        {
            "registry": _ref(registry_path, root),
            "primary_backend_id": "local-primary",
            "external_service_used": False,
            "seed": 12345,
            "max_tokens": 1024,
        }
    )
    config["resource_accounting_contract"].update(
        {
            "price_basis": "local_compute_not_monetized",
            "pricing_effective_on": "2026-07-26",
            "pricing_source": "not_applicable_local_compute",
            "rates_usd": {
                "per_call": 0,
                "input_per_million_tokens": 0,
                "output_per_million_tokens": 0,
            },
            "local_compute_cost_included": False,
            "cost_scope_note": (
                "Local compute is not monetized; exact hardware, runtime, "
                "tokens, calls, and dual latency are reported."
            ),
        }
    )
    config["confidence_reporting_contract"][
        "confidence_source_by_arm"
    ] = {
        "deterministic_only": "frozen deterministic support ordering",
        "zero_shot_dataset_level": "model-reported exactness probability",
        "one_shot_development_similarity_selected": (
            "model-reported exactness probability"
        ),
        "five_shot_development_similarity_selected": (
            "model-reported exactness probability"
        ),
        "zero_shot_byte_identical_response_plus_deterministic_verification": (
            "source-response confidence retained for accepted claims"
        ),
    }
    config["confidence_reporting_contract"][
        "confidence_interpretation_by_arm"
    ] = {
        "deterministic_only": "ordering_score_only",
        "zero_shot_dataset_level": "probability_of_exact_correctness",
        "one_shot_development_similarity_selected": (
            "probability_of_exact_correctness"
        ),
        "five_shot_development_similarity_selected": (
            "probability_of_exact_correctness"
        ),
        "zero_shot_byte_identical_response_plus_deterministic_verification": (
            "probability_of_exact_correctness"
        ),
    }
    declared_implementations = {
        key: {
            "artifact": _ref(common_code, root),
            "entrypoint": "ndp50_qualification_probe",
            "interface_version": interface_version(key),
        }
        for key in config["execution_implementations"]
    }
    declaration_path = root / "freeze" / "implementation-declaration.json"
    _write(
        declaration_path,
        {
            "schema_version": DECLARATION_SCHEMA_VERSION,
            "status": "complete_pending_qualification",
            "synthetic_probes_only": True,
            "development_validation_or_test_data_used": False,
            "implementations": declared_implementations,
            "completion_attestation": True,
        },
    )
    receipt_path = root / "freeze" / "implementation-qualification.json"
    _write(
        receipt_path,
        build_qualification_receipt(
            declaration_path=declaration_path,
            study_root=root,
        ),
    )
    config["execution_implementations"] = declared_implementations
    config["execution_qualification"] = {
        "declaration": _ref(declaration_path, root),
        "receipt": _ref(receipt_path, root),
    }
    config["execution_order"] = {
        "case_order_policy": "fixed_seed_hash_rank",
        "case_order_seed": 99173,
        "arm_interleaving_policy": (
            "case_major_seeded_cyclic_execution_blocks"
        ),
        "arm_order_seed": 37,
        "retry_policy": "one_transport_retry_no_prompt_mutation",
        "request_timeout_seconds": 300,
        "maximum_attempts_per_call": 2,
    }
    return {
        "root": root,
        "study_root": root,
        "config": config,
        "cpa_design_path": design_path,
        "packet_manifest_path": packet_manifest_path,
        "vocabulary_path": vocabulary_path,
        "approved_source_manifest_path": approved_source_path,
        "cpa_consensus_path": cpa_consensus_path,
        "semantic_gold_approval_path": gold_approval_path,
        "data_governance_audit_path": governance_audit_path,
        "data_governance_approval_path": governance_approval_path,
        "pool_path": pool_path,
    }


def test_neutral_template_and_workflow_do_not_claim_freeze(
    tmp_path: Path,
) -> None:
    root = tmp_path / "ndp50"
    design = root / "design.json"
    packets = root / "packets.json"
    _write(
        design,
        {
            "schema_version": "ndp50-cpa-design/v1",
            "planned_arms": ARMS,
            "row_sampling_sensitivity": [
                "head",
                "fixed_seed_stratified",
                "fixed_seed_adaptive",
            ],
            "analysis": registered_analysis_contract(),
            "metric_contract": registered_metric_contract(),
        },
    )
    _write(
        packets,
        {
            "schema_version": "ndp50-semantic-packet-pack/v1",
            "status": "neutral_packets_ready_source_bundles_blocked",
            "case_count": 1,
            "cases": [{"case_id": "dev", "split": "development"}],
        },
    )
    template_path = root / "template.json"
    template = build_config_template(
        cpa_design_path=design,
        packet_manifest_path=packets,
        study_root=root,
    )
    _write(template_path, template)
    workflow = build_workflow_spec(
        cpa_design_path=design,
        packet_manifest_path=packets,
        config_template_path=template_path,
        study_root=root,
    )

    assert template["human_decisions_present"] is False
    assert template["prompt_contracts"] == []
    assert template["backend_contract"]["registry"] is None
    assert template["resource_accounting_contract"]["price_basis"] is None
    assert (
        template["resource_accounting_contract"][
            "include_failed_model_calls"
        ]
        is True
    )
    assert (
        template["confidence_reporting_contract"]["score_field"]
        == "confidence_score"
    )
    assert (
        template["confidence_reporting_contract"][
            "minimum_group_support_for_calibration_claim"
        ]
        == 30
    )
    assert all(
        value is None
        for value in template["confidence_reporting_contract"][
            "confidence_source_by_arm"
        ].values()
    )
    assert template["execution_qualification"] == {
        "declaration": None,
        "receipt": None,
    }
    assert workflow["automatic_freeze"] is False
    assert workflow["implementation_qualification_required"] is True
    assert workflow["minimum_prompt_sensitivity_variants"] == 2
    assert workflow["primary_prompt_sensitivity_anchor_required"] is True
    assert workflow["primary_row_sampler_anchor_required"] is True
    assert workflow["sensitivity_single_factor_at_a_time_required"] is True


def test_prepare_rejects_test_cases(tmp_path: Path) -> None:
    root = tmp_path / "ndp50"
    design = root / "design.json"
    packets = root / "packets.json"
    _write(
        design,
        {
            "schema_version": "ndp50-cpa-design/v1",
            "planned_arms": ARMS,
            "row_sampling_sensitivity": ["head"],
            "analysis": {},
        },
    )
    _write(
        packets,
        {
            "schema_version": "ndp50-semantic-packet-pack/v1",
            "status": "neutral_packets_ready_source_bundles_blocked",
            "case_count": 1,
            "cases": [{"case_id": "sealed-test", "split": "test"}],
        },
    )

    with pytest.raises(NDPExecutionFreezeError, match="cannot contain test"):
        build_config_template(
            cpa_design_path=design,
            packet_manifest_path=packets,
            study_root=root,
        )


def test_valid_configuration_builds_and_replays_freeze(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    config = inputs.pop("config")
    inputs.pop("pool_path")
    inputs.pop("root")

    validation = validate_config(config, **inputs)
    frozen = build_freeze(config=config, **inputs)

    assert validation["status"] == "passed"
    assert frozen["derived_gates"]["prompt_and_backend_frozen"] is True
    assert verify_freeze(frozen, **inputs)["status"] == "passed"

    config["confidence_reporting_contract"][
        "pooling_across_labels_permitted"
    ] = True
    invalid_confidence = validate_config(config, **inputs)
    assert "confidence_pooling_invalid" in {
        item["code"] for item in invalid_confidence["errors"]
    }
    config["confidence_reporting_contract"][
        "pooling_across_labels_permitted"
    ] = False
    config["resource_accounting_contract"][
        "include_failed_model_calls"
    ] = False
    invalid = validate_config(config, **inputs)
    assert "resource_accounting_scope_invalid" in {
        item["code"] for item in invalid["errors"]
    }


def test_demonstration_pool_rejects_validation_case(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    config = inputs.pop("config")
    pool_path = inputs.pop("pool_path")
    root = inputs.pop("root")
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    pool["cases"][0]["case_id"] = "case-val-1"
    _write(pool_path, pool)
    config["demonstration_contract"]["candidate_pool_manifest"] = _ref(
        pool_path, root
    )

    validation = validate_config(config, **inputs)

    assert "demonstration_case_invalid" in {
        item["code"] for item in validation["errors"]
    }


def test_local_governance_rejects_external_backend(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    config = inputs.pop("config")
    inputs.pop("pool_path")
    inputs.pop("root")
    config["backend_contract"]["external_service_used"] = True

    validation = validate_config(config, **inputs)

    assert "local_policy_backend_transfer" in {
        item["code"] for item in validation["errors"]
    }


def test_analysis_contract_rejects_post_outcome_case_deletion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    config = inputs.pop("config")
    inputs.pop("pool_path")
    inputs.pop("root")
    config["analysis_contract"]["missingness_policy"][
        "post_outcome_case_deletion"
    ] = True

    validation = validate_config(config, **inputs)

    assert "analysis_contract_changed" in {
        item["code"] for item in validation["errors"]
    }


def test_prompt_sensitivity_requires_one_primary_zero_shot_anchor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    config = inputs.pop("config")
    inputs.pop("pool_path")
    inputs.pop("root")
    for item in config["prompt_sensitivity_contracts"]:
        item["is_primary"] = False

    validation = validate_config(config, **inputs)

    assert "prompt_sensitivity_primary_anchor_invalid" in {
        item["code"] for item in validation["errors"]
    }


def test_prompt_sensitivity_primary_anchor_must_match_zero_shot(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    config = inputs.pop("config")
    inputs.pop("pool_path")
    inputs.pop("root")
    primary = next(
        item
        for item in config["prompt_sensitivity_contracts"]
        if item["is_primary"]
    )
    primary["paper_factorization"]["classification_wording"] = "changed"

    validation = validate_config(config, **inputs)

    assert "prompt_sensitivity_primary_anchor_mismatch" in {
        item["code"] for item in validation["errors"]
    }


def test_prompt_sensitivity_variant_count_is_bounded(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    config = inputs.pop("config")
    inputs.pop("pool_path")
    inputs.pop("root")
    template = config["prompt_sensitivity_contracts"][0]
    for index in range(3):
        config["prompt_sensitivity_contracts"].append(
            {
                **template,
                "variant_id": f"extra-variant-{index}",
                "is_primary": False,
            }
        )

    validation = validate_config(config, **inputs)

    assert "prompt_sensitivity_count_invalid" in {
        item["code"] for item in validation["errors"]
    }


def test_execution_order_rejects_unregistered_interleaving_policy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    config = inputs.pop("config")
    inputs.pop("pool_path")
    inputs.pop("root")
    config["execution_order"][
        "arm_interleaving_policy"
    ] = "case_major_registered_arm_order"

    validation = validate_config(config, **inputs)

    assert "arm_interleaving_policy_invalid" in {
        item["code"] for item in validation["errors"]
    }


def test_unqualified_implementation_substitution_is_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    config = inputs.pop("config")
    inputs.pop("pool_path")
    inputs.pop("root")
    config["execution_implementations"]["scorer"][
        "entrypoint"
    ] = "unqualified_replacement"

    validation = validate_config(config, **inputs)

    assert "execution_implementation_declaration_mismatch" in {
        item["code"] for item in validation["errors"]
    }


def test_sampler_cannot_bypass_qualified_component(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    config = inputs.pop("config")
    inputs.pop("pool_path")
    root = inputs.pop("root")
    substitute = root / "freeze" / "unqualified-sampler.py"
    _write(substitute, "def sample(rows):\n    return rows\n")
    config["row_sampling_contract"]["sensitivity_samplers"][0][
        "implementation"
    ] = _ref(substitute, root)

    validation = validate_config(config, **inputs)

    assert "qualified_component_binding_mismatch" in {
        item["code"] for item in validation["errors"]
    }


def test_tampered_freeze_fails_replay(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    config = inputs.pop("config")
    inputs.pop("pool_path")
    inputs.pop("root")
    frozen = build_freeze(config=config, **inputs)
    frozen["derived_gates"]["prompt_and_backend_frozen"] = False

    validation = verify_freeze(frozen, **inputs)

    assert validation["status"] == "failed"
    assert validation["differing_top_level_keys"] == ["derived_gates"]
