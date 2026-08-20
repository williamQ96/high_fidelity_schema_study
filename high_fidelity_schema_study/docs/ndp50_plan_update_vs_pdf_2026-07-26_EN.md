# NDP-50 Research Plan Update: Changes Since the 2026-07-16 PDF

**Prepared:** 2026-07-26
**Comparison baseline:** `paper/build/semantic_architecture_study_en.pdf` and its Chinese counterpart, generated 2026-07-16
**Current plan:** NDP-50 External Validation, Semantic/CPA Preparation, Human Handoff, and Test Freeze workflows
**Current status:** structural validation complete; semantic study and test not authorized

## 1. Executive summary

The previous PDF consolidated semantic schema extraction into an auditable A/B/C/D architecture experiment. It validated the measurement harness, byte-identical B/C replay, evidence boundaries, and backend operational eligibility. It also stated clearly that no blind external effect estimate existed: the corpus, gold labels, power analysis, freeze receipts, and human signatures required for external evaluation were still placeholders.

This update does not revise or replace the previous PDF, and it does not claim an architecture winner. It adds a separate **NDP-50 external-validation track** that turns the earlier blind-evaluation intent into an executable, content-addressed, stage-gated research workflow:

- a complete lightweight NDP candidate frame and a deterministic 50-dataset selection are frozen;
- development and structural validation are complete while 25 test datasets remain sealed;
- compatibility, acquisition, declared-versus-observed metadata, semantic contribution, and CPA robustness are studied as distinct questions;
- the column property annotation design of Korini and Bizer is incorporated as a bounded tabular sub-study;
- vocabulary, source evidence, data governance, gold, execution, power, and test release now have human review and machine-replay gates;
- the current semantic-validation opportunity count is explicitly recognized as insufficient for a confirmatory superiority claim;
- all test activity is bound to independent signatures, hash freezes, immutable execution records, and preregistered inference.

In short, the project has moved from “a validated architecture harness plus a future blind-evaluation plan” to “a real external corpus, completed structural validation, and a complete semantic/test governance path that is waiting for genuine human decisions.”

## 2. Scope of the previous PDF

The previous PDF asked a focused question: how much semantic architecture is necessary when the deterministic extractor retains authority over the physical schema?

It froze four conditions:

| Condition | Definition |
|---|---|
| A | Deterministic extraction only; no semantic-model call |
| B | At most one dataset-level semantic response per dataset |
| C | Exact replay of B's raw response followed by deterministic evidence, field-relevance, contradiction, and conflict checks |
| D | Historical per-field/manual-group scheduling, free-JSON fallback, and legacy merge behavior |

Its original research questions were:

1. What does one dataset-level semantic response add beyond deterministic extraction?
2. What does deterministic verification change when the semantic response is held exactly constant?
3. Can a minimal hybrid preserve or improve trustworthiness with fewer calls than the legacy pipeline?

The evidence then consisted mainly of nine synthetic development cases and eight non-blind backend-qualification cases. The defensible conclusions were that the harness and operational boundaries worked and that Qwen3.6-27B was operationally eligible after the qualification correction. The report could not establish that semantic reasoning was beneficial, that verification reduced real errors, that D was better or worse, or that any result generalized externally.

## 3. Major changes in the current plan

| Dimension | 2026-07-16 PDF | 2026-07-26 NDP-50 update | Purpose of the change |
|---|---|---|---|
| Study population | Synthetic development and fixed qualification corpora | Frozen external sample from the NDP Central Catalog | Introduce real external heterogeneity |
| Corpus definition | Blind corpus not yet constructed | Complete lightweight frame of 5,823 dataset identities from 75 organizations | Prevent selection of only known-easy data |
| Sampling | Blind candidate frame was a placeholder | Deterministic stratified selection: 15 development, 10 validation, 25 sealed test, plus 17 ordered reserves | Prevent outcome-driven replacement |
| Research questions | Primarily A/B/C/D comparisons | Adds catalog compatibility, failure taxonomy, declared/observed conflict, semantic opportunity, and CPA stability | Separate product coverage, semantic accuracy, and CPA |
| Validation status | No blind external result | Development and structural validation complete | Advance from protocol to real external validation |
| Primary semantic contrasts | A-B, B-C, and C-D | Two co-primary contrasts: deterministic-only vs zero-shot; zero-shot vs byte-identical replay plus verification | Reduce primary hypotheses and sharpen causal interpretation |
| Legacy D | One of the fixed primary comparisons | Not a confirmatory primary contrast in NDP-50 | Avoid excessive primary testing in a small study |
| Few-shot and CPA | Not a central study design | One-shot, five-shot, prompt, row-sampling, domain, and vocabulary transfer as sensitivity analyses | Incorporate useful CPA-paper dimensions |
| Gold workflow | Two independent annotators required in principle | Executable independent review, consensus, and validator chains for vocabulary, sources, CPA applicability, and semantic gold | Turn independent gold into an enforceable workflow |
| Data governance | Provenance and freeze placeholders | Human decisions for licenses, external-model transfer, retention/training use, and redistribution | Avoid treating public access as permission to process or release |
| Power | Paired dataset effects and intervals required | Preregistered sign-flip tests, Holm correction, bootstrap, minimum-effect policy, opportunity assurance, and an underpowered stopping rule | Prevent overinterpretation of a small sample |
| Test control | Blind-freeze table still empty | Eight-stage handoff, independent test-release monitor, immutable run manifest, and sealed test | Prevent test leakage and post-outcome redesign |
| Reproducibility | Content-addressing principles and placeholders | Every stage binds inputs, implementations, submissions, receipts, and freezes by SHA-256 and validator replay | Convert principles into machine-checkable gates |

## 4. NDP-50 corpus and execution design

### 4.1 Candidate frame and selection

The current plan captures the complete NDP lightweight frame through CKAN `package_search`. It retains only stable identity, title, organization, modification time, and a format projection for selection. The frozen state is:

- 5,823 dataset records;
- 75 organizations;
- six contiguous, independently content-hashed catalog pages;
- 50 selected datasets plus 17 frozen ordered reserves;
- split: 15 development, 10 validation, and 25 sealed test datasets.

An earlier proposal to sample detailed records directly was rejected because 110 of 120 records came from one organization and expanded to 25,783 resources. The new design uses the complete lightweight frame, format strata, and an organization cap to reduce domination by one catalog contributor.

### 4.2 Dataset and resource denominators

NDP is a metadata catalog rather than a data repository. The current protocol therefore distinguishes:

- the dataset record as the selection unit;
- the attached resource as the processing unit;
- the dataset cluster as the statistical unit;
- resource-level micro coverage, dataset end-to-end coverage, and dataset-macro resource coverage as different estimands.

This implements the previous PDF's paired per-dataset principle and prevents conditional parser success from hiding catalog-level compatibility loss.

### 4.3 Frozen acquisition policy

The resource policy includes:

- at most three extractor-eligible resources per dataset;
- at most 25 MiB per resource and 50 MiB transferred per dataset;
- at most three attempts separated by a fixed 10-second interval;
- retries only for explicit asynchronous provider status responses;
- rejection of HTTP 200 status/error control documents before extraction;
- a uniquely verifiable store locator for remote Zarr;
- recording of URL, redirects, content type, byte count, SHA-256, and failure reason for every attempt;
- comparison of catalog-declared format with direct observation, but no use of the declaration as an extractor hint.

## 5. Completed structural update

### 5.1 Development

The 15 development datasets exposed 37 catalog resources. The frozen policy attempted 13, acquired 10 data payloads, and completed deterministic extraction on all 10.

All of the following denominators must be reported:

- dataset end-to-end coverage: 7/15 (46.7%);
- catalog-resource end-to-end coverage: 10/37 (27.0%);
- acquisition success given an attempt: 10/13 (76.9%);
- extraction success given acquired data: 10/10 (100%).

The 10/10 result is therefore a conditional extraction rate for acquired, recognizable payloads. It is not evidence of 100% NDP compatibility.

### 5.2 Structural validation

The 10 validation datasets contain 5,054 resources. The frozen policy attempted 10, acquired seven payloads, and extracted six; five of the ten datasets produced at least one schema.

| Measure | Development | Validation |
|---|---:|---:|
| Datasets with at least one schema | 7/15 (46.7%) | 5/10 (50.0%) |
| Resource end-to-end coverage | 10/37 (27.0%) | 6/5,054 (0.12%) |
| Acquisition given attempt | 76.9% | 70.0% |
| Extraction given acquisition | 100.0% | 85.7% |
| Per-dataset macro resource coverage | 35.6% | 44.0% |

The 10,000-replicate bootstrap 95% percentile interval for validation dataset coverage is 20%-80%. This wide interval is expected at n=10 and cannot support a precise prevalence estimate for the full NDP catalog.

One validation dataset contains 4,933 resources, or 97.6% of all validation resources. The 0.12% resource micro rate is therefore dominated by that resource expansion and cannot replace either the 50% dataset rate or the 44% dataset-macro rate.

### 5.3 Defensible interpretation

The structural evidence supports a narrow conclusion: when a payload is directly accessible, remains within the frozen safety bounds, and exposes a trustworthy direct format signal, deterministic extraction is reliable in this small validation split.

It rejects a broad compatibility claim. Coverage is mainly limited by unsupported geospatial and archive formats, extreme resource expansion, size limits, incomplete remote-store locators, and absent direct format signals.

It does not establish semantic correctness, population prevalence across NDP, or an architecture winner.

## 6. Oversights found and corrected

| Oversight | Correction |
|---|---|
| The protocol implied that the full catalog would fit in one response | Require six contiguous pages, individually hashed, whose combined unique IDs equal the catalog count |
| Repeated timestamps caused a dominant zero delta to be used as a cadence divisor | Abstain from cadence and missing-interval claims when the dominant delta is zero; add a regression test |
| HTTP 200 was treated as proof of a data payload | Detect ArcGIS `Pending`, `ExportingData`, and related control payloads and block extraction |
| Failed reruns could leave stale downloads and schemas | Clear only the exact generated targets for each attempted resource before reacquisition |
| Conditional extraction success overstated compatibility | Freeze dataset, catalog-resource, attempted-resource, and acquired-payload denominators separately |
| External payloads changed across retrievals | Freeze retrieval time, final URL, bytes, content type, and SHA-256 |
| Blank or duplicate CSV headers broke field identity | Generate stable unique paths while retaining raw header text and column index |
| The validation runner serialized the role as development | Preserve and exclude v1, record the deviation, and rerun under role-generic validation v2/v3 freezes |
| Semantic modules were accidentally added to the historical structural implementation boundary | Restore separate structural and semantic hash boundaries without rewriting the historical passed freeze |

Every accepted correction is a general rule with regression coverage. Dataset-name-specific workarounds remain forbidden.

## 7. Expansion of the semantic and CPA plan

### 7.1 Semantic opportunities

The current semantic-opportunity manifest contains only successfully extracted development and validation resources:

- 16 resource cases;
- 12 dataset clusters;
- 10 development and six validation cases;
- 277 unique field paths;
- 11 CSV cases requiring CPA applicability assessment;
- five non-tabular cases retained for the general semantic study but excluded from the CPA denominator;
- no test identity, resource, schema, or label.

### 7.2 Effect of the Korini and Bizer CPA paper

The current plan incorporates *Column Property Annotation using Large Language Models* as a bounded tabular sub-study rather than as a replacement for general schema extraction.

Adopted experimental dimensions include:

- zero-shot versus one-shot and five-shot prompting;
- similarity-selected demonstrations;
- prompt-formulation sensitivity;
- row-sampling sensitivity;
- an explicit target vocabulary;
- per-label, micro-F1, and macro-F1 metrics;
- OOV handling;
- cross-domain and cross-vocabulary transfer.

The NDP-50 plan adds safeguards needed for this study:

- demonstrations may come only from development data;
- relational-table, subject-column, and target-property applicability must be established first;
- B and C must consume the byte-identical semantic response;
- evidence references must resolve and be relevant to the field and case;
- unsupported-claim rate, verified coverage, and selective risk are reported;
- the primary unit remains the dataset cluster;
- fine-tuning is optional and cannot use validation or test cases.

CPA does not cover hierarchical, array, geospatial, documentation, or file-level schema questions. Those remain part of general schema extraction or structural compatibility.

## 8. Human governance and freeze workflow

The previous PDF left blind provenance, annotator identities, gold hashes,
prompt hashes, backend registry, and the analysis plan as empty fields. The
current update decomposes them into 11 dependency-ordered stages:

1. data-governance review and accountable approval;
2. vocabulary governance;
3. collaborator sign-off on the complete F01--F16 feedback response;
4. source-bundle rebuild and independent approval;
5. preregistered annotator calibration;
6. CPA applicability screening and semantic-gold review;
7. prompt, serialization, demonstration, and backend freeze;
8. non-blind calibration and power-plan freeze;
9. immutable external preregistration with independent verification;
10. test-release authorization by a study operator and an independent monitor;
11. authorized immutable test execution.

Only stages 1--3 are currently released. All downstream stages remain locked.

### 8.1 Current human assignments

The current release contains:

- one sequential data-governance review and countersignature assignment;
- vocabulary discovery A for a scientific metadata curator;
- vocabulary discovery B for an annotation methodologist;
- one complete F01--F16 collaborator feedback-sign-off assignment for the
  postdoctoral research collaborator.

The A and B vocabulary payloads are byte-identical, but their assignment wrappers are distinct. Each reviewer must independently complete all 16 cases. They may not communicate, view the other submission, construct the candidate catalog, or reveal disagreements until both submissions pass validation and their hashes are atomically frozen.

Data governance requires a non-developer stewardship reviewer and a distinct institutionally accountable approver. They review license, attribution, local analysis, external-model transfer, raw/metadata/derived-schema redistribution, and study-level provider policy for the 25 development/validation dataset records.

Every released assignment now identifies its working-copy and receipt
filenames, required and forbidden actions, return-manifest slot, and exact
validator command. The governance assignment additionally supplies the
validator-controlled approval-generation and approval-replay commands. The
feedback assignment explicitly records that collaborator review is not
independent validation and does not itself authorize test release.
The public preregistration source package now contains both released-task
validators and is machine-checked for closure over every repository-local
Python import. Pinned runtime and development requirements are included, while
environment, external-service, hardware, and backend reproduction remain
separate unresolved obligations.
Each released assignment also has a deterministic least-access packet
specification. Packets must be materialized outside the repository from the
public source base plus only the matching wrapper, payload, and released
inputs; exact-file validation and sealed-ID/title scanning precede
distribution. The completed-roster validator must then replay that live packet
root and both distribution receipts, bind the correct packet-manifest digest
to each of the five role slots, and verify validation, assignment, delivery,
acceptance, and roster-freeze order. No real packet receipt, delivery
attestation, reviewer identity, or completed roster currently exists, so this
implemented binding gate has not yet been satisfied operationally.

The repository currently contains no completed human decision, signature, date, or reviewer identity.

### 8.2 Vocabulary freeze order

Vocabulary is no longer frozen through one review. The workflow is:

1. two independent reviewers complete full-corpus discovery;
2. the validator checks both submissions and the operator atomically freezes their hashes;
3. the system constructs the deterministic union of proposals;
4. a fresh reviewer pair decides every candidate and policy;
5. disagreement is revealed only after both decisions are frozen;
6. a fresh adjudicator resolves disagreements;
7. the validator replays the entire chain and generates the frozen vocabulary.

This reduces proposal-ownership bias, recall bias, cross-review contamination, and the possibility of manually fabricating a `passed` or `frozen` status.

## 9. Stronger statistical plan

The previous PDF required paired per-dataset effects and confidence intervals but did not yet have an external opportunity count. The visible validation set now contains only:

- six semantic resource cases from five dataset clusters;
- four CPA candidate cases from three dataset clusters.

Development and validation semantic/CPA results are therefore preregistered as descriptive feasibility evidence. They cannot support confirmatory superiority, and a null result cannot support a claim of no effect.

The plan freezes:

- two co-primary paired contrasts;
- equal-weight dataset-level effects;
- a two-sided paired sign-flip test;
- Holm correction across the two primary p-values;
- a 10,000-replicate dataset bootstrap interval;
- explicit missingness, failure, abstention, and OOV denominators;
- `null`, rather than zero risk, when the selective-risk denominator is zero.

Under the worst-case Holm threshold of 0.025, at least seven nonzero dataset pairs are required for that p-value to be attainable. This is only a discrete-test resolution floor, not sufficient power. Before test execution, non-blind calibration must freeze the minimum meaningful effect, paired-difference variability, target power, and opportunity assurance. If comparable opportunities are insufficient after test opening, the result must remain underpowered; additional datasets cannot be selected.

## 10. Test safety boundary

All 25 test datasets remain unopened. Before test release, the project must freeze:

- vocabulary and source approvals;
- independent semantic gold;
- prompts, serialization, row samplers, and demonstrations;
- model, checkpoint/runtime identity, decoding, and backend registry;
- data-transfer and artifact-release policy;
- power plan, analysis code, and missingness rules;
- distinct study-operator and independent-monitor signatures.

After test execution begins, the study may not:

- add datasets or replace failures;
- change prompts, backends, samplers, parsers, or analyses in response to outcomes;
- delete abstentions, missing cases, or failures;
- promote pilot or sensitivity findings to confirmatory claims.

Every case-by-arm cell must retain content-addressed raw response, parsed output, score, failure/deviation record, and validator replay.

## 11. What remains unchanged

The update preserves the central principles of the previous PDF:

- the deterministic extractor retains authority over physical schema;
- the semantic layer may propose only evidence-bound claims for existing fields;
- confidence cannot substitute for evidence;
- evidence identity and relevance do not prove semantic truth;
- the B/C causal comparison requires an exactly shared response;
- development data cannot serve as generalization evidence;
- no architecture winner has been established;
- a clean null, an underpowered result, and a bounded compatibility result are all acceptable outcomes;
- NDP-50 does not revise the historical Artifact Paper metrics.

## 12. Current status and next steps

### Completed

- NDP candidate frame, selection, and split are frozen;
- development acquisition and extraction are complete;
- structural validation is complete with a documented deviation;
- semantic opportunities, prediction-neutral packets, and draft source bundles exist;
- CPA design, power feasibility, data-governance audit, human handoff, and test workflows are implemented;
- the current regression suite reports 520 passed tests;
- the initial human-assignment release exists and passes structural validation.

### Current blockers

- data-governance review and accountable approval are incomplete;
- vocabulary discovery A and B are incomplete;
- collaborator sign-off on the complete F01--F16 response is incomplete;
- vocabulary candidate decisions and consensus are not unlocked;
- source bundles cannot yet be approved;
- the semantic-gold annotator pair has not passed the preregistered calibration;
- CPA screening and semantic gold have not been performed;
- prompt, backend, and execution freezes are incomplete;
- the power policy has not been signed or frozen;
- an independently verified immutable OSF/Zenodo preregistration receipt is
  absent;
- semantic validation and test remain unauthorized.

### Recommended near-term sequence

1. Assign and complete the four current human assignments.
2. Validate governance, both vocabulary returns, and collaborator feedback
   sign-off.
3. Atomically freeze the vocabulary-discovery hashes.
4. Generate candidate-decision assignments and obtain decisions from a fresh
   reviewer pair.
5. Complete vocabulary consensus and the validator-generated freeze.
6. Rebuild and independently approve the source bundles.
7. Complete preregistered annotator calibration.
8. Complete CPA applicability and semantic gold in parallel.
9. Freeze the execution configuration and development-only demonstration pool.
10. Complete non-blind calibration and the power freeze.
11. Register the exact public package on OSF/Zenodo and obtain independent
    receipt verification.
12. Authorize the sealed test only after every gate and independent signature
    passes.

## 13. Conclusion

The central change since the previous PDF is not merely that another dataset was run. The update turns blind external evaluation from principles and placeholders into a real, replayable, stoppable NDP-50 research system.

The plan materially improves external validity, denominator discipline, reviewer independence, data governance, statistical conclusion validity, and test-leakage control. Those improvements also make the present limits more explicit: structural validation now has real results, but semantic accuracy does not yet have valid human gold, the test split remains sealed, and any architecture-superiority claim must wait for the complete freeze and authorized evaluation.

## 14. Primary supporting artifacts

- `paper/build/semantic_architecture_study_en.pdf`
- `docs/ndp50_protocol_v1.md`
- `docs/ndp50_development_notes_v1.md`
- `docs/ndp50_structural_validation_report_v1.md`
- `docs/ndp50_semantic_cpa_protocol_v1.md`
- `data/experiments/ndp50_v1/semantic/human_handoff_v1.json`
- `data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_release_v1.json`
- `data/experiments/ndp50_v1/semantic/readiness_report_v1.json`
