# Project Improvement Assessment From Deep Research Report

Source report: `docs/literature/deep_research_report_2026-05-14.md`

## Bottom Line

The current project is aligned with the strongest literature framing: deterministic-first schema recovery, field-level evidence, explicit uncertainty, evidence-constrained LLM annotation, retrieval-aware evaluation, and frozen reproducible artifacts.

The project does not need a conceptual pivot. It needs a convergence pass that formalizes several pieces that already exist informally:

- claim states and reason codes;
- PROV-like provenance serialization;
- standards-backed unit and semantic normalization;
- evidence adequacy metrics;
- benchmark-card documentation;
- retrieval qrels and non-planted query tasks;
- export formats such as Table Schema, RO-Crate, Croissant, or DCAT.

## What The Project Already Does Well

| Area from research report | Current project status | Assessment |
| --- | --- | --- |
| Deterministic-first extraction | CSV, HDF5, and time-series extractors exist; derived schemas are reproducible. | Strong. This is the main architectural strength. |
| Field-level evidence | `FieldSchema.source_evidence` records headers, sampled rows, HDF5 paths, HDF5 unit attributes, and name-based unit hints. | Good foundation, but evidence is still ad hoc rather than standards-aligned provenance. |
| Confidence and uncertainty | `confidence`, `uncertainty_reason`, unknown logical/semantic types, confidence buckets, and unknown-rate reports already exist. | Strong start. Needs explicit claim-state policy. |
| Semantic LLM annotation | Semantic layer validates field paths, requires evidence IDs for supported non-unknown claims, and preserves `unknown`. | Strong and literature-aligned. |
| Semantic merge safety | Merge logic rejects unsupported annotations, conflicts incompatible logical/semantic changes, and keeps conflict metadata. | Strong. This is already better than LLM-first extraction. |
| Gold evaluation | Internal gold schemas, second-pass audit, baseline evaluation, semantic merge evaluation, and regression tests exist. | Strong for pilot scale. Needs evidence-adequacy scoring. |
| Retrieval comparison | Metadata-only, README-only, deterministic schema-enhanced, and semantic-merged schema-enhanced systems are compared. | Strong for a bounded offline slice. Do not overclaim broad dataset-search robustness. |
| Deterministic profiling | Missingness, identifier quality, and shared semantic relationship candidates exist. | Good. Literature suggests obvious next profiling extensions. |
| Reproducible reporting | Frozen benchmark slice and generated paper-ready result tables exist. | Strong. Needs benchmark card and artifact-package framing. |

## Main Improvement Opportunities

### 1. Formalize The Schema Claim Model

Current state:

- Fields have `source_evidence`, `confidence`, `uncertainty_reason`, logical type, semantic type, and unit.
- Semantic annotations have `supporting_evidence`, `confidence`, and `uncertainty_reason`.
- Merge results record accepted annotations and conflicts.

Gap:

- There is no formal per-claim state machine such as `supported`, `derived`, `conflicted`, `unknown`.
- There are no standardized reason codes such as `explicit_metadata`, `name_pattern`, `sample_profile`, `weak_evidence`, `conflicting_evidence`, or `unsupported_by_deterministic_layer`.

Recommended change:

- Add a documented claim model before broadening experiments.
- Start as documentation plus generated summary, not a large model rewrite.
- Later add fields such as `claim_status` and `claim_reason_code` to derived output.

Priority: high.

Why it matters:

- This directly connects the project to PROV, DataCite unknown handling, and abstention literature.
- It makes the difference between deterministic structure and semantic hypothesis explicit.

### 2. Add PROV-Like Provenance Serialization

Current state:

- Evidence records exist but are local dictionaries.
- Merge metadata records conflicts and model info.

Gap:

- Evidence is not represented as entities, activities, and agents.
- Merge history is not formalized as provenance-of-provenance.
- There is no stable evidence ID namespace across deterministic extraction, semantic annotation, and merge outputs.

Recommended change:

- Add a lightweight internal provenance export, for example `data/derived/provenance_manifest.json`.
- Do not implement full PROV-O first. Use a PROV-like structure:
  - `entities`: files, fields, field claims, annotations;
  - `activities`: parser pass, semantic annotation pass, merge pass, evaluation pass;
  - `agents`: deterministic extractor, model name, manual gold review;
  - `wasGeneratedBy`, `wasDerivedFrom`, `used`.

Priority: high.

Why it matters:

- The project claims field-level provenance as a central contribution; the artifact should make that inspectable.

### 3. Standards-Backed Unit And Semantic Normalization

Current state:

- CSV units are inferred from suffixes such as `_C`, `_mm`, `_mg_l`.
- HDF5 units are read from `unit` or `units` attributes.
- HDF5 semantics use path, `long_name`, and `description` heuristics.

Gap:

- No UCUM normalization layer.
- No CF `standard_name` handling.
- No canonical unit table or unit-normalization report.
- No Table Schema export for tabular schemas.

Recommended change:

- Add a small deterministic normalization module with:
  - unit aliases to canonical internal names;
  - UCUM-compatible export strings where simple;
  - HDF5 attribute scan for `standard_name`, `units`, `long_name`, and `description`;
  - explicit `unit_normalization_status`.

Priority: high to medium.

Why it matters:

- The literature report identifies HDF5 + CF + UCUM + Table Schema as the strongest standards backbone for scientific files.
- This is a method improvement, not just paper framing.

### 4. Separate Label Accuracy From Evidence Adequacy

Current state:

- Evaluation reports physical, logical, semantic, unit, high-necessity, time-axis, uncertainty, and error-mode metrics.

Gap:

- A semantically correct label can score as correct even if evidence support is weak or undocumented.
- There is no score for evidence completeness, evidence type, or provenance quality.

Recommended change:

- Add an evidence adequacy table:
  - percent of fields with at least one evidence record;
  - percent of semantic claims with supporting evidence;
  - evidence types by source;
  - unsupported accepted-merge count, expected to be zero;
  - explicit-metadata-backed unit count vs name-inferred unit count.

Priority: high.

Why it matters:

- It turns the central paper claim, "schema claims are evidence-grounded," into a measurable result.

### 5. Create A Benchmark Card / Datasheet

Current state:

- The freeze document records scope, targets, distractors, retrieval systems, regression subsets, and known non-final items.
- Gold schemas have a second-pass consistency audit.

Gap:

- There is no datasheet-style benchmark card covering motivation, composition, collection/generation process, adjudication rules, exclusions, intended use, out-of-scope use, revision policy, and limitations.

Recommended change:

- Add `docs/benchmark_card_2026-05-14.md`.
- Link it from README and paper tables.

Priority: high for paper readiness.

Why it matters:

- This is the easiest way to align with Datasheets for Datasets, FAIR, and reproducibility literature.

### 6. Strengthen Retrieval Evaluation With Qrels And Non-Planted Tasks

Current state:

- `queries.json` has 10 planted query texts and one expected candidate per query.
- Retrieval reports clearly show the planted-slice limitation in docs.

Gap:

- No separate qrels file.
- No graded relevance.
- No user-inspired or repository-inspired queries.
- No query construction protocol beyond the freeze text.

Recommended change:

- Add `qrels.json` with query ID, candidate ID, relevance grade, relevance reason, and construction source.
- Keep current planted queries, but label them as `planted`.
- Add a small second set of `repository_inspired` or `user_inspired` queries, even if not used for headline metrics yet.

Priority: medium.

Why it matters:

- Dataset-search literature strongly warns against overclaiming from planted queries.
- A qrels file makes retrieval evaluation more benchmark-like.

### 7. Expand Deterministic Profiling Toward Data-Discovery Signals

Current state:

- Missingness, identifier quality, and shared semantic relationship candidates exist.

Gap:

- No pattern summaries.
- No candidate key table.
- No inclusion-dependency or value-overlap evidence.
- No relationship graph export.

Recommended change:

- Add profiling outputs incrementally:
  - regex-like value pattern summaries;
  - low-cardinality domain summaries;
  - candidate key report;
  - value-overlap sketches for safe, small tabular files;
  - relationship graph export for field/file candidates.

Priority: medium.

Why it matters:

- This aligns the project with data profiling, Aurum, and D3L-style discovery systems.

### 8. Add Standards-Oriented Export Artifacts

Current state:

- Internal JSON schema artifacts are readable and testable.
- Paper tables are generated.

Gap:

- No Table Schema export.
- No RO-Crate, Croissant, DCAT, or schema.org Dataset export.

Recommended change:

- Start with Table Schema export for CSV/time-series fields.
- Then add an RO-Crate or Croissant packaging experiment for the frozen benchmark.

Priority: medium to low for implementation, high for paper framing.

Why it matters:

- This demonstrates that extracted schemas are not just internal evaluation artifacts; they can feed scientific-data discovery and reuse ecosystems.

## Recommended Convergence Order

1. Write `benchmark_card_2026-05-14.md`.
2. Write `schema_claim_model.md` defining claim state, reason codes, evidence IDs, and merge semantics.
3. Add evidence adequacy metrics to the paper table builder.
4. Add lightweight PROV-like provenance export.
5. Add unit normalization status and a small canonical unit map.
6. Add retrieval qrels and label current queries as planted.
7. Add Table Schema export for tabular outputs.
8. Treat RO-Crate/Croissant, adjudication UI, and larger relationship graph as future-work or post-paper extensions.

## What Not To Do Next

- Do not turn the project into an LLM-first extractor.
- Do not expand the corpus before the current benchmark card, claim model, and evidence metrics are written.
- Do not cite the RNN papers as core related work; keep them out or mark them analogy-only.
- Do not claim broad retrieval robustness from the current planted-query result.
- Do not promote external semantic merges to final gold without manual review or codebook evidence.

## Immediate Next Step

The best next implementation step is not another retrieval run. It is:

> Add a formal schema-claim model and benchmark card, then extend paper-ready result tables with evidence adequacy metrics.

That moves the project from "strong reproducible prototype" toward "defensible paper artifact."
