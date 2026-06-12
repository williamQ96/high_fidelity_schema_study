from __future__ import annotations

import hashlib
from pathlib import Path

from high_fidelity_schema_study.evaluate_phase16a_json import evaluate_phase16a, write_phase16a_artifacts


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase16a_metrics_are_complete():
    metrics = evaluate_phase16a()["metrics"]

    assert metrics["case_count"] == 6
    for key, value in metrics.items():
        if key.endswith("_accuracy") or key == "evidence_coverage":
            assert value == 1.0, key
    assert metrics["unsupported_promotion_count"] == 0


def test_phase16a_builder_only_writes_requested_experiment_root(tmp_path):
    frozen = ROOT / "data" / "derived" / "internal_baseline_report.json"
    before = _sha256(frozen)
    output = tmp_path / "phase16a"

    report = write_phase16a_artifacts(output_root=output)

    assert (output / "report.json").exists()
    assert (output / "report.md").exists()
    assert len(list((output / "outcomes").glob("*.json"))) == report["metrics"]["case_count"]
    assert _sha256(frozen) == before
