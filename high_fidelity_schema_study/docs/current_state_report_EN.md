# Current State Report

Date: 2026-05-01

## 1. Original Goal

The project started with a narrow research goal:

- build a **high-fidelity schema extraction study**
- avoid the weak pattern of "let an LLM read a file and guess the schema"
- use a **deterministic-first** pipeline
- allow LLMs only to add bounded semantic interpretation, not to invent structure
- evaluate performance at the **field level**, not just with one opaque score

In practical terms, the study set out to answer:

- how much schema can be recovered deterministically from real scientific data files?
- when semantic augmentation is added carefully, does it improve usefulness without reducing trustworthiness?
- does evidence-grounded schema extraction improve retrieval behavior over metadata-only baselines?

## 2. Plan

The work was planned in stages:

1. Define a layered schema target and evaluation dimensions.
2. Build a small internal pilot corpus across CSV, HDF5, and time-series data.
3. Build deterministic extractors and baseline reports.
4. Expand into an external corpus from Zenodo and Dryad.
5. Build retrieval artifacts and compare metadata-only, README-only, and schema-enhanced retrieval.
6. Add a semantic layer with strict evidence constraints.
7. Measure whether semantic augmentation produces real gains.

## 3. Method

The core method is:

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
Evaluation
```

The key methodological commitment is:

- **deterministic structure first**
- **semantic augmentation second**
- **evidence attached to every claim**

## 4. Special Terms

### Pilot

A `pilot` dataset or `pilot corpus` is a deliberately small, controlled first-round corpus used to validate the method before scaling.

It is not the final benchmark. It is the place where we check:

- whether the pipeline runs end to end
- whether the schema output shape is correct
- whether the evaluation makes sense
- where failure modes appear early

### Gold

`Gold` means the human-authored reference truth used for evaluation.

A gold schema is the field-level answer key. It records:

- physical type
- logical type
- semantic type
- units
- necessity / importance

Gold is not the model output. Gold is what the model output is judged against.

### External

`External` means real datasets from outside the hand-built internal pilot corpus, mainly from:

- Zenodo
- Dryad

These files matter because they test whether the method still works on real public data rather than only on controlled examples.

### Same-Family Distractor

A `same-family distractor` is a file from the same dataset family or record bundle as the target, but not the actual intended match.

This is one of the hardest retrieval settings, because the distractor shares:

- domain
- metadata
- many field names
- a common record description

### Cross-Domain Distractor

A `cross-domain distractor` is a file from a different dataset family or topic.

This is useful for testing broad robustness, but it is usually easier than same-family discrimination.

## 5. What Has Been Built

### Internal pilot corpus

Built:

- 9 internal pilot datasets
- 9 gold schemas
- 9 deterministic derived schemas

Coverage:

- CSV
- HDF5
- time-series organization

### Deterministic extraction

Built:

- conservative CSV extractor
- time-series profiler
- HDF5 extractor
- deterministic batch builders

### Evaluation

Built:

- internal field-level baseline evaluation
- uncertainty analysis
- grouped error-mode analysis

### External corpus

Built:

- curated source manifest
- local external payload corpus
- deterministic derived schemas for the current curated files

Current curated external corpus:

- 16 local files
- 16 derived schemas

### Retrieval

Built:

- metadata-only retrieval artifacts
- README-like retrieval artifacts
- schema-enhanced retrieval artifacts
- planted query set
- retrieval report

Current retrieval pool:

- 16 files total
- 10 targets
- 6 distractors

### Semantic layer

Built:

- evidence-constrained semantic grounding bundles
- semantic annotation runner
- result normalization
- validation
- conservative merge-back
- semantic merge report

Current validated semantic smoke results:

- 2 internal tasks
- 4 external tasks

## 6. Special Methodological Choices

Several choices are deliberate and unusual relative to more naive "LLM schema extraction" workflows.

### Layered schema representation

The project separates:

- physical schema
- logical schema
- semantic schema

This prevents structure from being mixed with interpretation.

### Evidence-grounded merging

The semantic layer is allowed to suggest meaning, but not to freely rewrite the schema.

If a semantic output:

- lacks supporting evidence
- conflicts with explicit metadata
- proposes an incompatible logical type

then it is tracked, but not silently merged.

### No-regression-first semantic policy

The semantic layer is currently optimized for safety:

- accepted merge if evidence is present
- rejection if evidence is weak
- conflict recording if semantics are incompatible

This means the semantic layer may be low-yield at first, but it is less likely to damage trust.

## 7. Current Metrics Snapshot

### Internal deterministic baseline

The current deterministic baseline is strong.

Highlights:

- physical completeness: `1.0000`
- physical accuracy: `0.9815`
- logical accuracy: `0.9444`
- semantic accuracy: `1.0000`

This means the deterministic baseline already solves a large fraction of the problem.

### Retrieval

On the current 16-file / 10-target pool:

- `metadata_only recall_at_1 = 0.6000`
- `readme_only recall_at_1 = 0.5000`
- `schema_enhanced recall_at_1 = 0.8000`

This is important because the schema-enhanced representation still wins even after adding harder Dryad-backed targets and distractors.

### Semantic merge

Current semantic-merge result:

- accepted merges exist
- no regression has been observed
- but no clear metric-level gain has been demonstrated yet on the evaluated internal samples

This is a scientifically useful state:

- the semantic layer is not fake
- the semantic layer is not yet clearly beneficial

## 8. Current Limits

### 1. Semantic execution reliability

Some semantic tasks still fail, not because of missing data, but because of model execution issues:

- timeout
- endpoint instability
- context pressure

This is currently the biggest operational bottleneck.

### 2. Semantic yield is still low

The semantic layer can produce accepted merges, but not yet at a level that clearly improves benchmark metrics.

The key issue is not "can the model say something intelligent?"

The real issue is:

- can the model produce evidence-carrying outputs
- that survive validation
- that survive merge safety checks
- and that improve gold-aligned metrics

### 3. Benchmark scale is not final

The project now has a meaningful external corpus, but it is not yet a fully frozen benchmark.

### 4. Human review is incomplete

The gold set still needs a second-pass review if the project is moving toward publication.

## 9. What Needs Human Action

At this moment, very little manual data acquisition is needed.

The external corpus is already large enough to continue method work.

The main human effort needed later is:

- benchmark freeze decisions
- final gold review
- publication-quality interpretation

## 10. Next Steps

Most useful next steps:

1. Improve semantic runner reliability.
2. Increase semantic evidence yield.
3. Find the first accepted semantic merge that creates measurable gain.
4. Add broader regression comparisons.
5. Decide whether the two `keep_not_benchmark` Dryad files should stay out of the benchmark or move into a later benchmark tier.

## 11. Convergence

The project is not yet converged to its final scientific endpoint.

### What has converged

- deterministic extraction architecture
- baseline evaluation structure
- retrieval comparison framework
- external corpus ingestion framework

### What has not converged

- semantic-layer net gain
- final benchmark freeze
- publication-ready reporting

The clearest convergence condition from here is:

- at least one accepted semantic merge must produce measurable gold-aligned improvement
- across more than a single smoke-run case

Until that happens, the semantic layer should be considered **safe but not yet proven beneficial**.

## 12. Bottom Line

Current stage:

- deterministic-first extraction: working
- internal baseline evaluation: working
- larger external retrieval pool: working
- retrieval advantage of schema-enhanced artifacts: demonstrated
- semantic execution path: working
- semantic merge safety: demonstrated
- semantic net gain: not demonstrated yet
- final benchmark: not frozen
- paper stage: not reached

The project is in a strong experimental systems phase.

The next real milestone is not more infrastructure. The next milestone is **evidence-backed semantic improvement that measurably helps the benchmark**.
