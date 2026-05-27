# Deep Research Prompt: Established Work For High-Fidelity Schema Extraction

You are a research assistant helping position and strengthen a project called:

`A Deterministic-First Framework for High-Fidelity Schema Extraction from Scientific Data Files`

## Project Context

The project extracts schema from heterogeneous scientific data files. It is not an end-to-end LLM guessing system. Its core design is:

- deterministic parsers recover file-grounded structure from CSV, HDF5, and time-series data;
- every schema claim should have field-level provenance, evidence, uncertainty, and confidence;
- an LLM-assisted semantic layer may annotate meaning, but it must not invent unsupported fields or unsupported claims;
- unsupported claims should remain `unknown`;
- outputs are evaluated against gold field-level references;
- retrieval experiments compare metadata-only, README-only, deterministic schema-enhanced, and semantic-merged schema-enhanced dataset search;
- benchmark artifacts are frozen for reproducibility;
- deterministic profiles now include missingness, identifier quality, and cross-file relationship candidates.

Current components to map literature against:

- pilot corpus design and benchmark freeze;
- gold schema references;
- deterministic schema extraction;
- field-level provenance/evidence;
- logical type, semantic type, unit, and uncertainty labeling;
- evidence-constrained LLM semantic annotation;
- semantic merge-back with conflict handling;
- retrieval using schema-enhanced artifacts;
- deterministic data profiling and relationship-candidate discovery;
- paper-ready result tables and reproducible reporting.

## Local Seed Papers

Use the following local seed papers as starting points, but do not limit the search to them:

1. `AIDRIN 2.0: A Framework to Assess Data Readiness for AI`
   - file: `docs/literature/A Framework to Assess Data Readiness for AI.pdf`
   - themes: AI data readiness, data quality dimensions, privacy, fairness, usability, readiness inspection.

2. `Data Readiness for Scientific AI at Scale`
   - file: `docs/literature/Data Readiness for Scientific AI at Scale.pdf`
   - themes: scientific AI data readiness levels, processing stages, scalable scientific data pipelines, HPC workflows.

3. `Professor Forcing: A New Algorithm for Training Recurrent Networks`
   - file: `docs/literature/Professor Forcing A New Algorithm for Training.pdf`
   - themes: only analogical relevance unless stronger links are found; useful for thinking about train-time vs use-time behavior alignment and distribution shift.

4. `A Learning Algorithm for Continually Running Fully Recurrent Neural Networks`
   - file: `docs/literature/A Learning Algorithm for Continually Running Fully.pdf`
   - themes: only analogical relevance unless stronger links are found; useful for continual/online temporal behavior framing.

Important: If the RNN papers are not directly relevant to schema extraction, say so clearly. Do not force weak citations into the related-work section.

## Research Goal

Find established, credible, and citable work that can strengthen the project in three ways:

1. Theoretical positioning:
   - Show how this project relates to established ideas in data readiness, data quality, FAIR data, provenance, metadata standards, schema matching, semantic type detection, and scientific data management.

2. Method improvement:
   - Identify mature methods, standards, and evaluation practices that could improve high-fidelity schema extraction, field-level evidence, uncertainty handling, retrieval, and benchmark design.

3. Paper framing:
   - Build a defensible related-work map for a paper, including what this project borrows, what it rejects, and what gap it fills.

## Search Targets

Prioritize established work, surveys, standards, and widely cited systems. Include newer work only when it is directly relevant.

Search across these areas:

1. Data readiness and AI-readiness frameworks
   - data readiness levels;
   - AI data quality assessment;
   - scientific AI data readiness;
   - maturity matrices for data preparation;
   - readiness metrics for ML and foundation models.

2. Data quality and profiling
   - data quality dimensions;
   - data profiling systems;
   - missingness, uniqueness, outliers, constraints, type inference;
   - scientific data quality assessment.

3. FAIR, provenance, and scientific metadata standards
   - FAIR principles;
   - W3C PROV;
   - DataCite metadata;
   - DCAT;
   - schema.org Dataset;
   - RO-Crate;
   - Croissant / MLCommons data metadata;
   - Frictionless Data / Table Schema;
   - HDF5 conventions and CF metadata conventions where relevant.

4. Schema extraction, schema inference, and semantic typing
   - CSV/table schema inference;
   - HDF5 metadata extraction;
   - semantic type detection for columns;
   - unit detection and normalization;
   - table understanding;
   - scientific table interpretation;
   - data dictionaries and codebook extraction.

5. Schema matching, ontology alignment, and entity/field matching
   - schema matching surveys and systems;
   - ontology alignment;
   - column matching;
   - dataset integration;
   - field-level matching with confidence and provenance.

6. Dataset search and retrieval
   - dataset search using metadata, schema, columns, samples, or semantic annotations;
   - data discovery systems;
   - semantic dataset retrieval;
   - benchmark design for dataset search.

7. LLMs for data management, with caution
   - LLM-assisted data cleaning, data integration, metadata extraction, table understanding, or schema matching;
   - evidence-constrained generation;
   - hallucination mitigation;
   - uncertainty and abstention;
   - human-in-the-loop validation.

8. Evaluation and benchmark methodology
   - gold standard construction;
   - field-level metrics;
   - error analysis;
   - reproducibility;
   - benchmark leakage and planted-query limitations.

9. Distribution shift and behavior alignment
   - only if useful for framing semantic annotation or retrieval behavior;
   - distinguish direct relevance from analogy;
   - compare the train/test or prompt/deployment mismatch idea to Professor Forcing only if the link is defensible.

## Required Output

Produce a structured research report with these sections:

1. Executive summary
   - 8-12 bullet points summarizing the strongest established work and how it changes the project.

2. Related-work taxonomy
   - Group the literature into 6-9 categories.
   - For each category, explain the central idea, representative works, and relevance to this project.

3. Annotated bibliography
   - 25-40 high-quality works.
   - For each work include:
     - citation;
     - year;
     - DOI/arXiv/URL when available;
     - 2-4 sentence summary;
     - direct relevance to the current project;
     - whether it should be cited in the paper as core, supporting, background, or analogy-only.

4. Mapping table
   - Rows: project components.
   - Columns: relevant established work, what to borrow, what to avoid, how to implement or cite.
   - Include at least these project rows:
     - deterministic extraction;
     - field-level evidence/provenance;
     - uncertainty/unknown handling;
     - gold schema evaluation;
     - semantic LLM annotation;
     - semantic merge safety rails;
     - retrieval benchmark;
     - deterministic profiling;
     - paper-ready reproducibility.

5. Method recommendations
   - Concrete changes that would strengthen the project.
   - Separate recommendations into:
     - easy documentation changes;
     - medium implementation changes;
     - larger future-work changes.

6. Paper positioning
   - Draft 2-3 possible related-work paragraphs.
   - Draft a concise novelty statement.
   - Draft a limitations paragraph grounded in the literature.

7. Search appendix
   - Include exact search queries used.
   - Include databases searched.
   - Include rejected or weakly relevant clusters.
   - Clearly flag any papers that were not accessible or only available as abstracts.

## Quality Rules

- Prefer primary sources, survey papers, official standards, and established systems.
- Do not cite a paper unless the claim is supported by the paper.
- Distinguish direct relevance from analogy.
- Do not overfit to LLM literature; this project is deterministic-first.
- Do not overclaim retrieval robustness from planted-query experiments.
- Treat external semantic merges as working annotations, not final gold.
- Be explicit when a method is from general data management rather than scientific file extraction.
- Include enough bibliographic detail that citations can be verified later.

## Desired Final Answer Shape

Start with a short thesis:

> The strongest established framing for this project is likely the intersection of data readiness, FAIR/provenance standards, schema/semantic typing, and dataset search, with LLMs used only as an evidence-constrained annotation layer.

Then deliver the full structured report.
