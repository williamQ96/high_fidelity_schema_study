# Minimal Experimental Redesign: A/B/C/D

This experiment answers one narrow question:

> How far can the historical semantic architecture be compressed before correctness or selective risk becomes worse?

It does not replace the production extraction path. All variants consume the same existing semantic-grounding task, so parser output, samples, documentation, and evidence are held constant.

## Variants

| Variant | Architecture | Model-call policy | Trust behavior |
| --- | --- | ---: | --- |
| A | Deterministic only | 0 | Existing parser output; unknown values abstain |
| B | A + dataset-level reasoner | At most 1 per dataset | Model claims are accepted as unverified candidates |
| C | B + deterministic evidence verifier | Same reasoner call as B | Invalid, missing, or cross-field evidence abstains; deterministic conflicts reject |
| D | Existing per-field/manual-group pipeline | One call per legacy field/group | Preserves current merge behavior, including non-empty-string evidence acceptance |

B and C receive the exact same cached model response inside one harness run. Their difference therefore isolates the verifier instead of model sampling variance.

## Minimal claim contract

Every output property is represented as a claim with:

- field and property;
- value and generation source;
- evidence references;
- confidence;
- verification level and status;
- decision and reason.

Confidence never establishes verification. C can accept a confidence `0.0` claim when its evidence references are valid, and it can abstain on a confidence `1.0` claim when its evidence is nonexistent.

C provides failure-mode-independent reference and conflict checking; it does **not** prove semantic entailment. Its strongest model-only state is `evidence_grounded`, not `verified truth`.

## Unified metrics

The harness reports the same metrics for every variant:

- applicable-value accuracy;
- coverage;
- selective accuracy and selective risk;
- abstention rate;
- false-positive rate on explicit N/A targets and abstention accuracy on applicable-but-unknown targets;
- evidence-reference validity;
- unverified and unsupported accepted-model-claim rates;
- risk/coverage curve and AURC over achieved coverage;
- model calls, input/output tokens, latency, configured cost, failures, and issues.

N/A slots are never converted into automatic successes or failures in an applicable-value denominator.
Task fields absent from an open-world gold field list are reported as outside gold scope, not silently converted into N/A false positives.

## Run the deterministic smoke baseline

From the Git repository root:

```powershell
python -m high_fidelity_schema_study.architecture_evaluation `
  --manifest high_fidelity_schema_study/data/experiments/minimal_architecture_redesign/development_manifest.json `
  --variants A `
  --output-dir architecture-results/a-only
```

## Run all four variants against an OpenAI-compatible endpoint

```powershell
python -m high_fidelity_schema_study.architecture_evaluation `
  --manifest high_fidelity_schema_study/data/experiments/minimal_architecture_redesign/development_manifest.json `
  --variants A,B,C,D `
  --api-base http://127.0.0.1:1234/v1 `
  --model your-model-id `
  --input-price-per-million 0 `
  --output-price-per-million 0 `
  --output-dir architecture-results/full
```

The endpoint must support `chat/completions` and strict JSON Schema response format for B/C. B/C fail closed instead of salvaging prose or brace fragments. D alone preserves the historical free-JSON request and JSON-schema fallback behavior.

## Manifest contract

```json
{
  "schema_version": "minimal-architecture-manifest/v1",
  "benchmark_role": "blind_external",
  "cases": [
    {
      "case_id": "frozen-case-id",
      "task_file": "path/to/grounding.task.json",
      "gold_file": "path/to/independently-adjudicated.gold.json",
      "legacy_result_file": "optional/path/to/historical.result.json"
    }
  ]
}
```

Paths may be absolute, relative to the manifest, or relative to the package root. `legacy_result_file` is used only with `--replay-legacy`.

Historical replay cannot reconstruct calls, tokens, latency, or cost when the original artifact did not record them. Missing legacy results become observable failed D cases; they are not silently dropped.

## Output

The output directory contains:

- `report.json`: complete per-claim runs, per-slot evaluation, aggregate metrics, telemetry, and architecture deltas;
- `report.md`: compact comparison table and interpretation constraints.

Use `--no-runs` to omit full claims and evidence from the JSON report.

## Experimental validity requirements

The checked-in development manifest is synthetic and suitable only for mechanism tests and regressions. A research comparison requires a separately frozen `blind_external` manifest with independently adjudicated gold.

Before comparing the variants:

1. freeze case selection and gold;
2. use one model/version/configuration across B, C, and D;
3. record nonzero pricing when cost is part of the claim;
4. run multiple seeded repetitions when the endpoint is nondeterministic;
5. report all failures and denominators;
6. do not call C's `evidence_grounded` state truth verification.
7. require every semantic-reasoning target to be covered by gold, or keep the affected architecture comparison non-comparable;
8. report C's zero newly generated calls separately from its reused upstream response and effective architecture cost.
