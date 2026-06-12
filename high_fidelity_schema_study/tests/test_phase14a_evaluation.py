from __future__ import annotations

import hashlib
from pathlib import Path

from high_fidelity_schema_study.evaluate_phase14a_zarr import evaluate_phase14a, write_phase14a_artifacts


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase14a_metrics_are_complete():
    metrics = evaluate_phase14a()["metrics"]

    assert metrics["case_count"] == 14
    for key, value in metrics.items():
        if key not in {"case_count", "unsupported_promotion_count"}:
            assert value == 1.0, key
    assert metrics["unsupported_promotion_count"] == 0


def test_phase14a_builder_only_writes_requested_experiment_root(tmp_path):
    frozen_path = ROOT / "data" / "derived" / "internal_baseline_report.json"
    before = _sha256(frozen_path)

    output_root = tmp_path / "phase14a"
    report = write_phase14a_artifacts(output_root=output_root)

    assert (output_root / "report.json").exists()
    assert (output_root / "report.md").exists()
    assert len(list((output_root / "outcomes").glob("*.json"))) == report["metrics"]["case_count"]
    assert _sha256(frozen_path) == before
