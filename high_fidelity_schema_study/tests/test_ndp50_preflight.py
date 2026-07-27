from __future__ import annotations

import json
from pathlib import Path

from high_fidelity_schema_study.ndp50_execution import ResourcePolicy
from high_fidelity_schema_study.ndp50_preflight import (
    build_validation_freeze,
    implementation_paths,
    validate_validation_freeze,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_freeze_binds_artifacts_implementation_and_split_identity(
    tmp_path: Path,
) -> None:
    frame = tmp_path / "candidate_frame.json"
    design = tmp_path / "selection_design.json"
    selection = tmp_path / "selection.json"
    run = tmp_path / "runs" / "development.json"
    controls = tmp_path / "reports" / "negative.json"
    _write(frame, {"counts": {"dataset_count": 3}})
    import hashlib

    frame_hash = hashlib.sha256(frame.read_bytes()).hexdigest()
    _write(
        design,
        {
            "candidate_frame_sha256": frame_hash,
            "split_counts": {"development": 1, "validation": 1, "test": 1},
        },
    )
    design_hash = hashlib.sha256(design.read_bytes()).hexdigest()
    _write(
        selection,
        {
            "candidate_frame": {"sha256": frame_hash},
            "selection_design": {"sha256": design_hash},
            "selected_datasets": [
                {"dataset_id": "d", "split": "development"},
                {"dataset_id": "v", "split": "validation"},
                {"dataset_id": "t", "split": "test"},
            ],
        },
    )
    _write(run, {"datasets": [{"dataset_id": "d"}]})
    _write(
        controls,
        {
            "status": "passed",
            "counts": {"failed_count": 0},
        },
    )

    freeze = build_validation_freeze(
        candidate_frame_path=frame,
        selection_design_path=design,
        selection_path=selection,
        development_run_path=run,
        negative_controls_path=controls,
        policy=ResourcePolicy(),
    )
    report = validate_validation_freeze(
        freeze=freeze,
        candidate_frame_path=frame,
        selection_design_path=design,
        selection_path=selection,
        development_run_path=run,
        negative_controls_path=controls,
        require_unopened=True,
    )

    assert report["status"] == "passed"
    assert report["readiness"] == {
        "structural_validation_ready": True,
        "semantic_validation_ready": False,
        "test_ready": False,
    }


def test_structural_freeze_excludes_post_validation_semantic_code() -> None:
    names = {path.name for path in implementation_paths()}

    assert "ndp50_execution.py" in names
    assert "ndp50_cpa_screen_workflow.py" not in names
    assert "ndp50_readiness.py" not in names


def test_refreeze_after_opened_validation_requires_bound_deviation(
    tmp_path: Path,
) -> None:
    frame = tmp_path / "candidate_frame.json"
    design = tmp_path / "selection_design.json"
    selection = tmp_path / "selection.json"
    run = tmp_path / "development.json"
    controls = tmp_path / "negative.json"
    _write(frame, {"counts": {"dataset_count": 3}})
    import hashlib

    frame_hash = hashlib.sha256(frame.read_bytes()).hexdigest()
    _write(
        design,
        {
            "candidate_frame_sha256": frame_hash,
            "split_counts": {"development": 1, "validation": 1, "test": 1},
        },
    )
    design_hash = hashlib.sha256(design.read_bytes()).hexdigest()
    _write(
        selection,
        {
            "candidate_frame": {"sha256": frame_hash},
            "selection_design": {"sha256": design_hash},
            "selected_datasets": [
                {"dataset_id": "d", "split": "development"},
                {"dataset_id": "v", "split": "validation"},
                {"dataset_id": "t", "split": "test"},
            ],
        },
    )
    _write(run, {"datasets": [{"dataset_id": "d"}]})
    _write(controls, {"status": "passed", "counts": {"failed_count": 0}})
    validation_dir = tmp_path / "acquisition" / "validation_details"
    validation_dir.mkdir(parents=True)
    (validation_dir / "v.json.gz").write_bytes(b"opened")
    deviation = tmp_path / "deviation.md"
    deviation.write_text("documented", encoding="utf-8")

    freeze = build_validation_freeze(
        candidate_frame_path=frame,
        selection_design_path=design,
        selection_path=selection,
        development_run_path=run,
        negative_controls_path=controls,
        policy=ResourcePolicy(),
        deviation_record_path=deviation,
    )

    assert freeze["held_out_state"][
        "validation_details_opened_before_freeze"
    ] is True
    assert freeze["held_out_state"]["test_details_opened_before_freeze"] is False
    assert freeze["held_out_state"]["deviation_record"]["file"] == "deviation.md"


def test_preflight_detects_post_freeze_artifact_change(tmp_path: Path) -> None:
    # Reuse the public validator with a deliberately incomplete freeze to ensure
    # it fails closed instead of accepting missing hash bindings.
    paths = {}
    for name in (
        "candidate_frame",
        "selection_design",
        "selection",
        "development_run",
        "negative_controls",
    ):
        path = tmp_path / f"{name}.json"
        _write(path, {"selected_datasets": [], "datasets": []})
        paths[name] = path

    report = validate_validation_freeze(
        freeze={
            "schema_version": "ndp50-structural-validation-freeze/v1",
            "artifact_hashes": {},
            "implementation_hashes": {},
            "readiness_boundaries": {
                "structural_validation_authorized": True,
            },
        },
        candidate_frame_path=paths["candidate_frame"],
        selection_design_path=paths["selection_design"],
        selection_path=paths["selection"],
        development_run_path=paths["development_run"],
        negative_controls_path=paths["negative_controls"],
        require_unopened=False,
    )

    assert report["status"] == "failed"
    assert report["readiness"]["structural_validation_ready"] is False
