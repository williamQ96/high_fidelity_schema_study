from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_power_feasibility import (
    NDPPowerFeasibilityError,
    best_case_all_success_clopper_pearson_lower,
    build_feasibility_report,
    minimum_nonzero_pairs_for_resolution,
    minimum_two_sided_sign_flip_p,
    validate_feasibility_report,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    cases = []
    for index in range(2):
        cases.append(
            {
                "case_id": f"development-{index}",
                "dataset_id": f"d{index}",
                "split": "development",
                "cpa_applicability_status": (
                    "requires_manual_relation_and_subject_assessment"
                    if index == 0
                    else "not_applicable_non_tabular_format"
                ),
            }
        )
    for index in range(5):
        cases.append(
            {
                "case_id": f"validation-{index}",
                "dataset_id": f"v{index}",
                "split": "validation",
                "cpa_applicability_status": (
                    "requires_manual_relation_and_subject_assessment"
                    if index < 3
                    else "not_applicable_non_tabular_format"
                ),
            }
        )
    opportunity = tmp_path / "opportunity.json"
    _write(
        opportunity,
        {
            "schema_version": "ndp50-semantic-opportunity-manifest/v1",
            "counts": {
                "case_count": 7,
                "dataset_cluster_count": 7,
                "split_case_counts": {
                    "development": 2,
                    "validation": 5,
                },
            },
            "cases": cases,
        },
    )
    selection = tmp_path / "selection.json"
    _write(
        selection,
        {
            "counts": {
                "selected_dataset_count": 50,
                "split_counts": {
                    "development": 15,
                    "validation": 10,
                    "test": 25,
                },
            },
            "selected_datasets": [
                *[
                    {"dataset_id": f"d{i}", "split": "development"}
                    for i in range(15)
                ],
                *[
                    {"dataset_id": f"v{i}", "split": "validation"}
                    for i in range(10)
                ],
                *[
                    {"dataset_id": f"t{i}", "split": "test"}
                    for i in range(25)
                ],
            ]
        },
    )
    cpa_design = tmp_path / "cpa.json"
    _write(
        cpa_design,
        {
            "schema_version": "ndp50-cpa-design/v1",
            "candidate_counts": {
                "resource_cases": 4,
                "dataset_clusters": 4,
                "split_case_counts": {
                    "development": 1,
                    "validation": 3,
                },
            }
        },
    )
    study_root = tmp_path / "study"
    return opportunity, selection, cpa_design, study_root


def test_exact_resolution_floor_is_assumption_free() -> None:
    assert minimum_two_sided_sign_flip_p(5) == 0.0625
    assert minimum_two_sided_sign_flip_p(3) == 0.25
    assert minimum_nonzero_pairs_for_resolution(0.025) == 7
    assert best_case_all_success_clopper_pearson_lower(
        5, confidence_level=0.95
    ) == pytest.approx(0.4781762499)


def test_validation_is_explicitly_limited_to_descriptive_pilot(
    tmp_path: Path,
) -> None:
    opportunity, selection, cpa_design, study_root = _inputs(tmp_path)

    report = build_feasibility_report(
        opportunity_manifest_path=opportunity,
        selection_path=selection,
        cpa_design_path=cpa_design,
        study_root=study_root,
    )

    assert report["semantic_opportunity_counts"]["validation"][
        "dataset_cluster_count"
    ] == 5
    assert report["cpa_candidate_counts"]["validation"][
        "dataset_cluster_count"
    ] == 3
    assert report["validation_claim_scope"]["general_semantic"] == (
        "descriptive_feasibility_pilot_only"
    )
    assert report["gates"]["validation_confirmatory_power_established"] is False
    assert report["gates"]["test_power_plan_frozen"] is False


def test_pretest_report_rejects_test_identity_or_opened_details(
    tmp_path: Path,
) -> None:
    opportunity, selection, cpa_design, study_root = _inputs(tmp_path)
    payload = json.loads(opportunity.read_text(encoding="utf-8"))
    payload["cases"][0]["split"] = "test"
    _write(opportunity, payload)

    with pytest.raises(NDPPowerFeasibilityError, match="test identities"):
        build_feasibility_report(
            opportunity_manifest_path=opportunity,
            selection_path=selection,
            cpa_design_path=cpa_design,
            study_root=study_root,
        )

    opportunity, selection, cpa_design, study_root = _inputs(
        tmp_path / "opened"
    )
    detail = study_root / "acquisition" / "test_details" / "test.json.gz"
    detail.parent.mkdir(parents=True)
    detail.write_bytes(b"opened")
    with pytest.raises(NDPPowerFeasibilityError, match="unopened"):
        build_feasibility_report(
            opportunity_manifest_path=opportunity,
            selection_path=selection,
            cpa_design_path=cpa_design,
            study_root=study_root,
        )


def test_feasibility_artifact_is_exactly_recomputed(tmp_path: Path) -> None:
    opportunity, selection, cpa_design, study_root = _inputs(tmp_path)
    report = build_feasibility_report(
        opportunity_manifest_path=opportunity,
        selection_path=selection,
        cpa_design_path=cpa_design,
        study_root=study_root,
    )
    report["validation_claim_scope"][
        "confirmatory_superiority_claim_allowed"
    ] = True

    validation = validate_feasibility_report(
        report,
        opportunity_manifest_path=opportunity,
        selection_path=selection,
        cpa_design_path=cpa_design,
        study_root=study_root,
    )

    assert validation["status"] == "failed"
    assert validation["differing_top_level_keys"] == [
        "validation_claim_scope"
    ]


def test_ndp_power_freeze_is_bound_without_exposing_test_identity(
    tmp_path: Path,
) -> None:
    opportunity, selection, cpa_design, study_root = _inputs(tmp_path)
    power_freeze = tmp_path / "power-freeze.json"
    _write(
        power_freeze,
        {
            "schema_version": "ndp50-power-freeze/v1",
            "status": "frozen_before_test_semantic_execution",
            "test_outcomes_observed": False,
            "test_detail_snapshot_count": 0,
            "artifact_bindings": {
                "selection": {"sha256": _sha(selection)},
                "opportunity_manifest": {"sha256": _sha(opportunity)},
                "cpa_design": {"sha256": _sha(cpa_design)},
            },
            "power_calculation": {
                "planning_scenario": {
                    "required_semantic_opportunity_dataset_count": 7,
                    "required_total_dataset_count": 23,
                }
            },
            "derived_gates": {
                "test_power_plan_frozen": True,
                "test_design_meets_pretest_assurance": True,
            },
        },
    )
    report = build_feasibility_report(
        opportunity_manifest_path=opportunity,
        selection_path=selection,
        cpa_design_path=cpa_design,
        study_root=study_root,
        power_freeze_path=power_freeze,
    )
    assert report["gates"]["test_power_plan_frozen"] is True
    assert report["test_state"]["power_plan"][
        "required_total_dataset_count"
    ] == 23
    assert report["test_state"]["power_plan"][
        "maximum_selected_test_dataset_count"
    ] == 25


def test_ndp_power_freeze_binding_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    opportunity, selection, cpa_design, study_root = _inputs(tmp_path)
    power_freeze = tmp_path / "power-freeze.json"
    _write(
        power_freeze,
        {
            "schema_version": "ndp50-power-freeze/v1",
            "status": "frozen_before_test_semantic_execution",
            "test_outcomes_observed": False,
            "test_detail_snapshot_count": 0,
            "artifact_bindings": {
                "selection": {"sha256": "0" * 64},
                "opportunity_manifest": {"sha256": _sha(opportunity)},
                "cpa_design": {"sha256": _sha(cpa_design)},
            },
            "power_calculation": {
                "planning_scenario": {
                    "required_semantic_opportunity_dataset_count": 7,
                    "required_total_dataset_count": 23,
                }
            },
            "derived_gates": {"test_power_plan_frozen": True},
        },
    )
    with pytest.raises(
        NDPPowerFeasibilityError,
        match="selection binding mismatch",
    ):
        build_feasibility_report(
            opportunity_manifest_path=opportunity,
            selection_path=selection,
            cpa_design_path=cpa_design,
            study_root=study_root,
            power_freeze_path=power_freeze,
        )
