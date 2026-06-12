from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any


ROOT = Path(__file__).resolve().parent
CHALLENGE_ROOT = ROOT / "testdata" / "zarr_phase14a"


def _store(name: str) -> Path:
    CHALLENGE_ROOT.mkdir(parents=True, exist_ok=True)
    path = (CHALLENGE_ROOT / name).resolve()
    if path.parent != CHALLENGE_ROOT.resolve():
        raise ValueError("challenge store must remain inside the Phase 14A challenge root")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()
    return path


def _write_json(root: Path, relative: str, payload: Any) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _group(root: Path, relative: str = "") -> None:
    prefix = f"{relative}/" if relative else ""
    _write_json(root, f"{prefix}.zgroup", {"zarr_format": 2})


def _array(
    root: Path,
    relative: str,
    *,
    dtype: str = "<f4",
    shape: list[int] | None = None,
    chunks: list[int] | None = None,
    compressor: Any = None,
    fill_value: Any = None,
    order: str = "C",
    filters: Any = None,
    dimension_separator: str = ".",
    attrs: dict[str, Any] | None = None,
) -> None:
    shape = shape or [3]
    chunks = chunks or list(shape)
    _write_json(
        root,
        f"{relative}/.zarray",
        {
            "zarr_format": 2,
            "shape": shape,
            "chunks": chunks,
            "dtype": dtype,
            "compressor": compressor,
            "fill_value": fill_value,
            "order": order,
            "filters": filters,
            "dimension_separator": dimension_separator,
        },
    )
    if attrs is not None:
        _write_json(root, f"{relative}/.zattrs", attrs)


def build_minimal_group() -> None:
    root = _store("minimal_group.zarr")
    _group(root)


def build_basic_array() -> None:
    root = _store("basic_array.zarr")
    _group(root)
    _array(root, "temperature")


def build_nested_hierarchy() -> None:
    root = _store("nested_hierarchy.zarr")
    _group(root)
    _group(root, "observations")
    _array(root, "observations/temperature", shape=[2, 3], chunks=[1, 3])


def build_physical_metadata() -> None:
    root = _store("physical_metadata.zarr")
    _group(root)
    _array(
        root,
        "signal",
        dtype="<i2",
        shape=[4, 6],
        chunks=[2, 3],
        compressor={"id": "zlib", "level": 1},
        fill_value=-9999,
        order="F",
        filters=[{"id": "delta", "dtype": "<i2"}],
        dimension_separator="/",
        attrs={"long_name": "instrument signal"},
    )


def build_xarray_coordinates() -> None:
    root = _store("xarray_coordinates.zarr")
    _group(root)
    _array(
        root,
        "time",
        dtype="<f8",
        attrs={
            "_ARRAY_DIMENSIONS": ["time"],
            "standard_name": "time",
            "axis": "T",
            "units": "hours since 2026-01-01 00:00:00 UTC",
            "calendar": "standard",
        },
    )
    _array(
        root,
        "lat",
        attrs={
            "_ARRAY_DIMENSIONS": ["lat"],
            "standard_name": "latitude",
            "axis": "Y",
            "units": "degrees_north",
        },
    )
    _array(
        root,
        "temperature",
        shape=[3, 3],
        chunks=[1, 3],
        attrs={
            "_ARRAY_DIMENSIONS": ["time", "lat"],
            "coordinates": "time lat",
            "standard_name": "air_temperature",
            "units": "K",
        },
    )


def build_coordinate_conflict() -> None:
    root = _store("coordinate_conflict.zarr")
    _group(root)
    _array(
        root,
        "position",
        attrs={
            "_ARRAY_DIMENSIONS": ["record"],
            "standard_name": "latitude",
            "axis": "X",
        },
    )


def build_name_only_unknown() -> None:
    root = _store("name_only_unknown.zarr")
    _group(root)
    _array(root, "lat")


def build_partial_malformed() -> None:
    root = _store("partial_malformed.zarr")
    _group(root)
    _array(root, "valid")
    malformed = root / "broken" / ".zarray"
    malformed.parent.mkdir(parents=True)
    malformed.write_text("{not-json}\n", encoding="utf-8")


def build_malformed_root() -> None:
    root = _store("malformed_root.zarr")
    (root / ".zgroup").write_text("{not-json}\n", encoding="utf-8")


def build_missing_metadata() -> None:
    _store("missing_metadata.zarr")


def build_zarr_v3() -> None:
    root = _store("zarr_v3.zarr")
    _write_json(root, "zarr.json", {"zarr_format": 3, "node_type": "group"})


def build_consolidated_only() -> None:
    root = _store("consolidated_only.zarr")
    _write_json(
        root,
        ".zmetadata",
        {
            "zarr_consolidated_format": 1,
            "metadata": {
                ".zgroup": {"zarr_format": 2},
                "temperature/.zarray": {
                    "zarr_format": 2,
                    "shape": [3],
                    "chunks": [3],
                    "dtype": "<f4",
                    "compressor": None,
                    "fill_value": None,
                    "order": "C",
                    "filters": None,
                },
                "temperature/.zattrs": {"standard_name": "air_temperature", "units": "K"},
            },
        },
    )


def build_consolidated_conflict() -> None:
    root = _store("consolidated_conflict.zarr")
    _group(root)
    _array(root, "temperature", shape=[3])
    _write_json(
        root,
        ".zmetadata",
        {
            "zarr_consolidated_format": 1,
            "metadata": {
                ".zgroup": {"zarr_format": 2},
                "temperature/.zarray": {
                    "zarr_format": 2,
                    "shape": [99],
                    "chunks": [3],
                    "dtype": "<f4",
                    "compressor": None,
                    "fill_value": None,
                    "order": "C",
                    "filters": None,
                },
            },
        },
    )


def build_unknown_codec() -> None:
    root = _store("unknown_codec.zarr")
    _group(root)
    _array(root, "signal", compressor={"id": "future_codec", "level": 7})


def build_manifest() -> None:
    manifest = {
        "experiment_id": "phase14a_zarr",
        "cases": [
            {
                "case_id": "minimal_group",
                "store": "minimal_group.zarr",
                "expected_status": "success",
                "expected_groups": ["/"],
                "expected_arrays": {},
                "expected_issue_codes": [],
            },
            {
                "case_id": "basic_array",
                "store": "basic_array.zarr",
                "expected_status": "success",
                "expected_groups": ["/"],
                "expected_arrays": {
                    "temperature": {"dtype": "<f4", "shape": [3], "chunks": [3], "order": "C", "fill_value": None}
                },
                "expected_issue_codes": [],
            },
            {
                "case_id": "nested_hierarchy",
                "store": "nested_hierarchy.zarr",
                "expected_status": "success",
                "expected_groups": ["/", "observations"],
                "expected_arrays": {
                    "observations/temperature": {"shape": [2, 3], "chunks": [1, 3]}
                },
                "expected_issue_codes": [],
            },
            {
                "case_id": "physical_metadata",
                "store": "physical_metadata.zarr",
                "expected_status": "success",
                "expected_groups": ["/"],
                "expected_arrays": {
                    "signal": {
                        "dtype": "<i2",
                        "shape": [4, 6],
                        "chunks": [2, 3],
                        "order": "F",
                        "fill_value": -9999,
                        "compressor": {"id": "zlib", "level": 1},
                        "filters": [{"id": "delta", "dtype": "<i2"}],
                        "dimension_separator": "/",
                    }
                },
                "expected_attributes": {"signal": {"long_name": "instrument signal"}},
                "expected_issue_codes": [],
            },
            {
                "case_id": "xarray_coordinates",
                "store": "xarray_coordinates.zarr",
                "expected_status": "success",
                "expected_groups": ["/"],
                "expected_arrays": {"time": {}, "lat": {}, "temperature": {}},
                "expected_dimensions": {"time": 3, "lat": 3},
                "expected_coordinate_roles": {
                    "time": ["dimension_coordinate", "axis_t", "standard_time", "auxiliary_coordinate"],
                    "lat": ["dimension_coordinate", "axis_y", "standard_latitude", "geospatial_coordinate", "auxiliary_coordinate"],
                },
                "expected_calendar": {"time": ["standard", "supported"]},
                "expected_units": {"temperature": "normalized_ucum"},
                "expected_issue_codes": [],
            },
            {
                "case_id": "coordinate_conflict",
                "store": "coordinate_conflict.zarr",
                "expected_status": "success",
                "expected_groups": ["/"],
                "expected_arrays": {"position": {}},
                "expected_coordinate_states": {"position": "conflicted"},
                "expected_unknown_fields": ["position"],
                "expected_issue_codes": [],
            },
            {
                "case_id": "name_only_unknown",
                "store": "name_only_unknown.zarr",
                "expected_status": "success",
                "expected_groups": ["/"],
                "expected_arrays": {"lat": {}},
                "expected_unknown_fields": ["lat"],
                "expected_issue_codes": [],
            },
            {
                "case_id": "partial_malformed",
                "store": "partial_malformed.zarr",
                "expected_status": "partial",
                "expected_groups": ["/"],
                "expected_arrays": {"valid": {}},
                "expected_issue_codes": ["partial_extraction", "zarr_metadata_malformed"],
            },
            {
                "case_id": "malformed_root",
                "store": "malformed_root.zarr",
                "expected_status": "failed",
                "expected_groups": [],
                "expected_arrays": {},
                "expected_issue_codes": ["zarr_metadata_malformed"],
            },
            {
                "case_id": "missing_metadata",
                "store": "missing_metadata.zarr",
                "expected_status": "abstained",
                "expected_groups": [],
                "expected_arrays": {},
                "expected_issue_codes": ["zarr_metadata_missing"],
            },
            {
                "case_id": "zarr_v3",
                "store": "zarr_v3.zarr",
                "expected_status": "abstained",
                "expected_groups": [],
                "expected_arrays": {},
                "expected_issue_codes": ["unsupported_zarr_version"],
            },
            {
                "case_id": "consolidated_only",
                "store": "consolidated_only.zarr",
                "expected_status": "success",
                "expected_groups": ["/"],
                "expected_arrays": {"temperature": {"shape": [3], "chunks": [3]}},
                "expected_units": {"temperature": "normalized_ucum"},
                "expected_issue_codes": [],
            },
            {
                "case_id": "consolidated_conflict",
                "store": "consolidated_conflict.zarr",
                "expected_status": "partial",
                "expected_groups": ["/"],
                "expected_arrays": {"temperature": {"shape": [3], "chunks": [3]}},
                "expected_issue_codes": ["partial_extraction", "zarr_consolidated_conflict"],
            },
            {
                "case_id": "unknown_codec",
                "store": "unknown_codec.zarr",
                "expected_status": "success",
                "expected_groups": ["/"],
                "expected_arrays": {"signal": {"compressor": {"id": "future_codec", "level": 7}}},
                "expected_issue_codes": [],
            },
        ],
    }
    (CHALLENGE_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    build_minimal_group()
    build_basic_array()
    build_nested_hierarchy()
    build_physical_metadata()
    build_xarray_coordinates()
    build_coordinate_conflict()
    build_name_only_unknown()
    build_partial_malformed()
    build_malformed_root()
    build_missing_metadata()
    build_zarr_v3()
    build_consolidated_only()
    build_consolidated_conflict()
    build_unknown_codec()
    build_manifest()
    print("Phase 14A Zarr challenge pack built: 14 cases")


if __name__ == "__main__":
    main()
