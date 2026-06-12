# Experimental Artifacts

This directory contains versioned experiments that are intentionally separate from the frozen Artifact Paper benchmark.

Current experiments:

- `phase12_deterministic_substrate/`
  - capability-registry and structured-abstention checks;
  - temporal challenge evaluation;
  - generated outcomes and summary reports.
- `phase13_netcdf_cf/`
  - NetCDF classic and HDF5-backed container extraction checks;
  - CF coordinate, time, calendar, bounds, unit, evidence, and abstention evaluation;
  - generated outcomes and summary reports.
- `phase14a_zarr/`
  - local directory-store Zarr v2 metadata extraction checks;
  - hierarchy, physical metadata, explicit convention, evidence, portability, partial, and abstention evaluation;
  - generated outcomes and summary reports.
- `phase14b_zarr_compatibility/`
  - producer-shaped local Zarr v2 compatibility validation;
  - separate supported, unsupported-feature, malformed-failure, structured-abstention, and true-bug reporting;
  - generated outcomes and summary reports.
- `phase14c_zarr_external_conformance/`
  - externally sourced and pinned-library-produced local Zarr v2 metadata validation;
  - optional dev-only Zarr/Xarray cross-parser supporting evidence;
  - explained versus unexplained conformance-difference reporting.
- `phase15a_parquet_arrow/`
  - Parquet footer and embedded Arrow schema metadata extraction;
  - nested path, nullability, row-group, compression, encoding, metadata, statistics-policy, evidence, and row-value-abstention evaluation;
  - generated outcomes and summary reports.
- `phase16a_json_structure/`
  - bounded JSON and JSON Lines observed-structure extraction;
  - JSON Schema declared fields and explicit declared-observed conflict evaluation;
  - generated outcomes and summary reports.
- `phase16b_xml_xsd_structure/`
  - bounded namespace-aware XML element/attribute structure extraction;
  - lightweight XSD declaration and `xsi:type` conflict evaluation;
  - generated outcomes and summary reports.
- `phase17_unified_schema_envelope/`
  - additive versioned cross-format schema envelopes;
  - claim-state, evidence-integrity, conflict/abstention, provenance, and legacy-compatibility evaluation;
  - generated envelopes and summary reports.
- `phase18_unified_evaluation/`
  - categorized frozen-reference, bounded, compatibility, external-conformance, and cross-format track summary;
  - deliberately no cross-track aggregate score.
- `phase19_agent_ready_exports/`
  - read-only schema, claim/evidence, provenance, capability, and retrieval-context bundles;
  - canonical-mutation and silent-promotion guards.
- `phase20_release_readiness/`
  - required-file, README-link, generated-path-hygiene, and frozen-path audit.

Experiment builders must not write into `data/derived`, frozen benchmark files, paper tables, figures, or the manuscript.
