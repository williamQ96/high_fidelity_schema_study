# Phase 14A: Zarr Directory-Store Intake

Date: 2026-06-11

## Scope

Phase 14A proves that the deterministic registry and structured-outcome contracts can support a directory-backed scientific format. It adds local directory-store Zarr v2 metadata extraction without introducing a heavy Zarr/Xarray dependency or reading chunk payloads.

Implemented capabilities:

- registry detection from `.zgroup`, `.zarray`, `.zmetadata`, and `zarr.json` version signals;
- resource-kind-aware routing for local directory stores;
- group and array hierarchy discovery;
- `.zarray` dtype, shape, chunks, compressor, fill value, order, filters, and dimension separator extraction;
- explicit `.zattrs` extraction;
- bounded `_ARRAY_DIMENSIONS` and CF-like coordinate, calendar, unit, and temporal handling;
- metadata-relative evidence references;
- structured partial, failed, and abstained outcomes for malformed, missing, conflicting, and unsupported metadata;
- generic CLI and GUI scratch integration.

## Controlled Result

The isolated 14-case challenge pack covers valid hierarchy and physical metadata, explicit Xarray-compatible metadata, convention conflicts, name-only unknowns, partial malformed stores, malformed roots, missing metadata, Zarr v3, consolidated-only metadata, consolidated/direct conflicts, and unknown codecs.

All declared controlled metrics are `1.0000`, including store detection, routing, physical metadata, evidence coverage, temporal abstention, and path portability. Unsupported promotion count: `0`.

Generated artifacts:

- `testdata/zarr_phase14a/`
- `data/experiments/phase14a_zarr/`

## Deterministic Boundaries

- Only local directory-store Zarr v2 metadata is supported.
- Chunk payloads are never read or decoded.
- Value-level statistics remain explicitly unknown because chunk payloads are not read.
- Remote stores, Zarr v3, writing/repair, and full Xarray semantic reconstruction are out of scope.
- Unknown codec metadata is preserved but never executed.
- Names alone do not create coordinate, temporal, logical, or semantic claims.
- Metadata-only temporal candidates do not become a canonical time axis without samples.
- Conflicting convention metadata remains `conflicted` or partial rather than being promoted.

## Verification

- Regression suite: `109 passed`.
- Phase 14A controlled evaluator: all declared metrics `1.0000`; unsupported promotion count `0`.
- Generated Phase 14A artifacts contain no local absolute paths.
- Frozen benchmark, manuscript, paper tables, and figures remain unchanged.

## Recommended Next Step

Phase 14B should validate this bounded extractor against a separately curated real-world local Zarr v2 corpus. That validation should measure compatibility gaps before considering optional standards-library conformance checks, remote-store intake, or any broader support claim.
