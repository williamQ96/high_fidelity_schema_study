# Benchmark Card 2026-05-15

This benchmark card documents the current reproducible slice for the high-fidelity schema extraction study. It complements the machine-readable freeze in `docs/benchmark_freeze_2026-05-04.json`.

## Intended Use

The benchmark is intended to evaluate whether a deterministic-first pipeline can recover high-fidelity, field-level schema information from heterogeneous scientific data files and turn those schemas into auditable retrieval artifacts.

It is suitable for:

- pilot-scale method evaluation;
- field-level extraction and semantic-label error analysis;
- uncertainty and abstention analysis;
- schema-enhanced retrieval comparisons over a bounded external candidate pool;
- reproducible paper tables and artifact checks.

It is not suitable for claiming broad real-world dataset-search robustness.

## Composition

Internal pilot:

- 9 datasets;
- 3 CSV datasets;
- 3 HDF5 datasets;
- 3 time-series datasets;
- easy, medium, and hard examples in each family;
- field-level gold references under `data/gold`.

External retrieval slice:

- 16 candidate files;
- 10 promoted target files;
- 6 distractor files;
- current query set: 10 intentionally planted queries.

## Collection And Construction

The internal pilot corpus is synthetic and controlled. It is designed to expose extraction behavior across:

- clean metadata;
- partial metadata;
- ambiguous names;
- mixed physical types;
- hierarchical file structure;
- time-axis inference;
- unit and semantic labeling.

The external retrieval pool is assembled from staged Dryad and Zenodo records. Raw downloaded payloads are intentionally not tracked in git; manifests, derived schemas, retrieval artifacts, and reports are tracked.

## Gold References

Internal gold schemas are human-authored field-level references. They include:

- expected physical type;
- expected logical type;
- expected semantic type;
- expected unit;
- field necessity.

The current internal gold references passed a second-pass consistency audit on 2026-05-11. The audit found no blocking consistency errors, but `gold_evidence` arrays remain a future enrichment task.

## Retrieval Relevance Judgments

The current retrieval evaluation uses one expected candidate per query. Queries are intentionally planted to test whether schema-enhanced artifacts can recover known target files from a bounded candidate pool.

The qrels file is `data/retrieval/external_candidate_pool/qrels.json`. It currently records one highly relevant planted target for each query.

Known limitation:

- these planted queries are useful for controlled comparison;
- they are not a substitute for a full user-centered dataset-search benchmark;
- future work should extend qrels with graded non-planted or user-inspired judgments.

## Exclusions

Excluded or deferred files include:

- raw binary files without enough sidecar metadata;
- external files marked `keep_not_benchmark`;
- external semantic merges that are useful working annotations but not final gold references.

## Revision Policy

The frozen slice should not be changed silently. Any benchmark change should include:

- a new freeze document or versioned JSON update;
- an explanation in `log.md`;
- updated regression tests;
- regenerated paper result tables;
- explicit notes about whether headline metrics are comparable to the prior freeze.

## Known Risks

- The internal corpus is intentionally small.
- The external retrieval query set is planted and bounded.
- Some semantic labels remain intentionally conservative or unknown.
- Time-axis evaluation remains the clearest internal gap.
- External semantic-merged fields are not final gold references.
- Evidence-backed annotation improves auditability but does not guarantee semantic truth.

## Current Artifact Pointers

- Freeze: `docs/benchmark_freeze_2026-05-04.json`
- Gold audit: `docs/gold-schema-second-pass-2026-05-11.md`
- Internal baseline: `data/derived/internal_baseline_report.md`
- Retrieval report: `data/retrieval/external_candidate_pool/retrieval_report.md`
- Semantic merge report: `data/semantic_merged/semantic_merge_report.md`
- Paper tables: `docs/paper_result_tables_2026-05-15.md`
- Qrels: `data/retrieval/external_candidate_pool/qrels.json`
- Provenance manifest: `data/derived/provenance_manifest.json`
