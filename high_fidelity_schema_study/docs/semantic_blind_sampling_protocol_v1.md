# Semantic Blind Corpus Sampling Protocol v1

Status: executable protocol; candidate acquisition pending

## 1. Purpose and claim boundary

The blind corpus must not be hand-selected after inspecting model outputs,
architecture comparisons, or gold labels. This protocol turns corpus construction
into a content-hashed chain:

1. a content-hashed enumeration and acquisition log;
2. a frozen candidate frame containing every successfully acquired resource;
3. a sampling design registered before selection;
4. a deterministic selection artifact;
5. the final blind manifest in exactly the selected order.

This does not make a convenience frame representative of all scientific data.
External-validity claims remain limited to the frame described by its repositories,
retrieval cutoff, enumeration procedure, file-format scope, and eligibility rules.
Random selection controls discretionary choice within that frame; it cannot repair
an incomplete or biased frame.

## 2. Candidate-frame construction

Before the candidate frame, `semantic-blind-acquisition-log/v1` records the exact
catalog requests and raw response artifacts, contiguous page ordinals, the frozen
page-cap or API-exhaustion boundary for every repository, and every enumerated
file resource. Inclusion/exclusion criteria are defined once and evaluated as
Booleans for every enumerated resource. Eligibility and failure-reason IDs are
mechanically derived. Every eligible resource is either acquired or retained as
an explicit download failure; every ineligible resource is retained as
`excluded_before_download`.

Raw API pages alone are insufficient because one dataset record may expose
multiple files. `semantic_catalog_acquisition.py` replays the frozen
`zenodo_dryad_catalog_snapshot/v1` adapter over every snapshot. For Dryad, the
snapshot also retains the version/files responses for every returned dataset.
Each snapshot records both the number of returned dataset records and the number
of normalized file resources. The validator requires the complete normalized
identity set and all provider-derived metadata to equal the acquisition records.
It also rehashes downloaded bytes and checks the provider MD5/SHA-256 value.
Page gaps, missing expansions, missing repository termination boundaries,
unbound adapter code, omitted files, metadata drift, and checksum mismatch are
blocking.

`semantic-blind-candidate-frame/v1` is frozen before selection. Its
`frame_definition` records:

- the population/scope statement;
- the candidate unit;
- the reproducible enumeration method and retrieval cutoff;
- every source repository;
- objective inclusion and exclusion criteria.

Every criterion has a stable ID, description, and assessment method. Every
candidate records one Boolean result for every criterion. Eligibility and the
failure-reason IDs are mechanically derived: all inclusion criteria must pass and
no exclusion criterion may trigger. A curator cannot mark a candidate eligible
while its frozen criterion results imply exclusion.

Each candidate records a stable candidate and parent-dataset group ID, repository
record and URL, acquisition time, scientific family, format, license, frozen local
resource, neutral task, approved source bundle, deterministic semantic-opportunity
count, selection stratum, and eligibility decision.

The frame validator:

- requires the candidate set to equal all and only successfully acquired records;
- rejects any candidate metadata or resource hash that differs from the frozen
  acquisition log;
- rehashes every local artifact;
- recomputes semantic-opportunity targets from the neutral task;
- rejects duplicate resource hashes and candidate IDs;
- rejects eligible resources whose byte hashes or stable file-level source
  identities occur in the frozen union of development, annotator-calibration,
  backend-qualification, or other system-visible resources;
- rejects outcome-only keys such as gold, `correct_*`, legacy result, or model
  response fields in tasks and source bundles;
- requires eligibility decisions before selection and before any gold exists.

Eligibility may use deterministic extraction success, supported local format,
license/access constraints, resource integrity, and availability of source
documentation. It may not use A/B/C/D output quality.

## 3. Sampling design and registration

`semantic-blind-sampling-design/v1` binds the candidate-frame hash and final power
artifact. Its required total and semantic-opportunity counts must equal the power
artifact. The design also freezes:

- an exact positive quota for every selection stratum;
- a minimum number of scientific families;
- at most one resource per parent dataset/study group;
- a maximum contribution from one source repository;
- the selection algorithm and seed provenance.

Strata and quotas may be chosen after inspecting frame metadata but before model
outputs or gold. They must be justified as design choices, not tuned to make an
architecture win. Their sum equals the powered total dataset count.

Before selection, run `preflight-design`, then register the exact design SHA-256 in
an external or append-only system using
`semantic-sampling-registration-receipt/v1`. The receipt states both
`frozen_before_selection=true` and
`selection_not_executed_at_registration=true`. A preflight report is not a receipt.

The stable source identity is not a curator alias. The validator recomputes it
using `canonical_source_tuple_sha256/v1`: canonical JSON containing the
case-folded repository name, repository-stable record ID, and repository-stable
file/resource ID, hashed with SHA-256. It must therefore resolve the same source
file to the same value across historical and blind frames. This is necessary
because the workspace does not retain the original bytes for every historically
inspected external resource.
The checked-in registry at
`data/experiments/semantic_blind_sampling_v1/known_nonblind_resources.json` is
derived from all 25 entries in `data/semantic_grounding/manifest.json`: nine
internal resources are protected by both SHA-256 and identity; 16 external
resources are protected by identity because their original bytes are absent.
Their task hashes are provenance only and are not presented as substitutes for
resource hashes. The registry also binds its generator implementation hash;
changing exclusion semantics therefore invalidates the frozen registry.

## 4. Deterministic selection

The frozen algorithm is
`stratum_ordered_sha256_priority_with_frozen_caps/v1`:

1. process stratum names in lexical order;
2. within a stratum rank each eligible candidate by SHA-256 of the registered seed,
   candidate ID, and resource SHA-256;
3. accept candidates in that order while enforcing parent-group and repository
   caps;
4. stop when the frozen quota is filled.

If any quota, powered semantic-opportunity count, or scientific-family minimum
cannot be met, selection fails. The team may create a newly registered design, but
must retain the failed design and receipt. It may not manually replace a selected
case or try unregistered seeds until a preferred corpus appears.

The selection artifact persists every selected priority hash and is rebuilt exactly
by validation. The blind manifest must contain the same case IDs, order, task
hashes, and source-bundle hashes. Gold annotation starts only after this binding.

## 5. Commands

```powershell
python -m high_fidelity_schema_study.semantic_blind_sampling build-known-registry `
  --grounding-manifest path/to/semantic-grounding-manifest.json `
  --data-root path/to/data `
  --frozen-at YYYY-MM-DDTHH:MM:SSZ `
  --output path/to/known-nonblind-resources.json

python -m high_fidelity_schema_study.semantic_blind_sampling validate-known-registry `
  --artifact path/to/known-nonblind-resources.json

python -m high_fidelity_schema_study.semantic_blind_sampling validate-acquisition `
  --artifact path/to/blind-acquisition-log.json

python -m high_fidelity_schema_study.semantic_blind_sampling preflight-design `
  --design path/to/blind-sampling-design.json

python -m high_fidelity_schema_study.semantic_blind_sampling select `
  --design path/to/blind-sampling-design.json `
  --receipt path/to/external-sampling-registration-receipt.json `
  --output path/to/blind-selection.json

python -m high_fidelity_schema_study.semantic_blind_sampling validate `
  --artifact path/to/blind-selection.json
```

Templates:

- `templates/semantic_known_nonblind_resources_template.json`;
- `templates/semantic_blind_acquisition_log_template.json`;
- `templates/semantic_catalog_snapshot_zenodo_template.json`;
- `templates/semantic_catalog_snapshot_dryad_template.json`;
- `templates/semantic_blind_candidate_frame_template.json`;
- `templates/semantic_blind_sampling_design_template.json`;
- `templates/semantic_sampling_registration_receipt_template.json`.

## 6. Failure and interpretation rules

- Acquisition failure before frame freeze is recorded by the frame enumeration
  log; it is not silently omitted.
- A selected resource that becomes unavailable remains a documented selection
  failure. Replacement requires a preregistered deterministic reserve rule or a
  newly registered selection design; this version defines no ad hoc reserve.
- Insufficient semantic opportunities produce an underpowered/failed selection,
  not post-outcome sample extension.
- The selection artifact is corpus-design evidence, not architecture-performance
  evidence.
- Results support no claim beyond the frozen frame and sampled resources without
  additional sampling evidence.
