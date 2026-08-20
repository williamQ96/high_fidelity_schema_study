from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any, Dict, Iterable, Mapping

from .ndp50_preregistration_package import (
    _scan_public_text,
    _selected_test_identifiers,
    validate_public_package_manifest,
)


SPEC_SCHEMA_VERSION = "ndp50-human-assignment-distribution-spec/v1"
PACKET_MANIFEST_SCHEMA_VERSION = (
    "ndp50-human-assignment-distribution-packet/v1"
)
RECEIPT_SCHEMA_VERSION = (
    "ndp50-human-assignment-distribution-receipt/v1"
)
VALIDATION_SCHEMA_VERSION = (
    "ndp50-human-assignment-distribution-validation/v1"
)
RELEASE_SCHEMA_VERSION = "ndp50-human-assignment-release/v1"
PUBLIC_PACKAGE_SCHEMA_VERSION = "ndp50-public-preregistration-package/v1"
ASSIGNMENT_IDS = (
    "data_governance_review",
    "feedback_response_signoff",
    "vocabulary_discovery_a",
    "vocabulary_discovery_b",
)
PACKET_ROSTER_SLOTS = {
    "data_governance_review": [
        "governance_stewardship",
        "governance_accountable_approval",
    ],
    "feedback_response_signoff": ["feedback_response_signoff"],
    "vocabulary_discovery_a": ["vocabulary_discovery_a"],
    "vocabulary_discovery_b": ["vocabulary_discovery_b"],
}
PACKET_DIRECTORY_NAMES = {
    "data_governance_review": "governance",
    "feedback_response_signoff": "feedback",
    "vocabulary_discovery_a": "vocab-a",
    "vocabulary_discovery_b": "vocab-b",
}


class NDPAssignmentDistributionError(ValueError):
    pass


def _filesystem_path(path: Path) -> Path:
    resolved = path.resolve()
    if os.name != "nt":
        return resolved
    value = str(resolved)
    if value.startswith("\\\\?\\"):
        return resolved
    if value.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + value.removeprefix("\\\\"))
    return Path("\\\\?\\" + value)


def _repository_boundary(repo_root: Path) -> Path:
    resolved = repo_root.resolve()
    for candidate in (resolved, *resolved.parents):
        metadata = candidate / ".git"
        if metadata.is_file() or (
            metadata.is_dir()
            and (
                (metadata / "HEAD").is_file()
                or (metadata / "config").is_file()
            )
        ):
            return candidate
    return resolved


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(
        _filesystem_path(path).read_text(encoding="utf-8")
    )


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    filesystem_path = _filesystem_path(path)
    filesystem_path.parent.mkdir(parents=True, exist_ok=True)
    filesystem_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with _filesystem_path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()


def _relative_file(path: Path, root: Path, *, label: str) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise NDPAssignmentDistributionError(
            f"{label} must be inside {root}"
        ) from exc


def _binding(path: Path, root: Path) -> Dict[str, str]:
    return {
        "file": _relative_file(path, root, label="bound file"),
        "sha256": _sha256_file(path),
    }


def _resolve_binding(
    binding: Any,
    *,
    root: Path,
    label: str,
) -> Path:
    if not isinstance(binding, Mapping):
        raise NDPAssignmentDistributionError(f"{label} binding is missing")
    value = binding.get("file")
    digest = binding.get("sha256")
    if not isinstance(value, str) or not value:
        raise NDPAssignmentDistributionError(
            f"{label} binding file is missing"
        )
    relative = Path(value)
    if relative.is_absolute() or value != relative.as_posix():
        raise NDPAssignmentDistributionError(
            f"{label} binding must use a normalized relative POSIX path"
        )
    path = (root.resolve() / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise NDPAssignmentDistributionError(
            f"{label} binding escapes its root"
        ) from exc
    if not path.is_file() or _sha256_file(path) != digest:
        raise NDPAssignmentDistributionError(
            f"{label} binding is missing or stale"
        )
    return path


def _file_entry(
    *,
    path: Path,
    repo_root: Path,
    scope: str,
) -> Dict[str, Any]:
    filesystem_path = _filesystem_path(path)
    return {
        "file": _relative_file(path, repo_root, label="packet file"),
        "sha256": _sha256_file(path),
        "bytes": filesystem_path.stat().st_size,
        "scope": scope,
    }


def _add_file(
    entries: Dict[str, Dict[str, Any]],
    *,
    path: Path,
    repo_root: Path,
    scope: str,
) -> None:
    entry = _file_entry(path=path, repo_root=repo_root, scope=scope)
    existing = entries.get(entry["file"])
    if existing is not None:
        if (
            existing["sha256"] != entry["sha256"]
            or existing["bytes"] != entry["bytes"]
        ):
            raise NDPAssignmentDistributionError(
                f"conflicting packet file binding: {entry['file']}"
            )
        return
    entries[entry["file"]] = entry


def _source_bundle_files(manifest_path: Path) -> list[Path]:
    manifest = _load_json(manifest_path)
    if (
        manifest.get("schema_version")
        != "ndp50-source-bundle-draft-manifest/v1"
    ):
        raise NDPAssignmentDistributionError(
            "unexpected source-bundle manifest schema"
        )
    paths = []
    for case in manifest.get("cases") or []:
        if not isinstance(case, Mapping):
            raise NDPAssignmentDistributionError(
                "source-bundle case must be an object"
            )
        value = case.get("bundle_file")
        digest = case.get("bundle_sha256")
        if not isinstance(value, str) or not value:
            raise NDPAssignmentDistributionError(
                "source-bundle file is missing"
            )
        path = (manifest_path.parent / value).resolve()
        if (
            not path.is_file()
            or _sha256_file(path) != digest
            or path.parent != manifest_path.parent.resolve()
        ):
            raise NDPAssignmentDistributionError(
                f"source-bundle file is missing or stale: {value}"
            )
        paths.append(path)
    if len(paths) != manifest.get("case_count") or not paths:
        raise NDPAssignmentDistributionError(
            "source-bundle case count is inconsistent"
        )
    return paths


def _validate_public_manifest(
    *,
    public_manifest_path: Path,
    selection_path: Path,
    repo_root: Path,
) -> Dict[str, Any]:
    manifest = _load_json(public_manifest_path)
    validation = validate_public_package_manifest(
        manifest,
        repo_root=repo_root,
        selection_path=selection_path,
    )
    if validation.get("status") != "passed":
        raise NDPAssignmentDistributionError(
            "public package manifest does not replay"
        )
    if (
        manifest.get("schema_version") != PUBLIC_PACKAGE_SCHEMA_VERSION
        or manifest.get("status")
        != "draft_structurally_valid_not_registered"
        or manifest.get("authorization", {}).get("test_release_authorized")
        is not False
    ):
        raise NDPAssignmentDistributionError(
            "public package has an invalid pre-test state"
        )
    return manifest


def build_distribution_spec(
    *,
    assignment_release_path: Path,
    public_manifest_path: Path,
    selection_path: Path,
    study_root: Path,
    repo_root: Path,
) -> Dict[str, Any]:
    repo_root = repo_root.resolve()
    study_root = study_root.resolve()
    if not repo_root.is_dir() or not study_root.is_relative_to(repo_root):
        raise NDPAssignmentDistributionError(
            "study root must be inside the repository root"
        )
    release = _load_json(assignment_release_path)
    if (
        release.get("schema_version") != RELEASE_SCHEMA_VERSION
        or release.get("status") != "released_unassigned"
        or release.get("assignment_count") != 4
        or sorted((release.get("assignments") or {}).keys())
        != sorted(ASSIGNMENT_IDS)
    ):
        raise NDPAssignmentDistributionError(
            "assignment release is not the expected neutral four-packet release"
        )
    public_manifest = _validate_public_manifest(
        public_manifest_path=public_manifest_path,
        selection_path=selection_path,
        repo_root=repo_root,
    )
    public_entries = {
        item["file"]: {
            "file": item["file"],
            "sha256": item["sha256"],
            "bytes": item["bytes"],
            "scope": "public_source_base",
        }
        for item in public_manifest.get("public_scope", {}).get("files") or []
    }
    if len(public_entries) != public_manifest.get("public_scope", {}).get(
        "file_count"
    ):
        raise NDPAssignmentDistributionError(
            "public package file count is inconsistent"
        )
    packets: Dict[str, Any] = {}
    all_assignment_files = {
        assignment_id: _resolve_binding(
            release["assignments"][assignment_id],
            root=study_root,
            label=f"{assignment_id} wrapper",
        )
        for assignment_id in ASSIGNMENT_IDS
    }
    for assignment_id in ASSIGNMENT_IDS:
        wrapper_path = all_assignment_files[assignment_id]
        wrapper = _load_json(wrapper_path)
        if (
            wrapper.get("schema_version") != "ndp50-human-assignment/v1"
            or wrapper.get("assignment_id") != assignment_id
            or wrapper.get("release_state") != "ready_unassigned"
            or wrapper.get("reviewer_id") is not None
            or wrapper.get("test_data_access") != "forbidden"
        ):
            raise NDPAssignmentDistributionError(
                f"{assignment_id} wrapper is not neutral and releasable"
            )
        entries = dict(public_entries)
        _add_file(
            entries,
            path=public_manifest_path,
            repo_root=repo_root,
            scope="public_manifest",
        )
        _add_file(
            entries,
            path=assignment_release_path,
            repo_root=repo_root,
            scope="assignment_release",
        )
        _add_file(
            entries,
            path=wrapper_path,
            repo_root=repo_root,
            scope="assignment_wrapper",
        )
        payload_path = _resolve_binding(
            wrapper.get("payload"),
            root=study_root,
            label=f"{assignment_id} payload",
        )
        _add_file(
            entries,
            path=payload_path,
            repo_root=repo_root,
            scope="assignment_payload",
        )
        source_bundle_manifest = None
        for label, binding in sorted(
            (wrapper.get("released_inputs") or {}).items()
        ):
            path = _resolve_binding(
                binding,
                root=study_root,
                label=f"{assignment_id} released input {label}",
            )
            _add_file(
                entries,
                path=path,
                repo_root=repo_root,
                scope=f"released_input:{label}",
            )
            if label == "source_bundle_manifest":
                source_bundle_manifest = path
        if source_bundle_manifest is not None:
            for path in _source_bundle_files(source_bundle_manifest):
                _add_file(
                    entries,
                    path=path,
                    repo_root=repo_root,
                    scope="released_source_bundle",
                )
        files = [entries[key] for key in sorted(entries)]
        forbidden = []
        for other_id, other_path in all_assignment_files.items():
            if other_id == assignment_id:
                continue
            forbidden.append(
                _relative_file(
                    other_path,
                    repo_root,
                    label="forbidden assignment wrapper",
                )
            )
            other_wrapper = _load_json(other_path)
            other_payload = _resolve_binding(
                other_wrapper.get("payload"),
                root=study_root,
                label=f"{other_id} payload",
            )
            forbidden.append(
                _relative_file(
                    other_payload,
                    repo_root,
                    label="forbidden assignment payload",
                )
            )
        packets[assignment_id] = {
            "assignment_id": assignment_id,
            "packet_directory": PACKET_DIRECTORY_NAMES[assignment_id],
            "roster_slots": PACKET_ROSTER_SLOTS[assignment_id],
            "status": "specified_unmaterialized",
            "reviewer_ids_present": False,
            "human_decisions_present": False,
            "test_data_access": "forbidden",
            "extra_files_forbidden": True,
            "sealed_identity_scan_required": True,
            "forbidden_assignment_files": sorted(set(forbidden)),
            "file_count": len(files),
            "content_digest_sha256": _canonical_digest(
                [
                    {
                        "file": item["file"],
                        "sha256": item["sha256"],
                        "bytes": item["bytes"],
                    }
                    for item in files
                ]
            ),
            "files": files,
        }
    implementation = Path(__file__).resolve()
    return {
        "schema_version": SPEC_SCHEMA_VERSION,
        "status": "neutral_packets_specified_unmaterialized",
        "assignment_release": _binding(
            assignment_release_path,
            study_root,
        ),
        "public_package_manifest": _binding(
            public_manifest_path,
            repo_root,
        ),
        "public_package_content_digest_sha256": public_manifest[
            "public_scope"
        ]["content_digest_sha256"],
        "packet_root_directory_name": repo_root.name,
        "packet_count": len(packets),
        "packets": packets,
        "distribution_invariants": {
            "packet_roots_must_be_outside_repository": True,
            "packet_file_sets_are_exact": True,
            "extra_files_are_forbidden": True,
            "sealed_test_ids_and_titles_are_scanned": True,
            "vocabulary_reviewers_receive_distinct_wrappers": True,
            "vocabulary_payloads_remain_byte_identical": True,
            "reviewer_ids_present": False,
            "human_decisions_present": False,
        },
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
        "implementation_dependencies": {
            "ndp50_preregistration_package.py": _sha256_file(
                implementation.with_name("ndp50_preregistration_package.py")
            )
        },
    }


def _packet_manifest(
    *,
    spec_path: Path,
    packet: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "schema_version": PACKET_MANIFEST_SCHEMA_VERSION,
        "status": "materialized_unassigned",
        "assignment_id": packet["assignment_id"],
        "distribution_spec_sha256": _sha256_file(spec_path),
        "roster_slots": packet["roster_slots"],
        "reviewer_ids_present": False,
        "human_decisions_present": False,
        "test_data_access": "forbidden",
        "file_count": packet["file_count"],
        "content_digest_sha256": packet["content_digest_sha256"],
        "files": packet["files"],
    }


def _ensure_external_empty_root(
    *,
    packet_root: Path,
    repo_root: Path,
) -> None:
    resolved = packet_root.resolve()
    repository = _repository_boundary(repo_root)
    try:
        resolved.relative_to(repository)
    except ValueError:
        pass
    else:
        raise NDPAssignmentDistributionError(
            "packet root must be outside the repository"
        )
    if resolved.exists() and any(resolved.iterdir()):
        raise NDPAssignmentDistributionError(
            "packet root must not exist or must be empty"
        )
    resolved.mkdir(parents=True, exist_ok=True)


def _inspect_materialized_packets(
    *,
    spec: Mapping[str, Any],
    spec_path: Path,
    selection_path: Path,
    packet_root: Path,
    repo_root: Path,
) -> Dict[str, Any]:
    selection = _load_json(selection_path)
    dataset_ids, titles = _selected_test_identifiers(selection)
    packet_ids_by_directory = {
        packet["packet_directory"]: packet_id
        for packet_id, packet in spec["packets"].items()
    }
    if len(packet_ids_by_directory) != len(spec["packets"]):
        raise NDPAssignmentDistributionError(
            "packet directory names must be unique"
        )
    expected_packet_ids = set(packet_ids_by_directory)
    actual_packet_ids = {
        path.name for path in packet_root.iterdir() if path.is_dir()
    }
    actual_root_files = {
        path.name for path in packet_root.iterdir() if path.is_file()
    }
    if actual_packet_ids != expected_packet_ids or actual_root_files:
        raise NDPAssignmentDistributionError(
            "materialized packet root has missing or extra entries"
        )
    receipt_packets: Dict[str, Any] = {}
    package_directory_name = spec["packet_root_directory_name"]
    for packet_id, packet in sorted(spec["packets"].items()):
        packet_directory = packet_root / packet["packet_directory"]
        package_root = packet_directory / package_directory_name
        manifest_path = packet_directory / "packet_manifest.json"
        if not package_root.is_dir() or not manifest_path.is_file():
            raise NDPAssignmentDistributionError(
                f"{packet_id} packet layout is incomplete"
            )
        if {
            path.name for path in packet_directory.iterdir()
        } != {package_directory_name, "packet_manifest.json"}:
            raise NDPAssignmentDistributionError(
                f"{packet_id} packet layout has extra entries"
            )
        expected_files = {
            item["file"]: item for item in packet["files"]
        }
        filesystem_package_root = _filesystem_path(package_root)
        actual_files = {
            path.relative_to(filesystem_package_root).as_posix()
            for path in filesystem_package_root.rglob("*")
            if path.is_file()
        }
        if actual_files != set(expected_files):
            raise NDPAssignmentDistributionError(
                f"{packet_id} contains missing or extra package files"
            )
        for relative, entry in expected_files.items():
            path = package_root / Path(relative)
            filesystem_path = _filesystem_path(path)
            if (
                _sha256_file(filesystem_path) != entry["sha256"]
                or filesystem_path.stat().st_size != entry["bytes"]
            ):
                raise NDPAssignmentDistributionError(
                    f"{packet_id} packet file is stale: {relative}"
                )
            _scan_public_text(
                relative_path=relative,
                path=filesystem_path,
                dataset_ids=dataset_ids,
                titles=titles,
            )
        for forbidden in packet["forbidden_assignment_files"]:
            if _filesystem_path(
                package_root / Path(forbidden)
            ).exists():
                raise NDPAssignmentDistributionError(
                    f"{packet_id} contains forbidden assignment material"
                )
        expected_manifest = _packet_manifest(
            spec_path=spec_path,
            packet=packet,
        )
        if _load_json(manifest_path) != expected_manifest:
            raise NDPAssignmentDistributionError(
                f"{packet_id} packet manifest is stale"
            )
        receipt_packets[packet_id] = {
            "packet_manifest_sha256": _sha256_file(manifest_path),
            "file_count": packet["file_count"],
            "content_digest_sha256": packet["content_digest_sha256"],
            "sealed_dataset_id_matches": 0,
            "sealed_title_matches": 0,
            "extra_file_count": 0,
            "reviewer_ids_present": False,
            "human_decisions_present": False,
        }
    return receipt_packets


def _receipt(
    *,
    spec_path: Path,
    assignment_release_path: Path,
    public_manifest_path: Path,
    selection_path: Path,
    study_root: Path,
    repo_root: Path,
    packets: Mapping[str, Any],
) -> Dict[str, Any]:
    implementation = Path(__file__).resolve()
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": "materialized_and_verified_unassigned",
        "distribution_spec": {
            "sha256": _sha256_file(spec_path),
        },
        "assignment_release": _binding(
            assignment_release_path,
            study_root,
        ),
        "public_package_manifest": _binding(
            public_manifest_path,
            repo_root,
        ),
        "sealed_selection_sha256": _sha256_file(selection_path),
        "packet_count": len(packets),
        "packets": dict(packets),
        "sealed_identity_match_count": 0,
        "extra_file_count": 0,
        "reviewer_ids_present": False,
        "human_decisions_present": False,
        "implementation": {
            "file": implementation.name,
            "sha256": _sha256_file(implementation),
        },
    }


def materialize_distribution(
    *,
    spec_path: Path,
    assignment_release_path: Path,
    public_manifest_path: Path,
    selection_path: Path,
    study_root: Path,
    repo_root: Path,
    packet_root: Path,
) -> Dict[str, Any]:
    expected_spec = build_distribution_spec(
        assignment_release_path=assignment_release_path,
        public_manifest_path=public_manifest_path,
        selection_path=selection_path,
        study_root=study_root,
        repo_root=repo_root,
    )
    if _load_json(spec_path) != expected_spec:
        raise NDPAssignmentDistributionError(
            "distribution spec is missing or stale"
        )
    _ensure_external_empty_root(
        packet_root=packet_root,
        repo_root=repo_root,
    )
    package_directory_name = expected_spec["packet_root_directory_name"]
    for packet_id, packet in sorted(expected_spec["packets"].items()):
        packet_directory = packet_root / packet["packet_directory"]
        package_root = packet_directory / package_directory_name
        for entry in packet["files"]:
            source = repo_root / Path(entry["file"])
            target = package_root / Path(entry["file"])
            filesystem_target = _filesystem_path(target)
            filesystem_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(
                _filesystem_path(source),
                filesystem_target,
            )
        _write_json(
            packet_directory / "packet_manifest.json",
            _packet_manifest(spec_path=spec_path, packet=packet),
        )
    packets = _inspect_materialized_packets(
        spec=expected_spec,
        spec_path=spec_path,
        selection_path=selection_path,
        packet_root=packet_root,
        repo_root=repo_root,
    )
    return _receipt(
        spec_path=spec_path,
        assignment_release_path=assignment_release_path,
        public_manifest_path=public_manifest_path,
        selection_path=selection_path,
        study_root=study_root,
        repo_root=repo_root,
        packets=packets,
    )


def validate_distribution(
    receipt: Mapping[str, Any],
    *,
    spec_path: Path,
    assignment_release_path: Path,
    public_manifest_path: Path,
    selection_path: Path,
    study_root: Path,
    repo_root: Path,
    packet_root: Path,
) -> Dict[str, Any]:
    expected_spec = build_distribution_spec(
        assignment_release_path=assignment_release_path,
        public_manifest_path=public_manifest_path,
        selection_path=selection_path,
        study_root=study_root,
        repo_root=repo_root,
    )
    if _load_json(spec_path) != expected_spec:
        raise NDPAssignmentDistributionError(
            "distribution spec is missing or stale"
        )
    packets = _inspect_materialized_packets(
        spec=expected_spec,
        spec_path=spec_path,
        selection_path=selection_path,
        packet_root=packet_root,
        repo_root=repo_root,
    )
    expected_receipt = _receipt(
        spec_path=spec_path,
        assignment_release_path=assignment_release_path,
        public_manifest_path=public_manifest_path,
        selection_path=selection_path,
        study_root=study_root,
        repo_root=repo_root,
        packets=packets,
    )
    if dict(receipt) != expected_receipt:
        raise NDPAssignmentDistributionError(
            "distribution receipt does not replay"
        )
    return {
        "schema_version": VALIDATION_SCHEMA_VERSION,
        "status": "passed",
        "distribution_receipt_canonical_sha256": _canonical_digest(receipt),
        "distribution_spec_sha256": _sha256_file(spec_path),
        "assignment_release_sha256": _sha256_file(
            assignment_release_path
        ),
        "public_package_manifest_sha256": _sha256_file(
            public_manifest_path
        ),
        "sealed_selection_sha256": _sha256_file(selection_path),
        "packet_count": len(packets),
        "sealed_identity_match_count": 0,
        "extra_file_count": 0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Specify, materialize, and validate isolated least-access "
            "NDP-50 reviewer packets."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare-spec", "materialize", "validate"):
        command = subparsers.add_parser(name)
        command.add_argument(
            "--assignment-release",
            type=Path,
            required=True,
        )
        command.add_argument(
            "--public-package-manifest",
            type=Path,
            required=True,
        )
        command.add_argument("--selection", type=Path, required=True)
        command.add_argument("--study-root", type=Path, required=True)
        command.add_argument("--repo-root", type=Path, required=True)
        if name == "prepare-spec":
            command.add_argument("--output", type=Path, required=True)
        else:
            command.add_argument("--spec", type=Path, required=True)
            command.add_argument("--packet-root", type=Path, required=True)
            if name == "materialize":
                command.add_argument(
                    "--output-receipt",
                    type=Path,
                    required=True,
                )
            else:
                command.add_argument("--receipt", type=Path, required=True)
                command.add_argument("--output", type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    common = {
        "assignment_release_path": args.assignment_release,
        "public_manifest_path": args.public_package_manifest,
        "selection_path": args.selection,
        "study_root": args.study_root,
        "repo_root": args.repo_root,
    }
    if args.command == "prepare-spec":
        payload = build_distribution_spec(**common)
        _write_json(args.output, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "packet_count": payload["packet_count"],
                    "reviewer_ids_present": False,
                    "human_decisions_present": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "materialize":
        payload = materialize_distribution(
            spec_path=args.spec,
            packet_root=args.packet_root,
            **common,
        )
        _write_json(args.output_receipt, payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "packet_count": payload["packet_count"],
                    "sealed_identity_match_count": 0,
                    "extra_file_count": 0,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    receipt = _load_json(args.receipt)
    validation = validate_distribution(
        receipt,
        spec_path=args.spec,
        packet_root=args.packet_root,
        **common,
    )
    if args.output is not None:
        _write_json(args.output, validation)
    print(json.dumps(validation, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
