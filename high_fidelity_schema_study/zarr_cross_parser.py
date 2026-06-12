"""Optional dev-only Zarr/Xarray metadata conformance helpers.

These helpers are supporting evidence only. They never read array values and
are not part of the canonical extractor routing path.
"""

from __future__ import annotations

import importlib.metadata
import math
from pathlib import Path
from typing import Any, Dict, Optional


def _normalize(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            value = value.item()
        except ValueError:
            pass
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, dict):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


def _dtype_metadata(dtype: Any) -> Any:
    return _normalize(dtype.descr if dtype.names else dtype.str)


def _codec_metadata(codec: Any) -> Any:
    return _normalize(codec.get_config()) if codec is not None else None


def _array_metadata(array: Any) -> Dict[str, Any]:
    return {
        "dtype": _dtype_metadata(array.dtype),
        "shape": list(array.shape),
        "chunks": list(array.chunks),
        "compressor": _codec_metadata(array.compressor),
        "fill_value": _normalize(array.fill_value),
        "order": array.order,
        "filters": [_codec_metadata(item) for item in array.filters] if array.filters else None,
        "attributes": _normalize(array.attrs.asdict()),
    }


def collect_zarr_metadata(path: Path) -> Dict[str, Any]:
    try:
        import zarr
    except ImportError:
        return {"available": False, "parser": "zarr", "reason": "dependency_unavailable"}

    result: Dict[str, Any] = {
        "available": True,
        "parser": "zarr",
        "version": importlib.metadata.version("zarr"),
        "status": "success",
        "groups": {},
        "arrays": {},
        "value_reads": 0,
    }
    try:
        root = zarr.open(str(path), mode="r")
        if isinstance(root, zarr.Array):
            result["arrays"]["/"] = _array_metadata(root)
            return result

        result["groups"]["/"] = {"attributes": _normalize(root.attrs.asdict())}

        def visitor(name: str, item: Any) -> None:
            if isinstance(item, zarr.Array):
                result["arrays"][name] = _array_metadata(item)
            elif isinstance(item, zarr.Group):
                result["groups"][name] = {"attributes": _normalize(item.attrs.asdict())}

        root.visititems(visitor)
    except Exception as exc:
        result.update({"status": "error", "error_type": type(exc).__name__, "error": str(exc)})
    return result


def collect_xarray_metadata(
    path: Path,
    *,
    consolidated: Optional[bool] = None,
    group: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        import xarray as xr
    except ImportError:
        return {"available": False, "parser": "xarray", "reason": "dependency_unavailable"}

    result: Dict[str, Any] = {
        "available": True,
        "parser": "xarray",
        "version": importlib.metadata.version("xarray"),
        "status": "success",
        "variables": {},
        "dimensions": {},
        "value_reads": 0,
    }
    try:
        dataset = xr.open_zarr(
            str(path),
            consolidated=consolidated,
            group=group,
            chunks=None,
            decode_cf=False,
        )
        try:
            result["dimensions"] = {str(name): int(size) for name, size in dataset.sizes.items()}
            result["variables"] = {
                str(name): {
                    "dimensions": list(variable.dims),
                    "shape": list(variable.shape),
                    "dtype": _dtype_metadata(variable.dtype),
                    "attributes": _normalize(dict(variable.attrs)),
                }
                for name, variable in dataset.variables.items()
            }
        finally:
            dataset.close()
    except Exception as exc:
        result.update({"status": "error", "error_type": type(exc).__name__, "error": str(exc)})
    return result


def collect_cross_parser_metadata(path: Path, options: Dict[str, Any]) -> Dict[str, Any]:
    result = {"role": "dev_only_supporting_evidence", "value_reads": 0}
    if options.get("zarr"):
        result["zarr"] = collect_zarr_metadata(path)
    if options.get("xarray"):
        result["xarray"] = collect_xarray_metadata(
            path,
            consolidated=options.get("consolidated"),
            group=options.get("group"),
        )
    return result
