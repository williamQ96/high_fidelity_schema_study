from __future__ import annotations

from high_fidelity_schema_study.ndp50_report import summarize_run


def test_summary_keeps_end_to_end_and_conditional_denominators_separate() -> None:
    selection = {
        "selected_datasets": [
            {"dataset_id": "d1", "split": "development"},
            {"dataset_id": "d2", "split": "development"},
            {"dataset_id": "v1", "split": "validation"},
        ]
    }
    execution = {
        "run_role": "development",
        "datasets": [
            {
                "dataset_id": "d1",
                "resource_records": [
                    {
                        "resource_id": "r1",
                        "catalog_format": "csv",
                        "plan": {"decision": "attempt", "reason": None},
                        "download": {"status": "acquired", "failure": None},
                        "extraction": {"status": "success", "issues": []},
                    }
                ],
            },
            {
                "dataset_id": "d2",
                "resource_records": [
                    {
                        "resource_id": "r2",
                        "catalog_format": "image",
                        "plan": {
                            "decision": "skip_unsupported_format",
                            "reason": "unsupported",
                        },
                        "download": {"status": "skip_unsupported_format"},
                        "extraction": None,
                    }
                ],
            },
        ]
    }

    summary, ledger = summarize_run(execution, selection)

    assert summary["coverage"]["dataset_end_to_end_rate"] == 0.5
    assert summary["coverage"]["resource_end_to_end_rate"] == 0.5
    assert summary["coverage"]["extraction_success_rate_given_acquisition"] == 1.0
    assert summary["dataset_outcome_classes"] == {
        "no_policy_attempt": 1,
        "schema_extracted": 1,
    }
    assert summary["dataset_bootstrap_interval"]["repetitions"] == 10_000
    assert ledger["reason_counts"] == {"skip_unsupported_format": 1}


def test_abstention_ledger_uses_extraction_issue_not_attempt_label() -> None:
    selection = {
        "selected_datasets": [
            {
                "dataset_id": "v1",
                "split": "validation",
                "primary_format_class": "supported_tabular",
            }
        ]
    }
    execution = {
        "run_role": "validation",
        "datasets": [
            {
                "dataset_id": "v1",
                "resource_records": [
                    {
                        "resource_id": "r1",
                        "catalog_format": "csv",
                        "plan": {"decision": "attempt", "reason": None},
                        "download": {"status": "acquired", "failure": None},
                        "extraction": {
                            "status": "abstained",
                            "issues": [
                                {
                                    "code": "unknown_no_signature",
                                    "message": "No trustworthy signal.",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }

    _, ledger = summarize_run(execution, selection)

    assert ledger["reason_counts"] == {"unknown_no_signature": 1}
