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
- Current full regression suite: `183 passed`.
- Convergence baseline: `main` was synced to `origin/main` at `46faf9c Add CSV semantic guardrails and docs` before this final documentation and audit pass.
- Companion engineering appendix: `docs/phase20_companion_engineering_appendix.md`.
- Recent semantic guardrail closure: CSV GPU training-log temperatures now remain `gpu_temperature`, while channel suffixes such as `input_dim_c` no longer become Celsius unit claims.

## Release Audit

The generated `data/experiments/phase20_release_readiness/report.json` reports `ready=true`:

- required paths complete;
- major documentation local links resolve;
- generated experiment artifacts contain no local absolute paths;
- documentation contains no local absolute paths;
- frozen Artifact Paper paths are unchanged.

## Bounded Claims

This convergence round does not change the frozen manuscript, tables, figures, benchmark, or headline metrics. Bounded challenge packs remain bounded. External compatibility evidence remains separately labeled. The framework is agent-ready, not agent-controlled: exports are read-only and agents cannot silently promote canonical claims.

The companion appendix summarizes Phases 12-20 as post-freeze engineering evidence. It is intentionally separate from the frozen Artifact Paper result tables and should be read as artifact readiness, not as a new benchmark freeze.

## Deferred Work

- Broader external/multi-producer Parquet, JSON, XML, and NetCDF compatibility corpora.
- Zarr v3, remote stores, chunk decoding, and full Xarray reconstruction.
- FITS/GRIB and instrument reverse engineering.
- Any LLM-first or autonomous canonical extraction path.
