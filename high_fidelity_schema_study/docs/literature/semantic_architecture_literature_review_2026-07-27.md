# Semantic architecture literature review

Date: 2026-07-27  
Purpose: publication positioning and claim support for the semantic-architecture
and NDP-50 studies

## Research position

The project sits at the intersection of four literatures:

1. semantic annotation of tables and dataset metadata;
2. evidence-attributed language generation;
3. selective prediction and abstention;
4. controlled component ablation and ML system technical debt.

No single neighboring task is equivalent to the project. Column type annotation
(CTA) predicts a semantic type for a column. Column property annotation (CPA)
predicts a relationship between columns, normally against a supplied
vocabulary. Dataset-description generation produces human-readable summaries.
The present system instead begins with heterogeneous scientific files, preserves
parser authority over physical structure, and evaluates optional semantic claims
through evidence, abstention, and deterministic verification.

## Source-by-source synthesis

### Table and column annotation

**Suhara et al. (2022), Doduo.** Doduo jointly predicts column types and column
relations from whole-table context using a pretrained transformer and
multi-task learning. It establishes that intra-table context and joint task
structure are strong learned baselines for CTA/CPA. It is relevant to the
applicable relational-table subset, but its supervised label spaces and
table-only inputs do not make it a full-file schema-extraction baseline.

**Feuer et al. (2024), ArcheType.** ArcheType decomposes LLM-based CTA into
context sampling, prompt serialization, querying, and label remapping. Its
ablation results directly motivate freezing row sampling, serialization, prompt
wording, and label remapping rather than treating “use an LLM” as one
well-defined intervention. Its domain-shift results also motivate reporting
vocabulary and domain limitations. CTA remains narrower than the NDP-50
physical/logical/semantic claim space.

**Korini and Bizer (2025), CPA with LLMs.** This study evaluates zero-shot
prompt variants, demonstrations, similarity-based example selection,
fine-tuning, and multiple model families for column property annotation.
It directly supports varying prompt wording; one- and five-shot demonstrations
selected randomly or by embedding similarity; model and fine-tuning
comparisons; an explicit candidate vocabulary; counting OOV responses as
errors; and Micro-F1 under class imbalance. The paper always supplies the first
five table rows, filling missing cells from later rows, but it does not compare
row-sampling policies or report macro- and per-label F1. NDP-50 adapts the
directly supported dimensions as bounded sensitivities and independently adds
row-sampling ablations plus macro/per-label reporting as project design
choices. The original effect sizes are not priors for NDP because the data,
property vocabulary, models, and applicability conditions differ.

**Zhang et al. (2026), AutoDDG.** AutoDDG combines deterministic dataset
summaries, semantic enrichment, and language generation to produce
search-oriented descriptions, evaluated through retrieval and intrinsic text
quality. It is adjacent to the project’s retrieval motivation and illustrates a
profiler-to-LLM pipeline. Description quality is not schema-claim correctness,
so AutoDDG is background and a possible downstream consumer, not a direct
primary baseline. The 2025 arXiv version is now superseded for citation purposes
by the 2026 *Proceedings of the ACM on Management of Data* article.

### Evidence attribution and abstention

**Menick et al. (2022), GopherCite.** GopherCite supports answers with quoted
evidence and uses abstention to trade coverage for answer quality. It motivates
claim-level evidence and explicit abstention. It also shows why a citation is
not sufficient for truth: support quality and source validity remain separate
questions. NDP-50 therefore checks evidence identity, allowed purpose, field
relevance, and contradiction without calling verification a semantic oracle.

**Gao et al. (2023), RARR.** RARR motivates revising model output against
retrieved evidence while preserving auditable attribution. The relevant
principle is evidence-backed correction; NDP-50 differs by replaying the same
raw model response into deterministic verification so that generation and
verification are separable.

**Geifman and El-Yaniv (2017), selective classification.** Selective
classification formalizes the trade-off between predictive coverage and risk.
This supports treating `unknown` and abstention as first-class outcomes rather
than forcing every slot to receive a label.

**Traub et al. (2024), selective-classification evaluation.** Traub et al.
identify flaws in common multi-threshold metrics and propose AUGRC as an
interpretable alternative. This is a caution against using AURC as an
unqualified scalar ranking. The present study keeps exact accepted-claim rate
as primary, reports achieved coverage and tie rules for AURC, and plans AUGRC
only as a frozen descriptive sensitivity.

### Experimental validity and annotation

**Sainz et al. (2023), benchmark contamination.** The paper argues that
unmeasured benchmark exposure can overstate LLM performance. It supports an
explicit contamination limitation and a prohibition on claiming that a sealed
evaluation split is necessarily absent from model pretraining. It does not, by
itself, imply that development data are scientifically unusable; NDP-50 excludes
development data from confirmatory inference through its own prospective
protocol.

**Berzak et al. (2016), annotation anchoring.** The work demonstrates that
annotation procedures can affect agreement through anchoring. It motivates
prediction-blind independent submissions and freezing both submissions before
revealing disagreements. Because the task is syntactic annotation, it is used
as general methodological evidence rather than schema-specific validation.

**Cohen (1960) and Krippendorff (2018), agreement measurement.** Cohen's kappa
provides a chance-adjusted nominal agreement statistic for the two-annotator
decision slots. Krippendorff's framework motivates an optional alpha statistic
when units, distance, and missing-data handling are explicitly defined. Exact
agreement and marginal support remain necessary because chance-adjusted
coefficients can be undefined or hard to interpret under degenerate marginals.
Neither statistic establishes label validity or replaces reconciliation.

### Cost and technical debt

**Sculley et al. (2015), hidden technical debt.** The paper frames ML systems as
incurring maintenance costs through data dependencies, configuration,
entanglement, and system-level anti-patterns. The current project derives
“Model Capability Debt” as a narrower operational construct: orchestration or
compensation introduced for a model limitation that may no longer be necessary
when the model/runtime changes. This is a project hypothesis to be tested by
controlled deletion or substitution, not a new universal law.

**Khan (2025), prompting inversion.** On GSM8K, a restrictive “Sculpting”
prompt improved over simpler chain-of-thought prompting for GPT-4o but
underperformed it for GPT-5. This is a narrow, single-task preprint result, not
evidence about schema extraction and not construct validation. It motivates
the weaker, project-relevant proposition that compensating prompts and
orchestration should be retested when model capability changes.

**Chen et al. (2023), FrugalGPT.** FrugalGPT treats model choice, cascades, and
prompt adaptation as accuracy--cost trade-offs. It supports reporting resource
use alongside quality and considering model-family sensitivities. It is not a
direct architecture baseline because NDP-50 does not learn or optimize a model
cascade.

## Baseline map

| Comparator | Scientific role | Current NDP-50 status |
| --- | --- | --- |
| Deterministic-only | Non-LLM reference and product boundary | Co-primary anchor |
| Dataset-level zero-shot | Measures added semantic augmentation | Co-primary arm |
| Byte-identical response plus deterministic verification | Isolates deterministic verification from generation | Co-primary arm |
| One/five-shot development demonstrations | Prompt/example sensitivity | Descriptive |
| Doduo | Supervised whole-table CTA/CPA comparator | Literature comparator; executable extension requires label mapping |
| ArcheType | LLM CTA and sampling/serialization comparator | Literature and design-factor comparator |
| Korini--Bizer CPA | Direct CPA design precedent | Adapted bounded sub-study |
| Evidence-free single call | Parametric-memory diagnostic | Not active; pre-freeze decision gate |
| Heuristic name/value system | Lower-complexity semantic comparator | Optional non-confirmatory diagnostic |
| Second model family | Model-specificity sensitivity | Not active; preregistration required |
| Human consensus | Reference label process | Gold standard, not an upper bound |

## Claim-support boundaries

- Sculley et al. supports the technical-debt analogy, not the empirical claim
  that a specific component is obsolete.
- Khan provides a capability-relative prompt-effect example on GSM8K, not a
  general prompting law, schema-extraction result, or validation of Model
  Capability Debt.
- Menick et al. supports attribution and abstention, not the claim that a valid
  citation proves truth.
- Sainz et al. supports contamination caution, not a blanket prohibition on
  development sets.
- Berzak et al. supports anchoring controls generally, not schema-specific
  agreement thresholds.
- Korini and Bizer supports CPA design dimensions, not expected NDP effect
  sizes.
- Doduo and ArcheType support table-annotation comparisons, not claims about
  heterogeneous file parsing.
- FrugalGPT supports cost-aware evaluation, not the superiority of a particular
  NDP architecture.

## Primary-source claim-entailment audit

Audit date: 2026-07-27. A verified title, DOI, or venue establishes
bibliographic identity only. The `Directly supports` column records the maximum
claim scope permitted by the inspected primary source; the `Does not support`
column is an explicit prohibition against plausible but unentailed
extrapolation.

| Work | Primary locator inspected | Directly supports | Does not support | NDP-50 disposition |
| --- | --- | --- | --- | --- |
| Adelfio and Samet (2013) | PVLDB PDF, `https://www.vldb.org/pvldb/vol6/p421-adelfio.pdf` | Schema extraction from heterogeneous Web tables and recovery of tabular structure | The distinct Venetis et al. paper title *Recovering the Semantics of Tables on the Web*; general scientific-file semantics | Corrected citation identity; deterministic schema-recovery background only |
| Feuer et al. (2024), ArcheType | PVLDB PDF and DOI `10.14778/3665844.3665857` | CTA pipeline factors including sampling, serialization, querying, and label remapping | CPA performance or heterogeneous-file parsing accuracy | Row-sampling and serialization design-factor precedent; literature comparator |
| Korini and Bizer (2025) | ESWC author/conference PDF and DOI `10.1007/978-3-031-78952-6_6` | CPA prompt variants; random/similarity demonstrations; one/five-shot settings; fine-tuning/model comparisons; fixed candidate vocabularies; OOV-as-error; Micro-F1 | A comparison of row-sampling policies; macro-F1 or per-label-F1 reporting; expected NDP effect sizes | Direct CPA precedent, with unsupported factors labelled as independent NDP design choices |
| Traub et al. (2024) | NeurIPS proceedings page/PDF and DOI `10.52202/079017-0076` | Shortcomings of common selective-classification aggregate metrics and the proposed AUGRC metric | That AURC is invalid in every setting; that AUGRC is already an implemented NDP endpoint | AURC caveat; AUGRC remains an inactive, separately frozen descriptive sensitivity |
| Castelo et al. (2021), Auctus | PVLDB PDF and DOI `10.14778/3476311.3476346` | Content-aware dataset discovery, join/union-style augmentation queries, and profiler-backed indexing | Schema-extraction correctness or semantic-label accuracy | Verified discovery/augmentation background; no primary NDP arm |
| Zhang et al. (2026), AutoDDG | PACM Management of Data DOI `10.1145/3786626` and official author repository | A profiler-to-LLM dataset-description pipeline evaluated for description/retrieval objectives | Exact schema-claim correctness or a heterogeneous-file extraction baseline | Adjacent background and possible downstream consumer |
| Menick et al. (2022), GopherCite | arXiv `2203.11147` | Evidence attribution and abstention for supported answers | That a citation alone proves truth or field-level entailment | Supports claim/evidence traceability and abstention, not oracle language |
| Sainz et al. (2023) | ACL Anthology DOI `10.18653/v1/2023.findings-emnlp.722` | The need to measure and disclose benchmark contamination | Proof that NDP test records were or were not in model pretraining; a ban on development data | Explicit unresolved contamination limitation |
| Berzak et al. (2016) | ACL Anthology DOI `10.18653/v1/D16-1239` | Annotation anchoring can alter agreement in a syntactic task | Schema-specific agreement thresholds or proof that blinding guarantees validity | General motivation for prediction-blind independent submissions |
| Chen et al. (2023), FrugalGPT | arXiv `2305.05176` | Joint quality/cost reasoning for model selection and cascades | Superiority of an NDP architecture or a direct non-cascade baseline | Cost-reporting background only |
| Khan (2025), Prompting Inversion | arXiv `2510.22251` and DOI `10.48550/arXiv.2510.22251` | On GSM8K, the tested restrictive prompt helped GPT-4o relative to standard CoT but underperformed standard CoT on GPT-5; prompt value can be model-relative in that setting | A general law of model capability; schema-extraction behavior; validation of Model Capability Debt; evidence that any NDP component is obsolete | Narrow motivation for re-testing compensatory prompting after model changes |

## Verified bibliographic identifiers

- D. Sculley et al. “Hidden Technical Debt in Machine Learning Systems.”
  NeurIPS 2015.
- Yoshihiko Suhara et al. “Annotating Columns with Pre-trained Language
  Models.” SIGMOD 2022. DOI `10.1145/3514221.3517906`.
- Benjamin Feuer et al. “ArcheType: A Novel Framework for Open-Source Column
  Type Annotation using Large Language Models.” PVLDB 17(9), 2024. DOI
  `10.14778/3665844.3665857`.
- Keti Korini and Christian Bizer. “Column Property Annotation Using Large
  Language Models.” *The Semantic Web: ESWC 2024 Satellite Events*, LNCS 15344,
  pages 61--70, formally published 2025. DOI
  `10.1007/978-3-031-78952-6_6`.
- Jacob Menick et al. “Teaching Language Models to Support Answers with
  Verified Quotes.” arXiv `2203.11147`, 2022.
- Jeremias Traub et al. “Overcoming Common Flaws in the Evaluation of Selective
  Classification Systems.” *Advances in Neural Information Processing Systems*
  37:2323--2347, 2024. DOI `10.52202/079017-0076`; arXiv `2407.01032`.
- Oscar Sainz et al. “NLP Evaluation in Trouble: On the Need to Measure LLM
  Data Contamination for Each Benchmark.” Findings of EMNLP 2023. DOI
  `10.18653/v1/2023.findings-emnlp.722`.
- Yevgeni Berzak et al. “Anchoring and Agreement in Syntactic Annotations.”
  EMNLP 2016. DOI `10.18653/v1/D16-1239`.
- Jacob Cohen. “A Coefficient of Agreement for Nominal Scales.”
  *Educational and Psychological Measurement* 20(1):37--46, 1960. DOI
  `10.1177/001316446002000104`.
- Klaus Krippendorff. *Content Analysis: An Introduction to Its Methodology*.
  Fourth edition. SAGE Publications, 2018.
- Lingjiao Chen, Matei Zaharia, and James Zou. “FrugalGPT: How to Use Large
  Language Models While Reducing Cost and Improving Performance.” arXiv
  `2305.05176`, 2023.
- Sonia Castelo et al. “Auctus: A Dataset Search Engine for Data Discovery and
  Augmentation.” *Proceedings of the VLDB Endowment* 14(12):2791--2794, 2021.
  DOI `10.14778/3476311.3476346`.
- Haoxiang Zhang et al. “AutoDDG: Automated Dataset Description Generation
  using Large Language Models.” *Proceedings of the ACM on Management of Data*
  4(1), Article 12, pages 1--27, 2026. DOI `10.1145/3786626`; arXiv
  `2502.01050`.
