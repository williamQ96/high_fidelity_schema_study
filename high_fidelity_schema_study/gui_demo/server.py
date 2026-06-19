from __future__ import annotations

import json
import tempfile
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
