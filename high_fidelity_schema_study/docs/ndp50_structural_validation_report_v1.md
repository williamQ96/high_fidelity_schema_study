# NDP-50 structural validation report v1

Date: 2026-07-26

Status: structural validation complete; semantic validation and test not
authorized

## Scope

This report evaluates bounded resource acquisition and deterministic structural
schema extraction on the NDP-50 validation split. It does not evaluate semantic
label accuracy, does not alter the frozen Artifact Paper, and is not a
prevalence-weighted estimate of the
[NDP Central Catalog](https://nationaldataplatform.org/catalog/).

The candidate frame contains 5,823 dataset identities across 75 organizations.
Selection is deterministic and stratified: 15 development, 10 validation, and 25
test datasets. The test split remains unopened.

## Integrity and deviation handling

The first validation execution produced correct resource outcomes but serialized
the role as development because the executor/report code had a hard-coded role.
That run is excluded from formal reporting and preserved under
`validation_run_v1.json`. The defect and artifact hashes are recorded in
`docs/ndp50_validation_deviation_001.md`.

The correction was role-generic and did not change any extractor, threshold,
resource order, byte limit, retry limit, or selected identity. A new freeze binds
all implementation and input hashes, records that validation had already been
opened under the deviation, and confirms that test remains unopened. Validation
v2 was authorized by that freeze. Later semantic-packet preparation found a blank
CSV header in a development resource. A general, regression-tested header
canonicalization fix was applied, development was rebuilt, and validation v3 was
authorized by a new implementation freeze. Validation v1, v2, and v3 have
identical aggregate byte and status counts; the current report artifacts use
development v4 and validation v3.

## Frozen policy

- Maximum three extractor-eligible resources per dataset, ordered by resource ID.
- Maximum 25 MiB per resource and 50 MiB transferred per dataset.
- Maximum three attempts with a fixed 10-second interval.
- Only explicit asynchronous provider control responses are retryable.
- HTTP 200 control/error documents are rejected before extraction.
- Remote Zarr requires a uniquely resolved store with discoverable metadata
  markers; bucket roots and portal indexes fail closed.
- Declared catalog format is compared with, but never supplied as an extractor
  hint to, direct observation.

## Primary structural results

| Measure | Development | Validation |
|---|---:|---:|
| Dataset count | 15 | 10 |
| Catalog resource count | 37 | 5,054 |
| Policy-attempted resources | 13 | 10 |
| Acquired data payloads | 10 | 7 |
| Successful extractions | 10 | 6 |
| Datasets with at least one schema | 7 (46.7%) | 5 (50.0%) |
| Resource end-to-end coverage | 10/37 (27.0%) | 6/5,054 (0.12%) |
| Acquisition given attempt | 76.9% | 70.0% |
| Extraction success given acquisition | 100.0% | 85.7% |
| Macro mean per-dataset resource coverage | 35.6% | 44.0% |

The fixed-seed 10,000-replicate dataset bootstrap 95% percentile interval for
validation dataset end-to-end coverage is 20.0% to 80.0%. The wide interval is
expected at n=10 and precludes a precise population claim.

## Validation outcome taxonomy

- `schema_extracted`: 5 datasets;
- `attempted_but_not_acquired`: 2 datasets;
- `no_policy_attempt`: 3 datasets.

Of seven acquired payloads, six produced schemas. One 467-byte resource declared
as CSV had no suffix and no detectable delimiter. Because catalog metadata was
not used as a format hint, the product returned the planned
`unknown_no_signature` abstention.

At resource level:

- 5,043 resources had no extractor under the frozen policy;
- three eligible resources exceeded the 25 MiB limit;
- one remote Zarr resource lacked a uniquely resolvable store locator;
- one acquired resource abstained because no trustworthy direct format signal
  was present.

Declared-versus-observed format status was `agree` for six resources,
`observed_unknown` for one, and `not_observed` for 5,047.

## Stratified validation results

| Selection stratum | Datasets with schema | Resources with schema |
|---|---:|---:|
| Archive | 1/1 | 2/5 |
| Documentation/text | 0/1 | 0/3 |
| Geospatial/image | 0/2 | 0/5,035 |
| Other/unknown | 0/1 | 0/6 |
| Supported hierarchical | 0/1 | 0/1 |
| Supported semistructured | 2/2 | 2/2 |
| Supported tabular | 2/2 | 2/2 |

These cells are descriptive. Most contain only one or two datasets and are not
used for inferential format comparisons.

## Resource-count skew

Validation datasets contain between 1 and 4,933 resources (median 2). The largest
dataset contributes 97.6% of all validation resources. Consequently:

- the 0.12% resource micro rate is dominated by one geospatial dataset;
- the 50% dataset rate gives each catalog identity equal weight;
- the 44% macro mean gives each dataset equal weight after computing its own
  resource coverage;
- none of these estimands may be substituted for another.

Resource observations within a dataset are clustered; no independent-resource
confidence interval is reported.

## Interpretation

The result supports a narrow conclusion: when a payload is directly accessible
and structurally recognizable under the supported policy, deterministic
extraction is reliable in this small validation split. It rejects a broad
compatibility claim for the heterogeneous NDP catalog: coverage is chiefly
limited by unsupported geospatial/archive formats, extreme resource expansion,
byte limits, and incomplete remote-store locators.

This is a bounded compatibility pilot, not evidence of semantic correctness or
general NDP prevalence. The next research gate requires an independently frozen
semantic-opportunity manifest, two-annotator gold, prompt/backend registry, and
test analysis plan. Until those artifacts pass preflight, semantic validation
and all test execution remain unauthorized.
