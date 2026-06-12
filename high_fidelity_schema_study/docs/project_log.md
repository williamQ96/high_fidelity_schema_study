# Project Architecture Log

This log records high-level architectural decisions and post-freeze milestones. Detailed acquisition and implementation history remains in `log.md`.

## 2026-06-10: Deep Research Recommendation

Source:

- `docs/literature/deep_research_prompt_data_agent_comparison_2026-06-10.md`
- `docs/literature/deep_research_report_data_agent_comparison_2026-06-10.md`

Decision:

- Do not turn the project into an autonomous, LLM-first data agent.
- Treat the project as an agent-ready, deterministic-first schema substrate.
- Keep deterministic parsers, validators, evidence, provenance, conflict handling, and abstention ahead of any bounded semantic agent.
- Expand standards-backed format support before increasing agent autonomy.

Rationale:

Leading data-agent systems primarily operate over data that is already modeled, cataloged, governed, or queryable. This project addresses the upstream problem of establishing trustworthy schema from heterogeneous raw scientific files. Agent infrastructure may later consume the schema substrate, but it is not a substitute for spec-backed extraction.

## 2026-06-10: Phase 12 Deterministic Substrate

Report:

- `docs/phase12_deterministic_substrate_report.md`
- `data/experiments/phase12_deterministic_substrate/report.json`

Delivered:

- central extractor capability registry;
- conservative format detection and routing;
- typed extraction requests, decisions, capabilities, outcomes, and issues;
- structured success, partial, abstained, and failed paths;
- explicit failure and abstention reason codes;
- independent temporal-semantics subsystem;
- property-level temporal claims, validators, evidence references, and ambiguity abstention;
- generic CLI extraction and registry-backed GUI scratch extraction;
- isolated 13-case challenge pack and evaluator.

Controlled result:

- all declared Phase 12 challenge metrics: `1.0000`;
- unsupported promotion count: `0`.

Boundary:

These results do not replace the frozen Artifact Paper metrics. In particular, the frozen `time_axis_accuracy = 0.6667` remains unchanged.

## 2026-06-10: Phase 13 NetCDF/CF Extension

Report:

- `docs/phase13_netcdf_cf_report.md`
- `data/experiments/phase13_netcdf_cf/report.json`

Delivered:

- first new registry-native scientific format capability;
- NetCDF classic extraction through `scipy`;
- conservative HDF5-backed NetCDF4-marker extraction through `h5py`;
- dimensions, groups, variables, dtype, shape, attributes, fill/missing markers, and file metadata;
- evidence-backed CF coordinate, bounds, time-unit, calendar, and unit interpretation;
- reuse of shared temporal and unit subsystems;
- coordinate conflicts represented as `conflicted`;
- multiple plausible canonical time axes represented by abstention;
- original numeric time dtype preserved as physical truth;
- isolated 14-case challenge pack, evaluator, CLI/GUI coverage, and generated artifacts.

Controlled result:

- all declared Phase 13 metrics: `1.0000`;
- evidence coverage: `1.0000`;
- unsupported promotion count: `0`;
- regression suite at completion: `91 passed`.

Boundary:

Phase 13 does not claim complete arbitrary NetCDF4 reconstruction, non-standard-calendar decoding, or broad real-world NetCDF/CF robustness.

## 2026-06-11: Phase 14 Recommendation

Recommendation:

Proceed with `Phase 14: Zarr / Xarray-Compatible Scientific Array Extraction`.

Why:

- Zarr is a natural adjacent scientific-array format after NetCDF/CF.
- It tests whether the registry contract can support directory/store resources, chunk metadata, compressor metadata, and cloud-oriented array layouts.
- Xarray-compatible metadata can reuse the existing coordinate, temporal, unit, evidence, and abstention contracts when explicit conventions support the claims.
- A metadata-first Zarr v2 implementation can improve deterministic coverage without requiring agent inference or chunk-payload interpretation.

Required guardrails:

- plan and support Zarr v2 first;
- do not claim Zarr support until a registered extractor and challenge evaluator exist;
- do not create fields from directory names, chunk keys, or semantic guesses;
- use `_ARRAY_DIMENSIONS`, CF attributes, and other explicit conventions only when present and internally consistent;
- return `unknown`, `conflicted`, partial outcomes, or abstention for unsupported stores and ambiguous metadata;
- keep Phase 14 artifacts separate from frozen benchmark and paper artifacts.

Implementation plan:

- `docs/phase14_zarr_plan.md`

## 2026-06-11: Phase 14A Zarr Directory-Store Intake

Report:

- `docs/phase14a_zarr_report.md`
- `data/experiments/phase14a_zarr/report.json`

Delivered:

- resource-kind-aware intake for existing files and local directory stores;
- registry-backed, dependency-light Zarr v2 metadata extraction;
- group and array hierarchy plus complete `.zarray` physical metadata and explicit attributes;
- metadata-relative evidence and structured partial, failed, and abstained outcomes;
- bounded `_ARRAY_DIMENSIONS` and CF-like convention handling without semantic field creation;
- generic CLI and GUI scratch directory-store support;
- isolated 14-case challenge pack, evaluator, and generated artifacts.

Controlled result:

- all declared Phase 14A metrics: `1.0000`;
- evidence coverage and path portability: `1.0000`;
- unsupported promotion count: `0`;
- regression suite at completion: `109 passed`.

Boundary:

Phase 14A does not read chunk payloads or claim remote-store, Zarr v3, full Xarray reconstruction, or broad real-world Zarr robustness. Frozen Artifact Paper artifacts and headline metrics remain unchanged.

## 2026-06-11: Phase 14B Zarr Compatibility Validation

Report:

- `docs/phase14b_zarr_compatibility_report.md`
- `data/experiments/phase14b_zarr_compatibility/report.json`

Delivered:

- separate 17-case producer-shaped local Zarr v2 compatibility corpus;
- classified evaluator separating supported layouts, unsupported features, malformed failures, structured abstentions, and true bugs;
- structured NumPy dtype compatibility;
- array-boundary-aware metadata discovery that prunes slash-separated chunk directories;
- group-scoped coordinate reference resolution that prevents cross-group same-name promotion;
- explicit unresolved-coordinate and dimension-size compatibility gaps;
- isolated generated outcomes and summary reports.

Compatibility result:

- 10 of 10 supported layouts met expectations;
- 4 of 4 unsupported-feature cases were visible as expected;
- 2 of 2 malformed cases produced the expected structured outcomes;
- 1 of 1 structured-abstention cases abstained with the expected reason;
- evidence coverage, path portability, and chunk-payload non-claim rate: `1.0000`;
- unsupported promotion count: `0`;
- true bug count after fixes: `0`;
- regression suite at completion: `117 passed`.

Boundary:

The Phase 14B corpus reconstructs common producer layouts but is not a downloaded representative ecosystem sample. It does not justify claims for remote stores, Zarr v3 extraction, chunk decoding, or full Xarray reconstruction. Frozen Artifact Paper artifacts and headline metrics remain unchanged.

## 2026-06-11: Phase 14C External And Library Zarr Conformance

Report:

- `docs/phase14c_zarr_external_conformance_report.md`
- `data/experiments/phase14c_zarr_external_conformance/report.json`

Delivered:

- metadata-only 12-case corpus with exact official source-distribution metadata, pinned-library-produced stores, and labeled edge cases;
- source, version, license, URL, generation, usage, SHA-256, and limitation manifest;
- optional dev-only Zarr/Xarray cross-parser metadata collector;
- evaluator separating canonical compatibility, structured abstention, unsupported and malformed behavior, explained conformance differences, unexplained differences, and true bugs;
- portable generated outcomes and summary reports.

Compatibility result:

- all canonical expectations met;
- evidence coverage, path portability, source documentation, and chunk-payload non-claim rate: `1.0000`;
- unsupported promotion count: `0`;
- true bug count: `0`;
- 5 parser interpretation/default differences classified and explained;
- unexplained conformance difference count: `0`;
- regression suite at completion: `125 passed`.

Boundary:

Cross-parser output is supporting evidence only and does not override canonical raw metadata preservation. The corpus is targeted rather than representative. Remote stores, Zarr v3, chunk decoding, value-level profiling, and full Xarray reconstruction remain deferred. Frozen Artifact Paper artifacts and headline metrics remain unchanged.

## 2026-06-12: Phase 15A Parquet / Arrow Metadata-First Extraction

Report:

- `docs/phase15a_parquet_arrow_report.md`
- `data/experiments/phase15a_parquet_arrow/report.json`

Delivered:

- registry-backed Parquet magic/suffix routing and PyArrow metadata backend;
- recursive Arrow schema extraction with nested logical paths, nullability, metadata, and timestamp timezone declarations;
- separate Parquet physical column paths, types, definition/repetition levels, row groups, encodings, compression, and footer statistics;
- explicit Arrow-leaf to Parquet-column path mapping;
- CLI and GUI scratch compatibility;
- isolated 8-case challenge pack, evaluator, artifacts, and tests.

Controlled result:

- all declared Phase 15A metrics: `1.0000`;
- evidence coverage and row-value abstention accuracy: `1.0000`;
- unsupported promotion count: `0`;
- regression suite at completion: `136 passed`.

Boundary:

The extractor reads footer and embedded schema metadata only and reports `row_values_read=0`. Footer statistics are not independently validated against row values. The PyArrow-produced challenge pack is bounded evidence rather than broad multi-producer compatibility. Frozen Artifact Paper artifacts and headline metrics remain unchanged.

The post-freeze Phase 12 malformed Parquet routing case now expects the registered Parquet extractor and a structured `parser_error`, preserving Phase 12 current-state routing accuracy without changing frozen Artifact Paper results.

## 2026-06-12: Phase 16A Conservative JSON Structure Extraction

Report:

- `docs/phase16a_json_structure_report.md`
- `data/experiments/phase16a_json_structure/report.json`

Delivered:

- registry-backed JSON document and JSON Lines extraction;
- bounded observed paths, type sets, nullability, missingness, nested structures, and heterogeneous arrays;
- structured sample-truncation issues;
- JSON Schema declared fields and explicit declared-versus-observed example conflicts;
- CLI and GUI scratch compatibility;
- isolated 6-case challenge pack, evaluator, artifacts, and tests.

Controlled result:

- all declared Phase 16A metrics: `1.0000`;
- evidence coverage: `1.0000`;
- unsupported promotion count: `0`;
- regression suite at completion: `148 passed`.

Boundary:

Observed structure remains bounded by the configured sample and is not universal schema truth. JSON Schema declarations and observed examples remain separate claim classes. XML/XSD remains deferred. Frozen Artifact Paper artifacts and headline metrics remain unchanged.

## 2026-06-12: Phase 16B Lightweight XML / XSD Structure Extraction

Delivered namespace-aware bounded XML observation, repeated paths, lightweight XSD declarations, explicit `xsi:type` conflicts, CLI/GUI integration, a 5-case evaluator, artifacts, tests, and `docs/phase16b_xml_xsd_report.md`.

All declared Phase 16B metrics and evidence coverage are `1.0000`; unsupported promotion count is `0`. External schemas/entities are not loaded, and this is not a full validating XML processor.

## 2026-06-12: Phase 17 Unified Schema Envelope

Delivered a versioned additive cross-format envelope, `extract_unified()`, CLI output-shape selection, GUI envelope payloads, an 8-format evaluator, artifacts, tests, and `docs/phase17_unified_schema_envelope_report.md`.

All declared Phase 17 metrics are `1.0000`. Legacy outcomes remain immutable and authoritative; the envelope does not promote new semantic truth. Frozen Artifact Paper artifacts and headline metrics remain unchanged.

## 2026-06-12: Phases 18-20 Convergence

Phase 18 delivered a common categorized evaluation entrypoint with no cross-track aggregate score. Phase 19 delivered read-only agent bundles and capability exports with canonical-mutation guards. Phase 20 delivered a reviewer demo script and generated release-readiness audit.

Release evidence:

- 11 categorized evaluation tracks;
- 8 agent bundles and 7 registered capabilities;
- release-readiness audit: `ready=true`;
- full regression suite: `179 passed`;

## 2026-06-12: Final Release Workbench Pass

- Added small allowlisted runnable examples for CSV temporal semantics, opaque-binary abstention, NetCDF/CF, HDF5, Zarr v2, Parquet/Arrow, JSON, and XML conflict review.
- Recorded repository-relative example sources and SHA-256 digests; no external or sensitive data was added.
- Made Extract the default GUI workbench and surfaced format decisions, structured issues, claim states, conflicts, provenance, and evaluator/release status before raw JSON.
- Added a durable GUI design source under `gui_demo/DESIGN.md`.
- Preserved frozen Artifact Paper artifacts and deterministic-first boundaries.
- generated experiment artifacts contain no local absolute paths;
- frozen Artifact Paper paths remain unchanged.

The framework is publishable/demo-ready within its stated bounded claims. Recommended next work is broader external compatibility validation, not additional canonical autonomy.
