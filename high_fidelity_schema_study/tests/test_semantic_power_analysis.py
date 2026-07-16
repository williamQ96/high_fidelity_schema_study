from __future__ import annotations

import copy
import hashlib

import pytest

from high_fidelity_schema_study.semantic_power_analysis import (
    PowerAnalysisError,
    build_power_analysis,
    required_paired_sample_size,
    required_total_dataset_count,
    validate_power_analysis,
    verify_calibration_sources,
)


HASH = "a" * 64


def power_config() -> dict:
    return {
        "schema_version": "semantic-power-analysis-config/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "status": "frozen",
        "calibration_manifest_file": "calibration-manifest.json",
        "calibration_manifest_sha256": HASH,
        "calibration_statistics_file": "calibration-statistics.json",
        "calibration_statistics_sha256": "b" * 64,
        "sd_estimation_method": (
            "sample SD of equal-weight calibration dataset-level paired rate effects"
        ),
        "planning_rationale": (
            "inflate calibration SDs by 25 percent and report lower/base/planning scenarios"
        ),
        "primary_contrasts": ["A_vs_B", "B_vs_C"],
        "minimum_meaningful_effect": 0.1,
        "familywise_alpha": 0.05,
        "target_power": 0.8,
        "selective_risk_bound": 0.05,
        "paired_difference_sd_by_contrast": {
            "A_vs_B": 0.2,
            "B_vs_C": 0.25,
        },
        "planning_sd_inflation": 1.25,
        "semantic_opportunity_rate": 0.8,
        "noncomparability_rate": 0.05,
        "opportunity_count_assurance": 0.9,
        "minimum_total_dataset_count": 2,
        "sensitivity_sd_multipliers": [0.75, 1.0, 1.25],
    }


def test_power_artifact_is_deterministic_and_self_validating() -> None:
    first = build_power_analysis(power_config())
    second = build_power_analysis(power_config())

    assert first == second
    assert first["schema_version"] == "semantic-power-analysis/v2"
    assert first["primary_contrasts"] == ["A_vs_B", "B_vs_C"]
    assert first["alpha_per_contrast_for_planning"] == 0.025
    assert validate_power_analysis(first)["status"] == "ready"


def test_planning_uses_worst_required_co_primary_contrast() -> None:
    report = build_power_analysis(power_config())
    contrast_counts = [
        item["required_opportunity_dataset_count"]
        for item in report["calculation"]["contrasts"].values()
    ]

    assert report["assumptions"]["required_semantic_opportunity_case_count"] == max(
        contrast_counts
    )
    assert (
        report["assumptions"]["required_dataset_count"]
        >= report["assumptions"]["required_semantic_opportunity_case_count"]
    )
    assert (
        report["calculation"]["probability_of_at_least_required_opportunities"] >= 0.9
    )


def test_multiplicity_planning_is_more_conservative_than_unadjusted_test() -> None:
    adjusted = required_paired_sample_size(
        minimum_effect=0.1,
        paired_difference_sd=0.25,
        alpha=0.025,
        target_power=0.8,
    )
    unadjusted = required_paired_sample_size(
        minimum_effect=0.1,
        paired_difference_sd=0.25,
        alpha=0.05,
        target_power=0.8,
    )

    assert adjusted > unadjusted


def test_dataset_inflation_uses_probability_assurance_not_expected_value() -> None:
    count = required_total_dataset_count(
        required_opportunity_count=20,
        effective_scorable_rate=0.5,
        assurance=0.95,
        minimum_total_dataset_count=2,
    )

    assert count > 40


def test_tampered_calculation_fails_recomputation() -> None:
    report = build_power_analysis(power_config())
    tampered = copy.deepcopy(report)
    tampered["assumptions"]["required_dataset_count"] += 1

    validation = validate_power_analysis(tampered)

    assert validation["status"] == "blocked"
    assert validation["errors"][0]["code"] == ("power_analysis_recalculation_mismatch")


def test_primary_contrast_set_cannot_be_changed() -> None:
    config = power_config()
    config["primary_contrasts"] = ["A_vs_B"]

    with pytest.raises(PowerAnalysisError, match="primary_contrasts"):
        build_power_analysis(config)


def test_source_files_must_exist_and_match_their_hashes(tmp_path) -> None:
    manifest = tmp_path / "calibration-manifest.json"
    statistics = tmp_path / "calibration-statistics.json"
    manifest.write_text("{}\n", encoding="utf-8")
    statistics.write_text("[]\n", encoding="utf-8")
    config = power_config()
    config["calibration_manifest_sha256"] = hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest()
    config["calibration_statistics_sha256"] = hashlib.sha256(
        statistics.read_bytes()
    ).hexdigest()
    owner = tmp_path / "power.json"

    with pytest.raises(PowerAnalysisError, match="not reproducible"):
        verify_calibration_sources(config, owner=owner)
    statistics.write_text("[1]\n", encoding="utf-8")

    with pytest.raises(PowerAnalysisError, match="hash mismatch"):
        verify_calibration_sources(config, owner=owner)
