from __future__ import annotations

import hashlib
import json
from pathlib import Path

from high_fidelity_schema_study.ndp50_semantic_opportunities import (
    build_semantic_opportunity_manifest,
)


def _write(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_manifest_includes_schema_cases_and_defers_cpa_judgment(
    tmp_path: Path,
) -> None:
    selection = tmp_path / "selection.json"
    _write(
        selection,
        {
            "selected_datasets": [
                {
                    "dataset_id": "d1",
                    "split": "development",
                    "primary_format_class": "supported_tabular",
                }
            ]
        },
    )
    schema_path = tmp_path / "schemas" / "development" / "d1" / "r1.json"
    schema_hash = _write(
        schema_path,
        {
            "schema": {
                "file_format": "csv",
                "data_modality": "tabular",
                "fields": [
                    {"field_path": "id"},
                    {"field_path": "value"},
                ],
            }
        },
    )
    run = tmp_path / "development.json"
    _write(
        run,
        {
            "run_role": "development",
            "datasets": [
                {
                    "dataset_id": "d1",
                    "title": "Example",
                    "detail_snapshot": {"file": "d1.json.gz", "sha256": "a" * 64},
                    "resource_records": [
                        {
                            "resource_id": "r1",
                            "url": "https://example.invalid/r1.csv",
                            "download": {
                                "sha256": "b" * 64,
                                "bytes_downloaded": 10,
                                "content_type": "text/csv",
                            },
                            "extraction": {
                                "status": "success",
                                "artifact": {
                                    "file": "r1.json",
                                    "sha256": schema_hash,
                                },
                            },
                        }
                    ],
                }
            ],
        },
    )
    ledger = tmp_path / "failure.json"
    _write(
        ledger,
        {
            "run_role": "development",
            "entry_count": 0,
        },
    )

    manifest = build_semantic_opportunity_manifest(
        run_paths=[run],
        selection_path=selection,
        schemas_root=tmp_path / "schemas",
        failure_ledger_paths=[ledger],
    )

    assert manifest["counts"]["case_count"] == 1
    assert manifest["counts"]["dataset_cluster_count"] == 1
    case = manifest["cases"][0]
    assert case["field_paths"] == ["id", "value"]
    assert (
        case["cpa_applicability_status"]
        == "requires_manual_relation_and_subject_assessment"
    )
    assert case["cpa_subject_column_status"] == (
        "unassigned_requires_independent_annotation"
    )
