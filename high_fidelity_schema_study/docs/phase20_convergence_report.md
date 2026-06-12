# Phase 20: Repository, Paper, And Demo Convergence

Date: 2026-06-12

## Release-Style State

- Seven registered deterministic formats: CSV, HDF5, NetCDF/CF, Zarr v2 local stores, Parquet/Arrow, JSON/JSON Lines, and XML/XSD.
- Versioned unified schema envelope with legacy compatibility.
- Unified evaluation entrypoint with evidence-category separation and no misleading aggregate score.
- Read-only agent-ready exports with canonical-mutation guards.
- Reviewer demo script and GUI scratch workbench.
- Portable allowlisted demo examples with repository-relative sources and SHA-256 digests.
- Extraction-first GUI result review for format signals, issues/conflicts, claim states, provenance, fields, and structured JSON.
- Release-readiness audit covering required files, major documentation links, generated/documentation path hygiene, and frozen artifact diffs.
- Full regression suite: `179 passed`.

## Release Audit

The generated `data/experiments/phase20_release_readiness/report.json` reports `ready=true`:

- required paths complete;
- major documentation local links resolve;
- generated experiment artifacts contain no local absolute paths;
- documentation contains no local absolute paths;
- frozen Artifact Paper paths are unchanged.

## Bounded Claims

This convergence round does not change the frozen manuscript, tables, figures, benchmark, or headline metrics. Bounded challenge packs remain bounded. External compatibility evidence remains separately labeled. The framework is agent-ready, not agent-controlled: exports are read-only and agents cannot silently promote canonical claims.

## Deferred Work

- Broader external/multi-producer Parquet, JSON, XML, and NetCDF compatibility corpora.
- Zarr v3, remote stores, chunk decoding, and full Xarray reconstruction.
- FITS/GRIB and instrument reverse engineering.
- Any LLM-first or autonomous canonical extraction path.
