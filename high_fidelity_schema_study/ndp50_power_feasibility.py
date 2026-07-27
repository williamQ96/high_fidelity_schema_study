from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .semantic_power_analysis import (
    validate_power_analysis,
    verify_calibration_sources,
)


SCHEMA_VERSION = "ndp50-semantic-power-feasibility/v1"
FAMILYWISE_ALPHA = 0.05
PRIMARY_CONTRAST_COUNT = 2
ALPHA_PER_CONTRAST = FAMILYWISE_ALPHA / PRIMARY_CONTRAST_COUNT


class NDPPowerFeasibilityError(ValueError):
    pass


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def minimum_two_sided_sign_flip_p(nonzero_pair_count: int) -> float | None:
    if nonzero_pair_count < 0:
        raise NDPPowerFeasibilityError(
            "nonzero_pair_count cannot be negative"
        )
    if nonzero_pair_count == 0:
        return None
    return min(1.0, 2.0 ** (1 - nonzero_pair_count))


def minimum_nonzero_pairs_for_resolution(alpha: float) -> int:
    if not 0.0 < alpha < 1.0:
        raise NDPPowerFeasibilityError("alpha must be in (0, 1)")
    count = 1
    while minimum_two_sided_sign_flip_p(count) > alpha:
        count += 1
    return count


def best_case_all_success_clopper_pearson_lower(
    cluster_count: int,
    *,
    confidence_level: float,
) -> float | None:
    if cluster_count < 0:
        raise NDPPowerFeasibilityError("cluster_count cannot be negative")
    if cluster_count == 0:
        return None
    if not 0.0 < confidence_level < 1.0:
        raise NDPPowerFeasibilityError(
            "confidence_level must be in (0, 1)"
        )
    alpha = 1.0 - confidence_level
    return (alpha / 2.0) ** (1.0 / cluster_count)


def _split_counts(
    cases: list[Mapping[str, Any]],
    *,
    cpa_only: bool,
) -> Dict[str, Dict[str, int]]:
    selected = (
        [
            item
            for item in cases
            if item.get("cpa_applicability_status")
            == "requires_manual_relation_and_subject_assessment"
        ]
        if cpa_only
        else cases
    )
    result = {}
    for split in ("development", "validation"):
        split_cases = [
            item for item in selected if item.get("split") == split
        ]
        result[split] = {
            "resource_case_count": len(split_cases),
            "dataset_cluster_count": len(
                {str(item["dataset_id"]) for item in split_cases}
            ),
        }
    return result


def _resolution_diagnostic(cluster_count: int) -> Dict[str, Any]:
    min_p = minimum_two_sided_sign_flip_p(cluster_count)
    return {
        "maximum_nonzero_pair_count": cluster_count,
        "best_case_two_sided_exact_sign_flip_p": min_p,
        "holm_worst_case_alpha_per_primary_contrast": ALPHA_PER_CONTRAST,
        "can_reach_holm_worst_case_threshold_in_best_case": (
            min_p is not None and min_p <= ALPHA_PER_CONTRAST
        ),
        "minimum_nonzero_pairs_for_exact_resolution": (
            minimum_nonzero_pairs_for_resolution(ALPHA_PER_CONTRAST)
        ),
        "best_case_all_success_95pct_clopper_pearson_lower": (
            best_case_all_success_clopper_pearson_lower(
                cluster_count, confidence_level=0.95
            )
        ),
        "interpretation": (
            "Resolution diagnostic only. It assumes every available cluster "
            "has a nonzero paired difference in the same direction; actual "
            "power and precision can only be worse when ties, missingness, "
            "noncomparability, or heterogeneous effects occur."
        ),
    }


def build_feasibility_report(
    *,
    opportunity_manifest_path: Path,
    selection_path: Path,
    cpa_design_path: Path,
    study_root: Path,
    power_analysis_path: Path | None = None,
    power_freeze_path: Path | None = None,
) -> Dict[str, Any]:
    opportunity = _load_json(opportunity_manifest_path)
    selection = _load_json(selection_path)
    cpa_design = _load_json(cpa_design_path)
    if (
        opportunity.get("schema_version")
        != "ndp50-semantic-opportunity-manifest/v1"
    ):
        raise NDPPowerFeasibilityError(
            "unexpected semantic opportunity manifest schema"
        )
    cases = opportunity.get("cases")
    if not isinstance(cases, list) or not cases:
        raise NDPPowerFeasibilityError(
            "semantic opportunity manifest has no cases"
        )
    if any(item.get("split") == "test" for item in cases):
        raise NDPPowerFeasibilityError(
            "pre-test feasibility artifact must not contain test identities"
        )
    if any(item.get("split") not in {"development", "validation"} for item in cases):
        raise NDPPowerFeasibilityError(
            "semantic opportunity cases have invalid splits"
        )
    case_ids = [str(item.get("case_id") or "") for item in cases]
    if any(not case_id for case_id in case_ids) or len(case_ids) != len(
        set(case_ids)
    ):
        raise NDPPowerFeasibilityError(
            "semantic opportunity case identity is invalid"
        )
    general_counts = _split_counts(cases, cpa_only=False)
    cpa_counts = _split_counts(cases, cpa_only=True)
    declared_opportunity_counts = opportunity.get("counts", {})
    actual_split_case_counts = {
        split: general_counts[split]["resource_case_count"]
        for split in ("development", "validation")
    }
    if (
        declared_opportunity_counts.get("case_count") != len(cases)
        or declared_opportunity_counts.get("dataset_cluster_count")
        != len({str(item["dataset_id"]) for item in cases})
        or declared_opportunity_counts.get("split_case_counts")
        != actual_split_case_counts
    ):
        raise NDPPowerFeasibilityError(
            "opportunity manifest declared counts are inconsistent"
        )
    if cpa_design.get("schema_version") != "ndp50-cpa-design/v1":
        raise NDPPowerFeasibilityError("unexpected CPA design schema")
    declared_cpa = cpa_design.get("candidate_counts", {})
    actual_cpa_split_counts = {
        split: cpa_counts[split]["resource_case_count"]
        for split in ("development", "validation")
    }
    if (
        declared_cpa.get("resource_cases")
        != sum(item["resource_case_count"] for item in cpa_counts.values())
        or declared_cpa.get("dataset_clusters")
        != len(
            {
                str(item["dataset_id"])
                for item in cases
                if item.get("cpa_applicability_status")
                == "requires_manual_relation_and_subject_assessment"
            }
        )
        or declared_cpa.get("split_case_counts")
        != actual_cpa_split_counts
    ):
        raise NDPPowerFeasibilityError(
            "CPA design and opportunity manifest counts disagree"
        )
    selected = selection.get("selected_datasets")
    if not isinstance(selected, list):
        raise NDPPowerFeasibilityError("selection has no selected_datasets")
    selected_counts = Counter(str(item.get("split") or "") for item in selected)
    selected_ids = [str(item.get("dataset_id") or "") for item in selected]
    if set(selected_counts) != {"development", "validation", "test"}:
        raise NDPPowerFeasibilityError("selection split identity is invalid")
    if (
        any(not item for item in selected_ids)
        or len(selected_ids) != len(set(selected_ids))
        or selection.get("counts", {}).get("selected_dataset_count")
        != len(selected)
        or selection.get("counts", {}).get("split_counts")
        != dict(selected_counts)
    ):
        raise NDPPowerFeasibilityError(
            "selection declared counts or dataset identity are inconsistent"
        )
    test_detail_dir = study_root / "acquisition" / "test_details"
    test_detail_count = (
        len(list(test_detail_dir.glob("*.json.gz")))
        if test_detail_dir.exists()
        else 0
    )
    if test_detail_count:
        raise NDPPowerFeasibilityError(
            "test details must remain unopened during pre-test feasibility"
        )

    if power_analysis_path is not None and power_freeze_path is not None:
        raise NDPPowerFeasibilityError(
            "supply either the legacy power analysis or NDP power freeze"
        )
    power_plan = None
    power_plan_frozen = False
    if power_analysis_path is not None:
        payload = _load_json(power_analysis_path)
        report = validate_power_analysis(payload)
        if report.get("status") != "ready" or payload.get("status") != "frozen":
            raise NDPPowerFeasibilityError(
                "power analysis must be frozen and reproducible"
            )
        verify_calibration_sources(
            payload["planning_inputs"], owner=power_analysis_path
        )
        power_plan_frozen = True
        required = payload["assumptions"][
            "required_semantic_opportunity_case_count"
        ]
        power_plan = {
            "file": power_analysis_path.name,
            "sha256": _sha256_file(power_analysis_path),
            "required_semantic_opportunity_dataset_count": required,
            "maximum_selected_test_dataset_count": selected_counts["test"],
            "maximum_test_count_can_meet_requirement": (
                selected_counts["test"] >= required
            ),
        }
    elif power_freeze_path is not None:
        payload = _load_json(power_freeze_path)
        if (
            payload.get("schema_version") != "ndp50-power-freeze/v1"
            or payload.get("status")
            != "frozen_before_test_semantic_execution"
            or payload.get("test_outcomes_observed") is not False
            or payload.get("test_detail_snapshot_count") != 0
            or payload.get("derived_gates", {}).get(
                "test_power_plan_frozen"
            )
            is not True
        ):
            raise NDPPowerFeasibilityError(
                "NDP power freeze is not a valid pre-test frozen plan"
            )
        bindings = payload.get("artifact_bindings", {})
        expected_bindings = {
            "selection": _sha256_file(selection_path),
            "opportunity_manifest": _sha256_file(
                opportunity_manifest_path
            ),
            "cpa_design": _sha256_file(cpa_design_path),
        }
        for key, expected_hash in expected_bindings.items():
            if bindings.get(key, {}).get("sha256") != expected_hash:
                raise NDPPowerFeasibilityError(
                    f"NDP power freeze {key} binding mismatch"
                )
        calculation = payload.get("power_calculation", {})
        planning = calculation.get("planning_scenario", {})
        required = planning.get(
            "required_semantic_opportunity_dataset_count"
        )
        required_total = planning.get("required_total_dataset_count")
        if (
            not isinstance(required, int)
            or isinstance(required, bool)
            or required < 2
            or not isinstance(required_total, int)
            or isinstance(required_total, bool)
            or required_total < required
        ):
            raise NDPPowerFeasibilityError(
                "NDP power freeze planning counts are invalid"
            )
        power_plan_frozen = True
        power_plan = {
            "file": power_freeze_path.name,
            "sha256": _sha256_file(power_freeze_path),
            "schema_version": "ndp50-power-freeze/v1",
            "required_semantic_opportunity_dataset_count": required,
            "required_total_dataset_count": required_total,
            "maximum_selected_test_dataset_count": selected_counts["test"],
            "maximum_test_count_can_meet_requirement": (
                selected_counts["test"] >= required_total
            ),
            "test_design_meets_pretest_assurance": payload.get(
                "derived_gates", {}
            ).get("test_design_meets_pretest_assurance")
            is True,
        }

    validation_general_clusters = general_counts["validation"][
        "dataset_cluster_count"
    ]
    validation_cpa_clusters = cpa_counts["validation"][
        "dataset_cluster_count"
    ]
    implementation = Path(__file__).resolve()
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "feasibility_assessed_confirmatory_power_not_established",
        "artifact_bindings": {
            "opportunity_manifest": {
                "file": opportunity_manifest_path.name,
                "sha256": _sha256_file(opportunity_manifest_path),
            },
            "selection": {
                "file": selection_path.name,
                "sha256": _sha256_file(selection_path),
            },
            "cpa_design": {
                "file": cpa_design_path.name,
                "sha256": _sha256_file(cpa_design_path),
            },
        },
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            "semantic_power_analysis.py": _sha256_file(
                implementation.with_name("semantic_power_analysis.py")
            )
        },
        "primary_statistical_unit": "dataset",
        "selected_dataset_counts": dict(sorted(selected_counts.items())),
        "semantic_opportunity_counts": general_counts,
        "cpa_candidate_counts": cpa_counts,
        "validation_resolution": {
            "general_semantic": _resolution_diagnostic(
                validation_general_clusters
            ),
            "cpa": _resolution_diagnostic(validation_cpa_clusters),
        },
        "multiplicity": {
            "primary_contrast_count": PRIMARY_CONTRAST_COUNT,
            "familywise_alpha": FAMILYWISE_ALPHA,
            "holm_worst_case_alpha_per_contrast": ALPHA_PER_CONTRAST,
        },
        "validation_claim_scope": {
            "general_semantic": "descriptive_feasibility_pilot_only",
            "cpa": "descriptive_feasibility_pilot_only",
            "confirmatory_no_effect_claim_allowed": False,
            "confirmatory_superiority_claim_allowed": False,
            "reason": (
                "Even the best-case exact sign-flip p-value cannot reach "
                "the multiplicity-adjusted primary threshold with the "
                "available validation dataset clusters."
            ),
        },
        "test_state": {
            "test_detail_snapshot_count": test_detail_count,
            "test_split_unopened": True,
            "maximum_selected_test_dataset_count": selected_counts["test"],
            "semantic_opportunity_count": None,
            "power_plan_frozen": power_plan_frozen,
            "power_plan": power_plan,
            "confirmatory_inference_authorized": False,
        },
        "post_test_conditional_rules": [
            "Do not inspect test semantic outcomes until all non-power readiness gates and a frozen non-blind power plan pass.",
            "Use dataset clusters, never pooled resource or field rows, as the primary independent units.",
            "Require the frozen comparable-opportunity count; the exact sign-flip resolution floor is necessary but not sufficient power.",
            "If the frozen count is missed, label the result underpowered and do not interpret a null result as evidence of no effect.",
            "Do not add selectively chosen datasets after observing test outcomes.",
        ],
        "gates": {
            "feasibility_assessed": True,
            "validation_confirmatory_power_established": False,
            "test_power_plan_frozen": power_plan_frozen,
            "pilot_reporting_required": True,
        },
    }


def validate_feasibility_report(
    payload: Mapping[str, Any],
    *,
    opportunity_manifest_path: Path,
    selection_path: Path,
    cpa_design_path: Path,
    study_root: Path,
    power_analysis_path: Path | None = None,
    power_freeze_path: Path | None = None,
) -> Dict[str, Any]:
    expected = build_feasibility_report(
        opportunity_manifest_path=opportunity_manifest_path,
        selection_path=selection_path,
        cpa_design_path=cpa_design_path,
        study_root=study_root,
        power_analysis_path=power_analysis_path,
        power_freeze_path=power_freeze_path,
    )
    differing = sorted(
        key
        for key in set(payload) | set(expected)
        if payload.get(key) != expected.get(key)
    )
    return {
        "schema_version": "ndp50-semantic-power-feasibility-validation/v1",
        "status": "passed" if not differing else "failed",
        "differing_top_level_keys": differing,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assess NDP-50 semantic/CPA inferential feasibility."
    )
    parser.add_argument("--opportunity-manifest", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--cpa-design", type=Path, required=True)
    parser.add_argument("--study-root", type=Path, required=True)
    parser.add_argument("--power-analysis", type=Path)
    parser.add_argument("--power-freeze", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_feasibility_report(
        opportunity_manifest_path=args.opportunity_manifest,
        selection_path=args.selection,
        cpa_design_path=args.cpa_design,
        study_root=args.study_root,
        power_analysis_path=args.power_analysis,
        power_freeze_path=args.power_freeze,
    )
    _write_json(args.output, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "semantic_validation_clusters": payload[
                    "semantic_opportunity_counts"
                ]["validation"]["dataset_cluster_count"],
                "cpa_validation_clusters": payload["cpa_candidate_counts"][
                    "validation"
                ]["dataset_cluster_count"],
                "test_power_plan_frozen": payload["gates"][
                    "test_power_plan_frozen"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
