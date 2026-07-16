from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .architecture_variants import EVALUATED_PROPERTIES
from .semantic_gold_workflow import (
    compare_independent_artifacts,
    load_json,
)


DESIGN_SCHEMA_VERSION = "semantic-annotator-calibration-design/v1"
ROUND_SCHEMA_VERSION = "semantic-annotator-calibration-round/v1"
RECEIPT_SCHEMA_VERSION = "semantic-preregistration-receipt/v1"
SUMMARY_SCHEMA_VERSION = "semantic-annotator-calibration-summary/v1"
PROTOCOL_VERSION = "semantic-architecture-protocol/v1"
MINIMUM_CASE_COUNT_FLOOR = 9
MINIMUM_OVERALL_AGREEMENT_FLOOR = 0.8
MINIMUM_APPLICABILITY_AGREEMENT_FLOOR = 0.9
MINIMUM_PROPERTY_AGREEMENT_FLOOR = 0.7
MINIMUM_CASE_AGREEMENT_FLOOR = 0.5


class AnnotatorCalibrationError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(owner: Path, raw_path: Any) -> Path:
    path = Path(str(raw_path or ""))
    if path.is_absolute():
        return path
    return (owner.resolve().parent / path).resolve()


def _check_file(owner: Path, record: Dict[str, Any], label: str) -> Path:
    path = _resolve(owner, record.get("file"))
    if not path.is_file():
        raise AnnotatorCalibrationError(f"{label} is missing: {path}")
    expected = str(record.get("sha256") or "")
    actual = sha256_file(path)
    if actual != expected:
        raise AnnotatorCalibrationError(
            f"{label} hash mismatch: expected {expected}, got {actual}"
        )
    return path


def _ratio(policy: Dict[str, Any], key: str, floor: float) -> float:
    value = policy.get(key)
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not floor <= float(value) <= 1.0
    ):
        raise AnnotatorCalibrationError(f"{key} must be in [{floor}, 1]")
    return float(value)


def _validate_threshold_policy(policy: Any) -> Dict[str, Any]:
    if not isinstance(policy, dict):
        raise AnnotatorCalibrationError("threshold_policy must be an object")
    minimum_case_count = policy.get("minimum_case_count")
    if (
        not isinstance(minimum_case_count, int)
        or isinstance(minimum_case_count, bool)
        or minimum_case_count < MINIMUM_CASE_COUNT_FLOOR
    ):
        raise AnnotatorCalibrationError(
            f"minimum_case_count must be at least {MINIMUM_CASE_COUNT_FLOOR}"
        )
    property_policy = policy.get("minimum_property_exact_label_agreement")
    if not isinstance(property_policy, dict) or set(property_policy) != set(
        EVALUATED_PROPERTIES
    ):
        raise AnnotatorCalibrationError(
            "minimum_property_exact_label_agreement must cover all four properties"
        )
    normalized_property = {
        property_name: _ratio(
            property_policy,
            property_name,
            MINIMUM_PROPERTY_AGREEMENT_FLOOR,
        )
        for property_name in EVALUATED_PROPERTIES
    }
    if policy.get("evidence_agreement_is_descriptive_only") is not True:
        raise AnnotatorCalibrationError(
            "evidence agreement must remain descriptive rather than an automatic gold gate"
        )
    return {
        "minimum_case_count": minimum_case_count,
        "minimum_overall_exact_label_agreement": _ratio(
            policy,
            "minimum_overall_exact_label_agreement",
            MINIMUM_OVERALL_AGREEMENT_FLOOR,
        ),
        "minimum_applicability_agreement": _ratio(
            policy,
            "minimum_applicability_agreement",
            MINIMUM_APPLICABILITY_AGREEMENT_FLOOR,
        ),
        "minimum_case_exact_label_agreement": _ratio(
            policy,
            "minimum_case_exact_label_agreement",
            MINIMUM_CASE_AGREEMENT_FLOOR,
        ),
        "minimum_property_exact_label_agreement": normalized_property,
        "evidence_agreement_is_descriptive_only": True,
    }


def _validate_registration(
    round_manifest: Path, receipt: Any, design_sha256: str
) -> Dict[str, Any]:
    if not isinstance(receipt, dict):
        raise AnnotatorCalibrationError("registration_receipt must be an object")
    receipt_path = _check_file(round_manifest, receipt, "registration receipt")
    registration = load_json(receipt_path)
    if registration.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise AnnotatorCalibrationError("registration receipt schema is invalid")
    if registration.get("design_sha256") != design_sha256:
        raise AnnotatorCalibrationError(
            "registration receipt does not bind the frozen design hash"
        )
    for key in ("registered_at", "registry", "registration_identifier"):
        if not str(registration.get(key) or "").strip():
            raise AnnotatorCalibrationError(f"registration receipt {key} is required")
    if registration.get("frozen_before_first_submission") is not True:
        raise AnnotatorCalibrationError(
            "receipt must state frozen_before_first_submission=true"
        )
    return {
        "registered_at": registration["registered_at"],
        "registry": registration["registry"],
        "registration_identifier": registration["registration_identifier"],
        "frozen_before_first_submission": True,
        "receipt": {
            "file": str(receipt["file"]),
            "sha256": sha256_file(receipt_path),
        },
    }


def _validate_workflow(workflow_path: Path, workflow: Dict[str, Any]) -> None:
    if workflow.get("schema_version") != "semantic-annotation-workflow-manifest/v1":
        raise AnnotatorCalibrationError("invalid annotation workflow schema")
    if workflow.get("benchmark_role") != "annotator_calibration":
        raise AnnotatorCalibrationError("workflow must be annotator_calibration")
    independence = workflow.get("independence_policy", {})
    expected_independence = {
        "annotator_count": 2,
        "developer_participation": False,
        "model_outputs_visible": False,
        "other_annotation_visible_before_freeze": False,
        "comparison_only_after_both_validate": True,
    }
    if independence != expected_independence:
        raise AnnotatorCalibrationError("workflow independence policy is invalid")
    for label, file_key, hash_key in (
        (
            "calibration manifest",
            "calibration_manifest_file",
            "calibration_manifest_sha256",
        ),
        ("vocabulary", "vocabulary_file", "vocabulary_sha256"),
        ("handbook", "handbook_file", "handbook_sha256"),
        (
            "workflow implementation",
            "workflow_implementation_file",
            "workflow_implementation_sha256",
        ),
    ):
        _check_file(
            workflow_path,
            {"file": workflow.get(file_key), "sha256": workflow.get(hash_key)},
            label,
        )


def _prior_round_case_ids(design_path: Path, payload: Dict[str, Any]) -> set[str]:
    round_index = payload.get("round_index")
    prior = payload.get("prior_round_summary")
    if round_index == 1:
        if prior is not None:
            raise AnnotatorCalibrationError("round 1 cannot have a prior round summary")
        return set()
    if (
        not isinstance(round_index, int)
        or isinstance(round_index, bool)
        or round_index < 2
    ):
        raise AnnotatorCalibrationError("round_index must be a positive integer")
    if not isinstance(prior, dict):
        raise AnnotatorCalibrationError("later rounds require prior_round_summary")
    prior_path = _check_file(design_path, prior, "prior round summary")
    prior_payload = load_json(prior_path)
    if prior_payload.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        raise AnnotatorCalibrationError("prior round summary schema is invalid")
    if prior_payload.get("status") != "failed":
        raise AnnotatorCalibrationError(
            "a new calibration round is allowed only after a failed prior round"
        )
    if prior_payload.get("round_index") != round_index - 1:
        raise AnnotatorCalibrationError("prior round index is not consecutive")
    return set(str(item) for item in prior_payload.get("case_ids", []))


def _load_validated_design(design_path: Path) -> Dict[str, Any]:
    design_path = design_path.resolve()
    payload = load_json(design_path)
    if payload.get("schema_version") != DESIGN_SCHEMA_VERSION:
        raise AnnotatorCalibrationError(f"expected {DESIGN_SCHEMA_VERSION}")
    if payload.get("protocol_version") != PROTOCOL_VERSION:
        raise AnnotatorCalibrationError(f"expected {PROTOCOL_VERSION}")
    if payload.get("status") != "frozen_before_submissions":
        raise AnnotatorCalibrationError(
            "calibration design must be frozen_before_submissions"
        )
    if not str(payload.get("round_id") or "").strip():
        raise AnnotatorCalibrationError("round_id is required")
    if not isinstance(payload.get("round_index"), int) or isinstance(
        payload.get("round_index"), bool
    ):
        raise AnnotatorCalibrationError("round_index must be an integer")
    prior_case_ids = _prior_round_case_ids(design_path, payload)
    thresholds = _validate_threshold_policy(payload.get("threshold_policy"))
    workflow_record = payload.get("workflow_manifest")
    if not isinstance(workflow_record, dict):
        raise AnnotatorCalibrationError("workflow_manifest must be an object")
    workflow_path = _check_file(
        design_path, workflow_record, "annotation workflow manifest"
    )
    workflow = load_json(workflow_path)
    _validate_workflow(workflow_path, workflow)
    workflow_cases = workflow.get("cases")
    if not isinstance(workflow_cases, list):
        raise AnnotatorCalibrationError("workflow cases are required")
    workflow_case_ids = [str(item.get("case_id") or "") for item in workflow_cases]
    if any(not case_id for case_id in workflow_case_ids) or len(
        workflow_case_ids
    ) != len(set(workflow_case_ids)):
        raise AnnotatorCalibrationError("workflow case IDs must be present and unique")
    if len(workflow_case_ids) < thresholds["minimum_case_count"]:
        raise AnnotatorCalibrationError(
            "workflow contains fewer cases than the frozen minimum"
        )
    reused = prior_case_ids & set(workflow_case_ids)
    if reused:
        raise AnnotatorCalibrationError(
            f"revealed calibration cases cannot be reused in a new round: {sorted(reused)}"
        )
    return {
        "payload": payload,
        "thresholds": thresholds,
        "workflow_path": workflow_path,
        "workflow": workflow,
        "workflow_cases": workflow_cases,
        "workflow_case_ids": workflow_case_ids,
    }


def preflight_annotator_calibration_design(design_path: Path) -> Dict[str, Any]:
    try:
        validated = _load_validated_design(design_path)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [
                {
                    "code": "annotator_calibration_design_invalid",
                    "detail": str(exc),
                }
            ],
        }
    payload = validated["payload"]
    workflow_path = validated["workflow_path"]
    return {
        "status": "ready_for_external_registration",
        "errors": [],
        "design": {
            "file": str(design_path.resolve()),
            "sha256": sha256_file(design_path.resolve()),
            "round_id": payload["round_id"],
            "round_index": payload["round_index"],
        },
        "workflow": {
            "file": str(workflow_path),
            "sha256": sha256_file(workflow_path),
            "case_count": len(validated["workflow_case_ids"]),
            "case_ids": validated["workflow_case_ids"],
        },
        "threshold_policy": validated["thresholds"],
        "next_action": (
            "register the exact design SHA-256 in an external append-only registry "
            "before either annotator creates a submission"
        ),
        "not_a_registration_receipt": True,
    }


def _gate_check(
    check_id: str, observed: float | int, threshold: float | int
) -> Dict[str, Any]:
    return {
        "check_id": check_id,
        "observed": observed,
        "minimum": threshold,
        "passed": observed >= threshold,
    }


def build_annotator_calibration_summary(
    *, round_manifest_path: Path, output_path: Path
) -> Dict[str, Any]:
    round_manifest_path = round_manifest_path.resolve()
    round_payload = load_json(round_manifest_path)
    if round_payload.get("schema_version") != ROUND_SCHEMA_VERSION:
        raise AnnotatorCalibrationError(f"expected {ROUND_SCHEMA_VERSION}")
    if round_payload.get("protocol_version") != PROTOCOL_VERSION:
        raise AnnotatorCalibrationError(f"expected {PROTOCOL_VERSION}")
    if round_payload.get("status") != "submissions_frozen":
        raise AnnotatorCalibrationError(
            "calibration round status must be submissions_frozen"
        )
    design_record = round_payload.get("design")
    if not isinstance(design_record, dict):
        raise AnnotatorCalibrationError("round manifest design must be an object")
    design_path = _check_file(
        round_manifest_path, design_record, "annotator calibration design"
    )
    design_sha256 = sha256_file(design_path)
    validated_design = _load_validated_design(design_path)
    payload = validated_design["payload"]
    registration = _validate_registration(
        round_manifest_path,
        round_payload.get("registration_receipt"),
        design_sha256,
    )
    thresholds = validated_design["thresholds"]
    workflow_path = validated_design["workflow_path"]
    workflow = validated_design["workflow"]
    workflow_cases = validated_design["workflow_cases"]
    workflow_case_ids = validated_design["workflow_case_ids"]

    round_cases = round_payload.get("cases")
    if not isinstance(round_cases, list):
        raise AnnotatorCalibrationError("round cases are required")
    round_case_ids = [str(item.get("case_id") or "") for item in round_cases]
    if round_case_ids != workflow_case_ids:
        raise AnnotatorCalibrationError(
            "round case order/identity must exactly match the workflow manifest"
        )
    vocabulary_path = _resolve(workflow_path, workflow["vocabulary_file"])
    workflow_by_case = {str(item["case_id"]): item for item in workflow_cases}

    total_slots = 0
    total_agreed = 0
    total_evidence_agreed = 0
    applicability_agreed = 0
    property_counts = {
        property_name: {"agreed": 0, "total": 0}
        for property_name in EVALUATED_PROPERTIES
    }
    annotator_pair: Tuple[str, str] | None = None
    case_results: List[Dict[str, Any]] = []
    for round_case in round_cases:
        case_id = str(round_case["case_id"])
        workflow_case = workflow_by_case[case_id]
        packet_path = _check_file(
            workflow_path,
            {
                "file": workflow_case["packet_file"],
                "sha256": workflow_case["packet_sha256"],
            },
            f"{case_id} packet",
        )
        source_bundle_path = _check_file(
            workflow_path,
            {
                "file": workflow_case["source_bundle_file"],
                "sha256": workflow_case["source_bundle_sha256"],
            },
            f"{case_id} source bundle",
        )
        independent = round_case.get("independent_annotations")
        if not isinstance(independent, list) or len(independent) != 2:
            raise AnnotatorCalibrationError(
                f"{case_id} requires exactly two independent annotations"
            )
        artifact_paths = [
            _check_file(
                round_manifest_path, record, f"{case_id} independent annotation"
            )
            for record in independent
        ]
        disagreement_record = round_case.get("disagreement_report")
        if not isinstance(disagreement_record, dict):
            raise AnnotatorCalibrationError(
                f"{case_id} disagreement_report must be an object"
            )
        disagreement_path = _check_file(
            round_manifest_path,
            disagreement_record,
            f"{case_id} disagreement report",
        )
        expected = compare_independent_artifacts(
            artifact_paths[0],
            artifact_paths[1],
            packet_path=packet_path,
            source_bundle_path=source_bundle_path,
            vocabulary_path=vocabulary_path,
        )
        observed = load_json(disagreement_path)
        if observed != expected:
            raise AnnotatorCalibrationError(
                f"{case_id} disagreement report is not a deterministic rebuild"
            )
        current_pair = tuple(
            sorted(
                str(item["annotator_id"]) for item in observed["independent_artifacts"]
            )
        )
        if annotator_pair is None:
            annotator_pair = current_pair
        elif current_pair != annotator_pair:
            raise AnnotatorCalibrationError(
                "the same two annotators must complete every calibration case"
            )
        slots = int(observed["slot_count"])
        agreed = int(observed["agreed_slot_count"])
        evidence_agreed = round(
            float(observed["exact_evidence_agreement_rate"]) * slots
        )
        applicability_disagreements = sum(
            item["disagreement_type"] in {"applicability", "applicability_and_value"}
            for item in observed["disagreements"]
        )
        total_slots += slots
        total_agreed += agreed
        total_evidence_agreed += evidence_agreed
        applicability_agreed += slots - applicability_disagreements
        for property_name in EVALUATED_PROPERTIES:
            item = observed["agreement_by_property"][property_name]
            property_counts[property_name]["agreed"] += int(item["agreed"])
            property_counts[property_name]["total"] += int(item["total"])
        case_results.append(
            {
                "case_id": case_id,
                "slot_count": slots,
                "exact_label_agreement_rate": observed["exact_label_agreement_rate"],
                "exact_evidence_agreement_rate": observed[
                    "exact_evidence_agreement_rate"
                ],
                "applicability_agreement_rate": (
                    (slots - applicability_disagreements) / slots if slots else None
                ),
                "disagreement_report_sha256": sha256_file(disagreement_path),
            }
        )

    overall_rate = total_agreed / total_slots
    applicability_rate = applicability_agreed / total_slots
    property_metrics = {
        property_name: {
            **counts,
            "exact_label_agreement_rate": counts["agreed"] / counts["total"],
        }
        for property_name, counts in property_counts.items()
    }
    checks = [
        _gate_check("case_count", len(case_results), thresholds["minimum_case_count"]),
        _gate_check(
            "overall_exact_label_agreement",
            overall_rate,
            thresholds["minimum_overall_exact_label_agreement"],
        ),
        _gate_check(
            "applicability_agreement",
            applicability_rate,
            thresholds["minimum_applicability_agreement"],
        ),
    ]
    checks.extend(
        _gate_check(
            f"property_exact_label_agreement:{property_name}",
            property_metrics[property_name]["exact_label_agreement_rate"],
            thresholds["minimum_property_exact_label_agreement"][property_name],
        )
        for property_name in EVALUATED_PROPERTIES
    )
    checks.extend(
        _gate_check(
            f"case_exact_label_agreement:{item['case_id']}",
            item["exact_label_agreement_rate"],
            thresholds["minimum_case_exact_label_agreement"],
        )
        for item in case_results
    )
    passed = all(item["passed"] for item in checks)
    implementation_path = Path(__file__).resolve()
    output_parent = output_path.resolve().parent
    round_relative = Path(
        os.path.relpath(round_manifest_path, output_parent)
    ).as_posix()
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "research_evidence_status": "non_blind_annotator_calibration_only",
        "status": "passed" if passed else "failed",
        "round_id": payload["round_id"],
        "round_index": payload["round_index"],
        "source_round_manifest": {
            "file": round_relative,
            "sha256": sha256_file(round_manifest_path),
        },
        "source_design": {
            "file": str(design_record["file"]),
            "sha256": design_sha256,
        },
        "workflow_manifest_sha256": sha256_file(workflow_path),
        "qualified_handbook_sha256": workflow["handbook_sha256"],
        "qualified_vocabulary_sha256": workflow["vocabulary_sha256"],
        "registration": registration,
        "threshold_policy": thresholds,
        "annotator_ids": list(annotator_pair or ()),
        "case_ids": workflow_case_ids,
        "metrics": {
            "case_count": len(case_results),
            "slot_count": total_slots,
            "agreed_slot_count": total_agreed,
            "exact_label_agreement_rate": overall_rate,
            "applicability_agreement_rate": applicability_rate,
            "exact_evidence_agreement_rate": total_evidence_agreed / total_slots,
            "agreement_by_property": property_metrics,
        },
        "gate_checks": checks,
        "case_results": case_results,
        "next_action": (
            "qualified versions may be frozen for blind annotation"
            if passed
            else "revise instructions or vocabulary, then preregister a new round with entirely new calibration cases"
        ),
        "analysis_implementation": {
            "file": implementation_path.name,
            "sha256": sha256_file(implementation_path),
        },
    }


def validate_annotator_calibration_summary(path: Path) -> Dict[str, Any]:
    try:
        payload = load_json(path)
        source = payload.get("source_round_manifest")
        if not isinstance(source, dict):
            raise AnnotatorCalibrationError("source_round_manifest is required")
        round_path = _check_file(path, source, "source round manifest")
        expected = build_annotator_calibration_summary(
            round_manifest_path=round_path,
            output_path=path,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [
                {"code": "annotator_calibration_summary_invalid", "detail": str(exc)}
            ],
        }
    if payload != expected:
        differing = sorted(
            key
            for key in set(payload) | set(expected)
            if payload.get(key) != expected.get(key)
        )
        return {
            "status": "blocked",
            "errors": [
                {
                    "code": "annotator_calibration_summary_recalculation_mismatch",
                    "detail": f"recomputed artifact differs at keys: {differing}",
                }
            ],
        }
    return {"status": "ready", "errors": [], "payload": payload}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or validate the frozen two-annotator calibration gate."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight = subparsers.add_parser("preflight-design")
    preflight.add_argument("--design", type=Path, required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--round-manifest", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--artifact", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "preflight-design":
        report = preflight_annotator_calibration_design(args.design)
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if report["status"] == "ready_for_external_registration" else 1
    if args.command == "build":
        payload = build_annotator_calibration_summary(
            round_manifest_path=args.round_manifest,
            output_path=args.output,
        )
        write_json(args.output, payload)
        print(json.dumps({"status": payload["status"], "metrics": payload["metrics"]}))
        return 0 if payload["status"] == "passed" else 2
    report = validate_annotator_calibration_summary(args.artifact)
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
