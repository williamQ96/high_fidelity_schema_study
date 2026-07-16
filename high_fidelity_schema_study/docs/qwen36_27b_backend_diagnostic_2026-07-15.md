# Qwen3.6-27B backend qualification diagnostic — 2026-07-15

## Evidentiary status

This was a non-blind operational run over the frozen eight-case backend
calibration manifest. It did not access gold and cannot estimate A/B/C/D accuracy
or architecture effects. The run exposed evaluator and runtime defects and is
therefore invalidated as a candidate qualification. Its original JSON is retained
unchanged, and a machine-readable invalidation sidecar binds its SHA-256.

## Bound backend

- OpenAI-compatible model identifier: `qwen/qwen3.6-27b`
- selected variant: `qwen/qwen3.6-27b@q4_k_m`
- format and quantization: GGUF, Q4_K_M, four bits per weight
- reported model size: 17,478,734,335 bytes
- loaded context: 8,192 tokens
- advertised maximum context: 262,144 tokens
- flash attention: enabled
- KV-cache GPU offload: enabled
- parallel setting: 4
- speculative decoding: disabled
- B decoding: temperature 0, seed 0, maximum 4,096 output tokens
- D decoding: preserved temperature 0.2, no seed, maximum 1,000 output tokens
- checkpoint-file SHA-256: unavailable
- LM Studio runtime version: unavailable

The missing checkpoint hash and runtime version remain protocol-freeze blockers,
even after a later successful rerun.

## Uncorrected source-run observations

The immutable source report recorded 16 B attempts and eight D dataset attempts.
Only 2/16 B attempts produced contract-valid output. Twelve B attempts terminated
at the generation/context boundary, and both HDF5 attempts were rejected before
generation because a 10,044-token prompt exceeded the loaded 8,192-token context.
Seven of eight datasets produced byte-stable B response hashes across repeats; the
HDF5 case produced no semantic response. C made zero semantic generation calls in
every attempt.

D produced one contract-valid dataset result out of eight and used 23 physical
model calls. Those D token/context summaries are not valid because the original
failure path dropped successful earlier group records and failed fallback records.

These are failure-forensic observations, not eligibility rates. In particular,
the source report's target-scope and replay-identity rates must not be cited.

## Runtime failure diagnosis

The model's generated content shows that reasoning was not disabled. For the
smallest successful case, the server reported 3,254 completion tokens, including
2,995 reasoning tokens, for 879 characters of final JSON. Most larger cases
exhausted the output or remaining context before reaching final JSON.

One additional infrastructure diagnostic used the same smallest calibration
prompt, schema, temperature, seed, and output ceiling while supplying both
`reasoning="off"` and `chat_template_kwargs.enable_thinking=false`. It still
reported 2,995 reasoning tokens and the same 3,254-token completion. This call was
not included in any candidate metric. The observation establishes that the
served runtime did not honor the requested reasoning-off state; it does not by
itself identify the exact runtime version or internal cause.

LM Studio's public changelog states that version 0.4.18 fixed a condition in which
reasoning on/off could be ignored for models with custom reasoning settings. The
current runtime version is unavailable, so applicability is an inference rather
than a confirmed version diagnosis.

## Harness defects exposed and fixed

1. Context fit now uses input plus output tokens for each physical call. D retry
   attempts are kept separate, and requested `input + max_tokens` headroom is
   reported descriptively.
2. Malformed B failures now retain raw response hashes through the B-to-C failure
   cache. C records the identical hash while making zero semantic calls.
3. An unparseable response is now target-scope non-evaluable rather than silently
   valid.
4. D now retains successful earlier group records and every free-JSON/schema
   fallback attempt when a later group fails.
5. LM Studio's selected native model record is embedded in future reports, while
   unavailable runtime-version and checkpoint-hash fields remain explicit.

These fixes change measurement and provenance only. They do not change A/B/C/D,
the prompts, schemas, manifest, vocabulary, claim validation, or semantic call
budgets.

## Decision

**Qwen3.6-27B Q4_K_M is not yet qualified or disqualified as a semantic backend.**
The completed run is invalidated because its harness defects affect replay,
target-scope, and D measurement, while its runtime configuration independently
prevents the full frozen task set from executing.

Before rerunning:

1. use an LM Studio runtime where reasoning-off is demonstrably honored (the
   upstream fix record makes 0.4.18 or newer the minimum defensible version);
2. reload the exact checkpoint with at least a 16,384-token context;
3. record runtime version and checkpoint SHA-256; and
4. rerun the unchanged manifest and thresholds once.

Using a larger context or a fixed runtime is infrastructure compatibility, not
architecture tuning. Reducing targets, shortening case-specific prompts, changing
schemas, or lowering one architecture's burden would invalidate comparability and
must not be used as a workaround.
