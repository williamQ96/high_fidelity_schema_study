# NDP-50 validation deviation 001

Date: 2026-07-26

Status: resolved procedurally; validation v1 excluded from confirmatory reporting

## Event

The structural preflight passed before validation details were opened. The first
validation execution then revealed that `ndp50_execution.py` serialized
`run_role` as `development` unconditionally and that `ndp50_report.py` enforced
development IDs only. The extraction counts were produced, but the run could not
prove role identity through the intended report path.

This is an evaluation-infrastructure defect, not a dataset parser failure.
Nevertheless, the affected run is not used as the formal validation result.

## Preserved evidence

- invalidated freeze:
  `validation_freeze_v1_invalidated.json`,
  SHA-256 `1395948c6b382cf117587bd1ba60d5c06c9261b9e87b4bccf0328c81fe79c8a8`;
- preflight report:
  `preflight_before_validation.json`,
  SHA-256 `f6c3d4c4dde6b23088272f15f0fc7e3e6c76a6fb6e88f13d516176baf9566e95`;
- excluded execution:
  `validation_run_v1.json`,
  SHA-256 `da932e924b1852c3ab8e14c03d18db02f0c067f649dd1efd10b534925e40403b`.

The validation details remain opened. They are not described as sealed again.
The 25-case test split remains unopened.

## General correction

The correction is independent of any dataset identity or outcome:

1. execution requires an explicit `run_role`;
2. validation/test require a content-hashed authorization freeze;
3. the execution verifies every implementation hash in that freeze;
4. reports require exact identity equality with the selected role;
5. failure ledgers are written inside role-specific report directories;
6. test authorization remains false until the semantic and validation gates are
   complete.

No extractor rule, threshold, resource order, byte limit, retry count, or
selection was changed after observing validation v1. Development and negative
controls are rerun under the corrected generic executor, a new freeze is created,
and validation is then replayed under that freeze. Both validation attempts are
retained so external-resource instability can be assessed rather than hidden.
