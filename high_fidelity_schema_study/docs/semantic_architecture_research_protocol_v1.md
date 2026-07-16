# Semantic Architecture Research Protocol v1

Status: draft for calibration; architecture and causal contrasts frozen
Supersedes: semantic claims inferred from the nine-case synthetic development set

## 1. Primary research question

On independently selected and annotated blind scientific datasets, what causal contribution do one-call dataset-level semantic reasoning and deterministic verification make beyond deterministic extraction?

The primary estimand is the equal-weight mean dataset-level change in the rate of
correct accepted applicable semantic claims. The raw correct-claim gain and
dataset-level selective-risk change are co-reported. Field observations within one
dataset are not treated as independent experimental units; pooled-slot summaries
are descriptive only.

## 2. Fixed architecture arms

No additional arm may be added to this protocol.

| Arm | Fixed behavior | Model-call boundary |
| --- | --- | ---: |
| A | Deterministic claims only | 0 |
| B | A plus one dataset-level semantic response | At most 1 per semantic-opportunity dataset |
| C | Exact B response plus deterministic verification | 0 new generation calls; effective cost includes B |
| D | Historical per-field/manual-group scheduler and merge | Historical scheduler and fallback policy |

## 3. Pre-registered causal contrasts

### A versus B

Measures what one dataset-level semantic response adds beyond deterministic extraction:

- additional correct and incorrect accepted claims;
- coverage and end-to-end accuracy change;
- selective-risk and AURC change;
- unsupported proposed and accepted claims;
- effective calls, tokens, latency, failures, and configured cost.

### B versus C

Holds semantic generation exactly constant. Reports:

- B-accepted claims rejected or abstained by C;
- incorrect claims removed and correct claims lost;
- unsupported claims removed;
- coverage loss and selective-risk change.

A replay mismatch or any new C semantic call invalidates this contrast.

`A_vs_B` and `B_vs_C` are the two co-primary contrasts. Their final two-sided
p-values use Holm family-wise-error control. `C_vs_D` is secondary and is never
allowed to replace a failed co-primary comparison.

### C versus D

Compares the minimal hybrid with the historical architecture under the same backend identity. It is interpreted only when both arms are complete and all semantic targets are gold-covered.

## 4. Outcomes

Primary outcomes:

- end-to-end applicable-value accuracy;
- coverage of applicable-value slots;
- selective risk among accepted applicable-value predictions;
- correct accepted applicable-claim rate gain per dataset (primary, equal dataset
  weights);
- raw correct accepted semantic-claim gain per dataset;
- unsupported accepted-model-claim rate;
- model/architecture failure rate.

Secondary outcomes:

- confidence-tie-grouped AURC over achieved coverage;
- applicable-unknown abstention accuracy;
- N/A false-positive rate;
- model evidence-reference validity;
- effective calls, tokens, model latency, end-to-end latency, and configured cost;
- controlled failure taxonomy.

Overall and per-property results are reported. Dataset-level paired effects and
intervals are primary; pooled field-level intervals may be descriptive only. The
evaluation artifact persists every per-dataset paired difference so the primary
estimand cannot be reconstructed from pooled counts after outcome inspection.

The selective-risk bound, minimum meaningful effect, and required dataset count
will be filled from annotation/model calibration before blind sampling. They may
not be selected from blind outcomes. The exact executable calculation,
multiplicity policy, sensitivity requirements, and limitations are specified in
`docs/semantic_power_analysis_protocol_v1.md`.

## 5. Blind benchmark design

The blind corpus must:

- contain real external scientific datasets not used in development, prompts, or existing gold;
- be stratified by scientific family, file format, semantic evidence sufficiency, and difficulty;
- contain enough scorable semantic-opportunity datasets according to a calibration-based power analysis;
- cover every deterministic semantic target in gold;
- preserve datasets as the primary statistical clusters;
- freeze task files, gold files, backend registry, protocol, power analysis, and
  the executing architecture/evaluator/unit-normalization implementation by
  content hash.

Candidate-frame construction, known-nonblind byte-hash/source-identity exclusion,
sampling-design registration, deterministic selection, and manifest-order binding follow
`docs/semantic_blind_sampling_protocol_v1.md`. Randomization controls selection
within the declared frame only; it does not justify claims that the frame represents
all scientific datasets.

Retrieval queries, planted qrels, post-freeze conformance packs, and the nine synthetic development cases are excluded.

## 6. Gold independence

Two annotators who did not develop the system independently annotate each blind case. They may inspect the original dataset and approved source documentation, but not A/B/C/D outputs. Independent labels and evidence spans are retained before consensus adjudication.

Before blind work, the same pair must pass the preregistered nine-case calibration
gate in `docs/semantic_annotator_calibration_protocol_v1.md`. Blind preflight binds
the passing summary and requires identical annotator IDs, handbook hash, and
vocabulary hash.

The gold contract is defined in `docs/semantic_gold_annotation_handbook_v1.md`.
The executable independent-submission, disagreement, and consensus hash chain is
defined in `docs/semantic_gold_workflow_protocol_v1.md` and enforced by final
preflight. No automatic adjudicator is permitted.

## 7. Backend conditions

The planned local panel contains one frozen quantized checkpoint from each family:

- GLM5.2;
- Qwen3.6;
- Llama 3.3.

The intended range is approximately 27B-70B, constrained by stable local RTX 5090 execution. Exact checkpoint, quantization, file hash, runtime, runtime version, context limit, offload configuration, model identifier, endpoint, decoding parameters, prompt hash, and response-schema hash are frozen in a backend registry.

One backend is designated primary before blind gold is unsealed. The other local families are model-sensitivity conditions. They are not ensembled and do not vote.

A larger ceiling backend may be added only if it is registered before blind unsealing. A backend added after inspecting blind results is follow-up evidence and cannot replace or rescue the primary analysis.

## 8. Backend qualification

Qualification uses non-blind calibration cases and evaluates:

- endpoint/runtime stability;
- contract-valid response rate;
- target-scope compliance;
- repeatability under frozen decoding;
- context fit and truncation;
- timeout and failure rate;
- token, latency, and hardware feasibility;
- B/C replay identity.

Primary-backend selection is based on predeclared operational eligibility, not on which architecture wins calibration comparisons.

The executable qualification design, fixed eight-case non-blind manifest, frozen
thresholds, and infrastructure defect record are specified in
`docs/semantic_backend_qualification_protocol_v1.md`. Qualification reports are
content-hashed into the backend registry, and freeze preflight checks that every
registry summary exactly matches its raw report.

## 9. Freeze and execution

Before blind execution:

1. complete annotator calibration and handbook freeze;
2. complete power analysis and corpus sampling;
3. generate the blind inference plan specified in
   `docs/semantic_blind_inference_protocol_v1.md`;
4. bind that plan into the blind manifest and pass manifest/backend preflight;
5. freeze all content hashes;
6. run a non-blind operational rehearsal;
7. record the primary backend and sensitivity backends.

Blind runs are executed once in frozen manifest order. Selective reruns are forbidden. An infrastructure-invalid run may be repeated only as a complete registered run with the original artifacts retained.

Every model-backed blind run must select a qualification-eligible `backend_id`
from the exact registry hashed by the blind manifest. The execution harness fails
before its first model call if the registry, model identifier, endpoint, seed, or
token limit differs. The report persists the selected registry/backend-record
hash chain; checkpoint bytes remain an attestation from qualification because the
OpenAI-compatible runtime does not expose them for rehashing.

After execution, a separate analysis-run manifest binds the frozen plan, blind
manifest, and one report for every registered backend. The inference artifact is
then rebuilt deterministically; development-schema reports, backend identity
mismatches, missing opportunity rows, and invalid B/C replay block analysis.

## 10. Comparability and stopping

An affected contrast is non-comparable when:

- a semantic target lacks gold;
- B or C is partial, malformed, or missing;
- B/C raw response identity differs;
- C makes a new semantic generation call;
- D lacks its required historical behavior/dependency;
- frozen file or backend hashes do not match.

No result is repaired by prompt changes, extra calls, agents, judges, or a new architecture arm.

The study terminates with the observed result:

- architecture-level conclusion when effects are stable across predeclared backends;
- backend-conditional conclusion when model-family interaction is material;
- clean null when semantic augmentation adds no reliable value;
- benchmark/evaluation contribution only when opportunities or comparability are insufficient.
