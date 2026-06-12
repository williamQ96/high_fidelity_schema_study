from __future__ import annotations

import hashlib
from pathlib import Path

from high_fidelity_schema_study.evaluate_phase17_unified_envelope import evaluate_phase17, write_phase17_artifacts


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase17_metrics_are_complete():
    metrics = evaluate_phase17()["metrics"]

    assert metrics["case_count"] == 8
    for key, value in metrics.items():
        if key != "case_count":
            assert value == 1.0, key


def test_phase17_builder_only_writes_requested_experiment_root(tmp_path):
    frozen = ROOT / "data" / "derived" / "internal_baseline_report.json"
    before = _sha256(frozen)
    output = tmp_path / "phase17"

    report = write_phase17_artifacts(output_root=output)

    assert (output / "report.json").exists()
    assert (output / "report.md").exists()
    assert len(list((output / "envelopes").glob("*.json"))) == report["metrics"]["case_count"]
    assert _sha256(frozen) == before
