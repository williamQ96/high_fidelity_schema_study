# NDP-50 feedback-improvement amendment v1

Date: 2026-07-27  
Status: pre-freeze decision record; no test authorization  
Applies to: `docs/ndp50_protocol_v1.md`,
`docs/ndp50_semantic_cpa_protocol_v1.md`, and the semantic-architecture
manuscript

## 1. Relationship to the current NDP-50 update

This document incorporates Swathi's Phase 1 feedback into the latest NDP-50
research plan without mutating the existing content-addressed design artifacts.
The current NDP-50 workflow remains the experimental backbone:

- 50 selected datasets: 15 development, 10 validation, and 25 sealed test;
- dataset as the primary statistical unit;
- deterministic-only, dataset-level zero-shot, and byte-identical
  response-plus-verification as the core attribution chain;
- independently produced human labels and explicit consensus;
- test execution blocked until governance, execution, power, and release gates
  pass.

The feedback adds publication positioning, claim discipline, literature
coverage, metric cautions, and explicit decision gates. It does not authorize
semantic validation or test opening.

The NDP direction is supported by archived collaborator correspondence, but
the exact 50-record sample and 15/10/25 split are investigator-defined protocol
choices rather than a documented verbatim request from Swathi. The evidence
boundary and permitted attribution are frozen in
`docs/ndp50_scope_provenance_v1.md`.

## 2. Amendment classification

### 2.1 Immediate, non-design changes

The following changes do not alter arms, data, estimands, or test procedures:

1. position the work as evaluation methodology spanning selective prediction,
   attributed generation, and controlled component ablation;
2. define Model Capability Debt as a project-specific form of ML technical debt;
3. replace broad causal language with controlled component-attribution language;
4. add Doduo, ArcheType, Korini--Bizer CPA, AutoDDG, Sculley et al., Traub et
   al., Sainz et al., Berzak et al., Menick et al., and FrugalGPT to the scoped
   literature map;
5. state that citation identity and relevance do not prove entailment;
6. state that human consensus is a reference standard, not a human upper bound;
7. make collaborator and independent-review roles disjoint;
8. require a public, time-stamped preregistration receipt before test release.

### 2.2 Clarifications to existing executable requirements

These items are already substantially present and are now made explicit for
publication:

- resource reporting includes successful and failed physical calls, input and
  output tokens, model latency, end-to-end latency, retries, configured price,
  effective architecture cost, runtime, and hardware context. Before
  execution, the freeze must bind the price basis, effective date and source,
  exact per-call and per-million-token rates, currency, whether local compute
  is monetized, treatment of failed/retried/reused calls, and the exact backend
  registry record. Test-score records must use distinct
  `failed_model_calls`, `retry_count`, `model_latency_seconds`, and
  `end_to_end_latency_seconds` fields; a single undifferentiated latency or
  post-outcome price lookup is insufficient;
- agreement reporting includes exact counts and rates by decision slot,
  disagreement/adjudication counts, Cohen's kappa when defined, and the reason
  when it is undefined;
- AURC reports the achieved coverage interval, confidence-tie rule, and
  per-property curves rather than appearing as a context-free scalar;
- development and validation evidence remains descriptive unless the
  preregistered inferential requirements are independently met.

### 2.3 Changes requiring a new executable design version

The following cannot be enabled by prose alone:

- evidence-free single-call diagnostic;
- heuristic name/value-only comparator;
- Doduo or ArcheType executable comparator;
- second model-family sensitivity;
- Krippendorff's alpha as a registered gate rather than a descriptive statistic;
- AUGRC as a machine-scored registered endpoint;
- any change to the two co-primary contrasts.

If one is accepted, the study must create `ndp50-cpa-design/v2` or a separately
identified sensitivity protocol. That version must update the arm/condition
registry, missingness rules, metric definitions, call ceiling, power and
multiplicity consequences, runner/parser/scorer qualification, execution
freeze, human handoff bindings, readiness report, and all dependent hashes.

## 3. Optional sensitivity decision gates

### 3.1 Evidence-free single-call diagnostic

Purpose: estimate how much apparent semantic performance comes from parametric
model knowledge rather than approved evidence.

It may proceed only if all of the following are fixed before the affected
outcomes are observed:

- exact information-removal contract, including whether field names, values,
  physical types, title, and vocabulary remain visible;
- same backend, decoding, output schema, call budget, and scorer as the
  evidence-grounded anchor;
- no retrieval or hidden tool access;
- explicit classification as validation-only or descriptive test sensitivity;
- no addition to the co-primary family without revised multiplicity and power;
- reporting that apparent correctness does not establish trustworthy support.

Default decision: **do not include in the confirmatory test matrix**.

### 3.2 Heuristic comparator

Purpose: distinguish gains from generic name/value patterns from gains requiring
dataset-level semantic integration.

Minimum acceptable comparator:

- deterministic, versioned, and trained on no validation/test labels;
- uses only a predeclared subset of field name, physical type, and bounded value
  profile;
- produces the same prediction/abstention states and is scored by the same
  scorer;
- is called a heuristic comparator, never a human upper bound.

Default decision: **optional development/validation diagnostic**.

### 3.3 Second model family

Purpose: assess whether the direction of a component contrast is specific to the
primary backend.

Requirements:

- selected for coverage of a distinct model family before primary outcomes;
- passes the same contract, scope, replay, timeout, telemetry, and context-fit
  qualification;
- identical case inputs, prompt contracts, samplers, response schema, and
  scoring;
- reported as a sensitivity condition with no model shopping and no role in
  replacing an unfavorable primary result.

Default decision: **defer until governance and the primary execution contract
are frozen; include only if resources support complete paired execution**.

### 3.4 Learned CTA/CPA systems

Doduo and ArcheType are meaningful only on cases satisfying their table and
label-space assumptions. They cannot be treated as full-file schema-extraction
baselines. An executable comparison requires:

- a frozen mapping between the NDP vocabulary and the comparator label space;
- identical applicable cases and row/value visibility;
- frozen checkpoints, code commit, environment, and preprocessing;
- separate reporting for CTA and CPA;
- no extrapolation to hierarchical, array, geospatial, or file-level outcomes.

Default decision: **literature comparator now; executable scoped study only in
a separately registered extension**.

## 4. Measurement additions

### 4.1 Primary and secondary hierarchy

The primary NDP-50 outcome remains the within-dataset rate of exactly correct
accepted claims over all gold-applicable-known slots. This endpoint jointly
penalizes wrong claims, failures, and abstentions without using confidence-scale
comparability as an identifying assumption.

Secondary measures include:

- coverage and selective risk;
- unsupported-claim and evidence-reference-validity rates;
- micro-, macro-, and per-label F1 with support counts;
- OOV and explicit-abstention rates;
- calls, tokens, latency, failure surface, and configured cost;
- risk--coverage curves, AURC over achieved coverage, and descriptive AUGRC
  sensitivity after a scorer/version freeze.

AURC and AUGRC must not replace the primary endpoint post hoc. Any ranking
disagreement is reported, not resolved by selecting the favorable metric.

### 4.2 Confidence and calibration

Confidence is an ordering variable, not evidence and not a verification state.
Reports must include:

- confidence-source definition for every arm;
- one validated `confidence_score` in `[0,1]` for every accepted prediction
  and `null` for every nonaccepted slot;
- tie-group counts and the exact right-continuous ordering rule;
- achieved minimum/maximum coverage;
- separate arm-by-property results with no pooling across arms or properties;
- fixed-decile reliability support and empirical accuracy for every
  arm/property group;
- Brier score and fixed-decile expected calibration error only when that group
  has at least 30 accepted applicable-known predictions; below that threshold,
  the bins and support remain visible but calibration claims and the two
  summary scores are suppressed;
- risk--coverage curves formed by whole confidence tie groups and AURC
  integrated only over achieved coverage.

The score is evaluated against exact canonical correctness on
gold-applicable-known slots. It is an arm-specific ordering or probability
claim according to the frozen source declaration; it is never evidence,
verification, or permission to pool incomparable scales.

### 4.3 Human agreement

Before reconciliation, report:

- exact agreement numerator and denominator overall and by property/decision
  slot;
- disagreement rate and missing/invalid submission counts;
- Cohen's kappa with marginal tables, or an explicit undefined status;
- evidence-identity agreement separately from value-label agreement.

Krippendorff's alpha may be added descriptively if the unitization, distance
function, missing-data treatment, and bootstrap method are frozen first.
Neither kappa nor alpha can replace complete disagreement resolution.

## 5. Publication and preregistration gate

Before test release, archive a public registration package on OSF or Zenodo
containing:

- public protocol and this amendment;
- sampling-frame description and split counts without sealed identities;
- hypotheses, estimands, primary/secondary outcomes, and multiplicity policy;
- missingness, exclusion, stopping, and deviation rules;
- power policy and assurance decision;
- artifact manifest containing hashes for code, prompts, schemas, vocabulary,
  backend registry, scorer, and analysis plan;
- contributor roles and conflict declarations;
- a statement that model pretraining exposure cannot be ruled out.

The local hash chain remains the execution authority. The external receipt adds
independent timing and discoverability; it does not replace local replay
validation.

The public text-source package is assembled by
`ndp50_preregistration_package.py` from a sorted allowlist. The builder rejects
path escape, known test-detail directories, non-UTF-8/binary inputs, and exact
sealed test ID/title matches, then emits a deterministic draft manifest.
Passing that check is necessary but not sufficient: indirect re-identification
still requires human disclosure review, and only an immutable external receipt
establishes registration timing.

The publication gate is executable rather than advisory. The neutral workflow
generated by `ndp50_publication_gate.py` binds the response matrix, this
amendment, and the exact public-package manifest. Before `test_ready` may become
true, two separate artifacts must replay:

1. a collaborator sign-off covering F01--F16, explicitly labelled
   non-independent and freezing the default decisions for inactive optional
   sensitivities; and
2. an OSF/Zenodo receipt binding the exact manifest and content digest, checked
   by a non-developer who is neither a project collaborator nor the study
   operator and who attests attachment-hash and indirect-disclosure review.

Neither artifact authorizes test release by itself. The later release still
requires the distinct operator/monitor authorization and validator-generated
release receipt.

These events are implemented as separate lifecycle stages. The bound
collaborator assignment is released with the initial governance and vocabulary
work. External registration is released only after collaborator sign-off,
execution freeze, power freeze, and the pretest assurance gate pass.
Test-release authorization is a third stage that requires the verified
registration receipt. This ordering removes a circular dependency in which
the sign-off and receipt would otherwise be required for `test_ready` while
their human work remained locked until `test_ready`.
The executable field-by-field instructions and exact receipt-generation
command are frozen in
`docs/ndp50_swathi_feedback_signoff_guide_v1.md`.

The submission-ready structure is drafted in
`docs/preregistration/ndp50_osf_zenodo_preregistration_draft_v1.md`. Its
`DRAFT — NOT SUBMITTED OR REGISTERED` status and unresolved fields must remain
visible until an external receipt is actually verified. The public package must
also pass a sealed-identity leakage review.

## 6. Roles and independence

| Role | Permitted responsibilities | Independence restriction |
| --- | --- | --- |
| William / study developer-operator | Architecture, implementation, artifact generation, engineering validation, disclosed operator sign-off | Cannot fill non-developer annotator, adjudicator, methods-reviewer, or test-monitor slots |
| Swathi / postdoctoral research collaborator | Literature review, claim audit, baseline review, protocol critique, manuscript interpretation, amendment sign-off as collaborator | Cannot fill a slot whose validity depends on being blind and independent of project development/review |
| Independent annotators | Prediction-blind applicability and gold submissions | Must be qualified non-developers with conflicts disclosed |
| Fresh adjudicator where required | Resolve only revealed disagreements with evidence and rationale | Must be disjoint from the relevant independent reviewer pair |
| Independent methods reviewer | Review estimand, power policy, and inferential boundaries | Must be non-developer and distinct from the study operator |
| Independent test-release monitor | Verify all pretest gates and witness release | Must be distinct from the operator and cannot have inspected sealed test details |

Authorship or collaboration is compatible with scientific review, but not with
an independence claim that the person no longer satisfies.

## 7. Claim audit checklist

Every paper and report revision must answer:

1. What is the sampling frame and statistical unit?
2. Which result is confirmatory, descriptive, diagnostic, or engineering-only?
3. What exact artifact proves the reported value?
4. Are failures, abstentions, N/A states, and unsupported cases in the correct
   denominator?
5. Does the wording exceed the estimand or the sampled population?
6. Was the comparison registered before the outcome?
7. Are model, architecture, prompt, and evidence effects separated?
8. Is an agreement statistic being mistaken for label validity?
9. Is a citation being used for the claim it actually supports?
10. Could a collaborator role conflict with a claimed independent role?

The auditable application of this checklist is
`docs/semantic_architecture_claim_ledger_v1.md`.

The publication-level statistical interpretation and human-independence
controls are further fixed in:

- `docs/ndp50_statistical_analysis_plan_v1.md`;
- `docs/ndp50_annotation_and_independence_plan_v1.md`;
- `docs/ndp50_power_policy_review_guide_v1.md`;
- `docs/ndp50_methodological_risk_register_v1.md`.

These additions clarify the sign-flip null, the quota-weighted inferential
target, and the requirement that the NDP-50 gold annotator pair pass a
pre-submission-timestamped calibration bound to the final handbook and
vocabulary. They do not fill a human decision or authorize execution.

## 8. Current effect on authorization

This amendment does not change the present gate state:

- structural validation: complete within its declared scope;
- semantic validation: not authorized;
- CPA screening: blocked on approved evidence sources;
- execution freeze: incomplete;
- test split: sealed;
- test execution: not authorized.

No optional sensitivity described above is active until a new machine-validated
design or separate sensitivity protocol says so.
