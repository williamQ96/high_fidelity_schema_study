from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import tarfile
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent
CORPUS_ROOT = ROOT / "testdata" / "zarr_phase14c_external"
ZARR_SOURCE_URL = "https://pypi.org/project/zarr/2.18.7/"


def _reset_store(name: str) -> Path:
    CORPUS_ROOT.mkdir(parents=True, exist_ok=True)
    path = (CORPUS_ROOT / name).resolve()
    if path.parent != CORPUS_ROOT.resolve():
        raise ValueError("Phase 14C store must remain inside the corpus root")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()
    return path


def _source(
    *,
    source_kind: str,
    upstream: str,
    version: str,
    license_name: str,
    source_url: str,
    generation_method: str,
    usage_note: str,
    source_sha256: str | None = None,
) -> dict[str, Any]:
    result = {
        "source_kind": source_kind,
        "upstream": upstream,
        "version": version,
        "license": license_name,
        "source_url": source_url,
        "generation_method": generation_method,
        "usage_note": usage_note,
    }
    if source_sha256 is not None:
        result["source_sha256"] = source_sha256
    return result


def _extract_official_fixture_subset(source_tar: Path) -> tuple[list[str], str]:
    digest = hashlib.sha256(source_tar.read_bytes()).hexdigest()
    valid_root = _reset_store("official_zarr_python_fixture_subset.zarr")
    orphan_root = _reset_store("official_zarr_python_utf8attrs_orphan.zarr")
    selected_members: list[str] = []
    prefix = "zarr-2.18.7/fixture/"
    selected_direct = {
        f"{prefix}.zgroup",
        f"{prefix}.zattrs",
        f"{prefix}flat/.zarray",
        f"{prefix}nested/.zarray",
        f"{prefix}meta/.zarray",
    }
    with tarfile.open(source_tar) as archive:
        for member in archive.getmembers():
            name = member.name
            relative = name.removeprefix(prefix)
            is_group_zero_metadata = (
                name.startswith(f"{prefix}0/")
                and Path(relative).name in {".zgroup", ".zarray", ".zattrs"}
            )
            if name in selected_direct or is_group_zero_metadata:
                file_object = archive.extractfile(member)
                if file_object is None:
                    continue
                destination = valid_root / Path(relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(file_object.read())
                selected_members.append(name)
        orphan_member = archive.getmember(f"{prefix}utf8attrs/.zattrs")
        orphan_file = archive.extractfile(orphan_member)
        if orphan_file is None:
            raise ValueError("official UTF-8 attribute fixture is unavailable")
        (orphan_root / ".zattrs").write_bytes(orphan_file.read())
        selected_members.append(orphan_member.name)
    return sorted(selected_members), digest


def _require_optional_libraries():
    import numcodecs
    import xarray as xr
    import zarr

    if not zarr.__version__.startswith("2."):
        raise RuntimeError("Phase 14C corpus generation requires Zarr Python v2")
    return zarr, xr, numcodecs


def _library_versions() -> dict[str, str]:
    names = ["zarr", "numcodecs", "xarray", "dask", "numpy", "pandas"]
    return {name: importlib.metadata.version(name) for name in names}


def _assert_metadata_only(root: Path) -> None:
    allowed = {".zgroup", ".zarray", ".zattrs", ".zmetadata"}
    non_metadata = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name not in allowed
    ]
    if non_metadata:
        raise ValueError(f"library-produced corpus must be metadata-only: {non_metadata}")


def _remove_chunk_payloads(root: Path) -> int:
    allowed = {".zgroup", ".zarray", ".zattrs", ".zmetadata"}
    removed = 0
    for path in sorted(root.rglob("*"), reverse=True):
        if path.is_file() and path.name not in allowed:
            path.unlink()
            removed += 1
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    return removed


def _build_zarr_library_cases(zarr, numcodecs) -> None:
    root_array = _reset_store("zarr_library_root_array.zarr")
    zarr.open_array(
        str(root_array),
        mode="w",
        shape=(64, 32),
        chunks=(16, 8),
        dtype="<f4",
        compressor=numcodecs.Blosc(cname="zstd", clevel=3, shuffle=numcodecs.Blosc.BITSHUFFLE),
        fill_value=-9999.0,
    )

    hierarchy = _reset_store("zarr_library_group_hierarchy.zarr")
    group = zarr.open_group(str(hierarchy), mode="w")
    group.attrs.update({"title": "Zarr Python generated hierarchy", "source": "Phase 14C"})
    observations = group.create_group("observations")
    observations.attrs["instrument"] = "reference-sensor"
    observations.create_dataset("signal", shape=(12, 8), chunks=(4, 4), dtype="<i2")
    group.create_dataset("quality", shape=(12,), chunks=(12,), dtype="|u1")

    structured = _reset_store("zarr_library_structured_records.zarr")
    structured_group = zarr.open_group(str(structured), mode="w")
    structured_group.create_dataset(
        "records",
        shape=(128,),
        chunks=(32,),
        dtype=np.dtype([("timestamp", "<i8"), ("quality", "|u1"), ("value", "<f4")]),
        compressor=numcodecs.Zlib(level=1),
    )

    nested = _reset_store("zarr_library_nested_separator.zarr")
    nested_group = zarr.open_group(str(nested), mode="w")
    nested_group.create_dataset(
        "image",
        shape=(1024, 1024),
        chunks=(128, 128),
        dtype="|u1",
        dimension_separator="/",
    )

    strings = _reset_store("zarr_library_vlen_utf8.zarr")
    strings_group = zarr.open_group(str(strings), mode="w")
    strings_group.create_dataset(
        "labels",
        shape=(10,),
        chunks=(10,),
        dtype=object,
        object_codec=numcodecs.VLenUTF8(),
    )

    for store in (root_array, hierarchy, structured, nested, strings):
        _assert_metadata_only(store)


def _weather_dataset(xr):
    return xr.Dataset(
        data_vars={
            "temperature": (
                ("time", "latitude", "longitude"),
                np.zeros((4, 3, 5), dtype="<f4"),
                {
                    "standard_name": "air_temperature",
                    "units": "K",
                    "coordinates": "time latitude longitude",
                },
            ),
            "station_name": (
                ("station",),
                np.array(["alpha", "beta"], dtype=object),
                {"long_name": "station label"},
            ),
        },
        coords={
            "time": (
                "time",
                np.arange(4, dtype="<i8"),
                {
                    "standard_name": "time",
                    "axis": "T",
                    "units": "hours since 2024-01-01 00:00:00",
                    "calendar": "standard",
                },
            ),
            "latitude": (
                "latitude",
                np.array([40.0, 41.0, 42.0], dtype="<f4"),
                {"standard_name": "latitude", "axis": "Y", "units": "degrees_north"},
            ),
            "longitude": (
                "longitude",
                np.array([-72.0, -71.0, -70.0, -69.0, -68.0], dtype="<f4"),
                {"standard_name": "longitude", "axis": "X", "units": "degrees_east"},
            ),
            "station": ("station", np.arange(2, dtype="<i4")),
        },
        attrs={"title": "Xarray generated Phase 14C reference dataset", "Conventions": "CF-1.8"},
    )


def _write_xarray_metadata_only(dataset, path: Path, *, consolidated: bool, group: str | None = None) -> None:
    encoding = {
        "temperature": {"chunks": (1, 3, 5)},
        "station_name": {"chunks": (2,)},
        "time": {"chunks": (4,)},
        "latitude": {"chunks": (3,)},
        "longitude": {"chunks": (5,)},
        "station": {"chunks": (2,)},
    }
    dataset.to_zarr(
        str(path),
        group=group,
        mode="w" if group is None else "a",
        compute=False,
        consolidated=consolidated,
        zarr_format=2,
        encoding=encoding,
    )
    _remove_chunk_payloads(path)
    _assert_metadata_only(path)


def _build_xarray_library_cases(zarr, xr) -> None:
    nonconsolidated = _reset_store("xarray_library_nonconsolidated.zarr")
    _write_xarray_metadata_only(_weather_dataset(xr), nonconsolidated, consolidated=False)

    consolidated = _reset_store("xarray_library_consolidated.zarr")
    _write_xarray_metadata_only(_weather_dataset(xr), consolidated, consolidated=True)

    nested = _reset_store("xarray_library_nested_group.zarr")
    zarr.open_group(str(nested), mode="w").attrs["title"] = "Root for nested Xarray group"
    _write_xarray_metadata_only(_weather_dataset(xr), nested, consolidated=False, group="observations")

    dangling = _reset_store("xarray_library_dangling_coordinate.zarr")
    _write_xarray_metadata_only(_weather_dataset(xr), dangling, consolidated=False)
    temperature = zarr.open_group(str(dangling), mode="a")["temperature"]
    temperature.attrs["coordinates"] = "time latitude longitude missing_station_coordinate"
    _assert_metadata_only(dangling)

    malformed = _reset_store("zarr_library_malformed_optional_attrs.zarr")
    group = zarr.open_group(str(malformed), mode="w")
    group.create_dataset("signal", shape=(10,), chunks=(5,), dtype="<f4")
    (malformed / "signal" / ".zattrs").write_text("{not-json}\n", encoding="utf-8")
    _assert_metadata_only(malformed)


def _manifest(selected_members: list[str], source_sha256: str, versions: dict[str, str]) -> dict[str, Any]:
    zarr_library_source = _source(
        source_kind="library_produced",
        upstream="zarr-python",
        version=versions["zarr"],
        license_name="MIT",
        source_url=ZARR_SOURCE_URL,
        generation_method="Created by create_phase14c_zarr_external_corpus.py using Zarr Python APIs without writing array values.",
        usage_note="Metadata-only local store generated from a pinned public library.",
    )
    xarray_library_source = _source(
        source_kind="library_produced",
        upstream="xarray",
        version=versions["xarray"],
        license_name="Apache-2.0",
        source_url="https://docs.xarray.dev/en/v2024.11.0/generated/xarray.Dataset.to_zarr.html",
        generation_method="Created by Xarray Dataset.to_zarr(compute=False, zarr_format=2) using pinned libraries.",
        usage_note="Generated by a pinned public library; any eagerly written non-metadata objects were mechanically removed before corpus inclusion.",
    )
    official_source = _source(
        source_kind="external_public_sdist",
        upstream="zarr-python",
        version="2.18.7",
        license_name="MIT",
        source_url=ZARR_SOURCE_URL,
        source_sha256=source_sha256,
        generation_method="Exact metadata-only subset extracted from the public Zarr Python 2.18.7 source-distribution fixture.",
        usage_note="Only .zgroup, .zarray, and .zattrs documents are retained; fixture chunk payloads are excluded.",
    )
    cases = [
        {
            "case_id": "official_zarr_python_fixture_subset",
            "store": "official_zarr_python_fixture_subset.zarr",
            "classification": "supported",
            "source": official_source,
            "selected_source_members": selected_members[:-1],
            "expected_status": "success",
            "expected_features": ["public source fixture", "groups", "flat and nested dimension separators", "Blosc metadata"],
            "cross_parser": {"zarr": True, "xarray": False},
        },
        {
            "case_id": "official_zarr_python_utf8attrs_orphan",
            "store": "official_zarr_python_utf8attrs_orphan.zarr",
            "classification": "structured_abstention",
            "source": official_source,
            "selected_source_members": [selected_members[-1]],
            "expected_status": "abstained",
            "expected_issue_codes": ["zarr_metadata_missing"],
            "expected_features": ["public source fixture", "UTF-8 attributes without group or array metadata"],
            "cross_parser": {"zarr": True, "xarray": False, "expected_zarr_open": False},
        },
        {
            "case_id": "zarr_library_root_array",
            "store": "zarr_library_root_array.zarr",
            "classification": "supported",
            "source": zarr_library_source,
            "expected_status": "success",
            "expected_features": ["root array", "Blosc compressor", "fill value"],
            "cross_parser": {"zarr": True, "xarray": False},
        },
        {
            "case_id": "zarr_library_group_hierarchy",
            "store": "zarr_library_group_hierarchy.zarr",
            "classification": "supported",
            "source": zarr_library_source,
            "expected_status": "success",
            "expected_features": ["nested group", "group attributes", "multiple arrays"],
            "cross_parser": {"zarr": True, "xarray": False},
        },
        {
            "case_id": "zarr_library_structured_records",
            "store": "zarr_library_structured_records.zarr",
            "classification": "supported",
            "source": zarr_library_source,
            "expected_status": "success",
            "expected_features": ["structured dtype", "Zlib compressor"],
            "cross_parser": {"zarr": True, "xarray": False},
        },
        {
            "case_id": "zarr_library_nested_separator",
            "store": "zarr_library_nested_separator.zarr",
            "classification": "supported",
            "source": zarr_library_source,
            "expected_status": "success",
            "expected_features": ["slash dimension separator", "metadata-only array"],
            "cross_parser": {"zarr": True, "xarray": False},
        },
        {
            "case_id": "zarr_library_vlen_utf8",
            "store": "zarr_library_vlen_utf8.zarr",
            "classification": "supported",
            "source": zarr_library_source,
            "expected_status": "success",
            "expected_features": ["object dtype", "VLenUTF8 object codec"],
            "expected_unknown_fields": ["labels"],
            "cross_parser": {"zarr": True, "xarray": False},
        },
        {
            "case_id": "xarray_library_nonconsolidated",
            "store": "xarray_library_nonconsolidated.zarr",
            "classification": "supported",
            "source": xarray_library_source,
            "expected_status": "success",
            "expected_features": ["Xarray metadata", "non-consolidated", "coordinates", "object string variable"],
            "cross_parser": {"zarr": True, "xarray": True, "consolidated": False},
        },
        {
            "case_id": "xarray_library_consolidated",
            "store": "xarray_library_consolidated.zarr",
            "classification": "supported",
            "source": xarray_library_source,
            "expected_status": "success",
            "expected_features": ["Xarray metadata", "consolidated metadata", "coordinates"],
            "cross_parser": {"zarr": True, "xarray": True, "consolidated": True},
        },
        {
            "case_id": "xarray_library_nested_group",
            "store": "xarray_library_nested_group.zarr",
            "classification": "supported",
            "source": xarray_library_source,
            "expected_status": "success",
            "expected_features": ["Xarray metadata", "nested group", "coordinates"],
            "cross_parser": {"zarr": True, "xarray": True, "consolidated": False, "group": "observations"},
        },
        {
            "case_id": "xarray_library_dangling_coordinate",
            "store": "xarray_library_dangling_coordinate.zarr",
            "classification": "unsupported_feature",
            "source": {
                **xarray_library_source,
                "source_kind": "library_derived_edge",
                "generation_method": "Generated by Xarray, then one explicit coordinates attribute was changed to include a missing target.",
            },
            "expected_status": "success",
            "expected_gap_codes": ["unresolved_coordinate_reference"],
            "expected_features": ["Xarray metadata", "dangling explicit coordinate reference"],
            "cross_parser": {"zarr": True, "xarray": True, "consolidated": False},
        },
        {
            "case_id": "zarr_library_malformed_optional_attrs",
            "store": "zarr_library_malformed_optional_attrs.zarr",
            "classification": "malformed_edge",
            "source": {
                **zarr_library_source,
                "source_kind": "library_derived_edge",
                "generation_method": "Generated by Zarr Python, then the optional array .zattrs document was deliberately malformed.",
            },
            "expected_status": "partial",
            "expected_issue_codes": ["partial_extraction", "zarr_metadata_malformed"],
            "expected_features": ["valid library-generated array metadata", "malformed optional attributes"],
            "cross_parser": {"zarr": True, "xarray": False, "expected_zarr_open": False},
        },
    ]
    return {
        "experiment_id": "phase14c_zarr_external_conformance",
        "corpus_claim_boundary": "This corpus combines one public-source metadata subset with pinned library-produced metadata-only stores; it is not representative of the full Zarr ecosystem.",
        "generation_environment": versions,
        "chunk_payload_policy": "No chunk payloads are written, copied, decoded, or used for canonical claims.",
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Phase 14C external/library-produced Zarr v2 corpus.")
    parser.add_argument("--official-zarr-sdist", required=True, type=Path)
    args = parser.parse_args()

    zarr, xr, numcodecs = _require_optional_libraries()
    selected_members, source_sha256 = _extract_official_fixture_subset(args.official_zarr_sdist)
    _build_zarr_library_cases(zarr, numcodecs)
    _build_xarray_library_cases(zarr, xr)
    versions = _library_versions()
    manifest = _manifest(selected_members, source_sha256, versions)
    (CORPUS_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Phase 14C external/library-produced Zarr corpus built: {len(manifest['cases'])} cases")


if __name__ == "__main__":
    main()
