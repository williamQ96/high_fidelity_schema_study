# NDP-50 initial human-assignment execution guide v1

Date: 2026-07-27  
Status: released but unassigned; no human decisions recorded  
Scope: the four assignments in the initial NDP-50 human-work release

## 1. Purpose and evidentiary boundary

This guide turns the initial release into an operational, auditable handoff. It
does not supply reviewer identities, decisions, signatures, or approvals. A
neutral payload, assignment wrapper, or passing software test is not human
evidence.

The authoritative machine-readable artifacts are:

- `data/experiments/ndp50_v1/semantic/human_handoff_v1.json`;
- `data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_release_v1.json`;
- `data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_distribution_spec_v1.json`;
- `data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_roster_neutral_v1.json`;
- the four `*_assignment.json` wrappers in that assignment directory; and
- `return_manifest_neutral_v1.json`.

The cross-stage responsibility and acceptance map is
`docs/ndp50_human_external_gate_ledger_v1.md`. That ledger covers all ten live
readiness blockers plus the later test-release and test-execution gates; it is
an execution control, not evidence that any gate has closed.

Before distribution, replay `assignment_release_v1.json` with
`ndp50_human_assignments validate-release`. Do not distribute a package whose
replay status is not `passed`.

Before distributing any assignment, materialize the four least-access packets
from the checked-in neutral distribution specification into a new empty
directory outside the repository:

```bash
python -m high_fidelity_schema_study.ndp50_assignment_distribution materialize \
  --spec high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_distribution_spec_v1.json \
  --assignment-release high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_release_v1.json \
  --public-package-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/preregistration/public_package_manifest_v1.json \
  --selection high_fidelity_schema_study/data/experiments/ndp50_v1/selection.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --repo-root high_fidelity_schema_study \
  --packet-root <new-empty-directory-outside-the-repository> \
  --output-receipt <private-assignment-distribution-receipt.json>

python -m high_fidelity_schema_study.ndp50_assignment_distribution validate \
  --receipt <private-assignment-distribution-receipt.json> \
  --spec high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_distribution_spec_v1.json \
  --assignment-release high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_release_v1.json \
  --public-package-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/preregistration/public_package_manifest_v1.json \
  --selection high_fidelity_schema_study/data/experiments/ndp50_v1/selection.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --repo-root high_fidelity_schema_study \
  --packet-root <same-directory-outside-the-repository> \
  --output <private-assignment-distribution-validation.json>
```

Before any reviewer begins a submission, copy and complete the neutral roster.
It freezes five role slots: governance stewardship, governance accountable
approval, vocabulary A, vocabulary B, and collaborator feedback review. Each
slot records a stable pseudonymous ID, accepted role, qualification, conflict
and participation declarations, assignment, packet-delivery, acceptance, and
freeze timestamps, the exact packet ID and packet-manifest digest, and
contract/test/model/cross-packet access attestations. The vocabulary reviewers
must be distinct non-developer non-collaborators; the feedback collaborator
cannot fill either independent vocabulary slot.

Populate the roster's distribution evidence from the exact receipt and
validation files above. Record `validated_at` before assignment and delivery.
For each slot, copy only the packet ID and `packet_manifest_sha256` belonging to
that slot from the receipt. Then run the strict validator while the external
packet root is still available:

```bash
python -m high_fidelity_schema_study.ndp50_assignment_roster validate \
  --roster completed_assignment_roster.json \
  --assignment-release high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_release_v1.json \
  --handoff high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_handoff_v1.json \
  --distribution-spec high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_distribution_spec_v1.json \
  --distribution-receipt <private-assignment-distribution-receipt.json> \
  --distribution-validation <private-assignment-distribution-validation.json> \
  --public-package-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/preregistration/public_package_manifest_v1.json \
  --selection high_fidelity_schema_study/data/experiments/ndp50_v1/selection.json \
  --packet-root <same-directory-outside-the-repository> \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --repo-root high_fidelity_schema_study \
  --output assignment_roster_validation.json
```

This command rescans the live packet root and replays both distribution
artifacts before accepting any identity or delivery claim. The roster and its
exact validation receipt must be frozen before human submissions begin and are
required by the initial return manifest. Later return validation replays their
content bindings; it does not claim to re-observe delivery.

Distribute only the matching packet directory. Vocabulary reviewer A must
never receive packet B, and reviewer B must never receive packet A. The
governance packet is used sequentially by the stewardship reviewer and the
distinct accountable approver. The feedback packet is collaborator review
material and must not be treated as independent validation. A passing packet
receipt proves the file set at validation time; the completed roster adds the
per-role delivery and receipt attestations. The checked-in repository contains
neither a materialized packet root, a completed distribution receipt, nor a
completed roster.

## 2. Released assignments

| Assignment | Purpose | Required human role | Primary returned evidence |
| --- | --- | --- | --- |
| `data_governance_review` | Freeze dataset-level license, attribution, model-transfer, redistribution, and study-policy decisions | A stewardship reviewer followed by a distinct accountable approver | Completed review, exact validation receipt, validator-generated approval, and approval replay |
| `vocabulary_discovery_a` | Independently assess corpus vocabulary coverage and propose evidence-supported additions | Scientific metadata curator | Frozen discovery A submission and exact validation receipt |
| `vocabulary_discovery_b` | Independently assess the same corpus without seeing A | Annotation methodologist | Frozen discovery B submission and exact validation receipt |
| `feedback_response_signoff` | Review the complete F01--F16 response, content-bound supporting review bundle, and frozen optional-sensitivity decisions | Postdoctoral research collaborator | Completed collaborator sign-off and exact validation receipt |

The two vocabulary payloads are byte-identical, while their wrappers, assigned
roles, reviewer IDs, and submission IDs must be distinct. Swathi's feedback
review is collaborator review, not independent validation.

## 3. Common custody rules

1. Copy the released neutral payload to the exact working filename specified
   by its assignment wrapper.
2. Do not edit bound artifact hashes, case identities, evidence catalogs, or
   schema-version fields.
3. Use stable pseudonymous IDs and truthful qualification, role, participation,
   and conflict disclosures.
4. Keep test identities, details, gold, and outcomes inaccessible.
5. Run the exact validator command from the wrapper. Return the validator's
   generated receipt; do not hand-create or edit it.
6. Populate the matching slot in `return_manifest_neutral_v1.json` with
   content-addressed file bindings.
7. A human attestation may be set true only by the person responsible for that
   attestation after completing the specified review.

## 4. Governance execution

The stewardship reviewer completes every dataset decision and study-policy
field first. That completed review is frozen before the distinct accountable
approver receives it for countersignature. The same person or stable ID cannot
fill both slots.

The wrapper specifies four exact filenames:

- `completed_data_governance_review.json`;
- `data_governance_review_validation.json`;
- `data_governance_approval.json`; and
- `data_governance_approval_validation.json`.

Run the three wrapper commands in order:

1. `validate-review` checks the completed human review;
2. `approve` deterministically generates the approval from that exact review;
3. `verify-approved` replays the generated approval.

The derived approval must not be hand-edited. This workflow records a governed
research decision and does not claim to provide legal advice.

## 5. Independent vocabulary discovery

Reviewer A and reviewer B each complete all 16 case reviews and all corpus-level
policy decisions. Before both submissions and receipts are frozen, neither
reviewer may:

- communicate about review content;
- see the other assignment or submission;
- see a candidate catalog or disagreement report; or
- use model outputs.

Each reviewer cites only locatable evidence IDs from the released source
bundles and provides a rationale for each coverage judgment or proposal. The
assigned reviewer role, stable reviewer ID, unique submission ID,
qualification summary, conflict disclosure, and completion attestation are
required.

The exact working and receipt filenames are:

- `vocabulary_discovery_a.json` and
  `vocabulary_discovery_a_validation.json`;
- `vocabulary_discovery_b.json` and
  `vocabulary_discovery_b_validation.json`.

After both validator receipts pass, the operator records both submission
hashes and the dual-freeze attestations in the return manifest. Candidate
construction and disagreement reveal remain forbidden before that atomic
freeze.

## 6. Collaborator feedback review

The collaborator reviews every F01--F16 item in the response matrix and
amendment. The review must preserve the bound documents and frozen optional
sensitivity decisions, disclose collaborator status, and explicitly avoid an
independent-validation claim.

Use:

- `completed_feedback_response_signoff.json`; and
- `feedback_response_signoff_validation.json`.

The detailed item-level procedure is in
`docs/ndp50_swathi_feedback_signoff_guide_v1.md`. This sign-off alone does not
authorize semantic execution or test release.

## 7. Return and release validation

The operator may set the initial return manifest to
`completed_pending_validator_acceptance` only after:

- the pre-submission assignment roster and exact validation receipt are bound;
- all four submissions and receipts are present;
- governance signatory IDs are distinct;
- vocabulary reviewer and submission IDs are distinct;
- vocabulary role coverage matches the assigned slots;
- both vocabulary receipts passed before comparison;
- the dual-freeze record contains the exact submission hashes; and
- the completion attestation is true.

Run `ndp50_human_assignments validate-returns` against the exact release,
handoff, and study root. A passing return validation authorizes candidate
catalog construction only. It does not imply frozen vocabulary, approved
sources, completed semantic gold, external preregistration, or test release.

## 8. Evidence checklist

For each assignment, retain:

- the immutable assignment wrapper and neutral payload hash;
- the frozen pre-submission roster and roster-validation hash;
- assignment date and stable pseudonymous reviewer ID;
- completed submission;
- validator-generated receipt;
- qualification and conflict disclosures;
- custody or isolation attestations;
- any permitted operator freeze record; and
- the final return-manifest and return-validation hashes.

Any deviation from the released payload, roles, isolation rules, command
sequence, or test-data boundary must be recorded before downstream work
continues.
