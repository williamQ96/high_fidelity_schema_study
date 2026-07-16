from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
from pathlib import Path
from typing import Any, Dict, Iterable, List


SCHEMA_VERSION = "semantic-power-calibration-statistics/v1"
PROTOCOL_VERSION = "semantic-architecture-protocol/v1"
EVALUATION_SCHEMA_VERSION = "minimal-architecture-experiment/v3-development"
PRIMARY_CONTRASTS = ("A_vs_B", "B_vs_C")


class CalibrationStatisticsError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _case_ids_from_manifest(manifest: Dict[str, Any]) -> List[str]:
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise CalibrationStatisticsError("calibration manifest cases are required")
    case_ids = [
        str(item.get("case_id") or "") for item in cases if isinstance(item, dict)
    ]
    if len(case_ids) != len(cases) or any(not case_id for case_id in case_ids):
        raise CalibrationStatisticsError(
            "every calibration manifest case needs a case_id"
        )
    if len(case_ids) != len(set(case_ids)):
        raise CalibrationStatisticsError("calibration manifest case_ids must be unique")
    return case_ids


def _validate_report_boundary(
    report: Dict[str, Any], manifest_case_ids: List[str]
) -> List[str]:
    if report.get("schema_version") != EVALUATION_SCHEMA_VERSION:
        raise CalibrationStatisticsError(
            f"evaluation report must use {EVALUATION_SCHEMA_VERSION}"
        )
    roles = report.get("benchmark_roles")
    if not isinstance(roles, list) or not roles:
        raise CalibrationStatisticsError(
            "evaluation report benchmark_roles are required"
        )
    if "blind_external" in roles:
        raise CalibrationStatisticsError(
            "blind_external outcomes cannot be used for power calibration"
        )
    design = report.get("case_design")
    if not isinstance(design, list) or not design:
        raise CalibrationStatisticsError("evaluation report case_design is required")
    report_case_ids = [str(item.get("case_id") or "") for item in design]
    if report_case_ids != manifest_case_ids:
        raise CalibrationStatisticsError(
            "evaluation report case order/identity differs from the calibration manifest"
        )
    opportunity_ids = [
        str(item["case_id"])
        for item in design
        if item.get("dataset_reasoning_opportunity") is True
    ]
    if not opportunity_ids:
        raise CalibrationStatisticsError(
            "calibration report contains no semantic-opportunity datasets"
        )
    replay = report.get("execution_control", {}).get("b_c_replay_provenance")
    if not isinstance(replay, list):
        raise CalibrationStatisticsError("B/C replay provenance is required")
    replay_by_case = {str(item.get("case_id") or ""): item for item in replay}
    for case_id in opportunity_ids:
        if replay_by_case.get(case_id, {}).get("valid") is not True:
            raise CalibrationStatisticsError(
                f"B/C replay is invalid or missing for calibration case {case_id}"
            )
    return opportunity_ids


def _contrast_statistics(
    comparison: Dict[str, Any], opportunity_ids: List[str], contrast: str
) -> Dict[str, Any]:
    rows = comparison.get("cases")
    if not isinstance(rows, list):
        raise CalibrationStatisticsError(f"{contrast} dataset-level cases are required")
    row_by_case = {str(item.get("case_id") or ""): item for item in rows}
    if set(row_by_case) != set(opportunity_ids) or len(rows) != len(opportunity_ids):
        raise CalibrationStatisticsError(
            f"{contrast} must contain every semantic-opportunity case exactly once"
        )
    normalized_rows = []
    effects = []
    for case_id in opportunity_ids:
        row = row_by_case[case_id]
        status = row.get("status")
        effect = row.get("correct_accepted_claim_rate_gain")
        if status == "comparable":
            if (
                not isinstance(effect, (int, float))
                or isinstance(effect, bool)
                or not -1.0 <= float(effect) <= 1.0
            ):
                raise CalibrationStatisticsError(
                    f"{contrast}/{case_id} needs a bounded paired rate effect"
                )
            effect_value = float(effect)
            effects.append(effect_value)
        else:
            if effect is not None:
                raise CalibrationStatisticsError(
                    f"{contrast}/{case_id} is non-comparable but has an effect"
                )
            effect_value = None
        normalized_rows.append(
            {
                "case_id": case_id,
                "status": status,
                "effect": effect_value,
                "reasons": list(row.get("reasons") or []),
            }
        )
    if len(effects) < 2:
        raise CalibrationStatisticsError(
            f"{contrast} needs at least two comparable calibration datasets"
        )
    return {
        "opportunity_case_count": len(opportunity_ids),
        "comparable_case_count": len(effects),
        "noncomparability_rate": round(1.0 - len(effects) / len(opportunity_ids), 8),
        "mean_paired_rate_effect": round(statistics.mean(effects), 8),
        "sample_sd_paired_rate_effect": round(statistics.stdev(effects), 8),
        "cases": normalized_rows,
    }


def build_calibration_statistics(
    *,
    evaluation_report: Dict[str, Any],
    evaluation_report_file: str,
    evaluation_report_sha256: str,
    calibration_manifest: Dict[str, Any],
    calibration_manifest_file: str,
    calibration_manifest_sha256: str,
) -> Dict[str, Any]:
    manifest_case_ids = _case_ids_from_manifest(calibration_manifest)
    opportunity_ids = _validate_report_boundary(evaluation_report, manifest_case_ids)
    comparisons = (
        evaluation_report.get("predefined_analysis_strata", {})
        .get("dataset_reasoning_opportunity", {})
        .get("dataset_level_comparison")
    )
    if not isinstance(comparisons, dict):
        raise CalibrationStatisticsError(
            "opportunity-stratum dataset_level_comparison is required"
        )
    contrast_results = {
        contrast: _contrast_statistics(
            comparisons.get(contrast, {}), opportunity_ids, contrast
        )
        for contrast in PRIMARY_CONTRASTS
    }
    implementation_path = Path(__file__).resolve()
    paired_sds = {
        contrast: contrast_results[contrast]["sample_sd_paired_rate_effect"]
        for contrast in PRIMARY_CONTRASTS
    }
    max_noncomparability = max(
        contrast_results[contrast]["noncomparability_rate"]
        for contrast in PRIMARY_CONTRASTS
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "research_evidence_status": "non_blind_power_calibration_only",
        "primary_statistical_unit": "dataset",
        "primary_outcome": "correct_accepted_applicable_claim_rate_gain_per_dataset",
        "primary_contrasts": list(PRIMARY_CONTRASTS),
        "source_artifacts": {
            "evaluation_report": {
                "file": evaluation_report_file,
                "sha256": evaluation_report_sha256,
            },
            "calibration_manifest": {
                "file": calibration_manifest_file,
                "sha256": calibration_manifest_sha256,
            },
        },
        "analysis_implementation": {
            "file": implementation_path.name,
            "sha256": sha256_file(implementation_path),
        },
        "runtime": {"python": platform.python_version()},
        "dataset_count": len(manifest_case_ids),
        "semantic_opportunity_case_count": len(opportunity_ids),
        "semantic_opportunity_rate": round(
            len(opportunity_ids) / len(manifest_case_ids), 8
        ),
        "contrasts": contrast_results,
        "recommended_power_inputs": {
            "paired_difference_sd_by_contrast": paired_sds,
            "semantic_opportunity_rate": round(
                len(opportunity_ids) / len(manifest_case_ids), 8
            ),
            "noncomparability_rate": max_noncomparability,
        },
    }


def _resolve(owner: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (owner.parent / path).resolve()


def build_calibration_statistics_from_paths(
    *, evaluation_report_path: Path, calibration_manifest_path: Path, output_path: Path
) -> Dict[str, Any]:
    evaluation_report_path = evaluation_report_path.resolve()
    calibration_manifest_path = calibration_manifest_path.resolve()
    output_parent = output_path.resolve().parent
    return build_calibration_statistics(
        evaluation_report=json.loads(
            evaluation_report_path.read_text(encoding="utf-8")
        ),
        evaluation_report_file=os.path.relpath(evaluation_report_path, output_parent),
        evaluation_report_sha256=sha256_file(evaluation_report_path),
        calibration_manifest=json.loads(
            calibration_manifest_path.read_text(encoding="utf-8")
        ),
        calibration_manifest_file=os.path.relpath(
            calibration_manifest_path, output_parent
        ),
        calibration_manifest_sha256=sha256_file(calibration_manifest_path),
    )


def validate_calibration_statistics_file(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        sources = payload.get("source_artifacts", {})
        evaluation_source = sources.get("evaluation_report", {})
        manifest_source = sources.get("calibration_manifest", {})
        evaluation_path = _resolve(path, str(evaluation_source.get("file") or ""))
        manifest_path = _resolve(path, str(manifest_source.get("file") or ""))
        for label, source_path, expected_hash in (
            ("evaluation report", evaluation_path, evaluation_source.get("sha256")),
            ("calibration manifest", manifest_path, manifest_source.get("sha256")),
        ):
            if not source_path.is_file():
                raise CalibrationStatisticsError(f"{label} is missing: {source_path}")
            actual_hash = sha256_file(source_path)
            if actual_hash != expected_hash:
                raise CalibrationStatisticsError(
                    f"{label} hash mismatch: expected {expected_hash}, got {actual_hash}"
                )
        expected = build_calibration_statistics(
            evaluation_report=json.loads(evaluation_path.read_text(encoding="utf-8")),
            evaluation_report_file=str(evaluation_source["file"]),
            evaluation_report_sha256=str(evaluation_source["sha256"]),
            calibration_manifest=json.loads(manifest_path.read_text(encoding="utf-8")),
            calibration_manifest_file=str(manifest_source["file"]),
            calibration_manifest_sha256=str(manifest_source["sha256"]),
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "blocked",
            "errors": [
                {"code": "power_calibration_statistics_invalid", "detail": str(exc)}
            ],
        }
    if payload != expected:
        differing_keys = sorted(
            key
            for key in set(payload) | set(expected)
            if payload.get(key) != expected.get(key)
        )
        return {
            "status": "blocked",
            "errors": [
                {
                    "code": "power_calibration_statistics_recalculation_mismatch",
                    "detail": f"recomputed artifact differs at keys: {differing_keys}",
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
        description="Build non-blind dataset-level statistics for power planning."
    )
    parser.add_argument("--evaluation-report", type=Path, required=True)
    parser.add_argument("--calibration-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_calibration_statistics_from_paths(
        evaluation_report_path=args.evaluation_report,
        calibration_manifest_path=args.calibration_manifest,
        output_path=args.output,
    )
    write_json(args.output, payload)
    print(json.dumps(payload["recommended_power_inputs"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
