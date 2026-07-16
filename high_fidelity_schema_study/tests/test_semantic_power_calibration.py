from __future__ import annotations

import copy

import pytest

from high_fidelity_schema_study.semantic_power_calibration import (
    CalibrationStatisticsError,
    build_calibration_statistics,
    build_calibration_statistics_from_paths,
    sha256_file,
    validate_calibration_statistics_file,
    write_json,
)


def calibration_manifest() -> dict:
    return {
        "schema_version": "minimal-architecture-manifest/v1",
        "cases": [{"case_id": "cal-1"}, {"case_id": "cal-2"}],
    }


def evaluation_report() -> dict:
    def comparison(effects: list[float]) -> dict:
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

    return {
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
                    "A_vs_B": comparison([0.1, 0.3]),
                    "B_vs_C": comparison([-0.1, 0.1]),
                }
            }
        },
    }


def test_builds_equal_weight_dataset_level_calibration_statistics(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "report.json"
    output_path = tmp_path / "statistics.json"
    write_json(manifest_path, calibration_manifest())
    write_json(report_path, evaluation_report())

    payload = build_calibration_statistics_from_paths(
        evaluation_report_path=report_path,
        calibration_manifest_path=manifest_path,
        output_path=output_path,
    )
    write_json(output_path, payload)

    assert payload["semantic_opportunity_rate"] == 1.0
    assert payload["contrasts"]["A_vs_B"]["mean_paired_rate_effect"] == 0.2
    assert payload["contrasts"]["A_vs_B"][
        "sample_sd_paired_rate_effect"
    ] == pytest.approx(0.14142136)
    assert validate_calibration_statistics_file(output_path)["status"] == "ready"


def test_blind_outcomes_cannot_enter_power_calibration() -> None:
    report = evaluation_report()
    report["benchmark_roles"] = ["blind_external"]

    with pytest.raises(CalibrationStatisticsError, match="blind_external"):
        build_calibration_statistics(
            evaluation_report=report,
            evaluation_report_file="report.json",
            evaluation_report_sha256="a" * 64,
            calibration_manifest=calibration_manifest(),
            calibration_manifest_file="manifest.json",
            calibration_manifest_sha256="b" * 64,
        )


def test_invalid_replay_cannot_contribute_variance_estimate() -> None:
    report = evaluation_report()
    report["execution_control"]["b_c_replay_provenance"][0]["valid"] = False

    with pytest.raises(CalibrationStatisticsError, match="replay"):
        build_calibration_statistics(
            evaluation_report=report,
            evaluation_report_file="report.json",
            evaluation_report_sha256="a" * 64,
            calibration_manifest=calibration_manifest(),
            calibration_manifest_file="manifest.json",
            calibration_manifest_sha256="b" * 64,
        )


def test_manifest_and_report_case_order_must_match() -> None:
    manifest = calibration_manifest()
    manifest["cases"].reverse()

    with pytest.raises(CalibrationStatisticsError, match="order/identity"):
        build_calibration_statistics(
            evaluation_report=evaluation_report(),
            evaluation_report_file="report.json",
            evaluation_report_sha256="a" * 64,
            calibration_manifest=manifest,
            calibration_manifest_file="manifest.json",
            calibration_manifest_sha256="b" * 64,
        )


def test_tampered_statistics_fail_recalculation(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "report.json"
    output_path = tmp_path / "statistics.json"
    write_json(manifest_path, calibration_manifest())
    write_json(report_path, evaluation_report())
    payload = build_calibration_statistics_from_paths(
        evaluation_report_path=report_path,
        calibration_manifest_path=manifest_path,
        output_path=output_path,
    )
    tampered = copy.deepcopy(payload)
    tampered["recommended_power_inputs"]["semantic_opportunity_rate"] = 0.5
    write_json(output_path, tampered)

    validation = validate_calibration_statistics_file(output_path)

    assert validation["status"] == "blocked"
    assert validation["errors"][0]["code"] == (
        "power_calibration_statistics_recalculation_mismatch"
    )


def test_source_hash_change_invalidates_statistics(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    report_path = tmp_path / "report.json"
    output_path = tmp_path / "statistics.json"
    write_json(manifest_path, calibration_manifest())
    write_json(report_path, evaluation_report())
    payload = build_calibration_statistics_from_paths(
        evaluation_report_path=report_path,
        calibration_manifest_path=manifest_path,
        output_path=output_path,
    )
    write_json(output_path, payload)
    report_path.write_text("{}\n", encoding="utf-8")

    validation = validate_calibration_statistics_file(output_path)

    assert validation["status"] == "blocked"
    assert "hash mismatch" in validation["errors"][0]["detail"]
    assert (
        sha256_file(report_path)
        != payload["source_artifacts"]["evaluation_report"]["sha256"]
    )
