# High-Fidelity Schema Extraction Study

This directory is a root-level scaffold for a deterministic-first schema extraction study over heterogeneous scientific datasets.

The study premise is narrow and explicit:

- deterministic parsers extract only file-grounded structure
- LLMs may annotate meaning, but may not invent schema elements
- every schema claim must carry field-level evidence and uncertainty
- evaluation stays interpretable at schema and field level

## Working Title

`A Deterministic-First Framework for High-Fidelity Schema Extraction from Scientific Data Files`

## Core Questions

1. How much physical schema can we recover deterministically across CSV, HDF5, and time-series data?
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

## Method Summary

```text
Raw Dataset
   ->
File Type Detection
   ->
Deterministic Structural Extraction
   ->
Field-Level Evidence Capture
   ->
Semantic Annotation / Normalization
   ->
Uncertainty Estimation
   ->
Schema Output + Provenance
   ->
Evaluation: completeness, accuracy, necessary-field coverage, uncertainty
```

## Scope

Required modalities for the pilot:

- CSV
- HDF5 / self-describing binary
- time-series organization

Non-goals:

- end-to-end LLM schema guessing
- unsupported claims for raw binary files without sidecar metadata
- single opaque benchmark scores without field-level error analysis

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
- an internal baseline evaluation report under [data/derived/internal_baseline_report.md](data/derived/internal_baseline_report.md)
- an external staged corpus under [data/external](data/external)
- deterministic schemas for supported downloaded external files under [data/external/derived](data/external/derived)
- retrieval artifacts for the promoted external candidate pool under [data/retrieval/external_candidate_pool](data/retrieval/external_candidate_pool)
- a first retrieval comparison report under [data/retrieval/external_candidate_pool/retrieval_report.md](data/retrieval/external_candidate_pool/retrieval_report.md)
- a frozen benchmark-slice contract under [docs/benchmark_freeze_2026-05-04.md](docs/benchmark_freeze_2026-05-04.md)
- semantic-grounding task bundles under [data/semantic_grounding](data/semantic_grounding)
- semantic annotation outputs under [data/semantic_annotations](data/semantic_annotations)
- semantic merge-back outputs under [data/semantic_merged](data/semantic_merged)
- a running project log in [log.md](log.md)

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

- Zenodo payload downloads succeeded for 8 files in the current batch.
- Dryad curated payload files are now locally present under [data/external/dryad](data/external/dryad).
- deterministic derived schemas were built for all 16 currently downloaded curated external files.
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

- [ ] Freeze the evaluation corpus and gold references for reporting.
- [ ] Produce paper-ready tables and figures.
- [ ] Write the methods section around deterministic-first extraction, provenance, and uncertainty.
- [ ] Write the evaluation section with field-level interpretability rather than opaque scores.
- [ ] Write the retrieval section comparing metadata-only and schema-enhanced behavior.
- [ ] Record limitations, especially around raw binary underdetermination and repository access constraints.

## Immediate Next Steps

1. Decide whether the remaining time-axis accuracy gaps should be handled by semantic merge, deterministic profiling, or evaluation logic.
2. Review whether semantic-merged retrieval should remain a comparison artifact or become the default schema-enhanced variant.
3. Produce paper-ready result tables from the frozen benchmark slice.
4. Revisit the two `keep_not_benchmark` Dryad files later if benchmark scope expands.
5. Expand retrieval hardening further if new same-family Dryad distractors become useful.

## Rebuild Study Artifacts

Create or refresh the pilot corpus:

```bash
python -m high_fidelity_schema_study.create_pilot_corpus
```

Create or refresh deterministic derived schemas for all pilot datasets:

```bash
python -m high_fidelity_schema_study.build_derived_schemas
```

This also refreshes derived-schema deterministic profiles and the internal multi-file relationship profile.

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

## Logging

Project history is recorded in [log.md](log.md).

The current convention is to append dated entries in this shape:

- `Summary`
- `Action Points`
- `Important Process`
