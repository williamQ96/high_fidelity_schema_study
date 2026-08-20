# NDP-50 methodological risk register v1

Date: 2026-07-27  
Status: active pre-test register  
Review cadence: at every protocol, freeze, preregistration, and manuscript
revision

## 1. Rating convention

- **Critical**: can invalidate a confirmatory result or test-release authority.
- **High**: can materially bias interpretation or external validity.
- **Moderate**: can reduce precision, comparability, or reproducibility.
- **Low**: bounded reporting or presentation risk.

Status values are `open`, `controlled-pretest`, `externally pending`, or
`realization pending`. A control is not a completed empirical result.

## 2. Register

| ID | Risk | Severity | Current status | Control/evidence | Residual rule |
| --- | --- | --- | --- | --- | --- |
| MR01 | Test identities or outcomes influence prompts, arms, scorers, or exclusions | Critical | controlled-pretest | sealed 25-case split; release receipt; immutable execution workflow | Any exposure becomes a deviation and may invalidate affected inference |
| MR02 | B/C comparison silently regenerates a response | Critical | controlled-pretest | byte-identical raw-response binding; zero-new-call check | Any replay failure makes the contrast noncomparable |
| MR03 | Fields/resources are treated as independent observations | Critical | controlled-pretest | dataset-level aggregation in design and inference code | Publications must expose dataset counts and clustering |
| MR04 | Sign-flip test is misinterpreted as assumption-free mean inference | High | controlled-pretest | statistical analysis plan states sign-exchangeability assumption | Severe asymmetry downgrades the p-value to sensitivity evidence |
| MR05 | Equal-weight quota sample is presented as catalog prevalence | High | controlled-pretest | selection-design claim limit; SAP target definition | No full-catalog prevalence claim without design-weighted extension |
| MR06 | Small opportunity count makes null or superiority claims underpowered | Critical | externally pending | pre-calibration power policy, assurance, frozen stopping rule | Missed count produces underpowered/nonanalysable reporting, never rescue sampling |
| MR07 | Minimum effect or SD assumptions are selected after calibration | Critical | externally pending | signed pre-calibration policy and separate calibration artifact | A late policy cannot support confirmatory inference |
| MR08 | Annotators are called qualified without a reproducible qualification gate | Critical | externally pending | readiness gate and 11-stage handoff require matching calibration summary | Gold cannot complete until handbook, vocabulary, receipt, and IDs match |
| MR09 | System output anchors applicability or gold labels | High | controlled-pretest | prediction-blind packets and immutable independent hashes | Any output exposure is a recorded deviation with case/person scope |
| MR10 | High agreement is treated as label validity | High | controlled-pretest | exact agreement, marginals, kappa definedness, and consensus separated | Report evidence and ambiguity; never call kappa accuracy |
| MR11 | Collaborator review is represented as independent validation | High | controlled-pretest | role matrix and collaborator sign-off guide exclude active collaborators from blind roles and require explicit non-independence | Swathi's review is collaborator review with disclosure |
| MR12 | Public data availability is treated as processing or redistribution permission | Critical | externally pending | steward review plus distinct accountable approval | No semantic execution until signed governance approval replays |
| MR13 | Model-pretraining exposure is described as ruled out | High | open | sealed project-side split; contamination threat statement | Claims remain “cannot be ruled out” absent direct evidence |
| MR14 | Confidence scales are pooled across incompatible properties/models | Moderate | controlled-pretest | property-specific curves, tie rules, achieved coverage | AURC/AUGRC remain secondary and cannot rescue the primary endpoint |
| MR15 | Cost comparisons omit failed calls, retries, upstream replay cost, price scope, or distinct model/end-to-end latency | Moderate | controlled-pretest | execution freeze validates pricing basis/date/source, exact call/token rates, local-compute treatment, failed/retry/reuse inclusion, backend hardware/runtime identity, and score-v3 telemetry coherence | Report the frozen schedule and scope, runtime/hardware, failed/retry counts, both latency measures, reused upstream cost, and missing telemetry; do not monetize local compute when the frozen basis says it is unmonetized |
| MR16 | Learned CTA/CPA or second-model baselines are added after outcomes | High | controlled-pretest | inactive in design v1; versioned extension required | No post-outcome baseline shopping |
| MR17 | Remote resource mutation breaks provenance | High | realization pending | archived detail snapshots, payload hashes, transport records | Report inaccessible/mutated resources; do not silently replace cases |
| MR18 | Bootstrap interval is described as a catalog design-based interval | Moderate | controlled-pretest | SAP labels quota-weighted whole-dataset resampling boundary | Interval cannot support full-catalog prevalence language |
| MR19 | Undefined denominators are recoded as favorable zeros | High | controlled-pretest | explicit `null` plus denominator policy | All undefined counts and reasons appear in tables |
| MR20 | Multiple secondary metrics enable favorable-result selection | High | controlled-pretest | exactly two-value Holm family; secondary hierarchy and claim ledger | Report ranking disagreements; never replace primary endpoint post hoc |
| MR21 | External preregistration is claimed from a local draft | Critical | externally pending | visible draft banner and unresolved DOI/timestamp | Only a verified immutable external receipt satisfies the gate |
| MR22 | Passing software tests is presented as scientific validation | Moderate | controlled-pretest | claim ledger separates engineering and empirical evidence | Test counts support reproducibility only |
| MR23 | Public preregistration attachments reveal sealed identities directly or through an unsafe path | Critical | controlled-pretest | sorted text-source allowlist; path restrictions; exact ID/title scan; human disclosure review | Local exact-match checks do not rule out indirect re-identification; the external attachment set must be reviewed again |
| MR24 | A prose-only preregistration requirement is bypassed by machine test-release gates | Critical | controlled-pretest | publication-gate workflow; separate collaborator sign-off and independently verified external-receipt gates in readiness and release validation | `test_ready` remains false until both exact artifacts replay; neither artifact alone authorizes opening |
| MR25 | Circular stage prerequisites make required collaborator sign-off or external registration impossible to complete | Critical | controlled-pretest | separate initial feedback-signoff, post-freeze external-registration, and test-release-authorization stages; replayed assignment release | A publication-gate artifact cannot be both a prerequisite for and an output of the same release condition |
| MR26 | A feedback response or literature claim is labelled incorporated when it is only mentioned, planned, inactive, or not entailed by its cited source | High | controlled-pretest | item-level F01--F16 implementation audit separates machine implementation, documented boundaries, inactive proposals, and human/external evidence; primary-source claim-entailment audit records supported and prohibited extrapolations | Manuscript and sign-off language must preserve the audited status; bibliographic identity alone is not claim support; AUGRC and optional baselines remain inactive until separately frozen |
| MR27 | A structurally valid human assignment is operationally ambiguous, causing inconsistent filenames, missing receipts, cross-review leakage, or hand-edited derived artifacts | High | controlled-pretest | all four initial assignment wrappers specify required/forbidden actions, exact output names, return slots, and validator commands; focused replay tests cover every contract | Human work remains incomplete until exact returned artifacts and receipts replay; instructions do not substitute for decisions |
| MR28 | A downstream validator prints a passing result that is never persisted or bound, leaving no durable evidence for handoff or independent replay | High | controlled-pretest | all affected calibration, gold, qualification, demonstration, power, and inference replay commands accept `--output`; handoff stages enumerate validation and replay artifacts; focused CLI-contract test | Console output alone cannot satisfy a gate; the exact generated receipt must be stored, hashed, and replayed |
| MR29 | Reviewer identities or eligibility declarations are assigned after submissions begin, allowing role shopping, collaborator leakage into independent slots, or unverifiable timing | Critical | controlled-pretest | five-slot roster binds the exact release and handoff; assignment, acceptance, and freeze timestamps; role/conflict/participation/access attestations; exact roster receipt required by return validation | The neutral roster is not evidence of assignment; all five real acceptances must be frozen and validated before the first human submission |
| MR30 | A public source manifest lists entry points but omits local imported modules, so independent reviewers cannot replay the released validators from the registered source set | High | controlled-pretest | AST-based local-import closure check; package marker; pinned requirement files; governance and vocabulary validators plus transitive dependencies in the sorted allowlist | Source closure does not prove operating-system, hardware, external-service, or model-backend reproducibility; those environments and receipts remain separately required |
| MR31 | A reviewer receives the full repository, another reviewer's packet, or unlisted files, exposing sealed identities or enabling cross-review contamination despite a prose prohibition | Critical | controlled-pretest | deterministic four-packet least-access specification; materialization outside the repository; exact file-set/hash validation; forbidden-wrapper checks; full sealed ID/title rescan; strict roster validation replays the live packet root and both distribution receipts, binds every role slot to the correct packet-manifest digest, and enforces validation-before-delivery timing plus exact/no-other-packet attestations | No real packet, receipt, delivery, or completed roster exists yet; no submission may begin until the strict validator produces the exact frozen roster receipt. Later return validation replays that content-addressed receipt rather than claiming to re-observe delivery |
| MR32 | Calibration or AURC is promised in prose but cannot be replayed from NDP artifacts, or sparse/incomparable confidence scores are pooled into a favorable claim | High | controlled-pretest | scorer v3 and score v3 bind accepted-slot confidence to exact correctness; execution freeze requires arm-specific source/interpretation, fixed deciles, 30-observation claim threshold, whole-tie-group AURC, and no arm/label pooling; inference replay regenerates all diagnostics | Confidence remains secondary and may be only an ordering score. Below-threshold groups expose support/bins/AURC but no Brier, ECE, or calibration claim; AUGRC remains inactive and no confidence metric can replace the primary endpoint |
| MR33 | Collaborator sign-off binds only a summary response while supporting analysis, risk, claim, literature, or manuscript sources can drift after review | High | controlled-pretest | feedback sign-off schema v2 binds every required review source, an ordered bundle digest, and a dedicated all-materials-reviewed attestation; validator replay rejects changed, missing, additional, or reordered bindings | Swathi's sign-off remains collaborator review rather than independent validation; any bound-source change invalidates the sign-off and requires a regenerated neutral payload plus fresh review |
| MR34 | Internal correspondence is overstated as proof that a collaborator specified or justified the exact 50-record design | High | controlled-pretest | dated scope-provenance record separates directly observed correspondence, operational interpretation, and investigator-defined sample/split/analysis choices; the record is included in the public package and collaborator review bundle | Describe NDP as collaborator-originated direction and NDP-50 as the investigators' preregistered operationalization; do not attribute the exact number, split, power, or approval to Swathi without direct evidence |

## 3. Release audit

Before test release, the independent monitor must verify that:

- no Critical risk remains `open`;
- every `externally pending` Critical risk has a validated signed artifact;
- each realization-pending risk has a frozen disposition rule;
- the current claim ledger contains no prohibited wording;
- the public package passes sealed-identity leakage checks;
- the public Python source set passes local-import closure checks;
- every reviewer packet and its least-access distribution receipt replay;
- the five-slot roster binds the replayed distribution receipt, correct packet
  manifest per role, delivery timestamp, and receipt attestations before any
  human submission;
- the uploaded external attachment list matches the replayed local allowlist
  and manifest;
- the risk register hash is bound by the preregistration artifact manifest.

If a new risk is discovered after outcomes, it receives a new ID and deviation
record. Existing risk text cannot be rewritten to make an observed result
appear prespecified.
