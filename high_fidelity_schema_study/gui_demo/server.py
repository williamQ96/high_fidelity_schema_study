from __future__ import annotations

import json
import re
import tempfile
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qs, urlparse

from ..extractors.base import ExtractionRequest
from ..extractors.registry import (
    HDF5_MAGIC,
    NETCDF_CLASSIC_MAGICS,
    build_raw_binary_schema as build_registry_raw_binary_schema,
    extract_path,
)
from ..models import DatasetSchema
from ..unified_schema import build_unified_schema_envelope


STUDY_DIR = Path(__file__).resolve().parents[1]
DEMO_EXAMPLES_ROOT = STUDY_DIR / "demo_examples"
DEMO_EXAMPLES_MANIFEST = DEMO_EXAMPLES_ROOT / "manifest.json"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def _read_json(relative_path: str) -> dict[str, Any]:
    return json.loads((STUDY_DIR / relative_path).read_text(encoding="utf-8"))


def _read_paper_macros() -> dict[str, str]:
    text = (STUDY_DIR / "paper" / "results_macros.tex").read_text(encoding="utf-8")
    return {
        name: value
        for name, value in re.findall(r"\\newcommand\{\\([^}]+)\}\{([^}]*)\}", text)
    }


def build_research_dashboard_payload() -> dict[str, Any]:
    """Build a sealed-safe, aggregate-only view of the current research state."""
    selection = _read_json("data/experiments/ndp50_v1/selection.json")
    readiness = _read_json("data/experiments/ndp50_v1/semantic/readiness_report_v1.json")
    development = _read_json("data/experiments/ndp50_v1/reports/development_v4/summary.json")
    validation = _read_json("data/experiments/ndp50_v1/reports/validation_v3/summary.json")
    architecture = _read_json(
        "data/experiments/minimal_architecture_redesign/"
        "qwen35_9b_development_2026-07-14/report.json"
    )
    qualification = _read_json(
        "data/experiments/semantic_backend_qualification_v1/"
        "qwen36_27b_q4_k_m_candidate_qualification_rerun_2026-07-15.assessment.json"
    )
    roster = _read_json(
        "data/experiments/ndp50_v1/semantic/human_assignments_v1/"
        "assignment_roster_neutral_v1.json"
    )
    distribution = _read_json(
        "data/experiments/ndp50_v1/semantic/human_assignments_v1/"
        "assignment_distribution_spec_v1.json"
    )
    macros = _read_paper_macros()

    checks = readiness.get("checks", [])
    gate_values = readiness.get("gates", {})
    variant_summaries = architecture.get("variant_summaries", {})
    comparisons = architecture.get("architecture_comparison", {})
    split_counts = selection.get("counts", {}).get("split_counts", {})
    qualification_cost = qualification.get("descriptive_operational_cost", {})
    qualification_backend = qualification.get("backend", {})

    gate_groups = [
        {
            "id": "definitions",
            "label": "Definitions & source scope",
            "workflow_ready": bool(
                gate_values.get("vocabulary_review_workflow_ready")
                and gate_values.get("source_approval_workflow_implementation_ready")
            ),
            "evidence_complete": bool(
                gate_values.get("vocabulary_frozen")
                and gate_values.get("source_bundles_annotation_ready")
            ),
        },
        {
            "id": "cpa",
            "label": "CPA applicability",
            "workflow_ready": bool(gate_values.get("cpa_screen_workflow_ready")),
            "evidence_complete": bool(gate_values.get("cpa_applicability_consensus_complete")),
        },
        {
            "id": "gold",
            "label": "Calibration & blind gold",
            "workflow_ready": bool(gate_values.get("semantic_gold_workflow_ready")),
            "evidence_complete": bool(
                gate_values.get("annotator_calibration_passed")
                and gate_values.get("independent_gold_complete")
            ),
        },
        {
            "id": "execution",
            "label": "Execution & power freeze",
            "workflow_ready": bool(
                gate_values.get("execution_freeze_workflow_ready")
                and gate_values.get("power_freeze_workflow_ready")
            ),
            "evidence_complete": bool(
                gate_values.get("prompt_and_backend_frozen")
                and gate_values.get("test_power_plan_frozen")
            ),
        },
        {
            "id": "governance",
            "label": "Governance & publication",
            "workflow_ready": bool(
                gate_values.get("data_governance_review_workflow_ready")
                and gate_values.get("publication_gate_workflow_ready")
            ),
            "evidence_complete": bool(
                gate_values.get("data_governance_policy_frozen")
                and gate_values.get("feedback_response_collaborator_signoff_complete")
                and gate_values.get("external_preregistration_verified")
            ),
        },
    ]

    def execution_summary(report: dict[str, Any]) -> dict[str, Any]:
        coverage = report.get("coverage", {})
        denominators = report.get("denominators", {})
        return {
            "role": report.get("run_role"),
            "datasets": denominators.get("datasets", 0),
            "catalog_resources": denominators.get("catalog_resources", 0),
            "successful_datasets": coverage.get("datasets_with_successful_extraction", 0),
            "dataset_end_to_end_rate": coverage.get("dataset_end_to_end_rate"),
            "extraction_success_given_acquisition": coverage.get(
                "extraction_success_rate_given_acquisition"
            ),
            "claim_boundary": report.get("claim_boundary"),
        }

    variants = []
    for key in ("A", "B", "C", "D"):
        summary = variant_summaries.get(key, {})
        metrics = summary.get("metrics", {})
        telemetry = summary.get("telemetry", {})
        variants.append(
            {
                "id": key,
                "name": {
                    "A": "Deterministic only",
                    "B": "Dataset reasoner",
                    "C": "Replay + verifier",
                    "D": "Legacy pipeline",
                }[key],
                "end_to_end_accuracy": metrics.get("end_to_end_value_accuracy"),
                "coverage": metrics.get("coverage"),
                "selective_risk": metrics.get("selective_risk"),
                "model_calls": telemetry.get("model_calls", 0),
                "comparable": bool(summary.get("comparable")),
                "comparison_note": summary.get("comparison_note"),
            }
        )

    return {
        "schema_version": "research-dashboard/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_snapshot": {
            "paper_date": macros.get("PaperDate"),
            "readiness_created_at": readiness.get("created_at"),
            "selection_created_at": selection.get("selected_at"),
            "protocol_version": selection.get("protocol_version"),
        },
        "headline": {
            "title": "How Much Semantic Architecture Is Necessary?",
            "subtitle": "Replay-controlled evaluation for evidence-constrained dataset schema induction",
            "current_result": "Validated protocol + operationally eligible backend; no architecture winner yet.",
            "test_ready": bool(readiness.get("test_ready")),
            "semantic_execution_ready": bool(readiness.get("semantic_execution_ready")),
            "integrity_status": readiness.get("integrity_status"),
            "full_tests": int(macros.get("FullTests", "0")),
        },
        "methodology": {
            "research_question": (
                "What causal contribution do one dataset-level semantic response and deterministic "
                "verification make beyond deterministic extraction?"
            ),
            "pipeline": [
                "Validate intake",
                "Detect format",
                "Route extractor",
                "Extract physical structure",
                "Run deterministic validators",
                "Project claims + evidence",
            ],
            "variants": variants,
            "comparisons": comparisons,
            "co_primary_contrasts": [
                "A - B: contribution of one dataset-level semantic response",
                "B - C: contribution of deterministic verification over byte-identical replay",
            ],
            "primary_test": "Paired two-sided sign-flip tests on dataset-level differences",
            "multiplicity": "Holm control across the two registered co-primary contrasts",
            "claim_boundary": (
                "Missing gold, partial execution, or replay failure suppresses the affected comparison. "
                "A failure to reject is not evidence of no effect."
            ),
        },
        "ndp50": {
            "selected": selection.get("counts", {}).get("selected_dataset_count", 0),
            "reserves": selection.get("counts", {}).get("reserve_dataset_count", 0),
            "splits": {
                "development": split_counts.get("development", 0),
                "validation": split_counts.get("validation", 0),
                "sealed_test": split_counts.get("test", 0),
            },
            "strata": selection.get("counts", {}).get("stratum_counts", {}),
            "selection_status": selection.get("status"),
            "development_execution": execution_summary(development),
            "validation_execution": execution_summary(validation),
            "test_identity_visible": False,
        },
        "development_evidence": {
            "case_count": int(macros.get("DevCases", "0")),
            "semantic_opportunity_cases": int(macros.get("DevSemanticCases", "0")),
            "variants": variants,
            "pairwise_status": {
                key: value.get("status") for key, value in comparisons.items()
            },
            "interpretation": (
                "Development metrics are diagnostic only. All architecture comparisons are currently "
                "non-comparable and cannot establish superiority."
            ),
        },
        "qualification": {
            "assessment": qualification.get("assessment"),
            "eligible": bool(qualification.get("eligible_under_frozen_thresholds")),
            "model": qualification_backend.get("model_identifier"),
            "variant": qualification_backend.get("selected_variant"),
            "quantization": qualification_backend.get("quantization"),
            "context_length": qualification_backend.get("loaded_context_length"),
            "case_count": int(macros.get("QualificationCases", "0")),
            "target_count": int(macros.get("QualificationTargets", "0")),
            "dataset_calls": qualification_cost.get("dataset_physical_model_calls"),
            "legacy_calls": qualification_cost.get("legacy_physical_model_calls"),
            "dataset_mean_latency_seconds": round(
                qualification_cost.get("dataset_mean_attempt_latency_ms", 0) / 1000, 2
            ),
            "legacy_mean_latency_seconds": round(
                qualification_cost.get("legacy_mean_dataset_latency_ms", 0) / 1000, 2
            ),
            "identity_binding_complete": bool(
                qualification.get("identity_binding_complete_for_blind_freeze")
            ),
            "remaining_identity_blockers": qualification.get("remaining_identity_blockers", []),
            "interpretation_boundary": qualification.get("interpretation_boundary"),
        },
        "readiness": {
            "status": readiness.get("readiness_status"),
            "checks_passed": sum(1 for check in checks if check.get("passed")),
            "checks_total": len(checks),
            "blockers": readiness.get("blockers", []),
            "gate_groups": gate_groups,
        },
        "human_workflow": {
            "roster_status": roster.get("status"),
            "packet_count": distribution.get("packet_count", 0),
            "feedback_signoff_complete": bool(
                gate_values.get("feedback_response_collaborator_signoff_complete")
            ),
            "independent_gold_complete": bool(gate_values.get("independent_gold_complete")),
            "external_preregistration_verified": bool(
                gate_values.get("external_preregistration_verified")
            ),
            "roles": [
                "Vocabulary reviewers A and B",
                "Data steward + accountable validator",
                "Two calibrated independent gold annotators",
                "Postdoctoral collaborator for F01-F16 response sign-off",
                "Independent preregistration verifier",
            ],
            "information_boundary": (
                "The dashboard exposes aggregate preparation state only. Sealed test identities, blind "
                "gold, model outputs, reviewer submissions, and test outcomes are never returned."
            ),
        },
        "sources": [
            "paper/semantic_architecture_study_en.tex",
            "paper/results_macros.tex",
            "data/experiments/ndp50_v1/selection.json",
            "data/experiments/ndp50_v1/semantic/readiness_report_v1.json",
            "data/experiments/ndp50_v1/reports/development_v4/summary.json",
            "data/experiments/ndp50_v1/reports/validation_v3/summary.json",
            "data/experiments/minimal_architecture_redesign/"
            "qwen35_9b_development_2026-07-14/report.json",
            "data/experiments/semantic_backend_qualification_v1/"
            "qwen36_27b_q4_k_m_candidate_qualification_rerun_2026-07-15.assessment.json",
        ],
    }


def load_demo_examples() -> list[dict[str, Any]]:
    payload = json.loads(DEMO_EXAMPLES_MANIFEST.read_text(encoding="utf-8"))
    examples = payload.get("examples", [])
    if not isinstance(examples, list):
        raise ValueError("Demo example manifest must contain an examples list.")
    return examples


def extract_demo_example(example_id: str, sample_limit: int = 200) -> dict[str, Any]:
    example = next((item for item in load_demo_examples() if item.get("id") == example_id), None)
    if example is None:
        raise ValueError("Unknown demo example.")
    relative = normalize_upload_relative_path(str(example.get("path", "")))
    root = DEMO_EXAMPLES_ROOT.resolve()
    path = DEMO_EXAMPLES_ROOT.joinpath(*relative.parts).resolve()
    if path != root and root not in path.parents:
        raise ValueError("Demo example path escapes the allowlisted root.")
    if not path.exists():
        raise ValueError("Demo example is unavailable.")
    result = extract_uploaded_schema(path, path.name, "auto", sample_limit)
    result["example"] = example
    return result
def detect_upload_mode(filename: str, requested_mode: str, data: bytes) -> str:
    mode = requested_mode.strip().lower()
    if mode in {"hdf5", "json", "xml", "netcdf", "parquet", "zarr", "timeseries", "csv", "binary"}:
        return mode

    suffix = Path(filename).suffix.lower()
    if any(data.startswith(magic) for magic in NETCDF_CLASSIC_MAGICS) or suffix in {".nc", ".cdf"}:
        return "netcdf"
    if data.startswith(HDF5_MAGIC) or suffix in {".h5", ".hdf5", ".he5"}:
        return "hdf5"
    if data.startswith(b"PAR1") or suffix == ".parquet":
        return "parquet"
    if suffix == ".csv":
        return "timeseries"
    if suffix in {".json", ".jsonl", ".ndjson"}:
        return "json"
    if suffix in {".xml", ".xsd"}:
        return "xml"
    return "binary"


def build_raw_binary_schema(path: Path, original_filename: str, data: bytes) -> DatasetSchema:
    schema = build_registry_raw_binary_schema(path, file_id=original_filename)
    schema.metadata["field_claim_policy"] = "abstain_without_sidecar_metadata"
    schema.notes[0] = "Raw binary payloads without sidecar metadata are underdetermined."
    return schema


def extract_uploaded_schema(
    upload_path: Path,
    original_filename: str,
    requested_mode: str,
    sample_limit: int = 200,
) -> dict[str, Any]:
    outcome = extract_path(
        ExtractionRequest(
            path=str(upload_path),
            format_hint=requested_mode,
            sample_limit=sample_limit,
        )
    )
    schema = outcome.schema
    if schema is not None:
        schema.file_id = original_filename
        schema.dataset_id = Path(original_filename).stem
        if outcome.status == "abstained" and schema.file_format == "raw_binary":
            schema.metadata["field_claim_policy"] = "abstain_without_sidecar_metadata"
    selected_format = outcome.format_decision.selected_format
    mode = (
        "timeseries"
        if requested_mode.strip().lower() == "timeseries" and selected_format == "csv"
        else selected_format or "binary"
    )
    runtime_notes = [
        f"Central extractor registry outcome: {outcome.status}.",
        *[issue.message for issue in outcome.issues],
    ]
    if outcome.status == "success" and selected_format == "hdf5":
        runtime_notes.append("Used deterministic HDF5 group/dataset traversal with field-level evidence.")
    elif outcome.status == "success" and selected_format == "netcdf":
        runtime_notes.append("Used deterministic NetCDF structure extraction and evidence-backed CF interpretation.")
    elif outcome.status in {"success", "partial"} and selected_format == "zarr":
        runtime_notes.append("Used deterministic local Zarr v2 metadata extraction without reading chunk payloads.")
    elif outcome.status == "success" and selected_format == "parquet":
        runtime_notes.append("Used deterministic Parquet footer and Arrow schema extraction without reading row values.")
    elif outcome.status == "success" and selected_format == "json":
        runtime_notes.append("Used bounded JSON structure observation or explicit JSON Schema declarations.")
    elif outcome.status == "success" and selected_format == "xml":
        runtime_notes.append("Used bounded XML structure observation or explicit XSD declarations.")
    elif outcome.status == "success" and selected_format == "csv":
        runtime_notes.append(
            "Detected time-series organization from deterministic temporal analysis."
            if schema.data_modality == "time_series"
            else "Parsed as conservative CSV; no strong time-series organization was detected."
        )
    elif outcome.status == "abstained":
        runtime_notes.append("Abstained from unsupported field claims.")
    elif outcome.status == "failed":
        runtime_notes.append("Extraction failed before a schema payload could be produced.")

    outcome_payload = outcome.to_dict()
    outcome_payload.pop("schema", None)
    unified_envelope = build_unified_schema_envelope(outcome)
    issue_text = "; ".join(issue.message for issue in outcome.issues)

    return {
        "ok": outcome.status != "failed",
        "error": issue_text if outcome.status == "failed" else None,
        "requested_mode": requested_mode,
        "detected_mode": mode,
        "filename": original_filename,
        "schema": schema.to_dict() if schema is not None else None,
        "extraction_outcome": outcome_payload,
        "unified_schema_envelope": unified_envelope,
        "runtime_notes": runtime_notes,
    }


def normalize_upload_relative_path(filename: str) -> PurePosixPath:
    normalized = filename.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ".." in path.parts
        or any(":" in part for part in path.parts)
        or any(part in {"", "."} for part in path.parts)
    ):
        raise ValueError("Upload contains an invalid relative path.")
    return path


def parse_multipart_form(body: bytes, content_type: str) -> tuple[dict[str, str], list[tuple[str, bytes]]]:
    message = BytesParser(policy=default).parsebytes(
        b"Content-Type: " + content_type.encode("utf-8") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    )
    fields: dict[str, str] = {}
    uploads: list[tuple[str, bytes]] = []
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if name == "file" and filename:
            uploads.append((normalize_upload_relative_path(filename).as_posix(), payload))
        else:
            fields[name] = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    return fields, uploads


def materialize_uploaded_resource(
    temp_root: Path,
    uploads: list[tuple[str, bytes]],
) -> tuple[Path, str]:
    if not uploads:
        raise ValueError("Missing file field")

    normalized = [(normalize_upload_relative_path(name), payload) for name, payload in uploads]
    is_directory_upload = len(normalized) > 1 or len(normalized[0][0].parts) > 1
    if not is_directory_upload:
        relative, payload = normalized[0]
        suffix = Path(relative.name).suffix or ".bin"
        upload_path = temp_root / f"upload{suffix}"
        upload_path.write_bytes(payload)
        return upload_path, relative.name

    store_root = temp_root / "upload_store"
    for relative, payload in normalized:
        destination = store_root.joinpath(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)

    first_parts = [relative.parts[0] for relative, _payload in normalized]
    if len(set(first_parts)) == 1 and all(len(relative.parts) > 1 for relative, _payload in normalized):
        selected_root = store_root / first_parts[0]
        original_name = first_parts[0]
    else:
        selected_root = store_root
        original_name = "uploaded_store.zarr"
    return selected_root, original_name


def json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if hasattr(value, "tolist"):
        return json_safe(value.tolist())
    if hasattr(value, "item"):
        return json_safe(value.item())
    return value


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STUDY_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/research-status":
            try:
                payload = build_research_dashboard_payload()
            except (OSError, ValueError, KeyError) as exc:
                self._write_json({"ok": False, "error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._write_json({"ok": True, **payload})
            return
        if parsed.path == "/api/examples":
            self._write_json({"ok": True, "examples": load_demo_examples()})
            return
        if parsed.path == "/api/extract-example":
            query = parse_qs(parsed.query)
            example_id = query.get("id", [""])[0]
            try:
                sample_limit = max(1, min(int(query.get("sample_limit", ["200"])[0]), 10000))
                result = extract_demo_example(example_id, sample_limit)
            except (ValueError, OSError) as exc:
                self._write_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            self._write_json(result)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/extract-schema":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._write_json({"ok": False, "error": "Invalid Content-Length"}, HTTPStatus.BAD_REQUEST)
            return

        if length <= 0:
            self._write_json({"ok": False, "error": "Missing upload body"}, HTTPStatus.BAD_REQUEST)
            return
        if length > MAX_UPLOAD_BYTES:
            self._write_json({"ok": False, "error": "Upload exceeds 100 MB limit"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._write_json({"ok": False, "error": "Expected multipart/form-data"}, HTTPStatus.BAD_REQUEST)
            return

        try:
            fields, uploads = parse_multipart_form(self.rfile.read(length), content_type)
        except ValueError as exc:
            self._write_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if not uploads:
            self._write_json({"ok": False, "error": "Missing file field"}, HTTPStatus.BAD_REQUEST)
            return

        if any(not payload for _filename, payload in uploads):
            self._write_json({"ok": False, "error": "Uploaded file is empty"}, HTTPStatus.BAD_REQUEST)
            return

        requested_mode = fields.get("mode", "auto")
        try:
            sample_limit = int(fields.get("sample_limit", "200"))
        except ValueError:
            sample_limit = 200
        sample_limit = max(1, min(sample_limit, 10000))

        with tempfile.TemporaryDirectory(prefix="schema-demo-") as tmpdir:
            try:
                upload_path, original_filename = materialize_uploaded_resource(Path(tmpdir), uploads)
                result = extract_uploaded_schema(upload_path, original_filename, requested_mode, sample_limit)
            except Exception as exc:  # pragma: no cover - exercised by browser smoke paths
                self._write_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return

        self._write_json(result)

    def _write_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(json_safe(payload), indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Serve the high-fidelity schema GUI demo with upload extraction.")
    parser.add_argument("port", nargs="?", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), DemoHandler)
    print(f"Serving high-fidelity schema GUI at http://localhost:{args.port}/gui_demo/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
