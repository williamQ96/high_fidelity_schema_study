# A Deterministic-First Framework for High-Fidelity Schema Extraction from Scientific Data Files

Status: paper-ready draft v0.5, generated from frozen study artifacts and constrained by `docs/academic_rigor_audit.md`.

## Abstract

Scientific data repositories contain a large amount of reusable data, but their files often expose schema information unevenly across headers, hierarchical paths, sidecar documentation, units, and repository metadata. This makes automated reuse difficult: an extraction system must recover physical structure, infer logical roles, and represent semantic meaning without inventing unsupported claims. We present a deterministic-first framework for high-fidelity schema extraction from heterogeneous scientific data files. The framework separates physical, logical, and semantic schema layers; requires field-level evidence for extracted claims; and allows LLM-assisted semantic annotation only as a constrained enrichment step over deterministic structure.

We evaluate the framework on a frozen pilot slice containing 9 internal datasets and a 16-file external retrieval pool from Dryad and Zenodo. On the internal slice, deterministic extraction reaches 1.0000 physical completeness, 0.9815 physical accuracy, 0.9444 logical accuracy, and 1.0000 semantic accuracy. Every deterministic field in the internal slice has source evidence, and all accepted semantic merges cite supporting evidence. On the external retrieval slice, schema-enhanced retrieval reaches Recall@1 of 1.0000 on planted single-positive queries, compared with 0.7000 for metadata-only retrieval and 0.5000 for README-only retrieval. Evidence-constrained semantic merge improves logical accuracy on 2 of 3 reviewed internal datasets without measured metric regression. The current results support the claim that deterministic-first schema extraction can produce auditable field-level artifacts and improve controlled retrieval, while broader user-centered retrieval robustness remains future work.

## 1. Introduction

Scientific datasets are often distributed as CSV files, HDF5 files, time-series bundles, or related combinations of raw payloads and repository metadata. Their structure is partly explicit and partly implicit. A CSV header may expose a field name but not its role. An HDF5 dataset path may expose hierarchy, shape, and attributes, but not whether a variable is a measurement, identifier, coordinate, or time axis. A README may describe units or domain meaning, but it may not map cleanly to every machine field.

This creates a core problem for schema extraction: a system that guesses aggressively can produce complete-looking schemas that are not auditable, while a system that only records raw physical structure may be too weak for retrieval and reuse. High-fidelity schema extraction therefore requires a boundary between claims that are directly supported by file evidence, claims derived by deterministic rules, and semantic hypotheses that must remain unknown unless evidence supports them.

This paper studies a deterministic-first approach. The approach first extracts file-grounded structure and evidence, then optionally applies evidence-constrained semantic annotation. LLMs are not used to invent schema fields or overwrite deterministic evidence. They may only propose supported annotations over existing fields, and merge logic records conflicts instead of silently resolving them.

The contributions are:

- a layered schema contract separating physical, logical, and semantic claims;
- deterministic extractors for CSV, HDF5, and time-series organization with field-level evidence;
- a claim-state model for supported, derived, conflicted, and unknown schema assertions;
- evidence adequacy metrics that evaluate whether claims are auditable separately from whether labels are correct;
- a frozen pilot benchmark slice with internal gold schemas, external retrieval candidates, qrels, provenance export, and regression tests;
- an evaluation showing strong deterministic extraction, controlled retrieval gains from schema-enhanced artifacts, and safe semantic merge behavior.

## 2. Related Work

This study is positioned at the intersection of data profiling, dataset documentation, scientific data readiness, provenance, semantic annotation, and dataset search.

Datasheets and benchmark cards motivate explicit documentation of dataset composition, intended use, exclusions, and revision policy [Gebru2021Datasheets]. FAIR and scientific data-readiness literature motivate machine-actionable metadata, provenance, and reuse-oriented quality signals [Wilkinson2016FAIR; Lawrence2017DataReadiness; Hiniduma2025DRAI; Brewer2025ScientificAIReadiness]. Data profiling and data discovery systems motivate extracting field types, units, missingness, identifiers, and relationship candidates from the data itself [Abedjan2015Profiling; Schelter2018Deequ; Breck2019TFDV]. Provenance standards motivate representing schema claims as outputs of identifiable activities and agents, not as opaque strings [W3C2013PROVDM; Cheney2009DatabaseProvenance]. Dataset search work motivates evaluating whether schema-aware representations improve retrieval beyond repository metadata and free-text descriptions [GoogleDatasetSearch2020; Chapman2020DatasetSearchSurvey; Aurum2018; D3L2020].

The present framework differs from LLM-first extraction workflows by treating the LLM as a constrained annotation stage rather than the source of structural truth. That choice follows evidence-attribution and abstention work: unsupported model output is not treated as schema truth, and the correct action for underspecified fields is `unknown` rather than forced completion [RARR; Menick2022VerifiedQuotes; Geifman2017SelectiveClassification]. The framework also separates evidence adequacy from label accuracy: a correct label without evidence is not equivalent to an auditable supported claim.

Citation keys used in this draft resolve to the verified artifact bibliography in `docs/references.md`; `docs/literature/citation_matrix.md` records how each source supports the paper narrative. Venue-specific reference formatting is intentionally outside the current artifact package.

## 3. Method

### 3.1 Layered Schema Representation

The framework represents each file through three schema layers:

- physical schema: fields, paths, shapes, physical types, missingness, and file-local structure;
- logical schema: roles such as identifier, coordinate, time axis, measurement, label, group key, or unknown;
- semantic schema: domain-level meaning such as air temperature, latitude, station identifier, postal zone code, or unknown.

The layers are intentionally separated. Physical structure can be directly observed. Logical role is often derived from physical type, name, path, and value profile. Semantic type may require documentation or domain evidence and is allowed to remain unknown.

### 3.2 Deterministic Extraction

The deterministic layer handles CSV, HDF5, and time-series organization with modality-specific, file-grounded rules. CSV extraction records headers, sampled values, physical types, missingness signals, name-based unit hints, and conservative logical or semantic labels. HDF5 extraction traverses groups and datasets and records paths, shapes, dtypes, and attributes such as units or descriptions. Time-series profiling records organization-level regularity and file relationships without adding synthetic fields to the evaluated schema.

The deterministic layer is conservative by design. It may infer weak claims from deterministic patterns, but it reports confidence and uncertainty reasons when evidence is partial. Unsupported semantic claims are represented as `unknown` rather than guessed.

### 3.3 Schema Claim Model

The claim model defines schema assertions as field-level claims. Claim states are:

- supported: direct evidence supports the claim;
- derived: deterministic rules infer the claim from supported evidence;
- conflicted: evidence or annotations disagree;
- unknown: evidence is missing, weak, or underspecified.

Reason codes include explicit file structure, explicit metadata, header or path name, sample profile, name pattern, gold reference, LLM-supported annotation, conflicting evidence, weak evidence, and unsupported-by-deterministic-layer.

### 3.4 Evidence-Constrained Semantic Annotation

Semantic annotation is a second-stage enrichment over deterministic fields. The annotation task receives deterministic fields and approved evidence snippets. A non-unknown logical, semantic, or unit claim must cite supporting evidence. The merge policy accepts an annotation only when:

- the target field exists in the deterministic schema;
- supporting evidence is cited;
- the proposed logical type is compatible with the semantic type;
- explicit metadata is not overwritten by weaker evidence;
- conflicts are preserved rather than collapsed.

Accepted semantic claims are annotations over deterministic structure. They are not automatically promoted to gold references.

### 3.5 Provenance Export

The study exports a lightweight PROV-like manifest linking files, fields, evidence records, semantic annotation results, merge outputs, and reports. The current provenance export contains 218 entities, 31 activities, and 6 agents over 9 internal datasets. This makes the extraction process inspectable without requiring a full PROV-O implementation.

## 4. Benchmark Slice

The frozen benchmark slice contains 9 internal pilot datasets and 16 external retrieval candidate files (Figure 1). The internal pilot covers CSV, HDF5, and time-series modalities, with easy, medium, and hard cases for each family. Internal gold schemas are human-authored field-level references and passed a second-pass consistency audit with no blocking consistency errors. The slice is a controlled artifact for method validation and error analysis, not a claim of domain-wide coverage.

![Figure 1. Frozen benchmark slice](figures/figure_1_benchmark_slice.svg)

The external retrieval pool contains 10 promoted target files and 6 distractor files from staged Dryad and Zenodo records. The current retrieval qrels use one highly relevant planted target for each of 10 queries. This is suitable for controlled comparison of retrieval artifact representations, but not for broad claims about real-world user search robustness.

## 5. Evaluation

### 5.1 Deterministic Extraction Accuracy

On the internal slice, deterministic extraction reaches the aggregate metrics in Figure 2 and the table below. These metrics compare generated field-level schema claims with the reviewed internal gold schemas and should be read together with the evidence adequacy and error-mode results.

![Figure 2. Internal deterministic extraction metrics](figures/figure_2_internal_baseline_accuracy.svg)

| Metric | Value |
| --- | ---: |
| Physical completeness | 1.0000 |
| Physical accuracy | 0.9815 |
| Logical completeness | 0.9630 |
| Logical accuracy | 0.9444 |
| Semantic completeness | 0.9815 |
| Semantic accuracy | 1.0000 |
| Unit accuracy | 0.8889 |
| High-necessity coverage | 1.0000 |
| Time-axis accuracy | 0.6667 |

By family, CSV has lower logical and unit accuracy than HDF5, while time-series has the clearest remaining time-axis evaluation gap. The main error modes are time-axis mismatch, unexpected fields, logical unknowns, one logical mismatch, and one physical type mismatch.

### 5.2 Evidence Adequacy

Every deterministic field in the internal slice has at least one source evidence record (Figure 3). All 53 derived fields have confidence values. Fifteen fields have uncertainty reasons, indicating that uncertainty is surfaced rather than hidden. All 22 unit claims have unit evidence; 9 are backed by explicit metadata and 13 by name patterns. All 3 accepted semantic merges cite supporting evidence, and there are 0 unsupported accepted semantic merges.

![Figure 3. Evidence adequacy ratios](figures/figure_3_evidence_adequacy.svg)

This evidence adequacy result is separate from accuracy. It measures whether the system can audit its own claims, not whether each label is correct. Similarly, provenance improves traceability and debugging, but it does not by itself guarantee semantic truth.

### 5.3 Semantic Merge

Semantic merge is evaluated on 3 internal datasets with both gold references and semantic merge outputs. The aggregate result is:

- improved datasets: 2 of 3;
- accepted semantic merges: 3;
- conflicts: 1;
- mean logical accuracy delta: +0.1667.

The strongest gain appears in `csv_hard_field_campaign`, where logical accuracy improves from 0.6667 to 1.0000 after two accepted evidence-backed merges (Figure 5). `csv_easy_weather_stations` improves from 0.8333 to 1.0000. `hdf5_hard_ocean_profile` records one conflict and no metric change. These results show that semantic augmentation can be useful, but the current evidence supports a bounded claim: the merge policy is safe and can improve selected logical labels. It does not yet prove broad semantic benefit across a large benchmark.

![Figure 5. Semantic merge logical-accuracy delta](figures/figure_5_semantic_merge_delta.svg)

## 6. Retrieval Experiment

The retrieval experiment compares metadata-only, README-only, deterministic schema-enhanced, and semantic-merged schema-enhanced artifacts over the 16-file external candidate pool. The current qrels are single-positive planted judgments, which makes the experiment suitable for controlled comparison of artifact representations but insufficient for open-ended user-search claims.

![Figure 4. Retrieval metrics by artifact](figures/figure_4_retrieval_metrics.svg)

| System | Recall@1 | Recall@3 | Precision@1 | MRR | nDCG@3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| metadata_only | 0.7000 | 0.7000 | 0.7000 | 0.7617 | 0.7000 |
| readme_only | 0.5000 | 0.8000 | 0.5000 | 0.6610 | 0.6762 |
| schema_enhanced | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| schema_enhanced_deterministic | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| schema_enhanced_semantic_merged | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

Schema-enhanced representations improve Recall@1 by +0.3000 over metadata-only retrieval on this controlled slice. The improvement is driven by field-level and slice-specific signals that are absent or weaker in metadata and README text. The result should be interpreted as evidence that schema artifacts can improve controlled planted-query retrieval over this bounded 16-file pool, not as evidence that the system is robust for open-ended dataset search.

## 7. Discussion

The results support three main observations.

First, deterministic extraction can recover a high fraction of useful schema information when the target modalities are CSV, HDF5, and organized time-series bundles. The strongest deterministic results occur when files expose explicit structure or metadata.

Second, evidence adequacy is measurable and useful. The project can report not only whether a predicted label matches gold, but also whether that label was supported, derived, conflicted, or unknown. This is critical for high-fidelity extraction because unsupported completeness can be misleading.

Third, semantic annotation is most useful when treated as controlled enrichment. The semantic layer improves selected logical labels and preserves safety by rejecting unsupported or conflicting claims. The measured semantic gains are promising but still limited in scope.

## 8. Limitations

The internal pilot is small and synthetic by design. It is suitable for validating method behavior and failure modes, not for claiming coverage over all scientific data.

The external retrieval experiment uses planted single-positive qrels. These qrels support controlled artifact comparison, but future work should add non-planted, user-inspired, or graded relevance judgments.

Raw binary files without sidecar metadata remain out of scope. The current method intentionally avoids making unsupported claims for underdetermined files.

External semantic-merged fields are protected as high-confidence working annotations, not final gold references. Promoting them to gold would require additional manual review or codebook evidence.

Time-axis evaluation remains the clearest internal gap. The current frozen slice reports aggregate `time_axis_accuracy = 0.6667`, time-series-family `time_axis_accuracy = 0.0000`, and 3 `time_axis_mismatch` error-mode cases. This paper treats the gap as an explicit evaluation/extraction boundary rather than forcing a metric change during the current convergence round.

## 9. Conclusion

This study presents a deterministic-first framework for high-fidelity schema extraction from scientific data files. The framework makes structural extraction auditable, constrains semantic annotation to evidence-backed claims, and separates accuracy from evidence adequacy. On the frozen pilot slice, deterministic extraction achieves high field-level accuracy, schema-enhanced artifacts improve controlled planted-query retrieval, and semantic merge improves selected logical labels without measured regression. The accompanying artifact package provides generated tables, figures, a verified artifact bibliography, a rigor audit, and a read-only GUI inspection demo.

## Artifact Sources

- `docs/paper_result_tables_2026-05-15.md`
- `docs/figures/README.md`
- `docs/literature/citation_matrix.md`
- `docs/references.md`
- `docs/academic_rigor_audit.md`
- `docs/time_axis_gap_adjudication.md`
- `docs/artifact_handoff.md`
- `docs/benchmark_card_2026-05-15.md`
- `docs/schema_claim_model.md`
- `data/derived/provenance_manifest.json`
- `data/retrieval/external_candidate_pool/qrels.json`
- `data/retrieval/external_candidate_pool/retrieval_report.md`
- `data/semantic_merged/semantic_merge_report.md`
