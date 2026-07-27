from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_cpa_design import (
    registered_analysis_contract,
    registered_metric_contract,
)
from high_fidelity_schema_study.ndp50_power_freeze import (
    NDPPowerFreezeError,
    build_freeze,
    build_policy_template,
    build_workflow_spec,
    validate_policy,
    verify_freeze,
)


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(path: Path, root: Path) -> dict[str, str]:
    return {
        "file": path.relative_to(root).as_posix(),
        "sha256": _sha(path),
    }


def _fixture(tmp_path: Path) -> dict:
    root = tmp_path / "ndp50"
    selection_path = root / "selection.json"
    selected = [
        *[
            {"dataset_id": f"dev-{index}", "split": "development"}
            for index in range(1, 16)
        ],
        *[
            {"dataset_id": f"val-{index}", "split": "validation"}
            for index in range(1, 11)
        ],
        *[
            {"dataset_id": f"sealed-{index}", "split": "test"}
            for index in range(1, 26)
        ],
    ]
    _write(
        selection_path,
        {
            "counts": {
                "selected_dataset_count": 50,
                "split_counts": {
                    "development": 15,
                    "validation": 10,
                    "test": 25,
                },
            },
            "selected_datasets": selected,
        },
    )
    opportunity_path = root / "semantic" / "opportunities.json"
    opportunity_cases = [
        *[
            {
                "case_id": f"case-dev-{index}",
                "dataset_id": f"dev-{index}",
                "split": "development",
            }
            for index in range(1, 5)
        ],
        {
            "case_id": "case-val-1",
            "dataset_id": "val-1",
            "split": "validation",
        },
    ]
    _write(
        opportunity_path,
        {
            "schema_version": "ndp50-semantic-opportunity-manifest/v1",
            "cases": opportunity_cases,
        },
    )
    design_path = root / "semantic" / "cpa-design.json"
    _write(
        design_path,
        {
            "schema_version": "ndp50-cpa-design/v1",
            "analysis": registered_analysis_contract(),
            "metric_contract": registered_metric_contract(),
        },
    )
    execution_path = root / "semantic" / "execution-freeze.json"
    contrasts = [
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
    _write(
        execution_path,
        {
            "schema_version": "ndp50-execution-freeze/v1",
            "status": "frozen_ready_for_power_calibration",
            "derived_gates": {"prompt_and_backend_frozen": True},
            "config": {
                "planned_arms": [
                    "deterministic_only",
                    "zero_shot_dataset_level",
                    (
                        "zero_shot_byte_identical_response_plus_"
                        "deterministic_verification"
                    ),
                ],
                "analysis_contract": {"primary_contrasts": contrasts},
            },
        },
    )
    template_path = root / "semantic" / "power-policy-neutral.json"
    template = build_policy_template(
        selection_path=selection_path,
        opportunity_manifest_path=opportunity_path,
        cpa_design_path=design_path,
        study_root=root,
    )
    _write(template_path, template)
    policy_path = root / "semantic" / "power-policy.json"
    policy = copy.deepcopy(template)
    policy.update(
        {
            "status": "completed_precalibration_policy",
            "human_decisions_present": True,
            "execution_freeze": _ref(execution_path, root),
            "primary_contrasts": contrasts,
            "minimum_meaningful_effect": 0.1,
            "minimum_meaningful_effect_rationale": (
                "A ten percentage-point dataset-level gain is the minimum "
                "effect that justifies added semantic-model complexity."
            ),
            "target_power": 0.8,
            "selective_risk_bound": 0.05,
            "planning_sd_inflation": 1.25,
            "sd_floor": 0.05,
            "opportunity_count_assurance": 0.9,
            "sensitivity_sd_multipliers": [0.75, 1.0, 1.25],
            "signoffs": [
                {
                    "slot": "study_operator",
                    "signatory_id": "operator-1",
                    "role": "principal_investigator",
                    "institution": "Example Laboratory",
                    "qualification_summary": "Leads the registered study.",
                    "conflict_of_interest_declared": False,
                    "developer_participation": True,
                    "signed_on": "2026-07-26",
                },
                {
                    "slot": "independent_methods_reviewer",
                    "signatory_id": "reviewer-1",
                    "role": "statistical_methods_reviewer",
                    "institution": "Example University",
                    "qualification_summary": (
                        "Reviews multiplicity and power methods."
                    ),
                    "conflict_of_interest_declared": False,
                    "developer_participation": False,
                    "signed_on": "2026-07-26",
                },
            ],
            "completion_attestation": True,
        }
    )
    _write(policy_path, policy)
    report_path = root / "semantic" / "development-calibration.json"
    effects = [0.05, 0.1, 0.15, 0.2]
    report_contrasts = []
    for contrast_index, contrast in enumerate(contrasts):
        report_contrasts.append(
            {
                **contrast,
                "datasets": [
                    {
                        "dataset_id": f"dev-{index}",
                        "status": "comparable",
                        "paired_rate_effect": (
                            effect
                            if contrast_index == 0
                            else effect - 0.02
                        ),
                        "reasons": [],
                    }
                    for index, effect in enumerate(effects, start=1)
                ],
            }
        )
    _write(
        report_path,
        {
            "schema_version": "ndp50-development-calibration-report/v1",
            "status": "completed_development_only_calibration",
            "source_split": "development",
            "validation_outcomes_used": False,
            "test_outcomes_used": False,
            "gold_used_for_scoring": True,
            "primary_statistical_unit": "dataset",
            "execution_freeze": _ref(execution_path, root),
            "power_policy": _ref(policy_path, root),
            "contrasts": report_contrasts,
        },
    )
    return {
        "root": root,
        "study_root": root,
        "selection_path": selection_path,
        "opportunity_manifest_path": opportunity_path,
        "cpa_design_path": design_path,
        "execution_freeze_path": execution_path,
        "template_path": template_path,
        "policy_path": policy_path,
        "policy": policy,
        "calibration_report_path": report_path,
    }


def test_neutral_policy_and_workflow_do_not_claim_power_freeze(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    template = json.loads(
        inputs["template_path"].read_text(encoding="utf-8")
    )
    workflow = build_workflow_spec(
        selection_path=inputs["selection_path"],
        opportunity_manifest_path=inputs["opportunity_manifest_path"],
        cpa_design_path=inputs["cpa_design_path"],
        policy_template_path=inputs["template_path"],
        study_root=inputs["study_root"],
    )
    assert template["human_decisions_present"] is False
    assert template["minimum_meaningful_effect"] is None
    assert template["primary_contrasts"] == registered_analysis_contract()[
        "primary_contrasts"
    ]
    assert workflow["test_outcomes_observed"] is False
    assert workflow["validation_or_test_outcomes_forbidden"] is True


def test_policy_rejects_execution_contrast_substitution(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    execution = json.loads(
        inputs["execution_freeze_path"].read_text(encoding="utf-8")
    )
    execution["config"]["analysis_contract"]["primary_contrasts"][0][
        "arm_b"
    ] = (
        "zero_shot_byte_identical_response_plus_"
        "deterministic_verification"
    )
    _write(inputs["execution_freeze_path"], execution)
    policy = copy.deepcopy(inputs["policy"])
    policy["execution_freeze"] = _ref(
        inputs["execution_freeze_path"], inputs["study_root"]
    )
    policy["primary_contrasts"] = execution["config"][
        "analysis_contract"
    ]["primary_contrasts"]

    validation = validate_policy(
        policy,
        selection_path=inputs["selection_path"],
        opportunity_manifest_path=inputs["opportunity_manifest_path"],
        cpa_design_path=inputs["cpa_design_path"],
        execution_freeze_path=inputs["execution_freeze_path"],
        study_root=inputs["study_root"],
    )

    assert "execution_primary_contrasts_changed" in {
        item["code"] for item in validation["errors"]
    }


def test_valid_policy_replays_registered_execution_contrasts(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    policy_validation = validate_policy(
        inputs["policy"],
        selection_path=inputs["selection_path"],
        opportunity_manifest_path=inputs["opportunity_manifest_path"],
        cpa_design_path=inputs["cpa_design_path"],
        execution_freeze_path=inputs["execution_freeze_path"],
        study_root=inputs["study_root"],
    )
    frozen = build_freeze(
        policy=inputs["policy"],
        policy_path=inputs["policy_path"],
        calibration_report_path=inputs["calibration_report_path"],
        selection_path=inputs["selection_path"],
        opportunity_manifest_path=inputs["opportunity_manifest_path"],
        cpa_design_path=inputs["cpa_design_path"],
        execution_freeze_path=inputs["execution_freeze_path"],
        study_root=inputs["study_root"],
    )
    replay = verify_freeze(
        frozen,
        policy_path=inputs["policy_path"],
        calibration_report_path=inputs["calibration_report_path"],
        selection_path=inputs["selection_path"],
        opportunity_manifest_path=inputs["opportunity_manifest_path"],
        cpa_design_path=inputs["cpa_design_path"],
        execution_freeze_path=inputs["execution_freeze_path"],
        study_root=inputs["study_root"],
    )
    assert policy_validation["status"] == "passed"
    assert frozen["derived_gates"]["test_power_plan_frozen"] is True
    assert set(
        frozen["development_calibration_statistics"]["contrasts"]
    ) == {"deterministic-vs-zero", "zero-vs-verified"}
    assert replay["status"] == "passed"


def test_policy_rejects_calibration_outcome_peeking(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    policy = copy.deepcopy(inputs["policy"])
    policy[
        "calibration_outcomes_observed_before_policy_signoff"
    ] = True
    validation = validate_policy(
        policy,
        selection_path=inputs["selection_path"],
        opportunity_manifest_path=inputs["opportunity_manifest_path"],
        cpa_design_path=inputs["cpa_design_path"],
        execution_freeze_path=inputs["execution_freeze_path"],
        study_root=inputs["study_root"],
    )
    assert "calibration_timing_violated" in {
        item["code"] for item in validation["errors"]
    }


def test_calibration_rejects_validation_dataset(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    report = json.loads(
        inputs["calibration_report_path"].read_text(encoding="utf-8")
    )
    report["contrasts"][0]["datasets"][0]["dataset_id"] = "val-1"
    _write(inputs["calibration_report_path"], report)
    with pytest.raises(
        NDPPowerFreezeError,
        match="every development opportunity dataset",
    ):
        build_freeze(
            policy=inputs["policy"],
            policy_path=inputs["policy_path"],
            calibration_report_path=inputs["calibration_report_path"],
            selection_path=inputs["selection_path"],
            opportunity_manifest_path=inputs["opportunity_manifest_path"],
            cpa_design_path=inputs["cpa_design_path"],
            execution_freeze_path=inputs["execution_freeze_path"],
            study_root=inputs["study_root"],
        )


def test_opened_test_details_block_power_freeze(tmp_path: Path) -> None:
    inputs = _fixture(tmp_path)
    detail = (
        inputs["study_root"]
        / "acquisition"
        / "test_details"
        / "opened.json.gz"
    )
    detail.parent.mkdir(parents=True)
    detail.write_bytes(b"opened")
    with pytest.raises(NDPPowerFreezeError, match="unopened"):
        build_freeze(
            policy=inputs["policy"],
            policy_path=inputs["policy_path"],
            calibration_report_path=inputs["calibration_report_path"],
            selection_path=inputs["selection_path"],
            opportunity_manifest_path=inputs["opportunity_manifest_path"],
            cpa_design_path=inputs["cpa_design_path"],
            execution_freeze_path=inputs["execution_freeze_path"],
            study_root=inputs["study_root"],
        )


def test_tampered_power_calculation_fails_replay(
    tmp_path: Path,
) -> None:
    inputs = _fixture(tmp_path)
    frozen = build_freeze(
        policy=inputs["policy"],
        policy_path=inputs["policy_path"],
        calibration_report_path=inputs["calibration_report_path"],
        selection_path=inputs["selection_path"],
        opportunity_manifest_path=inputs["opportunity_manifest_path"],
        cpa_design_path=inputs["cpa_design_path"],
        execution_freeze_path=inputs["execution_freeze_path"],
        study_root=inputs["study_root"],
    )
    frozen["power_calculation"]["target_power"] = 0.9
    replay = verify_freeze(
        frozen,
        policy_path=inputs["policy_path"],
        calibration_report_path=inputs["calibration_report_path"],
        selection_path=inputs["selection_path"],
        opportunity_manifest_path=inputs["opportunity_manifest_path"],
        cpa_design_path=inputs["cpa_design_path"],
        execution_freeze_path=inputs["execution_freeze_path"],
        study_root=inputs["study_root"],
    )
    assert replay["status"] == "failed"
    assert replay["differing_top_level_keys"] == ["power_calculation"]
