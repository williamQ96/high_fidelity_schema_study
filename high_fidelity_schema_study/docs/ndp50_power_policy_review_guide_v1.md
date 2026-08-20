# NDP-50 power-policy review guide v1

Date: 2026-07-27  
Status: neutral pre-calibration guide; no policy values selected  
Audience: study operator and independent statistical methods reviewer

## 1. Purpose

This guide explains how to complete
`data/experiments/ndp50_v1/semantic/power_freeze/power_policy_neutral_v1.json`
without using development calibration outcomes to choose favorable assumptions.
It is not a completed policy, a power calculation, or reviewer approval.

The policy must be completed and signed after the execution contract is frozen
but before development-only calibration outcomes are inspected. Validation or
test semantic outcomes are forbidden inputs.

## 2. Decision sequence

1. Verify the execution freeze contains the same two co-primary contrasts and
   primary endpoint as CPA design v1.
2. Define the smallest mean dataset-level paired difference that would matter
   scientifically or operationally.
3. State the external rationale for that minimum effect without consulting the
   study's calibration outcomes.
4. Select target power and the conservative Holm planning threshold.
5. Select an SD floor and an inflation factor that guard against unstable
   development estimates.
6. Select at least three ordered SD sensitivity multipliers, including `1.0`
   and the chosen inflation factor.
7. Define the minimum acceptable selective-risk bound independently of
   accuracy.
8. Define the required assurance that the fixed 25-dataset test set contains
   enough comparable semantic-opportunity datasets.
9. Record independent methods review, conflicts, and signed dates.
10. Freeze and hash the policy before executing development calibration.

## 3. Field-level decision contract

| Field | Validator range | Required rationale |
| --- | --- | --- |
| `minimum_meaningful_effect` | \(0 < x \leq 1\) | Why an absolute change of this size in correct accepted applicable-claim rate would alter a scientific or operational decision |
| `minimum_meaningful_effect_rationale` | non-empty text | External/substantive basis, not observed NDP development performance |
| `target_power` | \(0 < x < 1\) | Chosen type-II-error tolerance and resource trade-off |
| `selective_risk_bound` | \(0 \leq x \leq 1\) | Maximum acceptable error among accepted known claims and why |
| `planning_sd_inflation` | \(1 < x \leq 3\) | Protection against a small or optimistic development SD |
| `sd_floor` | \(0 < x \leq 1\) | Minimum planning variability even if calibration differences are nearly constant |
| `opportunity_count_assurance` | \(0 < x < 1\) | Required probability of attaining the planned comparable-dataset count at fixed \(n=25\) |
| `sensitivity_sd_multipliers` | at least 3 unique ordered values in \([0.5,3]\) | Must include `1.0` and the chosen inflation factor; should expose optimistic and pessimistic scenarios |

The ranges are syntactic admissibility rules, not recommended values.

## 4. Minimum meaningful effect

The minimum meaningful effect concerns the equal-weight mean dataset-level
change in the primary endpoint, not pooled slot accuracy. Its rationale should
reference a decision consequence, such as a change large enough to justify
model cost or a verification component, and should explain why a smaller
change would not alter that decision.

Acceptable sources include:

- operational error budgets defined independently of study outcomes;
- domain-expert consequences of wrong or missing schema claims;
- resource-cost trade-offs fixed before calibration;
- prior external studies whose endpoint and scale are demonstrably comparable.

Unacceptable sources include:

- the observed NDP development effect;
- a threshold chosen because it produces feasible power;
- a rounded version of the observed effect;
- the smallest value that makes the planned result significant.

## 5. Variability protection

The development split may contain few comparable semantic-opportunity
datasets. Its observed paired-difference SD can therefore be unstable or zero.
Planning uses the larger of the signed `sd_floor` and the observed
development SD, then applies the prespecified inflation factor.

The sensitivity grid must show how the required opportunity count changes over
multiple SD scenarios. If the fixed test size fails the requested assurance
under the signed planning scenario, the design does not meet the pretest power
gate. The remedy is to report the limitation or redesign before test release,
not to weaken the policy after observing outcomes.

## 6. Relationship between planning and inference

The power calculation uses a paired-t approximation for sample-size planning.
The registered NDP-50 test remains the two-sided paired sign-flip test with
Holm control. The approximation does not redefine the null, primary p-value, or
effect estimator.

At least seven nonzero pairs are required merely for a two-sided exact
sign-flip p-value to attain the worst-case Holm threshold of 0.025. This
resolution floor does not establish target power, opportunity assurance, or
precision.

## 7. Independent-review questions

The methods reviewer must answer, before signing:

1. Is the minimum effect substantively meaningful on the registered endpoint?
2. Was its rationale fixed without calibration, validation, or test outcomes?
3. Are target power and familywise error stated separately?
4. Does the SD floor prevent a zero-variance or implausibly optimistic plan?
5. Is inflation large enough to reflect the small development sample?
6. Do sensitivity scenarios include the signed primary scenario and both less
   and more variable alternatives?
7. Does opportunity assurance account for the fixed maximum of 25 test
   datasets?
8. Are dataset clusters, not resources or fields, counted as independent?
9. Does a missed assurance requirement force underpowered reporting rather
   than sample rescue?
10. Are the reviewer and operator distinct, with developer participation and
    conflicts disclosed?

## 8. Required signed record

The completed machine-readable policy contains:

- stable pseudonymous IDs;
- roles and institutions;
- qualification summaries;
- conflict declarations;
- developer-participation declarations;
- ISO dates;
- `completion_attestation=true`.

A signature attests to a pre-outcome decision and disclosed independence. It
does not certify that the future study will be adequately powered; the
validator and later realized-opportunity reconciliation establish whether the
frozen requirements are met.

