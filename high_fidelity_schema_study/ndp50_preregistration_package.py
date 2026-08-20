from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence


SCHEMA_VERSION = "ndp50-public-preregistration-package/v1"
VALIDATION_SCHEMA_VERSION = (
    "ndp50-public-preregistration-package-validation/v1"
)
EXPECTED_TEST_DATASET_COUNT = 25
ALLOWED_TEXT_SUFFIXES = {
    ".bib",
    ".json",
    ".md",
    ".py",
    ".tex",
    ".txt",
}
REQUIRED_PUBLIC_FILES = {
    "__init__.py",
    "architecture_evaluation.py",
    "architecture_variants.py",
    "docs/ndp50_protocol_v1.md",
    "docs/ndp50_semantic_cpa_protocol_v1.md",
    "docs/ndp50_feedback_implementation_audit_v1.md",
    "docs/ndp50_feedback_improvement_amendment_v1.md",
    "docs/ndp50_initial_human_assignment_guide_v1.md",
    "docs/ndp50_statistical_analysis_plan_v1.md",
    "docs/ndp50_annotation_and_independence_plan_v1.md",
    "docs/ndp50_power_policy_review_guide_v1.md",
    "docs/ndp50_methodological_risk_register_v1.md",
    "docs/ndp50_swathi_feedback_signoff_guide_v1.md",
    "docs/semantic_annotator_calibration_protocol_v1.md",
    "docs/semantic_architecture_claim_ledger_v1.md",
    "docs/semantic_gold_workflow_protocol_v1.md",
    "docs/semantic_power_analysis_protocol_v1.md",
    "docs/swathi_feedback_response_matrix_v1.md",
    "docs/preregistration/README.md",
    "docs/preregistration/ndp50_osf_zenodo_preregistration_draft_v1.md",
    "docs/preregistration/public_package_files_v1.txt",
    "data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json",
    (
        "data/experiments/ndp50_v1/preregistration/"
        "feedback_response_signoff_neutral_v1.json"
    ),
    "data/experiments/ndp50_v1/semantic/power_feasibility_v1.json",
    (
        "data/experiments/ndp50_v1/semantic/power_freeze/"
        "power_policy_neutral_v1.json"
    ),
    (
        "data/experiments/ndp50_v1/semantic/power_freeze/"
        "power_freeze_workflow_v1.json"
    ),
    (
        "data/experiments/ndp50_v1/semantic/test_execution/"
        "test_execution_workflow_v1.json"
    ),
    "templates/ndp50_external_preregistration_receipt_template.json",
    "ndp50_assignment_distribution.py",
    "ndp50_assignment_roster.py",
    "ndp50_cpa_design.py",
    "ndp50_cpa_screen_workflow.py",
    "ndp50_data_governance.py",
    "ndp50_data_governance_review.py",
    "ndp50_demonstration_pool.py",
    "ndp50_execution_freeze.py",
    "ndp50_execution_qualification.py",
    "ndp50_human_assignments.py",
    "ndp50_human_handoff.py",
    "ndp50_power_feasibility.py",
    "ndp50_power_freeze.py",
    "ndp50_publication_gate.py",
    "ndp50_preregistration_package.py",
    "ndp50_readiness.py",
    "ndp50_semantic_gold.py",
    "ndp50_source_approval.py",
    "ndp50_test_execution.py",
    "ndp50_test_inference.py",
    "ndp50_vocabulary_workflow.py",
    "requirements-dev.txt",
    "requirements.txt",
    "semantic_annotate.py",
    "semantic_annotator_calibration.py",
    "semantic_blind_inference.py",
    "semantic_blind_sampling.py",
    "semantic_catalog_acquisition.py",
    "semantic_gold_workflow.py",
    "semantic_layer.py",
    "semantic_power_analysis.py",
    "semantic_power_calibration.py",
    "semantic_study_preflight.py",
    "unit_normalization.py",
}
FORBIDDEN_PUBLIC_PATH_PREFIXES = (
    "data/experiments/ndp50_v1/acquisition/test",
    "data/experiments/ndp50_v1/runs/test",
    "data/experiments/ndp50_v1/schemas/test",
    "data/experiments/ndp50_v1/semantic/test_execution/test_details",
    "data/experiments/ndp50_v1/semantic/test_execution/test_cases",
)
PREREGISTRATION_PATH = (
    "docs/preregistration/ndp50_osf_zenodo_preregistration_draft_v1.md"
)
DRAFT_BANNER = "**DRAFT — NOT SUBMITTED OR REGISTERED**"


class NDPPreregistrationPackageError(ValueError):
    pass


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_digest(value: Any) -> str:
    return _sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _repo_path(repo_root: Path, value: str, *, label: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or value != relative.as_posix():
        raise NDPPreregistrationPackageError(
            f"{label} must be a normalized repository-relative POSIX path"
        )
    root = repo_root.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise NDPPreregistrationPackageError(
            f"{label} escapes the repository root"
        ) from exc
    if not path.is_file():
        raise NDPPreregistrationPackageError(
            f"{label} does not exist: {value}"
        )
    return path


def load_public_file_list(
    *,
    file_list_path: Path,
    repo_root: Path,
) -> list[str]:
    try:
        relative_list_path = file_list_path.resolve().relative_to(
            repo_root.resolve()
        ).as_posix()
    except ValueError as exc:
        raise NDPPreregistrationPackageError(
            "public file list must be inside the repository root"
        ) from exc
    values = []
    for raw_line in file_list_path.read_text(encoding="utf-8").splitlines():
        value = raw_line.strip()
        if not value or value.startswith("#"):
            continue
        _repo_path(repo_root, value, label="public file")
        values.append(value)
    if values != sorted(set(values)):
        raise NDPPreregistrationPackageError(
            "public file list must be unique and lexicographically sorted"
        )
    if relative_list_path not in values:
        raise NDPPreregistrationPackageError(
            "public file list must include itself"
        )
    missing = sorted(REQUIRED_PUBLIC_FILES - set(values))
    if missing:
        raise NDPPreregistrationPackageError(
            f"required public files are missing: {missing}"
        )
    return values


def _local_python_modules(repo_root: Path) -> Dict[str, str]:
    modules: Dict[str, str] = {}
    for path in repo_root.rglob("*.py"):
        relative = path.relative_to(repo_root)
        if "__pycache__" in relative.parts:
            continue
        parts = list(relative.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        module = ".".join(parts)
        if module:
            modules[module] = relative.as_posix()
    return modules


def _imported_local_files(
    *,
    source_path: Path,
    relative_path: str,
    repo_root: Path,
    local_modules: Mapping[str, str],
) -> set[str]:
    try:
        tree = ast.parse(
            source_path.read_text(encoding="utf-8"),
            filename=relative_path,
        )
    except SyntaxError as exc:
        raise NDPPreregistrationPackageError(
            f"public Python source does not parse: {relative_path}"
        ) from exc
    current_parts = list(Path(relative_path).with_suffix("").parts)
    current_package = current_parts[:-1]
    package_name = repo_root.name
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base_parts = current_package.copy()
                for _ in range(node.level - 1):
                    if base_parts:
                        base_parts.pop()
                if node.module:
                    imported_modules.add(
                        ".".join(base_parts + node.module.split("."))
                    )
                else:
                    imported_modules.update(
                        ".".join(base_parts + alias.name.split("."))
                        for alias in node.names
                    )
            elif node.module == package_name:
                imported_modules.update(alias.name for alias in node.names)
            elif node.module and node.module.startswith(f"{package_name}."):
                imported_modules.add(
                    node.module.removeprefix(f"{package_name}.")
                )
        elif isinstance(node, ast.Import):
            imported_modules.update(
                alias.name.removeprefix(f"{package_name}.")
                for alias in node.names
                if alias.name.startswith(f"{package_name}.")
            )
    dependencies: set[str] = set()
    for module in imported_modules:
        parts = module.split(".")
        for end in range(1, len(parts) + 1):
            dependency = local_modules.get(".".join(parts[:end]))
            if dependency is not None:
                dependencies.add(dependency)
    return dependencies


def validate_public_python_import_closure(
    *,
    repo_root: Path,
    public_paths: Sequence[str],
) -> None:
    public_set = set(public_paths)
    local_modules = _local_python_modules(repo_root)
    missing_by_source: Dict[str, list[str]] = {}
    for relative_path in public_paths:
        if Path(relative_path).suffix.casefold() != ".py":
            continue
        dependencies = _imported_local_files(
            source_path=_repo_path(
                repo_root,
                relative_path,
                label="public Python source",
            ),
            relative_path=relative_path,
            repo_root=repo_root,
            local_modules=local_modules,
        )
        missing = sorted(dependencies - public_set)
        if missing:
            missing_by_source[relative_path] = missing
    if missing_by_source:
        detail = "; ".join(
            f"{source}: {dependencies}"
            for source, dependencies in sorted(missing_by_source.items())
        )
        raise NDPPreregistrationPackageError(
            "public Python source package is not closed over local imports: "
            f"{detail}"
        )


def _selected_test_identifiers(
    selection: Mapping[str, Any],
) -> tuple[list[str], list[str]]:
    if selection.get("schema_version") != "ndp50-selection/v1":
        raise NDPPreregistrationPackageError(
            "unexpected NDP-50 selection schema"
        )
    cases = [
        item
        for item in selection.get("selected_datasets") or []
        if isinstance(item, dict) and item.get("split") == "test"
    ]
    if len(cases) != EXPECTED_TEST_DATASET_COUNT:
        raise NDPPreregistrationPackageError(
            "selection must contain exactly 25 sealed test datasets"
        )
    dataset_ids = [str(item.get("dataset_id") or "") for item in cases]
    titles = [str(item.get("title") or "") for item in cases]
    if (
        any(not value for value in dataset_ids)
        or len(dataset_ids) != len(set(dataset_ids))
        or any(not value for value in titles)
    ):
        raise NDPPreregistrationPackageError(
            "sealed test identities are incomplete or duplicated"
        )
    return dataset_ids, titles


def _scan_public_text(
    *,
    relative_path: str,
    path: Path,
    dataset_ids: Sequence[str],
    titles: Sequence[str],
) -> Dict[str, Any]:
    suffix = path.suffix.casefold()
    if suffix not in ALLOWED_TEXT_SUFFIXES:
        raise NDPPreregistrationPackageError(
            f"public file is not in the auditable text-source allowlist: "
            f"{relative_path}"
        )
    for prefix in FORBIDDEN_PUBLIC_PATH_PREFIXES:
        if relative_path.casefold().startswith(prefix.casefold()):
            raise NDPPreregistrationPackageError(
                f"forbidden test-detail path in public package: "
                f"{relative_path}"
            )
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise NDPPreregistrationPackageError(
            f"public file is not valid UTF-8 text: {relative_path}"
        ) from exc
    folded = text.casefold()
    leaked_ids = [
        value for value in dataset_ids if value.casefold() in folded
    ]
    leaked_titles = [
        value
        for value in titles
        if len(value.strip()) >= 8 and value.casefold() in folded
    ]
    if leaked_ids or leaked_titles:
        raise NDPPreregistrationPackageError(
            f"sealed test identity leakage in {relative_path}: "
            f"{len(leaked_ids)} dataset IDs and "
            f"{len(leaked_titles)} titles"
        )
    return {
        "file": relative_path,
        "sha256": _sha256_file(path),
        "bytes": path.stat().st_size,
        "utf8_text_verified": True,
        "sealed_dataset_id_matches": 0,
        "sealed_title_matches": 0,
    }


def build_public_package_manifest(
    *,
    repo_root: Path,
    selection_path: Path,
    file_list_path: Path,
) -> Dict[str, Any]:
    root = repo_root.resolve()
    if not root.is_dir():
        raise NDPPreregistrationPackageError(
            "repository root does not exist"
        )
    try:
        selection_relative = selection_path.resolve().relative_to(
            root
        ).as_posix()
    except ValueError as exc:
        raise NDPPreregistrationPackageError(
            "selection must be inside the repository root"
        ) from exc
    selection = _load_json(selection_path)
    dataset_ids, titles = _selected_test_identifiers(selection)
    public_paths = load_public_file_list(
        file_list_path=file_list_path,
        repo_root=root,
    )
    validate_public_python_import_closure(
        repo_root=root,
        public_paths=public_paths,
    )
    entries = [
        _scan_public_text(
            relative_path=value,
            path=_repo_path(root, value, label="public file"),
            dataset_ids=dataset_ids,
            titles=titles,
        )
        for value in public_paths
    ]
    implementation_path = Path(__file__).resolve()
    implementation_entry = next(
        (
            item
            for item in entries
            if item["file"] == implementation_path.name
        ),
        None,
    )
    if (
        implementation_entry is None
        or implementation_entry["sha256"]
        != _sha256_file(implementation_path)
    ):
        raise NDPPreregistrationPackageError(
            "public package does not bind the exact running builder "
            "implementation"
        )
    preregistration_path = _repo_path(
        root,
        PREREGISTRATION_PATH,
        label="preregistration draft",
    )
    preregistration_text = preregistration_path.read_text(encoding="utf-8")
    draft_banner_present = DRAFT_BANNER in preregistration_text
    unresolved_marker_count = preregistration_text.count("<UNRESOLVED")
    if not draft_banner_present:
        raise NDPPreregistrationPackageError(
            "local package must retain the explicit unregistered draft banner"
        )
    if unresolved_marker_count == 0:
        raise NDPPreregistrationPackageError(
            "draft package unexpectedly contains no unresolved marker"
        )
    file_list_relative = file_list_path.resolve().relative_to(root).as_posix()
    content_projection = [
        {
            "file": item["file"],
            "sha256": item["sha256"],
            "bytes": item["bytes"],
        }
        for item in entries
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "draft_structurally_valid_not_registered",
        "authorization": {
            "external_registration_claimed": False,
            "semantic_execution_authorized": False,
            "test_release_authorized": False,
        },
        "public_scope": {
            "format": "utf8_text_source_manifest",
            "file_count": len(entries),
            "files": entries,
            "content_digest_sha256": _canonical_digest(
                content_projection
            ),
        },
        "file_list": {
            "file": file_list_relative,
            "sha256": _sha256_file(file_list_path),
        },
        "private_sealing_control": {
            "selection_file": selection_relative,
            "selection_sha256": _sha256_file(selection_path),
            "sealed_test_dataset_count": len(dataset_ids),
            "test_identities_emitted": False,
            "all_public_files_scanned": True,
            "sealed_identity_match_count": 0,
        },
        "draft_state": {
            "draft_banner_present": draft_banner_present,
            "unresolved_marker_count": unresolved_marker_count,
            "external_receipt_present": False,
            "human_signoffs_complete": False,
            "execution_freeze_complete": False,
            "power_freeze_complete": False,
        },
        "blocking_conditions": [
            "external OSF or Zenodo immutable receipt is absent",
            "required human and independent-methods sign-offs are absent",
            "execution freeze is incomplete",
            "power freeze is incomplete",
            "draft contains unresolved registration fields",
        ],
        "implementation": {
            "file": implementation_path.name,
            "sha256": _sha256_file(implementation_path),
        },
        "interpretation": (
            "This manifest proves only local text-package integrity and absence "
            "of exact sealed test IDs/titles in the listed files. It is not an "
            "external timestamp, registration receipt, legal review, semantic "
            "result, or test-release authorization."
        ),
    }


def validate_public_package_manifest(
    payload: Mapping[str, Any],
    *,
    repo_root: Path,
    selection_path: Path,
) -> Dict[str, Any]:
    try:
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise NDPPreregistrationPackageError(
                "unexpected public package schema"
            )
        file_list = payload.get("file_list")
        if not isinstance(file_list, dict):
            raise NDPPreregistrationPackageError(
                "file-list binding is missing"
            )
        file_list_path = _repo_path(
            repo_root.resolve(),
            str(file_list.get("file") or ""),
            label="file list",
        )
        if _sha256_file(file_list_path) != file_list.get("sha256"):
            raise NDPPreregistrationPackageError(
                "file-list binding does not verify"
            )
        expected = build_public_package_manifest(
            repo_root=repo_root,
            selection_path=selection_path,
            file_list_path=file_list_path,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": VALIDATION_SCHEMA_VERSION,
            "status": "failed",
            "differing_top_level_keys": [],
            "errors": [
                {
                    "code": "public_package_invalid",
                    "detail": str(exc),
                }
            ],
        }
    differing = sorted(
        key
        for key in set(payload) | set(expected)
        if payload.get(key) != expected.get(key)
    )
    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "status": "passed" if not differing else "failed",
        "differing_top_level_keys": differing,
        "errors": (
            []
            if not differing
            else [
                {
                    "code": "public_package_replay_mismatch",
                    "detail": (
                        "recomputed package differs at top-level keys: "
                        f"{differing}"
                    ),
                }
            ]
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build or replay the sealed-identity-safe NDP-50 public "
            "preregistration source manifest."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "validate"):
        command = subparsers.add_parser(name)
        command.add_argument("--repo-root", type=Path, required=True)
        command.add_argument("--selection", type=Path, required=True)
        if name == "build":
            command.add_argument("--file-list", type=Path, required=True)
            command.add_argument("--output", type=Path, required=True)
        else:
            command.add_argument("--artifact", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build":
        payload = build_public_package_manifest(
            repo_root=args.repo_root,
            selection_path=args.selection,
            file_list_path=args.file_list,
        )
        _write_json(args.output, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "file_count": payload["public_scope"]["file_count"],
                    "content_digest_sha256": payload["public_scope"][
                        "content_digest_sha256"
                    ],
                    "test_release_authorized": payload[
                        "authorization"
                    ]["test_release_authorized"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    payload = _load_json(args.artifact)
    validation = validate_public_package_manifest(
        payload,
        repo_root=args.repo_root,
        selection_path=args.selection,
    )
    print(json.dumps(validation, indent=2, sort_keys=True))
    return 0 if validation["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
