# Qwen3.6-27B backend qualification rerun — 2026-07-15

## Decision

**Operationally eligible under every frozen backend-qualification threshold.**

This result establishes that the served Qwen3.6-27B Q4_K_M condition can execute
the frozen semantic architecture contracts and preserve the B/C causal boundary.
It does not contain gold, estimate semantic accuracy, compare A/B/C/D quality, or
provide evidence of external generalization.

## Corrected runtime condition

- model: `qwen/qwen3.6-27b@q4_k_m`
- quantization: GGUF Q4_K_M
- loaded context: 16,384
- LM Studio version: 0.4.18, reported by the operator but not exposed by the API
- thinking: disabled in LM Studio and requested as disabled by the backend
- B: temperature 0, seed 0, maximum 4,096 output tokens
- D: historical temperature 0.2, no seed, maximum 1,000 output tokens

A one-call prequalification gate used the smallest frozen calibration case and was
excluded from qualification metrics. It produced contract-valid JSON with
`reasoning_tokens=0`, `finish_reason=stop`, and 2,721 total context tokens.

## Frozen-threshold results

| Criterion | Observed | Required | Result |
|---|---:|---:|---|
| Semantic-opportunity cases | 8 | >= 8 | pass |
| B contract-valid rate | 1.0 | >= 0.95 | pass |
| B target-scope-valid rate | 1.0 | 1.0 | pass |
| B/C replay identity | 1.0 | 1.0 | pass |
| B exact repeatability | 1.0 | 1.0 | pass |
| B timeout rate | 0.0 | 0.0 | pass |
| B truncation rate | 0.0 | 0.0 | pass |
| B context fit and telemetry | 1.0 / 1.0 | 1.0 / 1.0 | pass |
| D contract-valid rate | 1.0 | >= 0.95 | pass |
| D timeout rate | 0.0 | 0.0 | pass |
| D truncation rate | 0.0 | 0.0 | pass |
| D context fit and telemetry | 1.0 / 1.0 | 1.0 / 1.0 | pass |

Every B repeat produced byte-identical response hashes. Every paired C run consumed
the exact B hash and made zero semantic generation calls. The largest B call used
13,306 observed tokens; the largest `input + max_tokens` request budget was 14,142,
leaving 2,242 tokens below the loaded context limit.

## Operational cost and legacy surface

B used 16 physical calls for the two-repeat qualification, 76,976 input tokens,
26,436 output tokens, and a mean attempt latency of 27.95 seconds.

D used 59 physical calls for eight dataset attempts, 79,571 input tokens, 19,547
output tokens, and a mean dataset latency of 44.61 seconds. The HDF5 case alone
required 22 per-field calls. `functional_traits.csv` had one failed historical
free-JSON shape attempt followed by a successful schema fallback; all attempt
records and telemetry were retained. This is part of D's preserved failure surface,
not a new retry mechanism.

These figures establish an operational-cost difference but do not establish a
quality difference.

## Remaining freeze boundary

The backend is operationally eligible, but its identity is not yet complete for a
blind protocol freeze. The exact checkpoint-file SHA-256 is unavailable, and the
LM Studio 0.4.18 version is operator-reported rather than machine-observed through
the endpoint. Both must be bound in an auditable registry or preregistration
receipt before blind gold is unsealed.

There is no operational reason from this run to replace Qwen3.6-27B with GLM,
Llama, or a smaller Qwen. Alternative families remain sensitivity conditions or
fallbacks; they should not be introduced merely because the invalidated 8K/thinking
run failed.
