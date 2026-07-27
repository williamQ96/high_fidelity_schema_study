from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from high_fidelity_schema_study.extractors.base import ExtractionRequest
from high_fidelity_schema_study.extractors.registry import (
    EXTRACTOR_RUNNERS,
    HDF5_MAGIC,
    extract_path,
    list_capabilities,
)
from high_fidelity_schema_study.models import DatasetSchema


def test_registry_lists_supported_capabilities():
    formats = {item.formats[0] for item in list_capabilities()}

    assert formats == {"csv", "hdf5", "json", "netcdf", "parquet", "xml", "zarr"}


def test_magic_routes_hdf5_even_with_wrong_suffix(tmp_path):
    path = tmp_path / "payload.bin"
    path.write_bytes(HDF5_MAGIC + b"not-a-complete-file")

    outcome = extract_path(ExtractionRequest(str(path)))

    assert outcome.format_decision.selected_format == "hdf5"
    assert outcome.extractor is not None
    assert outcome.extractor.extractor_id == "h5py_structure_traversal"
    assert outcome.status == "failed"
    assert outcome.issues[0].code == "parser_error"


def test_conflicting_magic_and_hint_abstains(tmp_path):
    path = tmp_path / "payload.bin"
    path.write_bytes(HDF5_MAGIC + b"rest")

    outcome = extract_path(ExtractionRequest(str(path), format_hint="csv"))

    assert outcome.status == "abstained"
    assert outcome.extractor is None
    assert outcome.schema is not None
    assert outcome.schema.fields == []
    assert outcome.issues[0].code == "unknown_conflicting_format_signals"


def test_complete_json_with_misleading_csv_suffix_abstains(tmp_path):
    path = tmp_path / "payload.csv"
    path.write_text('{"status": "ok", "values": [1, 2]}', encoding="utf-8")

    outcome = extract_path(ExtractionRequest(str(path)))

    assert outcome.status == "abstained"
    assert outcome.format_decision.conflicted is True
    assert outcome.format_decision.selected_format is None
    assert {signal.format for signal in outcome.format_decision.signals} == {
        "csv",
        "json",
    }


def test_extensionless_complete_json_routes_to_json(tmp_path):
    path = tmp_path / "payload"
    path.write_text('{"values": [1, 2]}', encoding="utf-8")

    outcome = extract_path(ExtractionRequest(str(path)))

    assert outcome.status == "success"
    assert outcome.format_decision.selected_format == "json"
    assert outcome.format_decision.basis == "complete_json_probe"


def test_malformed_parquet_routes_to_registered_extractor(tmp_path):
    path = tmp_path / "sample.parquet"
    path.write_bytes(b"PAR1unsupported")

    outcome = extract_path(ExtractionRequest(str(path)))

    assert outcome.status == "failed"
    assert outcome.format_decision.selected_format == "parquet"
    assert outcome.extractor is not None
    assert outcome.extractor.extractor_id == "parquet_arrow_metadata_extractor"
    assert outcome.issues[0].code == "parser_error"


def test_unknown_binary_returns_structured_abstention(tmp_path):
    path = tmp_path / "opaque.bin"
    path.write_bytes(b"\x00\x01opaque")

    outcome = extract_path(ExtractionRequest(str(path)))

    assert outcome.status == "abstained"
    assert outcome.format_decision.selected_format is None
    assert outcome.issues[0].code == "unknown_no_signature"
    assert outcome.schema is not None
    assert outcome.schema.metadata["field_claim_policy"] == "abstain_without_spec_backed_extractor"


def test_csv_registry_dispatch_matches_legacy_api(tmp_path):
    path = tmp_path / "series.csv"
    path.write_text(
        "ts_utc,value\n"
        "2026-01-01T00:00:00Z,1\n"
        "2026-01-01T01:00:00Z,2\n",
        encoding="utf-8",
    )

    outcome = extract_path(ExtractionRequest(str(path), sample_limit=10))

    assert outcome.status == "success"
    assert outcome.extractor is not None
    assert outcome.extractor.extractor_id == "csv_conservative_profiler"
    assert outcome.schema is not None
    assert outcome.schema.metadata["time_series"]["time_axis"]["timezone"] == "UTC"


def test_dependency_failure_is_structured(tmp_path, monkeypatch):
    path = tmp_path / "payload.h5"
    path.write_bytes(HDF5_MAGIC + b"rest")

    def unavailable(_request):
        raise RuntimeError("h5py is required for HDF5 extraction")

    monkeypatch.setitem(EXTRACTOR_RUNNERS, "hdf5", unavailable)
    outcome = extract_path(ExtractionRequest(str(path)))

    assert outcome.status == "failed"
    assert outcome.issues[0].code == "dependency_unavailable"


def test_partial_extraction_is_structured(tmp_path, monkeypatch):
    path = tmp_path / "sample.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")

    def partial(_request):
        return DatasetSchema(
            dataset_id="sample",
            file_id="sample.csv",
            file_format="csv",
            metadata={"extraction_errors": [{"path": "b", "error": "recoverable"}]},
        )

    monkeypatch.setitem(EXTRACTOR_RUNNERS, "csv", partial)
    outcome = extract_path(ExtractionRequest(str(path)))

    assert outcome.status == "partial"
    assert outcome.issues[0].code == "partial_extraction"


def test_registry_import_survives_missing_optional_dependencies():
    code = """
import sys

class BlockOptionalDependencies:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in {"h5py", "numpy", "pyarrow", "scipy"}:
            raise ModuleNotFoundError(fullname)
        return None

sys.meta_path.insert(0, BlockOptionalDependencies())
from high_fidelity_schema_study.extractors.registry import list_capabilities
assert len(list_capabilities()) == 7
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_csv_cli_survives_missing_optional_dependencies(tmp_path):
    path = tmp_path / "series.csv"
    path.write_text(
        "ts_utc,value\n"
        "2026-01-01T00:00:00Z,1\n"
        "2026-01-01T01:00:00Z,2\n",
        encoding="utf-8",
    )
    code = f"""
import sys

class BlockOptionalDependencies:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in {{"h5py", "numpy", "pyarrow", "scipy"}}:
            raise ModuleNotFoundError(fullname)
        return None

sys.meta_path.insert(0, BlockOptionalDependencies())
sys.argv = ["schema-study", "extract", "--input", {str(path)!r}]
from high_fidelity_schema_study import cli
cli.main()
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "success"
    assert payload["format_decision"]["selected_format"] == "csv"
    assert payload["extractor"]["extractor_id"] == "csv_conservative_profiler"
