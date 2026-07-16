# Semantic architecture power-analysis protocol v1

Status: executable design complete; calibration inputs pending
Scope: A/B/C/D semantic architecture study only

## Estimand and statistical unit

The statistical unit is the dataset. The powered outcome is the equal-weight
per-dataset difference in correct accepted applicable-claim rate. It is not the
pooled field-level accuracy difference. The two co-primary paired contrasts are:

1. `A_vs_B`, estimating the contribution of one dataset-level semantic response;
2. `B_vs_C`, estimating the contribution of deterministic verification while the
   semantic response is held byte-identical.

`C_vs_D` remains a predeclared secondary comparison because D may be
non-comparable under some backends and because powering three primary hypotheses
would dilute the two direct causal questions.

## Multiplicity and power calculation

Final inference applies Holm's family-wise-error procedure to the two co-primary
two-sided tests. For conservative planning, each contrast is powered at
`familywise_alpha / 2`, the most stringent Holm threshold. This guarantees that
the sample-size calculation does not depend on which primary contrast later has
the smaller p-value. Holm's original procedure is described in
[Holm (1979), DOI 10.2307/4615733](https://doi.org/10.2307/4615733).

For each contrast, `semantic_power_analysis.py` calculates paired-test power from
the noncentral Student t distribution. For sample size `n`, minimum meaningful
rate difference `delta`, and calibration estimate of the paired-difference
standard deviation `s`, the noncentrality parameter is
`sqrt(n) * delta / s`. The implementation uses SciPy's documented noncentral-t
CDF and survival functions ([SciPy `scipy.stats.nct`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.nct.html)).

The required semantic-opportunity count is the larger requirement across the two
co-primary contrasts. This is then inflated to a total corpus size using:

- the non-blind calibration semantic-opportunity rate;
- the non-blind calibration non-comparability rate;
- a frozen probability that the sampled corpus contains at least the required
  number of comparable semantic-opportunity datasets.

The inflation uses the binomial tail probability, not merely
`required / expected_rate`. Thus, the stated corpus size has the declared
assurance of reaching the required analyzable count under the planning rates.

## Inputs that must be frozen before blind sampling

- calibration manifest and calibration-statistics files and hashes;
- minimum meaningful rate difference;
- family-wise alpha and target power;
- selective-risk safety bound;
- paired-difference SD for both primary contrasts;
- SD inflation greater than one, chosen to address small calibration samples;
- semantic-opportunity and non-comparability rates;
- opportunity-count assurance;
- at least three SD sensitivity scenarios, including the uninflated and planning
  scenarios;
- a written SD-estimation method and planning rationale.

These values may use only non-blind calibration. They cannot be selected or
revised after observing blind labels or architecture outcomes.

The two source paths in the config are resolved relative to the generated output
artifact. The builder refuses a missing file or byte-level hash mismatch, and
blind preflight checks both files again. A bare, unverifiable 64-character string
is therefore insufficient provenance.

## Executable artifact and tamper boundary

First derive the planning statistics from the non-blind calibration evaluator
report. This step rejects blind roles, manifest/report case-order mismatch,
incomplete B/C replay, missing opportunity cases, and fewer than two comparable
datasets per primary contrast:

```bash
python -m high_fidelity_schema_study.semantic_power_calibration \
  --evaluation-report path/to/calibration-evaluation-report.json \
  --calibration-manifest path/to/calibration-manifest.json \
  --output path/to/calibration-statistics.json
```

The generated statistics contain the exact sample SD for both primary contrasts,
semantic-opportunity rate, and the larger co-primary non-comparability rate. The
power builder refuses config values that differ from these deterministic
statistics. Create the remaining judgment-bearing inputs from
`templates/semantic_power_analysis_config_template.json`, then run:

```bash
python -m high_fidelity_schema_study.semantic_power_analysis build \
  --config path/to/power-config.json \
  --output path/to/frozen-power-analysis.json

python -m high_fidelity_schema_study.semantic_power_analysis validate \
  --artifact path/to/frozen-power-analysis.json
```

The output records all planning inputs, per-contrast calculations, sensitivity
scenarios, Python/SciPy versions, and the generator implementation hash. Blind
preflight independently recomputes both the calibration-statistics artifact and
the complete power artifact. A changed source report, result, runtime,
implementation, primary contrast, or multiplicity policy is blocking.

## Interpretation limits

This is a planning model, not evidence that calibration variance transports
perfectly to the blind corpus. Dataset-level rate differences are bounded and may
be non-normal, especially with few scorable slots. Therefore the paper must:

- report the frozen SD-inflation and sensitivity scenarios;
- retain every dataset-level paired effect;
- accompany the Holm-adjusted paired-t result with a predeclared paired
  randomization/sign-flip sensitivity analysis and dataset bootstrap interval;
- describe material disagreement between inferential methods rather than choosing
  the favorable method;
- treat a failure to reach the frozen comparable-opportunity count as an
  underpowered result, not as permission to add post-hoc datasets selectively.

The selective-risk bound is a safety/interpretability constraint and is reported
with its own dataset-level uncertainty. It is not silently converted into a second
power target in the current calculation.
