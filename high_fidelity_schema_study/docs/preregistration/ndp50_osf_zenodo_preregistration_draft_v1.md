# NDP-50 external validation preregistration

**DRAFT — NOT SUBMITTED OR REGISTERED**

Draft date: 2026-07-27  
Planned repository: OSF Registrations or Zenodo  
Registration DOI/immutable receipt: `<UNRESOLVED>`  
Public registration timestamp: `<UNRESOLVED>`  
Protocol version: `ndp50-external-validation-protocol/v1` plus
`ndp50_feedback_improvement_amendment_v1`

## 1. Study title

NDP-50: Replay-Controlled External Evaluation of Evidence-Constrained Semantic
Schema Architecture

## 2. Research status at registration

This registration must be submitted before test identities are expanded into
detail records, before test resources or gold are inspected, and before any test
semantic outcome is observed.

State represented by this draft:

- candidate-frame construction and deterministic selection: complete;
- structural development and validation: complete within the bounded protocol;
- human governance, vocabulary, and collaborator feedback-signoff work:
  released but incomplete;
- approved source bundles: absent;
- independent semantic gold: absent;
- prompt/backend execution freeze: absent;
- power freeze: absent;
- test split: unopened;
- semantic validation and test execution: not authorized.

This draft is not a registration receipt and cannot satisfy the test-release
gate.

The public text-source allowlist is assembled and replayed by
`ndp50_preregistration_package.py`. Its local manifest verifies current file
hashes and rejects exact sealed dataset ID/title matches, but it is neither an
independent timestamp nor an external registration. The immutable external
receipt must bind the resulting public-package manifest hash.

## 3. Research questions

1. What fraction of selected NDP datasets and catalog resources can the
   deterministic schema product acquire and process under the frozen bounded
   policy?
2. Which failures arise from access, packaging, format routing, parser coverage,
   bounded sampling, standards handling, or resource limits?
3. How often do declared catalog properties agree, conflict, remain missing, or
   remain untestable against direct resource observations?
4. On independently annotated semantic-opportunity datasets, what does one
   dataset-level semantic response add beyond deterministic extraction?
5. Holding the raw semantic response byte-identical, what does deterministic
   evidence and conflict verification change?
6. On applicable relational-table cases, how sensitive are CTA/CPA results to
   prompt wording, demonstrations, row sampling, domain, and vocabulary?

Questions 4 and 5 define the two co-primary component contrasts. Question 6 is
descriptive unless a later registered, powered extension explicitly says
otherwise.

## 4. Sampling frame and selection

The sampling frame is a complete lightweight capture of the NDP Central Catalog
at the frozen capture time:

- 5,823 selection-eligible dataset records;
- 75 organizations;
- candidate-frame SHA-256:
  `96dd37f89cbc34a5deb219acb636a8b643ba141bf07f62f70508fd090d91822f`.

The selected study sample contains 50 dataset records:

- development: 15;
- validation: 10;
- sealed test: 25.

The NDP study direction originated in collaborator discussion. The exact
50-record sample, 15/10/25 split, quota design, estimands, and inference are
investigator-defined protocol choices, not a documented verbatim instruction
from the collaborator. The attribution boundary is recorded in
`docs/ndp50_scope_provenance_v1.md`; it does not itself establish sample-size
sufficiency or collaborator approval.

Selection is stratified by declared/inferred primary format class, uses a frozen
organization cap, and orders candidates through seed-derived SHA-256 priority.
Split assignment uses a separate deterministic priority. Selection artifact
SHA-256:
`27d73de3b4aa8638616588fdac0d927d79321d7d230d2c55f96c952689bd471d`.

The public registration contains counts and hashes, not sealed test dataset
identities.

The sample is not claimed to represent all NDP records over time, all scientific
data, or all repositories.

## 5. Unit of analysis and clustering

The primary statistical unit is the NDP dataset. Resources, columns, fields, and
property slots within the same dataset are clustered and are not treated as
independent observations. Registered slots are pooled within each dataset and
arm before one dataset-level score is computed.

## 6. Conditions

### 6.1 Co-primary conditions

1. `deterministic_only`: parser-owned schema and deterministic claims; no
   semantic model call.
2. `zero_shot_dataset_level`: deterministic extraction plus at most one
   dataset-level semantic response for unresolved targets.
3. `zero_shot_byte_identical_response_plus_deterministic_verification`: consumes
   the exact raw response from condition 2, applies deterministic verification,
   and makes zero new semantic calls.

The registered contrasts are:

- `deterministic-vs-zero`;
- `zero-vs-verified`.

The B/C contrast is invalid if replay identity fails or the verified condition
makes a new semantic generation call.

### 6.2 Descriptive conditions

The current design includes one- and five-shot development-only
similarity-selected demonstrations, prompt variants, and head/fixed-seed
stratified/fixed-seed adaptive row samplers as descriptive sensitivities.

Validation and test cases cannot become demonstrations. Fine-tuning is outside
the primary study.

### 6.3 Inactive proposed conditions

The following are not active in design v1:

- evidence-free single-call diagnostic;
- deterministic name/value heuristic comparator;
- Doduo or ArcheType executable comparator;
- second model-family sensitivity;
- registered Krippendorff-alpha gate;
- registered AUGRC endpoint.

They require a new executable design version or a separately registered
sensitivity protocol before affected outcomes are observed.

## 7. Primary outcome

For each dataset and arm:

1. identify all gold `applicable_known` property slots;
2. count slots with an accepted prediction exactly matching the canonical gold
   value;
3. divide the count by all gold `applicable_known` slots;
4. form the paired `arm_b - arm_a` dataset-level difference.

Primary outcome ID:
`correct_accepted_applicable_claim_rate_gain_per_dataset`.

CPA design SHA-256:
`0313d5fee93c03b693cf8962ad9406e77b3f86e004c7d916d810c0bf7a791840`.

## 8. Secondary outcomes

Secondary reporting includes:

- coverage and selective risk;
- unsupported-claim and evidence-reference-validity rates;
- micro-F1, macro-F1, per-label F1, and label support;
- OOV and explicit-abstention rates;
- exact agreement, disagreement, adjudication/reconciliation counts, and
  Cohen's kappa before consensus;
- physical calls, failed attempts, retries, input/output tokens, model and
  end-to-end latency, configured price, and effective architecture cost;
- per-arm/per-label fixed-decile reliability support, with Brier score and
  fixed-decile ECE only at 30 or more accepted applicable-known predictions;
- whole-confidence-tie-group risk--coverage curves and AURC over achieved
  coverage, without pooling across labels or arms.

AUGRC may be reported only after a versioned scorer and descriptive sensitivity
contract are frozen. No secondary metric may replace the primary endpoint after
outcomes are observed.

## 9. Hypotheses and multiplicity

The two co-primary null hypotheses are sign exchangeability of the paired
dataset-level differences about zero for:

1. deterministic-only versus dataset-level zero-shot;
2. zero-shot versus deterministic verification of the byte-identical response.

Both tests are two-sided. Familywise alpha is 0.05. Holm step-down adjustment is
applied across exactly the two co-primary p-values. The decision basis is the
Holm-adjusted p-value family together with effect size, interval, realized
comparability, and the frozen minimum meaningful effect.

No confirmatory p-value is computed for descriptive sensitivities.

The sign-flip test is not distribution-free for a mean-null under arbitrary
asymmetry. The mean paired difference remains the effect estimand, while the
registered p-value tests its sign-exchangeability null. The complete
paired-difference distribution and assumption diagnostics will therefore be
reported, and failure to reject will not be interpreted as evidence of no mean
effect.

## 10. Primary inference

The primary test is a paired sign-flip test on dataset-level mean differences:

- up to 24 nonzero pairs: exact enumeration;
- above 24 nonzero pairs: 1,000,000 fixed-seed Monte Carlo flips;
- Monte Carlo p-value: plus-one numerator and denominator correction;
- exact zero differences remain in the total pair count but are excluded from
  effective sign patterns.

The 95% confidence interval is a fixed-seed, 10,000-repetition,
dataset-resampling percentile bootstrap for the mean paired difference.

The equal-weight estimand and bootstrap target the protocol-defined,
quota-weighted NDP-50 design. They are not prevalence-weighted estimates or
design-based intervals for the complete NDP catalog. The detailed analysis and
claim boundary are specified in
`docs/ndp50_statistical_analysis_plan_v1.md`.

## 11. Missingness, failures, and exclusions

- Transport, timeout, parser, and explicit abstention/OOV outcomes remain in the
  registered primary denominator as no correct accepted claim.
- Frozen CPA-inapplicable cases are excluded only from the CPA estimand and are
  reported by reason.
- Missing or invalid gold blocks model execution for the affected registered
  case; it is not repaired after model output.
- A dataset pair requires both registered arms and all comparability checks.
- Every exclusion and noncomparability reason is reported.
- Undefined selective risk is `null` with its zero denominator, never recoded as
  zero risk.
- Post-outcome case deletion and hand-selected replacement are forbidden.
- A deterministic reserve may be used only according to a rule frozen before
  outcome inspection.

## 12. Power and stopping

Before test release, the signed power policy must freeze:

- minimum meaningful mean paired effect and rationale;
- paired-difference SD floor and inflation;
- target power;
- Holm-aware planning threshold;
- selective-risk safety bound;
- semantic-opportunity assurance at the fixed 25-dataset test size;
- prespecified sensitivity scenarios.

At least seven nonzero paired differences are required merely for a two-sided
exact sign-flip p-value to reach the conservative `0.025` threshold. This is a
resolution floor, not proof of adequate power.

The pre-outcome decision procedure and independent-review questions are fixed
in `docs/ndp50_power_policy_review_guide_v1.md`; that guide intentionally
selects no numeric policy values.

If the frozen opportunity/comparability requirement is not met after test
opening, the result is reported as underpowered or non-analysable. Additional
datasets, prompts, models, or arms cannot be added to rescue the result.

Completed power-policy hash: `<UNRESOLVED>`  
Completed power-freeze hash: `<UNRESOLVED>`  
Target power: `<UNRESOLVED>`  
Minimum meaningful effect: `<UNRESOLVED>`

## 13. Human annotation and agreement

Prediction-blind human work follows a two-submission workflow:

- qualified non-developer annotators complete independent submissions;
- submissions are content-hashed before disagreement reveal;
- exact agreement and Cohen's kappa are reported by decision slot;
- degenerate kappa is explicitly undefined;
- every disagreement receives a human evidence-backed resolution;
- model outputs remain hidden until gold is frozen.

Human consensus is the reference label process, not a human upper bound.

Before NDP-50 blind gold begins, the exact annotator pair must pass a
preregistered non-NDP calibration round bound to the final handbook and frozen
NDP vocabulary. The passing
`semantic-annotator-calibration-summary/v1` artifact, its external
pre-submission receipt, and the exact annotator identities must be bound by the
release chain. The execution sequence is specified in
`docs/ndp50_annotation_and_independence_plan_v1.md`.

Swathi is an active postdoctoral research collaborator. She may review
literature, protocol, baselines, claims, and interpretation, but cannot occupy a
role requiring blind independence from project development or review.

## 14. Governance

Before semantic execution:

- a qualified data steward/research-compliance reviewer and a distinct
  accountable approver resolve license, attribution, processing, transfer, and
  redistribution policy;
- vocabulary discovery, candidate decisions, and consensus complete under the
  frozen role-separation workflow;
- source evidence is independently approved by allowed purpose;
- independent gold and CPA applicability consensus complete;
- prompt, serialization, samplers, demonstrations, model, decoding, backend,
  parser, scorer, and cost-accounting implementations freeze and qualify;
- the resource-accounting freeze binds currency, price basis, effective date
  and source, exact call/token rates, local-compute monetization boundary,
  treatment of failed/retried/reused calls, separate model and end-to-end
  latency fields, and the selected backend registry record supplying
  hardware/runtime identity.

Public catalog availability is not treated as legal or institutional approval.

## 15. Contamination and validity

The test split is sealed against project-side tuning. Because NDP records and
related public data may have been present in unknown model pretraining corpora,
pretraining contamination cannot be ruled out. The study will not describe the
sealed split as demonstrably uncontaminated.

Other predeclared threats include:

- bounded snapshot and organization-cap external-validity limits;
- mutable remote resources;
- incomplete format support;
- confidence-scale noncomparability across properties;
- evidence relevance without guaranteed entailment;
- label uncertainty despite agreement;
- underpowered semantic-opportunity counts.

## 16. Deviations

Every deviation receives:

- unique ID and timestamp;
- discovery stage and affected artifacts;
- reason and evidence;
- whether outcomes were visible;
- impact on eligibility, comparability, power, and claims;
- signatures and regenerated hashes when permitted.

An explicit empty deviation registry is required if no deviations occur.
Post-outcome changes to hypotheses, primary outcomes, cases, arms, scorers, or
missingness rules are prohibited.

## 17. Reporting commitments

The publication will report:

- dataset and resource flow with every disposition;
- all registered denominators and undefined counts;
- primary effect estimates, intervals, raw and Holm-adjusted p-values;
- realized power/opportunity reconciliation;
- secondary metrics with support;
- successful/failed call, retry, token, model-latency, end-to-end-latency, and
  cost accounting under the frozen price schedule and hardware/runtime scope;
- agreement and reconciliation statistics;
- all deviations;
- the final methodological risk register and residual-risk dispositions;
- negative, null, underpowered, or non-analysable outcomes without rescue
  analyses.

Development, validation, qualification, and test evidence will remain labelled
by their proper role.

## 18. Public artifact bindings

The following hashes are safe to disclose now:

| Artifact | SHA-256 |
| --- | --- |
| Candidate frame | `96dd37f89cbc34a5deb219acb636a8b643ba141bf07f62f70508fd090d91822f` |
| Selection artifact | `27d73de3b4aa8638616588fdac0d927d79321d7d230d2c55f96c952689bd471d` |
| CPA design draft | `0313d5fee93c03b693cf8962ad9406e77b3f86e004c7d916d810c0bf7a791840` |
| Structural validation report | `f8f5d1f160f1a592f7aa30461ca1b830becb6589a34af4cf0e4ba6e973ce063a` |
| Feedback-improvement amendment draft | `f4eb887864614bbf8758db83739e39764c8a979efb6c437e0df90ab60a584bcf` |
| Statistical analysis plan draft | `c690c5389b74e3490772aec437c2597ae117febc584cf1d75eb9477b2d5e9d52` |
| Annotation and independence plan draft | `2c2ace0621a840f1cfb9fce6add6f749a8c55325893e02cff2fa026b7ad7e8c4` |
| Power-policy review guide | `accf7cf54d361ee87e76159e2eced916a06b48178ea97584bb0f4419c4cd5f45` |
| Methodological risk register | `a04a289ef912c009d5e4538c373eef5eb1cc6dcb5ca8fa400232a85193eb1f31` |
| NDP-50 scope/request-provenance record | `065b1af907c41f7dd066c30911eb620d09011d79804a2436fbd29d0dfe9f3cf0` |
| Claim ledger draft | `11bcb975ed528697ee6e9e1796b696e9a31082846920d6acd89a90b142030ee2` |
| Feedback implementation audit | `cdb70d80051075bbbb09ca34e671eb728106e3dabff6c97865f2ed94da3539ff` |
| Human/external gate ledger | `143ad38e8c6def58d818894d5a7c84fda29d0828c8866cd0746de5dbe8b564aa` |
| Initial human-assignment execution guide | `e5a00d6bacd7649555fcee9b0c60e6ea2ead79c7bb9fd4b0e4d842cd74a9b1e8` |
| Semantic annotator-calibration protocol | `c6ef25e9ea48523455ceac748a3ca9bdb0c2434a286f075ea087c3522e067e4c` |
| Semantic-gold workflow protocol | `ee24b9bf6f7424d6f1076c7f3dec82bf9441a3be7f416e1e46668e089790f94b` |
| Semantic power-analysis protocol | `26dd3d1e5353a69f021b5d3dec3622ad2e84ef9b2b34d562199348546d7e5d5a` |
| Swathi feedback sign-off guide | `d5e0e2e212228ae153446bf5c858de0b6fb1dda33c87376741df7597a3941513` |
| Public-package text allowlist | `a4663e8dc8f8a4481e769ca5613f44fcc9b44a3326736b544c63638e0e82ec3e` |
| Public-package builder | `f74a5825d67acbe720303234f2d9030fd059cfc1088429be694b9fb33b42ef0a` |
| Human-assignment generator | `6eeb2b3659784205648196a078e1f200615da602900ab2a4c65bcf1c17bb8973` |
| Assignment-distribution validator | `2a2ecb0e9444fde479a66e7263ebb2b6708b6dd9a3d45dc0afe5396c0d15fae2` |
| Assignment-roster validator | `aa298a58e08ea3e126e2dc450d5b3ea54755f2d0d7e7bfda0d20321d5af85261` |
| Publication-gate validator | `526ec5f4a41e1d9f957ce40da26221e109b0534fd9326b46def9414386b46c42` |
| External receipt neutral template | `5aacdb096019e9676c729685f2220b52908b16a0df3276dbb70a698604b17cfd` |

These are current-snapshot bindings, not the final execution freeze. They must
be refreshed and supplemented at registration.

The generated feedback sign-off neutral artifact is intentionally not
self-bound in this table: sign-off schema v2 binds this preregistration draft
as a review material. The public-package manifest binds both files and supplies
their common acyclic content-addressed envelope.

The live readiness and human-handoff artifacts are intentionally not embedded
in the public package. A real external receipt changes their gate state, so
including their hashes here would create a circular receipt/readiness binding.
After registration, the live readiness report instead binds the immutable
public-package manifest and independently verified receipt from outside the
registered package.

Required unresolved public bindings:

- source commit/tree SHA-256;
- final registered protocol/amendment/analysis-plan SHA-256 values refreshed
  after sign-off;
- final claim-ledger and risk-register SHA-256 values refreshed after
  sign-off;
- frozen vocabulary and handbook SHA-256;
- approved source-manifest SHA-256;
- semantic-gold workflow and approval SHA-256;
- execution freeze and implementation qualification SHA-256;
- backend registry and exact checkpoint SHA-256;
- power policy/freeze SHA-256;
- test-execution workflow SHA-256;
- public preregistration package SHA-256;
- immutable external receipt/export SHA-256 and independently verified public
  URL/DOI.

Sealed identities, test details, gold, and outcomes are excluded from the public
registration attachment.

## 19. Sign-off and registration attestation

Study operator:

- pseudonymous/public ID: `<UNRESOLVED>`;
- qualification and role: `<UNRESOLVED>`;
- conflict/developer disclosure: `<UNRESOLVED>`;
- signed date: `<UNRESOLVED>`.

Postdoctoral collaborator review:

- reviewer ID: `<UNRESOLVED>`;
- review scope: literature, protocol, baselines, claims, interpretation;
- conflict/collaboration disclosure: `<UNRESOLVED>`;
- signed date: `<UNRESOLVED>`.

This review must use
`ndp50-feedback-response-signoff/v2`, cover F01--F16 exactly, bind the complete
review-material list and digest, freeze the
recorded default treatment of inactive sensitivities, and state
`independence_claimed=false`.

Independent external-registration verification:

- reviewer ID: `<UNRESOLVED>`;
- qualification: `<UNRESOLVED>`;
- developer participation: `false`;
- project collaborator: `false`;
- public record, attachment hashes, and indirect-disclosure review:
  `<UNRESOLVED>`;
- verified date: `<UNRESOLVED>`.

Independent methods review:

- reviewer ID: `<UNRESOLVED>`;
- qualification: `<UNRESOLVED>`;
- developer participation: `false`;
- conflict disclosure: `<UNRESOLVED>`;
- signed date: `<UNRESOLVED>`.

Final attestation:

> We attest that the registered public package matches the content-addressed
> local protocol and analysis plan; that no test detail, gold, or outcome was
> observed before registration; that every unresolved placeholder required for
> test release has been replaced by validated evidence; and that the immutable
> external receipt was obtained before the authorized test-opening event.

Attestation status: `<UNRESOLVED — DRAFT ONLY>`
