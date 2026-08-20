# NDP-50 collaborator feedback sign-off guide v1

Date: 2026-07-27  
Status: released for human collaborator review; no sign-off recorded  
Assigned role: Swathi, postdoctoral research collaborator  
Independence status: project collaborator; this review is not independent
validation

## 1. Purpose

This assignment asks Swathi to determine whether the current NDP-50 protocol,
analysis, governance, and manuscript changes faithfully incorporate feedback
items F01--F16 within the stated claim boundaries. It records collaborator
approval or non-approval; it does not validate empirical results, qualify an
annotator, verify preregistration, or authorize test access.

## 2. Materials to review

Review the exact content-bound versions of:

1. `docs/swathi_feedback_response_matrix_v1.md`;
2. `docs/ndp50_feedback_improvement_amendment_v1.md`;
3. every source file listed in the generated `review_materials` array.

The v2 neutral payload currently binds the citation matrix, dated literature
review, annotation/independence plan, implementation audit, human/external gate
ledger, methodological risk register, NDP-50 scope/request-provenance record,
statistical analysis plan, this sign-off guide, preregistration draft, claim
ledger, bibliography, result macros, and English manuscript source. The
validator recomputes every file hash and the ordered
`review_materials_digest_sha256`; a missing, changed, additional, or reordered
binding invalidates the sign-off.

`paper/build/semantic_architecture_study_en.pdf` may be supplied as a
convenience rendering, but the authoritative review binding is the public
English manuscript source plus its bibliography and result macros. Any source
change requires a new rendering and a fresh sign-off.

The executable assignment is
`data/experiments/ndp50_v1/semantic/human_assignments_v1/feedback_response_signoff_assignment.json`.
Its payload is
`data/experiments/ndp50_v1/semantic/human_assignments_v1/feedback_response_signoff_payload.json`.
The payload hashes identify the exact response matrix, amendment, and complete
review-material bundle. A changed binding requires regeneration and a fresh
review.

## 3. Review questions

For every item F01--F16, determine whether:

- the recorded decision matches the substance of the feedback;
- the implementation evidence actually supports the claimed incorporation;
- any rejected or deferred suggestion has an explicit methodological reason;
- the manuscript language remains within the registered estimand and evidence;
- inactive sensitivity analyses are clearly labelled as inactive;
- collaborator and independent-review roles are not conflated;
- no text implies that a local draft is an external preregistration;
- no text implies that a sealed test split rules out model pretraining exposure.

Record unresolved concerns outside the sign-off artifact first. Changes to a
reviewed source invalidate its existing hash, so the neutral payload must then
be regenerated before signing.

## 4. Completing the payload

Copy the neutral payload to
`completed_feedback_response_signoff.json`. Do not overwrite the neutral
source. In the working copy:

1. set `status` to `approved_with_recorded_boundaries` only if every review
   question passes;
2. set `human_decisions_present` to `true`;
3. keep `test_outcomes_observed` and `independence_claimed` as `false`;
4. preserve both artifact bindings and the complete
   `optional_sensitivity_decisions` object;
5. preserve the complete ordered `review_materials` array and
   `review_materials_digest_sha256`;
6. set `reviewed_feedback_items` to F01 through F16 exactly once and in order;
7. provide a stable pseudonymous `collaborator.reviewer_id`, the fixed
   `postdoctoral_research_collaborator` role, a qualification summary, and a
   truthful conflict-of-interest disclosure;
8. keep `project_collaborator=true`, `developer_participation=false`, and
   `independent_reviewer=false`;
9. use the same RFC 3339 UTC timestamp in both `signed_at` fields;
10. set each attestation, including
    `all_bound_review_materials_reviewed`, to `true` only after personally
    confirming it.

If approval is withheld, do not convert the neutral payload into a passing
artifact. Return a separate issue list and request a versioned correction.

## 5. Validation and return

From the repository root, run:

```powershell
python -m high_fidelity_schema_study.ndp50_publication_gate validate-signoff `
  --artifact completed_feedback_response_signoff.json `
  --feedback-matrix high_fidelity_schema_study/docs/swathi_feedback_response_matrix_v1.md `
  --amendment high_fidelity_schema_study/docs/ndp50_feedback_improvement_amendment_v1.md `
  --study-root high_fidelity_schema_study `
  --output feedback_response_signoff_validation.json
```

Return:

- `completed_feedback_response_signoff.json`;
- `feedback_response_signoff_validation.json`;
- any issue list or requested corrections.

The study operator must hash-bind both returned JSON files in the
`feedback_response_signoff` slot of the assignment return manifest. A passing
receipt completes only the collaborator-feedback stage. External
preregistration and independent test-release authorization remain separate
mandatory gates.
