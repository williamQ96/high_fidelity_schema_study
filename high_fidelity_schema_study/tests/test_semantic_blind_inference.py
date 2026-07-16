from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.semantic_blind_inference import (
    BlindInferenceError,
    _canonical_json_hash,
    bootstrap_mean_interval,
    build_analysis_plan,
    build_inference_artifact,
    holm_adjust,
    paired_t_inference,
    sha256_file,
    sign_flip_test,
    validate_analysis_plan,
    validate_inference_artifact,
)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def comparison(effects: list[float | None]) -> dict:
    rows = []
    for index, effect in enumerate(effects, start=1):
        comparable = effect is not None
        rows.append(
            {
                "case_id": f"case-{index}",
                "status": "comparable" if comparable else "not_comparable",
                "reasons": [] if comparable else ["partial_model_failure"],
                "correct_accepted_claim_rate_gain": effect,
                "correct_accepted_claim_gain": effect,
                "coverage_delta": effect,
                "selective_risk_delta": -effect if effect is not None else None,
                "unsupported_accepted_model_claim_delta": 0 if comparable else None,
            }
        )
    return {
        "status": "comparable"
        if all(item is not None for item in effects)
        else "not_comparable",
        "direction": "right minus left",
        "cases": rows,
    }


def blind_report(
    backend: dict, registry_sha256: str, effects: list[float | None]
) -> dict:
    case_ids = [f"case-{index}" for index in range(1, len(effects) + 1)]
    return {
        "schema_version": "minimal-architecture-experiment/v3-blind",
        "benchmark_roles": ["blind_external"],
        "case_design": [
            {
                "case_id": case_id,
                "dataset_reasoning_opportunity": True,
            }
            for case_id in case_ids
        ],
        "variant_summaries": {key: {} for key in "ABCD"},
        "execution_control": {
            "backend_identity": {
                "model_identifier": backend["model_identifier"],
                "backend_registry_sha256": registry_sha256,
                "registered_backend_id": backend["backend_id"],
                "registered_backend_role": backend["role"],
                "registered_backend_record_sha256": _canonical_json_hash(backend),
                "registered_checkpoint_sha256": backend.get("checkpoint_sha256"),
            },
            "b_c_replay_provenance": [
                {
                    "case_id": case_id,
                    "valid": True,
                    "c_semantic_generation_calls": 0,
                }
                for case_id in case_ids
            ],
        },
        "predefined_analysis_strata": {
            "dataset_reasoning_opportunity": {
                "dataset_level_comparison": {
                    "A_vs_B": comparison(effects),
                    "B_vs_C": comparison(
                        [value / 2 if value is not None else None for value in effects]
                    ),
                    "C_vs_D": comparison(
                        [0.0 if value is not None else None for value in effects]
                    ),
                }
            }
        },
    }


def build_fixture(tmp_path: Path, *, required_count: int = 2) -> tuple[Path, Path]:
    backend_ids = ("primary", "sensitivity")
    registry_path = tmp_path / "backends.json"
    power_path = tmp_path / "power.json"
    plan_path = tmp_path / "plan.json"
    blind_path = tmp_path / "blind.json"
    run_path = tmp_path / "run.json"
    backend_records = [
        {
            "backend_id": backend_id,
            "role": "primary" if backend_id == "primary" else "sensitivity",
            "model_family": "Qwen" if backend_id == "primary" else "Llama",
            "model_identifier": f"model-{backend_id}",
        }
        for backend_id in backend_ids
    ]
    registry = {
        "schema_version": "semantic-backend-registry/v1",
        "primary_backend_id": "primary",
        "backends": backend_records,
    }
    write_json(registry_path, registry)
    power = {
        "schema_version": "semantic-power-analysis/v2",
        "status": "frozen",
        "primary_contrasts": ["A_vs_B", "B_vs_C"],
        "alpha": 0.05,
        "assumptions": {
            "required_semantic_opportunity_case_count": required_count,
        },
    }
    write_json(power_path, power)
    plan = build_analysis_plan(
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
    write_json(plan_path, plan)
    blind = {
        "schema_version": "minimal-architecture-manifest/v2",
        "benchmark_role": "blind_external",
        "backend_registry_sha256": sha256_file(registry_path),
        "design": {
            "power_analysis_sha256": sha256_file(power_path),
            "analysis_plan_sha256": sha256_file(plan_path),
        },
        "cases": [{"case_id": "case-1"}, {"case_id": "case-2"}],
    }
    write_json(blind_path, blind)
    report_sources = []
    for backend_id in backend_ids:
        report_path = tmp_path / f"report-{backend_id}.json"
        backend_record = next(
            item for item in backend_records if item["backend_id"] == backend_id
        )
        write_json(
            report_path,
            blind_report(backend_record, sha256_file(registry_path), [0.2, 0.4]),
        )
        report_sources.append(
            {
                "backend_id": backend_id,
                "report_file": report_path.name,
                "report_sha256": sha256_file(report_path),
            }
        )
    run = {
        "schema_version": "semantic-blind-analysis-run/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "status": "complete",
        "analysis_plan_file": plan_path.name,
        "analysis_plan_sha256": sha256_file(plan_path),
        "blind_manifest_file": blind_path.name,
        "blind_manifest_sha256": sha256_file(blind_path),
        "evaluation_reports": report_sources,
    }
    write_json(run_path, run)
    return run_path, tmp_path / "inference.json"


def test_analysis_plan_is_recalculable_and_tamper_evident(tmp_path: Path) -> None:
    run_path, _ = build_fixture(tmp_path)
    run = json.loads(run_path.read_text(encoding="utf-8"))
    plan_path = tmp_path / run["analysis_plan_file"]
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    assert validate_analysis_plan(plan)["status"] == "ready"
    plan["multiplicity"]["familywise_alpha"] = 0.1
    assert validate_analysis_plan(plan)["status"] == "blocked"


def test_statistical_functions_preserve_dataset_unit_and_randomness() -> None:
    t_result = paired_t_inference([0.1, 0.2, 0.3], 0.95)
    assert t_result["n"] == 3
    assert t_result["mean"] == 0.2
    assert t_result["two_sided_p_value"] < 0.1

    exact = sign_flip_test(
        [1.0, 1.0], exact_max_n=20, monte_carlo_repetitions=100, seed=1
    )
    assert exact["method"] == "exact"
    assert exact["two_sided_p_value"] == 0.5

    first = bootstrap_mean_interval(
        [0.1, 0.2, 0.3], confidence_level=0.95, repetitions=1000, seed=7
    )
    second = bootstrap_mean_interval(
        [0.1, 0.2, 0.3], confidence_level=0.95, repetitions=1000, seed=7
    )
    assert first == second
    assert holm_adjust({"A_vs_B": 0.01, "B_vs_C": 0.04}) == {
        "A_vs_B": {
            "raw_p_value": 0.01,
            "holm_rank": 1,
            "holm_adjusted_p_value": 0.02,
        },
        "B_vs_C": {
            "raw_p_value": 0.04,
            "holm_rank": 2,
            "holm_adjusted_p_value": 0.04,
        },
    }


def test_blind_inference_rebuilds_exactly(tmp_path: Path) -> None:
    run_path, output_path = build_fixture(tmp_path)
    artifact = build_inference_artifact(
        run_manifest=json.loads(run_path.read_text(encoding="utf-8")),
        run_manifest_path=run_path,
        output_path=output_path,
    )
    write_json(output_path, artifact)

    assert artifact["confirmatory_status"] == "complete_as_planned"
    assert set(artifact["primary_backend_holm"]["contrasts"]) == {
        "A_vs_B",
        "B_vs_C",
    }
    assert validate_inference_artifact(output_path)["status"] == "ready"

    tampered = copy.deepcopy(artifact)
    tampered["backend_results"]["primary"]["contrasts"]["A_vs_B"]["effect_summary"][
        "mean"
    ] = 0.99
    write_json(output_path, tampered)
    assert validate_inference_artifact(output_path)["status"] == "blocked"


def test_underpowered_observed_count_is_reported_without_adding_cases(
    tmp_path: Path,
) -> None:
    run_path, output_path = build_fixture(tmp_path, required_count=3)
    artifact = build_inference_artifact(
        run_manifest=json.loads(run_path.read_text(encoding="utf-8")),
        run_manifest_path=run_path,
        output_path=output_path,
    )

    assert (
        artifact["confirmatory_status"]
        == "underpowered_observed_opportunity_or_comparability"
    )
    assert not artifact["backend_results"]["primary"]["contrasts"]["A_vs_B"][
        "planned_power_count_met"
    ]


def test_development_report_cannot_cross_blind_boundary(tmp_path: Path) -> None:
    run_path, output_path = build_fixture(tmp_path)
    run = json.loads(run_path.read_text(encoding="utf-8"))
    report_source = run["evaluation_reports"][0]
    report_path = tmp_path / report_source["report_file"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["schema_version"] = "minimal-architecture-experiment/v3-development"
    write_json(report_path, report)
    report_source["report_sha256"] = sha256_file(report_path)
    write_json(run_path, run)

    with pytest.raises(BlindInferenceError, match="v3-blind"):
        build_inference_artifact(
            run_manifest=run,
            run_manifest_path=run_path,
            output_path=output_path,
        )


def test_backend_identity_mismatch_is_not_pooled(tmp_path: Path) -> None:
    run_path, output_path = build_fixture(tmp_path)
    run = json.loads(run_path.read_text(encoding="utf-8"))
    report_source = run["evaluation_reports"][0]
    report_path = tmp_path / report_source["report_file"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["execution_control"]["backend_identity"]["model_identifier"] = "wrong"
    write_json(report_path, report)
    report_source["report_sha256"] = sha256_file(report_path)
    write_json(run_path, run)

    with pytest.raises(BlindInferenceError, match="model identifier"):
        build_inference_artifact(
            run_manifest=run,
            run_manifest_path=run_path,
            output_path=output_path,
        )


def test_registered_backend_record_mismatch_blocks_inference(tmp_path: Path) -> None:
    run_path, output_path = build_fixture(tmp_path)
    run = json.loads(run_path.read_text(encoding="utf-8"))
    report_source = run["evaluation_reports"][0]
    report_path = tmp_path / report_source["report_file"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["execution_control"]["backend_identity"][
        "registered_backend_record_sha256"
    ] = "0" * 64
    write_json(report_path, report)
    report_source["report_sha256"] = sha256_file(report_path)
    write_json(run_path, run)

    with pytest.raises(BlindInferenceError, match="backend record"):
        build_inference_artifact(
            run_manifest=run,
            run_manifest_path=run_path,
            output_path=output_path,
        )


def test_partial_d_makes_c_vs_d_non_comparable_without_affecting_primaries(
    tmp_path: Path,
) -> None:
    run_path, output_path = build_fixture(tmp_path)
    run = json.loads(run_path.read_text(encoding="utf-8"))
    report_source = run["evaluation_reports"][0]
    report_path = tmp_path / report_source["report_file"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["predefined_analysis_strata"]["dataset_reasoning_opportunity"][
        "dataset_level_comparison"
    ]["C_vs_D"] = comparison([0.0, None])
    write_json(report_path, report)
    report_source["report_sha256"] = sha256_file(report_path)
    write_json(run_path, run)

    artifact = build_inference_artifact(
        run_manifest=run,
        run_manifest_path=run_path,
        output_path=output_path,
    )

    primary = artifact["backend_results"]["primary"]["contrasts"]
    assert primary["A_vs_B"]["status"] == "analyzable"
    assert primary["C_vs_D"]["status"] == "not_comparable"
    assert primary["C_vs_D"]["paired_t"]["status"] == "insufficient_data"


def test_missing_opportunity_row_cannot_silently_reduce_analysis_set(
    tmp_path: Path,
) -> None:
    run_path, output_path = build_fixture(tmp_path)
    run = json.loads(run_path.read_text(encoding="utf-8"))
    report_source = run["evaluation_reports"][0]
    report_path = tmp_path / report_source["report_file"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rows = report["predefined_analysis_strata"]["dataset_reasoning_opportunity"][
        "dataset_level_comparison"
    ]["A_vs_B"]["cases"]
    rows.pop()
    write_json(report_path, report)
    report_source["report_sha256"] = sha256_file(report_path)
    write_json(run_path, run)

    with pytest.raises(BlindInferenceError, match="every semantic-opportunity case"):
        build_inference_artifact(
            run_manifest=run,
            run_manifest_path=run_path,
            output_path=output_path,
        )
