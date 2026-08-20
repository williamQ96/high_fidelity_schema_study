# Citation Matrix For Paper Draft

This matrix turns the local deep research report into draft-ready citation keys.
It is not a final bibliography file; it is a bridge for revising
`docs/paper_draft.md`.

Only entries listed as verified in `docs/references.md` are eligible to support
a manuscript claim. Bibliographic verification establishes source identity,
not claim entailment: each use must also stay within the paper role recorded
here and the primary-source boundaries in
`docs/literature/semantic_architecture_literature_review_2026-07-27.md`.
Entries under `Use With Caution` are inventory-only until their identity and
claim role are both verified.

## Core Framing

| Citation key | Work | Paper role |
| --- | --- | --- |
| `Lawrence2017DataReadiness` | Neil D. Lawrence, Data Readiness Levels, 2017 | Positions schema extraction as a readiness step from raw files toward reusable data. |
| `Hiniduma2025DRAI` | Data Readiness for AI: A 360-Degree Survey, 2025 | Frames readiness as multi-dimensional and broader than schema extraction. |
| `Brewer2025ScientificAIReadiness` | Data Readiness for Scientific AI at Scale, 2025 | Connects readiness to scientific AI and large-scale scientific workflows. |
| `Wilkinson2016FAIR` | The FAIR Guiding Principles for scientific data management and stewardship, 2016 | Supports machine-actionable, reusable data framing. |
| `Gebru2021Datasheets` | Datasheets for Datasets, 2021 | Supports benchmark card, intended use, exclusions, and limitations. |
| `Sculley2015TechnicalDebt` | Hidden Technical Debt in Machine Learning Systems, 2015 | Anchors the technical-debt analogy; does not itself validate Model Capability Debt. |
| `Khan2025PromptingInversion` | You Don't Need Prompt Engineering Anymore: The Prompting Inversion, arXiv:2510.22251, 2025 | Provides a narrow GSM8K example in which a restrictive prompt's advantage reverses across model generations; motivates capability-relative re-evaluation but does not validate Model Capability Debt or schema-extraction generalization. |

## Deterministic Profiling And Schema Recovery

| Citation key | Work | Paper role |
| --- | --- | --- |
| `Abedjan2015Profiling` | Profiling Relational Data: A Survey, 2015 | Anchors deterministic profiling: types, patterns, uniqueness, dependencies. |
| `Schelter2018Deequ` | Automating Large-Scale Data Quality Verification, 2018 | Supports data-quality checks as reusable artifacts. |
| `Breck2019TFDV` | Data Validation for Machine Learning, 2019 | Supports feature/schema validation as pipeline infrastructure. |
| `Adelfio2013TableExtraction` | Schema Extraction for Tabular Data on the Web, 2013 | Supports structure recovery from messy tabular sources. |
| `Sherlock2019SemanticTypes` | Sherlock semantic data type detection, 2019 | Supports semantic typing from table/value features while motivating stricter evidence boundaries. |
| `Suhara2022Doduo` | Annotating Columns with Pre-trained Language Models, 2022 | Provides a supervised whole-table CTA/CPA comparator for applicable relational cases. |
| `Feuer2024ArcheType` | ArcheType, 2024 | Motivates explicit context-sampling, serialization, model-query, and label-remapping ablations. |
| `Korini2025CPA` | Column Property Annotation Using Large Language Models, 2025 | Provides the direct basis for the bounded NDP-50 CPA prompt/demonstration/vocabulary study. |

## Provenance, Unknowns, And Standards

| Citation key | Work | Paper role |
| --- | --- | --- |
| `W3C2013PROVDM` | PROV-DM: The PROV Data Model, 2013 | Anchors entity/activity/agent provenance framing. |
| `Cheney2009DatabaseProvenance` | Provenance in Databases: Why, How, and Where, 2009 | Supports why/where/how lineage for field-level claims. |
| `DataCite2024MetadataSchema` | DataCite Metadata Schema 4.6, 2024 | Supports machine-recognizable unknown handling. |
| `W3C2024DCAT3` | Data Catalog Vocabulary Version 3, 2024 | Supports discoverable dataset/catalog outputs. |
| `ROCrate2023Spec` | RO-Crate Metadata Specification 1.1, 2023 | Supports future artifact packaging. |
| `CFConventions` | CF metadata conventions | Supports standards-backed scientific variable and unit interpretation. |
| `UCUM` | Unified Code for Units of Measure | Supports machine-readable unit normalization. |

## Dataset Search And Discovery

| Citation key | Work | Paper role |
| --- | --- | --- |
| `GoogleDatasetSearch2020` | Google Dataset Search | Supports dataset-search motivation and metadata limits. |
| `Chapman2020DatasetSearchSurvey` | Dataset search survey | Supports restrained retrieval claims and user-context limitations. |
| `Aurum2018` | Aurum data discovery system | Supports schema/value signals for discovery. |
| `D3L2020` | Dataset Discovery in Data Lakes | Supports discovery beyond metadata-only search. |
| `Auctus` | Auctus: A Dataset Search Engine for Data Discovery and Augmentation, 2021; DOI `10.14778/3476311.3476346` | Supports structure-aware dataset discovery and augmentation framing; not schema-extraction accuracy. |
| `Zhang2026AutoDDG` | AutoDDG, 2026; DOI `10.1145/3786626` | Supports the adjacent profiler-to-LLM dataset-description and retrieval pipeline; not schema-claim correctness. |

## Evidence-Constrained LLM Annotation

| Citation key | Work | Paper role |
| --- | --- | --- |
| `RARR` | Researching and Revising What Language Models Say | Supports evidence-backed model revision rather than unsupported generation. |
| `Menick2022VerifiedQuotes` | Teaching language models to support answers with verified quotes | Supports attribution requirements and abstention when support is insufficient. |
| `AttributedQA` | Attributed question answering | Supports evidence-backed answers and claims. |
| `Kadavath2022SelfKnowledge` | Language Models Mostly Know What They Know | Supports confidence and abstention discussion. |
| `Geifman2017SelectiveClassification` | Selective Classification for Deep Neural Networks | Supports `unknown` as a reject option. |
| `Traub2024SelectiveEvaluation` | Overcoming Common Flaws in the Evaluation of Selective Classification Systems, NeurIPS 2024; DOI `10.52202/079017-0076` | Supports qualified AURC reporting and a preregistered AUGRC sensitivity. |

## Annotation, Contamination, And Cost

| Citation key | Work | Paper role |
| --- | --- | --- |
| `Berzak2016Anchoring` | Anchoring and Agreement in Syntactic Annotations, 2016 | Motivates prediction-blind independent submissions; general evidence only. |
| `Cohen1960Kappa` | A Coefficient of Agreement for Nominal Scales, 1960 | Defines the nominal two-rater kappa reported with marginal support. |
| `Krippendorff2018ContentAnalysis` | Content Analysis, fourth edition, 2018 | Supports a fully specified descriptive alpha sensitivity when unitization and distance are frozen. |
| `Sainz2023Contamination` | NLP Evaluation in Trouble, 2023 | Supports explicit pretraining-contamination limitations; does not prove development data inadmissible. |
| `Chen2023FrugalGPT` | FrugalGPT, 2023 | Supports joint quality/resource reporting; not a direct NDP baseline. |

## Reproducibility

| Citation key | Work | Paper role |
| --- | --- | --- |
| `Pineau2021Reproducibility` | Improving Reproducibility in Machine Learning Research, 2021 | Supports frozen artifacts and reproducibility checklists. |
| `ACMArtifactBadging` | ACM Artifact Review and Badging | Supports reproducible artifact reporting. |
