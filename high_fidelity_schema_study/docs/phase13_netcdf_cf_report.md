# Phase 13 NetCDF/CF Registry Extension

Date: 2026-06-10

Status: implemented as an isolated standards-backed format experiment. The frozen Artifact Paper benchmark, manuscript, figures, and headline metrics remain unchanged.

## Goal

Phase 13 uses the Phase 12 registry and validation contracts for the first new format extension:

```text
NetCDF/CF file
  -> conservative format decision
  -> registered deterministic extractor
  -> physical structure and explicit attributes
  -> evidence-backed CF interpretation
  -> shared temporal and unit validation
  -> auditable schema outcome
```

The canonical path remains deterministic-first. It does not use sidecars, README text, agents, or model inference to promote NetCDF/CF claims.

## Implemented

- Added the registered `netcdf_cf_deterministic_extractor` capability.
- Added auto-detection for NetCDF classic signatures and HDF5-backed `.nc` containers with explicit NetCDF4 marker attributes.
- Added `.nc` and `.cdf` suffix routing and explicit `netcdf` format hints.
- Extracted dimensions, variables, dtype, shape, attributes, groups, fill markers, missing markers, and file-level metadata.
- Added evidence-backed CF interpretation for coordinate roles, `standard_name`, `axis`, `coordinates`, `bounds`, time units, calendars, and units.
- Reused the Phase 12 temporal-semantics subsystem for selected standard-calendar time coordinates.
- Reused the existing unit-normalization contract with explicit NetCDF-attribute evidence.
- Preserved unknown and conflicted claims when CF metadata is missing, malformed, ambiguous, or unsupported.
- Routed the generic CLI and GUI scratch extraction through the same registry contract.

## Backends And Boundaries

The available environment does not include `netCDF4`, `h5netcdf`, or `xarray`. The extractor therefore uses:

- `scipy.io.netcdf_file` for NetCDF classic files;
- `h5py` for HDF5-backed NetCDF4-compatible structure.

The HDF5-backed path intentionally extracts the structure and CF attributes that can be verified directly. It does not claim complete NetCDF4 semantic reconstruction from arbitrary HDF5 files.

Standard, Gregorian, and proleptic-Gregorian numeric time coordinates are decoded through deterministic rules. Known non-standard calendars such as `360_day` are preserved as explicit supported metadata but are not decoded by the standard-calendar temporal path. Malformed origins and unsupported calendars are surfaced as conflicted claims.

## Challenge Pack

The isolated challenge pack under `testdata/netcdf_cf_phase13/` contains 14 cases:

- standard dimension coordinates;
- auxiliary coordinates;
- `days since` time units;
- a `360_day` calendar;
- multiple plausible time variables;
- irregular sampling;
- a bounds variable;
- missing CF metadata;
- a coordinate-like name without supporting CF metadata;
- conflicting CF coordinate-axis evidence;
- malformed CF time metadata;
- an unmapped unit;
- fill and missing-value markers;
- an HDF5-backed grouped NetCDF4-compatible file.

## Phase 13 Results

Source: `data/experiments/phase13_netcdf_cf/report.json`.

| Metric | Value |
| --- | ---: |
| Challenge cases | 14 |
| Format detection accuracy | 1.0000 |
| Extractor routing accuracy | 1.0000 |
| Physical extraction accuracy | 1.0000 |
| Coordinate-role accuracy | 1.0000 |
| Time-axis accuracy | 1.0000 |
| Calendar-handling accuracy | 1.0000 |
| Unit-mapping accuracy | 1.0000 |
| Temporal abstention precision | 1.0000 |
| Temporal abstention recall | 1.0000 |
| Evidence coverage | 1.0000 |
| Unsupported promotion count | 0 |

These are controlled Phase 13 challenge results. They do not replace the frozen paper metrics and should not be interpreted as real-world NetCDF/CF corpus performance.

## Run

```bash
python -m high_fidelity_schema_study.create_phase13_challenge
python -m high_fidelity_schema_study.build_phase13_experiment
python -m high_fidelity_schema_study.cli extract --input path/to/file.nc --format auto
python -m pytest high_fidelity_schema_study\tests
```

## Next Improvements

- Curate a separately versioned real-world NetCDF/CF validation corpus.
- Add explicit coverage for chunking, compression, unlimited dimensions, compound types, and more nested-group relationships.
- Evaluate a standards-complete optional NetCDF backend without weakening dependency-failure reporting.
- Keep semantic enrichment outside the canonical deterministic claims until it has an independent evidence and abstention evaluation.
- Use the same registry contract for the planned Phase 14 Zarr / Xarray-compatible scientific-array extension.
