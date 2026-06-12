# Phase 14C External And Library-Produced Zarr Corpus

This metadata-only corpus combines:

- an exact metadata subset from the public `zarr-python 2.18.7` source-distribution fixture;
- stores produced by pinned `zarr`, `numcodecs`, and `xarray` APIs;
- two explicitly labeled library-derived edge cases.

It is not representative of the full Zarr ecosystem.

## External Source

- Upstream: `zarr-python`
- Version: `2.18.7`
- Source: `https://pypi.org/project/zarr/2.18.7/`
- License: MIT
- Source archive SHA-256 and selected fixture members: recorded in `manifest.json`

Only `.zgroup`, `.zarray`, and `.zattrs` documents from the selected public fixture are retained. No upstream fixture chunk payloads are copied.

## Library Generation Environment

- `zarr 2.18.7`
- `numcodecs 0.15.1`
- `xarray 2024.11.0`
- `dask 2024.11.2`

Xarray stores are created through `Dataset.to_zarr(compute=False, zarr_format=2)`. Xarray may still eagerly write some NumPy-backed objects, so the corpus generator mechanically removes every non-metadata object before inclusion.

## Rebuild

Create an isolated environment containing the pinned libraries, download the public `zarr 2.18.7` source distribution, then run:

```text
python create_phase14c_zarr_external_corpus.py --official-zarr-sdist <path-to-zarr-2.18.7.tar.gz>
```

`manifest.json` is the authoritative provenance, expectation, source, license, and limitation overlay.
