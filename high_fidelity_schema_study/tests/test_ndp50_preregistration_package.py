from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from high_fidelity_schema_study.ndp50_preregistration_package import (
    DRAFT_BANNER,
    NDPPreregistrationPackageError,
    REQUIRED_PUBLIC_FILES,
    build_public_package_manifest,
    validate_public_package_manifest,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "repository"
    selection = root / "data" / "experiments" / "ndp50_v1" / "selection.json"
    selection.parent.mkdir(parents=True, exist_ok=True)
    selection.write_text(
        json.dumps(
            {
                "schema_version": "ndp50-selection/v1",
                "selected_datasets": [
                    {
                        "dataset_id": f"sealed-test-{index:02d}",
                        "title": f"Sealed scientific dataset {index:02d}",
                        "split": "test",
                    }
                    for index in range(25)
                ],
            }
        ),
        encoding="utf-8",
    )
    for relative in sorted(REQUIRED_PUBLIC_FILES):
        if relative.endswith("public_package_files_v1.txt"):
            continue
        if relative == "ndp50_preregistration_package.py":
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(
                PACKAGE_ROOT / "ndp50_preregistration_package.py",
                target,
            )
            continue
        content = "{}\n"
        if relative.endswith(
            "ndp50_osf_zenodo_preregistration_draft_v1.md"
        ):
            content = (
                "# Registration\n\n"
                f"{DRAFT_BANNER}\n\n"
                "Receipt: `<UNRESOLVED>`\n"
            )
        _write(root / relative, content)
    file_list = (
        root / "docs" / "preregistration" / "public_package_files_v1.txt"
    )
    _write(
        file_list,
        "\n".join(sorted(REQUIRED_PUBLIC_FILES)) + "\n",
    )
    return root, selection, file_list


def test_repository_public_package_replays_and_keeps_test_sealed() -> None:
    artifact = (
        PACKAGE_ROOT
        / "data"
        / "experiments"
        / "ndp50_v1"
        / "preregistration"
        / "public_package_manifest_v1.json"
    )
    selection = (
        PACKAGE_ROOT
        / "data"
        / "experiments"
        / "ndp50_v1"
        / "selection.json"
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    validation = validate_public_package_manifest(
        payload,
        repo_root=PACKAGE_ROOT,
        selection_path=selection,
    )

    assert validation["status"] == "passed"
    assert payload["status"] == "draft_structurally_valid_not_registered"
    assert payload["authorization"] == {
        "external_registration_claimed": False,
        "semantic_execution_authorized": False,
        "test_release_authorized": False,
    }
    assert payload["private_sealing_control"][
        "sealed_test_dataset_count"
    ] == 25
    assert payload["private_sealing_control"][
        "sealed_identity_match_count"
    ] == 0
    public_files = {
        item["file"] for item in payload["public_scope"]["files"]
    }
    assert "data/experiments/ndp50_v1/selection.json" not in public_files
    assert {
        "ndp50_data_governance.py",
        "ndp50_data_governance_review.py",
        "ndp50_vocabulary_workflow.py",
        "requirements.txt",
    }.issubset(public_files)


def test_build_is_deterministic_and_validation_detects_tampering(
    tmp_path: Path,
) -> None:
    root, selection, file_list = _fixture(tmp_path)
    first = build_public_package_manifest(
        repo_root=root,
        selection_path=selection,
        file_list_path=file_list,
    )
    second = build_public_package_manifest(
        repo_root=root,
        selection_path=selection,
        file_list_path=file_list,
    )

    assert first == second
    first["status"] = "registered"
    validation = validate_public_package_manifest(
        first,
        repo_root=root,
        selection_path=selection,
    )
    assert validation["status"] == "failed"
    assert validation["differing_top_level_keys"] == ["status"]


def test_exact_sealed_dataset_id_or_title_blocks_public_package(
    tmp_path: Path,
) -> None:
    root, selection, file_list = _fixture(tmp_path)
    target = root / "docs" / "ndp50_protocol_v1.md"
    _write(
        target,
        "Accidental leak: sealed-test-00 / Sealed scientific dataset 01\n",
    )

    with pytest.raises(
        NDPPreregistrationPackageError,
        match="sealed test identity leakage",
    ):
        build_public_package_manifest(
            repo_root=root,
            selection_path=selection,
            file_list_path=file_list,
        )


def test_local_python_import_closure_is_enforced(tmp_path: Path) -> None:
    root, selection, file_list = _fixture(tmp_path)
    _write(root / "hidden_helper.py", "VALUE = 1\n")
    _write(
        root / "architecture_evaluation.py",
        "from .hidden_helper import VALUE\n",
    )

    with pytest.raises(
        NDPPreregistrationPackageError,
        match="not closed over local imports",
    ):
        build_public_package_manifest(
            repo_root=root,
            selection_path=selection,
            file_list_path=file_list,
        )


def test_path_escape_and_test_detail_paths_are_rejected(
    tmp_path: Path,
) -> None:
    root, selection, file_list = _fixture(tmp_path)
    outside = root.parent / "secret.txt"
    _write(outside, "not public\n")
    values = sorted(REQUIRED_PUBLIC_FILES | {"../secret.txt"})
    _write(file_list, "\n".join(values) + "\n")

    with pytest.raises(
        NDPPreregistrationPackageError,
        match="escapes the repository root",
    ):
        build_public_package_manifest(
            repo_root=root,
            selection_path=selection,
            file_list_path=file_list,
        )

    forbidden = (
        "data/experiments/ndp50_v1/acquisition/"
        "test_details/secret.json"
    )
    _write(root / forbidden, "{}\n")
    _write(
        file_list,
        "\n".join(sorted(REQUIRED_PUBLIC_FILES | {forbidden})) + "\n",
    )
    with pytest.raises(
        NDPPreregistrationPackageError,
        match="forbidden test-detail path",
    ):
        build_public_package_manifest(
            repo_root=root,
            selection_path=selection,
            file_list_path=file_list,
        )


def test_draft_banner_and_unresolved_marker_cannot_be_silently_removed(
    tmp_path: Path,
) -> None:
    root, selection, file_list = _fixture(tmp_path)
    prereg = (
        root
        / "docs"
        / "preregistration"
        / "ndp50_osf_zenodo_preregistration_draft_v1.md"
    )
    _write(prereg, "# Registration\n\nPretend complete.\n")

    with pytest.raises(
        NDPPreregistrationPackageError,
        match="unregistered draft banner",
    ):
        build_public_package_manifest(
            repo_root=root,
            selection_path=selection,
            file_list_path=file_list,
        )
