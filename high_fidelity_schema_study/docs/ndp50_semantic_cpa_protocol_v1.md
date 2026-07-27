# NDP-50 semantic and CPA preparation protocol v1

Status: neutral packets, source-bundle drafts, blind CPA screening, and the
corpus-level semantic-gold workflow are ready; independent screening, human
vocabulary/source approval, completed gold, prompts, and backend freeze remain
pending

## Scope and identity

Semantic annotation is prepared only for structurally extracted development and
validation resources. The opportunity manifest binds exact run, schema,
selection, detail-snapshot, download, and failure-ledger identities. It contains:

- 16 resource cases from 12 dataset clusters;
- 10 development and 6 validation resource cases;
- 277 unique field paths;
- 11 CSV cases requiring manual CPA applicability assessment;
- five non-tabular cases retained for the general semantic study but excluded
  from CPA.

The annotation unit is one resource. The primary statistical unit remains the
NDP dataset, so multiple resources from one dataset are clustered and cannot be
treated as independent samples.

No test identity, detail record, resource, schema, or label is present.

## Prediction-neutral packets

Each packet contains:

- the complete deterministic field inventory;
- physical type and bounded structural/statistical observations;
- the frozen NDP title as metadata evidence;
- content hashes of its schema and upstream opportunity manifest;
- stable source dataset/resource and analysis-cluster identities.

Logical type, semantic type, unit predictions, confidence, descriptions,
uncertainty labels, model outputs, and gold are removed. Absolute local paths are
reduced to source labels. Every packet passes the existing
`semantic-annotation-packet/v1` validator.

Packets are not yet annotation-ready because the corpus-specific vocabulary and
approved raw/documentation source bundles are not frozen.

## Vocabulary governance and freeze order

Vocabulary freeze precedes source-bundle approval. The current source bundles
bind `vocabulary_draft_v1.json`; approving them first and changing the
vocabulary later would invalidate their content identities. The required order
is therefore:

1. complete vocabulary discovery and consensus;
2. generate the frozen vocabulary through the validator;
3. rebuild all source bundles against that exact frozen hash;
4. obtain independent source-purpose approval;
5. begin CPA applicability screening and semantic gold annotation.

The neutral discovery artifact
`data/experiments/ndp50_v1/semantic/vocabulary_discovery_neutral_v1.json`
covers all 16 semantic cases and contains no human decision. The workflow
manifest
`data/experiments/ndp50_v1/semantic/vocabulary_review_workflow_v1.json`
binds that artifact, the draft vocabulary, all draft evidence catalogs, and the
exact implementation.

Vocabulary governance has two independent human stages:

- two non-developer reviewers inspect every case, decide whether the current
  vocabulary covers it, enumerate missing concepts, and propose only
  documentation-backed semantic types, units, aliases, or unit patterns;
- the deterministic union of both proposal sets becomes a candidate catalog,
  after which a fresh pair of two independent reviewers accepts or rejects
  every candidate and the frozen OOV/no-extension policies. Reusing either
  discovery reviewer is rejected to reduce proposal-ownership and recall bias.

At both stages, the pair must include at least one domain or scientific-metadata
curator and one annotation methodologist. Each submission records a
qualification summary and a negative conflict-of-interest declaration; distinct
IDs alone are not treated as sufficient evidence of qualified independence.

Only then is a disagreement worksheet revealed, and only to a fresh qualified
non-developer adjudicator who did not participate in discovery or candidate
decisions. The adjudicator records an allowed governance/methods role,
qualification summary, and negative conflict declaration. Consensus cannot
modify an agreed slot, every disagreement needs a human resolution and
locatable evidence, and the freeze builder re-runs all validators from the raw
submissions. A hand-authored `status=frozen` or `status=passed` file is
insufficient.
Physical types remain deterministic, logical types remain fixed, field-name
tokens remain discovery aids rather than labels, and applicable OOV values
remain JSON null.

The executable chain is exposed by:

```bash
python -m high_fidelity_schema_study.ndp50_vocabulary_workflow prepare ...
python -m high_fidelity_schema_study.ndp50_vocabulary_workflow validate-discovery ...
python -m high_fidelity_schema_study.ndp50_vocabulary_workflow build-candidates ...
python -m high_fidelity_schema_study.ndp50_vocabulary_workflow build-decision-template ...
python -m high_fidelity_schema_study.ndp50_vocabulary_workflow validate-decision ...
python -m high_fidelity_schema_study.ndp50_vocabulary_workflow compare ...
python -m high_fidelity_schema_study.ndp50_vocabulary_workflow build-consensus-template ...
python -m high_fidelity_schema_study.ndp50_vocabulary_workflow validate-consensus ...
python -m high_fidelity_schema_study.ndp50_vocabulary_workflow freeze ...
```

## Source-evidence approval

The downstream source-approval implementation is frozen in
`data/experiments/ndp50_v1/semantic/source_approval_workflow_spec_v1.json`.
Its current status is
`implementation_ready_waiting_on_frozen_vocabulary_and_rebuilt_bundles`.
An executable review template is deliberately not generated from the current
bundles because they bind a draft vocabulary and would become stale.

After vocabulary freeze and bundle rebuild, the workflow requires two qualified
independent reviewers to assess every evidence catalog item. For each item they
must decide whether its selector is locatable, whether it is relevant, and the
exact approved purposes:

- general semantic annotation;
- CPA relational-table assessment;
- CPA subject-column assessment;
- CPA property-annotation assessment.

A purpose cannot be granted to an unlocatable or irrelevant item. Subject-column
evidence must carry an explicit field-path scope. Each non-CPA case needs
general-semantic coverage; each CPA candidate additionally needs all three CPA
purposes and no unresolved documentation requirement.

The pair must again cover a domain/scientific-metadata curator and an annotation
methodologist. Consensus is assigned to a fresh qualified non-developer
adjudicator, with qualification and negative conflict declarations, who cannot
be either source reviewer. Agreement slots are immutable in consensus, every
disagreement requires an explicit human resolution, and only the validator can generate
`ndp50-source-bundle-approved-manifest/v1`. That manifest recursively binds and
replays the draft bundles, frozen vocabulary, review template, both independent
reviews, disagreement worksheet, and consensus. A draft manifest with a
manually changed status is rejected by the CPA evidence loader.

The executable stages are:

```bash
python -m high_fidelity_schema_study.ndp50_source_approval prepare ...
python -m high_fidelity_schema_study.ndp50_source_approval validate-review ...
python -m high_fidelity_schema_study.ndp50_source_approval compare ...
python -m high_fidelity_schema_study.ndp50_source_approval build-consensus-template ...
python -m high_fidelity_schema_study.ndp50_source_approval validate-consensus ...
python -m high_fidelity_schema_study.ndp50_source_approval approve ...
python -m high_fidelity_schema_study.ndp50_source_approval verify-approved ...
```

## Statistical feasibility and claim scope

The executable artifact
`data/experiments/ndp50_v1/semantic/power_feasibility_v1.json` binds the exact
selection, semantic-opportunity manifest, CPA design, implementation, and
power-analysis dependency. It contains no model or gold outcome.

The primary statistical unit is the NDP dataset cluster. Development resources
cannot be reused as confirmatory validation observations. The current
validation opportunities therefore comprise:

- six semantic resource cases from five dataset clusters;
- four CPA candidate resource cases from three dataset clusters.

The CPA design now carries a machine-validated estimand and scoring contract,
not only a list of metric names. The primary outcome is the within-dataset
rate of exactly correct accepted claims over all gold-applicable-known slots,
contrasted as `arm_b - arm_a`. Frozen CPA-inapplicable cases are excluded only
from the CPA estimand and remain reported by reason. Transport, timeout,
parser, explicit abstention, and OOV outcomes remain in the registered
coverage denominator as no correct accepted claim; post-outcome case deletion
is forbidden. Undefined selective-risk denominators are emitted as `null`
with their zero denominator rather than recoded as zero risk.

The registered primary test is a two-sided paired sign-flip test on
dataset-level mean differences. Up to 24 nonzero pairs use exact enumeration;
larger sets use 1,000,000 fixed-seed Monte Carlo flips with the plus-one
correction. The two co-primary p-values use Holm step-down control at
familywise alpha 0.05. The two hypotheses are fixed now, before downstream
human decisions or model outcomes: deterministic-only versus dataset-level
zero-shot, and that zero-shot arm versus deterministic verification of its
byte-identical response. Few-shot, prompt, row-sampling, and transfer
comparisons remain descriptive sensitivity analyses. Effect direction,
zero-difference handling, the
10,000-repetition dataset bootstrap percentile interval, metric
canonicalization, support counts, and failure accounting are all inherited
unchanged by the execution freeze and power workflow.

For two co-primary contrasts, conservative Holm planning uses the worst-case
per-contrast threshold `0.05 / 2 = 0.025`. With five nonzero dataset-level
paired differences, the smallest possible two-sided exact sign-flip p-value is
`0.0625`; with three it is `0.25`. At least seven nonzero paired differences
are required merely to make `p <= 0.025` attainable. This is a resolution
floor, not a power calculation: ties, noncomparability, missingness, or
heterogeneous effects can only weaken inference.

Even in the unrealistic all-success case, the two-sided 95% exact
Clopper-Pearson lower bound is approximately `0.4782` for five clusters and
`0.2924` for three. These are precision diagnostics, not observed performance
estimates and not population-prevalence intervals for the stratified NDP
sample.

Consequently, all development/validation semantic and CPA results are
predeclared descriptive feasibility-pilot evidence. They cannot support a
confirmatory superiority claim, and a null result cannot support “no effect.”
Structural acquisition/extraction validation retains its separately declared
scope.

The 25-dataset test split remains unopened. Before test execution, a frozen
power artifact derived only from non-blind calibration must specify the minimum
meaningful effect, paired-difference variability, multiplicity, target power,
and required comparable semantic-opportunity dataset count. Seven nonzero
pairs are necessary for exact p-value resolution but are not sufficient
evidence of adequate power. If the frozen opportunity count is missed after
test opening, the result remains underpowered; selectively adding datasets is
forbidden.

The neutral, content-addressed power material is:

- `data/experiments/ndp50_v1/semantic/power_freeze/power_policy_neutral_v1.json`;
- `data/experiments/ndp50_v1/semantic/power_freeze/power_freeze_workflow_v1.json`.

Readiness reports `power_freeze_workflow_ready=true` while
`test_power_plan_frozen=false`. The workflow does not reuse the generic
`A_vs_B`/`B_vs_C` labels: it must inherit the exact two contrast IDs and arm
pairs from the completed execution freeze. Before any development calibration
outcome is viewed, a study operator and a distinct non-developer statistical
methods reviewer must sign the minimum meaningful effect and rationale, target
power, selective-risk bound, SD floor and inflation, opportunity assurance,
and sensitivity scenarios.

After that policy hash is frozen, the calibration report must contain every
development semantic-opportunity dataset exactly once for each contrast,
aggregate resource cases at the dataset level, and explicitly exclude
validation and test outcomes. The validator recomputes equal-weight paired
effects, noncomparability, semantic-opportunity rate, Holm worst-case planning,
SD sensitivities, the required comparable-opportunity count, and binomial
assurance at the fixed 25-dataset test size. The paired-t calculation is
identified as a sample-size planning approximation; it does not replace or
redefine the registered primary analysis.

Prepare the neutral material now; policy validation, freezing, and replay are
run only after the required upstream artifacts exist:

```bash
python -m high_fidelity_schema_study.ndp50_power_freeze prepare \
  --selection high_fidelity_schema_study/data/experiments/ndp50_v1/selection.json \
  --opportunity-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/opportunity_manifest_v1.json \
  --cpa-design high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --policy-output high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/power_freeze/power_policy_neutral_v1.json \
  --workflow-output high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/power_freeze/power_freeze_workflow_v1.json

python -m high_fidelity_schema_study.ndp50_power_freeze validate-policy \
  --policy completed_power_policy.json \
  --selection high_fidelity_schema_study/data/experiments/ndp50_v1/selection.json \
  --opportunity-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/opportunity_manifest_v1.json \
  --cpa-design high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json \
  --execution-freeze execution_freeze.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output power_policy_validation.json

python -m high_fidelity_schema_study.ndp50_power_freeze freeze \
  --policy completed_power_policy.json \
  --calibration-report development_calibration_report.json \
  --selection high_fidelity_schema_study/data/experiments/ndp50_v1/selection.json \
  --opportunity-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/opportunity_manifest_v1.json \
  --cpa-design high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json \
  --execution-freeze execution_freeze.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output ndp50_power_freeze.json
```

`verify` accepts the same inputs plus `--frozen ndp50_power_freeze.json`.
No completed power policy, development calibration report, or power freeze is
present in the current snapshot.

## Immutable test-execution workflow

The neutral test-execution workflow is
`data/experiments/ndp50_v1/semantic/test_execution/test_execution_workflow_v1.json`.
It binds the selection, CPA design, execution-freeze workflow, power-freeze
workflow, and validator implementation while recording only the sealed test
count (`25`), not test identities. Readiness canonically rebuilds this artifact
and requires `test_execution_workflow_ready=true`; this implementation gate
does not authorize test opening.

After all upstream gates pass and test opening is explicitly authorized, the
test case manifest must give every selected test dataset exactly one
disposition. Every frozen case must then have one record for every registered
arm and one record for every separately derived OFAT sensitivity condition.
Failures and structured abstentions remain in both matrices and denominators.
Every record binds a score artifact whose slot counts, confusion counts,
model-call accounting, and identity are independently reconciled by the
validator. Every non-deterministic record also binds the raw UTF-8 response
artifact, the parsed-output artifact, and the exact case-gold artifact. The
execution receipt loads both the response parser and scorer from the frozen,
replayed qualification declaration. It reparses the bound raw response,
demands exact equality with the bound parsed slots, and then recomputes the
sufficient statistics from those slots and the bound gold. Thus the evidence
chain is raw response -> qualified parser v2 -> parsed output -> qualified
scorer v2 -> score -> registered inference. Internally self-consistent forged
scores, raw-response substitutions, coordinated parsed-output/score
substitutions, gold substitutions, stale parser or scorer code, and
interface-version drift are rejected for primary and sensitivity records.
The qualified runner v2 must reproduce the frozen schedule exactly: cases use
fixed-seed SHA-256 ranking, execution blocks use a seeded cyclic rotation
across case positions, and zero-shot plus replay remain one ordered dependency
block. Sequence numbers must match that schedule and timestamps cannot overlap
or contradict it. Runner, parser, and scorer actual-use contracts are covered
by synthetic conformance suite v3 before any study data are used. The
response-replay arm must bind and reuse the byte-identical zero-shot response
artifact and make zero physical model calls. A deviation registry is mandatory
even when empty, and post-outcome protocol, analysis, case-selection, or
sensitivity-condition changes are rejected.

The validator produces a content-addressed run receipt, a zero-call replay
comparison, and a missingness report. Publication reporting must include
dataset flow, all dispositions, case-by-arm failure counts, metric numerators
and denominators, undefined counts, calls/tokens/cost/latency, both
co-primary effects with intervals and raw/Holm-adjusted p-values, and all
deviations. Underpowered or non-analysable results cannot be restated as
evidence of no effect.

`ndp50_test_inference.py` implements the registered NDP analysis directly,
rather than reusing the incompatible generic A/B/C/D inference layer. It pools
registered slots within each dataset, forms the two frozen `arm_b - arm_a`
contrasts, excludes exact zero differences only from the sign-pattern count,
uses the registered exact/Monte Carlo sign-flip rule as the primary test,
builds the fixed-seed 10,000-repetition dataset bootstrap interval, and applies
Holm adjustment across exactly the two co-primary contrasts. It also reconciles
the realized comparable count against each frozen power requirement and
deterministically regenerates arm metrics, support counts, per-label F1,
undefined denominators, resource usage, dataset flow, failures, and claim
scope. It separately reports each registered OFAT sensitivity condition
against the primary zero-shot anchor using paired dataset-level descriptive
differences and explicitly emits no sensitivity p-value. Its `verify` command
must replay byte-for-byte before reporting.

Passing readiness alone does not open the test split. A completed
`ndp50-test-release-authorization/v1` must bind the exact ready snapshot,
selection, workflow, execution freeze, and power freeze. It requires signatures
from a study operator and a distinct qualified non-developer release monitor.
The validator rejects a shared identity, stale readiness implementation,
unmet `test_design_meets_pretest_assurance`, changed hashes, signatures after
authorization, or any claim that test outcomes were already observed. Only a
replayed `ndp50-test-release-receipt/v1` permits the witnessed opening event.
The case manifest then records authorization, opening, and case-freeze times;
execution records cannot predate that freeze.

Prepare only the neutral pre-release workflow now:

```bash
python -m high_fidelity_schema_study.ndp50_test_execution prepare-workflow \
  --selection high_fidelity_schema_study/data/experiments/ndp50_v1/selection.json \
  --cpa-design high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json \
  --execution-freeze-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/execution_freeze/execution_freeze_workflow_v1.json \
  --power-freeze-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/power_freeze/power_freeze_workflow_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/test_execution/test_execution_workflow_v1.json
```

`build-receipt`, `verify-receipt`, `build-missingness`, and the inference
`build`/`verify` commands are intentionally unusable until a passing
release-readiness snapshot, both completed freezes, and a replayed release
receipt exist. `build-release` and `verify-release` are the only commands that
can bridge passing readiness to an authorized opening. No completed release
authorization, release receipt, test case manifest, run manifest, test record,
score artifact, deviation registry, run receipt, missingness report, inference
result, or test result is present in the current snapshot.

## Vocabulary and source-bundle drafts

The conservative vocabulary draft begins with the previously frozen pre-NDP
calibration vocabulary. It automatically adds only deterministically observed
physical-type strings. It does not infer logical, semantic, or unit labels from
field names. A 111-token field lexicon and all field paths are retained solely as
human discovery aids; the artifact explicitly forbids promoting tokens without
approved documentation.

All 16 draft source bundles bind:

- the prediction-neutral annotation packet;
- the exact acquired raw payload and SHA-256;
- the exact compressed NDP `package_show` snapshot and SHA-256;
- per-field original-resource selectors;
- catalog title/notes selectors;
- the current draft vocabulary hash.

Every bundle passes structural and local file-identity validation. Passing these
mechanical validators does not establish semantic relevance or entailment.
Bundle status therefore remains
`draft_bundles_structurally_valid_not_annotation_ready`.

## Independent gold

The per-case two-annotator workflow is reused without automatic adjudication.
The NDP corpus wrapper is executable rather than a permanently false readiness
declaration:

- `data/experiments/ndp50_v1/semantic/gold/semantic_gold_index_neutral_v1.json`
  contains all 16 development/validation cases, no artifact paths, and no human
  decision;
- `data/experiments/ndp50_v1/semantic/gold/semantic_gold_workflow_spec_v1.json`
  binds the packet manifest, neutral index, exact corpus validator, source
  approval implementation, and per-case gold validator;
- readiness reports `semantic_gold_workflow_ready=true`, while
  `independent_gold_complete=false` until a validator-generated approval
  replays the entire corpus.

The enforced sequence is:

1. freeze a corpus-specific vocabulary from approved corpus documentation without
   inspecting model output;
2. freeze content-addressed source bundles and locatable evidence catalogs;
3. assign the same two qualified non-developer annotators;
4. collect and validate two independent submissions per case;
5. reveal only a deterministic disagreement worksheet after both submission
   hashes freeze;
6. require human resolutions for every disagreement;
7. validate a consensus artifact bound to both submissions and the worksheet.

The same two stable, distinct, non-developer annotators must cover every case.
Their registry records institution, qualifications, role, conflict status, and
signature date; together they must cover a domain/scientific-metadata curator
and an annotation methodologist. The consensus panel must be those same two
people. This is deliberately joint reconciliation rather than third-party
adjudication: both members are already role-qualified, conflict-cleared, and
stable across the corpus, and the validator requires the panel IDs to equal the
annotator registry. Completion permits no unresolved slot and no automatic adjudication.
Every evidence identifier used by either submission or consensus must be
approved specifically for `general_semantic_annotation`; presence in a draft
bundle alone is insufficient.

Applicability is assigned separately for physical type, logical type, semantic
type, and unit. Applicable unresolved values use JSON null. N/A is not scored as
correct or incorrect.

Prepare the neutral corpus index now. After frozen vocabulary and approved
sources exist, complete a separate copy with the two submissions, deterministic
disagreement report, and consensus for every case, then validate and approve:

```bash
python -m high_fidelity_schema_study.ndp50_semantic_gold prepare \
  --packet-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/annotation_pack_v1/manifest.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --index-output high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/gold/semantic_gold_index_neutral_v1.json \
  --workflow-output high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/gold/semantic_gold_workflow_spec_v1.json

python -m high_fidelity_schema_study.ndp50_semantic_gold validate-corpus \
  --index completed_semantic_gold_index.json \
  --packet-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/annotation_pack_v1/manifest.json \
  --approved-source-manifest approved_source_bundle_manifest.json \
  --vocabulary vocabulary_frozen.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output semantic_gold_validation.json

python -m high_fidelity_schema_study.ndp50_semantic_gold approve-corpus \
  --index completed_semantic_gold_index.json \
  --packet-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/annotation_pack_v1/manifest.json \
  --approved-source-manifest approved_source_bundle_manifest.json \
  --vocabulary vocabulary_frozen.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output semantic_gold_approval.json

python -m high_fidelity_schema_study.ndp50_semantic_gold verify-approved \
  --approved semantic_gold_approval.json \
  --packet-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/annotation_pack_v1/manifest.json \
  --approved-source-manifest approved_source_bundle_manifest.json \
  --vocabulary vocabulary_frozen.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output semantic_gold_approval_validation.json
```

## CPA applicability screen

The CPA candidate list is mechanical: a directly extracted CSV with at least two
unique field paths. Candidate status does not place the resource in the CPA
denominator.

Before any CPA prompt or model output is shown, two qualified independent
non-developers—one domain/scientific-metadata curator and one annotation
methodologist—must record qualifications, clear conflicts, and decide:

- whether the resource is a relational table;
- whether exactly one subject column is supported;
- the subject column's exact field path;
- whether target property annotation is meaningful.

CPA applicability requires all three boolean decisions to be true and a
supported subject field. Ambiguous subject columns are excluded from CPA only;
they remain in the general semantic study. Consensus occurs only after both
screening submissions are frozen.

### Executable blind-screen workflow

The content-addressed workflow manifest
`data/experiments/ndp50_v1/semantic/cpa_screen_workflow_v1.json` binds the
neutral screen, opportunity manifest, source-bundle manifest, and exact
validator implementation. It contains 11 cases from seven dataset clusters
(seven development and four validation), but contains no human decision.
Its current status is
`workflow_validated_screening_blocked_on_source_approval` and
`screening_execution_authorized=false`; the engineering workflow is ready, but
human screening may not begin against the draft, unapproved evidence bundles.

The validator enforces the following sequence:

1. each annotator independently copies and completes the neutral screen while
   model outputs remain hidden;
2. both submissions must retain the exact case order, resource identity, split,
   and complete field-path inventory;
3. each submission must contain three booleans, a logically consistent subject
   field, a rationale, and at least one evidence reference for every case;
   every reference must resolve to that case's approved evidence catalog, and a
   supported subject must have at least one reference applicable to its exact
   field path;
4. annotator and submission IDs must be distinct and non-placeholder, roles
   must cover curator and annotation methodologist, and both qualification and
   negative conflict declarations must validate;
5. only after both files are content-hashed may the deterministic disagreement
   worksheet be generated;
6. the worksheet reports agreement counts, observed agreement, and Cohen's
   kappa per decision slot. Kappa is explicitly null with status
   `undefined_degenerate_marginals` when both marginals are degenerate;
7. consensus is performed by a fresh qualified non-developer adjudicator who
   is neither screener; it may not alter any agreed slot, and every disagreed
   slot requires a specific human resolution, rationale, and evidence reference;
8. `cpa_applicable` is derived by the validator and cannot be independently
   asserted.

There is no majority vote, model adjudication, or automatic conflict
resolution. The readiness builder re-runs consensus validation from both
submissions, the worksheet, the neutral screen, and the consensus artifact; it
does not trust a hand-authored `passed` declaration.

The intended command sequence after the two human submissions exist is:

```bash
python -m high_fidelity_schema_study.ndp50_cpa_screen_workflow validate-independent --screen path/to/submission-a.json --neutral high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_applicability_screen_neutral_v1.json --source-bundle-manifest path/to/approved-source-bundle-manifest.json --output path/to/submission-a-validation.json
python -m high_fidelity_schema_study.ndp50_cpa_screen_workflow validate-independent --screen path/to/submission-b.json --neutral high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_applicability_screen_neutral_v1.json --source-bundle-manifest path/to/approved-source-bundle-manifest.json --output path/to/submission-b-validation.json
python -m high_fidelity_schema_study.ndp50_cpa_screen_workflow compare --screen-a path/to/submission-a.json --screen-b path/to/submission-b.json --neutral high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_applicability_screen_neutral_v1.json --source-bundle-manifest path/to/approved-source-bundle-manifest.json --output path/to/disagreements.json
python -m high_fidelity_schema_study.ndp50_cpa_screen_workflow build-consensus-template --screen-a path/to/submission-a.json --screen-b path/to/submission-b.json --neutral high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_applicability_screen_neutral_v1.json --source-bundle-manifest path/to/approved-source-bundle-manifest.json --worksheet path/to/disagreements.json --output path/to/consensus.json
```

## Adaptation of Korini and Bizer

The design adapts
[Column Property Annotation using Large Language Models](https://dl.acm.org/doi/10.1007/978-3-031-78952-6_6)
through zero-shot, one-shot, five-shot, similarity-selected demonstrations,
prompt factors, vocabulary, and row-sampling controls. The adaptation adds
this project's trust constraints:

- demonstrations are development-only;
- validation/test cases cannot become demonstrations;
- deterministic-only and dataset-level zero-shot are explicit baselines;
- one arm reuses the byte-identical semantic response and changes only
  deterministic verification;
- evidence validity, unsupported claims, verified coverage, selective risk,
  calls, tokens, latency, and cost are measured;
- dataset clustering, fixed-seed bootstrap, and multiplicity adjustment are
  mandatory;
- fine-tuning is outside the primary pilot unless separately registered.

CPA results are never generalized to hierarchical, semistructured, geospatial,
array, file-level, or relationship-discovery questions.

The reviewed
[author-hosted paper](https://www.uni-mannheim.de/media/Einrichtungen/dws/Files_Research/Web-based_Systems/pub/Korini-etal_Colum_Property_Annotation_using_Large_Languge_Models.pdf)
decomposes zero-shot prompts into task description, instructions, and
classification wording; serializes the first five rows as Markdown and fills
missing displayed cells from later rows; runs generation at temperature zero;
and compares random demonstrations with cosine-similarity selection using
`text-embedding-ada-002`. Few-shot examples are represented as user table
messages followed by assistant classification messages. These are provenance
for the NDP sensitivity factors, not defaults silently inherited by NDP.
The eventual execution freeze must explicitly bind the chosen Markdown/value
serialization, missing-value policy, row samplers, prompt wording, embedding or
other ranking implementation, seeds, and user/assistant message order.

This is an adaptation, not a direct replication. The paper studies CPA as
selection from a supplied relationship vocabulary and reports material
differences among prompt variants, models, demonstrations, and fine-tuning.
Its reported F1 improvements therefore are background evidence for design
choices, not effect-size priors or expected NDP performance. In particular:

- no result from GPT-3.5, GPT-4, SOLAR, RoBERTa, or the paper's fine-tuned
  models is transferred to the NDP analysis;
- the NDP property vocabulary, source evidence, subject-column decisions, and
  OOV policy must be frozen from the NDP workflow itself;
- model-family comparisons, fine-tuning, and cross-vocabulary transfer are
  excluded from confirmatory claims unless separately preregistered and
  powered;
- prompt and row-sampling variants are sensitivity analyses, not additional
  unadjusted opportunities to select a favorable result;
- pooled resource-, column-, or field-level micro-F1 is descriptive because
  those observations are clustered within datasets; dataset-cluster summaries
  remain the inferential unit;
- macro-F1, per-label F1, OOV rate, unsupported-claim rate, and verified
  coverage must accompany micro-F1 so a frequent-label gain cannot conceal
  failures on rare properties or abstained cases.

The primary case-by-arm matrix does not contain a random-demonstration arm or
a pre-registered held-out-domain contrast. It therefore cannot identify a
causal random-versus-similarity selection effect or cross-domain transfer
effect. The one- and five-shot arms are descriptive architecture arms in which
demonstration count and selection method remain bundled.

Prompt and row-sampler sensitivity use a separate, content-addressed
single-factor-at-a-time matrix. Exactly one prompt variant must match the
primary zero-shot prompt and factorization, and exactly one row sampler is the
primary sampler. Every non-primary prompt is executed with the primary sampler;
every non-primary sampler is executed with the primary prompt. Every frozen
case must appear under every derived condition. Unregistered factorial
interactions and post-outcome condition additions or deletions are rejected.
The freeze permits two to four prompt variants; together with the exact row
sampler registry this bounds the number of derived conditions. The run receipt
computes the maximum sensitivity calls as frozen cases multiplied by derived
conditions multiplied by maximum attempts, and verifies observed calls remain
within that bound.
The inference artifact reports paired dataset-level descriptive differences,
support counts, per-label metrics, and resource use, but performs no
confirmatory test or multiplicity-adjusted claim for these conditions.
Scientific-family stratification, if reported, remains descriptive and is not
evidence of transfer.

The authors' [TabAnnGPT repository](https://github.com/wbsg-uni-mannheim/TabAnnGPT)
provides the experiment code and data, but the current study has not frozen a
reviewed repository commit or reproduced that environment. Any later claim of
exact replication must bind the paper copy, repository commit, environment,
datasets, prompts, and scoring implementation; the current protocol makes no
such claim.

## Execution-freeze workflow

The content-addressed neutral configuration and workflow are:

- `data/experiments/ndp50_v1/semantic/execution_freeze/execution_freeze_config_neutral_v1.json`;
- `data/experiments/ndp50_v1/semantic/execution_freeze/demonstration_pool_workflow_v1.json`;
- `data/experiments/ndp50_v1/semantic/execution_freeze/execution_freeze_workflow_v1.json`.

They register five architecture arms and all three row-sampling sensitivities
from the CPA design but contain no selected prompt, backend, demonstration,
seed, or human decision. Readiness therefore reports
`execution_freeze_workflow_ready=true` and
`prompt_and_backend_frozen=false`.

The execution freeze also requires a replayable implementation-qualification
receipt. A file hash alone is insufficient: all eight responsibility slots
(`runner`, `response_cache`, `serializer`, `row_sampler`,
`demonstration_ranker`, `response_parser`, `scorer`, and
`cost_accounting`) must name a versioned Python entrypoint. The qualification
builder imports and calls every entrypoint with deterministic synthetic
conformance probes. These probes cover registered case/arm order, fixed-seed
hash-ranked cases, seeded cyclic execution blocks, byte-exact cache reuse,
canonical UTF-8 serialization, deterministic row selection, development-only
demonstration ranking, malformed-response rejection, actual-response parsing,
actual-case scoring,
coverage/selective-risk denominator handling, and frozen-schedule cost
arithmetic. The receipt binds every implementation, probe output, the
probe-suite hash, and the qualification implementation hash.

Qualification is synthetic-only:
`development_validation_or_test_data_used=false` is mandatory. The freeze
validator reruns the probes and requires the config's implementation map to
equal the qualified declaration exactly, so replacing only a scorer or
entrypoint invalidates the freeze.

Readiness also reports `demonstration_pool_workflow_ready=true`. The
demonstration-pool workflow deterministically includes every approved
development case and excludes validation and test cases. After semantic-gold
approval, its validator projects neutral structural packet observations into
the candidate input and projects each consensus field into exact
property-applicability/value targets. Execution-freeze replay therefore checks
few-shot labels against approved gold field by field; a content hash alone is
not sufficient. Rationale, evidence text, and annotator identity are excluded
from the model-facing projection.

A completed configuration must bind and replay the frozen vocabulary, approved
source manifest, CPA consensus, semantic-gold approval, data-governance audit,
and data-governance approval. It then freezes:

- exactly two dataset-level co-primary contrasts, dataset clustering, Holm
  adjustment, the exact/Monte Carlo sign-flip boundary, bootstrap repetitions,
  seed text, the scoring-contract hash, and all missingness rules;
- zero-, one-, and five-shot prompts, response schemas, candidate-vocabulary
  and OOV contract, exact user/assistant message ordering, and the paper's task
  description/instruction/classification-wording factorization;
- at least two separately identified prompt variants, reported only as
  descriptive sensitivity analyses;
- table format, column and row ordering, missing-value and displayed-cell fill
  policy, escaping, truncation, metadata fields, and maximum cell length;
- `head`, fixed-seed stratified, and fixed-seed adaptive row samplers, including
  implementation hashes, seeds, and parameters;
- a minimum five-case development-only demonstration pool bound to approved
  development gold, deterministic ranking and tie breaking, with validation
  and test cases forbidden;
- an operationally qualified backend registry, primary backend, temperature
  zero, seed, token limit, thinking mode, and an accuracy-independent backend
  selection declaration;
- runner, byte-response cache, serializer, row sampler, demonstration ranker,
  parser, scorer, cost accounting, their replayed synthetic qualification,
  execution order, retry policy, timeout, and maximum attempts.

The verification arm is required to consume the byte-identical zero-shot
response and make zero additional physical model calls. Local-only governance
also forces local similarity processing, no external backend transfer, and a
loopback primary endpoint. A distinct non-developer methods reviewer must sign
the configuration; the study operator may be a developer only with explicit
disclosure. Neither signatory may use observed semantic or gold outcomes to
select the configuration.

Only the validator can create and later replay the freeze:

```bash
python -m high_fidelity_schema_study.ndp50_execution_qualification prepare \
  --declaration execution_implementation_declaration.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output execution_implementation_qualification.json

python -m high_fidelity_schema_study.ndp50_execution_qualification verify \
  --receipt execution_implementation_qualification.json \
  --declaration execution_implementation_declaration.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1

python -m high_fidelity_schema_study.ndp50_demonstration_pool prepare \
  --packet-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/annotation_pack_v1/manifest.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/execution_freeze/demonstration_pool_workflow_v1.json

python -m high_fidelity_schema_study.ndp50_demonstration_pool build \
  --semantic-gold-approval semantic_gold_approval.json \
  --packet-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/annotation_pack_v1/manifest.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output development_demonstration_pool.json

python -m high_fidelity_schema_study.ndp50_demonstration_pool verify \
  --artifact development_demonstration_pool.json \
  --semantic-gold-approval semantic_gold_approval.json \
  --packet-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/annotation_pack_v1/manifest.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1

python -m high_fidelity_schema_study.ndp50_execution_freeze prepare \
  --cpa-design high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json \
  --packet-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/annotation_pack_v1/manifest.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --config-output high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/execution_freeze/execution_freeze_config_neutral_v1.json \
  --workflow-output high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/execution_freeze/execution_freeze_workflow_v1.json

python -m high_fidelity_schema_study.ndp50_execution_freeze validate-config \
  --config completed_execution_freeze_config.json \
  --cpa-design high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json \
  --packet-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/annotation_pack_v1/manifest.json \
  --vocabulary vocabulary_frozen.json \
  --approved-source-manifest approved_source_bundle_manifest.json \
  --cpa-consensus cpa_consensus.json \
  --semantic-gold-approval semantic_gold_approval.json \
  --data-governance-audit high_fidelity_schema_study/data/experiments/ndp50_v1/reports/data_governance_v1.json \
  --data-governance-approval data_governance_approval.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output execution_freeze_config_validation.json

python -m high_fidelity_schema_study.ndp50_execution_freeze freeze \
  --config completed_execution_freeze_config.json \
  --cpa-design high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json \
  --packet-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/annotation_pack_v1/manifest.json \
  --vocabulary vocabulary_frozen.json \
  --approved-source-manifest approved_source_bundle_manifest.json \
  --cpa-consensus cpa_consensus.json \
  --semantic-gold-approval semantic_gold_approval.json \
  --data-governance-audit high_fidelity_schema_study/data/experiments/ndp50_v1/reports/data_governance_v1.json \
  --data-governance-approval data_governance_approval.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output execution_freeze.json
```

`verify-frozen` accepts the same upstream arguments plus
`--frozen execution_freeze.json`. No completed configuration or freeze exists
in the current snapshot.

## Data provenance, license, and transfer governance

`data/experiments/ndp50_v1/reports/data_governance_v1.json` replays the
development and validation detail manifests, all 25 compressed CKAN detail
snapshots, and the frozen development/validation runs. It verifies snapshot
hashes, dataset identity, HTTPS catalog and acquired-resource transport, and
SHA-256 coverage for every acquired payload. It includes no test dataset
identity or detail.

The integrity result passes, but governance approval does not:

- 8 datasets have a standard or public-domain-style identifier;
- 2 have only a vague `other-open` or `other-attribution` designation;
- 2 explicitly state that the license is unspecified or not provided;
- 13 have no license identifier or title;
- none of the 25 snapshots provides a license URL;
- all 5,091 catalog resource URLs use HTTPS, but none carries a
  catalog-provided resource hash and only 7 have `last_modified`;
- all 17 payloads actually acquired for analysis have a local SHA-256 and an
  HTTPS final URL.

The original CKAN response bytes were not archived. Their captured body hashes
therefore cannot be independently recomputed from the parsed snapshots,
although each complete compressed snapshot itself is content-hashed. This is
reported as a provenance limitation rather than silently treated as full raw
response preservation.

Catalog license assertions are not legal approval. Before semantic execution
is frozen, a qualified stewardship reviewer and a distinct accountable
approver must resolve authoritative license and attribution terms and freeze:

1. whether model processing is local-only or permits transfer to an external
   provider, including retention and redaction rules;
2. which raw payloads, samples, metadata, and derived schemas may be
   redistributed;
3. what attribution must accompany analysis and published artifacts.

The executable neutral review and workflow are
`data/experiments/ndp50_v1/governance/data_governance_review_neutral_v1.json`
and
`data/experiments/ndp50_v1/governance/data_governance_review_workflow_v1.json`.
They cover exactly the 25 development/validation datasets in the replayed
audit. The stewardship signatory must be an institutional data steward or
research-compliance reviewer and a non-developer. The accountable signatory
must be a distinct principal investigator or institutional data controller.
Both record qualifications, institutional authority, conflict status, and an
ISO signature date.

Every dataset requires an authoritative HTTPS license source, resolved terms
and attribution, and explicit decisions for local analysis, external-model
transfer, raw-payload redistribution, metadata redistribution, and
derived-schema redistribution. A restrictive `false` decision is a valid
frozen policy; the workflow does not reinterpret it as approval. Study-level
processing must be either `local_only`, with every external-transfer decision
false, or `external_provider_approved_all_in_scope`, with verified provider
terms, retention/training-use policy, and every in-scope transfer decision
true. This records institutional governance, not legal advice.

The validator, rather than a human-edited status field, generates the approval
artifact and replays it from the embedded review, current audit, and exact
implementation. Until such an artifact exists,
`data_governance_policy_frozen=false`. This blocks execution freeze but does
not invalidate the already verified structural provenance.

Rebuild the audit from archived evidence:

```bash
python -m high_fidelity_schema_study.ndp50_data_governance build \
  --selection high_fidelity_schema_study/data/experiments/ndp50_v1/selection.json \
  --development-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/acquisition/development_detail_manifest.json \
  --development-details-dir high_fidelity_schema_study/data/experiments/ndp50_v1/acquisition/development_details \
  --development-run high_fidelity_schema_study/data/experiments/ndp50_v1/runs/development_run_v4.json \
  --validation-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/acquisition/validation_detail_manifest.json \
  --validation-details-dir high_fidelity_schema_study/data/experiments/ndp50_v1/acquisition/validation_details \
  --validation-run high_fidelity_schema_study/data/experiments/ndp50_v1/runs/validation_run_v3.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output high_fidelity_schema_study/data/experiments/ndp50_v1/reports/data_governance_v1.json
```

Prepare the neutral material, validate a completed human review, generate the
approval, and replay it:

```bash
python -m high_fidelity_schema_study.ndp50_data_governance_review prepare \
  --audit high_fidelity_schema_study/data/experiments/ndp50_v1/reports/data_governance_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --template-output high_fidelity_schema_study/data/experiments/ndp50_v1/governance/data_governance_review_neutral_v1.json \
  --workflow-output high_fidelity_schema_study/data/experiments/ndp50_v1/governance/data_governance_review_workflow_v1.json

python -m high_fidelity_schema_study.ndp50_data_governance_review validate-review \
  --review completed_data_governance_review.json \
  --audit high_fidelity_schema_study/data/experiments/ndp50_v1/reports/data_governance_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output data_governance_review_validation.json

python -m high_fidelity_schema_study.ndp50_data_governance_review approve \
  --review completed_data_governance_review.json \
  --audit high_fidelity_schema_study/data/experiments/ndp50_v1/reports/data_governance_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output data_governance_approval.json

python -m high_fidelity_schema_study.ndp50_data_governance_review verify-approved \
  --approved data_governance_approval.json \
  --audit high_fidelity_schema_study/data/experiments/ndp50_v1/reports/data_governance_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output data_governance_approval_validation.json
```

No completed review or approval is present in the current study snapshot.
After approval, rebuild readiness with
`--data-governance-approval data_governance_approval.json`; pass the same
optional flag to both handoff `build` and `validate`.

## Human handoff and release control

`data/experiments/ndp50_v1/semantic/human_handoff_v1.json` is the
content-addressed release manifest for work requiring human judgment. It binds
the current readiness report, vocabulary workflow and neutral template, source
approval specification and draft manifest, CPA workflow and neutral screen,
semantic-gold neutral index and workflow, power-feasibility report and neutral
pre-calibration power policy/workflow,
development demonstration-pool workflow, data-governance audit and neutral
review workflow, and every executable
implementation used by later stages.

The handoff is deliberately downstream of readiness and is validated
independently rather than being added back into readiness, which would create a
circular hash dependency. Its stages are:

1. data-governance review and accountable approval;
2. vocabulary governance;
3. source-bundle rebuild and approval;
4. parallel CPA applicability screening and semantic-gold review;
5. prompt, serialization, demonstration, and backend freeze;
6. non-blind calibration and power-plan freeze;
7. distinct-operator/independent-monitor test-release authorization;
8. authorized test execution.

Only stages marked `released` may be distributed as executable human
assignments. `completed` requires the corresponding validated consensus or
freeze artifact; generating a template never completes a stage. The current
artifact releases `data_governance_review` and `vocabulary_governance` in
parallel and locks every downstream stage.

The current vocabulary assignment requires two distinct, pseudonymous,
conflict-disclosed non-developer reviewers, covering a scientific metadata
curator role and an annotation-methodologist role. Each reviewer receives a
separate copy of the neutral discovery template and completes the full corpus.
Their files must be independently validated and content-hashed before any
comparison or disagreement reveal.

Build and replay validation use the same exact inputs:

```bash
python -m high_fidelity_schema_study.ndp50_human_handoff build \
  --readiness high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/readiness_report_v1.json \
  --packet-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/annotation_pack_v1/manifest.json \
  --vocabulary high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/vocabulary_draft_v1.json \
  --vocabulary-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/vocabulary_review_workflow_v1.json \
  --vocabulary-template high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/vocabulary_discovery_neutral_v1.json \
  --source-approval-spec high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/source_approval_workflow_spec_v1.json \
  --source-bundle-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/source_bundle_drafts_v1/manifest.json \
  --cpa-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_screen_workflow_v1.json \
  --cpa-screen high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_applicability_screen_neutral_v1.json \
  --cpa-design high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json \
  --power-feasibility high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/power_feasibility_v1.json \
  --power-policy-template high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/power_freeze/power_policy_neutral_v1.json \
  --power-freeze-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/power_freeze/power_freeze_workflow_v1.json \
  --data-governance high_fidelity_schema_study/data/experiments/ndp50_v1/reports/data_governance_v1.json \
  --data-governance-review-template high_fidelity_schema_study/data/experiments/ndp50_v1/governance/data_governance_review_neutral_v1.json \
  --data-governance-review-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/governance/data_governance_review_workflow_v1.json \
  --semantic-gold-index-template high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/gold/semantic_gold_index_neutral_v1.json \
  --semantic-gold-workflow-spec high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/gold/semantic_gold_workflow_spec_v1.json \
  --demonstration-pool-workflow-spec high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/execution_freeze/demonstration_pool_workflow_v1.json \
  --execution-freeze-config-template high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/execution_freeze/execution_freeze_config_neutral_v1.json \
  --execution-freeze-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/execution_freeze/execution_freeze_workflow_v1.json \
  --test-execution-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/test_execution/test_execution_workflow_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_handoff_v1.json

python -m high_fidelity_schema_study.ndp50_human_handoff validate \
  --artifact high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_handoff_v1.json \
  --readiness high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/readiness_report_v1.json \
  --packet-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/annotation_pack_v1/manifest.json \
  --vocabulary high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/vocabulary_draft_v1.json \
  --vocabulary-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/vocabulary_review_workflow_v1.json \
  --vocabulary-template high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/vocabulary_discovery_neutral_v1.json \
  --source-approval-spec high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/source_approval_workflow_spec_v1.json \
  --source-bundle-manifest high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/source_bundle_drafts_v1/manifest.json \
  --cpa-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_screen_workflow_v1.json \
  --cpa-screen high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_applicability_screen_neutral_v1.json \
  --cpa-design high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/cpa_design_draft_v1.json \
  --power-feasibility high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/power_feasibility_v1.json \
  --power-policy-template high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/power_freeze/power_policy_neutral_v1.json \
  --power-freeze-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/power_freeze/power_freeze_workflow_v1.json \
  --data-governance high_fidelity_schema_study/data/experiments/ndp50_v1/reports/data_governance_v1.json \
  --data-governance-review-template high_fidelity_schema_study/data/experiments/ndp50_v1/governance/data_governance_review_neutral_v1.json \
  --data-governance-review-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/governance/data_governance_review_workflow_v1.json \
  --semantic-gold-index-template high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/gold/semantic_gold_index_neutral_v1.json \
  --semantic-gold-workflow-spec high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/gold/semantic_gold_workflow_spec_v1.json \
  --demonstration-pool-workflow-spec high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/execution_freeze/demonstration_pool_workflow_v1.json \
  --execution-freeze-config-template high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/execution_freeze/execution_freeze_config_neutral_v1.json \
  --execution-freeze-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/execution_freeze/execution_freeze_workflow_v1.json \
  --test-execution-workflow high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/test_execution/test_execution_workflow_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1
```

The released work is materialized separately under
`semantic/human_assignments_v1/`. The package contains one sequential
data-governance review/countersignature assignment and two isolated vocabulary
discovery assignments. The vocabulary payloads are byte-identical copies of
the neutral template, while their wrappers are distinct and contain no
reviewer identity or human decision. The accountable governance signatory
receives the stewardship review only after its evidence fields are frozen;
this is a sequential countersignature, not a second independent form.

```bash
python -m high_fidelity_schema_study.ndp50_human_assignments prepare \
  --handoff high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_handoff_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output-dir high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1

python -m high_fidelity_schema_study.ndp50_human_assignments validate-release \
  --artifact high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_release_v1.json \
  --handoff high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_handoff_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_release_validation_v1.json
```

The neutral return manifest must not be marked complete until the governance
document has two distinct qualified signatories and an exact passing
validation receipt, and both vocabulary submissions have exact passing
receipts. A study operator must then atomically record both submission hashes
and attest that neither review, a candidate catalog, nor a disagreement report
was visible before that dual freeze. Only a passing validator-generated return
receipt authorizes construction of the vocabulary candidate catalog:

```bash
python -m high_fidelity_schema_study.ndp50_human_assignments validate-returns \
  --return-manifest completed_return_manifest.json \
  --assignment-release high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_release_v1.json \
  --handoff high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_handoff_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output human_assignment_return_validation.json
```

The repository contains no completed return manifest: identities, decisions,
signatures, dates, and independence attestations remain unfilled until real
human work occurs.

After the initial return validator passes, the transition command deterministically
rebuilds the candidate catalog from the two exact frozen discoveries. It then
creates two byte-identical decision payloads with distinct assignment wrappers.
The decision pair must cover scientific-metadata-curator and
annotation-methodologist roles and must be disjoint from the discovery pair.
No candidate catalog can be generated by this command before the initial
dual-freeze receipt passes, and no disagreement worksheet can be generated
before both decision receipts and hashes are frozen.

```bash
python -m high_fidelity_schema_study.ndp50_human_assignments prepare-decisions \
  --initial-return completed_return_manifest.json \
  --initial-return-validation human_assignment_return_validation.json \
  --initial-assignment-release high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_release_v1.json \
  --handoff high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_handoff_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output-dir candidate_decision_assignments

python -m high_fidelity_schema_study.ndp50_human_assignments validate-decision-release \
  --artifact candidate_decision_assignments/decision_assignment_release_v1.json \
  --initial-return completed_return_manifest.json \
  --initial-return-validation human_assignment_return_validation.json \
  --initial-assignment-release high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_release_v1.json \
  --handoff high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_handoff_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1

python -m high_fidelity_schema_study.ndp50_human_assignments validate-decision-returns \
  --return-manifest completed_decision_return_manifest.json \
  --decision-assignment-release candidate_decision_assignments/decision_assignment_release_v1.json \
  --initial-return completed_return_manifest.json \
  --initial-return-validation human_assignment_return_validation.json \
  --initial-assignment-release high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_assignments_v1/assignment_release_v1.json \
  --handoff high_fidelity_schema_study/data/experiments/ndp50_v1/semantic/human_handoff_v1.json \
  --study-root high_fidelity_schema_study/data/experiments/ndp50_v1 \
  --output candidate_decision_return_validation.json
```

These transition outputs do not yet exist in the study snapshot because no
real initial return has passed. The implementation and adversarial tests exist
now so the later human handoff does not require an improvised, unversioned
procedure.

After both candidate decisions pass and their hashes are frozen,
`prepare-consensus` deterministically recomputes the disagreement worksheet and
releases a neutral consensus assignment. `validate-consensus-release` replays
the complete discovery-to-decision chain before distribution, and
`validate-consensus-return` re-runs the underlying consensus validator before
authorizing vocabulary freeze:

```bash
python -m high_fidelity_schema_study.ndp50_human_assignments prepare-consensus ...
python -m high_fidelity_schema_study.ndp50_human_assignments validate-consensus-release ...
python -m high_fidelity_schema_study.ndp50_human_assignments validate-consensus-return ...
```

The consensus assignment excludes all four prior vocabulary reviewer IDs,
requires an allowed senior metadata/ontology/annotation-methods role, a
qualification summary, a negative conflict declaration, non-developer status,
and explicit completion attestation. Agreed slots remain immutable. These
artifacts also do not yet exist because the prerequisite human returns are
absent.

Any change to a bound upstream artifact or implementation invalidates the
handoff until it is rebuilt. Validation also hard-fails if readiness integrity
fails, a test-detail snapshot exists, the test split is reported open, or a
locked stage is manually changed to `released`.

## Current blockers

The following are required before semantic execution:

- two independent CPA applicability screens and consensus;
- a corpus-specific frozen vocabulary with OOV policy;
- approved source bundles with exact evidence selectors;
- resolved license/attribution terms and frozen model-transfer/redistribution
  policies;
- prompt text, serialization, row samplers, demonstration ranking, model,
  decoding parameters, and backend registry;
- two independent gold submissions and consensus;
- a frozen non-blind power plan before any test semantic outcome is inspected.

Until these gates pass, `semantic_validation_authorized=false` and
`test_authorized=false`.

The executable readiness artifact separately reports
`integrity_status=passed`, `readiness_status=blocked_as_expected`,
`vocabulary_review_workflow_ready=true`,
`vocabulary_frozen=false`,
`source_approval_workflow_implementation_ready=true`,
`semantic_power_feasibility_assessed=true`,
`power_freeze_workflow_ready=true`,
`data_governance_provenance_integrity=true`,
`data_governance_review_workflow_ready=true`,
`data_governance_policy_frozen=false`,
`semantic_gold_workflow_ready=true`,
`independent_gold_complete=false`,
`demonstration_pool_workflow_ready=true`,
`execution_freeze_workflow_ready=true`,
`prompt_and_backend_frozen=false`,
`validation_confirmatory_power_established=false`,
`test_power_plan_frozen=false`,
`cpa_screen_workflow_ready=true`,
`cpa_independent_screening_authorized=false`,
`cpa_applicability_consensus_complete=false`,
`semantic_execution_ready=false`, and `test_ready=false`. This separation
prevents successful workflow engineering or hashing from being misreported as
completed human screening or research readiness.
