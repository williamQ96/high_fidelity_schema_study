# First-Principles Architecture and Model Capability Debt Audit

Date: 2026-07-13
Scope: current working tree, including uncommitted documentation and release-audit changes
Method: repository reconstruction, history inspection, code-path tracing, artifact inspection, negative-control execution, full regression run, and a targeted current-literature check

## Executive verdict

The project contains a sound core and an unsound research claim stack.

- **Preserve:** spec-backed parsing, format-aware adapters, structured partial/failure/abstention outcomes, separation of physical facts from optional semantic enrichment, and regression fixtures.
- **Do not preserve as architecture:** per-field LLM scheduling, manual prompt compaction and dataset-specific grouping, the legacy-schema -> unified-envelope -> agent-export transformation chain, phase-specific evaluator proliferation, or corpus-specific semantic dictionaries.
- **Do not treat the frozen metrics as scientific evidence of general performance:** the internal corpus and its gold are generated together, the retrieval task is planted and lexically engineered, most post-freeze scores are self-authored conformance tests, and two headline metrics mishandle non-applicable cases.
- **Change the research question:** from “does deterministic-first extraction work and improve retrieval?” to “what is the minimum hybrid architecture that maximizes verified claim coverage at a bounded selective risk, across blind real scientific files?”
- **Do not replace parsers with a stronger model:** a model cannot improve on authoritative byte- and metadata-level facts. Use a current model only for semantic hypotheses that require contextual reasoning, and keep its output outside canonical truth until a deterministic or human verifier accepts each property-level claim.
- **No multi-agent redesign is justified.** The current repository has no real multi-agent runtime; `agent_exports.py` creates read-only context bundles. One semantic reasoner call per dataset, with deterministic tools and an adaptive fallback only when measured limits require it, is the appropriate experimental target.

The current software is best described as three projects sharing one tree:

1. a deterministic extraction library;
2. a frozen artifact-paper package over a 9-dataset synthetic pilot and 16-file retrieval slice;
3. a post-freeze engineering workbench with seven registered formats and ten phase-specific experiment tracks.

Their objectives, schemas, and evidence levels are not aligned. A first-principles redesign should retain one runtime core, isolate the historical artifact, and build a new benchmark around blind external data.

## Evidence notation

- **Fact:** directly observed in code, artifacts, history, or an executed check.
- **Observation:** a synthesis of multiple facts without asserting intent.
- **Inference:** the most likely explanation, but not directly recorded.
- **Hypothesis:** a testable possibility requiring an experiment.
- **Recommendation:** a proposed action.

## Verification snapshot

- **Fact:** the working tree contains 570 tracked/untracked repository files visible to `rg`, including 122 Python files, 257 JSON files, and 89 Markdown files.
- **Fact:** the non-test Python surface is approximately 14,151 lines across 71 files; the test suite is approximately 2,809 lines across 51 test modules.
- **Fact:** `python -m pytest high_fidelity_schema_study/tests -q` passes: `183 passed` on Python 3.12.10.
- **Fact:** generic CLI extraction and the unified evaluation entry point execute successfully.
- **Fact:** the semantic grounding manifest contains 25 tasks, 378 fields, and 296 fields selected for semantic review. The default scheduling logic expands those tasks into 276 model calls. Actual historical call count, tokens, latency, retries, and cost are not recorded.
- **Fact:** a targeted negative control supplied a nonexistent evidence ID and confidence `0.0`; validation returned no errors and merge accepted logical type, semantic type, and unit. The responsible paths are `semantic_layer.py:163-188` and `semantic_layer.py:246-345`.
- **Fact:** 77 tracked data artifacts contain JSON-escaped `D:\\github\\...` paths, but `audit_release_readiness()` reports path hygiene as passing. `release_audit.py:13-16` does not match JSON-escaped separators, and `release_audit.py:119-129` does not audit the full generated artifact surface.

---

# Phase 1 — Reconstruction

## 1.1 Actual problem being solved

### Product problem

Given a local scientific data resource, recover as much structural schema as can be justified by a format parser, explicit metadata, bounded samples, and deterministic validators. Return explicit partial, conflict, unknown, abstention, and failure states rather than inventing fields.

### Research problem in the frozen paper

Measure whether a deterministic-first representation over CSV, HDF5, and time-series organization:

- matches human-authored field labels;
- carries evidence for its claims;
- can be safely enriched by an LLM;
- improves lexical retrieval over metadata-only and README-like text.

### Post-freeze engineering problem

Generalize the extraction substrate to NetCDF/CF, Zarr, Parquet/Arrow, JSON, and XML/XSD; add an orchestration registry, unified envelope, evaluation entry point, agent-ready export, GUI, and release audit.

**Observation:** the implementation has outgrown the paper question. The paper evaluates three families, while the current runtime registers seven formats and the project reports Phases 12-20 separately. This is not merely documentation lag; it is a split identity.

## 1.2 Intended users

- **Fact:** `gui_demo/README.md` calls the GUI reviewer-facing and says its main views inspect frozen artifacts.
- **Fact:** the CLI and Python APIs support developers running local extraction.
- **Fact:** `agent_exports.py` targets a future agent consumer but prohibits canonical mutation.
- **Inference:** the primary current user is an artifact reviewer or developer, not a production data steward or end-user searching a scientific repository.
- **Unknown:** no user study, product requirements, service-level objective, workload distribution, or production deployment target exists.

## 1.3 Inputs

Canonical extraction:

- a file or local directory-store path;
- optional format hint;
- optional resource kind;
- bounded sample limit, default 200.

Supported resources:

- CSV/TSV;
- HDF5;
- NetCDF classic and a conservative HDF5-backed NetCDF path;
- local Zarr v2 directory stores;
- Parquet/Arrow metadata;
- JSON/JSON Lines;
- XML/XSD;
- opaque or unsupported resources, which produce abstention.

Semantic experiment:

- deterministic schema JSON;
- field evidence;
- local README or repository-record text;
- task instructions;
- OpenAI-compatible model endpoint.

Research/evaluation:

- repository-generated pilot files and gold JSON;
- external Dryad/Zenodo files and source records;
- challenge-pack fixtures and expected manifests;
- planted retrieval queries and qrels.

## 1.4 Outputs

Runtime outputs:

1. `DatasetSchema` in `models.py`;
2. `ExtractionOutcome` in `extractors/base.py`;
3. a projected `unified_schema_envelope` in `unified_schema.py`;
4. an `agent_export` bundle in `agent_exports.py`;
5. GUI-specific response JSON in `gui_demo/server.py`.

Study outputs:

- derived schemas;
- semantic task, annotation, and merge artifacts;
- provenance manifests;
- retrieval documents, rankings, and reports;
- per-phase experiment reports;
- paper tables, figures, manuscript, presentations, and release-readiness artifacts.

**Observation:** one extraction can be represented in at least five overlapping shapes. This is accidental complexity created by additive development and compatibility preservation, not by the problem itself.

## 1.5 Core abstractions

- `EvidenceRecord`: tier, type, source, detail, confidence.
- `FieldSchema`: physical, logical, semantic, unit, statistics, evidence, one field-wide confidence.
- `DatasetSchema`: identity, fields, groups, metadata, notes.
- `ExtractionRequest`, `FormatSignal`, `FormatDecision`, `ExtractorCapability`, `ExtractionIssue`, `ExtractionOutcome`.
- semantic task/result dataclasses and merge policy.
- unified claim/evidence envelope.

**Observation:** the intended abstraction is a claim ledger, but the canonical implementation is still a flattened mutable field object. `unified_schema.py` reconstructs claims after the fact by projecting that object. This loses property-specific state and evidence.

## 1.6 End-to-end data and control flow

```text
path + optional hint
  -> resource-kind check
  -> magic/suffix/text/directory probes
  -> FormatDecision
  -> registry lookup
  -> format-specific extractor
  -> shared temporal and unit helpers
  -> mutable DatasetSchema
  -> ExtractionOutcome(success | partial | abstained | failed)
  -> optional UnifiedSchemaEnvelope projection
  -> optional AgentExport projection
  -> CLI or GUI rendering
```

Older semantic track:

```text
derived DatasetSchema + README/repository text
  -> stored grounding task
  -> compact target selection
  -> per-field or manually grouped model calls
  -> JSON salvage/normalization
  -> structural validation
  -> merge into a copy of DatasetSchema
  -> post-merge evaluation
  -> optional retrieval document
```

Research artifact flow:

```text
generated pilot raw files + generated gold
  -> deterministic schemas
  -> exact-label evaluator
  -> semantic tasks/results/merges
  -> retrieval document builder
  -> TF-IDF ranking over planted queries
  -> paper tables/figures/manuscript/GUI
```

## 1.7 Model interactions

- **Fact:** no model participates in the canonical extraction path.
- **Fact:** `semantic_annotate.py:300-366` calls `/chat/completions` with a strict JSON prompt, temperature 0.2, maximum 1,000 output tokens, and thinking disabled.
- **Fact:** `semantic_annotate.py:287-297` tries a non-schema request first and then a JSON-Schema request.
- **Fact:** `semantic_annotate.py:266-279` salvages a JSON object from malformed surrounding text.
- **Fact:** per-field behavior is effectively mandatory because `--per-field` is `store_true` with `default=True` (`semantic_annotate.py:447`); there is no CLI way to set it false.
- **Fact:** history records local `qwen3.5-9b` context failures, a `llama-3.3-70b-instruct` smoke path, and remote `qwen3.6-27b` timeouts. The runtime model debt is therefore specifically local/remote endpoint capability debt, not evidence that a GPT runtime required this architecture.

## 1.8 Tool interactions

- format libraries: `h5py`, SciPy NetCDF, NumPy, and PyArrow;
- standard-library CSV, JSON, XML, file, and HTTP primitives;
- `requests` for corpus acquisition;
- optional Zarr/Xarray cross-parser comparisons;
- Git subprocess calls in the release audit;
- local HTTP server and temporary files for GUI uploads;
- model HTTP endpoint for the older semantic track.

## 1.9 Validation mechanisms

- 183 unit/integration/regression tests;
- format challenge packs with expected manifests;
- internal exact-match evaluation against gold;
- semantic output shape validation and merge rules;
- evidence-presence counts;
- retrieval metrics;
- optional cross-parser comparison for Zarr;
- generated-artifact freeze checks;
- release-readiness checks.

**Observation:** there are many validators, but they validate different constructs and are reported together too easily. Most post-freeze evaluators are high-quality regression tests, not external accuracy studies.

## 1.10 Trust boundaries

1. **Untrusted files -> parser process.** The GUI parses uploaded scientific binaries in the server process. It limits upload bytes and binds to loopback, but has no CPU, memory, recursion, decompression, or parser-time sandbox.
2. **External metadata/README -> model prompt.** Repository text is data, but no prompt-injection treatment or quoted-span identity is defined.
3. **Model output -> canonical semantic merge.** This should be the strongest boundary; it is currently breached by unverified evidence strings and a missing minimum confidence for new claims.
4. **Generated artifacts -> paper/GUI.** Frozen JSON is treated as authoritative even when it contains local absolute paths or metrics with non-applicable-case bugs.
5. **Gold -> evaluation.** Gold and raw pilot data are generated in `create_pilot_corpus.py`; the audit checks internal consistency, not independent correctness.

## 1.11 Principal failure modes

- suffix or hint misrouting when no strong signature exists;
- sample bias and false universality from 200-row profiles;
- domain-specific name heuristics promoting weak semantics to canonical fields;
- field-wide confidence obscuring which property is uncertain;
- model context fragmentation and loss of cross-field relationships;
- endpoint timeout and partial progress;
- invalid or hallucinated evidence references accepted as support;
- semantic evidence lost or misattributed during envelope projection;
- stale artifacts and machine-specific paths;
- benchmark leakage from co-generated fixtures/gold and post-hoc heuristic tuning;
- planted retrieval queries, unequal baselines, and lexical term stuffing;
- misleading aggregate metrics for non-applicable unit/time-axis cases;
- untrusted-file resource exhaustion in the demo server.

## 1.12 Complexity classification

### A. Essential complexity

- format-specific parsing and library dependencies;
- distinguishing observed, declared, derived, inferred, unknown, conflicted, and failed claims;
- evidence/provenance identity;
- sample scope versus full-file scope;
- partial results and abstention;
- format-specific standards such as CF calendars, Arrow types, XSD declarations, and Zarr metadata;
- independent semantic verification.

### B. Accidental complexity

- five overlapping output representations;
- an unused `BaseExtractor` abstraction (`extractors/base.py:92-96`);
- legacy direct CLI paths for CSV/HDF5 that bypass the registry;
- nine tiny `build_phase*.py` wrappers;
- one evaluator module per phase plus a wrapper evaluator;
- duplicated generated task files and frozen aliases;
- paper, slides, GUI, and reports embedding the same metrics separately;
- compatibility constraints with a schema that was explicitly labeled a scaffold.

### C. Earlier-model capability complexity

- per-field request expansion;
- two-evidence truncation, 180-character local snippets, 700-character grounding snippets, and eight context fields (`semantic_annotate.py:150-263`);
- dataset-specific `GROUP_STRATEGIES` (`semantic_annotate.py:19-33`);
- JSON salvage and two-mode request retry;
- fixed 1,000-token output budget;
- manual manifest repair and repeated endpoint babysitting;
- semantic prompt rules that try to teach cross-field reasoning through hard-coded hints.

---

# Phase 2 — Assumption audit

| Assumption | Classification | Evidence and consequence |
| --- | --- | --- |
| Physical structure should come from a spec-backed parser, not a model. | Still valid | Authoritative types, paths, shapes, and attributes are byte-level facts. A stronger model does not improve this boundary. |
| Unsupported structure should abstain rather than guess. | Still valid | `extractors/registry.py:482-496` makes this explicit and should be preserved. |
| Model output is untrusted and must not create physical fields. | Still valid | Stronger instruction-following reduces error probability; it does not change the trust boundary. |
| Physical, logical, and semantic layers should be distinct. | Still valid, implementation should be tested | The concept is sound, but `FieldSchema` flattens all layers and `physical_structure.fields` contains the full mixed field object. |
| One field-wide confidence can represent physical, logical, semantic, and unit correctness. | Actively harmful | `models.py:15-32` has one confidence. A parser type can be certain while a semantic label is speculative. |
| A CSV header/path can establish a supported semantic type. | Actively harmful | `csv_extractor.py:116-181` and `hdf5_extractor.py:31-61` promote corpus-specific meanings. Names are evidence, not verification. |
| A fixed 200-row prefix is a sufficient profile. | Probably valid for a demo, should be tested | Sampling scope is exposed, but no random/stratified/adaptive policy or sample-sensitivity study exists. |
| Format hints and suffixes are reliable when magic is absent. | Probably valid, should be tested adversarially | `registry.py:329-346` applies precedence rather than calibrating all signals; misleading suffixes are under-tested. |
| Per-field LLM calls are required for reliable semantic output. | Historical workaround | History explicitly attributes the change to context limits and timeouts. Current default expands 25 tasks to 276 calls. |
| Only two field evidence records and eight context fields are enough. | Historical workaround | The constraint reduces prompt size but fragments evidence and cross-field context. |
| Two named datasets require manually authored semantic groups. | Historical workaround | `GROUP_STRATEGIES` encodes task identity into orchestration. |
| Free-form output should be attempted before JSON Schema. | No longer necessary for capable endpoints; test compatibility | The code intentionally doubles a failing request path. Current structured-output-capable models should use one strict contract. |
| JSON salvage remains necessary. | Probably no longer necessary, but retain behind telemetry until tested | Salvage can mask protocol violations and makes reproducibility harder. |
| Any non-empty supporting-evidence string proves support. | Actively harmful | The negative control accepted `DOES_NOT_EXIST` at confidence 0.0. |
| Confidence need only gate conflicting logical overrides. | Actively harmful | New semantic types and units can be accepted at confidence 0.0. Documentation says confidence must be high enough; code does not. |
| Generated pilot data and gold can be authored in the same script without biasing accuracy. | Actively harmful for research | `create_pilot_corpus.py` builds raw fixtures and gold together, while heuristics encode many exact field names. |
| A consistency audit is equivalent to human gold validation. | Actively harmful | `audit_gold_schemas.py` verifies shape and label consistency; all 50 gold fields have empty `gold_evidence` arrays. No second annotator or agreement exists. |
| Repository-generated challenge packs demonstrate extractor accuracy. | Valid as regression, harmful as generalization evidence | Expected manifests and fixtures are co-authored; near-perfect scores are appropriate tests but weak research evidence. |
| The retrieval systems isolate the effect of schema. | Actively harmful | `schema_enhanced_document` concatenates metadata + README-like text + schema, while baselines contain only one of the first two. |
| Repeating filename slice terms four times is legitimate schema evidence. | Actively harmful | `build_retrieval_artifacts.py:186-200` deliberately changes lexical term frequency and leaks query-target construction. |
| Planted single-positive queries can establish retrieval benefit. | Valid only as a smoke test | The repository states this limit, but the perfect score is still central in the abstract and figures. |
| Unit accuracy is zero when no unit is expected. | Actively harmful | `safe_ratio(0, 0)` returns 0. The only 0.0 dataset has zero expected unit claims, creating the headline 0.8889. |
| A dataset without a gold time axis counts as a correct time-axis prediction. | Actively harmful | `evaluate_internal_baseline.py:109-114` makes non-applicable datasets score 1.0. The 0.6667 aggregate is six N/A successes plus three time-series failures. |
| Evidence adequacy means a claim has at least one evidence record. | Probably valid as coverage, invalid as adequacy | Presence does not test entailment, relevance, source identity, or property-specific support. |
| Frozen artifacts should remain unchanged indefinitely. | Still valid for historical reproducibility, harmful as current architecture constraint | Preserve an archival release; do not force new runtime schemas and metrics to remain backward-compatible. |
| Human review is inherently required for semantic gold. | Still valid for benchmark truth | A stronger model can assist annotation, but it cannot independently validate its own outputs as gold. |
| Multi-agent decomposition is needed. | No longer necessary—and never implemented | There is no multi-agent runtime. Do not add one. |

---

# Phase 3 — Adversarial architecture critique

| Component | Decision | Why |
| --- | --- | --- |
| `ExtractionRequest`, structured issues/outcomes, and abstention | **KEEP** | These make failures observable and preserve the strongest safety property. |
| Format detection and capability registry | **KEEP BUT SIMPLIFY** | The registry is useful. Replace wrappers/manual parallel dictionaries with adapter objects; calibrate or explicitly order probes. |
| Seven format-specific parser adapters | **KEEP** | This is essential complexity. Refactor them to emit observations and explicit declarations, not mixed canonical semantics. |
| CSV/HDF5 name-based semantic dictionaries | **REPLACE** | `csv_extractor.py` now contains a 32-field GPU-training ontology and exact pilot mappings. This does not generalize and obscures evidence level. |
| Temporal semantics | **KEEP BUT SIMPLIFY** | The subsystem has clear functional separation. Replace ad hoc calendar/time logic with standards-backed libraries where possible and evaluate only applicable cases. |
| Unit normalization | **REFACTOR** | Keep deterministic normalization, but use a maintained UCUM/UDUNITS implementation and versioned vocabulary instead of a small dictionary. |
| `deterministic_profile.py` relationship candidates | **REFACTOR** | Identifier profiles are useful. Cross-dataset relationships based only on shared semantic labels must remain unverified candidates and need value-level validation. |
| `DatasetSchema` flattened field model | **REPLACE** | It cannot represent property-specific confidence, state, verification, evidence, scope, or competing claims. |
| Legacy outcome + unified envelope | **MERGE** | The envelope is a lossy projection that duplicates fields and invents claim state after extraction. Make one claim ledger canonical; provide a legacy view only at the boundary. |
| `agent_exports.py` | **MERGE** | It is a read-only view of the envelope, not an agent subsystem. Export the same ledger through a view function. |
| `BaseExtractor` | **DELETE** | No extractor subclasses it. It is a premature abstraction. |
| Direct `extract-csv` / `extract-hdf5` CLI commands | **DELETE after deprecation evidence** | They bypass the central registry and duplicate the generic command. Search found no internal caller requiring them. |
| Semantic task-bundle builder | **KEEP BUT SIMPLIFY** | Persisted reproducible inputs are valuable. Store immutable evidence IDs/spans and prompt hashes, not a full duplicated schema blob per task. |
| Per-field semantic runner and manual groups | **REPLACE** | This is the clearest model capability debt: 276 scheduled calls, fragmented context, dataset-specific routing, and no call telemetry. |
| Semantic validator and merge | **REFACTOR URGENTLY** | The functional boundary is essential, but current evidence and confidence checks do not enforce the documented contract. |
| Semantic normalization, validation, merge, and evaluation as separate scripts | **MERGE** | Preserve separate logical stages inside one typed run pipeline and one run manifest; remove fragile file-to-file choreography. |
| Internal pilot and gold | **KEEP AS EXAMPLES, DELETE AS PRIMARY BENCHMARK** | Useful teaching fixtures; invalid evidence for generalization because construction, gold, and heuristic development are coupled. |
| Phase 12-17 challenge packs | **KEEP AS REGRESSION TESTS** | They test declared behavior well. Rename them conformance suites and stop treating 1.0000 as external accuracy. |
| Phase-specific evaluators and build wrappers | **MERGE** | A declarative case schema and one evaluator can express common exact, set, status, and abstention checks. |
| Unified Phase 18 evaluator | **REFACTOR** | Good refusal to aggregate incomparable tracks, but it mostly wraps heterogeneous bespoke reports. |
| Retrieval document builder | **REPLACE** | It creates an unequal ablation and manually repeats query-correlated tokens. |
| TF-IDF retrieval evaluator | **KEEP AS A LOWER BASELINE** | A lexical baseline is useful, but not sufficient in 2026 and not valid with current document construction. |
| Provenance manifest | **REFACTOR** | Provenance is valuable; current path identity is machine-specific and semantic evidence is not preserved property-by-property. |
| GUI workbench | **KEEP BUT SIMPLIFY** | Useful reviewer surface. Render the canonical ledger and run parsers in a resource-limited subprocess. |
| Paper/table/figure generation | **KEEP AS ARCHIVAL BUILD** | Reproducibility is valuable. Move the frozen artifact under an explicit archive namespace. |
| Release audit | **REPLACE** | It reports false path-hygiene success and checks Git working-tree differences rather than frozen content hashes. |
| Product/research/docs in one flat package | **REFACTOR** | Split into runtime, benchmark, and archived artifact packages/directories with independent versioning. |

### Concrete context-fragmentation path

`compact_task_payload()` removes most whole-dataset context, truncates evidence, and sends at most eight resolved context fields. It then defaults to one call for every unresolved field, except two task-name-specific groups. This can amplify errors:

1. the parser makes a weak name-based label;
2. target selection decides whether the model may reconsider it;
3. compaction removes distant corroborating or conflicting fields;
4. independent calls produce locally plausible but globally inconsistent types;
5. aggregation is last-write-wins by field path;
6. merge accepts any non-empty evidence string;
7. the envelope later reuses original field evidence for the accepted semantic claim.

This is both model capability debt and an integrity defect.

---

# Phase 4 — Capability upgrade analysis

The opportunities below are hypotheses until the listed experiment succeeds. “Current model” means the actual target model/version deployed for the new study, not an assumed frontier model.

## 4.1 Whole-dataset semantic reasoning

**OLD APPROACH:** `semantic_annotate.py` selects unresolved fields and schedules up to one call per field, with two hard-coded grouping plans.

**NEW APPROACH:** one structured call receives all field observations, dataset metadata, evidence spans, and cross-field relationships. It emits zero or more property-level candidate claims, alternatives, counterevidence, and abstentions. Only measured over-limit cases use automatic graph-based partitions.

**BENEFIT:** 276 scheduled calls become approximately 25 dataset calls on the current task set; cross-field consistency, latency, cost, and maintainability should improve.

**RISK:** one failed or overlong call has a larger blast radius; attention may degrade on the 128-field case.

**VALIDATION:** compare old per-field, one-shot, and adaptive partitioning on all 25 tasks over at least three seeded runs. Measure valid-output rate, claim precision/recall, evidence-reference precision, cross-field contradiction rate, wall time, tokens, and calls. Do not remove the old scheduler until the new path is non-inferior on verified-claim precision and better on at least one efficiency measure.

## 4.2 Direct structured output

**OLD APPROACH:** request free JSON, salvage braces, then retry with JSON Schema.

**NEW APPROACH:** use one provider-supported strict schema request; fail closed if the endpoint cannot honor it. Keep salvage only as a separately measured compatibility adapter.

**BENEFIT:** fewer calls, clearer failures, stable telemetry, less hidden protocol drift.

**RISK:** local OpenAI-compatible endpoints may implement structured output incompletely.

**VALIDATION:** replay the 25 tasks against each supported endpoint; compare schema-valid response rate and retry count.

## 4.3 Replace corpus-tuned semantic mappings

**OLD APPROACH:** exact name maps and dataset-context predicates in `csv_extractor.py`/`hdf5_extractor.py` produce canonical semantic labels.

**NEW APPROACH:** parsers emit names, samples, explicit attributes, and weak deterministic candidate features. A model may propose semantic claims over the full context, while standards validators accept explicit CF/CSVW/codebook claims. Name-only claims remain `inferred_unverified`.

**BENEFIT:** less hard-coded domain logic and better generalization to unseen fields.

**RISK:** nondeterminism, model cost, and worse precision on easy memorized patterns.

**VALIDATION:** blind external split with four arms: explicit metadata only, current heuristics, current model, hybrid. Report selective precision versus coverage; retain deterministic maps only where they demonstrate stable out-of-domain value.

## 4.4 Repository-level schema and invariant reasoning

**OLD APPROACH:** claim state is reconstructed in `unified_schema.py` by walking arbitrary nested metadata and assigning field evidence wholesale to multiple properties.

**NEW APPROACH:** define one versioned property-level claim schema and generate adapters/tests from it. Use a strong model during development to audit mappings and invariants, but enforce them in deterministic code.

**BENEFIT:** one source of truth, fewer transformations, better debuggability.

**RISK:** migration can break historical consumers.

**VALIDATION:** shadow-emit old and new outputs for the full regression corpus; assert an explicit property-by-property compatibility matrix and manually review every intentional difference.

## 4.5 Tool-grounded standards reasoning

**OLD APPROACH:** small hard-coded semantic/unit mappings and partial CF logic.

**NEW APPROACH:** deterministic lookup against versioned CF standard names, CF 1.13 rules, UCUM/UDUNITS, CSVW, JSON Schema, and XSD. The model may choose search terms or explain a candidate but cannot fabricate a registry match.

**BENEFIT:** broader vocabulary, traceable versioning, fewer hand-maintained rules.

**RISK:** standards are format/domain-specific and version changes can alter behavior.

**VALIDATION:** conformance cases from official specifications plus external files; record vocabulary version in every claim.

The latest released CF standard is 1.13 and its standard-name vocabulary is independently versioned; the repository does not currently record a CF ruleset/version in each claim. See the [CF 1.13 specification](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.13/cf-conventions.html), [current CF standard names](https://cfconventions.org/Data/cf-standard-names/current/build/cf-standard-name-table.html), and the [W3C CSVW metadata recommendation](https://www.w3.org/TR/tabular-metadata/).

## 4.6 Evidence-aware self-critique in one call

**OLD APPROACH:** model output contains one answer, then deterministic merge checks a few conditions.

**NEW APPROACH:** require each proposed property to include evidence IDs, an entailment explanation, counterevidence IDs, alternatives, and an abstention reason. Deterministic code verifies IDs and precedence. Do not add a second “critic agent” unless an ablation proves value.

**BENEFIT:** richer failure observability without another orchestration layer.

**RISK:** model explanations can be persuasive but non-evidential; more output tokens.

**VALIDATION:** negative controls with nonexistent IDs, irrelevant real IDs, contradicted metadata, and prompt-injected README text. Evidence precision must be measured by humans or deterministic entailment rules where available.

## 4.7 Retrieval synthesis and ranking

**OLD APPROACH:** hand-built TF-IDF documents concatenate unequal evidence sources and repeat slice terms.

**NEW APPROACH:** use controlled fielded indexes and fair ablations: metadata+description; +physical observations; +verified logical/semantic claims. Compare BM25/TF-IDF, a current embedding baseline, and a reranker. A model may synthesize a query-independent dataset summary, but it must not see qrels.

**BENEFIT:** tests whether schema adds value rather than whether more query terms add value.

**RISK:** larger systems complicate attribution.

**VALIDATION:** blind user-authored queries, graded multi-relevance qrels, family-level splits, and significance intervals. Preserve TF-IDF as a lower baseline.

## 4.8 Cross-file reasoning

**OLD APPROACH:** `deterministic_profile.py` declares relationship candidates when two schemas share semantic labels.

**NEW APPROACH:** a current model can propose candidate entity/key/coordinate relationships using full schema context, but deterministic value overlap, units, cardinality, and referential checks must verify them.

**BENEFIT:** stronger discovery capability and fewer false semantic joins.

**RISK:** combinatorial cost and plausible false joins.

**VALIDATION:** benchmark known joins and hard same-name non-joins; measure precision at a fixed review budget.

## 4.9 Multimodal documentation

**OLD APPROACH:** only machine-readable files and text snippets are used.

**NEW APPROACH:** optional document ingestion can extract codebooks from scanned tables/plots/PDFs when a dataset actually supplies them.

**BENEFIT:** recovers evidence unavailable in plain text.

**RISK:** OCR and visual interpretation add a new untrusted layer and are irrelevant to most current inputs.

**VALIDATION:** a separate document-grounding benchmark. Do not add multimodality to the core architecture until such data exists.

---

# Model Capability Debt register

| Suspected debt | Original limitation | Does it still exist? | Simplest replacement | Required old-vs-new experiment |
| --- | --- | --- | --- | --- |
| Per-field calls | Local 9B context/output reliability and remote timeout blast radius | Probably reduced, not eliminated for 128-field tasks | One dataset call; adaptive partitions only after measured failure | 276-call scheduler vs ~25-call one-shot vs adaptive; precision, evidence, contradictions, cost, latency |
| Manual `GROUP_STRATEGIES` | Large named tasks timed out | No reason to assume task-name routing remains necessary | Generic field graph partition by shared dimensions/terms/evidence | Hold out the two named tasks and unseen large tasks; compare completeness and consistency |
| Two evidence records / 8 context fields / snippet truncation | Prompt budget | Likely reduced | Full compact observation graph with token-aware evidence selection | Vary context budget; plot claim precision/coverage and contradiction rate |
| Free JSON then JSON Schema | Weak structured-output support | Endpoint-dependent | Strict schema first, fail closed | Endpoint matrix; valid response rate and calls |
| JSON brace salvage | Models emitted prose/code fences | Probably reduced | Remove from canonical path; compatibility adapter only | Malformed-output rate on target models |
| Fixed 1,000 output tokens | Local inference cost/context | Probably obsolete for whole-dataset output | Budget based on target count with hard cap and continuation protocol | Truncation rate and cost curve |
| Hard-coded `SEMANTIC_LOGICAL_HINTS` | Model confused logical and semantic types | May persist, but the solution should be a typed ontology | JSON Schema enums plus deterministic compatibility table | With/without prompt hints on blind schemas |
| CSV/HDF5 exact semantic maps | Deterministic path was used to avoid LLM hallucination/cost | Model capability improved; trust requirement remains | Explicit metadata -> verified; model/name -> unverified candidate | External blind ablation at fixed selective risk |
| Repeated critique-like stages | Weak model outputs required normalize/validate/merge choreography | The logical checks remain necessary | One typed run pipeline, not multiple scripts/calls | Fault-injection recovery and equivalence test |
| Manual manifest repair | Endpoint interruption and partial writes | Operational risk remains | Transactional run store with per-call state and resumability | Kill/restart tests; exactly-once artifact generation |

**Important:** evidence validation, abstention, parser authority, and human gold review are not model capability debt. They are trust-boundary controls and should become stricter, not disappear.

---

# Phase 5 — First-principles redesign

## 5.1 Revised objective

Build and evaluate a **verified schema claim system** for heterogeneous scientific files.

The unit of output is not “a schema field with a confidence.” It is a property-level claim with:

- subject and property;
- proposed value;
- epistemic state: observed, declared, derived, inferred, unknown, conflicted, unsupported;
- verification state: verified, unverified, rejected, not-verifiable;
- scope: full resource, metadata only, sample, or document span;
- evidence IDs and exact source locations;
- generator identity/version;
- verifier identity/version;
- property-specific confidence, only when calibrated;
- alternatives and conflict links.

The primary research metric becomes **verified claim coverage at a stated error rate**, not raw completeness or a single aggregate accuracy.

## 5.2 New architecture

```text
1. Isolated intake
   path/stream -> hash -> resource limits -> format evidence

2. Parser adapters
   bytes/metadata -> Observation Graph
   (nodes, fields, declarations, samples, exact evidence spans)

3. Standards validators
   Observation Graph -> verified/derived claims
   (CF, UCUM/UDUNITS, Arrow, JSON Schema, XSD, CSVW where applicable)

4. Optional semantic reasoner
   Observation Graph + documentation -> unverified candidate claims
   (one dataset-level structured call; no physical-field creation)

5. Claim adjudicator and ledger
   reference checks + precedence + contradiction rules + verification state

6. Views
   canonical JSON, legacy adapter, retrieval index record, reviewer UI

7. Offline benchmark
   blind external corpus + independent gold + strategy/cost/coverage evaluation
```

This is one runtime pipeline, not multiple agents.

## 5.3 Component responsibilities

### Isolated intake

- compute content hash and stable resource identity;
- enforce file count, byte, CPU, memory, recursion, and parser-time limits;
- collect magic, suffix, media type, and directory signals;
- never infer schema semantics.

### Parser adapters

- read authoritative physical structure and explicit declarations;
- emit observation scope and evidence locations;
- never label name-only semantics as verified;
- expose adapter capability and spec/library version.

### Standards validators

- convert explicit metadata to verified claims;
- derive deterministic properties with versioned reason codes;
- validate units, calendars, dimensions, coordinate relationships, and declared schemas;
- emit conflicts rather than mutate a field in place.

### Optional semantic reasoner

- consume the complete dataset observation graph and allowed documentation;
- propose only properties for existing subjects;
- cite existing immutable evidence IDs;
- return alternatives/counterevidence and abstain when unsupported;
- have no write access to the canonical ledger.

### Claim adjudicator

- reject nonexistent or property-inapplicable evidence;
- enforce evidence precedence and semantic/logical compatibility;
- require calibrated policy thresholds where confidence is used;
- keep verified facts, unverified hypotheses, and rejected claims simultaneously;
- make every transition auditable.

### Views

- derive old `DatasetSchema` only for compatibility;
- build retrieval fields from an allowlisted claim-state policy;
- render the same canonical ledger in CLI and GUI;
- never copy claims into a new independent truth representation.

### Benchmark

- remain outside runtime imports;
- version protocols, splits, prompts, models, and standards;
- regenerate reports from raw run records;
- keep historical frozen artifacts under `archive/artifact_paper_2026/`.

## 5.4 Model/tool boundaries

- Deterministic code owns format detection, parsing, evidence identity, schema validation, standards lookup, merge/adjudication, metrics, and artifact writes.
- The model owns contextual semantic candidate generation and explanations only.
- A model may request a controlled vocabulary lookup through an allowlisted read-only tool; deterministic code records and validates the returned registry item.
- Model self-critique is advisory. It is never verification.
- Human experts own semantic gold and adjudication of inherently semantic disagreements.

## 5.5 Validation strategy

1. JSON/schema validity.
2. Evidence referential integrity.
3. Evidence applicability to subject/property.
4. Source-span/hash integrity.
5. State-transition and precedence invariants.
6. Parser differential checks against native libraries.
7. Standards conformance suites.
8. Negative controls for hallucinated evidence, contradictions, prompt injection, misleading names, and sample shifts.
9. Human review for semantic entailment.

Correctness and confidence are separate:

- correctness is determined retrospectively against independent gold or an authoritative standard;
- confidence is a generator output that must be calibrated on held-out data;
- verification state records whether an independent mechanism accepted the claim;
- evidence coverage records whether traceable support exists;
- none substitutes for another.

## 5.6 Evaluation strategy

### Corpora

- controlled fixtures: regression only;
- external compatibility set: parser conformance;
- blind real-file benchmark: research claims;
- adversarial/negative-control set: safety claims.

### Strategies

1. native parser/declaration baseline;
2. current deterministic heuristics;
3. current-model semantic-only over equal observations;
4. hybrid parser + model candidates + adjudicator;
5. human expert upper bound.

### Metrics

- per-property precision, recall, and coverage;
- selective risk versus coverage;
- verified-claim precision and coverage;
- abstention precision/recall on applicable cases;
- evidence-reference validity and evidence entailment precision;
- calibration error/Brier score where confidence is used;
- cross-field consistency;
- parser failure/partial recovery;
- latency, calls, input/output tokens, and cost;
- inter-annotator agreement and adjudication rate;
- retrieval nDCG/Recall with confidence intervals over graded qrels.

Never score N/A as zero or one. Report denominators for every metric and both micro and macro summaries.

## 5.7 Failure recovery

- parser adapter failure returns partial observations plus structured issues;
- model failure leaves the deterministic ledger usable and unchanged;
- oversized semantic tasks use measured, generic partitioning and deterministic reconciliation;
- every run is resumable by content hash + configuration hash;
- transient endpoint errors are retried with bounded exponential backoff and logged;
- schema-invalid model output is quarantined, not salvaged into canonical data;
- historical artifacts are immutable by hash, while new versions are written separately;
- reviewer UI shows rejected/unverified claims and exact failure stages.

---

# Phase 6 — Current versus proposed

| Dimension | Current system | Proposed system |
| --- | --- | --- |
| Logical runtime components | Roughly 20 before study builders/evaluators; 7 adapters plus registry/helpers, 3 schema/export shapes, CLI/GUI, and 4 semantic stages | 7: intake, adapters, validators, reasoner, ledger/adjudicator, views, offline benchmark |
| Model calls | Canonical extraction: 0. Optional semantic default: 276 scheduled calls over 25 current tasks; actual historical calls unrecorded | Deterministic mode: 0. Semantic target: ~25 dataset calls, with measured adaptive fallback |
| Context fragmentation | High; mostly per-field, 2 evidence items, max 8 resolved context fields | Low; whole observation graph first |
| Latency/cost | Excellent without semantics; potentially poor and failure-prone with per-field semantics | Same deterministic cost; much lower expected semantic call overhead |
| Reliability | Strong on authored fixtures; semantic trust boundary is defective | Stronger referential/verification guarantees; model generalization remains empirical |
| Maintainability | 14k source lines, many phase wrappers/evaluators, overlapping schemas | Smaller runtime, declarative conformance cases, one canonical claim model |
| Debuggability | Many artifacts, but evidence changes identity and stages are file-coupled | One run record with immutable observations, claims, decisions, and telemetry |
| Generalizability | Physical adapters generalize within tested specs; CSV/HDF5 semantics and retrieval are corpus-tuned | Physical behavior preserved; semantics evaluated on blind external data |
| Research value | Low-to-moderate as currently evaluated | High if reframed around verified coverage/selective risk and executed on a credible benchmark |
| Technical debt | Frozen compatibility, duplicated artifacts, hard-coded mappings/groups | Migration adapter and archive are the main deliberate debt |

## Cases where the existing system is better

- For physical schema, the existing deterministic parser path is better than an LLM-first redesign.
- For offline/local use, zero-model extraction is cheaper, faster, private, and reproducible.
- The explicit abstention and structured issue model is already better than best-effort generation.
- The format challenge packs are useful regression assets and should not be discarded.
- The frozen artifact is useful as a historical reproducibility snapshot even though it is not a strong benchmark.
- The current simple TF-IDF implementation remains a valuable transparent lower baseline once document construction is fixed.
- The model-independent GUI examples communicate failure and conflict states well.

---

# Phase 7 — Research critique

## 7.1 Is the question still interesting?

**Yes, after reformulation.** Reliable, auditable claims from raw scientific files remain important. Stronger models do not remove the need to parse binary containers, obey scientific metadata standards, or distinguish evidence from guesses.

**No, in its current contribution framing.** “Deterministic first, then constrained LLM annotation” is no longer enough by itself. Recent adjacent work already studies scientific LLM schema mining, LLM schema matching, hybrid retrieval, complex schema benchmarks, and human-in-the-loop validation: [LLMs4SchemaDiscovery](https://arxiv.org/abs/2504.00752), [Schemora](https://arxiv.org/abs/2507.14376), [LLMatch/SchemaNet](https://arxiv.org/abs/2507.10897), [Towards Scalable Schema Mapping using LLMs](https://arxiv.org/abs/2505.24716), and [BDIViz](https://arxiv.org/abs/2604.10763).

These are adjacent rather than identical tasks, but they make the paper’s current LLM baselines and novelty discussion obsolete. None appears in `docs/references.md`.

## 7.2 Is the problem implicitly solved by stronger models?

- Physical extraction: no.
- Semantic typing on the 50-field synthetic pilot: plausibly yes; must be tested with a current model-only baseline.
- Evidence verification and calibrated abstention: no. Stronger generation is not independent verification.
- Retrieval over 16 planted candidates: likely trivial for modern embeddings/rerankers and not scientifically informative.

## 7.3 Does the project measure a real phenomenon?

Partly.

- Parser conformance and structured failure behavior are real engineering phenomena.
- The internal accuracy result is heavily confounded by co-generation and tuning.
- The semantic “evidence adequacy” result measures evidence-list presence, not whether evidence supports the property.
- The retrieval gain measures a mixture of added metadata, added README text, schema terms, repeated slice terms, and target-authored queries.
- Post-freeze 1.0000 metrics mostly measure whether code satisfies manifests authored with its fixtures.

## 7.4 Methodological defects

### Gold and corpus circularity

`create_pilot_corpus.py` writes both the synthetic inputs and their gold. The same repository then adds exact semantic mappings for names found in those files. The “second-pass human review” is a consistency script, not independent reannotation, and all 50 gold field evidence lists are empty.

**Consequence:** internal accuracy is a development-set regression score, not a generalization estimate.

### Metric invalidity

- Unit accuracy treats zero expected units as 0.0. The reported 0.8889 is entirely caused by one N/A dataset.
- Time-axis accuracy treats N/A datasets as 1.0. The reported 0.6667 is not an extraction success rate; all three applicable time-series cases fail exact comparison.
- Semantic accuracy counts `unknown == unknown` as correct without a selective-accuracy analysis.
- Macro averages over nine designed datasets have no uncertainty interval.

### Semantic trust failure

The implementation accepts nonexistent evidence and confidence 0.0. Therefore “all accepted semantic merges cite supporting evidence” is only a string-presence claim, not an evidence-integrity claim. `unified_schema.py:86-114` then applies the same original field evidence to physical, logical, semantic, unit, and nullable claims, regardless of which evidence supported which property.

### Retrieval confounding and leakage

- `schema_enhanced` includes metadata + README-like description + schema; the baselines are metadata-only and README-only.
- filename slice terms are repeated four times specifically to distinguish same-family files;
- queries are hand-written from expected targets;
- qrels contain one planted positive;
- candidate pool is 16 files;
- only TF-IDF is evaluated.

The result is a demo, not evidence that extracted schemas improve real dataset retrieval.

### Benchmark and test conflation

Phase 12-17 fixtures and expected manifests are created in the repository. These are good contract tests. Reporting their perfect scores alongside research metrics encourages a false impression of external validation.

### Reproducibility gaps

- actual semantic call counts, token use, latency, seeds, retries, and per-call model identifiers are not stored;
- an internal network endpoint is embedded in the annotation manifest;
- many generated artifacts contain local absolute paths;
- release audit misses those paths;
- prompt and code hashes are absent from semantic run records.

## 7.5 Missing baselines

- native library output and standards validators;
- current strong model over headers/samples/docs with no project heuristics;
- current strong model over full parser observations;
- hybrid model with and without adjudication;
- explicit-metadata-only semantic baseline;
- BM25, current embeddings, and reranking for retrieval;
- human expert upper bound;
- always-unknown selective lower bound.

## 7.6 Missing ablations

- disable CSV/HDF5 name heuristics;
- headers only vs values only vs descriptions only vs all evidence;
- per-field vs whole-dataset vs adaptive semantic scheduling;
- evidence presence vs evidence-reference validation vs human entailment;
- deterministic standards lookup vs model interpretation;
- metadata+README baseline vs +physical vs +logical vs +semantic retrieval fields;
- with/without repeated slice terms;
- with/without confidence thresholds;
- legacy field model vs claim ledger in shadow mode.

## 7.7 Stronger negative controls

- randomize or swap field names while preserving values;
- give misleading suffixes and format hints;
- inject conflicting units/standard names;
- insert prompt instructions into README/source metadata;
- cite nonexistent, real-but-irrelevant, and cross-field evidence IDs;
- create same-name non-join fields and same-family near duplicates;
- shift the first 200 rows away from the rest of a file;
- compare duplicated fields with different scopes/groups;
- hold out entire domains and producers, not random files.

## 7.8 Better bounds

- lower: parser-only physical observations, always unknown semantics;
- lexical lower: unbiased TF-IDF/BM25;
- oracle physical: native library + declared schema;
- oracle semantic: two experts with codebook and adjudication;
- oracle retrieval: graded qrels with exhaustive pool judgments;
- cost upper bound: human review of every claim;
- coverage upper bound: all gold properties, with unsupported properties explicitly marked not-verifiable.

## 7.9 Contribution assessment

| Contribution type | Current strength | Honest assessment |
| --- | --- | --- |
| Engineering | Moderate | Multi-format adapters, structured outcomes, fixtures, CLI/GUI, and CI are useful, though custom and over-expanded. |
| Research | Weak | Current benchmark cannot support general claims; novelty baseline is outdated. |
| Evaluation | Promising concept, weak execution | Separating correctness/evidence/abstention is valuable, but metrics and evidence validation are flawed. |
| Dataset | Weak | Synthetic 9-dataset pilot and 16-file planted pool are examples, not a publishable benchmark. |
| Infrastructure | Moderate-to-strong | Reproducible builders, many tests, frozen artifacts, and demo are substantial; path/provenance hygiene needs repair. |

**Reviewer recommendation for the current paper:** reject as an empirical research paper; consider as a software/artifact demonstration after claim corrections. Encourage resubmission only after an independent blind benchmark, current baselines, valid evidence checks, and corrected metrics.

---

# Phase 8 — Prioritized migration plan

No old path should be removed until its proposed replacement passes the stated comparison. Historical artifacts should be archived, not rewritten.

## Tier 0 — Verify before changing

### T0.1 Semantic scheduling bakeoff

- **What:** old per-field vs whole-dataset vs adaptive partitioning on the same 25 tasks.
- **Why:** directly tests the largest model capability debt.
- **Expected benefit:** up to an order-of-magnitude call reduction and better consistency.
- **Risk:** large-task attention/truncation failure.
- **Effort:** medium, 3-5 days plus model runtime.
- **Success:** non-inferior verified-claim precision; fewer calls and lower latency; no worse evidence validity.
- **Reversible:** yes; feature flag and stored run manifests.

### T0.2 Blind semantic strategy benchmark

- **What:** create a producer/domain-held-out real-file set and compare explicit-only, current heuristics, model-only, and hybrid.
- **Why:** determines whether deterministic semantic rules or a current model should own candidate generation.
- **Expected benefit:** evidence-based deletion of corpus-tuned rules.
- **Risk:** expert annotation cost.
- **Effort:** high, 3-6 weeks.
- **Success:** confidence intervals for selective precision/coverage; inter-annotator agreement reported.
- **Reversible:** yes; no runtime replacement until results exist.

### T0.3 Retrieval deconfounding study

- **What:** rebuild documents with equal metadata+description baselines, no repeated slice terms, fielded schema additions, modern rankers, and graded user queries.
- **Why:** tests whether schema itself helps retrieval.
- **Expected benefit:** valid retrieval contribution or a justified deletion of the retrieval claim.
- **Risk:** the reported gain may disappear.
- **Effort:** high, 2-4 weeks.
- **Success:** pre-registered ablation and significance/interval estimates on a larger held-out pool.
- **Reversible:** yes; preserve frozen demo.

### T0.4 Claim-ledger shadow projection

- **What:** emit a property-level ledger alongside current outputs for all fixtures.
- **Why:** validates the core redesign without breaking consumers.
- **Expected benefit:** exposes evidence/state loss and migration cost.
- **Risk:** temporary duplication.
- **Effort:** medium, 1-2 weeks.
- **Success:** explicit mapping coverage for every legacy property and reviewed intentional differences.
- **Reversible:** yes.

### T0.5 External parser differential study

- **What:** compare adapters with native library/xarray/cf-xarray/Zarr/Arrow views on real producer files.
- **Why:** separates custom adapter value from reimplementation defects.
- **Expected benefit:** deletes redundant parsing and strengthens conformance claims.
- **Risk:** version-sensitive differences.
- **Effort:** medium-high.
- **Success:** categorized differences with zero unexplained high-severity mismatches on the target scope.
- **Reversible:** yes.

## Tier 1 — High value / low risk

### T1.1 Enforce evidence and confidence integrity

- **What:** validate evidence ID existence, field/property applicability, exact source identity, and a documented acceptance threshold; reject confidence-0 claims.
- **Why:** closes a demonstrated canonical-truth breach.
- **Expected benefit:** trustworthy semantic merge.
- **Risk:** current accepted merge count may fall.
- **Effort:** low, 1-2 days.
- **Success:** negative controls fail closed; all historical accepted claims are re-audited.
- **Reversible:** code-reversible, but should not be disabled after validation.

### T1.2 Correct N/A metrics in a new report version

- **What:** represent N/A as null/excluded, report denominators, micro/macro metrics, and selective accuracy.
- **Why:** current unit and time-axis headline values are mathematically misleading.
- **Expected benefit:** valid evaluation.
- **Risk:** headline numbers change and the frozen paper requires an erratum note.
- **Effort:** low.
- **Success:** unit accuracy is 1.0 over 8 applicable datasets; time-axis result is reported over 3 applicable datasets, not 9; all metrics include denominators.
- **Reversible:** preserve old frozen report as historical.

### T1.3 Fix artifact identity and release audit

- **What:** normalize evidence sources to content-addressed/repository-relative URIs; detect escaped paths; audit all generated artifacts; freeze by hashes, not only `git diff`.
- **Why:** current readiness audit has a demonstrated false negative.
- **Expected benefit:** portable artifacts and credible release checks.
- **Risk:** large regenerated diffs.
- **Effort:** low-medium.
- **Success:** injected escaped Windows/Unix paths are caught; clean rebuild is byte-stable where promised.
- **Reversible:** yes, with artifact versioning.

### T1.4 Add semantic run telemetry

- **What:** record task/config/prompt/code hashes, provider/model version, seed, calls, retries, tokens, latency, finish reason, and per-call status.
- **Why:** current model results cannot be costed or exactly reconstructed.
- **Expected benefit:** experimental reproducibility and operational debugging.
- **Risk:** provider metadata variance and accidental endpoint disclosure.
- **Effort:** low-medium.
- **Success:** every new semantic result is traceable without storing secrets/internal URLs.
- **Reversible:** yes.

### T1.5 Reclassify challenge packs

- **What:** rename reporting categories to regression/conformance and remove them from any aggregate impression of model/system accuracy.
- **Why:** fixtures and expectations are co-authored.
- **Expected benefit:** honest claim boundaries.
- **Risk:** less impressive presentation.
- **Effort:** low.
- **Success:** paper/demo never describe authored-pack scores as real-world accuracy.
- **Reversible:** documentation-only.

### T1.6 Package/test configuration cleanup

- **What:** add `pyproject.toml`, one console entry point, explicit Python matrix/config, and remove the pytest-asyncio warning source if in scope.
- **Why:** Git root/package root and invocation paths are easy to confuse.
- **Expected benefit:** simpler installation and reproducibility.
- **Risk:** packaging migration details.
- **Effort:** low.
- **Success:** editable install, CLI, tests, and clean checkout work on the declared matrix.
- **Reversible:** yes.

## Tier 2 — Architectural improvements

### T2.1 Introduce Observation Graph + Claim Ledger

- **What:** replace mutable flattened fields as the canonical internal model.
- **Why:** property-specific state/evidence/confidence cannot be represented today.
- **Expected benefit:** correctness, provenance, and simpler exports.
- **Risk:** largest compatibility migration.
- **Effort:** high, 3-6 weeks.
- **Success:** shadow comparison passes; negative controls and evidence invariants are complete.
- **Reversible:** yes while the legacy adapter remains.

### T2.2 Separate parsers from semantic candidate generation

- **What:** adapters emit observations/declarations only; move name-based semantics to a candidate plugin.
- **Why:** prevents weak names from becoming “supported” truth.
- **Expected benefit:** clearer trust boundary and fair strategy ablation.
- **Risk:** apparent semantic completeness drops.
- **Effort:** medium-high.
- **Success:** physical conformance unchanged; verified semantic precision improves or holds on blind data.
- **Reversible:** feature-gated candidate plugin.

### T2.3 Merge output representations

- **What:** canonical ledger plus derived legacy/retrieval/UI views; retire independent unified/agent truth copies.
- **Why:** reduces context loss and duplicate transformations.
- **Expected benefit:** lower maintenance and better debugging.
- **Risk:** downstream schema changes.
- **Effort:** medium.
- **Success:** one canonical serialized artifact; compatibility tests for required consumers.
- **Reversible:** legacy view adapter.

### T2.4 Consolidate evaluators/builders

- **What:** declarative case manifests and one typed evaluator/build CLI; delete trivial phase wrappers after equivalence.
- **Why:** the phase file structure is historical, not functional.
- **Expected benefit:** fewer components and consistent metric semantics.
- **Risk:** losing special-case diagnostics.
- **Effort:** medium.
- **Success:** byte/semantic equivalence for archived reports and simpler new case addition.
- **Reversible:** keep old scripts until diff is clean.

### T2.5 Sandbox parser execution

- **What:** run uploaded-file parsing in a constrained subprocess with resource and time limits.
- **Why:** untrusted scientific formats are parsed in the GUI server process.
- **Expected benefit:** observable, bounded failure.
- **Risk:** platform-specific process control.
- **Effort:** medium.
- **Success:** oversized/deep/malformed fixtures terminate without taking down the server.
- **Reversible:** local-dev bypass flag.

### T2.6 Split runtime, benchmark, and archive

- **What:** separate package boundaries and versioning.
- **Why:** current product, paper, and post-freeze objectives conflict.
- **Expected benefit:** smaller install/runtime, clearer claims, less frozen-compatibility pressure.
- **Risk:** repository migration and links.
- **Effort:** medium-high.
- **Success:** runtime tests do not import benchmark/paper builders; archive rebuild remains documented.
- **Reversible:** Git history/archive branch.

## Tier 3 — Experimental redesigns

### T3.1 Current-model whole-schema reasoner

- **What:** deploy the winner of T0.1 as an optional candidate generator.
- **Why:** remove historical context fragmentation.
- **Expected benefit:** fewer calls and richer cross-field semantics.
- **Risk:** model drift/nondeterminism.
- **Effort:** medium after Tier 0.
- **Success:** pre-registered thresholds on blind verified claims, cost, and latency.
- **Reversible:** yes; optional plugin.

### T3.2 Controlled-vocabulary tool use

- **What:** allow read-only CF/UCUM/domain ontology lookup through deterministic tools.
- **Why:** combines model query formulation with authoritative verification.
- **Expected benefit:** broader semantics without fabricated registry claims.
- **Risk:** ontology mismatch and network/version dependence.
- **Effort:** medium-high.
- **Success:** improved verified semantic coverage with no precision regression.
- **Reversible:** yes.

### T3.3 Human-in-the-loop benchmark workbench

- **What:** evolve the GUI from artifact display to blind claim adjudication with disagreement capture.
- **Why:** independent semantic gold is the bottleneck, and recent work treats interactive validation as core infrastructure.
- **Expected benefit:** a real dataset/evaluation contribution.
- **Risk:** substantial UX and study-design effort.
- **Effort:** high.
- **Success:** two annotators, adjudication workflow, agreement metrics, and locked test split.
- **Reversible:** separate benchmark app.

### T3.4 Multimodal codebook grounding

- **What:** ingest scanned tables/PDF codebooks only for datasets that require it.
- **Why:** potentially recovers unavailable evidence.
- **Expected benefit:** broader document-grounded coverage.
- **Risk:** new OCR/vision error surface and scope creep.
- **Effort:** high.
- **Success:** separate benchmark demonstrates net verified coverage gain.
- **Reversible:** optional module.

---

# Final disposition

## Preserve

- parser authority over physical facts;
- structured outcomes and abstention;
- format adapters and their regression fixtures;
- optionality of semantic inference;
- visible uncertainty/conflict concepts;
- reproducible historical artifact.

## Simplify or remove after evidence

- per-field model calls and manual groups;
- corpus-specific semantic mappings;
- overlapping schema/envelope/agent representations;
- phase wrappers and evaluator proliferation;
- retrieval term engineering;
- unused abstractions and direct legacy CLI paths.

## Build now

- real evidence-reference validation;
- correct N/A-aware metrics;
- property-level claim/verification model in shadow mode;
- complete semantic telemetry;
- portable content-addressed provenance;
- blind external evaluation and current baselines.

The project’s durable insight is not “deterministic code beats models.” It is that different claims require different authorities. Bytes and explicit declarations belong to parsers and standards. Contextual meaning may benefit from a strong model. Canonical truth requires independent verification. The minimum architecture is the one that preserves those authority boundaries while deleting everything that exists only to nurse a weaker model through fragmented prompts.
