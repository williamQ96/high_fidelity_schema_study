# Semantic Annotation Interface

This document defines the evidence-constrained semantic layer contract for the study.

## Purpose

The semantic layer is not allowed to invent schema elements. It operates only on:

- deterministic schema outputs
- README-like text
- source-record metadata
- explicitly supplied grounding snippets

## Input Contract

Each semantic annotation task contains:

- `task_id`
- `dataset_id`
- `file_format`
- `data_modality`
- full deterministic schema payload
- prioritized grounding snippets
- explicit instructions

The current machine-readable task shape is defined in [semantic_layer.py](D:\github\searnxg\llm-schema\high_fidelity_schema_study\semantic_layer.py).

## Grounding Priorities

Use evidence in this order:

1. explicit field metadata in the deterministic schema
2. deterministic structural cues such as names, paths, shapes, and time-axis computations
3. dataset README snippets
4. source-record description, notes, and keywords

Lower-priority text may annotate unresolved meaning, but must not overwrite higher-priority explicit metadata.

## Output Contract

The semantic layer should return:

- field-level semantic annotations
- optional logical-type refinements
- optional units when grounded
- descriptions
- supporting evidence references
- confidence
- uncertainty reason
- explicit conflicts

## Current Status

Implemented now:

- evidence-constrained task schema
- internal grounding bundle generation
- external grounding bundle generation

Not yet implemented:

- live LLM execution over the task bundles
- conflict adjudication policy beyond explicit reporting
- automated merge-back from semantic annotations into final schema artifacts
