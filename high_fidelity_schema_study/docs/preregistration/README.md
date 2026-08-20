# NDP-50 preregistration package

This directory contains public-facing preregistration material prepared before
semantic test release.

- `ndp50_osf_zenodo_preregistration_draft_v1.md` is the registration text.
- `../ndp50_statistical_analysis_plan_v1.md` fixes the estimand, primary
  inference, assumptions, and reporting boundary.
- `../ndp50_annotation_and_independence_plan_v1.md` fixes annotator
  qualification, role separation, blinding, agreement, and consensus.
- `../ndp50_feedback_implementation_audit_v1.md` separates machine
  implementation, documented boundaries, inactive proposals, and unresolved
  human/external evidence for F01--F16.
- `../ndp50_power_policy_review_guide_v1.md` guides pre-calibration human
  decisions without selecting values.
- `../ndp50_methodological_risk_register_v1.md` tracks invalidation and
  interpretation risks through release.
- `../ndp50_scope_provenance_v1.md` separates the collaborator-originated NDP
  direction from the investigator-defined 50-record sample, split, and
  analysis choices.
- `../ndp50_swathi_feedback_signoff_guide_v1.md` defines the collaborator's
  review questions, editable fields, non-independence boundary, and exact
  validator-generated return receipt.

The current file is a draft, not evidence of registration. A valid registration
requires an external time-stamped DOI or immutable receipt, final collaborator
review, refreshed artifact hashes, completed power and execution freezes, and
independent test-release authorization.

Sealed test identities, detail records, resources, gold, and outcomes must never
be added to this public package before the authorized opening event.

## Deterministic local assembly

`public_package_files_v1.txt` is the sorted public text-source allowlist.
`ndp50_preregistration_package.py` hashes every listed file, rejects
repository-path escape and known test-detail directories, and scans all listed
UTF-8 text against the 25 sealed dataset IDs and titles from the private
selection artifact. It also parses every listed Python source and rejects the
package unless every repository-local import is present in the same allowlist.
The package marker and pinned runtime/development requirement files are
included so that the source set is an executable package rather than a set of
disconnected entry points. This is source-level closure, not evidence that an
operating system, external service, hardware environment, or model backend has
been independently reproduced.

The live readiness and human-handoff artifacts are deliberately not package
members. They must change after a real receipt is supplied, so including them
would create a circular binding: the receipt would change readiness, which
would change the package the receipt purported to bind. The public package
instead includes the frozen protocols, executable test workflow, publication
gate implementation, the content-bound neutral feedback artifact, and the
generic external-receipt template. The live readiness report binds the
finished public manifest from outside that manifest.
The allowlist also includes the core metric, CPA, semantic-gold, power,
execution-freeze, test-execution/inference, human-handoff, publication-gate,
governance-review, and vocabulary-review implementations cited by the
feedback implementation audit, together with their transitive local Python
dependencies. Final prompt, backend, vocabulary, source, and gold freeze
artifacts must still be added or bound at actual registration.

Build and replay the current local draft:

```bash
python -m high_fidelity_schema_study.ndp50_preregistration_package build \
  --repo-root high_fidelity_schema_study \
  --selection high_fidelity_schema_study/data/experiments/ndp50_v1/selection.json \
  --file-list high_fidelity_schema_study/docs/preregistration/public_package_files_v1.txt \
  --output high_fidelity_schema_study/data/experiments/ndp50_v1/preregistration/public_package_manifest_v1.json

python -m high_fidelity_schema_study.ndp50_preregistration_package validate \
  --repo-root high_fidelity_schema_study \
  --selection high_fidelity_schema_study/data/experiments/ndp50_v1/selection.json \
  --artifact high_fidelity_schema_study/data/experiments/ndp50_v1/preregistration/public_package_manifest_v1.json
```

The local output is deliberately
`draft_structurally_valid_not_registered`. Exact ID/title absence does not
prove that every indirect clue is non-identifying, and a local hash does not
provide an independent timestamp. A human disclosure review and an immutable
OSF/Zenodo receipt remain mandatory.

## Human sign-off and external-receipt gate

`ndp50_publication_gate.py` separates three events that must not be conflated:

1. Swathi's collaborator review of F01--F16, explicitly not independent
   validation;
2. immutable OSF/Zenodo registration of the exact public-package manifest and
   content digest, followed by independent attachment and disclosure review;
3. later test-release authorization by the study operator and a distinct
   independent monitor.

The feedback input is the generated, content-bound
`data/experiments/ndp50_v1/preregistration/feedback_response_signoff_neutral_v1.json`;
the external-receipt input is
`templates/ndp50_external_preregistration_receipt_template.json`. Completing a
template does not make it valid; the validator recomputes all bindings and
rejects placeholder values, changed feedback decisions, non-HTTPS records,
invalid timing, or a verifier who is a developer or project collaborator.
The released wrapper is
`data/experiments/ndp50_v1/semantic/human_assignments_v1/feedback_response_signoff_assignment.json`.
It may be returned by the named collaborator now, independently of the later
external-registration and test-release stages.

The initial human release also generates
`assignment_roster_neutral_v1.json`. The completed roster must be frozen and
validated before any human submission begins. The live roster is intentionally
excluded from this public package because it binds the live assignment release
and handoff, which in turn bind readiness and this package; embedding it would
create a circular content-addressing dependency. The public package includes
the roster validator and execution guide instead. The completed roster and its
receipt remain private handoff evidence and are required by initial-return
validation.

The same release generates `assignment_distribution_spec_v1.json`. Its
materializer constructs four reviewer-specific packet roots outside the
repository from the import-closed public source base plus only the matching
assignment wrapper, payload, and released inputs. Validation requires an exact
file set, rejects another assignment's wrapper or payload, and rescans every
file against the sealed test IDs and titles. Packet roots and receipts are
private operational evidence and are not public-package members. No checked-in
receipt proves actual delivery. The strict roster validator reopens the live
external packet root, replays both distribution artifacts, binds the correct
packet-manifest digest to every role slot, and enforces validation-before-
delivery timing and receipt attestations. That mechanism is implemented, but
the real receipt, delivery, identities, and completed roster remain absent and
must be supplied before work begins.

Generate or replay the bound neutral feedback artifact:

```bash
python -m high_fidelity_schema_study.ndp50_publication_gate feedback-template \
  --feedback-matrix high_fidelity_schema_study/docs/swathi_feedback_response_matrix_v1.md \
  --amendment high_fidelity_schema_study/docs/ndp50_feedback_improvement_amendment_v1.md \
  --study-root high_fidelity_schema_study \
  --output high_fidelity_schema_study/data/experiments/ndp50_v1/preregistration/feedback_response_signoff_neutral_v1.json
```

After finalizing the public package, generate its local workflow:

```bash
python -m high_fidelity_schema_study.ndp50_publication_gate workflow \
  --public-package-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/preregistration/public_package_manifest_v1.json \
  --feedback-matrix high_fidelity_schema_study/docs/swathi_feedback_response_matrix_v1.md \
  --amendment high_fidelity_schema_study/docs/ndp50_feedback_improvement_amendment_v1.md \
  --study-root high_fidelity_schema_study \
  --output high_fidelity_schema_study/data/experiments/ndp50_v1/preregistration/publication_gate_workflow_v1.json
```

The current workflow remains pending. Do not create a synthetic “completed”
sign-off or receipt: the two validated artifacts must come from the named human
review and actual external registration.
