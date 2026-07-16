# A/B/C/D Development-Harness Validation

> Evaluator-version note (2026-07-15): this report predates the explicit
> equal-weight `dataset_level_comparison` artifact. Its pooled development metrics
> and preserved raw case traces remain historical debugging evidence, but this
> report must not be used as the analysis implementation for blind inference. The
> frozen blind evaluator will report paired per-dataset effects; pooled-slot deltas
> are descriptive only.

Date: 2026-07-14
Decision: **READY TO FREEZE WITH DOCUMENTED LIMITATIONS**

This report validates the experiment, not the superiority of an architecture. The nine cases are synthetic development/regression cases and provide no evidence of external generalization.

## Executive finding

**Fact:** The final harness preserves exactly A/B/C/D. A makes zero model calls; B makes at most one dataset-level call per case with a semantic target; C generates no new response and replays B byte-for-byte; D preserves the historical field/manual-group scheduler and non-empty evidence-string merge behavior.

**Observation:** All nine B/C replay records passed identity checks. The two cases with semantic targets have matching B/C SHA-256 response hashes, matching raw content, and `C semantic generation calls = 0`. Seven cases had no semantic target and therefore no B/C response.

**Observation:** The development manifest cannot support a valid architecture ranking. Only 2/9 cases contain any dataset-level semantic target. One of those targets (`/campaign/meta/platform`) is absent from gold, and Qwen violated the target contract on that case. Consequently A-vs-B, B-vs-C, and C-vs-D are all correctly reported as non-comparable.

**Inference:** The harness now fails visibly on the defects that would invalidate a blind result. The development outputs do not estimate the contribution of dataset-level reasoning or verification: B produced no accepted, scorable semantic claim, so the B/C verifier had no assertive claim on which to operate.

## Evaluator invariant table

| Invariant | Intended behavior | Final implementation | Match | Protected by |
| --- | --- | --- | :---: | --- |
| A call boundary | Always zero model calls | A never receives or invokes a backend | Yes | `test_architecture_call_counts_and_shared_contract` |
| B call boundary | At most one generation call per dataset | B accepts 0 calls when no targets and exactly 1 otherwise; any backend telemetry above 1 makes the run partial | Yes | call-count and retry-count tests |
| C generation boundary | No new semantic generation | C requires an in-run B replay and reports 0 generated calls | Yes | call-count and C-without-B tests |
| B/C identity | Exact same semantic response | Raw content and SHA-256 response hash are persisted and compared per case | Yes | shared-contract and tamper tests |
| B/C failure replay | C must not retry a failed B request | Failures are memoized; C replays the failure with zero calls | Yes | timeout/failure-cache test |
| C-only execution | Missing B replay must not silently degrade | Requesting C without B raises before execution | Yes | missing-replay test |
| C causal boundary | C differs only through deterministic verification | Same parsed response; no verifier model call | Yes | replay provenance plus call tests |
| Abstention monotonicity | Verification cannot promote model abstention | `unknown`/empty candidates remain abstained and unverified | Yes; blocking defect fixed | abstention-promotion regression test |
| Confidence boundary | Confidence is ordering metadata, not verification | Confidence 0 can pass evidence checks; confidence 1 cannot rescue unsupported evidence | Yes | confidence 0/1 tests |
| Evidence identity | Nonexistent IDs cannot verify | C abstains and marks `unsupported` | Yes | nonexistent-ID test |
| Evidence existence | Empty evidence cannot verify | C abstains and marks `unsupported` | Yes | empty-evidence test |
| Field relevance | Existing cross-field or non-field spans cannot verify | Evidence ID must list the claim field in `applicable_field_paths` | Yes | irrelevant-evidence and wrong-span tests |
| Semantic entailment boundary | C must not claim truth verification | Valid field-relevant references yield only `evidence_grounded/supported` | Yes | state assertions and report policy |
| Deterministic contradiction | Conflicting deterministic value must reject | C marks `contradicted/rejected` | Yes | contradiction test |
| Cross-claim conflict | Incompatible logical/semantic claims must not both pass | C abstains both using the existing compatibility map | Yes | mutually-conflicting-claims test |
| Malformed output | Must fail closed | Invalid top-level/claim shapes produce a partial deterministic fallback | Yes | malformed and partial-output tests |
| Duplicate claims | Must not become order-dependent accepted output | Any duplicate makes B/C partial | Yes | duplicate test |
| Applicable value | Abstention is not an incorrect prediction internally, but lowers end-to-end accuracy | End-to-end accuracy uses all applicable-value slots; selective risk conditions on accepted predictions | Yes | zero/all-accepted tests |
| Applicable unknown | Must not collapse into N/A | Explicitly applicable unknown rewards abstention and has its own denominator | Yes | applicable-unknown test |
| N/A | Must not enter applicable-value denominator | Explicit/inferred N/A is scored only for N/A false positives | Yes | N/A test |
| Gold scope | Missing gold field is not automatically N/A | Task-field predictions outside an open-world gold list are counted but not scored | Yes; blocking defect fixed | open-world-gold test |
| Target coverage | Every semantic opportunity used for comparison must be scorable | Unscored target paths are reported and make B/C/D architecture comparisons non-comparable | Yes; blocking defect fixed | unscored-target test |
| Unsupported rate | Deterministic evidence must not dilute model trust metrics | Proposed-model and accepted-model unsupported rates are reported separately | Yes | unsupported-evidence tests |
| AURC ordering | Ties must not depend on arbitrary claim order | Whole confidence tie groups form right-continuous risk steps | Yes; ambiguity fixed | tied-confidence test |
| AURC denominator | Abstentions must not be silently converted into errors | AURC is integrated only over achieved coverage; end-to-end accuracy separately accounts for abstention | Yes | zero-accepted and tie tests |
| Model retry accounting | Hidden retries must not preserve B comparability | More than one B generation call makes B partial | Yes | retry-count test |
| Token/failure accounting | Failed fallback attempts must retain usage | D accumulates calls, tokens, latency, and failed attempts across both legacy attempts | Yes; defect fixed | legacy-fallback telemetry test |
| C resource accounting | Zero generated calls must not imply zero architecture cost | Reports generated, reused-upstream, and effective-architecture telemetry separately | Yes; defect fixed | shared-contract resource assertions |
| D fidelity | Preserve historical scheduling/merge contract | Historical free JSON then schema fallback, temperature 0.2, max 1000, and non-empty evidence merge are retained | Yes | legacy fallback and behavior tests |
| Comparability | Partial/replay/design failures must block deltas | Pairwise deltas are emitted only when both sides are comparable | Yes | missing replay, malformed, target-coverage tests |

## Adversarial validation

All requested adversarial conditions are covered by focused tests:

| # | Condition | Expected protected inference | Result |
| ---: | --- | --- | :---: |
| 1 | Nonexistent evidence identifier | C cannot manufacture verification | Pass |
| 2 | Existing but field-irrelevant evidence | Identity alone is insufficient | Pass |
| 3 | Correct document, wrong span | Document identity cannot substitute for field relevance | Pass |
| 4 | Contradictory deterministic evidence/value | C rejects deterministic conflict | Pass |
| 5 | Empty evidence | C abstains | Pass |
| 6 | Confidence 0 with assertion | Confidence does not veto verification | Pass |
| 7 | Confidence 1 with unsupported evidence | Confidence does not establish verification | Pass |
| 8 | Malformed model output | B/C fail closed and become non-comparable | Pass |
| 9 | Duplicate claims | No order-dependent projection | Pass |
| 10 | Mutually conflicting claims | C abstains incompatible pair | Pass |
| 11 | N/A marker with an applicable value | Contradictory gold is rejected | Pass |
| 12 | Applicable property incorrectly collapsed to N/A | `applicable_unknown` is separate | Pass |
| 13 | Missing B/C replay | C-only is rejected; failed B is not retried | Pass |
| 14 | Different B/C responses | Hash/content mismatch invalidates both sides | Pass |
| 15 | Backend retry raises B call count | B becomes partial | Pass |
| 16 | Partial model output | Response is fail-closed | Pass |
| 17 | Timeout | One physical attempt; C replays failure | Pass |
| 18 | Zero accepted claims | No divide-by-zero; achieved coverage is zero | Pass |
| 19 | All applicable claims accepted | Coverage/risk endpoints are correct | Pass |
| 20 | Tied confidence | AURC is order-independent | Pass |

Additional tests cover legacy fallback token/failure accounting, abstention monotonicity, open-world gold scope, effective C resource accounting, and semantic-target gold coverage. The focused harness suite contains 31 tests.

## LM Studio backend configuration

| Item | Value |
| --- | --- |
| Endpoint | `http://127.0.0.1:1234/v1` |
| Model returned by `/models` | `qwen/qwen3.5-9b` |
| External paid API | None |
| Timeout | 180 seconds |
| B/C decoding | temperature 0; seed 0; max tokens 4096; thinking disabled; strict JSON schema |
| D decoding | temperature 0.2; no added seed; max tokens 1000; thinking disabled; historical free-JSON then JSON-schema fallback |
| Configured price | USD 0 for local input/output tokens |
| Physical execution | 5 backend invocations, 8 HTTP model calls |

D scheduled three semantic groups. Each free-JSON attempt was unusable, so all three used the historical schema fallback: 6 calls total and 3 recorded failed attempts. Raw responses, parsed responses, evidence, hashes, decisions, tokens, latency, errors, and replay provenance are retained in `report.json`.

## Development results

These aggregates are descriptive diagnostics only. B/C/D are non-comparable because the development manifest has an unscored semantic target; B/C additionally have one partial case.

| Variant | Comparable | End-to-end accuracy | Coverage | Selective risk | AURC | Model claims accepted / proposed | Generated / reused / effective calls | Effective tokens in/out | Effective model latency |
| --- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | Yes | 0.976608 | 0.988304 | 0.011834 | 0.014603 | 0 / 0 | 0 / 0 / 0 | 0 / 0 | 0 ms |
| B | No | 0.976608 | 0.988304 | 0.011834 | 0.014603 | 0 / 1 | 2 / 0 / 2 | 5752 / 381 | 4128.415 ms |
| C | No | 0.976608 | 0.988304 | 0.011834 | 0.014603 | 0 / 1 | 0 / 2 / 2 | 5752 / 381 | 4128.415 ms |
| D | No | 0.988304 | 1.000000 | 0.011696 | 0.014705 | 4 / 4 | 6 / 0 / 6 | 7538 / 3598 | 22171.453 ms |

All nine per-case replay provenance records passed. More precisely, the two actual B responses had byte-identical C inputs and matching hashes:

- `csv_hard_field_campaign`: `3b7cd63a800a596c1dc63d8070154aa786449324f25d57a4cecbea1f23c0dbf5`
- `hdf5_hard_ocean_profile`: `eb4093d50a904ead57b1f892e667a2d3e9a7a4a85776bb369ca738110c372460`

The other seven cases had no semantic targets and correctly made no B/C call. The harness reports eight accepted deterministic predictions for task fields outside the open-world gold scope; they are observable but no longer misclassified as N/A false positives.

## Per-case traces and failure taxonomy

| Case | Deterministic observation | B semantic result | C verification | D legacy result | Gold/evaluation outcome | Failure classification |
| --- | --- | --- | --- | --- | --- | --- |
| `csv_easy_weather_stations` | No unresolved semantic target | No call | No call | No call | `elevation_m`: physical `int` vs `float`; logical `coordinate` vs `measurement` | Primary: deterministic extraction miss (2) |
| `csv_hard_field_campaign` | `zc.logical_type`; `val.logical_type` and semantic type unresolved | One call; only `zc.logical_type=unknown`, explicit abstention; omitted `val` claim | Exact replay; abstention remains abstention | Four calls after two fallbacks; accepted `zc` identifier/postal code and `val` measurement | A/B/C miss two applicable logical values; D fills both correctly | Primary: semantic reasoning miss; contributing: small-model conservative/instruction-following limitation |
| `csv_medium_water_quality` | No unresolved semantic target | No call | No call | No call | No scored error | None |
| `hdf5_easy_climate_cube` | No unresolved semantic target | No call | No call | No call | No scored error | None |
| `hdf5_hard_ocean_profile` | Only target is `/campaign/meta/platform.semantic_type`; target absent from gold | One call; emitted unit claims for two resolved, non-target fields; entire response failed closed | Exact replay; same partial state, zero generation calls | Two calls after fallback; accepted platform logical identifier | Model target is unscorable; B/C contract failure; D platform change is also unscorable | Primary: prompt/contract compliance failure; contributing: small-model capability limitation and development-gold coverage defect |
| `hdf5_medium_station_hierarchy` | No unresolved semantic target | No call | No call | No call | No scored error | None |
| `ts_easy_hourly_weather` | No unresolved semantic target | No call | No call | No call | No scored error | None |
| `ts_hard_irregular_buoy` | No unresolved semantic target | No call | No call | No call | No scored error | None |
| `ts_medium_power_meter` | No unresolved semantic target | No call | No call | No call | No scored error | None |

No development failure was classified as unsupported semantic claim, evidence identity failure, evidence relevance failure, conflict-resolution failure, N/A handling error, legacy merge defect, or infrastructure failure. This is absence of exposure, not evidence those failure modes are rare.

## Causal comparisons

### A vs B

**Formal status: not comparable.** B had one partial case, and one of the two semantic-opportunity cases contains an unscored target.

Descriptively, B added 0 accepted correct claims, 0 accepted incorrect claims, 0 coverage, and 0 selective-risk change. It added two effective calls, 5752 input tokens, 381 output tokens, and 4128.415 ms of model latency. On the only complete and fully scorable opportunity case, B recognized the issue but abstained on `zc` and omitted `val`; this is a semantic reasoning miss under Qwen3.5 9B, not evidence that dataset-level reasoning has no value.

### B vs C

**Formal status: not comparable, although replay identity is valid.** Generation was held constant exactly, but B supplied no accepted model assertion on which verification could act.

The observed verification tradeoff is therefore all zero: B-accepted/C-rejected 0; B-accepted/C-abstained 0; incorrect claims removed 0; correct claims lost 0; unsupported claims removed 0; coverage change 0; selective-risk change 0. This is an uninformative contrast, not a clean null effect. The adversarial tests, rather than these nine cases, establish that C changes decisions when identity, relevance, or conflict checks fail.

### C vs D

**Formal status: not comparable.** C is partial on one case, and the shared development manifest omits gold for a semantic target used by C and D.

Descriptively, C required 2 effective calls while D made 6; D used 7538/3598 input/output tokens versus 5752/381 for C and took about 22.17 s versus 4.13 s of model latency. D recovered two gold-covered logical values in the CSV hard case, but its platform change is unscored. These observations cannot establish that D is more accurate or that C is more efficient at equal quality.

## Qwen3.5 9B backend interpretation

**Observation:** Qwen obeyed the strict JSON shape but violated target scope on the HDF5 case. On the CSV case it cited valid evidence yet returned an explicit unknown despite notes recognizing the postal-code semantics.

**Inference:** Both failures are plausibly sensitive to model capability and contract following. A stronger model might make the correct scoped claims without changing B/C. That has not been tested here and must not be stated as fact.

**Recommendation:** Do not add decomposition, extra calls, critics, or model-specific routing to compensate for this 9B behavior. Such changes would reintroduce Model Capability Debt and invalidate the fixed A/B/C/D comparison.

## Freeze decision

### READY TO FREEZE WITH DOCUMENTED LIMITATIONS

There is no remaining known harness defect that silently changes model-call counts, replay identity, evidence trust states, N/A denominators, AURC ordering, unsupported-claim rates, or pairwise comparability. The harness now converts each observed validity problem into an explicit partial/non-comparable state.

### Blocking

No blocking implementation defect remains after the fixes in this phase.

Before executing a blind evaluation, its frozen manifest must pass these protocol requirements:

1. every deterministic semantic target must be covered by gold;
2. target opportunity counts and property distributions must be reported before model execution;
3. gold must distinguish applicable value, applicable unknown, N/A, and outside-scope fields;
4. any replay mismatch, extra C generation call, malformed/partial response, or missing D dependency preserves non-comparability;
5. enough scorable semantic opportunities must exist to answer the research question; this development set does not justify a numeric minimum.

Failure of any of these requirements blocks interpretation of the affected blind comparison, not merely publication language.

### Non-blocking limitations

- Only 2/9 development cases invoke B/C, and only one is fully gold-covered.
- Qwen3.5 9B caused one B/C partial case; this is an observed backend/contract failure, not an evaluator defect.
- D's preserved temperature 0.2 behavior is not guaranteed deterministic; no seed was added because that would alter the historical condition.
- Local configured cost is USD 0; token and latency comparisons remain available.
- Overall AURC mixes confidence scales across properties. Per-property curves are included and should be preferred when calibration differs.
- C verifies reference identity, field relevance, and deterministic conflicts—not semantic entailment or factual truth.

### Future work after freeze

- Run the independently adjudicated blind manifest without prompt or architecture changes.
- Evaluate stronger current models as predeclared backend conditions, not as post-hoc rescue attempts.
- Add no judges, agents, recursive critique, or extra semantic passes to this protocol.

## Exact changes made in this phase

1. Added strict response-shape, claim, confidence, evidence-list, scope, logical-type, and duplicate validation.
2. Made malformed/partial output fail closed and non-comparable.
3. Added success and failure replay caching, raw-content hashes, response IDs, raw response persistence, and per-case B/C identity records.
4. Enforced B call limits, C zero-generation calls, and C-without-B rejection.
5. Fixed C's abstention-promotion defect and added deterministic cross-claim conflict handling.
6. Separated applicable values, applicable unknowns, N/A, and outside-gold-scope predictions.
7. Fixed the open-world gold bug that treated unannotated task fields as N/A false positives.
8. Added semantic-target gold-coverage preflight reporting and comparability invalidation.
9. Defined confidence-tie AURC ordering and added per-property curves.
10. Separated deterministic evidence metrics from model-only proposed/accepted trust metrics.
11. Preserved failed-response tokens, latency, raw content, and failed-attempt counts.
12. Separated C's generated, reused-upstream, and effective-architecture resource accounting.
13. Restored D's historical free-JSON then schema fallback and preserved its legacy merge boundary.
14. Added the predefined, output-independent semantic-opportunity analysis stratum.
15. Added the adversarial and regression tests described above.

The architecture variants themselves were not redesigned, and no variant, agent, judge, semantic pass, or paid API was added.

## Verification record

- Focused harness tests: `31 passed`.
- Full repository tests from the repository root after final formatting: `214 passed in 2.29s`.
- Lint on changed harness Python files: passed.
- Repository-wide Ruff: 7 pre-existing findings outside the changed harness files (`E731`, `F841`, four unused imports, and one shadowed import); left untouched to preserve unrelated work.
- `git diff --check`: no whitespace errors; only existing Windows LF-to-CRLF conversion warnings.

Artifacts:

- `data/experiments/minimal_architecture_redesign/qwen35_9b_development_2026-07-14/report.json`
- `data/experiments/minimal_architecture_redesign/qwen35_9b_development_2026-07-14/report.md`
