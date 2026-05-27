# Established Work for High-Fidelity Schema Extraction

> The strongest established framing for this project is likely the intersection of data readiness, FAIR/provenance standards, schema and semantic typing, and dataset search, with LLMs used only as an evidence-constrained annotation layer.

This report maps that framing onto the deterministic-first architecture in your brief: file-grounded parsing for CSV/HDF5/time-series data, field-level provenance and evidence, explicit uncertainty and `unknown`, evidence-constrained semantic annotation, schema-enhanced retrieval, deterministic profiling, and frozen reproducible artifacts. fileciteturn0file0

## Executive summary

- The most defensible top-level framing is **not** “LLMs extract schema,” but rather “deterministic schema recovery plus provenance-aware semantic enrichment for scientific data readiness and discovery.” That framing is strongly supported by work on data readiness levels, AI data readiness surveys, scientific AI readiness, FAIR, provenance, and dataset search. citeturn21view2turn23search0turn22view0turn27view0turn27view2turn29view3

- Established data-readiness work is useful for **positioning**, but it does **not** solve your core problem. Lawrence’s readiness levels, the DRAI survey, AIDRIN, and scientific-AI readiness papers give a vocabulary for maturity, quality, governance, privacy, and AI suitability, yet they stop well short of file-grounded, field-level schema extraction with gold references. That is a genuine gap your project can fill. citeturn21view2turn23search0turn24search0turn21view0turn22view0

- The most useful mature methodological base for your deterministic layer is the **data profiling** literature. Classic profiling work explicitly covers single-column statistics, patterns, type discovery, distributions, uniqueness, dependencies, and foreign-key discovery, which aligns closely with your missingness, identifier quality, and relationship-candidate modules. citeturn28view0turn28view1turn28view2

- Your requirement that every schema claim carry field-level evidence and provenance is well grounded in both **W3C PROV** and **database provenance** research. PROV-DM provides the interoperable conceptual model; database provenance explains why, where, and how lineage supports trust, debugging, and explanation. citeturn27view2turn12search0

- Your insistence that unsupported claims remain `unknown` is unusually strong and worth emphasizing. It is supported by two mature literatures: metadata standards that already encode machine-recognizable unknowns, such as DataCite, and selective prediction / abstention work showing that systems should sometimes refuse to answer rather than guess. citeturn25view0turn25view1turn15search3turn18search2

- For scientific files, the strongest standards-and-format stack is **HDF5 + CF + unit normalization**. HDF5 is self-describing and attaches metadata through attributes; CF adds standardized variable names and canonical-unit expectations; UCUM offers machine-processable unit codes for unambiguous electronic communication. This is exactly the kind of standards-based backbone a high-fidelity extractor should exploit before any semantic generation happens. citeturn20search0turn20search2turn20search4turn20search6turn26view3turn26view4

- Retrieval work strongly supports your plan to compare metadata-only, README-only, deterministic schema-enhanced, and semantic-merged schema-enhanced search. Dataset-search and data-discovery literature already shows that metadata alone is often insufficient, while schema- and value-level signals can materially improve discovery. At the same time, user studies warn against overclaiming from toy or planted benchmarks because real dataset search is socio-technical and trust-laden. citeturn29view2turn29view3turn28view3turn28view4turn28view5turn29view1

- The right LLM literature for this project is **attribution, evidence support, and abstention**, not end-to-end free-form extraction. RARR, verified-quote QA, attributed QA, and model self-knowledge work all support a design in which the model only labels or explains claims that are explicitly backed by deterministic evidence. citeturn16search3turn18search0turn18search1turn18search2

- In related work, your project should explicitly say that it borrows from **schema extraction, semantic typing, schema matching, provenance, and dataset search**, but rejects the common move of treating semantic annotation as equivalent to ground-truth structure. Classical table and column semantics papers show value in annotation, but your contribution is the stronger separation between structural facts and semantic hypotheses. citeturn32view4turn32view3turn33view0turn32view1turn31view4

- The benchmark story should be centered on **field-level gold references, reproducibility, and artifact freezing**. Datasheets, reproducibility checklists, and ACM artifact policies all support publishing frozen corpora, adjudication rules, versioned artifacts, and exact experimental configurations. citeturn27view3turn34search3turn34search2turn34search10

- The two RNN seed papers in your brief should not anchor the main related-work section. At most, they provide analogy about train-time versus use-time mismatch or continual temporal behavior; they are not established prior art on schema extraction, metadata, provenance, or dataset retrieval. fileciteturn0file0

## Related-work taxonomy

**Data readiness and AI-readiness frameworks.** This literature defines what it means for data to be ready for analysis or AI use. Lawrence provides a compact maturity framing; the DRAI survey broadens readiness into quality, accessibility, governance, fairness, and privacy; AIDRIN operationalizes some of those dimensions; and Brewer et al. adapt readiness to large-scale scientific AI and HPC pipelines. For your project, this category is best used to justify why schema extraction is part of readiness, not as a substitute for extraction itself. citeturn21view2turn23search0turn24search0turn21view0turn22view0

**Data quality and profiling.** This category gives you the strongest established methods for deterministic profiling. Wang and Strong make “fitness for use” the central data-quality idea, while profiling work formalizes counts, nullness, uniqueness, distributions, pattern inference, dependency discovery, and candidate keys. Deequ and TensorFlow Data Validation show how those signals can be turned into production checks and data-unit tests. This is directly relevant to your deterministic profiles, missingness statistics, identifier quality scores, and cross-file relationship candidates. citeturn9search0turn28view0turn28view1turn28view2

**FAIR, provenance, and scientific metadata standards.** FAIR gives the normative target for machine-actionable discovery and reuse; FAIR metrics add measurable criteria; PROV-DM gives a portable vocabulary for who/what/when/how lineage; DataCite, DCAT, schema.org Dataset, RO-Crate, Croissant, and Table Schema define increasingly operational metadata packages for publication, exchange, and discovery; HDF5, CF, and UCUM provide file- and domain-specific structure for scientific arrays, variables, and units. This is the standards layer that lets your extracted schema plug into the broader scientific-data ecosystem. citeturn27view0turn34search0turn27view2turn25view0turn1search5turn26view1turn26view2turn25view4turn25view3turn25view2turn20search0turn20search2turn26view3turn26view4

**Schema extraction and semantic typing.** Adelfio and Samet show how to recover structure from messy tabular data; Venetis et al. recover table semantics using external evidence and explicit evidence models; Sherlock and Sato show how semantic type detection benefits from rich value features and table context; the semantic-table-interpretation survey integrates the broader annotation landscape. Your project belongs here, but with a stricter emphasis on file-grounded structure, provenance, and abstention than most semantic labeling systems. citeturn32view4turn32view3turn33view0turn32view1turn32view2

**Schema matching and ontology alignment.** Classical schema-matching work is central because it formalizes correspondences, confidence, evidence families, and combinations of name-, structure-, and instance-based signals. But those systems usually assume schemas already exist. Your project is earlier in the pipeline: first recover high-fidelity schema from raw files, then optionally align or enrich. That distinction is worth making explicit in the paper. citeturn31view4turn31view1

**Dataset search and data discovery.** Google Dataset Search, dataset-search surveys, Aurum, D3L, Auctus, and related discovery systems show that richer metadata, schema signals, and instance-level signals materially affect discoverability. User-centered dataset-search work adds a second lesson: discovery is not only a ranking problem, but also a trust, context, and sense-making problem. This literature strongly supports your retrieval experiments, especially the comparison between metadata-only and schema-enhanced artifacts. citeturn29view2turn29view3turn28view3turn28view4turn28view5turn29view1

**Evidence-constrained LLMs and abstention.** The useful LLM literature here is not generic table QA or end-to-end metadata generation. It is the narrower literature on attribution, quote support, evidence-backed revision, self-knowledge, and reject options. These works justify an LLM layer that labels semantics only when backed by deterministic evidence and otherwise emits `unknown`. citeturn16search3turn18search0turn18search1turn18search2turn15search3

**Evaluation, documentation, and reproducibility.** Datasheets for Datasets, ML reproducibility programs, and ACM badging policies provide a mature model for documenting corpus construction, intended use, limitations, and reproducible artifacts. This category directly supports your benchmark freeze, gold-reference publication, paper-ready tables, and artifact appendix. citeturn27view3turn34search3turn34search7turn34search2turn34search10

## Annotated bibliography

_Data readiness, scientific AI, and profiling._

**Lawrence, Neil D. _Data Readiness Levels_.** Year: 2017. Identifier: arXiv:1705.02245. This position paper proposes a common language for data preparedness and emphasizes that missing values, storage problems, privacy, security, and curation effort are often underestimated in ML projects. Its main value for your paper is conceptual positioning: schema extraction can be cast as moving data from poorly understood raw form toward operational readiness. Direct relevance: strong for framing, weak for method details. Citation role: **core**. citeturn21view2

**Hiniduma, Byna, and Bez. _Data Readiness for AI: A 360-Degree Survey_.** Year: 2025. Identifier: DOI 10.1145/3722214; arXiv:2404.05779. This survey synthesizes readiness metrics across structured and unstructured data, covering quality, accessibility, fairness, privacy, and governance. It is useful because it shows that “AI-ready data” is already a multi-dimensional concept, but also because it leaves open the lower-level problem of file-grounded schema extraction. Direct relevance: strong for theoretical positioning. Citation role: **core**. citeturn23search0turn23search7

**Hiniduma et al. _AI Data Readiness Inspector (AIDRIN) for Quantitative Assessment of Data Readiness for AI_.** Year: 2024. Identifier: DOI 10.1145/3676288.3676296; arXiv:2406.19256. AIDRIN operationalizes readiness through a broad metrics stack including completeness, outliers, duplicates, feature importance, fairness, privacy, and FAIR compliance. It is directly useful as evidence that the field wants quantitative readiness tooling, but your project is more fine-grained and file-structural than AIDRIN’s metric dashboard orientation. Direct relevance: strong for positioning, moderate for feature ideas. Citation role: **supporting**. citeturn24search0turn24search2

**Hiniduma et al. _AIDRIN 2.0: A Framework to Assess Data Readiness for AI_.** Year: 2025. Identifier: arXiv:2505.18213. This short paper updates AIDRIN with user-interface improvements and privacy-preserving federated-learning integration. It is relevant mainly as evidence that readiness tooling is actively evolving, but methodologically it is still much broader and shallower than field-level schema extraction with gold references. Direct relevance: moderate. Citation role: **background**. citeturn21view0

**Brewer et al. _Data Readiness for Scientific AI at Scale_.** Year: 2025. Identifier: arXiv:2507.23018. This paper adapts readiness to scientific foundation-model pipelines and proposes a matrix of readiness levels and data-processing stages in HPC contexts. It is particularly helpful for positioning your work in scientific data systems, especially where preprocessing, sharding, reproducibility, and scalable workflows matter. Direct relevance: strong for scientific-AI framing. Citation role: **core**. citeturn22view0

**Wang and Strong. _Beyond Accuracy: What Data Quality Means to Data Consumers_.** Year: 1996. Identifier: DOI 10.1080/07421222.1996.11518099. This classic paper broadened data quality beyond simple correctness to a multi-dimensional, user-centered concept. It remains useful for justifying completeness, consistency, interpretability, and usability metrics in your deterministic profiles. Direct relevance: strong as background for quality dimensions. Citation role: **supporting**. citeturn9search0

**Abedjan et al. _Profiling Relational Data: A Survey_.** Year: 2015. Identifier: survey article; accessible author PDF. This survey remains one of the clearest taxonomies of profiling tasks, spanning single-column statistics, value distributions, patterns, domain classification, multi-column analysis, and dependency discovery. It maps almost one-to-one onto the deterministic profiling features you already list. Direct relevance: extremely high for implementation. Citation role: **core**. citeturn28view0

**Schelter et al. _Automating Large-Scale Data Quality Verification_.** Year: 2018. Identifier: DOI 10.14778/3229863.3229867. This paper turns profiling and constraints into scalable “unit tests for data,” including anomaly detection over quality-metric time series. It is especially relevant for turning your profiling outputs into reusable validation artifacts rather than one-off descriptive summaries. Direct relevance: high for profiling and validation. Citation role: **supporting**. citeturn28view1turn35view1

**Breck et al. _Data Validation for Machine Learning_.** Year: 2019. Identifier: MLSys 2019 paper. TensorFlow Data Validation defines a feature-level schema with constraints relevant to ML and shows how data validation can be integrated into production pipelines. The important lesson for your project is not the ML stack itself, but the idea that deterministic feature/schema checks should be first-class artifacts, not post hoc commentary. Direct relevance: high for schema-plus-constraints design. Citation role: **supporting**. citeturn28view2

_FAIR, provenance, metadata, and scientific standards._

**Wilkinson et al. _The FAIR Guiding Principles for scientific data management and stewardship_.** Year: 2016. Identifier: DOI 10.1038/sdata.2016.18. FAIR is the canonical high-level statement of findability, accessibility, interoperability, and reusability for scientific data. For your paper, FAIR is a framing standard: schema extraction improves machine-actionable metadata, but FAIR alone does not tell you how to recover field-grounded schema from files. Direct relevance: high for positioning. Citation role: **core**. citeturn27view0

**Wilkinson et al. _A design framework and exemplar metrics for FAIRness_.** Year: 2018. Identifier: DOI 10.1038/sdata.2018.118. This follow-on paper makes FAIR more measurable by proposing concrete FAIRness indicators. It is useful for arguing that your frozen benchmark artifacts and exported metadata should be auditable and testable, not only aspirationally FAIR. Direct relevance: moderate to high. Citation role: **supporting**. citeturn34search0turn34search4

**W3C. _PROV-DM: The PROV Data Model_.** Year: 2013. Identifier: W3C Recommendation. PROV-DM defines provenance in terms of entities, activities, and agents, explicitly connecting provenance to assessments of quality, reliability, and trustworthiness. It provides the cleanest existing standard to serialize your field-level evidence, derivations, and merge history. Direct relevance: extremely high for provenance design. Citation role: **core**. citeturn27view2

**Cheney, Chiticariu, and Tan. _Provenance in Databases: Why, How, and Where_.** Year: 2009. Identifier: survey article. This survey summarizes database provenance formalisms for explaining where output came from, why it appeared, and how it was produced. It is highly relevant because your schema claims are not just labels; they are outputs that should be explainable in terms of source evidence and derivation steps. Direct relevance: high for evidence semantics. Citation role: **core**. citeturn12search0turn12search2

**DataCite Metadata Working Group. _DataCite Metadata Schema 4.6_.** Year: 2024. Identifier: DOI 10.14454/mzv1-5b55 documentation; DOI 10.14454/csba-e454 schema. DataCite is a mature operational metadata schema for research outputs and explicitly recommends machine-recognizable codes when required metadata are unknown. That is directly useful for your `unknown` state and for exporting extracted schema into repository-friendly metadata bundles. Direct relevance: high for metadata packaging and unknown handling. Citation role: **core**. citeturn25view0turn25view1

**W3C. _Data Catalog Vocabulary (DCAT) Version 3_.** Year: 2024. Identifier: W3C Recommendation. DCAT is the standard RDF vocabulary for catalogs, datasets, and distributions on the web. It matters because your output artifacts can be published as discoverable catalog records, and because DCAT gives a bridge from extracted schema artifacts to dataset-search systems. Direct relevance: moderate to high. Citation role: **supporting**. citeturn1search5turn26view0

**RO-Crate Community. _RO-Crate Metadata Specification 1.1_.** Year: 2023. Identifier: DOI 10.5281/zenodo.7867028. RO-Crate packages research objects, data entities, contextual entities, and provenance in JSON-LD. It is a strong fit for publishing benchmark bundles, gold references, and reproducibility artifacts around your extraction pipeline. Direct relevance: high for artifact packaging. Citation role: **supporting**. citeturn25view4

**MLCommons. _Croissant Format Specification_.** Year: current official specification. Identifier: official specification. Croissant targets standardized ML dataset metadata with an explicit emphasis on discoverability, portability, reproducibility, and responsible AI. It is especially relevant if your schema-enhanced artifacts are meant to feed dataset search and model-training pipelines. Direct relevance: moderate to high. Citation role: **supporting**. citeturn25view3

**Frictionless Data. _Table Schema_.** Year: 2021 update to v1 specification. Identifier: official specification. Table Schema is a lightweight JSON schema for tabular data with fields, types, constraints, missing values, primary keys, and foreign keys. It is probably the most directly reusable standard for your CSV-facing deterministic outputs. Direct relevance: high for exchange format design. Citation role: **core**. citeturn25view2

**The HDF Group. _HDF5 documentation and file-format specification_.** Year: living documentation/specification. Identifier: official specification and user guide. HDF5 is explicitly self-describing and attaches metadata to datasets and groups through attributes describing intended usage and nature. That makes it central to your HDF5 path, especially because your extractor can recover reliable structural claims before any semantic interpretation. Direct relevance: extremely high for format-specific extraction. Citation role: **core**. citeturn20search0turn20search2turn20search4turn20search6

**CF Conventions Community. _NetCDF Climate and Forecast Metadata Conventions_.** Year: living standard. Identifier: official conventions document. CF standardizes `standard_name`, canonical-unit expectations, modifiers, and related variable semantics for scientific arrays. It is one of the best domain standards to exploit for high-fidelity variable naming, units, and uncertainty semantics in scientific data. Direct relevance: high for scientific semantics and unit checking. Citation role: **core**. citeturn26view3

**Regenstrief / HL7. _Unified Code for Units of Measure (UCUM)_.** Year: living specification. Identifier: official specification. UCUM is explicitly designed for unambiguous electronic communication of quantities and unit expressions. It gives you a standards-backed path to normalize extracted units rather than relying on ad hoc string cleaning. Direct relevance: high for unit normalization. Citation role: **core**. citeturn26view4

_Schema extraction, semantic typing, and matching._

**Rahm and Bernstein. _A Survey of Approaches to Automatic Schema Matching_.** Year: 2001. Identifier: DOI 10.1007/s007780100057. This remains a foundational taxonomy of schema matching methods, distinguishing schema- versus instance-level and element- versus structure-level matchers. Its relevance is strategic: your work is adjacent to schema matching, but solves an earlier problem by recovering schema from raw files before alignment starts. Direct relevance: high for paper positioning. Citation role: **core**. citeturn31view4

**Adelfio and Samet. _Schema Extraction for Tabular Data on the Web_.** Year: 2013. Identifier: PVLDB 6(6). This paper tackles schema recovery from messy tabular sources that lack explicit machine-readable structure. It is one of the closest established antecedents to your deterministic-first extraction layer, even though your domain is scientific files rather than web tables. Direct relevance: extremely high. Citation role: **core**. citeturn32view4turn19search12

**Venetis et al. _Recovering Semantics of Tables on the Web_.** Year: 2011. Identifier: PVLDB paper. This work is valuable because it does not merely attach semantics; it reasons about whether there is sufficient evidence for labels and uses recovered semantics for table search. That evidence-centered stance is very close to your semantic layer, though your project should be stricter about abstaining and preserving deterministic structure. Direct relevance: high. Citation role: **core**. citeturn32view3

**Hulsebos et al. _Sherlock: A Deep Learning Approach to Semantic Data Type Detection_.** Year: 2019. Identifier: arXiv:1905.10688; KDD 2019. Sherlock shows that semantic column typing can outperform dictionaries and regexes when it uses rich statistical, character, and embedding features. For your project, it is a strong supporting citation for semantic-type labeling, but also a foil: semantic typing should annotate deterministic fields, not invent them. Direct relevance: high. Citation role: **supporting**. citeturn33view0

**Zhang et al. _Sato: Contextual Semantic Type Detection in Tables_.** Year: 2020. Identifier: DOI 10.14778/3407790.3407793. Sato improves semantic type detection by incorporating both global table intent and local neighboring-column context. It is especially helpful for your semantic layer because it shows why multi-column context matters, while still leaving room for your stronger evidence and provenance constraints. Direct relevance: high. Citation role: **supporting**. citeturn32view1

_Dataset search and retrieval._

**Brickley, Burgess, and Noy. _Google Dataset Search: Building a search engine for datasets in an open Web ecosystem_.** Year: 2019. Identifier: DOI 10.1145/3308558.3313685. This paper is foundational for modern dataset search: it relies on semantically enhanced metadata published by dataset providers, then aggregates and reconciles those records for search. It is directly relevant to your retrieval experiments because it exemplifies the metadata-centric baseline that your schema-enhanced artifacts should be tested against. Direct relevance: extremely high. Citation role: **core**. citeturn29view2turn7search0

**Chapman et al. _Dataset Search: a Survey_.** Year: 2020. Identifier: DOI 10.1007/s00778-019-00564-x. This survey frames dataset search as a distinct field and highlights benchmark scarcity, metadata limitations, and the need to connect user tasks with dataset and metadata properties. It is probably the single most useful survey for motivating your retrieval section and benchmarking choices. Direct relevance: extremely high. Citation role: **core**. citeturn29view3turn14search16

**Fernandez et al. _AURUM: A Data Discovery System_.** Year: 2018. Identifier: ICDE system paper. Aurum builds an enterprise knowledge graph over datasets and uses schema- and content-level relationships, including PK/FK candidates, to support discovery. It is highly relevant to your relationship-candidate discovery and to schema-aware retrieval. Direct relevance: high. Citation role: **supporting**. citeturn28view3

**Bogatu et al. _Dataset Discovery in Data Lakes_.** Year: 2020. Identifier: DOI 10.1109/ICDE48307.2020.00067. This paper uses schema- and instance-based fine-grained features to index datasets in data lakes and shows that combining evidence types improves relatedness estimation. It is one of the best direct precedents for using structure-aware artifacts to improve dataset retrieval. Direct relevance: extremely high. Citation role: **core**. citeturn28view4turn8search13

**Castelo et al. _Auctus: A Dataset Search Engine for Data Discovery and Augmentation_.** Year: 2021. Identifier: DOI 10.14778/3476311.3476346. Auctus targets structured-data discovery and augmentation, including richer queries over dataset properties. It helps position your retrieval work as part of a broader movement from keyword-only discovery toward structure-aware search. Direct relevance: high. Citation role: **supporting**. citeturn28view5turn35view4

**Gregory et al. _Understanding data search as a socio-technical practice_.** Year: 2020. Identifier: DOI 10.1177/0165551519837182. This paper is essential cautionary reading for benchmark design: dataset search is shaped by metadata, repositories, social trust, access routes, documentation, and researcher context, not only by query-to-record matching. It is the strongest literature-based reason not to overclaim retrieval robustness from planted or overly synthetic tasks. Direct relevance: extremely high. Citation role: **core**. citeturn29view1

_Evidence-constrained LLMs, abstention, and reproducibility._

**Gao et al. _RARR: Researching and Revising What Language Models Say, Using Language Models_.** Year: 2023. Identifier: ACL 2023; arXiv:2210.08726. RARR retrieves evidence, attributes model output, and revises unsupported claims. It is highly relevant to your semantic layer because it offers a concrete pattern for post hoc evidence grounding without letting the model redefine the underlying structure. Direct relevance: extremely high. Citation role: **core**. citeturn16search3turn16search0

**Menick et al. _Teaching language models to support answers with verified quotes_.** Year: 2022. Identifier: arXiv:2203.11147. This work trains models to answer factual questions with explicit quoted support and shows that abstaining when uncertain improves quality. Its main importance for your project is methodological: semantic annotations should be support-bearing and rejective, not merely fluent. Direct relevance: high. Citation role: **core**. citeturn18search0

**Bohnet et al. _Attributed Question Answering: Evaluation and Modeling for Attributed Large Language Models_.** Year: 2022. Identifier: arXiv:2212.08037. This paper builds a reproducible attribution benchmark and focuses directly on how to measure evidence-supported generation. It is useful for your evaluation design because it separates answer quality from attribution quality, a distinction that also matters for semantic labeling. Direct relevance: high. Citation role: **supporting**. citeturn18search1turn18search5

**Kadavath et al. _Language Models (Mostly) Know What They Know_.** Year: 2022. Identifier: arXiv:2207.05221. This paper studies whether language models can estimate the correctness of their own answers and introduces useful confidence notions like `P(True)` and `P(IK)`. For your purposes, it supports confidence scoring and uncertainty-aware abstention in the semantic layer. Direct relevance: moderate to high. Citation role: **supporting**. citeturn18search2

**Geifman and El-Yaniv. _Selective Classification for Deep Neural Networks_.** Year: 2017. Identifier: arXiv:1705.08500. This paper formalizes the reject option: a model can trade coverage for lower risk. That is exactly the logic behind leaving unsupported semantic claims as `unknown`. Direct relevance: high. Citation role: **core**. citeturn15search3

**Pineau et al. _Improving Reproducibility in Machine Learning Research_.** Year: 2021. Identifier: JMLR 22; arXiv:2003.12206. This paper documents the NeurIPS reproducibility program, including checklists, code policies, and reproducibility challenges. It is directly relevant to your benchmark freeze, reporting protocol, and public artifact expectations. Direct relevance: high. Citation role: **core**. citeturn34search3turn34search7

**ACM. _Artifact Review and Badging_.** Year: 2020 current policy version. Identifier: ACM policy / training pages. ACM’s policy states plainly that an experimental result is not fully established unless it can be independently reproduced, and it defines artifact categories and badges. That gives you a mature external reference for frozen artifacts, public bundles, and reproducible tables. Direct relevance: high. Citation role: **core**. citeturn34search2turn34search6

**Gebru et al. _Datasheets for Datasets_.** Year: 2021 CACM version; arXiv:1803.09010. Datasheets propose structured documentation of motivation, composition, collection, recommended uses, and limitations for datasets. This is directly applicable to your pilot corpus, gold references, and retrieval benchmark artifacts, which should be documented as carefully as the extraction method itself. Direct relevance: high. Citation role: **supporting**. citeturn27view3turn11search11

## Mapping table

| Project component | Relevant established work | What to borrow | What to avoid | How to implement or cite |
|---|---|---|---|---|
| Deterministic extraction | HDF5 docs/spec, CF conventions, Table Schema, Adelfio and Samet. citeturn20search0turn20search2turn20search4turn20search6turn26view3turn25view2turn32view4 | File-grounded parsing, explicit field descriptors, path-aware structure, standards-backed units and variable names. | Treating semantic guesses as structural facts; flattening away hierarchy too early; inferring fields that do not occur in the file. | Emit a canonical structural record per field: file path, header/attribute/path evidence, physical type, logical type, shape/cardinality, parser confidence, and unresolved ambiguities. Cite Adelfio for extraction lineage and HDF5/CF/Table Schema for format semantics. |
| Field-level evidence and provenance | PROV-DM, database provenance, dataset/feature/attribute provenance applications. citeturn27view2turn12search0turn11search21turn12search21 | Entity/activity/agent modeling, why/where explanations, provenance of provenance, attribute-level lineage. | Dataset-level provenance only, with no way to justify individual field claims. | Model each schema claim as a provenance-linked assertion backed by specific headers, byte ranges, HDF5 attributes, variable names, value samples, or parser rules; retain merge history as provenance-of-provenance. |
| Uncertainty and `unknown` handling | DataCite unknown-value guidance, selective classification, model self-knowledge, attributed QA with abstention. citeturn25view0turn15search3turn18search2turn18search0 | An explicit reject option; machine-recognizable unknown codes; confidence separated from coverage. | Forced completion, silent defaulting, or converting every low-confidence guess into a “best effort” field value. | Add a small state machine per claim: `supported`, `derived`, `conflicted`, `unknown`. Require reason codes such as “no evidence,” “weak evidence,” “conflicting evidence,” or “unsupported by deterministic layer.” |
| Gold schema evaluation | Semantic typing and STI literature, schema-matching literature, attribution-benchmark practice. citeturn33view0turn32view1turn32view2turn31view4turn18search1 | Field-level gold labels, micro/macro precision/recall/F1, per-type breakdowns, adjudicated reference sets, separate scoring of label correctness and evidence correctness. | Dataset-level pass/fail metrics, underspecified adjudication, or only reporting aggregate accuracy. | Freeze field-level gold references with explicit decision rules. Report exact-match metrics for structure first, then semantic-label metrics, then evidence/provenance completeness metrics. |
| Semantic LLM annotation | RARR, verified-quote QA, attributed QA, confidence-aware LMs. citeturn16search3turn18search0turn18search1turn18search2 | Evidence-bounded prompts, attribution, self-checking, abstention when support is absent. | End-to-end free-form extraction, chain-of-thought-style invented rationales, or model-generated fields that bypass deterministic parsing. | Give the model only deterministic evidence packets and ask for bounded tasks: semantic type, unit normalization suggestion, uncertainty note, and short rationale tied to evidence IDs. |
| Semantic merge safety rails | PROV-DM, RARR, attributed QA, DataCite unknowns. citeturn27view2turn16search3turn18search1turn25view0 | Separation between canonical structure and optional semantic overlay; auditable merge decisions. | Overwriting deterministic fields with unsupported LLM output; collapsing uncertainty during merge. | Store two layers: canonical deterministic schema and a semantic overlay. Merge only when semantic annotations reference existing fields and satisfy evidence thresholds; otherwise retain parallel competing hypotheses or `unknown`. |
| Retrieval benchmark | Google Dataset Search, dataset-search survey, Aurum, D3L, Auctus, socio-technical dataset-search work. citeturn29view2turn29view3turn28view3turn28view4turn28view5turn29view1 | Multi-view retrieval baselines, schema/value-aware discovery signals, benchmark modesty, user-context sensitivity. | Overclaiming from planted queries, ignoring trust and documentation, or declaring “real-world robustness” from a narrow benchmark. | Keep your four-way comparison, but publish query construction rules, relevance judgments, and benchmark limits. Include at least some user-inspired or repository-inspired tasks in addition to planted ones. |
| Deterministic profiling | Profiling survey, Deequ, TFDV, Aurum, D3L. citeturn28view0turn28view1turn28view2turn28view3turn28view4 | Missingness, uniqueness, pattern mining, dependency discovery, anomaly tracking, relation-candidate discovery. | Turning every profiled regularity into a hard rule without domain review. | Keep missingness and identifier quality; add pattern summaries, domain cardinality, candidate keys, inclusion-dependency evidence, and historical metric deltas where repeated datasets exist. |
| Paper-ready reproducibility | Datasheets, FAIR metrics, RO-Crate, Croissant, Pineau, ACM artifact review. citeturn27view3turn34search0turn25view4turn25view3turn34search3turn34search2 | Structured dataset documentation, measurable metadata quality, versioned artifact bundles, exact experimental manifests. | Mutable gold references, undocumented benchmark revisions, or prompt-only experimental descriptions. | Publish the corpus manifest, schema outputs, gold references, retrieval qrels, evaluation scripts, and table-generation scripts as versioned artifacts; include a short artifact appendix aligned with ACM/NeurIPS-style reproducibility expectations. |

## Method recommendations

**Easy documentation changes.** First, formalize a claim model in the paper and artifact docs: every schema claim should explicitly record evidence, provenance, confidence, and one of `supported`, `derived`, `conflicted`, or `unknown`. That single design choice aligns the project with PROV, DataCite’s unknown-value guidance, and abstention literature, while making your deterministic-first philosophy legible to reviewers. Second, document the pilot corpus and gold references with a benchmark card or datasheet-style appendix: selection criteria, adjudication process, revision policy, exclusions, and known blind spots. Third, describe your retrieval benchmark as a **bounded offline evaluation**, not a complete model of real-world dataset search, and say so in the paper. citeturn27view2turn25view0turn27view3turn29view1turn29view3

**Medium implementation changes.** The most valuable technical upgrade would be a standards-backed **unit and semantic normalization layer**: parse HDF5 attributes, exploit CF `standard_name` and canonical units where present, and normalize unit expressions through UCUM before any LLM sees them. A second worthwhile change is to serialize field-level provenance in a PROV-like internal form, even if you do not export full PROV-O yet. A third is to calibrate the semantic layer with a real abstention policy: evaluate confidence thresholds, report coverage-versus-risk curves, and default to `unknown` when support is weak. A fourth is to separate evaluation into three scores: structural extraction, semantic labeling, and evidence adequacy. citeturn20search2turn26view3turn26view4turn27view2turn15search3turn18search2turn18search1

**Larger future-work changes.** Over time, the project would be significantly strengthened by a **relationship graph** over fields and files using profiling signals such as candidate keys, inclusion dependencies, shared identifiers, and value-overlap sketches, closer in spirit to data-discovery systems like Aurum and D3L. Another strong direction is a human adjudication interface that lets reviewers inspect evidence packets and approve, reject, or refine semantic overlays. A third is to package benchmark artifacts as RO-Crate or Croissant records so that the extracted schema is not just evaluated internally but also published in a discovery-friendly form. Finally, if the corpus broadens, domain profiles for climate, imaging, genomics, or materials science would let the deterministic layer exploit file-format conventions without collapsing into domain-specific hardcoding. citeturn28view3turn28view4turn25view4turn25view3turn22view0

## Paper positioning

A strong related-work paragraph could read like this:

Existing work gives several pieces of the problem, but not the full stack addressed here. Data-readiness frameworks define maturity, quality, governance, and AI suitability for datasets, while FAIR and scientific metadata standards define how data and metadata should be published and reused. However, these literatures generally operate above the level of file-grounded field recovery: they articulate what good scientific data stewardship should look like, but not how to deterministically recover a high-fidelity schema from heterogeneous scientific files with field-level evidence, uncertainty, and gold-standard evaluation. citeturn21view2turn23search0turn22view0turn27view0turn25view0turn1search5

A second paragraph could read like this:

Closer to our method are literatures on schema extraction, semantic typing, and schema matching. Prior work has shown how to recover structure from messy tables, annotate columns with semantic types, and match existing schemas using name-, structure-, and instance-based signals. We borrow heavily from these traditions, especially their emphasis on evidence families and confidence, but differ in two ways: first, we target scientific data files whose structure must be recovered from the file itself rather than assumed to be already available; second, we separate deterministic structural recovery from semantic interpretation, treating semantic labels as evidence-constrained overlays rather than as ground truth for schema. citeturn32view4turn32view3turn33view0turn32view1turn31view4

A third paragraph could read like this:

Our retrieval setting is informed by dataset-search and data-discovery systems, which show that metadata, schema, and instance signals can all affect discoverability. We therefore evaluate schema-enhanced retrieval directly, comparing metadata-only and README-only baselines with deterministic and semantically enriched schema artifacts. At the same time, unlike recent LLM-first approaches to data management, our use of language models is narrow: we draw on attribution and abstention work to constrain LLMs to semantic annotation over deterministic evidence, and we require unsupported claims to remain unknown. citeturn29view2turn29view3turn28view3turn28view4turn28view5turn16search3turn18search0turn18search1turn15search3

A concise novelty statement could be:

**This project contributes a deterministic-first framework for scientific-file schema extraction that combines file-grounded structural recovery, field-level provenance and uncertainty, evidence-constrained semantic annotation, and retrieval-aware evaluation against frozen field-level gold references.** It sits between high-level data-readiness frameworks and downstream dataset-search systems by turning heterogeneous scientific files into auditable, schema-enhanced discovery artifacts rather than relying on end-to-end model guesses. citeturn23search0turn27view2turn29view3turn16search3turn34search3

A literature-grounded limitations paragraph could read like this:

This framework also has clear limitations. First, scientific tabular and array data are highly heterogeneous, and even strong extraction and semantic-typing systems do not eliminate the difficulty of interpreting tables or variables in the wild; domain-specific conventions still matter. Second, provenance and attribution improve auditability but do not by themselves guarantee truth, and evidence-backed semantic labels may still be incomplete or conservative. Third, offline retrieval benchmarks remain only partial proxies for real dataset search, which is shaped by trust, domain context, access conditions, and documentation quality. These limitations argue for explicit `unknown` handling, conservative semantic merge policies, and restrained claims about benchmark generalization. citeturn32view2turn27view2turn18search0turn29view1turn29view3

## Search appendix

**Databases and sources searched.** I relied on web search across arXiv, ACM Digital Library, PVLDB/VLDB, W3C, Nature/Scientific Data, PubMed, Google Research, DataCite documentation, schema.org and Google Search Central, MLCommons, the HDF Group, CF Conventions, UCUM, and author-hosted or official mirror PDFs where needed.

**Exact search queries used.**

```text
"data readiness levels" Lawrence 2017 arXiv
"AIDRIN 2.0" "A Framework to Assess Data Readiness for AI"
"Data Readiness for Scientific AI at Scale"
"Profiling relational data: a survey"
site:w3.org PROV-DM W3C recommendation 2013
site:w3.org DCAT version 3 W3C Recommendation 2024
site:schema.org Dataset schema.org
DataCite Metadata Schema 4.6 official
RO-Crate specification official 1.1 2023
MLCommons Croissant metadata format official 1.0
Frictionless Table Schema specification official
CF Conventions official latest
HDF5 official documentation metadata groups datasets attributes
UCUM specification official
"A Survey of Approaches to Automatic Schema Matching" pdf
Sherlock semantic data type detection KDD 2019
"Recovering semantics of tables on the web" VLDB 2011
"Google Dataset Search: Building a search engine for datasets in an open web ecosystem"
"dataset search" survey Chapman Simperl Koesten 2020
"Aurum" data discovery system VLDB 2018
"Dataset Discovery in Data Lakes" Bogatu 2020 D3L
"Auctus: A Dataset Search Engine for Data Discovery and Augmentation"
"Understanding data search as a socio-technical practice"
RARR researching and revising what language models say arXiv
"Teaching language models to support answers with verified quotes" arxiv
"Attributed Question Answering" attributed large language models
"Language Models (Mostly) Know What They Know"
"Selective Classification for Deep Neural Networks"
"Improving Reproducibility in Machine Learning Research" JMLR 2021
"Artifact Review and Badging" ACM official
```

**Rejected or weakly relevant clusters.**

- **Classical RNN training papers from the seed list.** I do not recommend using _Professor Forcing_ or _A Learning Algorithm for Continually Running Fully Recurrent Neural Networks_ in the main related-work section. At best they support a weak analogy about train/deployment mismatch or online temporal behavior, but they are not direct prior art for schema extraction, provenance, metadata standards, or dataset retrieval. fileciteturn0file0

- **End-to-end LLM table understanding and generic “LLMs for everything” data-management papers.** Much of this literature is too generation-centric for a deterministic-first paper and would blur the core contribution.

- **Commercial blog posts and tooling pages without a stable scholarly or standards basis.** These were excluded unless they pointed to official docs that I then used directly.

- **Highly domain-specific scientific metadata papers** that were useful as examples but too narrow to anchor a general-purpose schema-extraction paper.

**Accessible only as abstracts, index pages, or alternate mirrors.**

- Some publisher pages were only accessible through abstract/index pages in this session, especially for older ACM/Taylor & Francis content.
- A few papers were easiest to access through arXiv records, author-hosted PDFs, or metadata pages rather than the publisher landing page.
- The local seed PDFs listed in your brief were not directly accessible as local attachments in this chat environment, so I relied on public versions or public metadata where available. fileciteturn0file0

**Open questions and limitations in the search itself.**

- I found strong general and standards-based support for your architecture, but less mature literature specifically on **scientific-file schema extraction with field-level gold references**. That appears to be part of the gap your paper can credibly claim.
- I found strong support for **evidence-constrained annotation** and **abstention**, but much of that literature comes from attributed QA rather than file-schema studies. In the paper, I would present that borrow as principled adaptation rather than direct precedent.
- I found many discovery systems and dataset-search papers, but the literature still confirms a shortage of **standardized, ecologically realistic dataset-retrieval benchmarks**, which strengthens your reproducibility story while also arguing for restraint in claims. citeturn29view3turn29view1turn34search3