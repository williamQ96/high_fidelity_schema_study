# Stage Report

Date: 2026-04-29

## Checklist Status

Based on the current [README.md](../README.md) checklist:

- Checked items: `54`
- Unchecked items: `14`

Completed phases in practical terms:

- Phase 0: Framing and study design
- Phase 1: Repository and artifact scaffolding
- Phase 2: Internal pilot corpus
- Phase 3: Gold reference construction, except second-pass human review
- Phase 4: Deterministic extraction baseline, except richer profiling
- Phase 5: External corpus preparation
- Phase 6: Validation basics, except broader regression-set comparisons
- Phase 7: Evaluation pipeline
- Phase 8: Semantic augmentation layer, core execution path implemented
- Phase 9: Retrieval experiment

Still materially open:

- richer deterministic profiling
- broader regression testing
- scale-up benchmark hardening
- paper/final-deliverable work

## Current Stage

The project is past pure setup and prototype scaffolding. It is now in a **mid-stage experimental systems phase** with:

- deterministic extraction working across internal pilot modalities
- internal field-level evaluation in place
- external corpus staging and retrieval pool construction in place
- first retrieval comparison completed
- semantic layer execution path implemented and smoke-tested

The project is **not yet** at a final benchmark or paper-ready stage.

## What Works Now

### Deterministic-first extraction

The repository can currently:

- build deterministic schema artifacts for internal CSV, HDF5, and time-series pilot files
- preserve field-level evidence and extraction metadata
- compute internal field-level baseline metrics against gold references
- produce grouped error-mode and uncertainty summaries

Key artifacts:

- [internal_baseline_report.md](../data/derived/internal_baseline_report.md)
- [internal_baseline_report.json](../data/derived/internal_baseline_report.json)

### External corpus and retrieval

The repository can currently:

- stage a curated external corpus from Zenodo plus locally available Dryad payloads
- derive schemas for downloaded external files
- maintain a harder retrieval pool with same-family distractors
- build three retrieval artifact variants:
  - `metadata_only`
  - `readme_only`
  - `schema_enhanced`
- run a first retrieval comparison with planted matches

Key artifacts:

- [retrieval_report.md](../data/retrieval/external_candidate_pool/retrieval_report.md)
- [artifact_manifest.json](../data/retrieval/external_candidate_pool/artifact_manifest.json)
- [pool_manifest.json](../data/retrieval/external_candidate_pool/pool_manifest.json)

Current retrieval snapshot on the expanded 16-file pool:

- `metadata_only recall_at_1 = 0.6000`
- `readme_only recall_at_1 = 0.5000`
- `schema_enhanced recall_at_1 = 0.8000`

### Semantic layer

The repository can currently:

- generate evidence-constrained semantic grounding tasks
- call a local OpenAI-compatible endpoint for semantic annotation
- call a reachable remote OpenAI-compatible endpoint at `http://100.66.106.126:1234/v1`
- normalize model outputs into a stable result contract
- validate outputs
- conservatively merge accepted semantic annotations back into schema artifacts
- reject unsupported or incompatible semantic updates
- report post-merge outcomes

Key artifacts:

- [semantic_annotation_interface.md](semantic_annotation_interface.md)
- [semantic_annotations/manifest.json](../data/semantic_annotations/manifest.json)
- [semantic_merged/manifest.json](../data/semantic_merged/manifest.json)
- [semantic_merge_report.md](../data/semantic_merged/semantic_merge_report.md)

Current semantic status:

- two internal tasks and four external tasks have validated semantic annotation results
- multiple accepted semantic merges now exist, including Dryad-backed external examples
- the remote endpoint exposes `qwen/qwen3.6-27b` and was successfully used for additional semantic smoke runs
- current post-merge evaluation covers two internal merged tasks and shows **no regression**, but still **no net metric gain** on the internal samples evaluated so far
- the two highest-priority remaining Dryad semantic targets, Greenland cod year1 and functional_traits, are still blocked by remote endpoint timeout despite grouped field-slice retries

## What The System Cannot Reliably Do Yet

The repository does **not yet** reliably support:

- broad semantic annotation coverage over many tasks without manual babysitting
- stable semantic execution on smaller local models with tight context windows
- guaranteed evidence-carrying semantic outputs from the model
- benchmark-scale external corpus hardening, even though the current curated Dryad payload set is now locally available
- large-scale benchmark evaluation beyond the current internal pilot and staged external pool
- paper-ready frozen corpus and results

## Main Limits

### 1. Model-context limit in semantic annotation

Some semantic grounding tasks still exceed local model context limits, especially for:

- `csv_medium_water_quality`
- some richer external tasks

This is currently the biggest blocker to scaling semantic coverage. The remote endpoint improves availability, but does not by itself solve evidence-yield or prompt-size issues.

### 2. Low semantic yield despite safe merge logic

The semantic layer is now conservative and safe, but its yield is still low:

- many model outputs omit usable `supporting_evidence`
- unsupported semantic claims are correctly blocked from merge
- accepted merges are still too sparse to produce broad measurable gains

This is scientifically honest, but it means the next iteration must improve **evidence yield**, not just output volume.

### 3. Dryad review remains incomplete

Dryad is no longer blocked for the current curated set. The selected payloads are now locally available.

That means:

- Dryad can now contribute real payload-backed benchmark candidates
- the next problem is review and promotion, not raw acquisition

### 4. Benchmark scale is still modest

The current system has:

- a strong internal pilot
- a meaningful external retrieval pool with 10 targets and 6 distractors

But it does not yet have a large, hardened, final benchmark corpus.

## Next Priorities

### Immediate next step

Most valuable next step:

1. Increase semantic annotation coverage while improving evidence-carrying outputs.

That means:

- keep tasks small
- keep prompts evidence-first
- prefer field-level requests over large bundle requests when needed
- aim for accepted semantic merges that create measurable gold-aligned gains
- use the remote `qwen/qwen3.6-27b` endpoint as the current default semantic smoke target when the local endpoint is unavailable

### After that

1. Decide the fate of the two pending HDF5 benchmark candidates.
2. Review the newly available Dryad files and decide which become benchmark targets versus harder distractors.
3. Expand retrieval evaluation with additional hard distractors or newly downloaded files.
4. Add broader regression comparisons for representative datasets.
5. Move from pilot/external-stage evaluation to a larger frozen benchmark.

## Bottom Line

Current stage:

- **Deterministic extraction:** working
- **Field-level evaluation:** working
- **Harder retrieval pool and comparison:** working
- **Semantic layer execution path:** working
- **Semantic layer net gain:** not demonstrated yet
- **Benchmark completeness:** not finished
- **Paper-ready final stage:** not reached

The project is in a strong exploratory systems phase with real, reproducible artifacts and meaningful evaluation, but the main open problem is now **turning safe semantic augmentation into consistently useful semantic augmentation**.
