from __future__ import annotations

import hashlib
import json
from pathlib import Path

from high_fidelity_schema_study.evaluate_phase14c_zarr_external import (
    evaluate_phase14c,
    write_phase14c_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase14c_canonical_metrics_without_optional_dependencies():
    report = evaluate_phase14c(enable_cross_parser=False)
    metrics = report["metrics"]

    assert metrics["case_count"] == 12
    assert metrics["external_public_case_count"] == 2
    assert metrics["library_produced_case_count"] == 8
    assert metrics["library_derived_edge_count"] == 2
    for key in (
        "supported_compatibility_rate",
        "structured_abstention_quality",
        "unsupported_feature_visibility",
        "malformed_edge_quality",
        "source_documentation_completeness",
        "evidence_coverage",
        "path_portability_accuracy",
        "chunk_payload_non_claim_rate",
    ):
        assert metrics[key] == 1.0, key
    assert metrics["unsupported_promotion_count"] == 0
    assert metrics["true_bug_count"] == 0
    assert metrics["zarr_conformance_assessed_count"] == 0
    assert metrics["xarray_conformance_assessed_count"] == 0
    assert metrics["conformance_difference_count"] == 0


def test_phase14c_generated_report_records_dev_only_conformance():
    report = json.loads(
        (ROOT / "data" / "experiments" / "phase14c_zarr_external_conformance" / "report.json").read_text(
            encoding="utf-8"
        )
    )
    metrics = report["metrics"]

    assert metrics["zarr_conformance_assessed_count"] == 12
    assert metrics["zarr_physical_conformance_rate"] == 0.8333
    assert metrics["xarray_conformance_assessed_count"] == 4
    assert metrics["xarray_structure_conformance_rate"] == 1.0
    assert metrics["conformance_difference_count"] == 5
    assert metrics["unexplained_conformance_difference_count"] == 0
    assert report["conformance_difference_summary"] == {
        "encoded_fill_value_interpretation": 1,
        "parser_default_materialization": 4,
    }


def test_phase14c_builder_only_writes_requested_experiment_root(tmp_path):
    frozen_path = ROOT / "data" / "derived" / "internal_baseline_report.json"
    before = _sha256(frozen_path)

    output_root = tmp_path / "phase14c"
    report = write_phase14c_artifacts(output_root=output_root, enable_cross_parser=False)

    assert (output_root / "report.json").exists()
    assert (output_root / "report.md").exists()
    assert len(list((output_root / "outcomes").glob("*.json"))) == report["metrics"]["case_count"]
    assert _sha256(frozen_path) == before
