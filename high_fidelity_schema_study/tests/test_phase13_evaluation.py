from __future__ import annotations

import hashlib
from pathlib import Path

from high_fidelity_schema_study.evaluate_phase13_netcdf_cf import (
    evaluate_phase13,
    write_phase13_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase13_netcdf_cf_metrics_are_complete():
    report = evaluate_phase13()
    metrics = report["metrics"]

    assert metrics["case_count"] == 14
    assert metrics["format_detection_accuracy"] == 1.0
    assert metrics["extractor_routing_accuracy"] == 1.0
    assert metrics["physical_extraction_accuracy"] == 1.0
    assert metrics["coordinate_role_accuracy"] == 1.0
    assert metrics["time_axis_accuracy"] == 1.0
    assert metrics["calendar_handling_accuracy"] == 1.0
    assert metrics["unit_mapping_accuracy"] == 1.0
    assert metrics["temporal_abstention_precision"] == 1.0
    assert metrics["temporal_abstention_recall"] == 1.0
    assert metrics["unsupported_promotion_count"] == 0
    assert metrics["evidence_coverage"] == 1.0


def test_phase13_builder_only_writes_requested_experiment_root(tmp_path):
    frozen_path = ROOT / "data" / "derived" / "internal_baseline_report.json"
    before = _sha256(frozen_path)

    output_root = tmp_path / "phase13"
    report = write_phase13_artifacts(output_root=output_root)

    assert (output_root / "report.json").exists()
    assert (output_root / "report.md").exists()
    assert len(list((output_root / "outcomes").glob("*.json"))) == report["metrics"]["case_count"]
    assert _sha256(frozen_path) == before
