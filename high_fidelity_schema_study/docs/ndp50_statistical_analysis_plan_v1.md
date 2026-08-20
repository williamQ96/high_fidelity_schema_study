# NDP-50 statistical analysis plan v1

Date: 2026-07-27  
Status: pre-outcome draft; requires methods-review sign-off and a frozen power
artifact before test release  
Scope: NDP-50 semantic-architecture contrasts only

## 1. Purpose and authority

This plan makes the NDP-50 estimand, inferential target, assumptions, and
reporting rules explicit before semantic validation or test outcomes are
observed. It does not authorize semantic execution or opening the sealed test
split.

The machine-readable authority for design v1 is
`data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json`, currently bound
at SHA-256
`0313d5fee93c03b693cf8962ad9406e77b3f86e004c7d916d810c0bf7a791840`.
The registered test implementation is `ndp50_test_inference.py`. A completed
execution freeze and power freeze must bind the exact design and implementation
hashes used at test time.

`docs/semantic_blind_inference_protocol_v1.md` describes the earlier generic
A/B/C/D study. Its paired-t primary analysis does not govern NDP-50. NDP-50
uses the named arms and sign-flip procedure specified here and in the
machine-readable NDP-50 design.

## 2. Inferential population and claim boundary

The NDP-50 selection deliberately oversamples supported tabular and
hierarchical formats, caps organizations, and fixes format-stratum quotas. The
equal-weight dataset estimand therefore targets the **protocol-defined,
quota-weighted NDP-50 test design**, not the prevalence-weighted NDP Central
Catalog and not scientific datasets generally.

The 25 sealed test datasets are the maximum selected test sample. Multiple
resources, fields, and property slots within one NDP dataset remain clustered
inside that dataset and never increase the primary independent-unit count.

Permitted population language:

> Under the frozen NDP-50 quota and organization-cap design, the mean
> dataset-level paired difference was ...

Prohibited population language:

> The effect across the complete NDP catalog, all repositories, or all
> scientific datasets was ...

Any broader transport claim requires a separately justified sampling or
replication study.

## 3. Conditions and co-primary contrasts

The three confirmatory conditions are:

1. `deterministic_only`;
2. `zero_shot_dataset_level`;
3. `zero_shot_byte_identical_response_plus_deterministic_verification`.

The two and only two co-primary contrasts are:

| Contrast ID | Arm A | Arm B | Direction |
| --- | --- | --- | --- |
| `deterministic-vs-zero` | deterministic only | dataset-level zero-shot | B minus A |
| `zero-vs-verified` | dataset-level zero-shot | byte-identical replay plus deterministic verification | B minus A |

The second contrast is valid only when the verified condition consumes the
exact raw response bytes from the zero-shot condition and makes zero new
semantic-generation calls.

Few-shot prompting, demonstration count, prompt wording, row sampling, domain
transfer, evidence-free calls, heuristic comparators, learned CTA/CPA systems,
and additional model families are not members of this confirmatory family in
design v1.

## 4. Primary endpoint and estimand

For dataset \(i\), condition \(a\), and the frozen set of
gold-`applicable_known` property slots:

\[
Y_{ia} =
\frac{\text{exactly correct accepted claims}_{ia}}
     {\text{gold-applicable-known slots}_{i}}.
\]

For contrast \(c=(a,b)\), the paired dataset effect is
\(D_{ic}=Y_{ib}-Y_{ia}\). The estimand is the equal-weight arithmetic mean of
the comparable dataset effects:

\[
\Delta_c = \frac{1}{n_c}\sum_{i=1}^{n_c}D_{ic}.
\]

Resource cases are pooled within their parent dataset before \(Y_{ia}\) is
calculated. A dataset with more resources or slots therefore receives no more
primary weight than another dataset.

Abstention, OOV prediction, transport failure, timeout, and parser failure
remain incorrect/no-accepted-claim outcomes in the registered denominator when
gold and arm comparability are otherwise valid. They are not silently deleted.

## 5. Primary hypothesis test

For each contrast, the primary p-value is a two-sided paired sign-flip test of
the observed mean dataset-level difference:

- nonzero pair count at most 24: enumerate all sign patterns exactly;
- nonzero pair count above 24: use 1,000,000 fixed-seed Monte Carlo sign
  patterns;
- Monte Carlo p-values use the plus-one numerator and denominator correction;
- exact zero differences remain in the reported total pair count but do not
  increase the effective sign-pattern count.

The two raw p-values are adjusted with Holm's step-down procedure at familywise
alpha 0.05.

### 5.1 Assumption and interpretation boundary

A sign-flip p-value is justified by sign exchangeability of the paired
dataset-level differences under its null (commonly operationalized as a
distribution symmetric about zero). It is not a distribution-free test of the
mean-null for every possible asymmetric difference distribution.

Consequently, the publication must:

- state the sign-exchangeability assumption;
- show the complete paired-difference distribution, including ties and
  influential cases;
- report the mean effect independently of the test decision;
- avoid translating failure to reject into evidence of no mean effect;
- downgrade the p-value to a sensitivity result if diagnostics reveal severe
  asymmetry or a few cases determine the sign pattern.

The design's paired-t calculation is a **power-planning approximation only**.
It is not an alternative primary test and cannot replace the registered
sign-flip result after outcomes are visible.

## 6. Interval and descriptive distribution

For each contrast, report:

- the mean paired effect;
- median, minimum, maximum, standard deviation, and every dataset-level paired
  effect;
- a fixed-seed 10,000-repetition percentile bootstrap interval obtained by
  resampling whole datasets;
- the comparable and noncomparable dataset counts and every exclusion reason.

The bootstrap interval describes uncertainty under whole-dataset resampling of
the selected quota-weighted sample. Because the design uses fixed stratum
quotas and an organization cap, this interval is not a design-weighted
prevalence interval for the complete NDP catalog. It must not be described as
one.

If fewer than two comparable datasets are available, the interval is
undefined. Undefined intervals and metrics are emitted as `null` with the
reason and denominator, not as zero.

## 7. Multiplicity and decision rule

The confirmatory Holm family contains exactly two p-values. No secondary,
diagnostic, model-family, CTA/CPA-only, cost, calibration, AURC, or agreement
metric enters that family.

A contrast may be described as showing evidence against its registered null
only when all of the following hold:

1. the raw and Holm-adjusted p-values are available;
2. the Holm-adjusted p-value is at most 0.05;
3. the frozen comparable-opportunity requirement is met;
4. replay, gold, arm, and execution comparability checks pass;
5. the direction, magnitude, interval, and assumption diagnostics are
   reported.

Statistical significance alone does not establish practical importance,
trustworthiness, or generality. The two contrasts yield separate component
attributions; there is no post hoc omnibus “architecture winner” rule.

## 8. Missingness, exclusion, and noncomparability

Pre-outcome exclusions are limited to the frozen rules:

- CPA-inapplicable cases are excluded from the CPA estimand and reported by
  reason;
- missing or invalid gold blocks the case before model execution;
- a pair requires both registered arms and identical registered denominators;
- a B/C replay mismatch or any new C semantic-generation call invalidates that
  contrast;
- post-outcome case deletion or hand-selected replacement is forbidden.

Every selected test dataset must appear in the disposition flow. Every
semantic-opportunity dataset must appear in each registered contrast as either
comparable or noncomparable. Failures, abstentions, and zero denominators are
reported separately so that operational failure cannot disappear inside an
accuracy average.

## 9. Secondary and selective-prediction measures

Secondary reporting includes coverage, selective risk, unsupported-claim rate,
evidence-reference validity, micro/macro/per-label F1 with support, OOV rate,
and resource use.

For risk--coverage analysis:

- freeze the confidence source and interpretation for every arm;
- require `confidence_score` in `[0,1]` for every accepted prediction and
  `null` otherwise;
- score exact canonical correctness only on gold-applicable-known slots;
- report each arm-by-label group separately and never pool confidence across
  labels or arms;
- publish fixed-decile support, mean confidence, and empirical accuracy for
  every nonempty bin;
- publish Brier score and fixed-decile ECE only when an arm-by-label group has
  at least 30 accepted predictions; otherwise emit `null` for those summaries
  and `insufficient_support_no_calibration_claim`;
- order whole confidence tie groups, use the registered right-continuous
  curve, and report achieved minimum and maximum coverage;
- show the curve and label-specific support, not AURC alone;
- integrate AURC only over achieved coverage;
- treat AUGRC as descriptive unless a versioned scorer and endpoint are frozen
  before outcomes.

Confidence is neither evidence nor verification. A deterministic support score
may be useful for ordering but must not be described as a calibrated
probability unless its frozen arm declaration says
`probability_of_exact_correctness` and the support gate passes. No selective or
calibration metric may replace the primary endpoint because it ranks the
conditions more favorably.

## 10. Agreement, cost, and failures

Inter-annotator agreement is measured before consensus and is not a model
endpoint. Report exact agreement counts/rates, marginal tables, Cohen's kappa
when defined, evidence-identity agreement separately, missing/invalid
submissions, disagreement counts, and reconciliation counts. Agreement does
not prove label validity.

Resource reporting must include successful and failed physical calls, retries,
input/output tokens, model latency, end-to-end latency, configured prices,
effective architecture cost, runtime, and hardware. A replayed response has
zero new-generation cost but retains its explicitly attributed upstream cost.
The completed execution freeze must bind the currency, price basis, effective
date and source, exact per-call and per-million-token rates, whether local
compute is monetized, inclusion of failed/retried/reused calls, and the exact
backend registry record supplying hardware/runtime identity. Score artifacts
use separate `failed_model_calls`, `retry_count`, `model_latency_seconds`, and
`end_to_end_latency_seconds` fields. The inference artifact must aggregate
these fields without silently replacing missing telemetry with zero. Costs
under a `local_compute_not_monetized` basis are reported as zero USD together
with the frozen non-monetization boundary, not as evidence of zero resource
consumption.

## 11. Power and underpowered outcomes

Before development calibration outcomes are inspected, the study operator and
a distinct independent methods reviewer must sign:

- minimum meaningful mean paired effect and rationale;
- target power;
- paired-difference SD floor and inflation;
- Holm-aware planning threshold;
- selective-risk safety bound;
- opportunity assurance and sensitivity scenarios.

The completed power freeze uses development-only calibration. Seven nonzero
pairs are merely the discrete resolution floor for a two-sided p-value at
0.025, not proof of adequate power. If the frozen comparable-opportunity
requirement is missed after test release, the registered result is reported as
underpowered or nonanalysable. No dataset, prompt, model, arm, or metric may be
added to rescue it.

## 12. Mandatory publication table

For each co-primary contrast, the final paper must expose at least:

| Field | Required |
| --- | --- |
| Eligible / comparable / noncomparable datasets | Yes |
| Noncomparability reasons | Yes |
| Mean, median, SD, range of paired effects | Yes |
| Raw sign-flip p-value and exact/Monte Carlo mode | Yes |
| Holm-adjusted p-value | Yes |
| Bootstrap interval and repetitions | Yes |
| Frozen required and realized opportunity count | Yes |
| Effect direction and practical interpretation | Yes |
| Assumption/diagnostic qualification | Yes |
| Calls, tokens, latency, cost, and failures | Yes |

Null, negative, underpowered, and nonanalysable outcomes remain publishable
study outcomes and must not trigger an unregistered rescue analysis.

## 13. Freeze checklist

This plan is ready to become binding only after:

- an independent methods reviewer accepts the estimand and sign-flip
  assumption boundary;
- the completed power policy and power freeze are content-addressed;
- the execution freeze binds the exact inference implementation;
- the public preregistration package binds this plan's hash;
- the F01--F16 collaborator sign-off replays without an independence claim;
- a sealed-identity leakage check passes;
- an independent non-developer/non-collaborator verifies that the immutable
  external registration receipt binds the exact manifest and predates test
  release.
