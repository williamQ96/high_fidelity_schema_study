# Phase 14: Zarr / Xarray-Compatible Scientific Array Extraction

Date: 2026-06-11

Status: Phase 14A, Phase 14B, and Phase 14C implemented. Local directory-store Zarr v2 metadata is registry-detected and extracted through a spec-backed, dependency-light reader, with separate producer-shaped and external/library-produced compatibility corpora. Optional cross-parser evidence found no unexplained conformance differences. Remote stores, chunk payload decoding, Zarr v3, and full Xarray reconstruction remain deferred.

## Goal

Add Zarr as the next deterministic, registry-native scientific-array format without weakening the guarantees established by Phase 12 and Phase 13.

```text
Zarr store
  -> resource/store intake
  -> deterministic Zarr version and metadata detection
  -> registered Zarr v2 extractor
  -> groups, arrays, physical metadata, and explicit attributes
  -> convention-backed coordinate/temporal/unit validation
  -> evidence-grounded structured outcome
  -> CLI, GUI scratch path, and isolated evaluator
```

Phase 14 must not use semantic inference to create arrays, dimensions, coordinates, or physical fields.

## Why Zarr Is The Natural Next Step

Zarr is adjacent to NetCDF/CF in the scientific-array ecosystem but introduces a meaningfully different physical substrate:

- array and group metadata are represented as structured JSON;
- stores are commonly directories or object-store key spaces rather than single files;
- chunk shape, compressor, filters, fill value, order, and dimension separator are first-class physical metadata;
- Xarray-compatible stores may encode dimension names and CF-like attributes that can reuse the existing interpretation and validation subsystems;
- metadata-first extraction can establish useful physical schema without decoding every chunk payload.

This makes Zarr a strong test of the registry architecture. It expands scientific format coverage while forcing a careful resource-intake extension, rather than increasing agent autonomy.

## Current Environment And Dependency Position

At planning time:

- `zarr`, `xarray`, and `numcodecs` are not installed;
- `fsspec` is available.

The first implementation should therefore prefer a small, structured, metadata-only Zarr v2 reader for local directory stores using JSON parsing and existing project contracts. Optional library-backed conformance checks may be added later, but missing optional dependencies must produce structured issues rather than silent behavior changes.

No remote object-store, authentication, or broad cloud robustness claim is part of the first Phase 14 acceptance gate.

## Scope

### In Scope

- Zarr v2 first;
- local directory stores first;
- explicit detection of `.zgroup`, `.zarray`, `.zattrs`, and optional consolidated `.zmetadata`;
- nested group and array discovery;
- extraction of:
  - array path and name;
  - dtype;
  - shape;
  - chunks;
  - order;
  - compressor metadata;
  - filters;
  - fill value;
  - dimension separator;
  - explicit attributes;
- preservation of raw metadata values in portable JSON-compatible form;
- explicit evidence for every accepted group, array, physical property, and promoted convention-backed claim;
- reuse of the central registry, structured outcome, temporal semantics, unit normalization, evidence/provenance model, generic CLI, and GUI scratch path;
- isolated challenge data and experiment artifacts.

### Convention-Backed Interpretation

Coordinate, temporal, and unit claims may be promoted only when explicit and internally consistent metadata supports them.

Candidate evidence includes:

- Xarray `_ARRAY_DIMENSIONS`;
- explicit `coordinates` references;
- CF-style `standard_name`, `long_name`, `axis`, `units`, `calendar`, and `bounds`;
- deterministic array/group relationships derived from store paths and metadata documents.

Required behavior:

- `_ARRAY_DIMENSIONS` may support dimension labels but must not invent missing arrays;
- coordinate names alone do not establish coordinate semantics;
- time-like names alone do not establish a canonical time axis;
- numeric time remains numeric physical dtype even when convention-backed decoding supports a temporal interpretation;
- multiple plausible time-axis candidates must abstain from canonical selection;
- contradictory axis, dimension, coordinate, calendar, or unit evidence must become `conflicted`;
- missing convention metadata must remain `unknown`.

### Out Of Scope For The First Iteration

- Zarr v3 implementation;
- remote object-store traversal, credentials, and network retry policy;
- writing, mutating, repairing, or consolidating Zarr stores;
- decoding every chunk payload;
- arbitrary codec execution;
- deriving physical fields from chunk filenames or directory-name heuristics;
- Dask execution or Xarray dataset materialization;
- sidecar, README, notebook, or agent-driven promotion of canonical claims;
- any change to frozen benchmark artifacts, paper tables, figures, manuscript, or headline metrics.

## Required Substrate Change: Resource Intake

The current `ExtractionRequest.path` and `extract_path()` intake assume a regular file. Zarr commonly uses a directory store, so Phase 14 should extend intake conservatively.

Proposed compatible additions:

```python
ExtractionRequest(
    path,
    format_hint=None,
    sample_limit=200,
    resource_kind="auto",  # auto | file | directory_store
)
```

The existing file path behavior must remain unchanged.

Directory-store intake rules:

1. Accept a directory only when a registered capability explicitly declares directory-store support.
2. Detect Zarr v2 from spec-backed metadata documents, not only the `.zarr` suffix.
3. Treat a `.zarr` suffix without valid metadata as unsupported or malformed, not as successful extraction.
4. Reject path traversal and keep all discovered metadata paths inside the selected store root.
5. Return structured failure or abstention when metadata is unreadable, contradictory, or unsupported.

The capability contract should add resource-kind and metadata-document declarations only if they are useful beyond Zarr. Existing capabilities must remain backward compatible.

## Proposed Registry Capability

Illustrative capability:

```text
extractor_id: zarr_v2_metadata_extractor
formats: [zarr]
resource_kinds: [directory_store]
operations:
  - enumerate_groups
  - enumerate_arrays
  - read_array_metadata
  - read_attributes
  - interpret_xarray_dimensions
  - interpret_cf_coordinates
  - decode_supported_cf_time
evidence_types:
  - zarr_group_metadata
  - zarr_array_metadata
  - zarr_attribute
  - zarr_consolidated_metadata
```

The capability must declare deterministic failure modes and must not advertise chunk-payload decoding unless that operation is actually implemented and evaluated.

## Proposed Output And Evidence

Each group and array should preserve its store-relative path and evidence source.

Example physical array claim:

```json
{
  "field_path": "observations/temperature",
  "physical_type": "<f4",
  "shape": [24, 180, 360],
  "metadata": {
    "chunks": [1, 180, 360],
    "order": "C",
    "compressor": {"id": "zlib", "level": 1},
    "fill_value": null
  },
  "source_evidence": [
    {
      "evidence_type": "zarr_array_metadata",
      "source": "observations/temperature/.zarray",
      "detail": "dtype, shape, chunks, compressor, fill_value, and order"
    }
  ]
}
```

Evidence sources in generated artifacts must remain store-relative and portable. Local absolute paths must not appear.

## Structured Failure And Abstention

Phase 14 should reuse existing reason codes where they fit and add narrowly scoped Zarr codes only when needed.

Required cases include:

- `.zarr` suffix but no valid Zarr metadata;
- malformed `.zgroup`, `.zarray`, `.zattrs`, or `.zmetadata`;
- unsupported Zarr version;
- array metadata missing required keys;
- conflicting consolidated and per-node metadata;
- unsupported or unknown codec metadata;
- invalid shape/chunk/dtype declarations;
- coordinate reference to a missing array;
- conflicting `_ARRAY_DIMENSIONS` and array rank;
- multiple plausible temporal candidates;
- partial extraction where one array is malformed but other arrays remain auditable.

Unknown codecs should be recorded as metadata and surfaced as unsupported for payload decoding; they must not erase otherwise valid physical schema.

## Challenge Pack

Create:

```text
testdata/zarr_phase14/
data/experiments/phase14_zarr/
docs/phase14_zarr_report.md
```

The challenge pack should include at least:

1. minimal root group;
2. one valid numeric array;
3. nested groups and arrays;
4. chunks, compressor, filters, order, and fill value;
5. explicit `.zattrs`;
6. consolidated `.zmetadata`;
7. Xarray `_ARRAY_DIMENSIONS`;
8. convention-backed coordinate arrays;
9. supported CF numeric time;
10. multiple plausible time arrays requiring abstention;
11. coordinate-axis conflict requiring `conflicted`;
12. missing coordinate target;
13. malformed `.zarray`;
14. conflicting consolidated versus node metadata;
15. unknown codec metadata;
16. Zarr v3 metadata requiring structured unsupported-format behavior;
17. `.zarr` suffix without Zarr metadata;
18. partial store with one valid and one invalid array.

Do not require large chunk payloads for the physical-schema challenge pack.

## Evaluator Metrics

Report separately:

- store/version detection accuracy;
- extractor routing accuracy;
- group discovery accuracy;
- array discovery accuracy;
- dtype, shape, chunks, order, compressor, filters, and fill-value accuracy;
- attribute extraction accuracy;
- consolidated-metadata handling accuracy;
- Xarray dimension-label accuracy;
- coordinate-role accuracy;
- time-axis selection accuracy;
- calendar-handling accuracy;
- unit-mapping accuracy;
- structured failure artifact completeness;
- partial-extraction accuracy;
- abstention precision and recall;
- reason-code coverage;
- evidence coverage for accepted physical, logical, and semantic claims;
- unsupported promotion count;
- generated-artifact path portability.

Metrics must remain separate. A single aggregate score must not hide unsupported promotion, conflict handling, or evidence gaps.

## Implementation Sequence

1. Extend intake and capability contracts for directory-store resources while preserving all existing file behavior.
2. Implement deterministic Zarr v2 detection from metadata documents.
3. Implement group and array metadata extraction with store-relative evidence.
4. Add consolidated-metadata support with explicit conflict checks.
5. Interpret `_ARRAY_DIMENSIONS` and convention-backed coordinate relationships.
6. Reuse shared temporal and unit validation for explicitly supported claims.
7. Route generic CLI and GUI scratch extraction through the same registry path.
8. Build the isolated challenge pack and evaluator.
9. Generate Phase 14 artifacts and a bounded report.
10. Run full regression, path-hygiene, and frozen-artifact audits.

## Acceptance Gates

- Existing CSV, HDF5, temporal, NetCDF/CF, CLI, and GUI behavior remains compatible.
- Full regression suite passes.
- Every Zarr extraction outcome includes a format/store decision and extractor identity or explicit abstention/failure reason.
- Valid groups, arrays, dimensions, and promoted claims include evidence.
- Evidence coverage for accepted claims is `1.0000` on the controlled challenge pack.
- Unsupported promotion count is `0`.
- Multiple temporal candidates abstain from canonical selection.
- Conflicting coordinate, dimension, calendar, or unit evidence becomes `conflicted`.
- Names, directory paths, and chunk keys do not create unsupported physical or semantic fields.
- Unknown codecs do not trigger arbitrary code execution.
- Generated artifacts contain no local absolute paths.
- Phase 14 builders write only to the new experiment directory.
- Frozen benchmark artifacts, paper result tables, figures, manuscript, and headline metrics remain unchanged.

## Known Planning Risks

- Directory-store support changes a core file-oriented intake assumption and needs careful compatibility tests.
- Consolidated and per-node metadata may disagree; precedence must be explicit and conflicts auditable.
- Xarray compatibility is convention-based and must not be confused with full Xarray behavior.
- Codec metadata can be extracted safely without executing codecs, but payload sampling may require optional dependencies later.
- A controlled challenge pack cannot establish cloud-store reliability or broad Zarr ecosystem robustness.

## Recommended First Deliverable

Implement a local-directory, metadata-only Zarr v2 extractor that can enumerate groups and arrays, extract complete `.zarray` physical metadata, read `.zattrs`, preserve explicit `_ARRAY_DIMENSIONS`, and produce evidence-grounded structured outcomes without reading chunk payloads.

This is the smallest Phase 14 slice that materially extends the substrate while preserving deterministic-first guarantees.
