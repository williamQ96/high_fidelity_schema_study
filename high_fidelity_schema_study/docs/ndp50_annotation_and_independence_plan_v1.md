# NDP-50 annotation and independence plan v1

Date: 2026-07-27  
Status: execution-ready specification; human work and external receipts pending  
Scope: CPA applicability, semantic gold, agreement, and role independence

## 1. Purpose

This plan connects the existing NDP-50 human handoff to the blind semantic-gold
handbook and two-annotator calibration protocol. It closes a publication-risk
gap: describing annotators as “qualified” is insufficient unless qualification
is defined, passed before blind annotation, and bound to the same handbook,
vocabulary, and annotator identities used for NDP-50 gold.

This plan does not fill human decisions, fabricate signatures, or authorize
semantic execution.

## 2. Role registry and disjointness

Every person uses one stable pseudonymous ID and declares qualification,
institution or organizational relationship, developer participation, and
conflicts of interest.

| Function | Minimum requirement | Must be disjoint from |
| --- | --- | --- |
| Study operator | Disclosed developer/operator | independent annotator, fresh adjudicator, methods reviewer, test-release monitor |
| Postdoctoral collaborator | Literature, protocol, baseline, claim, and interpretation review | roles whose validity requires independence from active project review |
| Vocabulary discovery | two independent qualified non-developers | later fresh vocabulary decision pair |
| Vocabulary decision | two independent qualified non-developers | discovery pair |
| Vocabulary adjudication | one fresh qualified non-developer | discovery and decision reviewers |
| Source review | two independent qualified non-developers | fresh source adjudicator |
| Source adjudication | one fresh qualified non-developer | source reviewers |
| CPA applicability | two independent qualified non-developers | fresh CPA adjudicator |
| CPA adjudication | one fresh qualified non-developer | CPA screeners |
| Semantic gold | the same two calibrated non-developer annotators across the corpus | developers and active system reviewers |
| Gold consensus | the same calibrated pair, jointly, after disagreement reveal | architecture-output viewers before gold freeze |
| Methods review | one qualified independent reviewer | study operator/developer |
| Test release | one qualified independent monitor | study operator and anyone who inspected sealed test detail |

Swathi is an active postdoctoral collaborator and may sign the collaborator
review. She cannot be represented as an independent annotator, fresh
adjudicator, independent methods reviewer, or independent test-release monitor.

## 3. Required sequence

### Stage A: freeze instructions and admissible evidence

1. Complete data-governance approval.
2. Freeze the NDP vocabulary through the independent discovery/decision/
   adjudication workflow.
3. Rebuild and independently approve source bundles against that vocabulary.
4. Freeze the semantic-gold handbook, annotation schemas, validator, and
   admissible-evidence policy by hash.

### Stage B: qualify the semantic-gold annotator pair

Before either annotator sees an NDP-50 blind gold packet:

1. build a non-NDP calibration workflow using at least nine cases excluded from
   NDP-50 evaluation;
2. bind the exact final handbook and NDP vocabulary hashes;
3. preregister the design and thresholds before the first submission;
4. collect two independent, prediction-blind submissions;
5. freeze both hashes before generating disagreement reports;
6. deterministically build and validate the calibration summary;
7. require a passing summary for exactly the two annotator IDs assigned to
   NDP-50 gold.

Protocol floors are:

| Gate | Minimum |
| --- | ---: |
| Cases | 9 |
| Overall exact state/value agreement | 0.80 |
| Applicability agreement | 0.90 |
| Each property's exact agreement | 0.70 |
| Every case's exact agreement | 0.50 |

These are operational qualification floors, not universal validity constants.
A failed round may inform revisions, but the confirmation round must use new
preregistered cases. The old revealed cases cannot be reused as an unbiased
gate.

### Stage C: CPA applicability

The two CPA screeners independently decide relational-table applicability,
single-subject-column support, and property-annotation applicability without
model outputs. Both submissions are validated and frozen before a deterministic
disagreement worksheet is revealed. A fresh adjudicator resolves every
disagreement with approved evidence and rationale.

### Stage D: semantic gold

The calibrated pair annotates every registered case independently using only
the raw resource, neutral field inventory, approved source bundle, frozen
vocabulary, and handbook. They cannot inspect architecture outputs, model
responses, prior project gold, the other submission, or predictive hints.

For every `(dataset_id, field_path, property)` slot they distinguish:

- applicable known value;
- applicable unknown;
- not applicable;
- outside evaluation scope.

Every known value requires approved evidence. Every null decision requires a
property-specific rationale. Both independent artifacts must validate and
freeze before comparison.

### Stage E: agreement and consensus

Before reconciliation, compute and retain:

- exact state/value agreement numerator and denominator;
- applicability agreement;
- agreement by property and dataset;
- disagreement and invalid/missing-submission counts;
- Cohen's kappa with its full marginal table, or an explicit undefined reason;
- evidence-identity agreement separately from value-label agreement.

Krippendorff's alpha is optional and descriptive unless unitization, distance,
missing-data policy, and bootstrap method are frozen before labels. No
coefficient replaces disagreement resolution.

The disagreement report is generated deterministically. Agreed slots are
immutable. Each disagreement receives one human resolution and rationale.
Model output remains hidden. Consensus binds both original submissions and the
disagreement report by hash.

## 4. Anchoring and leakage controls

- Annotation packets contain neutral structural evidence but hide predictive
  deterministic logical/semantic/unit values.
- Architecture outputs and model confidence are inaccessible until consensus
  gold is frozen.
- Reviewers complete the full assigned corpus independently before comparison.
- Assignment wrappers contain no reviewer identity or decision.
- Test identities and test-detail evidence remain outside public and
  development-facing material.
- Any accidental exposure is a versioned deviation that identifies affected
  people, cases, timing, and disposition.

Prediction blinding reduces anchoring from system output; it does not prove the
absence of domain conventions, shared training, or other correlated judgment.

## 5. Agreement interpretation

Agreement is process evidence, not truth evidence. High agreement can reflect
shared error, and low agreement can expose unclear instructions, insufficient
evidence, or genuine ambiguity.

The paper must report both pre-consensus agreement and post-consensus label
coverage. It must not:

- call consensus a human upper bound;
- describe kappa as accuracy;
- omit degenerate marginals;
- pool properties with incompatible decision spaces without support counts;
- use consensus to overwrite immutable independent submissions.

## 6. Machine-enforcement requirement

Before NDP-50 can claim publication-ready independent gold, readiness and the
human handoff must bind a passing
`semantic-annotator-calibration-summary/v1` artifact and verify:

1. `status=passed`;
2. exact handbook hash match;
3. exact frozen NDP vocabulary hash match;
4. exact two-person annotator-ID match with the semantic-gold corpus registry;
5. valid pre-submission registration receipt;
6. replay of the calibration summary from its bound inputs.

The gate is implemented but has not passed:
`independent_gold_complete` remains false. Even after it passes, test release
also requires the separately validated collaborator-feedback sign-off,
immutable external preregistration receipt, execution/power freezes, and final
independent release authorization. The current real state remains blocked
before semantic annotation.

## 7. Required publication artifacts

- role and conflict registry;
- collaborator feedback-response sign-off explicitly marked non-independent;
- immutable external preregistration receipt plus a distinct independent
  registration-verification record;
- frozen handbook and vocabulary hashes;
- calibration design and external timing receipt;
- both immutable calibration submissions and passing summary;
- both CPA applicability submissions, disagreement worksheet, and consensus;
- both semantic-gold submissions per case;
- corpus agreement report with denominators and marginal tables;
- disagreement/resolution log;
- consensus gold and validator approval;
- leakage/deviation register, including an explicit empty register when none
  occurred.

## 8. Current status

The executable annotation, CPA, source-approval, and disagreement workflows
exist. Human governance, final vocabulary, source approval, annotator
qualification, CPA screening, and semantic gold are not complete. No statement
in this plan upgrades those pending states.
