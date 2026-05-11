# Evaluation Plan

The study should report field-level evidence, not only aggregate performance.

## Primary Dimensions

### 1. Completeness

How many reference schema elements were extracted?

```text
completeness = extracted_reference_matched_elements / reference_elements
```

Report separately for:

- physical completeness
- logical completeness
- semantic completeness

### 2. Accuracy

How many extracted claims are correct?

Suggested split:

- physical accuracy: names, paths, dtypes, shapes
- logical accuracy: identifiers, time axis, measurements
- semantic accuracy: units, descriptions, domain type

### 3. Necessary-Field Coverage

Focus on fields needed for retrieval, discovery, and safe reuse.

Suggested necessary fields:

- variables / measurements
- units
- time coverage
- spatial coverage
- identifier fields
- provenance
- license or access constraints when present

Important rule:

- `unknown` should count better than a hallucinated wrong claim when evidence is insufficient

### 4. Uncertainty

Measure whether confidence aligns with actual correctness.

Suggested analyses:

- confidence calibration buckets
- ambiguity detection rate
- conflict surfacing rate
- unknown-when-unsupported rate

## Retrieval Evaluation

Compare at least three indexing strategies:

1. metadata only
2. file name plus README only
3. schema-enhanced retrieval with evidence-grounded annotations

Suggested metrics:

- Recall@k
- Precision@k
- MRR
- nDCG

Each retrieval example should also include explanation traces showing which extracted schema elements led to the match.

## Error Analysis

For each failed case, record:

- missed field
- incorrect field claim
- unsupported semantic leap
- parser limitation
- source metadata conflict
- retrieval false positive cause
