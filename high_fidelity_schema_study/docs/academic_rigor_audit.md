# Academic Rigor Audit

This audit constrains the paper and demo to claims supported by frozen artifacts. It is a guardrail against overclaiming from a small pilot, planted qrels, or semantic annotations that are not final gold references.

## Claim Boundaries

| Claim | Artifact evidence | Allowed wording | Disallowed wording |
| --- | --- | --- | --- |
| Deterministic extraction works well on the internal pilot. | `docs/paper_result_tables_2026-05-15.md`, Table 2: physical completeness `1.0000`, physical accuracy `0.9815`, logical accuracy `0.9444`, semantic accuracy `1.0000`. | "High field-level accuracy on the frozen 9-dataset internal pilot." | "Solved schema extraction" or "generalizes across scientific data." |
| Evidence adequacy is measurable and currently complete for deterministic fields. | Table 5: 53/53 derived fields with source evidence and confidence. | "Every deterministic field in the current internal slice has source evidence." | "Every schema claim is true" or "provenance guarantees correctness." |
| Semantic merge can improve selected logical labels without measured regression. | Semantic merge report: 3 reviewed datasets, 2 improved, 3 accepted merges, 1 conflict, mean logical delta `+0.1667`. | "Evidence-constrained merge improves logical accuracy on 2 of 3 reviewed internal tasks." | "Semantic augmentation is broadly beneficial" or "LLM labels are validated gold." |
| Schema-enhanced retrieval improves controlled planted-query retrieval. | Retrieval report: schema-enhanced Recall@1 `1.0000`; metadata-only Recall@1 `0.7000`; readme-only Recall@1 `0.5000`. | "Schema-enhanced artifacts improve Recall@1 on the planted 10-query, 16-file external slice." | "Broad retrieval robustness" or "real-world search superiority." |
| External semantic merges are useful working annotations. | Freeze and benchmark card mark external semantic merges as not final gold. | "Protected working annotations." | "External gold references" or "final benchmark truth." |
| Time-axis handling remains a visible gap. | Table 2: time_axis_accuracy `0.6667`; family table: time_series `0.0000`; error modes: `time_axis_mismatch = 3`. | "Time-axis evaluation remains the clearest non-final gap." | Hiding the gap behind aggregate accuracy. |

## Required Cautions In Final Text

- Evidence adequacy measures auditability, not truth.
- Provenance improves traceability and debugging, but does not guarantee semantic correctness.
- The retrieval qrels are planted single-positive judgments, not a full user-centered search benchmark.
- The internal pilot is intentionally small and method-focused.
- LLM semantic annotation is constrained enrichment over deterministic fields, not a structural extractor.

## Current Rigor Status

- Corpus and benchmark scope: artifact-ready for a pilot paper.
- References: verified artifact bibliography exists, with `verification_needed` isolated from core claims.
- Time-axis gap: adjudicated as a limitation for this convergence round.
- GUI: read-only artifact inspection surface; visual smoke screenshots should be stored outside tracked artifacts unless explicitly needed.

