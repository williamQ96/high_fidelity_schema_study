# Phase 14C: External And Library-Produced Zarr Conformance

Date: 2026-06-11

## Purpose

Phase 14C validates the canonical local Zarr v2 metadata extractor against a small externally sourced and pinned-library-produced corpus. Optional `zarr` and `xarray` parsing is used only as development-time supporting evidence. It does not override raw metadata preservation or canonical extraction outcomes.

## Corpus

The metadata-only 12-case corpus contains:

- 2 cases derived from the official `zarr-python 2.18.7` source distribution;
- 8 stores generated through pinned `zarr`, `numcodecs`, and `xarray` APIs;
- 2 explicitly labeled library-derived edge cases.

The manifest records source category, upstream project, version, license, source URL, generation method, usage note, expected behavior, and the official source archive SHA-256. No chunk payload is retained or read. This is a targeted compatibility corpus, not a representative sample of the Zarr ecosystem.

## Canonical Result

| Metric | Result |
| --- | ---: |
| Supported compatibility rate | `1.0000` |
| Structured abstention quality | `1.0000` |
| Unsupported-feature visibility | `1.0000` |
| Malformed-edge quality | `1.0000` |
| Source documentation completeness | `1.0000` |
| Evidence coverage | `1.0000` |
| Path portability accuracy | `1.0000` |
| Chunk-payload non-claim rate | `1.0000` |
| Unsupported promotion count | `0` |
| True bug count | `0` |

The official fixture subset extracts successfully, while the official orphan `.zattrs` fixture produces the expected structured abstention. Library-produced structured dtypes, nested layouts, consolidated metadata, and Xarray dimensions remain supported. The dangling-coordinate and malformed-optional-attributes cases remain explicit rather than being promoted.

## Optional Cross-Parser Evidence

The pinned development environment assessed all 12 cases with `zarr 2.18.7` and 4 intended Xarray cases with `xarray 2024.11.0`.

| Metric | Result |
| --- | ---: |
| Zarr cases assessed | `12` |
| Raw physical metadata conformance rate | `0.8333` |
| Xarray cases assessed | `4` |
| Xarray structural conformance rate | `1.0000` |
| Total observed differences | `5` |
| Unexplained differences | `0` |

The five observed Zarr-parser differences are classified as:

- 4 `parser_default_materialization` differences, where the parser adds the omitted Blosc default `blocksize=0`;
- 1 `encoded_fill_value_interpretation` difference, where a structured fill value is interpreted from its encoded raw metadata form.

These are parser interpretation/default differences, not canonical extractor bugs. The canonical extractor correctly preserves the physical metadata documents as stored.

## Reproducibility And Boundaries

- Corpus provenance and limitations are recorded in `testdata/zarr_phase14c_external/manifest.json`.
- Generated results live only under `data/experiments/phase14c_zarr_external_conformance/`.
- Cross-parser dependencies are optional and absent from the canonical extraction path.
- Xarray may eagerly write NumPy-backed chunks even with `compute=False`; the corpus generator mechanically removes every non-metadata object.
- No value-level statistics, chunk-key schema claims, remote stores, Zarr v3, or full Xarray reconstruction are claimed.
- Frozen benchmark artifacts, paper tables, figures, manuscript, and headline metrics remain unchanged.
- Full repository regression suite at completion: `125 passed`.

## Next Gate

Phase 14C does not identify a compatibility defect requiring a canonical extractor change. The next expansion should therefore remain evidence-led: either add a larger independently curated local Zarr v2 corpus or return to a standards-backed adjacent format such as Parquet/Arrow. Remote-store support, Zarr v3, and bounded chunk sampling remain deferred.
