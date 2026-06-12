# Phase 18 Unified Evaluation

Common entrypoint with explicit track-category separation and no cross-track aggregate score.

| Track | Category | Status |
| --- | --- | --- |
| frozen_internal_baseline | frozen_artifact_paper | reference_only_not_rerun |
| frozen_retrieval_slice | frozen_artifact_paper | reference_only_not_rerun |
| phase12_deterministic_substrate | bounded_challenge | evaluated |
| phase13_netcdf_cf | bounded_challenge | evaluated |
| phase14a_zarr | bounded_challenge | evaluated |
| phase14b_zarr_compatibility | compatibility | evaluated |
| phase14c_zarr_external_conformance | external_conformance | evaluated |
| phase15a_parquet_arrow | bounded_challenge | evaluated |
| phase16a_json_structure | bounded_challenge | evaluated |
| phase16b_xml_xsd_structure | bounded_challenge | evaluated |
| phase17_unified_schema_envelope | cross_format_contract | evaluated |

## Category Summary

- `bounded_challenge`: 6
- `compatibility`: 1
- `cross_format_contract`: 1
- `external_conformance`: 1
- `frozen_artifact_paper`: 2

## Boundaries

- No cross-track aggregate score is computed because track scopes and claim boundaries differ.
- Frozen Artifact Paper metrics are referenced only and are not rerun or rewritten.
- Bounded challenge, compatibility, external-conformance, and cross-format-contract tracks remain separate.
