# Phase 12 Deterministic Substrate Upgrade

Date: 2026-06-10

Status: implemented as a new experimental track. The frozen Artifact Paper benchmark and headline metrics remain unchanged.

## Goal

Phase 12 strengthens the system that sits before any bounded semantic agent:

```text
heterogeneous file
  -> trustworthy format decision
  -> registered deterministic extractor
  -> auditable temporal validation
  -> structured success, partial, abstention, or failure outcome
```

The project remains deterministic-first. Agent autonomy, new format implementations, sidecar/code enrichment, MCP exposure, and a breaking schema-v2 migration are deferred.

## Implemented

- Added typed extraction contracts for requests, format signals, format decisions, extractor capabilities, issues, and outcomes.
- Added a central capability registry and `extract_path()` orchestration entrypoint.
- Added conservative routing from magic, explicit hints, suffixes, and bounded text probes.
- Added structured abstention for unknown, unsupported, container-only, and conflicting-format cases.
- Preserved legacy CSV/HDF5 extractor functions, CLI commands, and GUI response fields.
- Added the generic CLI command `python -m high_fidelity_schema_study.cli extract`.
- Routed GUI scratch extraction through the central registry and exposed `extraction_outcome`.
- Replaced the former time-series-only heuristic core with an auditable temporal subsystem.
- Added timezone-preserving parsing, deterministic candidate ranking, multi-candidate abstention, per-property claims, validators, reason codes, and evidence references.
- Kept naive timestamps at timezone `unknown`; explicit `Z`/zero offset becomes `UTC`; conflicting offsets remain `conflicted`.
- Added a separate 13-case Phase 12 challenge experiment and evaluator.

## Phase 12 Results

Source: `data/experiments/phase12_deterministic_substrate/report.json`.

| Metric | Value |
| --- | ---: |
| Challenge cases | 13 |
| Temporal cases | 9 |
| Format detection accuracy | 1.0000 |
| Extractor routing accuracy | 1.0000 |
| Structured failure artifact completeness | 1.0000 |
| Time-axis selection accuracy | 1.0000 |
| Per-property temporal accuracy | 1.0000 |
| Exact temporal profile accuracy | 1.0000 |
| Abstention precision | 1.0000 |
| Abstention recall | 1.0000 |
| Reason-code coverage | 1.0000 |
| Evidence coverage | 1.0000 |
| Unsupported promotion count | 0 |

These are controlled Phase 12 challenge results, not replacements for the frozen paper metrics.

## Important Finding

The frozen `time_axis_accuracy = 0.6667` was not caused by failure to identify the three internal time axes. The existing extractor already recovered their fields, frequencies, regularity, and missing-interval behavior. The strict whole-object comparison failed because the derived profiles omitted `timezone`.

Phase 12 therefore separates temporal properties and makes their evidence state explicit:

- explicit `Z`/zero offset supports `UTC`;
- consistent non-zero offsets support a normalized offset;
- naive timestamps remain timezone `unknown`;
- sidecar-only local-time descriptions do not become deterministic truth;
- ambiguous time-axis candidates cause selection abstention.

The current frozen evaluation remains unchanged. Any future headline-metric revision requires a separately versioned benchmark and evaluation-policy decision.

## Run

```bash
python -m high_fidelity_schema_study.build_phase12_experiment
python -m pytest high_fidelity_schema_study\tests
```

Generic extraction:

```bash
python -m high_fidelity_schema_study.cli extract --input path/to/file --format auto
```

## Deferred

- Parquet/Arrow and NetCDF/CF extractor implementation.
- Sidecar, producer-code, notebook, or data-dictionary enrichment.
- Context graph, review memory, MCP, or bounded semantic-agent orchestration.
- Sandboxed parsing workers and production dependency isolation.
- Breaking `confidence` to `support_score` schema migration.
