# Target Schema

The study should emit a layered schema rather than a single flattened artifact.

## Layer 1: Physical Schema

These fields must be deterministic and file-grounded.

| Field | Meaning |
| --- | --- |
| `dataset_id` | Stable dataset identifier within the study corpus |
| `file_id` | Source file name or canonical file identifier |
| `file_format` | CSV, HDF5, Parquet, NetCDF, etc. |
| `field_name` | Human-facing field name |
| `field_path` | Canonical structural location such as HDF5 path or CSV column |
| `physical_type` | Observed type or parser-grounded type |
| `shape` | Array or dataset shape when present |
| `nullable` | Whether empty or missing values are observed or allowed |
| `missing_count` | Count of missing observations in the sample or full scan |
| `value_range` | Numeric range when deterministic profiling supports it |
| `unique_ratio` | Distinct-value ratio for candidate identifiers |
| `source_evidence` | Evidence records that justify the claim |
| `extraction_method` | Deterministic extractor that produced the claim |

## Layer 2: Logical Schema

These fields describe data organization and may combine deterministic computation with bounded semantic normalization.

| Field | Meaning |
| --- | --- |
| `logical_type` | Identifier, time axis, measurement, coordinate, label, relationship |
| `data_modality` | Tabular, hierarchical, time_series, multimodal, unknown |
| `identifier_fields` | Candidate entity identifiers |
| `time_axis` | Time field, frequency, regularity, timezone, missing intervals |
| `spatial_axis` | Latitude, longitude, depth, x/y/z coordinate fields |
| `relationships` | Parent-child or joinable references when defensible |

## Layer 3: Semantic Schema

These fields are useful but must remain evidence-constrained.

| Field | Meaning |
| --- | --- |
| `semantic_type` | Domain meaning such as air_temperature or station_identifier |
| `unit` | Explicit or inferred unit |
| `description` | Human-readable explanation |
| `confidence` | Confidence attached to the final claim |
| `uncertainty_reason` | Why the claim remains uncertain or why it was marked unknown |

## Evidence Tiers

Use the following precedence order:

1. `explicit_metadata`
2. `structural`
3. `statistical`
4. `llm_inference`

Rules:

- higher-tier evidence wins over lower-tier evidence
- lower-tier evidence may annotate but may not overwrite higher-tier claims
- conflicts must be surfaced, not silently resolved
- `unknown` is preferred over unsupported semantic invention
