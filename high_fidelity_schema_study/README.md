# High-Fidelity Schema Extraction Study

This repository implements a deterministic-first, registry-backed, evidence-grounded substrate for extracting auditable schemas from heterogeneous scientific data files.

Its canonical job is narrow: establish the strongest schema that can be supported by file structure, explicit metadata, deterministic validators, and recorded evidence. It is **not** an autonomous data agent, an LLM-first metadata generator, or a system that fills unsupported gaps by guessing.

Core guarantees:

- deterministic extractors establish physical structure;
- semantic interpretation cannot create physical fields;
- accepted claims remain traceable to field- or structure-level evidence;
- ambiguity and conflict remain visible as `unknown`, `conflicted`, partial outcomes, or abstentions;
- LLM-assisted annotation, where used in older experimental tracks, is downstream and constrained by deterministic fields;
- controlled challenge-pack results remain separate from the frozen Artifact Paper benchmark.

## Working Title

`A Deterministic-First Framework for High-Fidelity Schema Extraction from Scientific Data Files`

## Core Questions

1. How much physical schema can we recover deterministically across CSV, HDF5, NetCDF/CF, and time-series organization?
2. When deterministic extraction is separated from semantic augmentation, does field-level fidelity improve?
3. Does evidence-grounded schema extraction improve retrieval over metadata-only baselines?
4. Does the system expose uncertainty honestly instead of collapsing ambiguity into opaque scores?

## Terminology

### Pilot

In this study, a `pilot` dataset or `pilot corpus` means a deliberately small, controlled first-round dataset collection used to validate method design before scaling up.

For this directory, the pilot corpus is not the final benchmark. It is a compact set of:

- easy cases with clean metadata
- medium cases with partial or mixed metadata
- hard cases with ambiguity, missing metadata, or structural traps

The point of a pilot is to answer:

- can the extractor run end to end?
- do the schema outputs have the right shape?
- are the evaluation dimensions sensible?
- where do the failure modes show up before we scale?

### Gold

`Gold` means the human-authored reference truth used to evaluate extracted schemas.

In this study, a gold schema is the field-level answer key for a dataset. It records what we currently believe is the correct interpretation of:

- physical type
- logical type
- semantic type
- units
- necessity / importance

Gold is not "whatever the model predicted best." Gold is the evaluation target that the extractor is compared against.

## System Identity

The system is best understood as an **agent-ready deterministic schema substrate**. A future bounded agent may call its tools or inspect its outcomes, but the agent must not replace the parser, invent physical fields, or silently promote weak evidence into canonical truth.

The project separates:

- physical schema: fields, variables, dimensions, groups, dtypes, shapes, missing markers;
- logical schema: identifiers, coordinates, canonical time axes, measurements, relationships;
- semantic schema: units, descriptions, standard names, and domain meaning;
- claim state: supported, derived, unknown, conflicted, partial, abstained, or failed;
- evidence and provenance: why a claim exists and which deterministic operation produced it.

## Architecture

```text
input resource
  -> deterministic intake and bounded probes
  -> format signals and conflict-aware format decision
  -> extractor capability registry
  -> registered format-specific deterministic extractor
  -> shared temporal-semantics and unit-normalization validators
  -> structured extraction outcome: success | partial | abstained | failed
  -> field/structure evidence and provenance
  -> explicit unknown/conflict/abstention paths
  -> CLI, GUI scratch workbench, and independent evaluators
```

The central orchestration API is `extract_path(ExtractionRequest(...))`. It returns a structured outcome containing the format decision, selected extractor capability or abstention reason, schema when available, and structured issues.

The additive unified API is `extract_unified(ExtractionRequest(...))`. It returns a versioned cross-format envelope while legacy outcomes remain unchanged. The generic CLI supports `--output-shape legacy|envelope|both`.

## Supported Formats

| Input form | Current deterministic behavior | Registry status | Important boundary |
| --- | --- | --- | --- |
| CSV / delimited text | Header-grounded fields, sampled physical profiling, missingness, and shared temporal analysis | Registered extractor | Sample-derived properties are bounded by `sample_limit`; names alone do not establish semantic truth |
| HDF5 | Group/dataset traversal, paths, dtypes, shapes, and explicit attributes | Registered extractor | Generic HDF5 is not promoted to NetCDF merely because its filename ends in `.nc` |
| Time-series organization | Shared temporal candidate analysis, timezone preservation, frequency, regularity, missing intervals, and ambiguity abstention | Shared subsystem used by CSV and decoded NetCDF/CF time coordinates | This is an organization/validation layer, not a standalone file format; the global frozen time-axis metric is not claimed solved |
| NetCDF/CF | NetCDF classic plus conservative HDF5-backed NetCDF4-marker path; dimensions, groups, variables, attributes, CF coordinates, bounds, calendars, time units, fill/missing markers, and units | Registered extractor | No claim of complete arbitrary NetCDF4 reconstruction; non-standard calendars are preserved but not decoded |
| Zarr v2 local directory store | Metadata-only group/array discovery; `.zarray` physical metadata; explicit attributes; bounded Xarray/CF convention handling | Registered extractor | Local directories only; chunk payloads, remote stores, Zarr v3, and full Xarray reconstruction are out of scope |
| Parquet / Arrow | Parquet footer and embedded Arrow schema extraction; nested paths, types, nullability, row groups, encodings, compression, metadata, and footer statistics | Registered extractor | Requires `pyarrow`; row values are not read; footer statistics are not independently validated |
| JSON / JSON Lines | Bounded observed paths, type sets, null/missing, arrays, nested structures, plus JSON Schema declarations and example conflicts | Registered extractor | Observed structure is sample-bounded; declarations and observations remain separate |
| XML / XSD | Namespace-aware bounded element/attribute paths, repeated paths, lightweight XSD declarations, and `xsi:type` conflicts | Registered extractor | Not a full validating XML/XSD processor; external schemas and entities are not loaded |
| Raw / opaque binary | File-level evidence and structured abstention without field claims | Deliberate abstention path | No spec-backed extractor means no invented fields |

Recognized-but-unregistered formats return structured abstention rather than parser-free schema claims. Phase 14A extends intake to local Zarr directory stores while preserving existing regular-file behavior.

## Scope And Non-Goals

Current scope is high-fidelity extraction and validation of supported inputs, plus isolated post-freeze format experiments.

Non-goals:

- autonomous agent orchestration over the canonical extraction path;
- end-to-end LLM schema guessing;
- semantic inference that creates physical fields;
- unsupported claims for raw binary or recognized-but-unparsed formats;
- claiming broad robustness from bounded challenge packs;
- silently revising the frozen benchmark, manuscript, tables, figures, or headline metrics.

## Folder Layout

```text
high_fidelity_schema_study/
  README.md
  study_manifest.json
  cli.py
  models.py
  create_pilot_corpus.py
  build_derived_schemas.py
  build_external_derived_schemas.py
  build_retrieval_artifacts.py
  build_paper_tables.py
  build_provenance_manifest.py
  expand_retrieval_pool.py
  build_semantic_grounding.py
  audit_gold_schemas.py
  evaluate_internal_baseline.py
  evaluate_semantic_merge.py
  evaluate_retrieval_artifacts.py
  import_external_corpus.py
  merge_semantic_annotations.py
  repair_semantic_annotation_manifest.py
  deterministic_profile.py
  semantic_layer.py
  semantic_annotate.py
  log.md
  extractors/
  docs/
    project_log.md
    phase14_zarr_plan.md
    literature/
  templates/
  data/
  tests/
```

## Initial Deliverables In This Scaffold

- target schema definition
- evaluation plan
- pilot corpus plan
- JSON templates for field-level gold annotations and schema claims
- minimal extractor skeletons for CSV, HDF5, and time-series profiling
- lightweight CLI for initial experiments
- reproducible batch builder for derived schema artifacts
- reproducible external corpus import workflow
- structured project log

## Current State

This directory is no longer only a scaffold. It already contains:

- a 3 x 3 internal pilot corpus under [data/raw](data/raw)
- field-level gold schemas under [data/gold](data/gold)
- a second-pass internal gold consistency review under [docs/gold-schema-second-pass-2026-05-11.md](docs/gold-schema-second-pass-2026-05-11.md)
- deterministic derived schemas under [data/derived](data/derived)
- richer deterministic profiling outputs inside derived schemas, plus [data/derived/internal_relationship_profile.json](data/derived/internal_relationship_profile.json)
- unit normalization status inside derived schema fields
- a lightweight PROV-like provenance export under [data/derived/provenance_manifest.json](data/derived/provenance_manifest.json)
- an internal baseline evaluation report under [data/derived/internal_baseline_report.md](data/derived/internal_baseline_report.md)
- an external staged corpus under [data/external](data/external)
- deterministic schemas for supported downloaded external files under [data/external/derived](data/external/derived)
- retrieval artifacts for the promoted external candidate pool under [data/retrieval/external_candidate_pool](data/retrieval/external_candidate_pool)
- a first retrieval comparison report under [data/retrieval/external_candidate_pool/retrieval_report.md](data/retrieval/external_candidate_pool/retrieval_report.md)
- a frozen benchmark-slice contract under [docs/benchmark_freeze_2026-05-04.md](docs/benchmark_freeze_2026-05-04.md)
- a benchmark card under [docs/benchmark_card_2026-05-15.md](docs/benchmark_card_2026-05-15.md)
- a schema claim model under [docs/schema_claim_model.md](docs/schema_claim_model.md)
- paper-ready result tables with evidence adequacy metrics under [docs/paper_result_tables_2026-05-15.md](docs/paper_result_tables_2026-05-15.md)
- a final-polished paper-ready draft under [docs/paper_draft.md](docs/paper_draft.md)
- generated paper figures under [docs/figures](docs/figures)
- a draft citation matrix under [docs/literature/citation_matrix.md](docs/literature/citation_matrix.md)
- a draft reference list under [docs/references.md](docs/references.md)
- an academic rigor audit under [docs/academic_rigor_audit.md](docs/academic_rigor_audit.md)
- a time-axis gap adjudication under [docs/time_axis_gap_adjudication.md](docs/time_axis_gap_adjudication.md)
- an artifact handoff guide under [docs/artifact_handoff.md](docs/artifact_handoff.md)
- GUI visual QA notes under [docs/gui_visual_qa.md](docs/gui_visual_qa.md)
- a final convergence report under [docs/final_convergence_report.md](docs/final_convergence_report.md)
- a visual GUI demo under [gui_demo](gui_demo), including frozen artifact inspection and scratch local schema extraction
- a polished default extraction workbench plus small runnable inputs under [demo_examples](demo_examples), with repository-relative provenance and SHA-256 digests
- retrieval qrels under [data/retrieval/external_candidate_pool/qrels.json](data/retrieval/external_candidate_pool/qrels.json)
- local related-work seed papers and a deep research prompt under [docs/literature](docs/literature)
- an isolated deterministic-substrate experiment and report under [data/experiments/phase12_deterministic_substrate](data/experiments/phase12_deterministic_substrate) and [docs/phase12_deterministic_substrate_report.md](docs/phase12_deterministic_substrate_report.md)
- a registry-backed NetCDF/CF extractor, 14-case challenge pack, and isolated Phase 13 report under [data/experiments/phase13_netcdf_cf](data/experiments/phase13_netcdf_cf) and [docs/phase13_netcdf_cf_report.md](docs/phase13_netcdf_cf_report.md)
- a metadata-first Zarr v2 local-directory extractor, 14-case challenge pack, and isolated Phase 14A report under [data/experiments/phase14a_zarr](data/experiments/phase14a_zarr) and [docs/phase14a_zarr_report.md](docs/phase14a_zarr_report.md)
- a 17-case producer-shaped local Zarr v2 compatibility corpus, classified compatibility evaluator, and Phase 14B report under [data/experiments/phase14b_zarr_compatibility](data/experiments/phase14b_zarr_compatibility) and [docs/phase14b_zarr_compatibility_report.md](docs/phase14b_zarr_compatibility_report.md)
- a 12-case external/library-produced metadata-only Zarr v2 corpus, optional cross-parser evaluator, and Phase 14C report under [data/experiments/phase14c_zarr_external_conformance](data/experiments/phase14c_zarr_external_conformance) and [docs/phase14c_zarr_external_conformance_report.md](docs/phase14c_zarr_external_conformance_report.md)
- a registry-backed Parquet/Arrow metadata extractor, 8-case challenge pack, and isolated Phase 15A report under [data/experiments/phase15a_parquet_arrow](data/experiments/phase15a_parquet_arrow) and [docs/phase15a_parquet_arrow_report.md](docs/phase15a_parquet_arrow_report.md)
- a registry-backed conservative JSON structure extractor, 6-case challenge pack, and isolated Phase 16A report under [data/experiments/phase16a_json_structure](data/experiments/phase16a_json_structure) and [docs/phase16a_json_structure_report.md](docs/phase16a_json_structure_report.md)
- a registry-backed lightweight XML/XSD extractor, 5-case challenge pack, and isolated Phase 16B report under [data/experiments/phase16b_xml_xsd_structure](data/experiments/phase16b_xml_xsd_structure) and [docs/phase16b_xml_xsd_report.md](docs/phase16b_xml_xsd_report.md)
- a versioned unified schema envelope and 8-format compatibility evaluator under [data/experiments/phase17_unified_schema_envelope](data/experiments/phase17_unified_schema_envelope) and [docs/phase17_unified_schema_envelope_report.md](docs/phase17_unified_schema_envelope_report.md)
- a unified evaluation harness under [data/experiments/phase18_unified_evaluation](data/experiments/phase18_unified_evaluation) and [docs/phase18_unified_evaluation_report.md](docs/phase18_unified_evaluation_report.md)
- read-only agent-ready bundles under [data/experiments/phase19_agent_ready_exports](data/experiments/phase19_agent_ready_exports) and [docs/phase19_agent_ready_exports_report.md](docs/phase19_agent_ready_exports_report.md)
- a reviewer [demo script](docs/demo_script.md) and generated [release-readiness audit](data/experiments/phase20_release_readiness)
- semantic-grounding task bundles under [data/semantic_grounding](data/semantic_grounding)
- semantic annotation outputs under [data/semantic_annotations](data/semantic_annotations)
- semantic merge-back outputs under [data/semantic_merged](data/semantic_merged)
- a running project log in [log.md](log.md)
- a high-level architecture log and Phase 14 plan under [docs/project_log.md](docs/project_log.md) and [docs/phase14_zarr_plan.md](docs/phase14_zarr_plan.md)

## Post-Freeze Development

The frozen Artifact Paper slice remains the reporting baseline. Phase 12 through Phase 20 are separately versioned, post-freeze engineering experiments and do not rewrite its corpus, gold references, paper tables, figures, manuscript, or headline metrics.

### Phase 12: Deterministic Substrate

Phase 12 introduced the central capability registry, conservative format routing, typed extraction requests and outcomes, structured failure/abstention reason codes, and an independent temporal-semantics subsystem. Its 13-case controlled challenge pack reports `1.0000` across its declared format, routing, temporal, abstention, reason-code, and evidence metrics, with unsupported promotion count `0`.

See [docs/phase12_deterministic_substrate_report.md](docs/phase12_deterministic_substrate_report.md) and [data/experiments/phase12_deterministic_substrate](data/experiments/phase12_deterministic_substrate).

### Phase 13: NetCDF/CF Registry Extension

Phase 13 used the Phase 12 contracts for the first registry-native scientific format extension. It added conservative NetCDF/CF extraction, shared temporal/unit validation, physical-structure evidence, coordinate-conflict handling, and ambiguous-time abstention. Its 14-case controlled challenge pack reports `1.0000` across all declared metrics, evidence coverage `1.0000`, and unsupported promotion count `0`.

See [docs/phase13_netcdf_cf_report.md](docs/phase13_netcdf_cf_report.md) and [data/experiments/phase13_netcdf_cf](data/experiments/phase13_netcdf_cf).

### Phase 14A: Zarr Directory-Store Intake

Phase 14A extends the registry to local directory-store resources and adds a dependency-light Zarr v2 metadata extractor. It enumerates groups and arrays, preserves `.zarray` physical metadata and explicit attributes, applies bounded `_ARRAY_DIMENSIONS` and CF-like conventions, never reads chunk payloads, and keeps value-level statistics explicitly unknown. Its 14-case controlled challenge pack reports `1.0000` across all declared metrics, path portability `1.0000`, and unsupported promotion count `0`.

See [docs/phase14a_zarr_report.md](docs/phase14a_zarr_report.md) and [data/experiments/phase14a_zarr](data/experiments/phase14a_zarr).

### Phase 14B: Zarr Compatibility Validation

Phase 14B validates the metadata extractor against a separate 17-case producer-shaped local compatibility corpus. It adds structured-dtype compatibility, array-boundary-aware metadata discovery, group-scoped coordinate resolution, and explicit compatibility-gap reporting. All 10 supported layouts met expectations; 4 unsupported-feature cases, 2 malformed cases, and 1 structured abstention were surfaced as expected. Evidence coverage, path portability, and chunk-payload non-claim rate are `1.0000`; unsupported promotion and true bug counts are `0`.

See [docs/phase14b_zarr_compatibility_report.md](docs/phase14b_zarr_compatibility_report.md) and [data/experiments/phase14b_zarr_compatibility](data/experiments/phase14b_zarr_compatibility).

### Phase 14C: External And Library Zarr Conformance

Phase 14C validates the canonical extractor against a metadata-only 12-case corpus containing an exact subset of the official `zarr-python 2.18.7` source fixture, stores produced by pinned Zarr/Xarray libraries, and labeled edge cases. All canonical expectations passed with evidence coverage, path portability, and chunk-payload non-claim rate at `1.0000`; unsupported promotion and true bug counts are `0`. Optional dev-only cross-parser checks found 5 explained parser interpretation/default differences and `0` unexplained differences.

See [docs/phase14c_zarr_external_conformance_report.md](docs/phase14c_zarr_external_conformance_report.md) and [data/experiments/phase14c_zarr_external_conformance](data/experiments/phase14c_zarr_external_conformance).

### Phase 15A: Parquet / Arrow Metadata-First Extraction

Phase 15A adds registry-backed Parquet footer and Arrow schema extraction without reading row values. It preserves nested Arrow logical paths separately from Parquet physical column paths and exposes types, nullability, row groups, compression, encodings, metadata, and footer statistics. Its 8-case controlled pack reports `1.0000` across all declared metrics with unsupported promotion count `0`.

See [docs/phase15a_parquet_arrow_report.md](docs/phase15a_parquet_arrow_report.md) and [data/experiments/phase15a_parquet_arrow](data/experiments/phase15a_parquet_arrow).

### Phase 16A: Conservative JSON Structure Extraction

Phase 16A adds bounded observed-structure extraction for JSON documents and JSON Lines, plus declared-only JSON Schema handling and explicit conflicts against schema examples. Its 6-case controlled pack reports `1.0000` across all declared metrics with unsupported promotion count `0`.

See [docs/phase16a_json_structure_report.md](docs/phase16a_json_structure_report.md) and [data/experiments/phase16a_json_structure](data/experiments/phase16a_json_structure).

### Phase 16B: Lightweight XML / XSD Structure Extraction

Phase 16B adds namespace-aware bounded XML element/attribute observation, repeated paths, lightweight XSD declarations, and explicit `xsi:type` conflicts. Its 5-case controlled pack reports `1.0000` across all declared metrics with unsupported promotion count `0`.

See [docs/phase16b_xml_xsd_report.md](docs/phase16b_xml_xsd_report.md) and [data/experiments/phase16b_xml_xsd_structure](data/experiments/phase16b_xml_xsd_structure).

### Phase 17: Unified Schema Envelope

Phase 17 adds a versioned additive envelope covering identity, detection, capability, physical structure, logical/semantic/unit/temporal claims, relationships, normalized claim states, evidence, provenance, conflicts, abstentions, unsupported features, and evaluation metadata. Its 8-format evaluator reports `1.0000` across all declared metrics while proving legacy outcome immutability.

See [docs/phase17_unified_schema_envelope_report.md](docs/phase17_unified_schema_envelope_report.md) and [data/experiments/phase17_unified_schema_envelope](data/experiments/phase17_unified_schema_envelope).

### Phases 18-20: Evaluation, Agent Exports, And Convergence

Phase 18 provides one evaluation entrypoint while preserving frozen, bounded, compatibility, external-conformance, and cross-format categories. It deliberately computes no aggregate score. Phase 19 exports read-only agent bundles with claims, evidence, provenance, capabilities, retrieval context, and canonical-mutation guards. Phase 20 adds the reviewer demo script, runnable controlled examples, a polished extraction-first GUI workbench, and a generated release-readiness audit.

See [docs/phase18_unified_evaluation_report.md](docs/phase18_unified_evaluation_report.md), [docs/phase19_agent_ready_exports_report.md](docs/phase19_agent_ready_exports_report.md), [docs/phase20_convergence_report.md](docs/phase20_convergence_report.md), and [docs/demo_script.md](docs/demo_script.md).

These controlled results prove the declared challenge cases, not broad real-world robustness.

## Current Results Snapshot

| Track | Current evidence | Honest interpretation |
| --- | --- | --- |
| Frozen internal pilot | 9 datasets; physical completeness `1.0000`, physical accuracy `0.9815`, logical accuracy `0.9444`, semantic accuracy `1.0000` | High field-level accuracy on the frozen small pilot, not solved scientific schema extraction |
| Frozen time-axis metric | `time_axis_accuracy = 0.6667` | Remains a visible frozen-slice limitation; Phase 12 did not rewrite this headline metric |
| Frozen retrieval slice | Schema-enhanced Recall@1 `1.0000`, metadata-only `0.7000`, README-only `0.5000` | Controlled planted-query result over a 10-query, 16-file slice, not broad search superiority |
| Phase 12 challenge | 13 cases; declared metrics `1.0000`; unsupported promotion `0` | Controlled deterministic-substrate validation |
| Phase 13 NetCDF/CF challenge | 14 cases; declared metrics and evidence coverage `1.0000`; unsupported promotion `0` | Controlled NetCDF/CF contract validation, not complete NetCDF4 or corpus-wide performance |
| Phase 14A Zarr challenge | 14 cases; declared metrics, evidence coverage, and path portability `1.0000`; unsupported promotion `0` | Controlled local Zarr v2 metadata validation, not cloud-store or full Xarray support |
| Phase 14B Zarr compatibility | 17 producer-shaped cases; 10 supported layouts compatible; expected unsupported/malformed/abstention behavior `1.0000`; true bugs `0`; unsupported promotion `0` | Realistic local compatibility validation, not a downloaded representative ecosystem sample |
| Phase 14C external/library conformance | 12 metadata-only cases; canonical expectations `1.0000`; explained cross-parser differences `5`; unexplained differences `0`; true bugs `0` | Targeted external and pinned-library evidence, not representative ecosystem coverage |
| Phase 15A Parquet/Arrow challenge | 8 cases; declared metrics and evidence coverage `1.0000`; row-value abstention `1.0000`; unsupported promotion `0` | Controlled PyArrow-produced metadata validation, not broad multi-producer compatibility |
| Phase 16A JSON challenge | 6 cases; declared metrics and evidence coverage `1.0000`; unsupported promotion `0` | Controlled bounded-structure validation, not universal JSON schema inference |
| Phase 16B XML/XSD challenge | 5 cases; declared metrics and evidence coverage `1.0000`; unsupported promotion `0` | Controlled lightweight structure validation, not full XML Schema validation |
| Phase 17 unified envelope | 8 formats; section, claim-state, evidence, conflict/abstention, provenance, and compatibility metrics `1.0000` | Additive projection over existing claims, not a new inference layer |
| Phase 18 unified evaluation | 11 categorized tracks; frozen references are not rerun; aggregate score is `null` | Common reporting entrypoint without collapsing evidence boundaries |
| Phase 19 agent exports | 8 bundles; policy, fidelity, evidence, provenance, context, and bounded-action metrics `1.0000`; 7 capabilities | Agent-ready read-only context, not agent-controlled canonical extraction |
| Phase 20 release readiness | Required paths, major documentation links, generated/documentation path hygiene, and frozen paths pass | Release-style repository readiness, not broader empirical validation |
| Current regression suite | `179 passed` after final workbench and demo-example validation | Current repository regression status; it should be re-run after every later change |

## Current Target

Phases 15-20 are implemented and the repository is in a demo-ready convergence state. The next recommended work is broader external/multi-producer compatibility validation for Parquet, JSON, XML, and NetCDF/CF. Zarr v3, remote stores, chunk decoding, and LLM-first agents remain deferred until evidence identifies a concrete need.

The paper and frozen Artifact Paper artifacts remain unchanged unless a separately approved freeze or reporting round explicitly replaces them.

## Bounded Limitations

- The frozen internal pilot is intentionally small and cannot establish broad scientific-data generalization.
- Phase 12, Phase 13, and Phase 14A metrics are exact results on bounded synthetic/controlled challenge packs. Phase 14B uses a broader producer-shaped but still locally reconstructed compatibility corpus. Phase 14C adds targeted external and pinned-library-produced evidence, but is still not a representative ecosystem sample.
- The frozen paper still reports `time_axis_accuracy = 0.6667`; post-freeze temporal improvements do not silently revise it.
- NetCDF classic support uses `scipy`; HDF5-backed NetCDF extraction uses conservative `h5py` structure and explicit NetCDF4 markers, not a complete arbitrary NetCDF4 implementation.
- Zarr support is limited to local directory-store v2 metadata. It does not read chunk payloads, access remote/object stores, implement Zarr v3, or reconstruct full Xarray semantics.
- Parquet support currently depends on PyArrow and reads footer/schema metadata only. It does not validate footer statistics against row values or establish broad producer compatibility.
- JSON support reports bounded observed structure or explicit JSON Schema declarations. Sampled paths, missingness, and type sets are not complete universal truth.
- XML/XSD support is lightweight and sample-bounded; it is not a full validating XML processor and does not load external schemas or entities.
- Unified envelopes and agent exports are deterministic projections over canonical extraction outcomes, not new inference layers.
- Known non-standard calendars are preserved but are not decoded by the standard-calendar path.
- CSV profiling is sampled; sample-derived frequency, regularity, missingness, and type properties remain bounded by the sample.
- Raw/opaque binary and recognized formats without a registered spec-backed extractor abstain from field claims.
- Evidence adequacy establishes auditability, not correctness.
- Semantic annotation and future bounded-agent work must remain downstream of canonical physical extraction.

## Data Layout

```text
data/
  raw/
    csv/
    hdf5/
    time_series/
  gold/
    csv/
    hdf5/
    time_series/
  derived/
    csv/
    hdf5/
    time_series/
    derived_manifest.json
    internal_baseline_report.json
    internal_baseline_report.md
  external/
    curated_sources.json
    import_manifest.json
    derived/
    dryad/
    zenodo/
  retrieval/
    external_candidate_pool/
  semantic_grounding/
  semantic_annotations/
  semantic_merged/
  pilot_corpus_manifest.json
```

## Current Corpus Status

Internal study assets:

- 9 internal pilot datasets are present across CSV, HDF5, and time-series organization.
- 9 matching gold schema files are present for field-level reference evaluation.
- 9 deterministic derived schema files are present for baseline extraction output.
- an initial internal field-level baseline report is present in JSON and Markdown form.

External acquisition status:

- [data/external/import_manifest.json](data/external/import_manifest.json) records 16 downloaded Dryad/Zenodo files; the raw payload directories are not present in this current worktree.
- deterministic derived schemas are present for all 16 recorded imports under [data/external/derived](data/external/derived).
- one external HDF5 file is only partially recoverable and carries recorded `extraction_errors`, but no longer blocks batch extraction.
- a first-pass benchmark-candidate triage is recorded in [data/external/benchmark_candidates.json](data/external/benchmark_candidates.json).
- current external benchmark-candidate status is 10 promoted, 2 distractor, 2 keep_not_benchmark, and 2 excluded_by_user.
- The exact selected sources and import results are pinned in [data/external/curated_sources.json](data/external/curated_sources.json) and [data/external/import_manifest.json](data/external/import_manifest.json).
- External derived output status is pinned in [data/external/derived/derived_manifest.json](data/external/derived/derived_manifest.json).

Retrieval preparation status:

- retrieval artifacts have been rebuilt over an expanded 16-file pool consisting of 10 targets and 6 harder distractors
- the current benchmark slice is frozen in [docs/benchmark_freeze_2026-05-04.json](docs/benchmark_freeze_2026-05-04.json), covering 9 internal pilot datasets and the 16-file external retrieval pool
- planted retrieval queries now cover the full 10 promoted benchmark targets inside that expanded pool
- schema-enhanced retrieval now has explicit schema-source comparison artifacts: deterministic-only and semantic-merged where available
- schema-enhanced artifacts include year, file-slice, school-slice, and month-slice terms for same-family disambiguation
- artifact locations are pinned in [data/retrieval/external_candidate_pool/artifact_manifest.json](data/retrieval/external_candidate_pool/artifact_manifest.json)
- a first lexical retrieval comparison has been run; current artifact-level ranking performance is summarized in [data/retrieval/external_candidate_pool/retrieval_report.md](data/retrieval/external_candidate_pool/retrieval_report.md)
- current retrieval metrics on the expanded 16-file pool still show `schema_enhanced` outperforming both `readme_only` and `metadata_only`:
  `schema_enhanced recall_at_1 = 1.0000`, `schema_enhanced_semantic_merged recall_at_1 = 1.0000`, `readme_only recall_at_1 = 0.5000`, `metadata_only recall_at_1 = 0.7000`

Semantic grounding status:

- an evidence-constrained semantic annotation interface is defined in [semantic_layer.py](semantic_layer.py) and [docs/semantic_annotation_interface.md](docs/semantic_annotation_interface.md)
- README-driven and metadata-driven grounding bundles have been built for 9 internal tasks and 16 external tasks
- semantic grounding task locations are pinned in [data/semantic_grounding/manifest.json](data/semantic_grounding/manifest.json)
- an LLM-assisted semantic annotation runner and merge-back path now exist through [semantic_annotate.py](semantic_annotate.py) and [merge_semantic_annotations.py](merge_semantic_annotations.py)
- smoke-run outputs currently include three internal and six external semantic annotation results plus merged artifacts, with explicit validation and conflict tracking
- validated semantic annotation results are tracked in [data/semantic_annotations/manifest.json](data/semantic_annotations/manifest.json), and a repair utility exists in [repair_semantic_annotation_manifest.py](repair_semantic_annotation_manifest.py)
- a first post-merge semantic evaluation report is available in [data/semantic_merged/semantic_merge_report.md](data/semantic_merged/semantic_merge_report.md)
- the current semantic smoke set includes accepted external Dryad merges as well as internal and Zenodo examples; internal post-merge evaluation now shows measurable semantic-layer gain in 2 of 3 evaluated internal tasks, including `csv_hard_field_campaign` logical accuracy improving from `0.6667` to `1.0000` and `csv_easy_weather_stations` logical accuracy improving from `0.8333` to `1.0000`
- the previously blocked high-value Dryad semantic targets, Greenland cod year1 and functional_traits, now have validated grouped semantic annotation outputs and merged artifacts

## Intended Output Contract

The study output separates:

- physical schema: columns, dtypes, paths, shapes, missingness
- logical schema: identifiers, time axis, measurements, relationships
- semantic schema: units, descriptions, domain meaning

Each field claim should be traceable to evidence. Example:

```json
{
  "field_name": "temperature",
  "physical_type": "float",
  "logical_type": "measurement",
  "semantic_type": "air_temperature",
  "unit": "Celsius",
  "source_evidence": [
    {
      "tier": "explicit_metadata",
      "evidence_type": "hdf5_attribute",
      "source": "/observations/temperature",
      "detail": "units='C'",
      "confidence": 0.99
    }
  ],
  "confidence": 0.99,
  "uncertainty_reason": null
}
```

## Roadmap And Checklist

This is the end-to-end execution checklist for the study. Checked items are already done in the current directory state.

### Phase 0: Framing And Study Design

- [x] Define the deterministic-first study framing.
- [x] Separate physical, logical, and semantic schema layers.
- [x] Define field-level evidence and provenance as a core output requirement.
- [x] Define the main evaluation dimensions: completeness, accuracy, necessary-field coverage, and uncertainty.
- [x] Write initial study documentation for target schema, pilot design, and evaluation plan.

### Phase 1: Repository And Artifact Scaffolding

- [x] Create a dedicated study directory at [high_fidelity_schema_study](.).
- [x] Add reusable schema models and extractor module structure.
- [x] Add a lightweight CLI entrypoint.
- [x] Add a project log file and logging convention.
- [x] Add reproducible scripts for pilot generation, derived-schema generation, and external corpus import.

### Phase 2: Internal Pilot Corpus

- [x] Define a 3 x 3 internal pilot design across CSV, HDF5, and time-series.
- [x] Generate 9 internal pilot datasets under [data/raw](data/raw).
- [x] Cover easy, medium, and hard cases for each modality.
- [x] Add sidecar README files for the pilot datasets.
- [x] Create a machine-readable pilot manifest.

### Phase 3: Gold Reference Construction

- [x] Define the gold field template.
- [x] Create field-level gold schemas for all 9 internal pilot datasets.
- [x] Record physical, logical, and semantic expectations in gold.
- [x] Record unit expectations and field necessity in gold.
- [x] Perform a second-pass human review of the gold schemas for consistency.

### Phase 4: Deterministic Extraction Baseline

- [x] Implement a conservative CSV extractor.
- [x] Implement a time-series profiling layer.
- [x] Implement an HDF5 hierarchy extractor.
- [x] Normalize HDF5 string-like datasets to `string` rather than raw `object`.
- [x] Batch-generate deterministic derived schemas for all 9 internal pilot datasets.
- [x] Save a derived manifest for the internal batch.
- [x] Add richer deterministic profiling for missingness, identifier quality, and multi-file relationships.

### Phase 5: External Corpus Preparation

- [x] Define a curated external source manifest spanning Dryad and Zenodo.
- [x] Implement a reproducible external import script.
- [x] Download a first external Zenodo batch into [data/external](data/external).
- [x] Stage Dryad record metadata and landing pages for selected targets.
- [x] Batch-build deterministic derived schemas for supported downloaded external files.
- [x] Complete actual Dryad payload downloads for the current curated source set.
- [x] Resolve the one current external HDF5 extraction failure or explicitly exclude that file from later benchmark use.
- [x] Decide which external staged files should be promoted into benchmark candidates.

### Phase 6: Validation And Regression Protection

- [x] Add unit tests for CSV extraction behavior.
- [x] Add unit tests for time-series regularity logic.
- [x] Add a smoke test for HDF5 extraction and string dtype normalization.
- [x] Run extractor smoke checks on imported external Zenodo files.
- [x] Add regression tests comparing derived outputs against expected field subsets for representative datasets.

### Phase 7: Evaluation Pipeline

- [x] Implement field-level comparison between derived schemas and gold schemas.
- [x] Report physical completeness and physical accuracy.
- [x] Report logical completeness and logical accuracy.
- [x] Report semantic completeness and semantic accuracy.
- [x] Report necessary-field coverage.
- [x] Report uncertainty behavior and confidence calibration.
- [x] Produce error analysis grouped by failure mode.

### Phase 8: Semantic Augmentation Layer

- [x] Define the evidence-constrained semantic annotation interface.
- [x] Add README-driven and metadata-driven semantic grounding inputs.
- [x] Implement LLM-assisted annotation that cannot invent unsupported schema claims.
- [x] Mark unsupported claims as `unknown` instead of guessing.
- [x] Preserve conflicts between explicit metadata and inferred semantics.

### Phase 9: Retrieval Experiment

- [x] Build a metadata-only retrieval baseline.
- [x] Build a README-only retrieval baseline.
- [x] Build a schema-enhanced retrieval index using deterministic outputs plus evidence-grounded semantic annotations.
- [x] Create query sets with intentionally planted relevant matches.
- [x] Evaluate retrieval with Recall@k, Precision@k, MRR, and nDCG.
- [x] Add case-study explanations for why relevant datasets were retrieved.

### Phase 10: Scale-Up And Corpus Hardening

- [ ] Expand beyond the internal pilot to a larger curated benchmark.
- [ ] Increase format diversity where justified, while keeping file-grounded extraction rules explicit.
- [ ] Decide whether raw binary without sidecar metadata stays out of scope or gets a low-confidence profiling lane.
- [x] Add benchmark inclusion criteria and exclusion criteria as explicit documentation.

### Phase 11: Paper And Final Deliverables

- [x] Freeze the current evaluation corpus and reviewed internal gold references for reporting.
- [x] Produce paper-ready result tables from frozen benchmark, deterministic baseline, retrieval, semantic merge, deterministic profile, and evidence adequacy artifacts.
- [x] Add related-work deep research report and project improvement assessment.
- [x] Formalize schema claim states, reason codes, and merge semantics.
- [x] Add benchmark-card documentation for the frozen reproducible slice.
- [x] Add evidence adequacy metrics to paper-ready result tables.
- [x] Add lightweight PROV-like provenance export.
- [x] Add standards-backed unit normalization status.
- [x] Add retrieval qrels and mark current queries as planted.
- [x] Draft an initial complete paper-ready manuscript from the frozen artifacts.
- [x] Build an initial static visual GUI demo for artifact inspection.
- [x] Add a scratch schema extraction tab for uploaded HDF5, CSV time-series, and raw binary abstention demos.
- [x] Produce initial paper-ready figures.
- [x] Add an academic rigor audit and explicit claim boundaries.
- [x] Adjudicate the time-axis gap as a documented current-slice limitation.
- [x] Add an artifact handoff guide for paper/demo review.
- [x] Run browser-level GUI visual smoke checks on desktop and mobile viewports.
- [x] Revise the paper draft into a final artifact-ready manuscript draft.
- [x] Write the methods section around deterministic-first extraction, provenance, and uncertainty.
- [x] Write the evaluation section with field-level interpretability rather than opaque scores.
- [x] Write the retrieval section comparing metadata-only and schema-enhanced behavior.
- [x] Write the related-work section from established data-readiness, provenance, schema extraction, and dataset-search literature.
- [x] Record limitations, especially around planted qrels, working annotations, raw binary underdetermination, and the time-axis gap.
- [x] Verify and refine the GUI demo against the frozen artifact files so it remains an inspection layer rather than an alternate evaluation path.
- [x] Add final convergence audit for paper, references, GUI, verification, and remaining limits.
- [ ] Convert the manuscript and references into a target venue template after a venue is selected.

### Phase 12: Deterministic Substrate Upgrade

- [x] Add typed extraction requests, format signals, capability declarations, structured issues, and extraction outcomes.
- [x] Add a central capability registry and conservative format-routing entrypoint.
- [x] Preserve legacy CSV/HDF5 extractor APIs while adding a generic `extract` CLI command.
- [x] Route GUI scratch extraction through the registry and expose structured outcome metadata.
- [x] Add an independent auditable temporal-semantics subsystem.
- [x] Preserve timezone offsets, keep naive timezones unknown, and surface conflicting offsets.
- [x] Abstain when multiple time-axis candidates have approximately equal deterministic support.
- [x] Add property-level temporal claims, validator results, reason codes, and evidence references.
- [x] Add an isolated temporal/format challenge pack and Phase 12 evaluator.
- [x] Keep Phase 12 artifacts separate from the frozen paper benchmark and headline metrics.
- [x] Use the Phase 12 registry contract as the base for the first standards-backed format extension.

### Phase 13: NetCDF/CF Registry Extension

- [x] Register NetCDF/CF as a deterministic extractor capability without changing legacy CSV/HDF5 APIs.
- [x] Auto-detect NetCDF classic signatures and HDF5-backed `.nc` containers.
- [x] Extract dimensions, variables, dtype, shape, attributes, groups, fill markers, missing markers, and file metadata.
- [x] Interpret evidence-backed CF coordinate roles, time units, calendars, bounds, and units.
- [x] Reuse the Phase 12 temporal semantics and existing unit-normalization contracts.
- [x] Preserve unknown/conflicted states and abstain on ambiguous or unsupported temporal promotion.
- [x] Add a 14-case challenge pack, independent evaluator, generated outcomes, CLI/GUI coverage, and reviewer-facing report.
- [x] Keep Phase 13 artifacts separate from frozen paper artifacts and headline metrics.

### Phase 14: Zarr / Xarray-Compatible Scientific Array Extraction

- [x] Define the bounded implementation plan and acceptance gates.
- [x] Extend intake contracts to support local directory-store resources without changing existing file behavior.
- [x] Add a dependency-light Zarr v2 metadata-first extractor and registry capability.
- [x] Reuse shared temporal, unit, evidence, structured-outcome, CLI, GUI, and evaluator contracts.
- [x] Add an isolated 14-case Zarr challenge pack and experiment artifacts.
- [x] Preserve unsupported-promotion count `0` and keep frozen artifacts unchanged.
- [x] Validate against a separate producer-shaped local Zarr v2 compatibility corpus.
- [x] Classify supported layouts, unsupported features, malformed failures, structured abstentions, and true bugs independently.
- [ ] Validate against externally sourced local Zarr v2 stores.
- [ ] Evaluate optional library-backed cross-parser conformance checks before any broader support claim.

## Immediate Next Steps

1. Curate an externally sourced local Zarr v2 validation corpus without mixing it into the controlled or producer-shaped packs.
2. Evaluate optional library-backed cross-parser conformance checks and record disagreements as structured evidence.
3. Keep external-corpus outputs isolated and leave the frozen Artifact Paper artifacts unchanged.
4. Then compare Parquet/Arrow against broader scientific-array convention coverage before selecting the next registry extension.

## Rebuild Study Artifacts

Create or refresh the pilot corpus:

```bash
python -m high_fidelity_schema_study.create_pilot_corpus
```

Create or refresh deterministic derived schemas for all pilot datasets:

```bash
python -m high_fidelity_schema_study.build_derived_schemas
```

This also refreshes field unit-normalization status, derived-schema deterministic profiles, and the internal multi-file relationship profile.

Create or refresh the external corpus staging batch:

```bash
python -m high_fidelity_schema_study.import_external_corpus
```

Create or refresh the internal baseline evaluation report:

```bash
python -m high_fidelity_schema_study.evaluate_internal_baseline
```

Create or refresh the internal gold consistency review:

```bash
python -m high_fidelity_schema_study.audit_gold_schemas
```

Create or refresh deterministic derived schemas for downloaded external files:

```bash
python -m high_fidelity_schema_study.build_external_derived_schemas
```

Create or refresh retrieval artifacts for the promoted external candidate pool:

```bash
python -m high_fidelity_schema_study.build_retrieval_artifacts
```

This also refreshes `qrels.json`, which currently marks the frozen retrieval queries as planted single-positive judgments.

Create or refresh the PROV-like provenance export:

```bash
python -m high_fidelity_schema_study.build_provenance_manifest
```

Download and derive the current hard-distractor retrieval pool expansion:

```bash
python -m high_fidelity_schema_study.expand_retrieval_pool
```

Create or refresh the first retrieval comparison report:

```bash
python -m high_fidelity_schema_study.evaluate_retrieval_artifacts
```

Create or refresh semantic grounding task bundles:

```bash
python -m high_fidelity_schema_study.build_semantic_grounding
```

Run LLM-assisted semantic annotation over selected grounding tasks:

```bash
python -m high_fidelity_schema_study.semantic_annotate --scope internal --task-id-pattern csv_hard_field_campaign --model llama-3.3-70b-instruct
```

Merge validated semantic annotation outputs back into schema artifacts:

```bash
python -m high_fidelity_schema_study.merge_semantic_annotations
```

Evaluate baseline vs semantic-merged internal outputs:

```bash
python -m high_fidelity_schema_study.evaluate_semantic_merge
```

Create or refresh paper-ready result tables from frozen artifacts:

```bash
python -m high_fidelity_schema_study.build_paper_tables
```

Create or refresh paper-ready SVG figures from generated result tables:

```bash
python -m high_fidelity_schema_study.build_paper_figures
```

Create or refresh the isolated Phase 12 deterministic-substrate experiment:

```bash
python -m high_fidelity_schema_study.build_phase12_experiment
```

Create or refresh the isolated Phase 13 NetCDF/CF experiment:

```bash
python -m high_fidelity_schema_study.create_phase13_challenge
python -m high_fidelity_schema_study.build_phase13_experiment
```

Run one file through the central capability registry:

```bash
python -m high_fidelity_schema_study.cli extract --input path/to/file --format auto
```

## Logging

Detailed acquisition and implementation history remains in [log.md](log.md). High-level architectural milestones and current recommendations are summarized in [docs/project_log.md](docs/project_log.md).

The current convention is to append dated entries in this shape:

- `Summary`
- `Action Points`
- `Important Process`
