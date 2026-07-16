# Phase 20 Companion Engineering Appendix

Date: 2026-06-28

This appendix summarizes the post-freeze engineering evidence for Phases 12-20. It is a companion to the Artifact Paper package, not a replacement for the frozen paper benchmark. The frozen corpus, gold references, result tables, figures, qrels, manuscript metrics, and headline claims remain unchanged.

## Purpose

The frozen Artifact Paper demonstrates a deterministic-first schema extraction method on a small controlled benchmark slice. Phases 12-20 harden the same project into an agent-ready deterministic schema substrate:

- conservative format detection and extractor routing;
- structured success, partial, abstained, and failed outcomes;
- evidence-preserving temporal, unit, and schema-envelope projections;
- registry-native support for additional scientific and structured formats;
- categorized evaluation that avoids misleading aggregate scores;
- read-only agent context exports;
- reproducible dependencies, CI, demo examples, GUI scratch extraction, and release-readiness checks.

These additions strengthen the artifact package and future extensibility. They do not silently promote bounded challenge-pack results into broad robustness claims.

## Engineering Evidence By Subsystem

### Orchestration And Failure Contracts

Phase 12 introduced `ExtractionRequest`, `FormatSignal`, `ExtractorCapability`, `ExtractionIssue`, and `ExtractionOutcome`, plus the central `extract_path()` orchestration API. Format routing prioritizes trusted signatures, compatible explicit hints, conservative suffix/text probes, and structured abstention when no spec-backed extractor exists.

All extraction outcomes include a format decision and either an extractor identity or a clear abstention/failure reason. Opaque binary and recognized-but-unparsed resources do not produce invented field claims.

### Temporal Semantics

The temporal subsystem separates candidate discovery, canonical-axis selection, property claims, validators, and issues. It preserves timezone evidence, supports UTC and explicit offsets, marks naive datetimes as `unknown`, records mixed-aware conflicts, and abstains when multiple plausible time axes have near-equal support.

The frozen paper's `time_axis_accuracy = 0.6667` remains unchanged. Post-freeze temporal improvements are companion engineering evidence only.

### Registry-Native Format Extensions

Phases 13-16 extended the registry while preserving deterministic-first boundaries:

- NetCDF/CF extraction for dimensions, variables, attributes, CF coordinates, units, calendars, and conservative NetCDF4/HDF5-marker routing.
- Zarr v2 local directory-store metadata extraction, compatibility validation, and targeted external/library conformance without chunk-payload reads or remote-store claims.
- Parquet/Arrow footer and embedded schema extraction without reading row values.
- JSON/JSON Lines bounded observed-structure extraction plus declared JSON Schema conflict handling.
- XML/XSD lightweight namespace-aware structure extraction without external entity/schema loading.

Each track keeps its generated artifacts under versioned experiment directories and reports bounded metrics separately from frozen paper results.

### Unified Envelope, Evaluation, And Agent Context

Phase 17 added a versioned additive schema envelope that projects legacy outcomes into identity, format detection, physical structure, logical roles, semantic hints, units, temporal semantics, claims, evidence, provenance, conflicts, abstentions, unsupported features, and evaluation metadata.

Phase 18 added a unified evaluation entrypoint that reports distinct tracks and deliberately keeps `aggregate_score = null`.

Phase 19 added read-only agent-ready exports. Agents may inspect evidence and request bounded reruns, but they cannot mutate canonical claims, invent extractors, or promote suggestions into truth.

### Release Readiness And Semantic Guardrails

Phase 20 added pinned dependencies, CI coverage, a reviewer demo script, portable demo examples, an extraction-first GUI workbench, and release-readiness audit checks for required paths, links, generated-artifact path hygiene, documentation path hygiene, and frozen artifact diffs.

The 2026-06-28 final convergence pass also added CSV semantic guardrails for ML/GPU training logs. Explicit GPU temperature fields now remain `gpu_temperature`, and channel-count suffixes such as `input_dim_c` no longer become Celsius unit claims. This is a targeted overclaiming fix, not a broad semantic benchmark.

## Current Verification State

- Full regression suite: `183 passed`.
- Release readiness: `ready=true`.
- Convergence baseline: `main` was synced to `origin/main` at `46faf9c Add CSV semantic guardrails and docs` before this final documentation and audit pass.
- Frozen artifact paths: unchanged.
- Generated experiment artifacts: no local absolute paths.
- Documentation: no local absolute paths under the release audit policy.
- Office lock files: ignored and intentionally untracked.

## How To Cite This Appendix

Use this appendix for engineering readiness claims such as:

- "The artifact includes a registry-backed deterministic extraction substrate with structured abstention/failure contracts."
- "Post-freeze experiments validate additional format contracts on bounded challenge and compatibility packs."
- "The release package includes CI, pinned dependencies, demo examples, GUI scratch extraction, and a release-readiness audit."

Do not use this appendix to claim:

- broad real-world scientific-data robustness;
- replacement of the frozen Artifact Paper result tables;
- solved semantic typing;
- autonomous data-agent extraction;
- complete support for arbitrary NetCDF4, Zarr v3, remote stores, chunk decoding, Parquet producer diversity, full JSON schema inference, or validating XML Schema processing.
