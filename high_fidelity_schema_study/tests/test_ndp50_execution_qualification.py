from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from high_fidelity_schema_study.ndp50_execution_qualification import (
    DECLARATION_SCHEMA_VERSION,
    IMPLEMENTATION_SLOTS,
    NDPExecutionQualificationError,
    build_qualification_receipt,
    interface_version,
    verify_qualification_receipt,
)


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ref(path: Path, root: Path) -> dict[str, str]:
    return {
        "file": path.relative_to(root).as_posix(),
        "sha256": _sha256(path),
    }


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "study"
    component = root / "implementation" / "component.py"
    component.parent.mkdir(parents=True, exist_ok=True)
    component.write_text(
        "from high_fidelity_schema_study."
        "ndp50_execution_qualification import reference_probe_response\n\n"
        "def ndp50_qualification_probe(request):\n"
        "    return reference_probe_response(request)\n",
        encoding="utf-8",
    )
    declaration = root / "implementation" / "declaration.json"
    _write_json(
        declaration,
        {
            "schema_version": DECLARATION_SCHEMA_VERSION,
            "status": "complete_pending_qualification",
            "synthetic_probes_only": True,
            "development_validation_or_test_data_used": False,
            "implementations": {
                slot: {
                    "artifact": _ref(component, root),
                    "entrypoint": "ndp50_qualification_probe",
                    "interface_version": interface_version(slot),
                }
                for slot in IMPLEMENTATION_SLOTS
            },
            "completion_attestation": True,
        },
    )
    return root, declaration


def test_synthetic_qualification_builds_and_replays(
    tmp_path: Path,
) -> None:
    root, declaration = _fixture(tmp_path)

    receipt = build_qualification_receipt(
        declaration_path=declaration,
        study_root=root,
    )
    replay = verify_qualification_receipt(
        receipt,
        declaration_path=declaration,
        study_root=root,
    )

    assert receipt["status"] == "passed"
    assert receipt["qualified_slot_count"] == len(IMPLEMENTATION_SLOTS)
    assert all(item["all_passed"] for item in receipt["slots"].values())
    assert replay["status"] == "passed"


def test_qualification_rejects_non_synthetic_data_use(
    tmp_path: Path,
) -> None:
    root, declaration = _fixture(tmp_path)
    payload = json.loads(declaration.read_text(encoding="utf-8"))
    payload["development_validation_or_test_data_used"] = True
    _write_json(declaration, payload)

    with pytest.raises(
        NDPExecutionQualificationError,
        match="cannot use development, validation, or test data",
    ):
        build_qualification_receipt(
            declaration_path=declaration,
            study_root=root,
        )


def test_wrong_probe_output_is_rejected(tmp_path: Path) -> None:
    root, declaration = _fixture(tmp_path)
    payload = json.loads(declaration.read_text(encoding="utf-8"))
    component = root / payload["implementations"]["runner"]["artifact"]["file"]
    component.write_text(
        "def ndp50_qualification_probe(request):\n"
        "    return {'status': 'claimed-pass'}\n",
        encoding="utf-8",
    )
    for item in payload["implementations"].values():
        item["artifact"]["sha256"] = _sha256(component)
    _write_json(declaration, payload)

    with pytest.raises(
        NDPExecutionQualificationError,
        match="output mismatch",
    ):
        build_qualification_receipt(
            declaration_path=declaration,
            study_root=root,
        )


def test_tampered_receipt_fails_replay(tmp_path: Path) -> None:
    root, declaration = _fixture(tmp_path)
    receipt = build_qualification_receipt(
        declaration_path=declaration,
        study_root=root,
    )
    receipt["slots"]["scorer"]["all_passed"] = False

    replay = verify_qualification_receipt(
        receipt,
        declaration_path=declaration,
        study_root=root,
    )

    assert replay["status"] == "failed"
    assert replay["differing_top_level_keys"] == ["slots"]
