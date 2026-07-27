from __future__ import annotations

from high_fidelity_schema_study.ndp50_negative_controls import (
    run_negative_controls,
)


def test_all_ndp50_negative_controls_pass() -> None:
    report = run_negative_controls()

    assert report["status"] == "passed"
    assert report["counts"] == {
        "control_count": 11,
        "passed_count": 11,
        "failed_count": 0,
    }
    assert len({item["control_id"] for item in report["controls"]}) == 11
