# Semantic architecture calibration pack v1

This directory is a reproducible, non-blind calibration artifact. It is used to
rehearse the two-independent-annotator workflow and to detect semantic backend
contract failures before the external benchmark is frozen.

It is **not** part of the blind benchmark and must not be used to estimate A/B/C/D
effects, external validity, or publication-level performance. The nine source
cases are synthetic development cases previously visible to the system team.

The distributed annotation packets contain physical and structural observations,
examples, ranges, and approved grounding snippets. They exclude deterministic
`logical_type`, `semantic_type`, and `unit` predictions, confidence fields,
descriptions, derived column-name unit hints, source task paths, gold paths, and
legacy-result paths. Content hashes in `manifest.json` preserve provenance without
providing a navigation path back to prediction-bearing task files.

Rebuild from the repository root with:

```text
python -m high_fidelity_schema_study.build_semantic_calibration_pack \
  --manifest high_fidelity_schema_study/data/experiments/minimal_architecture_redesign/development_manifest.json \
  --output-dir high_fidelity_schema_study/data/experiments/semantic_architecture_calibration_v1
```

After either annotator submits an independent artifact, retain that artifact by
content hash before revealing the other annotation or any calibration consensus.

`annotation_workflow_manifest.json` binds all nine packets, their approved source
bundles, the calibration-only canonical vocabulary, the handbook, and the validator
implementation by SHA-256. Two annotators receive separate copies of the packet,
source bundle, vocabulary, handbook, and independent-annotation template. They must
not share output directories or view the other submission before both validators
return `ready` and both hashes are frozen.

The round-1 preregistered design is
`annotator_calibration_design_round1.json`, SHA-256
`1bab4078a30dc7846ab31de20f0cdfe9cfce225abe2beef337a62f91e0a80fae`.
It binds workflow-manifest SHA-256
`d2476583dc28d6bc4d653f286745a7841282bb917963da3bc9ac7a3f6b45c318`
and the fixed agreement floors. Before either annotator starts, register the exact
design hash in an auditable external or append-only registry and retain a receipt
matching `templates/semantic_preregistration_receipt_template.json`. Do not edit
the design after registration; any change requires a new design, hash, and receipt.

Immediately before external registration, revalidate the frozen design and its
workflow hash chain:

```text
python -m high_fidelity_schema_study.semantic_annotator_calibration preflight-design \
  --design high_fidelity_schema_study/data/experiments/semantic_architecture_calibration_v1/annotator_calibration_design_round1.json
```

This output is explicitly not a receipt. The external registration record must
still exist before the first submission is created.

After both annotators complete all nine cases, create the completed round manifest
from `templates/semantic_annotator_calibration_round_template.json`, then build and
validate the gate:

```text
python -m high_fidelity_schema_study.semantic_annotator_calibration build \
  --round-manifest path/to/completed-calibration-round.json \
  --output path/to/calibration-summary.json
python -m high_fidelity_schema_study.semantic_annotator_calibration validate \
  --artifact path/to/calibration-summary.json
```

Validate and compare with the commands in
`docs/semantic_gold_workflow_protocol_v1.md`. The vocabulary deliberately normalizes
unit aliases before comparison; it must not be reused as the future blind vocabulary.
