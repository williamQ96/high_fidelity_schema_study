from __future__ import annotations

import hashlib
from pathlib import Path

from high_fidelity_schema_study.evaluate_phase14b_zarr_compatibility import (
    evaluate_phase14b,
    write_phase14b_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase14b_compatibility_metrics_and_classifications():
    report = evaluate_phase14b()
    metrics = report["metrics"]

    assert metrics["case_count"] == 17
    assert metrics["supported_case_count"] == 10
    for key, value in metrics.items():
        if key not in {
            "case_count",
            "supported_case_count",
            "compatibility_gap_count",
            "unsupported_promotion_count",
            "true_bug_count",
        }:
            assert value == 1.0, key
    assert metrics["compatibility_gap_count"] == 2
    assert metrics["unsupported_promotion_count"] == 0
    assert metrics["true_bug_count"] == 0
    assert report["classification_summary"] == {
        "malformed_failure": {"case_count": 2, "expectations_met": 2},
        "structured_abstention": {"case_count": 1, "expectations_met": 1},
        "supported": {"case_count": 10, "expectations_met": 10},
        "unsupported_feature": {"case_count": 4, "expectations_met": 4},
    }


def test_phase14b_builder_only_writes_requested_experiment_root(tmp_path):
    frozen_path = ROOT / "data" / "derived" / "internal_baseline_report.json"
    before = _sha256(frozen_path)

    output_root = tmp_path / "phase14b"
    report = write_phase14b_artifacts(output_root=output_root)

    assert (output_root / "report.json").exists()
    assert (output_root / "report.md").exists()
    assert len(list((output_root / "outcomes").glob("*.json"))) == report["metrics"]["case_count"]
    assert _sha256(frozen_path) == before
