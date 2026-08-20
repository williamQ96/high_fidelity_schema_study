# Semantic Blind Inference Protocol v1

Status: executable protocol; freeze before blind architecture execution

> **Scope note.** This document governs the earlier generic A/B/C/D study. It
> does not govern the NDP-50 named-arm analysis. NDP-50 uses the paired
> sign-flip primary test in its machine-readable CPA design and
> `docs/ndp50_statistical_analysis_plan_v1.md`. The paired-t primary analysis
> below must not be imported into NDP-50 after outcomes.

## 1. Boundary

This protocol analyzes only the frozen A/B/C/D semantic architecture study. It
does not change claim generation, add an architecture arm, tune a prompt, invoke
a model, or adjudicate gold. The dataset is the statistical unit. Field slots are
not treated as independent observations.

The executable implementation is `semantic_blind_inference.py`. A blind report
must use `minimal-architecture-experiment/v3-blind`; a development or calibration
report is rejected even when its JSON shape is otherwise compatible.

## 2. Three-artifact chain

The chain is deliberately split to avoid a circular or post-outcome analysis
freeze.

1. `semantic-blind-analysis-plan/v1` is generated and frozen before blind
   architecture execution. It binds the backend registry, power artifact,
   contrasts, alpha, estimators, random seeds, repetition counts, and analysis
   implementation hash. It cannot bind outcome reports that do not yet exist.
2. `semantic-blind-analysis-run/v1` is created after execution. It binds the
   already-frozen plan, blind manifest, and exactly one evaluation report for
   every registered backend by content hash.
3. `semantic-blind-inference/v1` is generated deterministically from the run
   manifest. Validation reconstructs the complete artifact from its hashed
   sources and requires exact equality.

The blind manifest binds the analysis-plan hash. The plan independently binds the
backend-registry and power-analysis hashes. The result therefore cannot switch an
analysis rule, backend panel, or required sample count after seeing outcomes.

## 3. Confirmatory analysis

The two co-primary contrasts are `A_vs_B` and `B_vs_C`. For the preregistered
primary backend, the outcome is the equal-weight mean dataset-level change in
correct accepted applicable-claim rate, in the direction right arm minus left
arm.

For each contrast the artifact reports:

- every included paired dataset effect and every exclusion reason;
- mean, sample standard deviation, median, minimum, and maximum;
- a two-sided one-sample Student t test on paired dataset differences;
- a two-sided Student-t confidence interval for the mean difference;
- a two-sided sign-flip sensitivity test using the absolute mean difference;
- a fixed-seed dataset percentile-bootstrap sensitivity interval;
- descriptive mean changes in raw correct claims, coverage, selective risk, and
  unsupported accepted model claims.

The two primary paired-t p-values receive Holm step-down family-wise-error
control at the frozen alpha. The sign-flip test and bootstrap interval are
sensitivity analyses; they do not replace a failed or unavailable primary test.
The sign-flip test is exact at or below the frozen case threshold and uses a
fixed-seed Monte Carlo estimate with a plus-one correction above it.

## 4. Backend and secondary boundaries

Only the registry-designated primary backend enters the confirmatory Holm family.
Other preregistered backends are model-family sensitivity conditions and are
reported separately. They are not pooled, ensembled, or used to select a more
favorable primary result.

`C_vs_D` is secondary. If any required C or D dataset row is non-comparable, the
tool reports the contrast as non-comparable and performs no partial-case
inferential substitute. This preserves the protocol rule that D is interpreted
only when its historical behavior ran completely under the selected backend.

## 5. Missingness and power

Each report must contain every preregistered semantic-opportunity case exactly
once and in frozen manifest order for every contrast. B/C replay provenance must
also contain every opportunity case exactly once, be valid, and show zero new C
semantic-generation calls. These checks prevent silent case deletion.

Primary contrasts use evaluator-marked comparable rows and retain all exclusions.
The observed comparable count is compared with the required opportunity count in
the frozen power artifact. Falling below that count changes the confirmatory
status to `underpowered_observed_opportunity_or_comparability`; it does not permit
post-outcome dataset replacement or sample-size extension.

## 6. Required provenance

For every backend report, the analyzer checks:

- blind-only report schema and role;
- exact blind case identity and order;
- exactly A/B/C/D summaries;
- registered model identifier;
- the exact frozen backend-registry hash, backend ID, role, and canonical backend
  record hash;
- registered endpoint, seed, and dataset-reasoner token limit when declared;
- B/C response-replay validity;
- complete contrast row identity.

The full per-backend variant summaries and architecture comparison remain in the
inference artifact so call, token, latency, cost, and failure measurements can be
reported beside quality outcomes.

Blind model execution itself must select `--backend-id` from the registry bound by
the blind manifest. Before making a model call, the harness checks registry hash,
qualification eligibility, served model identifier, endpoint, dataset-reasoner
seed/token limit, and the fixed legacy decoding contract. For example:

```powershell
python -m high_fidelity_schema_study.architecture_evaluation `
  --manifest path/to/frozen-blind-manifest.json `
  --backend-id frozen-primary-backend-id `
  --model exact-served-model-id `
  --api-base http://127.0.0.1:1234/v1 `
  --seed 0 `
  --max-tokens 4096 `
  --output-dir path/to/backend-run
```

The report records checkpoint hash, quantization, and runtime from the selected
frozen registry record. This is an execution-selection attestation, not a new
hash of the model bytes: the OpenAI-compatible API does not expose checkpoint
bytes. Checkpoint-byte identity therefore remains grounded in the earlier
qualification and registry-freeze chain and must not be described as runtime
rehashing.

## 7. Commands

Generate and validate the pre-execution plan:

```powershell
python -m high_fidelity_schema_study.semantic_blind_inference build-plan `
  --config path/to/blind-analysis-plan-config.json `
  --output path/to/blind-analysis-plan.json
python -m high_fidelity_schema_study.semantic_blind_inference validate-plan `
  --plan path/to/blind-analysis-plan.json
```

After all registered backend reports exist, generate and validate the result:

```powershell
python -m high_fidelity_schema_study.semantic_blind_inference analyze `
  --run-manifest path/to/blind-analysis-run.json `
  --output path/to/blind-inference.json
python -m high_fidelity_schema_study.semantic_blind_inference validate-result `
  --artifact path/to/blind-inference.json
```

Templates are `templates/semantic_blind_analysis_plan_config_template.json` and
`templates/semantic_blind_analysis_run_template.json`. Neither the run manifest
nor the result is a substitute for the pre-execution frozen plan.

## 8. Interpretation limits

A passed hash chain establishes procedural integrity, not model correctness,
exchangeability, or external validity beyond the sampled corpus. A small-model
failure remains backend-conditional unless model-family sensitivity evidence
supports a broader interpretation. A clean null, an underpowered result, and a
non-comparable D condition are valid study outcomes and must not trigger an
architecture change within this protocol.
