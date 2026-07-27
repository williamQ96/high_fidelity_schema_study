from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

from .ndp50_execution import ResourcePolicy


FREEZE_SCHEMA_VERSION = "ndp50-structural-validation-freeze/v1"
PREFLIGHT_SCHEMA_VERSION = "ndp50-preflight-report/v1"
PACKAGE_ROOT = Path(__file__).resolve().parent


class NDPPreflightError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def implementation_paths() -> Sequence[Path]:
    paths = [
        PACKAGE_ROOT / "models.py",
        PACKAGE_ROOT / "temporal_semantics.py",
        PACKAGE_ROOT / "unified_schema.py",
        PACKAGE_ROOT / "ndp50_study.py",
        PACKAGE_ROOT / "ndp50_execution.py",
        PACKAGE_ROOT / "ndp50_report.py",
        PACKAGE_ROOT / "ndp50_negative_controls.py",
        PACKAGE_ROOT / "ndp50_preflight.py",
    ]
    paths.extend(sorted((PACKAGE_ROOT / "extractors").glob("*.py")))
    return tuple(paths)


def _implementation_hashes() -> Dict[str, str]:
    return {
        path.relative_to(PACKAGE_ROOT).as_posix(): _sha256_file(path)
        for path in implementation_paths()
    }


def _selected_ids(selection: Mapping[str, Any]) -> Dict[str, list[str]]:
    grouped: Dict[str, list[str]] = {
        "development": [],
        "validation": [],
        "test": [],
    }
    seen = set()
    for item in selection.get("selected_datasets", []):
        dataset_id = str(item.get("dataset_id") or "")
        split = str(item.get("split") or "")
        if not dataset_id or split not in grouped:
            raise NDPPreflightError("selection contains an invalid dataset ID or split")
        if dataset_id in seen:
            raise NDPPreflightError("selection contains duplicate dataset IDs")
        seen.add(dataset_id)
        grouped[split].append(dataset_id)
    return {split: sorted(ids) for split, ids in grouped.items()}


def _assert_splits_unopened(study_root: Path, splits: Sequence[str]) -> None:
    for split in splits:
        detail_dir = study_root / "acquisition" / f"{split}_details"
        if detail_dir.exists() and any(detail_dir.glob("*.json.gz")):
            raise NDPPreflightError(
                f"{split} detail snapshots already exist before freeze"
            )


def build_validation_freeze(
    *,
    candidate_frame_path: Path,
    selection_design_path: Path,
    selection_path: Path,
    development_run_path: Path,
    negative_controls_path: Path,
    policy: ResourcePolicy,
    deviation_record_path: Path | None = None,
) -> Dict[str, Any]:
    policy.validate()
    candidate_frame = _load_json(candidate_frame_path)
    selection_design = _load_json(selection_design_path)
    selection = _load_json(selection_path)
    development_run = _load_json(development_run_path)
    negative_controls = _load_json(negative_controls_path)

    frame_hash = _sha256_file(candidate_frame_path)
    design_hash = _sha256_file(selection_design_path)
    if selection["candidate_frame"]["sha256"] != frame_hash:
        raise NDPPreflightError("selection does not bind the candidate frame")
    if selection["selection_design"]["sha256"] != design_hash:
        raise NDPPreflightError("selection does not bind the selection design")
    if selection_design["candidate_frame_sha256"] != frame_hash:
        raise NDPPreflightError("selection design does not bind the candidate frame")
    split_ids = _selected_ids(selection)
    declared_split_counts = selection_design["split_counts"]
    for split, ids in split_ids.items():
        if len(ids) != int(declared_split_counts[split]):
            raise NDPPreflightError(f"{split} count does not match the design")
    development_ids = sorted(
        str(item["dataset_id"]) for item in development_run["datasets"]
    )
    if development_ids != split_ids["development"]:
        raise NDPPreflightError(
            "development run does not exactly match the frozen development split"
        )
    if negative_controls.get("status") != "passed":
        raise NDPPreflightError("negative controls have not passed")
    study_root = selection_path.parent
    if deviation_record_path is None:
        _assert_splits_unopened(study_root, ("validation", "test"))
        held_out_state = {
            "validation_details_opened_before_freeze": False,
            "test_details_opened_before_freeze": False,
            "deviation_record": None,
        }
    else:
        if not deviation_record_path.is_file():
            raise NDPPreflightError("declared deviation record does not exist")
        _assert_splits_unopened(study_root, ("test",))
        validation_dir = study_root / "acquisition" / "validation_details"
        if not validation_dir.exists() or not any(
            validation_dir.glob("*.json.gz")
        ):
            raise NDPPreflightError(
                "deviation mode requires existing validation detail snapshots"
            )
        held_out_state = {
            "validation_details_opened_before_freeze": True,
            "test_details_opened_before_freeze": False,
            "deviation_record": {
                "file": deviation_record_path.name,
                "sha256": _sha256_file(deviation_record_path),
            },
        }

    artifact_paths = {
        "candidate_frame": candidate_frame_path,
        "selection_design": selection_design_path,
        "selection": selection_path,
        "development_run": development_run_path,
        "negative_controls": negative_controls_path,
    }
    return {
        "schema_version": FREEZE_SCHEMA_VERSION,
        "status": "frozen_after_development_before_validation",
        "frozen_at": _utc_now(),
        "claim_scope": (
            "Structural acquisition/extraction validation only. Semantic accuracy "
            "and final test execution require separate frozen gold/backend artifacts."
        ),
        "catalog_dataset_count": candidate_frame["counts"]["dataset_count"],
        "selected_dataset_ids": split_ids,
        "resource_policy": asdict(policy),
        "artifact_hashes": {
            key: {
                "file": path.name,
                "sha256": _sha256_file(path),
            }
            for key, path in artifact_paths.items()
        },
        "implementation_hashes": _implementation_hashes(),
        "held_out_state": held_out_state,
        "readiness_boundaries": {
            "structural_validation_authorized": True,
            "semantic_validation_authorized": False,
            "test_authorized": False,
            "semantic_blockers": [
                "independent semantic opportunity manifest not frozen",
                "semantic prompt and backend registry not frozen",
                "two-annotator gold workflow has not produced NDP gold",
            ],
            "test_blockers": [
                "validation has not been completed",
                "semantic study artifacts are not frozen",
            ],
        },
    }


def validate_validation_freeze(
    *,
    freeze: Mapping[str, Any],
    candidate_frame_path: Path,
    selection_design_path: Path,
    selection_path: Path,
    development_run_path: Path,
    negative_controls_path: Path,
    require_unopened: bool,
) -> Dict[str, Any]:
    checks = []

    def check(check_id: str, passed: bool, detail: str) -> None:
        checks.append({"check_id": check_id, "passed": passed, "detail": detail})

    check(
        "freeze_schema",
        freeze.get("schema_version") == FREEZE_SCHEMA_VERSION,
        str(freeze.get("schema_version")),
    )
    paths = {
        "candidate_frame": candidate_frame_path,
        "selection_design": selection_design_path,
        "selection": selection_path,
        "development_run": development_run_path,
        "negative_controls": negative_controls_path,
    }
    for key, path in paths.items():
        expected = (freeze.get("artifact_hashes") or {}).get(key, {}).get("sha256")
        actual = _sha256_file(path)
        check(f"artifact_hash:{key}", actual == expected, actual)
    current_implementation = _implementation_hashes()
    expected_implementation = freeze.get("implementation_hashes") or {}
    check(
        "implementation_hash_manifest",
        current_implementation == expected_implementation,
        f"{len(current_implementation)} source files",
    )

    selection = _load_json(selection_path)
    development = _load_json(development_run_path)
    negative = _load_json(negative_controls_path)
    split_ids = _selected_ids(selection)
    check(
        "development_identity",
        sorted(item["dataset_id"] for item in development["datasets"])
        == split_ids["development"],
        f"{len(split_ids['development'])} development IDs",
    )
    check(
        "negative_controls",
        negative.get("status") == "passed"
        and negative.get("counts", {}).get("failed_count") == 0,
        json.dumps(negative.get("counts", {}), sort_keys=True),
    )
    study_root = selection_path.parent
    try:
        _assert_splits_unopened(study_root, ("test",))
        test_unopened = True
        test_detail = "test detail snapshots absent"
    except NDPPreflightError as exc:
        test_unopened = False
        test_detail = str(exc)
    check("test_split_unopened", test_unopened, test_detail)
    if require_unopened:
        try:
            _assert_splits_unopened(study_root, ("validation",))
            unopened = True
            unopened_detail = "validation detail snapshots absent"
        except NDPPreflightError as exc:
            unopened = False
            unopened_detail = str(exc)
        check("held_out_splits_unopened", unopened, unopened_detail)

    passed_count = sum(item["passed"] for item in checks)
    all_passed = passed_count == len(checks)
    boundaries = freeze.get("readiness_boundaries") or {}
    return {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "validated_at": _utc_now(),
        "status": "passed" if all_passed else "failed",
        "counts": {
            "check_count": len(checks),
            "passed_count": passed_count,
            "failed_count": len(checks) - passed_count,
        },
        "readiness": {
            "structural_validation_ready": all_passed
            and boundaries.get("structural_validation_authorized") is True,
            "semantic_validation_ready": all_passed
            and boundaries.get("semantic_validation_authorized") is True,
            "test_ready": all_passed and boundaries.get("test_authorized") is True,
        },
        "checks": checks,
    }


def _common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--candidate-frame", type=Path, required=True)
    parser.add_argument("--selection-design", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--development-run", type=Path, required=True)
    parser.add_argument("--negative-controls", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Freeze and validate NDP-50 gates.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build-freeze")
    _common_paths(build)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--max-resources-per-dataset", type=int, default=3)
    build.add_argument("--max-bytes-per-resource", type=int, default=25 * 1024 * 1024)
    build.add_argument("--max-bytes-per-dataset", type=int, default=50 * 1024 * 1024)
    build.add_argument("--timeout-seconds", type=float, default=90.0)
    build.add_argument("--sample-limit", type=int, default=200)
    build.add_argument("--max-download-attempts", type=int, default=3)
    build.add_argument("--retry-delay-seconds", type=float, default=10.0)
    build.add_argument(
        "--validation-already-opened-under-deviation",
        type=Path,
        help="Bind a deviation record when validation details were already opened.",
    )

    validate = subparsers.add_parser("validate")
    _common_paths(validate)
    validate.add_argument("--freeze", type=Path, required=True)
    validate.add_argument("--output", type=Path, required=True)
    validate.add_argument("--require-unopened", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    common = {
        "candidate_frame_path": args.candidate_frame,
        "selection_design_path": args.selection_design,
        "selection_path": args.selection,
        "development_run_path": args.development_run,
        "negative_controls_path": args.negative_controls,
    }
    if args.command == "build-freeze":
        payload = build_validation_freeze(
            **common,
            policy=ResourcePolicy(
                max_resources_per_dataset=args.max_resources_per_dataset,
                max_bytes_per_resource=args.max_bytes_per_resource,
                max_bytes_per_dataset=args.max_bytes_per_dataset,
                timeout_seconds=args.timeout_seconds,
                sample_limit=args.sample_limit,
                max_download_attempts=args.max_download_attempts,
                retry_delay_seconds=args.retry_delay_seconds,
            ),
            deviation_record_path=args.validation_already_opened_under_deviation,
        )
    else:
        payload = validate_validation_freeze(
            freeze=_load_json(args.freeze),
            **common,
            require_unopened=args.require_unopened,
        )
    _write_json(args.output, payload)
    print(json.dumps(payload.get("counts") or payload["readiness_boundaries"], indent=2))
    return 0 if payload.get("status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
