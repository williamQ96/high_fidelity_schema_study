from __future__ import annotations

import hashlib
from pathlib import Path

from high_fidelity_schema_study.unified_evaluation import write_unified_evaluation_artifacts


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase18_builder_preserves_frozen_report(tmp_path):
    frozen = ROOT / "data" / "derived" / "internal_baseline_report.json"
    before = _sha256(frozen)

    report = write_unified_evaluation_artifacts(output_root=tmp_path / "phase18")

    assert report["aggregate_score"] is None
    assert _sha256(frozen) == before
