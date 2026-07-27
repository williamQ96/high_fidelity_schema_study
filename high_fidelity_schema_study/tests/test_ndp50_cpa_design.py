from __future__ import annotations

import json
from pathlib import Path

from high_fidelity_schema_study.ndp50_cpa_design import (
    PRIMARY_OUTCOME_ID,
    build_cpa_design,
)


def test_cpa_design_requires_blind_manual_applicability_screen(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "opportunities.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "ndp50-semantic-opportunity-manifest/v1",
                "cases": [
                    {
                        "case_id": "csv-case",
                        "dataset_id": "d1",
                        "resource_id": "r1",
                        "split": "development",
                        "field_paths": ["subject", "value"],
                        "cpa_applicability_status": (
                            "requires_manual_relation_and_subject_assessment"
                        ),
                    },
                    {
                        "case_id": "json-case",
                        "dataset_id": "d2",
                        "resource_id": "r2",
                        "split": "validation",
                        "field_paths": ["$.value"],
                        "cpa_applicability_status": (
                            "not_applicable_non_tabular_format"
                        ),
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    design, screen = build_cpa_design(manifest)

    assert design["candidate_counts"] == {
        "resource_cases": 1,
        "dataset_clusters": 1,
        "split_case_counts": {"development": 1},
    }
    assert design["status"].startswith("draft_blocked")
    assert design["analysis"]["primary_outcome_id"] == PRIMARY_OUTCOME_ID
    assert design["analysis"]["primary_test"]["method"] == (
        "two_sided_paired_sign_flip_on_dataset_level_mean_difference"
    )
    assert [item["contrast_id"] for item in design["analysis"][
        "primary_contrasts"
    ]] == ["deterministic-vs-zero", "zero-vs-verified"]
    assert design["analysis"]["missingness_policy"][
        "post_outcome_case_deletion"
    ] is False
    assert design["metric_contract"]["undefined_denominator_policy"] == (
        "emit_null_with_explicit_zero_denominator_and_never_impute_zero"
    )
    assert screen["model_outputs_visible"] is False
    assert screen["developer_participation"] is False
    assert screen["cases"][0]["subject_column_field_path"] is None
