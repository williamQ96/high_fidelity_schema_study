# Phase 17: Unified Schema Envelope

Date: 2026-06-12

## Purpose

Phase 17 adds a versioned, additive cross-format schema envelope while preserving every legacy `ExtractionOutcome` and `DatasetSchema` consumer.

## Envelope

`schema_envelope_version = 1.0.0` includes:

- file identity, format decision, extractor capability, and outcome;
- physical structure and format-specific analysis;
- logical roles, semantic hints, units, and temporal semantics;
- relationships, normalized claims, evidence, and provenance;
- conflicts, abstentions, unsupported features, and evaluation metadata.

Normalized claim states are:

`observed`, `declared`, `derived`, `supported`, `conflicted`, `unknown`, `unsupported`, and `abstained`.

## Compatibility

- `extract_path()` and legacy CLI output remain unchanged by default.
- `extract_unified()` returns the unified envelope.
- CLI `extract --output-shape legacy|envelope|both` selects the desired payload.
- GUI scratch responses preserve `schema` and `extraction_outcome` and add `unified_schema_envelope`.

## Controlled Result

The 8-case cross-format evaluator covers CSV, HDF5, NetCDF/CF, Zarr, Parquet, JSON, XML, and raw-binary abstention. All declared metrics are `1.0000`, including section completeness, physical fidelity, valid claim states, evidence integrity, conflict/abstention projection, provenance, and legacy outcome immutability.

## Boundaries

- The envelope is a deterministic projection of existing claims.
- It does not promote new semantic truth.
- Legacy schemas remain authoritative during the compatibility period.
- Format-specific detail remains available under `physical_structure.format_specific`.
- Frozen Artifact Paper artifacts and headline metrics remain unchanged.
