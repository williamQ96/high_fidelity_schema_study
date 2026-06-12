# Deep Research Prompt: High-Fidelity Schema Extraction Versus Leading Data-Agent Architectures

Research cutoff date: `2026-06-10`

## Role

Act as a senior research scientist and data-systems architect. Produce a rigorous, source-verifiable comparison between the current project and the latest leading data-agent, scientific-agent, metadata, schema-inference, and data-understanding architectures.

The report must distinguish:

1. systems that infer trustworthy schema from raw heterogeneous files;
2. systems that answer questions over data that is already structured, cataloged, governed, or modeled;
3. agent infrastructure patterns that could improve the project without weakening its deterministic-first guarantees.

Do not treat all three as the same problem.

Write the final report primarily in Chinese, while preserving precise English names for systems, papers, standards, metrics, and architectural components.

## Non-Negotiable Project Goal

The target system is:

```text
Input file or file collection
  - raw/opaque binary
  - time-series data
  - HDF5 / NetCDF-like hierarchical scientific data
  - CSV / tabular data
  - future formats such as Parquet, Arrow, JSON, XML, FITS, GRIB,
    Zarr, scientific instrument exports, and multimodal containers
        ->
High-fidelity schema extraction process
        ->
High-confidence, evidence-grounded, auditable schema
```

The output must recover or safely abstain on:

- physical structure and field existence;
- physical types, shapes, nesting, encoding, nullability, and missingness;
- logical roles such as identifier, time axis, coordinate, measurement, label, and relationship;
- semantic types, units, descriptions, and domain meaning when evidence permits;
- file-level and field-level provenance;
- claim confidence, uncertainty, conflict, and `unknown` states;
- relationships across fields, groups, files, or dataset families when defensible.

The system must prefer `unknown` or explicit abstention over unsupported invention. It must not silently turn an LLM guess into canonical schema.

## Current Project Architecture

The project is titled:

`A Deterministic-First Framework for High-Fidelity Schema Extraction from Scientific Data Files`

Its current architecture is:

```text
Raw File
  -> format detection
  -> deterministic format-specific extractor
  -> field-level structural evidence
  -> deterministic profiling and normalization
  -> evidence-constrained semantic annotation
  -> conservative conflict-aware merge
  -> layered schema + provenance + uncertainty
  -> field-level evaluation and retrieval artifacts
```

Current principles:

- deterministic extraction owns canonical physical structure;
- semantic augmentation may enrich existing claims but may not invent unsupported fields;
- every accepted claim should cite evidence;
- stronger evidence overrides weaker evidence;
- conflicts remain visible;
- `unknown` is a valid and preferred output when evidence is insufficient;
- evaluation separates correctness, completeness, evidence adequacy, uncertainty, and retrieval utility.

Current implemented components:

- deterministic CSV, HDF5, and time-series extractors;
- raw-binary high-fidelity abstention behavior when no structural metadata exists;
- layered physical, logical, and semantic schemas;
- field-level source evidence, confidence, uncertainty reasons, and claim states;
- deterministic profiling for missingness, identifier quality, and relationship candidates;
- unit normalization with UCUM-oriented status;
- evidence-constrained semantic annotation and conservative merge-back;
- PROV-like provenance export;
- gold schemas, benchmark freeze, qrels, generated reports, tests, and a GUI workbench;
- scratch local extraction that does not mutate frozen benchmark artifacts.

Current frozen-slice results to use as context, not as broad claims:

- internal pilot datasets: `9`;
- external retrieval candidates: `16`;
- deterministic physical completeness: `1.0000`;
- deterministic physical accuracy: `0.9815`;
- deterministic logical accuracy: `0.9444`;
- deterministic semantic accuracy: `1.0000`;
- unit accuracy: `0.8889`;
- time-axis accuracy: `0.6667`, the clearest current deterministic gap;
- deterministic fields with source evidence: `53/53`;
- accepted semantic merges with support: `3/3`;
- unsupported accepted semantic merges: `0`;
- semantic merge improved logical accuracy on `2/3` reviewed internal datasets;
- planted-query schema-enhanced retrieval Recall@1: `1.0000`, which must not be presented as broad retrieval robustness.

Important current files to map recommendations against:

- `README.md`
- `docs/target_schema.md`
- `docs/schema_claim_model.md`
- `docs/evaluation_plan.md`
- `docs/academic_rigor_audit.md`
- `docs/benchmark_card_2026-05-15.md`
- `docs/paper_result_tables_2026-05-15.md`
- `docs/final_convergence_report.md`
- `extractors/base.py`
- `extractors/csv_extractor.py`
- `extractors/hdf5_extractor.py`
- `extractors/timeseries_profiler.py`
- `deterministic_profile.py`
- `semantic_layer.py`
- `semantic_annotate.py`
- `unit_normalization.py`
- `build_provenance_manifest.py`
- `evaluate_internal_baseline.py`
- `evaluate_semantic_merge.py`
- `gui_demo/`

## Central Research Question

Compared with the latest OpenAI data-agent architecture, Anthropic agent architecture, and other leading data-agent or data-understanding systems, what should this project:

- preserve;
- adopt;
- adapt;
- reject;
- implement next;

to become a substantially stronger and more extensible system for:

```text
heterogeneous raw files -> high-fidelity extraction -> high-confidence schema
```

The report must determine whether the best future architecture is:

- a deterministic pipeline with a bounded semantic agent;
- an agent orchestrating deterministic extractor tools;
- a hybrid workflow/agent system with verification gates;
- a multi-agent system with specialized format, evidence, semantic, and validation roles;
- or another architecture supported by evidence.

Do not assume that greater agent autonomy is better.

## Required Systems And Architecture Families

Verify the latest available primary sources as of `2026-06-10`. Use exact publication or documentation dates. At minimum, investigate the following.

### 1. OpenAI

Analyze OpenAI's in-house data agent, including:

- layered context: table usage, human annotations, code/Codex enrichment, institutional knowledge, memory, and runtime context;
- schema and table discovery;
- the claim that important meaning lives in pipeline code, not only schema or query history;
- closed-loop exploration, validation, self-correction, and memory;
- MCP and multiple user entrypoints;
- evaluation using expected SQL, dataframes/results, and reasoning;
- trust, permissions, security, and learned context;
- the lesson to guide the goal without over-prescribing the path.

Also analyze relevant OpenAI agent primitives:

- Responses API and Agents SDK;
- tools, handoffs, guardrails, tracing, and evals;
- Structured Outputs;
- code execution and MCP/connectors where relevant.

Primary seed source:

- OpenAI, `Inside OpenAI's in-house data agent`, published `2026-01-29`:
  `https://openai.com/index/inside-our-in-house-data-agent/`

### 2. Anthropic

Do not invent a single branded "Anthropic Data Agent" if none exists. Instead, analyze Anthropic's relevant architecture patterns:

- simple composable workflows versus autonomous agents;
- just-in-time context retrieval and progressive disclosure;
- Claude Code / Agent SDK as a general data-analysis harness;
- MCP and agent-friendly deterministic tools;
- tool search, programmatic tool calling, and tool-use examples;
- sandboxed code execution;
- context management, compaction, memory, and long-running tasks;
- multi-agent research patterns where they are genuinely useful;
- agent evaluations using multiple trials, graders, traces, and outcomes;
- human approvals, permission boundaries, and containment.

Give special attention to the scientific-agent lesson that deterministic retrieval/execution layers can sharply improve reliability over agents navigating heterogeneous scientific infrastructure unaided.

Primary seed sources:

- Anthropic, `Effective context engineering for AI agents`;
- Anthropic, `Writing effective tools for agents - with agents`;
- Anthropic, `Introducing advanced tool use on the Claude Developer Platform`;
- Anthropic, `Demystifying evals for AI agents`;
- Anthropic, `Building Effective AI Agents`;
- Anthropic, `Paving the way for agents in biology`, published `2026-06-08`.

### 3. Other Leading Data-Agent Systems

Compare at least these systems using current official documentation and, where available, research papers:

- Databricks Genie / Genie Agent Mode / Genie Code:
  specialized knowledge search, parallel thinking, multi-LLM routing, semantic context, permissions, plans, approvals, execution, and evaluation;
- Google BigQuery data agents, Data Engineering Agent, Data Science Agent, Conversational Analytics API, ADK, MCP, and A2A;
- Microsoft Fabric Data Agent:
  OneLake sources, semantic models, ontologies, instructions, permissions, and conversational Q&A;
- Snowflake Cortex Agents and Cortex Analyst:
  governed execution, semantic views, tool routing, traces, evaluation, and structured/unstructured data access;
- DataHub Agent Context Kit or equivalent metadata/context graph:
  lineage, ownership, glossary, quality, governance, trust signals, and agent context;
- leading open-source orchestration approaches where directly relevant, such as LangGraph, LlamaIndex workflows/agents, Semantic Kernel, or Haystack.

For every system, explicitly state whether it:

- extracts schema from raw heterogeneous files;
- assumes schema/catalog/semantic models already exist;
- improves downstream analysis only;
- provides reusable architectural ideas for upstream schema extraction.

### 4. Non-Agent Baselines And Standards

Compare the project with mature non-agent systems and standards because they may be more appropriate for the core extraction path:

- Apache Tika and format-identification/content-extraction systems;
- Apache Arrow, Parquet metadata, DuckDB, and robust tabular sniffing;
- HDF5, NetCDF, CF Conventions, Zarr, FITS, GRIB, and domain-specific metadata conventions;
- Frictionless Data / Table Schema;
- JSON Schema, XML Schema, Avro, and Protobuf descriptor-driven schema;
- UCUM, QUDT, or other unit and quantity vocabularies;
- W3C PROV, RO-Crate, Croissant, DCAT, schema.org Dataset, DataCite;
- data catalogs, lineage systems, data profiling, schema matching, semantic typing, ontology alignment, and data contracts.

Identify where deterministic standards support should be expanded before adding more agent behavior.

### 5. Relevant Research And Benchmarks

Include recent, credible work on:

- raw-file schema inference and schema discovery;
- semantic type detection and column understanding;
- scientific metadata extraction;
- data profiling, relationship discovery, and data-lake discovery;
- uncertainty calibration and selective prediction/abstention;
- agentic data analysis and data engineering;
- agent/tool evaluation and trace evaluation;
- benchmark contamination, ambiguous gold labels, and weak qrels.

At minimum, assess whether and how the following are relevant:

- DABstep;
- Spider 2.0 and Spider2-DBT;
- DSEval / `Benchmarking Data Science Agents`;
- DataSciBench;
- newer Data Agent Benchmark work available by the cutoff date;
- benchmarks for schema inference, semantic typing, table understanding, or scientific data extraction.

Do not use text-to-SQL or data-analysis benchmarks as substitutes for schema-extraction evaluation. Explain what they measure and what they do not.

## Required Comparison Framework

Build a comparison matrix with one row per system or architecture and these columns:

| Dimension | Required Analysis |
| --- | --- |
| Primary problem | Raw schema extraction, catalog discovery, NL-to-SQL, analytics, data engineering, or general agent orchestration |
| Input assumptions | Raw bytes/files, parsed tables, warehouse schemas, semantic models, metadata catalogs, codebases, or documents |
| Supported data forms | Binary, CSV, HDF5, time series, hierarchical data, tables, documents, multimodal, streams |
| Deterministic core | What is guaranteed by parsers, APIs, validators, or execution engines |
| Agent role | Planning, tool selection, extraction, semantic enrichment, validation, synthesis, or memory |
| Context architecture | Upfront context, RAG, just-in-time retrieval, context graph, code enrichment, memory |
| Evidence model | Field-level evidence, citations, lineage, traces, query results, or none |
| Schema/semantic layer | How types, entities, metrics, relationships, units, and business/domain meaning are represented |
| Validation loop | Parsing validation, schema validation, code execution, result checking, self-correction, human review |
| Abstention/conflict | Whether unknowns, unsupported claims, and conflicts remain explicit |
| Provenance/audit | Claim provenance, action traces, lineage, versioning, reproducibility |
| Security/governance | Permissions, sandboxing, data boundaries, prompt injection, approval gates |
| Evaluation | Task success, field accuracy, execution accuracy, evidence adequacy, multi-trial reliability, cost, latency |
| Extensibility | How new file formats, tools, conventions, and domains are added |
| Key strength | Most important transferable capability |
| Key limitation | Why it does not directly solve this project's goal |

## Required Gap Analysis

Evaluate the current project against the strongest observed patterns. At minimum, investigate these potential gaps without assuming they are all worth implementing:

1. **Format routing and capability discovery**
   - Should extractor selection become registry-based, plugin-based, MIME/magic-aware, or agent-assisted?
   - How should unsupported formats fail safely?

2. **Progressive extraction**
   - Should the system use cheap inspection first, then selectively deepen extraction?
   - How should it handle very large files without loading them fully?

3. **Agent-orchestrated deterministic tools**
   - Could an agent select and sequence trusted extractor/profiler/validator tools while deterministic outputs remain canonical?
   - Which decisions must remain fixed workflows?

4. **Code and sidecar enrichment**
   - Following OpenAI's "meaning lives in code" lesson, should the system inspect producer code, notebooks, README files, data dictionaries, pipeline definitions, or sidecars?
   - How should this weaker contextual evidence be ranked against file-grounded evidence?

5. **Context graph**
   - Should field claims, files, evidence, provenance, relationships, standards mappings, and human decisions become a queryable graph?
   - Would this improve cross-file schema alignment and future agent use?

6. **Tool and extractor interface design**
   - Should extractors expose typed capabilities, cost estimates, safety properties, supported evidence types, and validation contracts?
   - Should they be exposed through MCP, an internal tool registry, or both?

7. **Verification and self-correction**
   - Which closed-loop checks can be deterministic?
   - Examples: re-parse checks, shape consistency, round-trip validation, sample-vs-full-scan agreement, time-axis invariants, unit compatibility, and cross-parser consensus.

8. **Confidence calibration and abstention**
   - Is current confidence meaningful and calibrated?
   - Recommend selective-risk, coverage-versus-accuracy, expected calibration error, or conformal approaches where appropriate.

9. **Time-series and temporal semantics**
   - Propose concrete ways to fix the current time-axis gap.
   - Cover time zones, calendars, irregular sampling, event time versus ingestion time, intervals, missing periods, and multi-axis time.

10. **Binary and opaque formats**
    - Define a defensible ladder from file signature and container metadata through parser/plugin availability, sidecar evidence, reverse engineering, and final abstention.
    - State where automated inference becomes unsafe or scientifically invalid.

11. **New-format extensibility**
    - Design a practical path for Parquet, Arrow, JSON, XML, NetCDF/CF, Zarr, FITS, GRIB, Avro, Protobuf, and instrument-specific exports.

12. **Human review and memory**
    - Should adjudicated reviewer decisions become versioned reusable memory?
    - How can the system avoid turning stale or incorrect memory into false canonical truth?

13. **Evaluation maturity**
    - Add multi-trial agent evaluation only where nondeterminism exists.
    - Propose separate evaluation tracks for physical extraction, logical inference, semantic enrichment, evidence adequacy, provenance, abstention, robustness, scalability, and end-to-end utility.

14. **Operational concerns**
    - Cost, latency, parallelism, caching, reproducibility, sandboxing, permissions, prompt injection from malicious files, and dependency isolation.

## Required Future Architecture Proposal

Propose a concrete target architecture for the next major version. It must preserve deterministic-first behavior and clearly show trust boundaries.

At minimum, consider a structure similar to:

```text
File Intake + Safety Boundary
  -> Format Identification + Capability Registry
  -> Deterministic Extractor/Profiler Tools
  -> Validation and Cross-Check Layer
  -> Evidence + Claim + Provenance Store
  -> Optional Context Enrichment
       - sidecars
       - producer code
       - documentation
       - catalog/ontology/standards
  -> Bounded Semantic Agent
  -> Policy/Conflict/Abstention Gate
  -> Canonical High-Confidence Schema
  -> Export + Review + Evaluation
```

Determine:

- whether an agent should orchestrate the whole flow or only ambiguous branches;
- whether specialized subagents are justified;
- which components should be deterministic services, agent tools, validators, stores, or human-review surfaces;
- how claims move from `unknown` to `derived` to `supported`, or to `conflicted`;
- what evidence is required at every promotion boundary;
- how every final claim can be reproduced and audited.

Include:

1. a Mermaid architecture diagram;
2. component responsibilities;
3. trust boundaries;
4. data and claim flow;
5. failure and abstention paths;
6. plugin/tool interface proposal;
7. proposed canonical schema envelope;
8. proposed evaluation harness.

## Required Improvement Roadmap

Produce a prioritized roadmap with four horizons:

### Horizon A: Immediate, low-risk improvements

Changes achievable without changing the paper's frozen benchmark claims.

### Horizon B: Next experimental round

Changes that require new tests, datasets, or benchmark tracks.

### Horizon C: Extensible production architecture

Changes needed to support many formats, large files, plugins, security boundaries, and operational use.

### Horizon D: Research frontier

Ambitious work such as calibrated semantic agents, active human adjudication, cross-file conceptual schema induction, or agent-ready scientific data infrastructure.

For every recommendation, provide:

- problem addressed;
- source system or research idea;
- exact proposed change;
- likely repo modules affected;
- expected benefit;
- risk or tradeoff;
- implementation effort: small, medium, or large;
- validation experiment;
- success metric;
- whether it changes the project's core thesis.

Rank recommendations using:

```text
priority = expected fidelity gain
         + evidence/auditability gain
         + extensibility gain
         - implementation risk
         - scientific validity risk
```

## Required Output

Produce a report with these sections:

1. **Executive conclusion**
   - State the strongest architectural conclusion in no more than 12 bullets.
   - Explicitly answer whether this project should become a data agent.

2. **Problem-boundary clarification**
   - Explain the difference between raw-file schema extraction and downstream data agents.

3. **Current project assessment**
   - Identify present strengths, weaknesses, and non-negotiable guarantees.

4. **Latest-system briefs**
   - OpenAI, Anthropic, Databricks, Google, Microsoft, Snowflake, DataHub, relevant open-source systems, and non-agent baselines.

5. **Unified comparison matrix**
   - Use the required dimensions above.

6. **Transferable architecture patterns**
   - What should be adopted or adapted.

7. **Patterns to reject or constrain**
   - Especially architectures that weaken provenance, reproducibility, or abstention.

8. **Detailed gap analysis**
   - Cover all required gap-analysis topics.

9. **Proposed next-version architecture**
   - Diagram, components, trust boundaries, claim promotion, tools, and validation.

10. **Prioritized roadmap**
    - Horizons A-D with implementation mapping and experiments.

11. **Top 10 concrete repo changes**
    - Name likely files/modules and describe the smallest useful implementation.

12. **Evaluation redesign**
    - Datasets, benchmark tracks, metrics, graders, multi-trial policy, and failure analysis.

13. **Research risks and open questions**
    - Include scientific-validity and overclaim risks.

14. **Source appendix**
    - Exact URLs, titles, organizations/authors, publication/update dates, source type, and access date.

15. **Fact/Inference/Recommendation ledger**
    - Label major statements as:
      - `verified fact`;
      - `reasoned inference`;
      - `recommendation`;
      - `unknown / insufficient public evidence`.

## Source And Quality Rules

- The cutoff date is `2026-06-10`; verify that each claimed "latest" item is actually current by this date.
- Prefer official engineering posts, official documentation, standards bodies, peer-reviewed papers, and original benchmark repositories.
- Use vendor claims cautiously and label results that come only from internal or unpublished benchmarks.
- Do not infer undocumented internal architectures.
- Do not call Anthropic's collection of agent patterns a single data-agent product unless a primary source supports that wording.
- Separate raw-file extraction capability from downstream warehouse/catalog analytics.
- Separate deterministic guarantees from probabilistic model behavior.
- Separate final-output correctness from trajectory quality and evidence adequacy.
- Treat provenance as auditability, not proof of truth.
- Treat perfect planted-query retrieval as a bounded result, not general robustness.
- Treat current external semantic annotations as working annotations, not gold.
- Identify negative findings and architectural dead ends.
- Include exact dates when discussing recent systems.
- Every major recommendation must cite at least one source or clearly state that it is an original synthesis.

## Desired Research Thesis To Test

Do not simply accept this thesis; test it against evidence:

> The strongest future form of this project is not an autonomous LLM-first data agent. It is an agent-ready, deterministic-first schema system in which trusted format-specific tools establish physical truth, validators and provenance make claims auditable, and a bounded semantic agent uses just-in-time context to resolve only the ambiguities that deterministic evidence cannot safely settle.
