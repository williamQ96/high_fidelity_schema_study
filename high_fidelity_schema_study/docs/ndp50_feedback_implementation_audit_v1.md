# NDP-50 feedback implementation audit v1

Date: 2026-07-27  
Status: pre-test implementation audit; collaborator sign-off pending  
Scope: feedback items F01--F16 in
`docs/swathi_feedback_response_matrix_v1.md`

## 1. Audit rule

This audit does not treat a document mention, neutral template, passing software
test, or future-tense plan as evidence that a scientific or human-review result
exists. Each item is classified using one or more of:

- **machine implemented**: executable behavior and a focused test exist;
- **documented boundary**: publication language or scope is fixed, but no new
  empirical capability is claimed;
- **inactive by design**: the proposal is excluded unless a new versioned
  design, power review, and freeze activate it;
- **human/external pending**: the control exists, but required human judgment
  or external evidence is absent.

An item is not complete merely because its implementation status is
`machine implemented`. Human and external gates remain independent.

## 2. Item-level audit

| ID | Audited status | Direct implementation evidence | Verification evidence | Remaining evidence or boundary |
| --- | --- | --- | --- | --- |
| F01 | documented boundary | English manuscript and literature review position the work as replay-controlled component attribution across selective prediction, attributed generation, and ablation | `tests/test_swathi_feedback_integration.py::test_english_manuscript_contains_feedback_guardrails` | Positioning is a contribution claim, not evidence that one architecture wins |
| F02 | documented boundary plus primary-source entailment audit | citation matrix, literature review, bibliography, and related-work section distinguish CTA, CPA, metadata generation, and heterogeneous file schema extraction; the dated primary-source table records both directly supported and prohibited extrapolations | `tests/test_swathi_feedback_integration.py::test_literature_review_records_scope_boundaries_and_identifiers`; bibliography/citation-key build | Doduo, ArcheType, Korini--Bizer CPA, Auctus, and AutoDDG are scoped literature comparators, not active NDP-50 arms; bibliographic verification is not treated as claim entailment |
| F03 | documented boundary plus narrow motivating evidence | manuscript defines Model Capability Debt as a project-specific operational construct anchored in Sculley et al.; Khan's primary preprint is cited only for a single-task, cross-model prompt-effect reversal | manuscript citation checks, bibliography build, and primary-source claim-entailment table | No field-wide construct-validity, schema-transfer, or component-obsolescence claim is permitted |
| F04 | documented boundary plus machine analysis boundary | manuscript removes broad causal wording; statistical plan limits inference to frozen within-system component substitutions | sign-flip, bootstrap, and claim-scope logic in `ndp50_test_inference.py`; manuscript guardrail test | No population-wide or mechanistic causal interpretation |
| F05 | machine implemented for the primary baseline; other comparators scoped out | `deterministic_only` is a frozen arm in the CPA design, execution freeze, and test workflow | `tests/test_ndp50_test_execution.py`; `tests/test_ndp50_execution_freeze.py` | Doduo and ArcheType remain applicability-scoped extensions and have no executable NDP-50 arm |
| F06 | inactive by design | publication workflow freezes `evidence_free_single_call=exclude_from_confirmatory_matrix` | feedback-template replay and publication-gate tests | Activation requires a versioned information-removal contract, call budget, power/multiplicity review, and fresh hashes |
| F07 | documented boundary; heuristic inactive | gold workflow treats consensus as the reference process; amendment forbids “human upper bound” language | claim-ledger and feedback-integration tests | No measured human-performance ceiling exists; heuristic comparator is validation/development-only unless separately frozen |
| F08 | machine implemented; outcomes pending | execution freeze now requires an exact pricing basis, effective date/source, nonnegative call/token rates, cost scope, failed-call/retry/reuse treatment, separate model/end-to-end latency fields, and a bound backend hardware/runtime record; test-score v3 records and inference aggregation require and reconcile those fields | `tests/test_ndp50_execution_freeze.py`; `tests/test_semantic_study_preflight.py`; `tests/test_ndp50_test_execution.py` and inference replay tests | The checked-in configuration is deliberately neutral; realized prices, hardware/runtime identity, failures, latency, and totals remain absent until a completed freeze and authorized execution |
| F09 | machine implemented; human submissions pending | CPA workflow reports exact agreement, per-slot support, marginals, Cohen's kappa, and degenerate definedness; semantic-gold comparison reports exact label/evidence agreement, per-property support, and kappa before consensus | `tests/test_ndp50_cpa_screen_workflow.py`; `tests/test_semantic_gold_workflow.py::test_cohen_kappa_reports_defined_and_degenerate_cases` | Krippendorff's alpha is inactive unless unitization, distance, and missingness are separately frozen; agreement is not accuracy |
| F10 | machine implemented for calibration/reliability and AURC; secondary outcomes pending | scorer v3 binds each accepted applicable-known slot to an arm-specific confidence and exact-correctness indicator; score v3 reconciles those observations; registered inference reports separate arm-by-label fixed-decile reliability bins, suppresses Brier/ECE and calibration claims below 30 observations, and computes whole-tie-group risk--coverage plus AURC over achieved coverage without cross-arm/label pooling | `tests/test_ndp50_execution_qualification.py`; `tests/test_ndp50_test_execution.py::test_invalid_confidence_observation_is_rejected`; registered inference replay test; existing generic tied-confidence AURC regression | No realized calibration or AURC result exists; confidence is not evidence or verification. AUGRC remains inactive until a separately versioned scorer/endpoint is frozen |
| F11 | inactive by design | publication workflow freezes the second-model decision as deferred unless complete paired execution is frozen | publication-gate template replay tests | No second backend family is an active arm; it cannot be added after outcomes |
| F12 | machine implemented; human/external pending | deterministic public-package builder, collaborator-signoff validator, external-receipt validator, readiness gates, and test-release checks | preregistration, publication-gate, readiness, and test-execution test modules | No collaborator sign-off, immutable OSF/Zenodo record, or independent receipt verification currently exists |
| F13 | machine implemented; human/calibration pending | neutral power policy, Holm-aware power planning, dataset inflation by opportunity assurance, underpowered stopping rule, and power-freeze replay | `tests/test_ndp50_power_freeze.py`; `tests/test_semantic_power_analysis.py` | Minimum meaningful effect, SD inputs, assurance choice, and completed freeze require pre-calibration human review and development-only calibration |
| F14 | documented limitation | protocol, preregistration, risk register, claim ledger, and manuscript state that model pretraining exposure cannot be ruled out | feedback-integration boundary test | Project-side sealing prevents outcome tuning but is not contamination measurement |
| F15 | machine implemented process; human work pending | vocabulary, CPA, calibration, and semantic-gold contracts hide model outputs and freeze independent submissions before disagreement reveal | workflow tests for model visibility, distinct reviewers, hash freeze, and consensus mutation | No real independent NDP-50 submissions or adjudicated gold currently exist |
| F16 | machine implemented role and provenance boundary; human sign-off pending | collaborator assignment fixes `project_collaborator=true` and `independent_reviewer=false`; sign-off v2 binds the full review-material list and ordered digest; external verifier and test monitor must be non-collaborators | publication-gate review-material tamper test plus human-assignment, readiness, and feedback-integration tests | Swathi's review cannot count as independent annotation, adjudication, methods review, registration verification, or test monitoring; any bound-source change requires a fresh sign-off |

## 3. Oversights found and disposition

The audit found thirteen implementation-level issues:

1. **Circular publication-stage dependency.** The original handoff combined
   feedback sign-off, external registration, and test authorization behind a
   condition that itself depended on those artifacts. The 11-stage handoff now
   releases them in causal order.
2. **Validator receipt gap.** The sign-off and external-receipt validators
   printed reports but could not directly create the receipt files required by
   the return manifest. Both commands now accept `--output`, and the CLI receipt
   path is tested.
3. **Semantic-gold agreement gap.** CPA screening reported kappa and marginal
   definedness, while semantic-gold comparison reported exact agreement only.
   Semantic-gold comparison now adds per-property label-state support, Cohen's
   kappa, and explicit degenerate/no-slot states before consensus.
4. **Human-assignment execution-contract asymmetry.** The feedback assignment
   specified exact working-copy, receipt, return-slot, and validator
   instructions, but the governance and vocabulary assignments exposed only
   lower-level machine metadata. All four initially released assignments now
   include required and forbidden actions, exact output filenames,
   return-manifest slots, and replayable validator commands. The governance
   contract additionally distinguishes human review from validator-generated
   approval and approval replay.
5. **Downstream validation-receipt persistence gap.** Several locked-stage
   validators could recompute a preflight or replay result but only printed it
   to standard output, while the handoff requires durable content-addressed
   evidence. Calibration preflight/summary validation, per-case semantic-gold
   independent/consensus validation, execution qualification replay,
   demonstration-pool replay, power-analysis validation, and final inference
   replay now accept `--output`. The handoff now enumerates the corresponding
   validation, approval, and replay artifacts instead of listing human
   submissions alone.
6. **Pre-assignment identity and timing gap.** The initial wrappers were
   deliberately neutral, but no artifact proved who accepted each role or that
   role, conflict, isolation, and access commitments were frozen before human
   submissions began. A five-slot neutral assignment roster and validator now
   bind the exact release/handoff, enforce role and independence constraints,
   order RFC 3339 UTC assignment/acceptance/freeze timestamps, and produce a
   receipt that the initial return validator requires. No real identities are
   populated in the repository.
7. **Public-source import-closure gap.** The public preregistration manifest
   listed the human-assignment generator and several execution validators
   without every local Python module they import. In particular, the released
   governance and vocabulary assignments named validators that were absent
   from the public source set. The builder now parses every listed Python file,
   rejects an allowlist that is not closed over local imports, and requires the
   package marker, pinned runtime/development requirements, both released-task
   validators, and their transitive local dependencies. This establishes
   source-level replay closure; it does not claim that an external environment
   or model backend has been independently reproduced.
8. **Reviewer-packet least-access gap.** The assignment wrappers prohibited
   test access and cross-review visibility, but the repository did not define
   or verify the exact files delivered to each reviewer. A deterministic
   distribution specification and materializer now build four isolated packet
   roots outside the repository from the import-closed public source base plus
   only the assignment-specific wrapper, payload, and released inputs. The
   validator rejects missing, changed, forbidden, or extra files and rescans
   every packet file against all 25 sealed test IDs and titles. The roster
   validator now requires the live external packet root, exact distribution
   receipt and validation receipt, public manifest, sealed selection, and
   neutral distribution specification. It independently replays packet
   validation, binds each of the five role slots to the correct packet-manifest
   digest, and enforces validation--assignment--delivery--acceptance--freeze
   timestamp order plus exact-packet and no-other-packet attestations.
   Downstream return validation replays the frozen roster receipt and its
   content bindings without reopening material already delivered to reviewers.
   No real packet root, receipt, identity, delivery, or completed roster is
   checked in; those remain human-operational evidence required before the
   first submission.
9. **Citation-identity and claim-entailment drift.** The citation matrix
   accidentally described the Adelfio--Samet schema-extraction paper using the
   title of a distinct Venetis et al. paper; Auctus remained marked unverified
   despite an inspectable PVLDB record; Traub et al. and AutoDDG retained stale
   preprint-only metadata; and the literature review attributed row-sampling
   comparisons plus macro/per-label reporting to Korini--Bizer even though that
   paper fixes the first five rows and reports Micro-F1. The bibliography,
   citation matrix, manuscript keys, and literature review now use the verified
   primary records. A dated claim-entailment table separates what each source
   directly supports from prohibited extrapolations. These corrections change
   neither an NDP arm nor an observed outcome.
10. **Resource-accounting contract gap.** The publication prose required
    failed calls, retries, model latency, end-to-end latency, an exact price
    schedule, and hardware/runtime context, while the original executable score
    contract exposed only physical calls, tokens, one undifferentiated latency,
    and USD cost. The execution freeze now validates the pricing basis,
    effective date and source, exact call/token rates, cost boundary, treatment
    of failed/retried/reused calls, and the backend registry as the
    hardware/runtime source. Test-score schema v3 requires separate failed-call,
    retry, model-latency, and end-to-end-latency fields and reconciles them
    against record state. Backend preflight now requires GPU identity, GPU
    count, offload configuration, and context length. This closes the
    specification-to-implementation gap without claiming that a neutral
    template is a completed freeze or that any resource outcome has been
    observed.
11. **NDP confidence-evidence-chain gap.** The original feedback explicitly
    requested a calibration/reliability check and AURC sensitivity, while the
    response matrix said the suggestion was accepted. However, AURC existed
    only in the earlier generic architecture evaluator: NDP score artifacts
    carried aggregate correctness counts but no per-slot confidence, so the
    registered NDP inference path could not replay calibration or AURC. The
    scorer interface is now v3 and emits a confidence/exactness observation
    for every accepted applicable-known slot; test-score schema v3 validates
    and reconciles those observations; execution freeze requires a
    `confidence_score` field and freezes its arm-specific source,
    interpretation, range, decile bins, minimum support, tie rule, and pooling
    prohibitions. Registered inference now emits arm-by-label reliability
    bins, conditionally reportable Brier/ECE, risk--coverage curves, achieved
    coverage, and AURC. The 30-observation threshold suppresses calibration
    claims and Brier/ECE when support is sparse; it does not delete raw support
    or permit a favorable secondary metric to replace the primary endpoint.
12. **Original-feedback source-identity gap.** The earlier response captured
    Sculley et al. as the technical-debt anchor but omitted the separate Khan
    prompting-inversion example named in the slides. The user-supplied DOI
    `10.1007/978-3-031-78952-6_6` resolves to the Korini--Bizer CPA paper, not
    to Khan. The response matrix, literature review, bibliography, manuscript,
    and claim ledger now bind the two sources separately. Khan is used only as
    narrow GSM8K evidence that a restrictive prompt's relative value can
    reverse across model generations; it does not validate Model Capability
    Debt, schema-extraction transfer, or removal of any NDP component. A
    focused integration test prevents future DOI/source conflation.
13. **Collaborator-sign-off review-bundle gap.** The sign-off guide required
    Swathi to inspect the implementation audit, analysis plan, risk register,
    claim ledger, preregistration draft, and manuscript, but the v1 sign-off
    artifact cryptographically bound only the response matrix and amendment.
    A later change to a supporting artifact therefore would not necessarily
    invalidate a completed signature. Sign-off schema v2 now binds every
    required review source individually, freezes an ordered bundle digest, and
    requires a separate attestation that all bound materials were reviewed.
    The validator recomputes the complete bundle and rejects changed, missing,
    additional, or reordered bindings. The preregistration draft no longer
    embeds the neutral sign-off artifact's hash, avoiding a cycle because the
    sign-off bundle itself binds the preregistration draft. The public manifest
    remains the common content-addressed envelope for both.
14. **NDP-50 request-provenance attribution gap.** The accessible project
    conversation directly records Swathi supplying the NDP locator, referring
    back to the data repository, providing the CPA paper, and delivering the
    Phase 1 feedback file. It does not contain a Swathi-authored instruction
    specifying exactly 50 datasets. The new scope-provenance record therefore
    distinguishes collaborator-originated NDP direction from the investigators'
    operational interpretation and the protocol-defined 50-record sample,
    15/10/25 split, quota, estimand, and inferential choices. This prevents an
    internal project request from being misreported as sample-size
    justification, preregistration, independent validation, or approval.

One proposed metric remains intentionally incomplete: AUGRC has no frozen
machine implementation. It is therefore not an active or reportable NDP-50
endpoint. This is a disclosed boundary, not silent implementation debt.

## 4. Current conclusion

The current repository supports the recorded response decisions without
upgrading unobserved outcomes or incomplete human work. The implementation
audit is ready for collaborator review, but it is not collaborator approval.
The study remains blocked from semantic execution and test release until all
applicable human, freeze, preregistration, and independent-monitor gates replay.
