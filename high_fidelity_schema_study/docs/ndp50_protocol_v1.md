# NDP-50 External Validation and Capability Discovery Protocol v1

Status: structural validation complete; semantic study/test not authorized

## 1. Purpose

This study evaluates the deterministic schema-extraction product on a bounded,
versioned sample from the National Data Platform (NDP) Central Catalog. It also
uses development cases to identify capability debt without contaminating the
held-out result.

NDP is a metadata catalog rather than a data repository. The selection unit is
therefore an NDP dataset record, while the processing unit is a resource attached
to that record. Dataset counts and resource counts are never reported as
interchangeable.

The study is a new external-validation track. It does not revise the frozen
Artifact Paper benchmark or its historical headline metrics.

## 2. Research questions

1. What fraction of selected NDP datasets expose resources that the current
   deterministic product can successfully, partially, or not extract?
2. Which failures arise from access, packaging, format routing, parser coverage,
   bounded sampling, standards handling, or resource limits?
3. How often do NDP-declared format, MIME, column dictionary, temporal, spatial,
   size, and access metadata agree with direct resource observations?
4. On independently annotated semantic-opportunity cases, what do one
   dataset-level semantic response and deterministic verification add beyond
   deterministic extraction?
5. For applicable tabular resources, how stable are column type/property
   annotations across prompt formulations, example-selection methods, domains,
   and vocabularies?

## 3. Claim boundary

The first 50-dataset run is an external pilot unless the executable power
analysis independently shows that its sealed comparable semantic-opportunity
count is sufficient. Random selection within a bounded snapshot does not make the
sample representative of all NDP data or all scientific repositories.

Post-selection download failures, access failures, unsupported resources, and
parser failures remain in the denominator appropriate to their research
question. They are not silently replaced. A replacement is permitted only by
the deterministic reserve order frozen before outcome inspection.

## 4. Corpus construction

### 4.1 Source

The source is the public NDP CKAN `package_search` endpoint:

`https://nationaldataplatform.org/catalog/api/3/action/package_search`

Every capture freezes the complete request URL, response bytes, retrieval time,
catalog count, returned records, adapter implementation hash, and snapshot hash.

### 4.2 Complete lightweight candidate frame

The catalog is first captured with a restricted CKAN `fl` projection containing
only stable dataset identity, title, organization, modification time, and indexed
resource-format values. The capture must consist of contiguous, individually
content-hashed pages whose combined unique identities exactly equal the catalog's
reported count. Resource lists and extras are deliberately not expanded before
selection.

Every identity record is selection-eligible. Access, entity-type, resource-count,
and format-detail failures discovered by the later `package_show` expansion stay
in the study as acquisition or catalog-quality outcomes. This prevents the system
from selecting only records that are already known to be easy or supported.

The earlier fixed-seed random detailed-snapshot design was rejected during
protocol development: 110 of 120 sampled records belonged to one organization,
and those records exposed 25,783 resources. The complete lightweight frame plus
organization caps avoids silently treating the dominant catalog contributor as
the whole NDP population.

### 4.3 Selection and split

The target is 50 dataset records:

- development: 15;
- validation: 10;
- sealed test: 25.

Selection is stratified by the dominant declared/inferred resource-format class.
Within each stratum, SHA-256 priority derived from the registered seed selects
records subject to a frozen maximum contribution per organization. Split
assignment uses a separate SHA-256 priority. The design also freezes per-stratum
reserve counts.

Only development records may drive implementation changes. Validation records
may reject a proposed fix or threshold but may not motivate dataset-specific
logic. Test records stay sealed until acquisition policy, product code,
evaluation code, semantic prompt, backend registry, and gold workflow are
frozen.

## 5. Resource acquisition and execution

All resources remain inventoried. Full extraction is limited to resources
selected by a deterministic resource policy frozen after development:

- at most three extractor-eligible resources per dataset in stable resource-ID
  order;
- at most 25 MiB per resource and 50 MiB transferred per dataset;
- at most three attempts separated by 10 seconds, and only explicit asynchronous
  provider status responses are retryable;
- data-bearing resources are preferred over documentation only through explicit
  resource-role evidence;
- archives are inventoried before any member selection;
- byte, wall-time, recursion, member-count, and decompression-ratio limits are
  mandatory;
- unknown size never means unlimited download;
- redirects, final URL, content type, byte count, SHA-256, and failure reason are
  recorded;
- credentials and restricted data are never committed.

Remote Zarr processing additionally requires resource metadata that uniquely
locates a store with discoverable Zarr metadata markers. A bucket root, portal
index, or store path found only in unstructured third-party documentation is
recorded as `remote_store_locator_incomplete`; the executor does not guess a
dataset-specific path.

The canonical execution path is
`extract_path(ExtractionRequest(...))`. Every attempted resource produces a
structured success, partial, abstained, or failed record. Model output cannot
create physical fields.

## 6. Declared-versus-observed audit

The NDP metadata is evidence, not gold. The audit retains declared and observed
values separately for:

- entity and resource format;
- MIME type;
- byte size;
- field/column dictionary;
- temporal extent, resolution, and timezone;
- spatial extent and projection;
- license and access rights;
- documentation and provenance.

Agreement, conflict, missing declaration, and untestable status are distinct.
N/A is never scored as zero or one.

## 7. Capability-debt loop

Development failures use the fixed taxonomy:

- access or transport;
- archive or multi-resource organization;
- unsupported format;
- format-signal conflict or misrouting;
- parser/standard limitation;
- bounded-sample instability;
- declared/observed conflict;
- unit, temporal, spatial, or relationship limitation;
- evidence/provenance integrity;
- resource/performance/security limit;
- documentation or prompt-injection risk.

Each accepted fix requires a minimized regression fixture, a general rule rather
than a dataset-name mapping, validation evidence, and a change record. No test
case is used to tune the product.

## 8. Independent gold

Semantic research uses the existing two-annotator independent workflow and
sealed consensus hash chain. Annotators may inspect original resources and
approved source documentation but not architecture outputs. NDP metadata may
support a label only when the annotation records the exact supporting span; it
is never automatically copied into gold.

Dataset is the primary statistical unit. Gold coverage, agreement,
disagreement, adjudication rate, and evidence identity are reported.

## 9. Column annotation sub-study

The sub-study applies only when a tabular resource and the target relationship
are applicable. It adapts Korini and Bizer's column property annotation study
without treating CPA as equivalent to general schema extraction.

Pre-registered comparisons are:

- deterministic-only;
- zero-shot whole-dataset semantic response;
- byte-identical response plus deterministic verification;
- one- and five-shot responses using development-only similarity-selected
  demonstrations;
- optional fine-tuning only with a separately frozen training corpus.

The vocabulary, subject-column applicability rule, table serialization, row
sampling, prompt variants, model, decoding parameters, and OOV handling are
frozen. Metrics include micro- and macro-F1, per-label F1, OOV rate, prompt
sensitivity, cross-domain/vocabulary transfer, verified coverage, selective
risk, unsupported claims, evidence-reference validity, calls, tokens, latency,
and cost.

Head, stratified, and adaptive row samples are compared on development and
validation data. Missing values are not silently filled from other rows.

## 10. Negative controls

Before test unsealing, the pipeline must fail closed on:

- nonexistent and irrelevant evidence IDs;
- contradicted declared metadata;
- prompt instructions embedded in descriptions or documentation;
- misleading extensions and MIME declarations;
- empty, truncated, corrupt, or duplicate resources;
- row-order/sample shifts;
- oversized archives and decompression bombs;
- unavailable or redirecting resource URLs.

## 11. Reporting and stopping rules

Reports include dataset- and resource-level denominators, missingness, N/A
counts, macro and micro summaries, dataset bootstrap intervals, and the
pre-registered paired sensitivity analyses. Controlled regression packs remain
engineering evidence and are not mixed with external accuracy estimates.

The study may conclude with successful external validation, a bounded
compatibility result, an underpowered semantic result, a clean null for model
augmentation, or a documented benchmark contribution. No new architecture arm,
prompt, rerun, or hand-picked replacement is added to rescue a result.

## 12. Artifact layout

```text
data/experiments/ndp50_v1/
  catalog_snapshots/
  candidate_frame.json
  selection_design.json
  selection.json
  acquisition/
  resources/
  schemas/
  declared_observed/
  gold/
  runs/
  reports/
    <run-role>/
      summary.json
      failure_ledger.json
      report.md
```

## 13. Feedback incorporation and publication control

Swathi's Phase 1 methodological feedback is incorporated through:

- `docs/swathi_feedback_response_matrix_v1.md`;
- `docs/ndp50_feedback_implementation_audit_v1.md`;
- `docs/ndp50_feedback_improvement_amendment_v1.md`;
- `docs/ndp50_statistical_analysis_plan_v1.md`;
- `docs/ndp50_annotation_and_independence_plan_v1.md`;
- `docs/ndp50_power_policy_review_guide_v1.md`;
- `docs/ndp50_methodological_risk_register_v1.md`;
- `docs/ndp50_swathi_feedback_signoff_guide_v1.md`;
- `docs/semantic_architecture_claim_ledger_v1.md`;
- `docs/preregistration/ndp50_osf_zenodo_preregistration_draft_v1.md`;
- `docs/preregistration/public_package_files_v1.txt`;
- `ndp50_publication_gate.py`, the content-bound neutral sign-off artifact,
  and the external-receipt template;
- `docs/literature/semantic_architecture_literature_review_2026-07-27.md`.

These documents strengthen positioning, citation coverage, claim language,
resource reporting, agreement reporting, selective-prediction sensitivity, role
independence, and public preregistration. They do not alter the current frozen
selection or authorize semantic/test execution.

The preregistration file is explicitly a draft. It cannot satisfy test release
until every required placeholder is replaced, its public attachments are
reviewed for sealed-identity leakage, and an external immutable receipt is
verified. The claim ledger likewise records current evidence boundaries; it
must be versioned after blind execution rather than retroactively edited to
match an outcome.

`ndp50_preregistration_package.py` deterministically hashes and scans the
sorted public text-source allowlist. Its replayed local manifest establishes
listed-file integrity and zero exact sealed ID/title matches only; it is not an
external timestamp, cannot rule out indirect re-identification, and adds no
test-release authority.

`ndp50_publication_gate.py` closes the prose-to-code gap. `test_ready` cannot
become true until (a) a collaborator sign-off covers F01--F16 without claiming
independence and freezes the inactive-sensitivity decisions, and (b) an
independent non-developer/non-collaborator verifies an immutable OSF/Zenodo
receipt for the exact public manifest and content digest. These are distinct
from, and do not replace, the final operator/independent-monitor test-release
authorization. The 11-stage handoff releases the collaborator sign-off with
the initial human work, releases external registration only after the
execution/power freezes, and releases test authorization only after the
external receipt replays. This ordering prevents the publication prerequisites
from depending circularly on `test_ready`.

An evidence-free call, heuristic comparator, learned CTA/CPA comparator, second
model family, or new registered metric requires a versioned executable design
and regenerated downstream hashes before it can be active. Human consensus is a
reference standard and is never reported as a human upper bound. Swathi is a
research collaborator and may review literature, protocol, claims, and
interpretation, but cannot fill a slot whose validity depends on being blind and
independent of the project.
