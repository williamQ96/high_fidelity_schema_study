# Evaluation Plan

The study should report field-level evidence, not only aggregate performance.

## Primary Dimensions

### 1. Completeness

How many reference schema elements were extracted?

```text
completeness = extracted_reference_matched_elements / reference_elements
```

Report separately for:

- physical completeness
- logical completeness
- semantic completeness

### 2. Accuracy

How many extracted claims are correct?

Suggested split:

- physical accuracy: names, paths, dtypes, shapes
- logical accuracy: identifiers, time axis, measurements
- semantic accuracy: units, descriptions, domain type

### 3. Necessary-Field Coverage

Focus on fields needed for retrieval, discovery, and safe reuse.

Suggested necessary fields:

- variables / measurements
- units
- time coverage
- spatial coverage
- identifier fields
- provenance
- license or access constraints when present

Important rule:

- `unknown` should count better than a hallucinated wrong claim when evidence is insufficient

### 4. Uncertainty

Measure whether confidence aligns with actual correctness.

Suggested analyses:

- confidence calibration buckets
- ambiguity detection rate
- conflict surfacing rate
- unknown-when-unsupported rate

## Retrieval Evaluation

Compare at least three indexing strategies:

1. metadata only
2. file name plus README only
3. schema-enhanced retrieval with evidence-grounded annotations

Suggested metrics:

- Recall@k
- Precision@k
- MRR
- nDCG

Each retrieval example should also include explanation traces showing which extracted schema elements led to the match.

## Error Analysis

For each failed case, record:

- missed field
- incorrect field claim
- unsupported semantic leap
- parser limitation
- source metadata conflict
- retrieval false positive cause

## Phase 12 Experimental Tracks

Phase 12 adds an isolated deterministic-substrate experiment. It does not replace the frozen Artifact Paper metrics.

Report separately:

- format detection accuracy;
- extractor routing accuracy;
- structured failure artifact completeness;
- time-axis selection accuracy;
- per-property temporal accuracy;
- exact temporal profile accuracy;
- abstention precision and recall;
- reason-code coverage;
- evidence coverage;
- unsupported promotion count.

Temporal evaluation must compare `field`, `type`, `timezone`, `frequency`, `regularity`, and `missing_intervals` independently before reporting an exact-profile score. Naive timestamps must not inherit timezone claims from sidecar text in the deterministic track.

## Phase 13 NetCDF/CF Track

Phase 13 is the first standards-backed registry extension. It remains isolated from the frozen Artifact Paper metrics.

Report separately:

- format detection accuracy;
- extractor routing accuracy;
- physical extraction accuracy for dimensions, variables, dtype, shape, attributes, groups, and missing markers;
- CF coordinate-role accuracy;
- CF time-axis accuracy;
- calendar-handling accuracy;
- unit-mapping accuracy;
- temporal abstention precision and recall;
- evidence coverage;
- unsupported promotion count.

Non-standard calendars may be preserved as explicit metadata without being decoded into standard-calendar timestamps. Missing or malformed CF metadata must remain unknown or conflicted rather than being promoted from names alone.

## Phase 14A Zarr Directory-Store Track

Phase 14A evaluates local directory-store Zarr v2 metadata extraction independently from the frozen Artifact Paper metrics.

Report separately:

- store detection and extractor routing accuracy;
- outcome-status accuracy;
- group and array discovery accuracy;
- physical metadata and attribute extraction accuracy;
- `_ARRAY_DIMENSIONS`, coordinate-role, calendar, and unit handling accuracy;
- reason-code coverage and partial-extraction accuracy;
- temporal abstention precision and recall;
- value-observation abstention accuracy;
- evidence coverage and path portability;
- unsupported promotion count.

The evaluator must verify that accepted evidence references are metadata-relative, that no chunk payloads are read, and that malformed, missing, conflicted, or unsupported metadata is represented explicitly rather than guessed.

## Phase 14B Zarr Compatibility Track

Phase 14B uses a separate producer-shaped local Zarr v2 corpus. It is broader and more realistic than the controlled Phase 14A challenge pack, but it is not a downloaded representative ecosystem sample.

Report separately:

- supported-layout compatibility rate;
- unsupported-feature visibility;
- malformed-store failure quality;
- structured-abstention quality;
- evidence coverage and path portability;
- chunk-payload non-claim rate;
- value-observation abstention accuracy;
- compatibility-gap count and reason-code distribution;
- unsupported promotion count;
- true bug count.

An unsupported or malformed case counts as compatible only when the extractor surfaces the expected structured result. Aggregate accuracy must not treat an expected abstention as a failure or hide a true bug inside unsupported-feature counts.

## Phase 14C External And Library Conformance Track

Phase 14C uses a metadata-only corpus combining exact metadata from a public upstream source distribution, stores produced by pinned Zarr/Xarray APIs, and labeled library-derived edge cases. It remains a targeted validation set rather than a representative ecosystem sample.

Report separately:

- source-category counts and source-documentation completeness;
- supported compatibility, structured abstention, unsupported-feature visibility, and malformed-edge quality;
- evidence coverage, path portability, and chunk-payload non-claim rate;
- unsupported promotion count and canonical true bug count;
- optional Zarr raw-physical-metadata conformance;
- optional Xarray structural conformance;
- explained parser interpretation/default differences;
- unexplained conformance difference count.

Optional cross-parser results are development-time supporting evidence only. They must never override canonical raw metadata preservation or turn parser defaults and interpretations into deterministic truth. The corpus and generated artifacts must contain no chunk payloads or local absolute paths.

## Phase 15A Parquet / Arrow Track

Phase 15A evaluates registry-backed Parquet footer and Arrow schema extraction independently from frozen Artifact Paper metrics.

Report separately:

- format detection and extractor routing accuracy;
- recursive Arrow field and Parquet physical column accuracy;
- logical-to-physical nested path mapping;
- nullability and timestamp-timezone declaration accuracy;
- row-group, compression, and encoding accuracy;
- key-value and field metadata accuracy;
- footer-statistics presence/absence policy accuracy;
- evidence coverage and row-value abstention accuracy;
- unsupported promotion count.

Footer statistics are metadata claims and must not be presented as independently validated value observations. The evaluator must verify `row_values_read=0`, retain Arrow logical paths separately from Parquet physical paths, and keep bounded PyArrow-produced results distinct from future external compatibility evidence.

## Phase 16A JSON Structure Track

Report separately:

- format detection, extractor routing, and extraction-mode accuracy;
- observed path, missingness, nullability, and heterogeneous-array accuracy;
- JSON Schema declared-property accuracy;
- declared-versus-observed conflict accuracy;
- sampling-issue accuracy and evidence coverage;
- unsupported promotion count.

Observed JSON structure is bounded by `sample_limit`. JSON Schema declarations and observed examples must remain separate claim classes, and conflicts must be explicit rather than silently resolved.

## Phase 16B XML / XSD Structure Track

Report separately:

- format detection, extractor routing, and extraction-mode accuracy;
- namespace-aware element and attribute path accuracy;
- repeated-path accuracy;
- lightweight XSD declaration accuracy;
- `xsi:type` declared-versus-observed conflict accuracy;
- sampling-issue accuracy and evidence coverage;
- unsupported promotion count.

Observed XML structure is sample-bounded. XSD and `xsi:type` declarations must remain separate from observations. External schemas and entities must not be loaded.

## Phase 17 Unified Schema Envelope Track

Report separately:

- required-section completeness;
- identity, format-decision, and extractor-capability projection accuracy;
- physical-structure fidelity;
- normalized claim-state validity and claim-evidence integrity;
- conflict, abstention, and unsupported-feature projection;
- provenance completeness;
- legacy outcome immutability.

The envelope is additive and must not become a new inference layer. Legacy output remains unchanged by default, and the projection must not mutate its source outcome.
