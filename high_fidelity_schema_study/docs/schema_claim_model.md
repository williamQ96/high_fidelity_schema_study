# Schema Claim Model

This document formalizes how the study treats schema claims. It converts the current design principle, "every claim needs evidence," into a paper-ready contract.

## Claim Scope

A schema claim is any field-level assertion produced by the pipeline:

- field existence;
- physical type;
- logical type;
- semantic type;
- unit;
- shape or cardinality;
- nullable or missingness behavior;
- identifier quality;
- relationship candidate;
- semantic annotation or merge decision.

Dataset-level metadata can summarize claims, but the unit of audit is the field-level claim.

## Claim States

| State | Meaning | Allowed Use |
| --- | --- | --- |
| `supported` | Direct evidence supports the claim. | Structural facts such as CSV headers, HDF5 paths, explicit HDF5 attributes, or gold-reviewed labels. |
| `derived` | Deterministic rules infer the claim from supported evidence. | Name-based units, logical types inferred from physical type plus field name, sampled missingness, identifier quality. |
| `conflicted` | Multiple evidence sources or annotations disagree. | Semantic merge conflicts, unit conflicts, explicit metadata vs weaker inferred semantics. |
| `unknown` | Evidence is missing, weak, or underspecified. | Semantic type, logical type, unit, or relationship claims that cannot be supported safely. |

The default for unsupported semantic claims is `unknown`, not best-effort guessing.

## Reason Codes

| Reason Code | Description |
| --- | --- |
| `explicit_file_structure` | The file directly exposes the field, path, group, shape, or type. |
| `explicit_metadata` | The file directly provides metadata such as HDF5 attributes, units, `long_name`, or descriptions. |
| `header_or_path_name` | A CSV header or HDF5 path provides name evidence. |
| `sample_profile` | Sampled values support physical type, missingness, uniqueness, or range. |
| `name_pattern` | A deterministic naming pattern supports a weak semantic, unit, or identifier claim. |
| `gold_reference` | Human-authored gold schema supports the evaluation target. |
| `llm_supported_annotation` | A semantic annotation references approved evidence IDs and passes merge checks. |
| `conflicting_evidence` | Evidence or annotations disagree and should not be silently collapsed. |
| `weak_evidence` | Evidence is suggestive but insufficient for a supported claim. |
| `unsupported_by_deterministic_layer` | The semantic layer proposed something not grounded in an existing deterministic field or evidence packet. |

## Evidence ID Policy

Evidence IDs should be stable within an artifact:

- deterministic evidence can use IDs such as `D1`, `D2`, `D3`;
- grounding snippets can use IDs such as `S1`, `S2`;
- semantic annotations should cite only available evidence IDs;
- merge outputs should preserve cited evidence IDs and record rejected claims as conflicts.

The current semantic layer already enforces the main rule: a non-unknown semantic, logical, or unit claim needs supporting evidence. Future provenance export should make these IDs stable across deterministic extraction, annotation, merge, and evaluation reports.

## Merge Semantics

The canonical deterministic schema is the base layer. The semantic annotation layer may enrich it only when:

- the field path exists in the deterministic schema;
- the annotation cites supporting evidence;
- the proposed logical type is compatible with the semantic type;
- explicit metadata is not overwritten by weaker evidence;
- confidence is high enough for the merge policy;
- conflicts are recorded instead of silently resolved.

Accepted semantic claims are still annotations over deterministic structure. They are not automatically promoted to gold references.

## Evaluation Implication

Paper reporting should separate:

- structural extraction accuracy;
- logical and semantic label accuracy;
- unit accuracy;
- uncertainty and unknown behavior;
- evidence adequacy.

Evidence adequacy measures whether claims are auditable, not whether they are correct. Both are needed for the paper claim that high-fidelity schema extraction is evidence-grounded.
