from __future__ import annotations

import hashlib
import json
from pathlib import Path

from high_fidelity_schema_study.architecture_variants import (
    ALLOWED_LOGICAL_TYPES,
)
from high_fidelity_schema_study.ndp50_semantic_gold import (
    build_approval,
    build_index_template,
    build_workflow_spec,
    validate_corpus_index,
    verify_approval,
)


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(path: Path, root: Path) -> dict[str, str]:
    return {
        "file": path.relative_to(root).as_posix(),
        "sha256": _sha(path),
    }


def _vocabulary() -> dict:
    return {
        "schema_version": "semantic-annotation-vocabulary/v1",
        "protocol_version": "semantic-architecture-protocol/v1",
        "status": "frozen",
        "vocabulary_version": "fixture-v1",
        "physical_types": ["float32"],
        "logical_types": sorted(ALLOWED_LOGICAL_TYPES),
        "semantic_types": ["air_temperature"],
        "units": ["degree_Celsius"],
        "unit_aliases": {"C": "degree_Celsius"},
        "unit_patterns": [],
        "unknown_representation": None,
    }


def _fixture(tmp_path: Path, monkeypatch) -> dict:
    root = tmp_path / "ndp50"
    packet_manifest = root / "semantic" / "pack" / "manifest.json"
    packet_cases = []
    approved_cases = []
    registry = {}
    for ordinal, case_id in enumerate(("case-dev", "case-val"), start=1):
        split = "development" if ordinal == 1 else "validation"
        packet = packet_manifest.parent / "packets" / f"{case_id}.json"
        _write(packet, {"case_id": case_id, "dataset_id": f"dataset-{ordinal}"})
        packet_cases.append(
            {
                "case_id": case_id,
                "dataset_id": f"dataset-{ordinal}",
                "split": split,
                "packet_file": f"packets/{case_id}.json",
                "packet_sha256": _sha(packet),
            }
        )
    _write(
        packet_manifest,
        {
            "schema_version": "ndp50-semantic-packet-pack/v1",
            "status": "neutral_packets_ready_source_bundles_blocked",
            "case_count": 2,
            "cases": packet_cases,
        },
    )
    vocabulary = root / "semantic" / "vocabulary.json"
    _write(vocabulary, _vocabulary())
    source_dir = root / "semantic" / "source"
    draft_manifest = source_dir / "draft_manifest.json"
    for case in packet_cases:
        bundle = source_dir / f"{case['case_id']}.source-bundle.json"
        _write(bundle, {"case_id": case["case_id"]})
        approved_cases.append(
            {
                "case_id": case["case_id"],
                "draft_bundle_file": bundle.name,
                "draft_bundle_sha256": _sha(bundle),
            }
        )
        registry[case["case_id"]] = {
            "E1": {
                "catalog_evidence_id": "E1",
                "approved_purposes": ["general_semantic_annotation"],
            }
        }
    _write(draft_manifest, {"schema_version": "fixture-source-draft/v1"})
    approved_source = source_dir / "approved.json"
    approved_payload = {
        "schema_version": "ndp50-source-bundle-approved-manifest/v1",
        "status": "ready_for_independent_annotation",
        "source_bundle_draft_manifest": {
            "file": draft_manifest.name,
            "sha256": _sha(draft_manifest),
            "vocabulary_sha256": _sha(vocabulary),
        },
        "cases": approved_cases,
    }
    _write(approved_source, approved_payload)
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_semantic_gold."
        "load_approved_evidence_registry",
        lambda path: (registry, approved_payload),
    )
    monkeypatch.setattr(
        "high_fidelity_schema_study.ndp50_semantic_gold."
        "validate_consensus_artifact",
        lambda *args, **kwargs: {
            "status": "ready",
            "summary": {"unresolved_count": 0},
            "errors": [],
        },
    )
    index = build_index_template(
        packet_manifest_path=packet_manifest,
        study_root=root,
    )
    index.update(
        {
            "status": "completed_pending_validator_approval",
            "human_decisions_present": True,
            "approved_source_manifest": _ref(approved_source, root),
            "frozen_vocabulary": _ref(vocabulary, root),
            "annotator_registry": [
                {
                    "slot": "annotation_a",
                    "annotator_id": "annotator-a",
                    "reviewer_role": "scientific_metadata_curator",
                    "institution": "Example University",
                    "qualification_summary": "Scientific metadata curator.",
                    "conflict_of_interest_declared": False,
                    "developer_participation": False,
                    "signed_on": "2026-07-26",
                },
                {
                    "slot": "annotation_b",
                    "annotator_id": "annotator-b",
                    "reviewer_role": "annotation_methodologist",
                    "institution": "Example University",
                    "qualification_summary": "Annotation methodologist.",
                    "conflict_of_interest_declared": False,
                    "developer_participation": False,
                    "signed_on": "2026-07-26",
                },
            ],
            "consensus_panel": {
                "member_ids": ["annotator-a", "annotator-b"],
                "joint_human_consensus_attested": True,
                "automatic_adjudication": False,
            },
            "completion_attestation": True,
        }
    )
    for case in index["cases"]:
        case_dir = root / "semantic" / "gold" / case["case_id"]
        for key in (
            "annotation_a",
            "annotation_b",
            "disagreement_report",
            "consensus",
        ):
            annotator_id = (
                "annotator-a" if key == "annotation_a" else "annotator-b"
            )
            payload = (
                {"report": "deterministic"}
                if key == "disagreement_report"
                else {
                    "annotator_id": annotator_id,
                    "fields": [
                        {
                            "gold_evidence": [
                                {"catalog_evidence_id": "E1"}
                            ]
                        }
                    ],
                }
            )
            path = case_dir / f"{key}.json"
            _write(path, payload)
            case[key] = _ref(path, root)
    return {
        "root": root,
        "study_root": root,
        "packet_manifest_path": packet_manifest,
        "approved_source_manifest_path": approved_source,
        "vocabulary_path": vocabulary,
        "index": index,
    }


def test_neutral_index_and_workflow_contain_no_human_decisions(
    tmp_path: Path,
) -> None:
    root = tmp_path / "ndp50"
    packet = root / "semantic" / "manifest.json"
    packet_file = root / "semantic" / "packets" / "dev.json"
    _write(packet_file, {"case_id": "case-dev"})
    _write(
        packet,
        {
            "schema_version": "ndp50-semantic-packet-pack/v1",
            "status": "neutral_packets_ready_source_bundles_blocked",
            "case_count": 1,
            "cases": [
                {
                    "case_id": "case-dev",
                    "split": "development",
                    "packet_file": "packets/dev.json",
                    "packet_sha256": _sha(packet_file),
                }
            ],
        },
    )
    index_path = root / "semantic" / "gold_index.json"
    index = build_index_template(
        packet_manifest_path=packet,
        study_root=root,
    )
    _write(index_path, index)
    workflow = build_workflow_spec(
        packet_manifest_path=packet,
        index_template_path=index_path,
        study_root=root,
    )

    assert index["human_decisions_present"] is False
    assert all(
        case[key] is None
        for case in index["cases"]
        for key in (
            "annotation_a",
            "annotation_b",
            "disagreement_report",
            "consensus",
        )
    )
    assert workflow["human_decisions_present"] is False
    assert workflow["automatic_adjudication"] is False
    assert workflow["consensus_governance"][
        "mode"
    ] == "joint_consensus_by_same_qualified_annotator_pair"
    assert workflow["consensus_governance"][
        "panel_member_ids_must_equal_annotator_registry"
    ] is True


def test_valid_corpus_builds_and_replays_approval(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    index = inputs.pop("index")
    inputs.pop("root")

    report = validate_corpus_index(index, **inputs)
    approval = build_approval(index=index, **inputs)

    assert report["status"] == "passed"
    assert report["valid_case_count"] == 2
    assert report["stable_annotator_count"] == 2
    assert approval["derived_gates"]["independent_gold_complete"] is True
    assert verify_approval(approval, **inputs)["status"] == "passed"


def test_corpus_requires_stable_annotator_slots(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    index = inputs.pop("index")
    root = inputs.pop("root")
    second = index["cases"][1]["annotation_b"]
    path = root / second["file"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["annotator_id"] = "annotator-b-replacement"
    _write(path, payload)
    second["sha256"] = _sha(path)

    report = validate_corpus_index(index, **inputs)

    assert report["status"] == "blocked"
    assert "annotator_identity_not_stable" in {
        item["code"] for item in report["errors"]
    }


def test_unapproved_evidence_cannot_enter_gold(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    index = inputs.pop("index")
    root = inputs.pop("root")
    ref = index["cases"][0]["consensus"]
    path = root / ref["file"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["fields"][0]["gold_evidence"][0][
        "catalog_evidence_id"
    ] = "NOT_APPROVED"
    _write(path, payload)
    ref["sha256"] = _sha(path)

    report = validate_corpus_index(index, **inputs)

    assert report["status"] == "blocked"
    assert "unapproved_gold_evidence" in {
        item["code"] for item in report["errors"]
    }


def test_tampered_approval_fails_replay(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _fixture(tmp_path, monkeypatch)
    index = inputs.pop("index")
    inputs.pop("root")
    approval = build_approval(index=index, **inputs)
    approval["validation"]["valid_case_count"] = 999

    report = verify_approval(approval, **inputs)

    assert report["status"] == "failed"
    assert report["differing_top_level_keys"] == ["validation"]
