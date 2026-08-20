# Swathi feedback response matrix v1

Date: 2026-07-27  
Scope: semantic-architecture manuscript and NDP-50 external-validation track  
Source reviewed: `Feedback_Phase1.pptx` supplied by Swathi, postdoctoral research collaborator

## Purpose

This matrix converts the Phase 1 feedback into auditable research changes. It
distinguishes changes that can be incorporated immediately from changes that
would alter the registered experiment. It does not treat reviewer suggestions
as completed evidence and does not silently rewrite content-addressed NDP-50
artifacts.

Decision labels are:

- **accept**: incorporate now;
- **accept with boundary**: incorporate only with the stated claim or scope
  restriction;
- **pre-freeze decision gate**: potentially useful, but it changes the design
  and requires a versioned amendment before any affected outcome is observed;
- **do not adopt as stated**: retain the underlying concern but reject the
  proposed interpretation.

## Response matrix

| ID | Feedback theme | Decision | Incorporation into the latest NDP-50 update | Evidence or deliverable |
| --- | --- | --- | --- | --- |
| F01 | Position the work at the intersection of selective prediction, attributed generation, and controlled ablation | **Accept** | The paper now presents the contribution as an evaluation methodology for component attribution, not merely a schema-extraction system. | Revised English manuscript; `docs/literature/semantic_architecture_literature_review_2026-07-27.md` |
| F02 | Add adjacent column-annotation and metadata-generation work | **Accept with boundary** | Doduo, ArcheType, Korini--Bizer CPA, and AutoDDG are discussed as adjacent tasks. CTA, CPA, and dataset-description generation are not treated as equivalent to general scientific schema extraction. | Literature review, bibliography, manuscript related work |
| F03 | Anchor Model Capability Debt in technical debt and the prompting-inversion example | **Accept with boundary** | The term is explicitly defined as a project-specific operational construct derived from Sculley et al.'s ML technical-debt framing. Khan's 2025 arXiv preprint is included only as a narrow GSM8K example that restrictive prompt value can reverse across model generations; it does not validate the construct, generalize to schema extraction, or show that an NDP component is obsolete. | Revised manuscript, primary-source entailment audit, and bibliography |
| F04 | Be cautious with the word “causal” | **Accept** | “Causally controlled” is replaced by “replay-controlled” or “component-attribution.” The protocol may estimate effects of frozen component substitutions within the study, but it does not claim population-wide causality or mechanistic causation. | Revised title, research questions, captions, threats, and conclusion |
| F05 | Add stronger non-LLM and task-specific baselines | **Accept with boundary** | Deterministic-only is the primary non-LLM baseline. Doduo and ArcheType are scoped comparators for applicable CTA/CPA cases, not drop-in baselines for heterogeneous file extraction. | Baseline decision section in the protocol amendment |
| F06 | Add an evidence-free single-call baseline | **Pre-freeze decision gate** | It is not added to the co-primary family. A validation-only diagnostic may be registered before execution freeze if it has a precise information-removal contract, no access to test outcomes, a fixed call budget, and a stated safety purpose. | `docs/ndp50_feedback_improvement_amendment_v1.md` |
| F07 | Add a human or heuristic upper bound | **Do not adopt as stated** | Human consensus is the reference standard, not an “upper bound.” A deterministic name/value heuristic may be added only as a labelled secondary comparator if frozen before outcomes; it must not be called human performance. | Protocol amendment |
| F08 | Report calls, tokens, latency, and cost | **Accept** | Already required by the NDP-50 metric and execution contracts. Reporting is strengthened to require generated, reused, failed-attempt, and effective architecture totals, plus the exact price schedule and hardware/runtime context. | Existing NDP-50 design plus clarification in amendment/manuscript |
| F09 | Strengthen inter-annotator agreement reporting | **Accept with boundary** | Exact agreement, decision-slot support, disagreement rate, and Cohen’s kappa are required. Degenerate marginals remain explicitly undefined. Krippendorff’s alpha may be descriptive if its distance function and missing-data handling are preregistered; it is not a substitute for adjudication. | Existing executable screen workflow plus amendment/manuscript |
| F10 | Add calibration/reliability checks and AURC sensitivity | **Accept with boundary** | Primary inference remains the dataset-level rate of exactly correct accepted claims. NDP test-score v3 now binds every accepted applicable-known prediction to a replayed `confidence_score` and exact-correctness indicator. Frozen per-arm/per-label decile reliability bins, Brier score, fixed-bin ECE, right-continuous whole-tie-group risk--coverage curves, and AURC over achieved coverage are secondary and descriptive. Brier/ECE and calibration wording are suppressed below 30 accepted predictions per arm/label; confidence is never evidence or verification, and scales are not pooled across arms or labels. AUGRC remains inactive until separately implemented and frozen. | Executable scorer/test/inference contracts, revised manuscript, amendment, and focused tests |
| F11 | Add a second model | **Pre-freeze decision gate** | A second model family is allowed only as a preregistered sensitivity condition with a separately qualified backend, identical inputs and scoring, and no role in rescuing or selecting the primary result. | Protocol amendment |
| F12 | Publicly preregister the frozen protocol | **Accept** | A time-stamped OSF or Zenodo registration receipt is a mandatory pre-test publication artifact. The receipt must bind the public protocol, analysis plan, artifact manifest, and hashes without exposing sealed test identities. `test_ready` now remains false until collaborator feedback sign-off and an independently verified external receipt both replay. The sign-off, external-registration, and release-authorization stages are separated so the required human work is executable without circular prerequisites. | Protocol amendment, manuscript freeze block, preregistration draft, `ndp50_publication_gate.py`, bound neutral sign-off artifact, and released collaborator assignment |
| F13 | Add formal power analysis | **Already incorporated** | NDP-50 already has a neutral power-policy template, dataset-level planning, Holm-aware resolution checks, opportunity assurance, and an underpowered stopping rule. No claim is upgraded merely because the workflow exists. | `ndp50_power_freeze.py`; power workflow artifacts |
| F14 | Address benchmark contamination | **Accept with boundary** | Model pretraining exposure is treated as an unmeasured threat. Development cases are excluded from confirmatory inference by protocol, not because contamination can be proven absent. Results must not imply that a sealed split guarantees pretraining non-exposure. | Revised literature review and threats-to-validity text |
| F15 | Address annotation anchoring | **Accept with boundary** | Independent submissions freeze before disagreement reveal, and model outputs remain hidden. Berzak et al. motivates anchoring controls generally; it is not cited as schema-specific validation. | Existing human workflow plus revised manuscript |
| F16 | Clarify Swathi’s collaboration role | **Accept** | Swathi may review literature, claims, baselines, protocol amendments, and interpretation. Sign-off schema v2 binds the complete supporting review-material list and ordered digest so later source drift invalidates the signature. Because she is an active project collaborator, she cannot fill a slot requiring a blind independent annotator, fresh adjudicator, independent methods reviewer, or independent test-release monitor. | Role table in protocol amendment, v2 executable sign-off validator, and `docs/ndp50_swathi_feedback_signoff_guide_v1.md` |

## Source-identity clarification

The user-supplied DOI `10.1007/978-3-031-78952-6_6` resolves to Korini and
Bizer's *Column Property Annotation Using Large Language Models*, not to
Khan's prompting-inversion paper. The two sources support different claims and
must not be conflated:

- Korini--Bizer supports bounded CPA prompt, demonstration, vocabulary, and
  model/fine-tuning design precedents;
- Khan's separate arXiv preprint `2510.22251` provides only a narrow GSM8K
  example of a cross-model prompt-effect reversal.

Neither source validates Model Capability Debt or demonstrates an NDP-50
effect.

## Baseline decision

The confirmatory NDP-50 study retains two co-primary contrasts:

1. deterministic-only versus dataset-level zero-shot semantic augmentation;
2. the zero-shot response versus deterministic verification of the
   byte-identical response.

This preserves the clean intervention already encoded in the executable design.
The following are not silently added to that family:

- an evidence-free model call;
- Doduo or ArcheType;
- a heuristic name-only system;
- a second model family;
- fine-tuning.

Each may be informative in a distinct secondary study, but adding it now to the
co-primary family would change multiplicity, power, execution cost, and the
meaning of the frozen comparison. Any inclusion therefore requires a new
versioned design, updated power assessment, implementation qualification, and
fresh hashes before the affected split is run.

## Claim-language rules

The manuscript and reports must use the following hierarchy:

- **fact** for directly replayed artifact observations;
- **descriptive association** for unadjusted or non-confirmatory comparisons;
- **controlled component effect within this frozen system** only for a
  predeclared contrast whose replay, inputs, scoring, and comparability gates
  pass;
- **generalization** only within the stated sampling frame and uncertainty;
- never use “no effect” for an underpowered or non-analysable result.

“Causal” must not be used as shorthand for a clean-looking difference. If the
term is retained anywhere, it must name the intervention, estimand,
identification assumptions, analysis population, and failure conditions.

## Completion status

This response matrix completes feedback triage, not the human review or the
experiment. Immediate manuscript and protocol-document changes are actionable.
The following remain external or pre-freeze gates:

- collaborator sign-off on the response matrix (the bound assignment is
  released, but no completed human return is present);
- real human governance, vocabulary, source, applicability, and gold work;
- decision on optional evidence-free, heuristic, or second-model sensitivities;
- completed execution and power freezes;
- public preregistration receipt;
- independent test-release authorization.

The claim-by-claim implementation audit is maintained in
`docs/semantic_architecture_claim_ledger_v1.md`. The preregistration text is
prepared but remains explicitly unsubmitted and cannot be counted as a
completed gate.
The item-level implementation/evidence audit is
`docs/ndp50_feedback_implementation_audit_v1.md`; it explicitly distinguishes
machine implementation from documented boundaries, inactive proposals, and
human/external evidence still absent.

The local implementation prevents the preregistration requirement from
remaining prose-only: the readiness report records separate false gates for
collaborator sign-off and independently verified external registration, and
the test-release validator requires both. This control does not complete either
human/external action.
