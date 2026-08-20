# NDP-50 human and external gate ledger v1

Date: 2026-07-27  
Status: pre-submission execution control; no human decision, signature,
delivery, approval, registration, or test outcome is recorded here  
Scope: all unresolved human and external gates between the validated NDP-50
preparation state and publication reporting

## 1. Authority and evidence rule

The live machine authorities are:

- `data/experiments/ndp50_v1/semantic/readiness_report_v1.json`;
- `data/experiments/ndp50_v1/semantic/human_handoff_v1.json`;
- `data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_release_v1.json`;
- the validators named below; and
- the final content-addressed receipts produced by those validators.

This ledger is an execution map, not completion evidence. A neutral template,
released assignment, materialized packet, passing unit test, or unchecked
human-authored JSON cannot close a gate. A gate closes only when all required
human or external evidence exists, its exact validator replay passes, and a
rebuilt readiness or downstream release artifact exposes the corresponding
machine predicate.

Stable pseudonymous reviewer IDs are permitted. Anonymous or invented
attestations are not. No role may be reassigned merely to obtain a passing
decision, and no collaborator review may be relabelled as independent review.

## 2. Current readiness-blocker coverage

The ten rows below correspond one-to-one with the ten live readiness blockers.
Rows H06 and H07 share one handoff stage but require distinct evidence and
predicates.

| Gate | Exact readiness blocker | Handoff stage | Responsible role boundary | Minimum closing evidence | Machine acceptance predicate |
| --- | --- | --- | --- | --- | --- |
| H01 | `license, attribution, model data-transfer, and artifact redistribution governance are not frozen` | `data_governance_review` | Qualified non-developer data steward followed by a distinct accountable approver | Completed review, review validation, validator-generated approval, and approval replay | `human_license_and_attribution_review_complete=true`; `external_model_data_transfer_policy_frozen=true`; `artifact_redistribution_policy_frozen=true`; `data_governance_policy_frozen=true` |
| H02 | `corpus-specific vocabulary is not frozen` | `vocabulary_governance` | Two distinct, prediction-blind non-developer reviewers covering scientific-metadata-curator and annotation-methodologist roles; later fresh consensus role | Two independently validated discoveries, two independently validated candidate decisions, frozen disagreement worksheet, evidence-backed consensus, and frozen vocabulary | `vocabulary_frozen=true` |
| H03 | `collaborator sign-off on the F01--F16 response matrix is absent` | `feedback_response_signoff` | Swathi as postdoctoral project collaborator; explicitly not an independent reviewer | Completed F01--F16 sign-off and validator-generated replay receipt bound to the current matrix, amendment, complete supporting review-material list, and ordered bundle digest | `feedback_response_collaborator_signoff_complete=true` |
| H04 | `source relevance and bundle readiness lack human approval` | `source_approval` | Two distinct qualified source reviewers followed by a fresh adjudicator | Rebuilt frozen source bundle, two validated independent reviews, frozen disagreement worksheet, validated consensus, and approved-manifest replay | `source_bundles_annotation_ready=true` |
| H05 | `the semantic-gold annotator pair has not passed a preregistered calibration bound to the frozen handbook and vocabulary` | `annotator_calibration` | The exact two future gold annotators; independent of project development and bound before NDP gold access | Preflighted calibration design, immutable pre-submission registration receipt, two independent calibration submissions, round manifest, passing summary, and summary replay | `annotator_calibration_passed=true` |
| H06 | `two independent CPA applicability screens and consensus are absent` | `cpa_screen_and_semantic_gold` | Two distinct qualified screeners followed by a fresh adjudicator; model outputs hidden | Two validated independent CPA screens, frozen disagreement worksheet, validated human consensus | `cpa_applicability_consensus_complete=true` |
| H07 | `calibration-matched two-annotator independent gold and consensus are absent` | `cpa_screen_and_semantic_gold` | The exact calibration-passing annotator pair followed by a fresh adjudicator | Two independently validated gold submissions, frozen disagreement report, validated per-case consensus, corpus validation, approval, and approval replay | `gold_annotator_identity_matches_calibration=true`; `independent_gold_complete=true` |
| H08 | `prompt, serialization, demonstrations, and backend registry are not frozen` | `execution_freeze` | Study operator plus qualified implementation reviewers; no validation/test outcomes visible | Completed execution configuration, implementation declaration and qualification replay, development-only demonstration pool replay, backend registry, and execution-freeze replay | `prompt_and_backend_frozen=true` |
| H09 | `frozen non-blind semantic power plan is absent` | `power_freeze` | Pre-calibration methods decision maker followed by independent review of the frozen policy | Validated development-only calibration statistics, completed policy and validation, power freeze and replay, and rebuilt feasibility report | `test_power_plan_frozen=true`; `test_design_meets_pretest_assurance=true` |
| H10 | `independently verified immutable OSF/Zenodo preregistration receipt is absent` | `external_preregistration` | Study operator deposits; a distinct non-developer, non-collaborator verifier checks the public record and disclosure boundary | Immutable public record, exported receipt, completed receipt artifact, independent verification, and receipt validation bound to the exact public manifest | `external_preregistration_verified=true` |

## 3. Downstream gates that are not yet readiness blockers

These stages remain mandatory even though the current readiness report stops at
the ten upstream blockers.

| Gate | Handoff stage | Required evidence | Acceptance boundary |
| --- | --- | --- | --- |
| H11 | `test_release_authorization` | Passing `test_ready=true` snapshot; distinct study-operator and independent-monitor signatures; completed release authorization; validator-generated release receipt and replay | No test identity or test-detail access before the witnessed opening event. Collaborators and developers cannot fill the independent-monitor role |
| H12 | `test_execution` | Frozen 25-dataset disposition manifest; complete case-by-arm and registered-sensitivity matrices; immutable response, parse, score, deviation, missingness, run-receipt, inference, and replay artifacts | Every disposition and matrix cell is retained. No post-outcome arm, metric, case, scorer, missingness, or power rescue is permitted |

## 4. Causal execution order

1. Validate the current assignment release.
2. Materialize and strictly validate the four least-access reviewer packets in
   a new empty directory outside the repository.
3. Complete and validate the five-slot roster before any human submission.
4. Run H01, H02, and H03 under their released assignments. These may proceed
   concurrently, but vocabulary A and B remain mutually isolated.
5. Validate the complete initial return manifest before candidate construction
   or disagreement reveal.
6. Complete H04 and H05; rebuild readiness and handoff after each accepted
   upstream evidence set.
7. Complete H06 and H07 without exposing model predictions or one annotator's
   submission to the other before both hashes freeze.
8. Complete H08, then H09. Power-policy choices precede inspection of
   development calibration outcomes.
9. Regenerate the public package after all permitted pre-registration changes;
   obtain H03 again if any reviewed source changed; then complete H10.
10. Rebuild readiness. Only a replayed `test_ready=true` state may enter H11.
11. Execute H12 exactly once under the frozen release and publish all
    registered outcomes, including null, negative, underpowered, failed, and
    non-analysable states.

## 5. Cross-gate invariants

- Content changes invalidate every downstream hash that binds them.
- Human evidence is frozen before comparison, disagreement reveal, or
  adjudication.
- A validator receipt is generated by replay; it is never hand-authored or
  edited.
- Reviewer qualification, participation, conflicts, assignment, delivery,
  acceptance, and timing are explicit.
- Sealed test identities, details, gold, and outcomes remain inaccessible
  until H11.
- Confidence is not evidence or verification. Calibration language follows the
  frozen arm-by-label support rule.
- Human consensus is the reference standard, not a human upper bound.
- Local public-package validation is not external preregistration.
- Passing software tests validates implementation consistency, not the
  scientific hypothesis.

## 6. Operator closeout record

For each gate, the private operator record must retain:

- gate ID and handoff stage;
- exact input and output artifact paths and SHA-256 values;
- reviewer/operator stable IDs and role/conflict disclosures;
- start, submission, freeze, adjudication, approval, and validation timestamps
  as applicable;
- validator command, implementation hash, exit status, and receipt hash;
- protocol deviations and whether any outcome was visible;
- the rebuilt readiness/handoff hash exposing the accepted predicate; and
- the next stage actually unlocked.

The publication artifact may report pseudonymous role IDs and content hashes,
but private identity and delivery records remain governed research records.
