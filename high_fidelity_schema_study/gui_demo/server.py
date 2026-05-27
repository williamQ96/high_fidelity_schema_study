from __future__ import annotations

import json
import tempfile
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ..extractors.csv_extractor import extract_csv_schema
from ..extractors.hdf5_extractor import extract_hdf5_schema
from ..models import DatasetSchema


STUDY_DIR = Path(__file__).resolve().parents[1]
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"


def detect_upload_mode(filename: str, requested_mode: str, data: bytes) -> str:
    mode = requested_mode.strip().lower()
    if mode in {"hdf5", "timeseries", "csv", "binary"}:
        return mode

    suffix = Path(filename).suffix.lower()
    if data.startswith(HDF5_MAGIC) or suffix in {".h5", ".hdf5", ".he5"}:
        return "hdf5"
    if suffix == ".csv":
        return "timeseries"
    return "binary"


def build_raw_binary_schema(path: Path, original_filename: str, data: bytes) -> DatasetSchema:
    return DatasetSchema(
        dataset_id=path.stem,
        file_id=original_filename,
        file_format="raw_binary",
        data_modality="unknown",
        fields=[],
        metadata={
            "byte_size": len(data),
            "magic_hex_prefix": data[:16].hex(" "),
            "field_claim_policy": "abstain_without_sidecar_metadata",
            "extraction_errors": [],
        },
        notes=[
            "Raw binary payloads without sidecar metadata are underdetermined.",
            "The high-fidelity policy records file-level evidence and abstains from unsupported field claims.",
        ],
    )


def extract_uploaded_schema(
    upload_path: Path,
    original_filename: str,
    requested_mode: str,
    sample_limit: int = 200,
) -> dict[str, Any]:
    data = upload_path.read_bytes()
    mode = detect_upload_mode(original_filename, requested_mode, data)
    runtime_notes: list[str] = []

    if mode == "hdf5":
        schema = extract_hdf5_schema(str(upload_path))
        runtime_notes.append("Used deterministic HDF5 group/dataset traversal with field-level evidence.")
    elif mode in {"timeseries", "csv"}:
        schema = extract_csv_schema(str(upload_path), sample_limit=sample_limit)
        if schema.data_modality == "time_series":
            runtime_notes.append("Detected time-series organization from datetime fields or assembled date parts.")
        else:
            runtime_notes.append("Parsed as conservative CSV; no strong time-series organization was detected.")
    else:
        schema = build_raw_binary_schema(upload_path, original_filename, data)
        runtime_notes.append("Raw binary mode abstained from field extraction without sidecar metadata.")

    return {
        "ok": True,
        "requested_mode": requested_mode,
        "detected_mode": mode,
        "filename": original_filename,
        "schema": schema.to_dict(),
        "runtime_notes": runtime_notes,
    }


def parse_multipart_form(body: bytes, content_type: str) -> tuple[dict[str, str], tuple[str, bytes] | None]:
    message = BytesParser(policy=default).parsebytes(
        b"Content-Type: " + content_type.encode("utf-8") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    )
    fields: dict[str, str] = {}
    upload: tuple[str, bytes] | None = None
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if name == "file" and filename:
            upload = (Path(filename).name, payload)
        else:
            fields[name] = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    return fields, upload


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

        fields, upload = parse_multipart_form(self.rfile.read(length), content_type)
        if upload is None:
            self._write_json({"ok": False, "error": "Missing file field"}, HTTPStatus.BAD_REQUEST)
            return

        original_filename, payload = upload
        if not payload:
            self._write_json({"ok": False, "error": "Uploaded file is empty"}, HTTPStatus.BAD_REQUEST)
            return

        requested_mode = fields.get("mode", "auto")
        try:
            sample_limit = int(fields.get("sample_limit", "200"))
        except ValueError:
            sample_limit = 200
        sample_limit = max(1, min(sample_limit, 10000))

        suffix = Path(original_filename).suffix or ".bin"
        with tempfile.TemporaryDirectory(prefix="schema-demo-") as tmpdir:
            upload_path = Path(tmpdir) / f"upload{suffix}"
            upload_path.write_bytes(payload)
            try:
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
