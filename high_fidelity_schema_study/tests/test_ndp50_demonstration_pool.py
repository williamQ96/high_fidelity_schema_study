from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_demonstration_pool import (
    NDPDemonstrationPoolError,
    build_pool,
    build_workflow_spec,
    verify_pool,
)


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding(path: Path, root: Path) -> dict[str, str]:
    return {
        "file": path.relative_to(root).as_posix(),
        "sha256": _sha(path),
    }


def _fixture(root: Path) -> tuple[Path, Path]:
    packet_dir = root / "semantic" / "packets"
    gold_dir = root / "semantic" / "gold"
    manifest_cases = []
    gold_cases = []
    for index in range(1, 7):
        split = "development" if index <= 5 else "validation"
        case_id = f"case-{split}-{index}"
        packet_path = packet_dir / f"{case_id}.json"
        packet = {
            "schema_version": "semantic-annotation-packet/v1",
            "case_id": case_id,
            "dataset_id": f"dataset-{index}",
            "data_modality": "tabular",
            "field_inventory": [
                {
                    "field_path": "temperature",
                    "field_name": "temperature",
                    "physical_type": "float",
                    "example_values": ["18.5", "20.1"],
                    "nullable": False,
                    "shape": None,
                }
            ],
        }
        _write(packet_path, packet)
        manifest_cases.append(
            {
                "case_id": case_id,
                "split": split,
                "packet_file": packet_path.relative_to(
                    root / "semantic"
                ).as_posix(),
                "packet_sha256": _sha(packet_path),
            }
        )
        consensus_path = gold_dir / f"{case_id}.json"
        consensus = {
            "schema_version": "blind-semantic-gold/v1",
            "annotation_stage": "consensus",
            "fields": [
                {
                    "field_path": "temperature",
                    "applicability": {
                        "physical_type": True,
                        "logical_type": True,
                        "semantic_type": True,
                        "unit": True,
                    },
                    "correct_physical_type": "float",
                    "correct_logical_type": "continuous",
                    "correct_semantic_type": "air_temperature",
                    "unit": "degree_Celsius",
                }
            ],
        }
        _write(consensus_path, consensus)
        gold_cases.append(
            {
                "case_id": case_id,
                "split": split,
                "consensus": _binding(consensus_path, root),
            }
        )
    manifest_path = root / "semantic" / "manifest.json"
    _write(
        manifest_path,
        {
            "schema_version": "ndp50-semantic-packet-pack/v1",
            "status": "neutral_packets_ready_source_bundles_blocked",
            "cases": manifest_cases,
        },
    )
    approval_path = root / "semantic" / "gold-approval.json"
    _write(
        approval_path,
        {
            "schema_version": "ndp50-semantic-gold-approval/v1",
            "status": "approved_independent_gold_complete",
            "derived_gates": {"independent_gold_complete": True},
            "index": {"cases": gold_cases},
        },
    )
    return manifest_path, approval_path


def test_workflow_is_neutral_and_counts_development_cases(
    tmp_path: Path,
) -> None:
    manifest, _ = _fixture(tmp_path)
    workflow = build_workflow_spec(
        packet_manifest_path=manifest,
        study_root=tmp_path,
    )
    assert workflow["human_decisions_present"] is False
    assert workflow["development_case_count"] == 5
    assert workflow["candidate_inclusion_policy"] == (
        "all_approved_development_cases"
    )


def test_pool_is_deterministic_development_only_and_replays(
    tmp_path: Path,
) -> None:
    manifest, approval = _fixture(tmp_path)
    pool = build_pool(
        semantic_gold_approval_path=approval,
        packet_manifest_path=manifest,
        study_root=tmp_path,
    )
    assert pool["case_count"] == 5
    assert {item["source_split"] for item in pool["cases"]} == {
        "development"
    }
    assert [
        item["case_id"] for item in pool["cases"]
    ] == sorted(item["case_id"] for item in pool["cases"])
    assert (
        pool["cases"][0]["gold_projection"]["fields"][0]["annotations"][
            "semantic_type"
        ]["value"]
        == "air_temperature"
    )
    assert (
        verify_pool(
            pool,
            semantic_gold_approval_path=approval,
            packet_manifest_path=manifest,
            study_root=tmp_path,
        )["status"]
        == "passed"
    )


def test_pool_replay_rejects_semantic_projection_tampering(
    tmp_path: Path,
) -> None:
    manifest, approval = _fixture(tmp_path)
    pool = build_pool(
        semantic_gold_approval_path=approval,
        packet_manifest_path=manifest,
        study_root=tmp_path,
    )
    tampered = copy.deepcopy(pool)
    tampered["cases"][0]["gold_projection"]["fields"][0]["annotations"][
        "semantic_type"
    ]["value"] = "water_temperature"
    validation = verify_pool(
        tampered,
        semantic_gold_approval_path=approval,
        packet_manifest_path=manifest,
        study_root=tmp_path,
    )
    assert validation["status"] == "failed"
    assert "cases" in validation["differing_top_level_keys"]


def test_pool_rejects_packet_gold_field_coverage_mismatch(
    tmp_path: Path,
) -> None:
    manifest, approval = _fixture(tmp_path)
    approval_payload = json.loads(approval.read_text(encoding="utf-8"))
    first = approval_payload["index"]["cases"][0]
    consensus_path = tmp_path / first["consensus"]["file"]
    consensus = json.loads(consensus_path.read_text(encoding="utf-8"))
    consensus["fields"][0]["field_path"] = "different"
    _write(consensus_path, consensus)
    first["consensus"]["sha256"] = _sha(consensus_path)
    _write(approval, approval_payload)
    with pytest.raises(
        NDPDemonstrationPoolError,
        match="packet and gold field coverage differ",
    ):
        build_pool(
            semantic_gold_approval_path=approval,
            packet_manifest_path=manifest,
            study_root=tmp_path,
        )
