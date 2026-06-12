from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any


ROOT = Path(__file__).resolve().parent
CORPUS_ROOT = ROOT / "testdata" / "zarr_phase14b_compatibility"


def _store(name: str) -> Path:
    CORPUS_ROOT.mkdir(parents=True, exist_ok=True)
    path = (CORPUS_ROOT / name).resolve()
    if path.parent != CORPUS_ROOT.resolve():
        raise ValueError("compatibility store must remain inside the Phase 14B corpus root")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()
    return path


def _write_json(root: Path, relative: str, payload: Any) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(root: Path, relative: str, payload: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _write_dummy_chunk(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"PHASE14B-DUMMY-CHUNK-NOT-VALID-DATA")


def _group(root: Path, relative: str = "", attrs: dict[str, Any] | None = None) -> None:
    prefix = f"{relative}/" if relative else ""
    _write_json(root, f"{prefix}.zgroup", {"zarr_format": 2})
    if attrs is not None:
        _write_json(root, f"{prefix}.zattrs", attrs)


def _array(
    root: Path,
    relative: str,
    *,
    dtype: Any = "<f4",
    shape: list[int] | None = None,
    chunks: list[int] | None = None,
    compressor: Any = None,
    fill_value: Any = None,
    order: str = "C",
    filters: Any = None,
    dimension_separator: str = ".",
    attrs: dict[str, Any] | None = None,
    chunk_keys: list[str] | None = None,
) -> None:
    shape = [3] if shape is None else shape
    chunks = list(shape) if chunks is None else chunks
    prefix = f"{relative}/" if relative else ""
    _write_json(
        root,
        f"{prefix}.zarray",
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
        _write_json(root, f"{prefix}.zattrs", attrs)
    for chunk_key in chunk_keys or []:
        _write_dummy_chunk(root, f"{prefix}{chunk_key}")


def _consolidate(root: Path) -> None:
    metadata: dict[str, Any] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name in {".zgroup", ".zarray", ".zattrs"}:
            metadata[path.relative_to(root).as_posix()] = json.loads(path.read_text(encoding="utf-8"))
    _write_json(root, ".zmetadata", {"zarr_consolidated_format": 1, "metadata": metadata})


def build_root_array_numpy_style() -> None:
    root = _store("root_array_numpy_style.zarr")
    _array(root, "", dtype="<f8", shape=[64, 32], chunks=[16, 16], chunk_keys=["0.0", "0.1"])


def build_xarray_weather_nonconsolidated() -> None:
    root = _store("xarray_weather_nonconsolidated.zarr")
    _group(root, attrs={"title": "Regional weather reference layout", "Conventions": "CF-1.8"})
    _array(
        root,
        "time",
        dtype="<i8",
        shape=[24],
        chunks=[24],
        attrs={
            "_ARRAY_DIMENSIONS": ["time"],
            "standard_name": "time",
            "axis": "T",
            "units": "hours since 2024-01-01 00:00:00",
            "calendar": "proleptic_gregorian",
        },
        chunk_keys=["0"],
    )
    _array(
        root,
        "latitude",
        shape=[180],
        chunks=[180],
        attrs={
            "_ARRAY_DIMENSIONS": ["latitude"],
            "standard_name": "latitude",
            "axis": "Y",
            "units": "degrees_north",
        },
        chunk_keys=["0"],
    )
    _array(
        root,
        "longitude",
        shape=[360],
        chunks=[360],
        attrs={
            "_ARRAY_DIMENSIONS": ["longitude"],
            "standard_name": "longitude",
            "axis": "X",
            "units": "degrees_east",
        },
        chunk_keys=["0"],
    )
    _array(
        root,
        "temperature",
        shape=[24, 180, 360],
        chunks=[1, 90, 180],
        compressor={"id": "blosc", "cname": "zstd", "clevel": 5, "shuffle": 2, "blocksize": 0},
        fill_value="NaN",
        attrs={
            "_ARRAY_DIMENSIONS": ["time", "latitude", "longitude"],
            "coordinates": "time latitude longitude",
            "standard_name": "air_temperature",
            "units": "K",
        },
        chunk_keys=["0.0.0"],
    )


def build_xarray_ocean_consolidated() -> None:
    root = _store("xarray_ocean_consolidated.zarr")
    _group(root, attrs={"title": "Ocean profile reference layout"})
    _array(
        root,
        "depth",
        shape=[50],
        chunks=[50],
        attrs={
            "_ARRAY_DIMENSIONS": ["depth"],
            "standard_name": "depth",
            "axis": "Z",
            "positive": "down",
            "units": "m",
        },
    )
    _array(
        root,
        "salinity",
        shape=[8, 50],
        chunks=[1, 50],
        compressor={"id": "zlib", "level": 4},
        fill_value=-9999.0,
        attrs={
            "_ARRAY_DIMENSIONS": ["profile", "depth"],
            "coordinates": "depth",
            "standard_name": "sea_water_salinity",
            "units": "1",
        },
        chunk_keys=["0.0"],
    )
    _consolidate(root)


def build_nested_instrument_groups() -> None:
    root = _store("nested_instrument_groups.zarr")
    _group(root, attrs={"title": "Grouped station reference layout"})
    for station in ("station_a", "station_b"):
        _group(root, station, attrs={"station_id": station.upper()})
        _array(
            root,
            f"{station}/qc",
            dtype="|u1",
            shape=[10],
            chunks=[10],
            attrs={"_ARRAY_DIMENSIONS": ["record"], "long_name": "quality flag"},
        )
        _array(
            root,
            f"{station}/measurement",
            shape=[10],
            chunks=[5],
            attrs={
                "_ARRAY_DIMENSIONS": ["record"],
                **({"coordinates": "qc"} if station == "station_a" else {}),
                "long_name": "instrument measurement",
            },
        )


def build_scalar_and_zero_length() -> None:
    root = _store("scalar_and_zero_length.zarr")
    _group(root)
    _array(root, "scalar", dtype="<i4", shape=[], chunks=[], fill_value=0)
    _array(root, "empty", dtype="<f4", shape=[0], chunks=[1024])


def build_structured_dtype_records() -> None:
    root = _store("structured_dtype_records.zarr")
    _group(root)
    _array(
        root,
        "records",
        dtype=[["timestamp", "<i8"], ["quality", "|u1"], ["value", "<f4"]],
        shape=[128],
        chunks=[32],
        compressor={"id": "zlib", "level": 1},
        chunk_keys=["0"],
    )


def build_object_vlen_utf8() -> None:
    root = _store("object_vlen_utf8.zarr")
    _group(root)
    _array(
        root,
        "labels",
        dtype="|O",
        shape=[12],
        chunks=[12],
        filters=[{"id": "vlen-utf8"}],
        chunk_keys=["0"],
    )


def build_slash_separator_tree() -> None:
    root = _store("slash_separator_tree.zarr")
    _group(root)
    _array(
        root,
        "image",
        dtype="|u1",
        shape=[2048, 2048],
        chunks=[256, 256],
        dimension_separator="/",
        chunk_keys=["0/0", "0/1", "1/0"],
    )


def build_special_fill_values() -> None:
    root = _store("special_fill_values.zarr")
    _group(root)
    _array(root, "nan_fill", fill_value="NaN")
    _array(root, "positive_infinity_fill", fill_value="Infinity")


def build_unknown_codec_metadata() -> None:
    root = _store("unknown_codec_metadata.zarr")
    _group(root)
    _array(
        root,
        "signal",
        compressor={"id": "site.custom-codec", "configuration": {"level": 7}},
        filters=[{"id": "site.custom-filter"}],
    )


def build_unresolved_coordinate_reference() -> None:
    root = _store("unresolved_coordinate_reference.zarr")
    _group(root)
    _array(
        root,
        "lat",
        attrs={
            "_ARRAY_DIMENSIONS": ["lat"],
            "standard_name": "latitude",
            "units": "degrees_north",
        },
    )
    _array(
        root,
        "measurement",
        attrs={
            "_ARRAY_DIMENSIONS": ["lat"],
            "coordinates": "lat missing_lon",
        },
    )


def build_dimension_conflict_group() -> None:
    root = _store("dimension_conflict_group.zarr")
    _group(root)
    _array(root, "first", shape=[3], attrs={"_ARRAY_DIMENSIONS": ["record"]})
    _array(root, "second", shape=[4], attrs={"_ARRAY_DIMENSIONS": ["record"]})


def build_stale_consolidated_metadata() -> None:
    root = _store("stale_consolidated_metadata.zarr")
    _group(root)
    _array(root, "temperature", shape=[3], chunks=[3])
    _consolidate(root)
    _array(root, "temperature", shape=[4], chunks=[4])


def build_malformed_optional_attrs() -> None:
    root = _store("malformed_optional_attrs.zarr")
    _group(root)
    _array(root, "valid")
    _write_text(root, "valid/.zattrs", "{not-json}\n")


def build_malformed_only_array() -> None:
    root = _store("malformed_only_array.zarr")
    _write_text(root, ".zarray", "{not-json}\n")


def build_zarr_v3_reference() -> None:
    root = _store("zarr_v3_reference.zarr")
    _write_json(root, "zarr.json", {"zarr_format": 3, "node_type": "group"})


def build_empty_suffix_only() -> None:
    _store("empty_suffix_only.zarr")


def build_manifest() -> None:
    cases = [
        {
            "case_id": "root_array_numpy_style",
            "store": "root_array_numpy_style.zarr",
            "producer_profile": "standalone NumPy-style root array",
            "classification": "supported",
            "expected_status": "success",
            "expected_fields": ["/"],
            "expected_physical": {"/": {"dtype": "<f8", "shape": [64, 32], "chunks": [16, 16]}},
        },
        {
            "case_id": "xarray_weather_nonconsolidated",
            "store": "xarray_weather_nonconsolidated.zarr",
            "producer_profile": "Xarray-style non-consolidated multidimensional dataset",
            "classification": "supported",
            "expected_status": "success",
            "expected_fields": ["time", "latitude", "longitude", "temperature"],
            "expected_coordinate_fields": ["time", "latitude", "longitude"],
            "expected_physical": {
                "temperature": {
                    "shape": [24, 180, 360],
                    "chunks": [1, 90, 180],
                    "compressor": {"id": "blosc", "cname": "zstd", "clevel": 5, "shuffle": 2, "blocksize": 0},
                    "fill_value": "NaN",
                }
            },
        },
        {
            "case_id": "xarray_ocean_consolidated",
            "store": "xarray_ocean_consolidated.zarr",
            "producer_profile": "Xarray-style consolidated ocean dataset",
            "classification": "supported",
            "expected_status": "success",
            "expected_fields": ["depth", "salinity"],
            "expected_coordinate_fields": ["depth"],
            "expected_physical": {"salinity": {"compressor": {"id": "zlib", "level": 4}}},
        },
        {
            "case_id": "nested_instrument_groups",
            "store": "nested_instrument_groups.zarr",
            "producer_profile": "Nested grouped station dataset with repeated variable names",
            "classification": "supported",
            "expected_status": "success",
            "expected_groups": ["/", "station_a", "station_b"],
            "expected_fields": [
                "station_a/qc",
                "station_a/measurement",
                "station_b/qc",
                "station_b/measurement",
            ],
            "expected_coordinate_fields": ["station_a/qc"],
            "expected_not_coordinate_fields": ["station_b/qc"],
        },
        {
            "case_id": "scalar_and_zero_length",
            "store": "scalar_and_zero_length.zarr",
            "producer_profile": "Scalar and empty scientific arrays",
            "classification": "supported",
            "expected_status": "success",
            "expected_fields": ["scalar", "empty"],
            "expected_physical": {
                "scalar": {"shape": [], "chunks": []},
                "empty": {"shape": [0], "chunks": [1024]},
            },
        },
        {
            "case_id": "structured_dtype_records",
            "store": "structured_dtype_records.zarr",
            "producer_profile": "NumPy structured-record array",
            "classification": "supported",
            "expected_status": "success",
            "expected_fields": ["records"],
            "expected_physical": {
                "records": {
                    "dtype": [["timestamp", "<i8"], ["quality", "|u1"], ["value", "<f4"]],
                    "shape": [128],
                }
            },
        },
        {
            "case_id": "object_vlen_utf8",
            "store": "object_vlen_utf8.zarr",
            "producer_profile": "Object array with vlen UTF-8 filter metadata",
            "classification": "supported",
            "expected_status": "success",
            "expected_fields": ["labels"],
            "expected_physical": {"labels": {"dtype": "|O", "filters": [{"id": "vlen-utf8"}]}},
            "expected_unknown_fields": ["labels"],
        },
        {
            "case_id": "slash_separator_tree",
            "store": "slash_separator_tree.zarr",
            "producer_profile": "Large image array with slash-separated chunk keys",
            "classification": "supported",
            "expected_status": "success",
            "expected_fields": ["image"],
            "expected_physical": {"image": {"dimension_separator": "/"}},
            "expected_pruned_array_directories_min": 1,
        },
        {
            "case_id": "special_fill_values",
            "store": "special_fill_values.zarr",
            "producer_profile": "Floating arrays with JSON special fill values",
            "classification": "supported",
            "expected_status": "success",
            "expected_fields": ["nan_fill", "positive_infinity_fill"],
            "expected_physical": {
                "nan_fill": {"fill_value": "NaN"},
                "positive_infinity_fill": {"fill_value": "Infinity"},
            },
        },
        {
            "case_id": "unknown_codec_metadata",
            "store": "unknown_codec_metadata.zarr",
            "producer_profile": "Site-defined codec metadata preserved without execution",
            "classification": "supported",
            "expected_status": "success",
            "expected_fields": ["signal"],
            "expected_physical": {
                "signal": {
                    "compressor": {"id": "site.custom-codec", "configuration": {"level": 7}},
                    "filters": [{"id": "site.custom-filter"}],
                }
            },
            "expected_unknown_fields": ["signal"],
        },
        {
            "case_id": "unresolved_coordinate_reference",
            "store": "unresolved_coordinate_reference.zarr",
            "producer_profile": "Xarray-style dataset with one missing coordinate target",
            "classification": "unsupported_feature",
            "expected_status": "success",
            "expected_fields": ["lat", "measurement"],
            "expected_coordinate_fields": ["lat"],
            "expected_gap_codes": ["unresolved_coordinate_reference"],
        },
        {
            "case_id": "dimension_conflict_group",
            "store": "dimension_conflict_group.zarr",
            "producer_profile": "Inconsistent Xarray dimension-size declarations",
            "classification": "unsupported_feature",
            "expected_status": "success",
            "expected_fields": ["first", "second"],
            "expected_gap_codes": ["dimension_size_conflict"],
        },
        {
            "case_id": "stale_consolidated_metadata",
            "store": "stale_consolidated_metadata.zarr",
            "producer_profile": "Direct metadata newer than stale consolidated metadata",
            "classification": "unsupported_feature",
            "expected_status": "partial",
            "expected_fields": ["temperature"],
            "expected_issue_codes": ["partial_extraction", "zarr_consolidated_conflict"],
            "expected_physical": {"temperature": {"shape": [4], "chunks": [4]}},
        },
        {
            "case_id": "malformed_optional_attrs",
            "store": "malformed_optional_attrs.zarr",
            "producer_profile": "Valid array with malformed optional attributes",
            "classification": "malformed_failure",
            "expected_status": "partial",
            "expected_fields": ["valid"],
            "expected_issue_codes": ["partial_extraction", "zarr_metadata_malformed"],
        },
        {
            "case_id": "malformed_only_array",
            "store": "malformed_only_array.zarr",
            "producer_profile": "Malformed root array metadata",
            "classification": "malformed_failure",
            "expected_status": "failed",
            "expected_fields": [],
            "expected_issue_codes": ["zarr_metadata_malformed"],
        },
        {
            "case_id": "zarr_v3_reference",
            "store": "zarr_v3_reference.zarr",
            "producer_profile": "Recognized Zarr v3 group",
            "classification": "unsupported_feature",
            "expected_status": "abstained",
            "expected_fields": [],
            "expected_issue_codes": ["unsupported_zarr_version"],
        },
        {
            "case_id": "empty_suffix_only",
            "store": "empty_suffix_only.zarr",
            "producer_profile": "Directory suffix without spec-backed metadata",
            "classification": "structured_abstention",
            "expected_status": "abstained",
            "expected_fields": [],
            "expected_issue_codes": ["zarr_metadata_missing"],
        },
    ]
    manifest = {
        "experiment_id": "phase14b_zarr_compatibility",
        "corpus_origin": "locally reconstructed producer-shaped Zarr v2 reference layouts",
        "corpus_claim_boundary": "This is a realistic compatibility corpus, not a downloaded representative ecosystem sample.",
        "cases": cases,
    }
    (CORPUS_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    build_root_array_numpy_style()
    build_xarray_weather_nonconsolidated()
    build_xarray_ocean_consolidated()
    build_nested_instrument_groups()
    build_scalar_and_zero_length()
    build_structured_dtype_records()
    build_object_vlen_utf8()
    build_slash_separator_tree()
    build_special_fill_values()
    build_unknown_codec_metadata()
    build_unresolved_coordinate_reference()
    build_dimension_conflict_group()
    build_stale_consolidated_metadata()
    build_malformed_optional_attrs()
    build_malformed_only_array()
    build_zarr_v3_reference()
    build_empty_suffix_only()
    build_manifest()
    print("Phase 14B Zarr compatibility corpus built: 17 cases")


if __name__ == "__main__":
    main()
