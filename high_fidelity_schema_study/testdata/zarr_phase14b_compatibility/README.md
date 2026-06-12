# Phase 14B Zarr Compatibility Corpus

This directory contains a locally reconstructed, producer-shaped Zarr compatibility corpus.

It models common local Zarr v2 layouts seen in NumPy/Zarr and Xarray-style workflows, but it is not a downloaded or statistically representative ecosystem sample. The corpus exists to test compatibility boundaries, structured outcomes, evidence, and unsupported-promotion behavior.

Coverage includes:

- standalone root arrays;
- grouped stores and repeated names across groups;
- consolidated and non-consolidated Xarray-style metadata;
- coordinate arrays and `_ARRAY_DIMENSIONS`;
- structured dtypes, object/vlen metadata, scalars, and empty arrays;
- compressor, filter, special fill-value, and slash-separated chunk metadata;
- unresolved references, dimension conflicts, stale consolidated metadata;
- malformed metadata, Zarr v3, and suffix-only directories.

Several stores contain dummy chunk keys with intentionally invalid bytes. The metadata-only extractor must never decode them or use them to create schema or value-level claims.

`manifest.json` is the authoritative expectation and classification overlay.
