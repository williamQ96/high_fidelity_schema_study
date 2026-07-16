# Semantic backend qualification protocol v1

Status: candidate-backend execution pending
Scope: operational eligibility only; no gold and no A/B/C/D effect estimates

## Purpose

Qualification answers whether a local backend can execute the already fixed
semantic architectures without breaking their contracts or causal boundaries. It
does not ask whether a backend is accurate and must not be used to choose whichever
model makes B, C, or D look strongest.

The fixed calibration manifest is
`data/experiments/semantic_backend_qualification_v1/manifest.json`. Its eight tasks
were already exposed during earlier development and can never enter the blind
benchmark. Selection preceded candidate GLM5.2, Qwen3.6, and Llama 3.3 runs and was
based on format, modality, semantic-target count, and legacy scheduling coverage.
There are eight semantic-opportunity datasets and 74 targets.

## Execution

For each registered backend:

1. resolve the exact model identifier from the local OpenAI-compatible `/models`
   endpoint and, when LM Studio's native metadata endpoint is available, bind the
   selected quantization and loaded-instance configuration into the report;
2. verify every calibration task against its frozen SHA-256 and declared target
   count;
3. bind the frozen calibration vocabulary hash and expose its canonical semantic
   types, units, aliases, and bounded unit patterns to the dataset-level contract;
4. run B twice per dataset at temperature 0 and frozen seed;
5. immediately run C through the B response cache after each B run;
6. assert C makes zero physical model calls and consumes the identical response
   hash, including when the response is contract-invalid;
7. run D once per dataset with its unchanged free-JSON-then-schema retry policy,
   temperature 0.2, and historical grouping;
8. persist raw and parsed responses, request/response hashes, normalized claims,
   issues, finish reason, calls, tokens, and latency;
9. calculate context fit from input plus output tokens for each physical call. Keep
   D's free-JSON and schema-fallback attempts separate; never compare their
   aggregate token count with a per-call context limit. Also report whether each
   requested `input + max_tokens` budget fits as descriptive headroom telemetry.

D does not receive the controlled-vocabulary payload because doing so would alter
the historical architecture. Vocabulary absence remains part of D's documented
failure surface, while B and C share the exact same vocabulary-bearing request.

The runner never resolves or opens a `gold_file` key. It rejects blind manifests.

## Frozen eligibility policy

The thresholds below are fixed before running any intended candidate family. The
one-case Qwen3.5-35B infrastructure smoke is not a candidate-family qualification
and was not used to optimize thresholds.

The registry-level qualification policy also freezes one calibration-manifest
SHA-256 and one calibration-vocabulary SHA-256. Every candidate report must bind
those exact values. Merely supplying a syntactically valid but different hash is a
blocking preflight error because it would make the backend panel non-comparable.

| Criterion | Threshold | Rationale |
|---|---:|---|
| Semantic-opportunity datasets | >= 8 | Use the full fixed operational calibration set |
| Dataset contract-valid rate | >= 0.95 | With 16 attempts, one failure yields 0.9375 and therefore fails |
| Dataset target-scope-valid rate | 1.0 | Any out-of-scope claim violates the experimental contract |
| B/C replay identity rate | 1.0 | Any mismatch invalidates the B-vs-C contrast |
| Exact dataset response repeatability | 1.0 | Required under temperature 0 and a frozen seed |
| Dataset timeout rate | 0.0 | A timed-out opportunity would be non-comparable in blind execution |
| Dataset truncation rate | 0.0 | Truncated output is contract-invalid and context-dependent |
| Dataset context-fit rate | 1.0 | Every observed request must fit the frozen runtime context |
| Dataset context telemetry observed | 1.0 | Missing token telemetry cannot establish context fit |
| Legacy contract-valid rate | >= 0.95 | With eight attempts, any failure falls below threshold |
| Legacy timeout rate | 0.0 | D must remain comparable on every calibration dataset |
| Legacy truncation rate | 0.0 | A truncated D response cannot validate historical behavior |
| Legacy context-fit rate | 1.0 | Every D call must fit the frozen context |
| Legacy context telemetry observed | 1.0 | Missing telemetry cannot establish fit |

The eligibility `context-fit` measures observed per-call input plus output tokens.
Requested-budget fit is reported separately because `max_tokens` is a ceiling, not
observed consumption, and is not an additional post-hoc eligibility criterion.

D exact repeatability is measured descriptively but is not an eligibility criterion:
the preserved historical architecture intentionally uses temperature 0.2 without a
seed. Changing that policy would change D rather than qualify it.

## Candidate panel and selection

The intended candidate families remain GLM5.2, Qwen3.6, and Llama 3.3, using exact
quantized checkpoints in the approximately 27B-70B range on the local RTX 5090.
Every eligible candidate remains in the sensitivity panel. The primary backend is
chosen by a predeclared operational rule (hardware feasibility, eligibility, then
latency/resource budget), never architecture accuracy. Exact checkpoint files,
quantization, runtime, context, and offload identity must be registered before
blind gold is unsealed.

An optional larger ceiling backend is confirmatory only and must be registered
before blind unsealing. It cannot replace an ineligible or unfavorable primary run.

## Infrastructure smoke and defect record

On 2026-07-15, the endpoint exposed `qwen/qwen3.5-35b-a3b`; none of the intended
candidate families was available. A single-case smoke therefore tested only the
transport and artifact path.

The first smoke found three pre-freeze defects:

- the dataset payload did not expose the parser's allowed logical-type vocabulary;
- replay identity incorrectly depended on contract-valid status;
- exact repeatability incorrectly depended on contract-valid status.

The stable model response used `logical_type="quantity"`, which the parser correctly
rejected but the prompt had never prohibited. The smallest contract fix exposed the
existing allowed vocabulary in the observation payload and prompt. Measurement was
changed so replay identity and response repeatability are independent of semantic or
contract correctness. A fourth provenance defect was fixed so partial C runs retain
`reused_response_hash`.

Under the same model, case, decoding, and call budget, the second smoke produced:

- dataset contract-valid rate 1.0;
- target-scope-valid rate 1.0;
- B/C replay identity 1.0 with C making zero calls;
- exact repeatability 1.0;
- no timeout or truncation;
- D contract-valid rate 1.0, using two physical calls because its historical first
  free-JSON attempt required the preserved schema fallback.

These observations validate the defect fixes and local transport only. One case,
one non-candidate model, and a manually supplied smoke context length provide no
backend eligibility, architecture comparison, or external-validity evidence.

A third smoke reran the same case after the controlled semantic-type and unit
vocabulary became part of the B/C observation contract. Its immutable report is
`data/experiments/semantic_backend_qualification_v1/qwen35_35b_infrastructure_smoke_vocabulary_contract_2026-07-15.json`.
The report SHA-256 is
`3a2af2e563e6131cfba5ae20772edad4348ca74104d317bc1473fcf2e5554592`.
It binds:

- model identifier `qwen/qwen3.5-35b-a3b`;
- calibration vocabulary SHA-256
  `874548a10f8871449be9b749c99e95e72e8852d261324abc8fa3c492246ed888`;
- dataset prompt SHA-256
  `1b75583a35549a5cbdfecc79be5796eb358d2e5f976f5483b25756a81f8f8060`;
- dataset response-schema SHA-256
  `e79212874554daf93c401578b97963f45934854b22b6786ee41ae60bf8dfd7ca`.

Across its two B attempts, contract validity, target-scope validity, B/C replay
identity, exact response repeatability, and observed context fit were all 1.0;
timeouts and truncations were 0.0. B used one physical call per attempt, while C
used zero and consumed the identical response hash. The two B responses were
byte-identical. D remained contract-valid but used two physical calls because its
historical first free-JSON attempt required the preserved schema fallback. The B
response selected the in-vocabulary label `precipitation` for `max_VIL`; because
qualification has no gold, this is a contract observation, not evidence that the
claim is correct. This third smoke supersedes the earlier smoke artifacts only as
the current contract check; it remains non-candidate, single-case infrastructure
evidence.

## Remaining blockers

- Install/load exact GLM5.2, Qwen3.6, and Llama 3.3 candidate checkpoints.
- Record checkpoint hashes, quantization, runtime version, actual context limit,
  and offload configuration.
- Freeze the common calibration-manifest and calibration-vocabulary hashes in the
  registry policy, then bind both exact values in every qualification report.
- Run the complete eight-case qualification once per candidate.
- Persist each qualification report and bind its content hash into the backend
  registry.
- Apply the frozen thresholds and designate the primary backend before blind gold
  is unsealed.

## Qwen3.6 candidate diagnostic on 2026-07-15

The first full Qwen3.6-27B Q4_K_M execution is an invalidated diagnostic, not a
candidate qualification. It bound an 8,192-token loaded context, which rejected a
10,044-token HDF5 prompt, and its served runtime did not honor reasoning-off. The
run also exposed three measurement defects: malformed failure responses lost C
replay identity, unparseable output was counted as target-scope valid, and partial
D failure dropped earlier group/fallback provenance. All three were fixed without
changing the architectures, prompts, schemas, cases, or call budgets. The original
run and its invalidation sidecar remain immutable evidence of the defect discovery.

The corrected rerun used the same checkpoint family and quantization with thinking
disabled and a 16,384-token loaded context. A one-call gate first established zero
reasoning tokens and a valid contract response; it was excluded from qualification
metrics. The full rerun then passed every frozen operational threshold, including
exact B repeatability and B/C replay identity. Qwen3.6-27B Q4_K_M is therefore an
operationally eligible candidate. Checkpoint-file SHA-256 and an auditable runtime
version binding remain required before blind protocol freeze.
