# Dryad Semantic Merge Retrieval And Benchmark Impact

Date: 2026-05-04

## Scope

This review covers the two newly validated Dryad semantic-merged outputs:

- `dryad/10.5061_dryad.2f2b3/...fjord_year1.csv`
- `dryad/10.5061_dryad.zkh1893nh/functional_traits.csv`

The goal was to determine whether the new semantic merge outputs should change retrieval behavior or benchmark status.

## Current Retrieval Integration

Retrieval artifacts now include explicit schema-source comparison modes:

- `schema_enhanced`: backward-compatible deterministic schema artifact
- `schema_enhanced_deterministic`: explicit deterministic-only artifact
- `schema_enhanced_semantic_merged`: semantic-merged schemas where available, deterministic fallback otherwise

Schema-enhanced documents also now include repeated file-slice and time-slice terms such as `year1`, `school5`, and `jan` to make same-family distractors easier to separate when the query specifies a slice.

## Retrieval Check

| Artifact | Recall@1 | Recall@3 | MRR | nDCG@3 |
| --- | ---: | ---: | ---: | ---: |
| metadata_only | 0.7000 | 0.7000 | 0.7617 | 0.7000 |
| readme_only | 0.5000 | 0.8000 | 0.6610 | 0.6762 |
| schema_enhanced | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| schema_enhanced_deterministic | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| schema_enhanced_semantic_merged | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

The explicit schema-source modes now separate the effect of deterministic schema text from semantic-merged schema text. In this lexical setup, both schema-source variants retrieve all planted targets at rank 1 after slice disambiguation.

### Greenland Cod Year1

Before slice disambiguation, schema_enhanced ranked the year2 distractor above year1. After adding year/file-slice terms and making the query explicitly ask for year1 / first-year data:

- expected: `...fjord_year1.csv`
- top1: `...fjord_year1.csv`
- top1 correct in both deterministic and semantic-merged schema-source modes

The merge adds useful logical structure to year1:

- `Hourbin`, `Month`, `Year` -> `time_axis`
- `COA_Lat`, `COA_Lon`, `POINT_X`, `POINT_Y` -> `coordinate`
- `Tag` -> `identifier`
- `Transplant`, `Cove` -> `label`

The key retrieval fix was not the generic logical types by themselves. It was adding explicit file-slice evidence (`year1`, `first-year`) so the query can distinguish year1 from the year2 same-family distractor.

### Functional Traits

After adding schema-source comparison and slice-aware artifacts:

- expected: `functional_traits.csv`
- top1: `functional_traits.csv`
- top1 correct in both deterministic and semantic-merged schema-source modes

The merge adds useful logical structure:

- `Species` -> `identifier`
- `Mass.g` -> `measurement`, unit `g`
- taxon/resource columns -> mixed `label` and `measurement`

The target remains top1. Semantic-merged schema text still adds generic logical words, so future retrieval work should keep field names and file identity weighted strongly.

## Benchmark Impact

### Keep Both As Promoted Targets

Both files still satisfy their current benchmark roles:

- Greenland cod year1 remains a strong movement/telemetry target with temporal, coordinate, identifier, and treatment/site fields.
- `functional_traits.csv` remains a compact ecological trait target with entity rows and interpretable trait columns.

### Do Not Treat Semantic Merge As Final Gold

The semantic merges are useful but not gold-quality benchmark references yet.

For Greenland cod year1:

- logical roles are plausible and useful
- semantic types remain mostly `unknown`
- latitude/longitude-like fields are not yet normalized to explicit `latitude`/`longitude`
- year1/year2 distinction still depends on file identity or temporal slice, not schema semantics

For `functional_traits.csv`:

- `Species` and `Mass.g` are strong accepted merges
- trait columns have inconsistent logical assignments (`label` vs `measurement`) across similar 0-3 coded fields
- precise semantic meanings remain unknown without a codebook or paper-specific trait definition

## Recommendation

Keep both schema-source modes for now.

Next retrieval-facing changes:

1. Treat `schema_enhanced_deterministic` and `schema_enhanced_semantic_merged` as side-by-side comparison artifacts.
2. Do not make semantic-merged retrieval the only default until additional non-planted and harder same-family queries are added.
3. Preserve file-slice/time-slice terms in schema-enhanced artifacts; they fixed the Greenland cod year1/year2 confusion and help with school/month slice distractors.

Next benchmark-facing change:

1. Keep both files promoted.
2. Add external field-subset regression checks for the high-confidence merged fields.
3. Require additional documentation or manual review before promoting the merged semantic fields to gold reference status.
