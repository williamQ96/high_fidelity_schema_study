from __future__ import annotations

import hashlib
from pathlib import Path

from high_fidelity_schema_study.extractors.base import ExtractionRequest
from high_fidelity_schema_study.extractors.registry import extract_path
from high_fidelity_schema_study.evaluate_phase12 import evaluate_phase12, write_phase12_artifacts


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase12_challenge_metrics_are_complete():
    report = evaluate_phase12()
    metrics = report["metrics"]

    assert metrics["case_count"] == 13
    assert metrics["format_detection_accuracy"] == 1.0
    assert metrics["extractor_routing_accuracy"] == 1.0
    assert metrics["structured_failure_artifact_completeness"] == 1.0
    assert metrics["time_axis_selection_accuracy"] == 1.0
    assert metrics["per_property_temporal_accuracy"] == 1.0
    assert metrics["exact_temporal_profile_accuracy"] == 1.0
    assert metrics["abstention_precision"] == 1.0
    assert metrics["abstention_recall"] == 1.0
    assert metrics["reason_code_coverage"] == 1.0
    assert metrics["evidence_coverage"] == 1.0
    assert metrics["unsupported_promotion_count"] == 0


def test_phase12_builder_only_writes_requested_experiment_root(tmp_path):
    frozen_path = ROOT / "data" / "derived" / "internal_baseline_report.json"
    before = _sha256(frozen_path)

    output_root = tmp_path / "phase12"
    report = write_phase12_artifacts(output_root=output_root)

    assert (output_root / "report.json").exists()
    assert (output_root / "report.md").exists()
    assert len(list((output_root / "outcomes").glob("*.json"))) == report["metrics"]["case_count"]
    assert _sha256(frozen_path) == before


def test_existing_pilot_temporal_profiles_keep_core_properties():
    expected = {
        "ts_easy_hourly_weather/hourly_weather.csv": {
            "field": "timestamp",
            "timezone": "unknown",
            "frequency": "1 hour",
            "regularity": "regular",
            "missing_intervals": 0,
        },
        "ts_hard_irregular_buoy/buoy_irregular.csv": {
            "field": "event_time",
            "timezone": "unknown",
            "frequency": "mixed",
            "regularity": "irregular",
            "missing_intervals": None,
        },
        "ts_medium_power_meter/power_meter.csv": {
            "field": "ts_utc",
            "timezone": "UTC",
            "frequency": "15 minutes",
            "regularity": "mostly_regular",
            "missing_intervals": 1,
        },
    }

    for relative_path, expected_axis in expected.items():
        path = ROOT / "data" / "raw" / "time_series" / relative_path
        outcome = extract_path(ExtractionRequest(str(path)))
        assert outcome.schema is not None
        assert outcome.schema.metadata["time_series"]["time_axis"] == {
            "type": "datetime",
            **expected_axis,
        }
