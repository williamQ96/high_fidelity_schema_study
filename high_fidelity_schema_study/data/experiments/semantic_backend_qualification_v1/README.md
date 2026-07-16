# Backend qualification calibration v1

This is a non-blind operational calibration set for the frozen A/B/C/D semantic
architecture study. All eight tasks were already present in the developed external
corpus, so none may later enter the blind external evaluation.

Selection was made before running any candidate GLM5.2, Qwen3.6, or Llama 3.3
backend. The fixed rule spans CSV and HDF5, tabular, time-series, and hierarchical
data, one to 22 dataset-level targets, and both generic and historically manual
legacy grouping. It yields eight semantic-opportunity datasets and 74 targets.

The qualification runner does not open a gold file and does not compute correctness
or architecture effects. It measures response-contract validity, target scope,
B/C replay identity, exact repeatability at deterministic decoding, timeout,
truncation, context fit, physical calls, tokens, latency, and legacy compatibility.

The cases are not a sample for power analysis and their output cannot be used to
select the backend that makes a preferred architecture win.

## Candidate-run inventory

The 2026-07-15 Qwen3.6-27B Q4_K_M execution is retained as an invalidated
diagnostic run. Its JSON must only be interpreted together with the adjacent
`.invalidation.json` sidecar and
`docs/qwen36_27b_backend_diagnostic_2026-07-15.md`. It exposed replay-provenance,
target-scope-evaluability, per-call context-accounting, and partial-D provenance
defects before a valid candidate qualification was produced.

After LM Studio thinking was disabled and the same model was reloaded with a
16,384-token context, the adjacent `candidate_qualification_rerun` report passed
every frozen operational threshold. Its `.assessment.json` binds the report hash,
the excluded one-call prequalification gate, the threshold decisions, and the
remaining checkpoint/runtime identity blockers. The successful qualification does
not supersede the first run as defect evidence; it supersedes it only for current
Qwen3.6 operational eligibility.
