# From File Input to Unified Schema Envelope Output: High-Fidelity Schema Extraction Pipeline

In scientific dataset management and retrieval, accurately and auditably identifying dataset file structures, inferring their physical/logical/semantic properties, and maintaining full evidence traceability are core challenges. This document details the end-to-end process of the **File In -> Schema Out** pipeline implemented in this project.

---

## Core Design Philosophy: Deterministic-First

Traditional metadata and schema extraction often rely on a "black-box LLM guessing" approach—directly feeding a filename and a few sample rows of data to a Large Language Model (LLM) and asking it to generate a schema. For scientific datasets, this approach suffers from three fatal issues:
1. **Hallucinations and Lack of Control**: The model may fabricate fields, shapes, or data types that do not exist.
2. **Lack of Audit Trail**: There is no way to trace which specific row, metadata attribute, or README sentence supported a given schema claim.
3. **Lack of Reproducibility**: The same input might produce different results across multiple runs.

To address these limitations, this project adopts a **Deterministic-First** philosophy:
* **Program-Led Structure Extraction**: The pipeline first uses highly stable, format-specific deterministic parsers to extract the physical layout and intrinsic metadata.
* **Evidence Collection and Confidence Scoring**: Throughout the parsing phase, the system captures the precise source of every decision (e.g., column headers, internal attribute names, line offsets).
* **Constrained LLM Semantic Enrichment**: An LLM is introduced *only* after deterministic parsing is complete. The LLM is restricted to interpreting external documentation (like READMEs) and adding high-level semantics. All LLM claims must be supported by evidence and pass strict schema compatibility checks.
* **Unified Graph Projection**: Finally, the system projects all structures, inferences, claims, and evidence into a unified graph format, generating a standardized "Schema Envelope".

Here is the complete processing pipeline:

```text
Raw File / Store Input (File In)
       │
       ▼
 1. Format Detection & Routing ────────► Match magic bytes, suffixes, or directory layouts
       │
       ▼
 2. Deterministic Extraction ──────────► Run format-specific extractor (CSV, JSON, Zarr, etc.)
       │                                 └─ Extract physical types, basic logical roles, and evidence
       ▼
 3. Profiling & Normalization ─────────► Identify time axes, normalize units to standard scales
       │
       ▼
 4. Constrained Semantic Merge ────────► Integrate LLM-inferred semantics with strict validation
       │
       ▼
 Unified Schema Envelope (Schema Out) ──► Project output to unified envelope with claims-evidence graph
```

---

## Phase 1: File Intake & Format Detection

When a file path is provided to the system, it enters the entry point [extract_path](../extractors/registry.py#L415) in `extractors/registry.py`. Before invoking any specific parser, the system performs **resource validation** and **format detection**:

### 1. Resource Kind Validation
The system determines whether the input is a single file (`file`) or a directory-based store (`directory_store`, such as Zarr) using `_actual_resource_kind(path)`. If the caller requests a mismatching resource kind, the pipeline halts immediately with a `resource_kind_mismatch` error.

### 2. Format Signal Collection (`detect_format`)
To prevent errors from relying solely on file extensions, the system collects four tiers of format signals:
* **Magic Bytes Signal (`_magic_signal`)**: If the input is a file, the first 16 bytes are read.
  * `\x89HDF\r\n\x1a\n` ──► Identifies an `hdf5` container.
  * `PAR1` ──► Identifies a `parquet` container.
  * `CDF\x01`, `CDF\x02`, `CDF\x05` ──► Identifies classic `netcdf` formats.
  * `PK\x03\x04` ──► Identifies a `zip_container`.
  * **HDF5 Override**: If the magic bytes indicate an HDF5 container, but the file has a `.nc` or `.cdf` extension and contains NetCDF4 attributes (checked via [hdf5_has_netcdf_markers](../extractors/netcdf_extractor.py)), the signal is updated to `netcdf`.
* **Directory Structure Signal (`_directory_signal`)**: If the input is a directory, the system looks for Zarr metadata files.
  * Presence of `zarr.json` ──► Identifies a Zarr v3 store.
  * Presence of `.zgroup`, `.zarray`, or `.zmetadata` ──► Identifies a Zarr v2 store.
* **Suffix Signal (`_suffix_signal`)**: Matches extensions to target formats (e.g., `.json`/`.jsonl` ──► `json`, `.csv`/`.tsv` ──► `csv`).
* **Text Probe Signal (`_looks_like_delimited_text`)**: For text files without clear magic bytes, the system reads the first 8192 bytes and uses Python's `csv.Sniffer` to detect delimiters (`,`, `\t`, `;`, `|`). If the first 5 lines yield a consistent column count ($\ge 2$), it records a `csv` signal.

### 3. Priority Resolution and Conflict Handling
Once all signals are collected, the system resolves the format according to the following priority:
$$\text{Magic Bytes} > \text{Explicit Hint} > \text{Filename Suffix} > \text{Text Probe}$$

* If a strong signal (like Magic Bytes) conflicts with the explicit user hint (e.g., magic is HDF5 but hint is JSON), the system marks the format as `conflicted` and **abstains** from parsing, falling back to a generic `raw_binary` schema.
* Otherwise, the selected format is matched against the capabilities in [EXTRACTOR_CAPABILITIES](../extractors/registry.py#L71) and routed to the corresponding runner.

---

## Phase 2: Deterministic Structural Extraction

Once routed, the deterministic extractor parses the file to harvest its physical structures and intrinsic metadata.

### 1. CSV Extractor (`csv_conservative_profiler`)
Implementation: [csv_extractor.py](../extractors/csv_extractor.py).
* **Data Ingestion**: Reads the headers and samples up to $N$ rows (default $N=200$).
* **Conservative Physical Type Inference**:
  * Strips whitespace from cell samples.
  * **Int Detection**: If all non-empty samples are digits (plus optional sign), it is inferred as `int`. **Pre-emptive Protection**: To prevent numeric codes (like zip codes or phone numbers) with leading zeros from losing their formatting, the system runs `_has_leading_zero`. Any pure-digit column containing a leading zero (e.g., `"0123"`) is forced to `string`.
  * **Datetime Detection**: Attempts to parse samples using standard formats. If 100% of non-empty values are successfully parsed, the column is inferred as `datetime`.
  * **Float Detection**: Checks if samples convert to floats and contain `.` or `e/E`.
  * **Conservative Fallback**: Any type conflict within a column triggers a fallback to `string`, recording `uncertainty_reason="conservative fallback to string to avoid over-claiming"`.
* **Heuristic Role Mapping**:
  * **Semantic Type**: Automatically maps column names to known concepts (e.g., `lat` -> `latitude`, `temp` -> `air_temperature`).
  * **Logical Type**: Assigns logical roles (such as `identifier`, `coordinate`, `measurement`, `label`, `attribute`) based on physical and semantic types.
  * **Unit Suffixes**: Extracts unit hints from header names (e.g., `_c` -> `Celsius`).
* **Evidence Generation**: Attaches structural evidence (`evidence_type="csv_header"`) and statistical evidence (`evidence_type="sample_rows"`).

### 2. JSON Extractor (`json_bounded_structure_extractor`)
Implementation: [json_extractor.py](../extractors/json_extractor.py).
* **Memory Protection**: Aborts extraction if the document size exceeds 16MB to avoid out-of-memory issues.
* **Dual-Track Mode**:
  1. **Declared Mode**: If the root document declares a standard JSON Schema (`$schema`/`$id` and `properties`), the extractor recursively traverses the schema declarations to register fields as `declared` claims. If sample values are present, it validates them against the schema.
  2. **Observed Mode**: If no schema is declared, the extractor activates a recursive structure crawler.
* **Recursive Path Traversal**:
  * Traverses nested elements via `visit(value, path, record_index)`.
  * Flattens objects into dotted path notation (e.g., `$.store.book[].title`).
  * Computes path-level type sets, nullability, missing ratios, and array configurations (lengths and element types).
* **Security Constraints**: Because JSON is highly dynamic, no semantic or logical roles are inferred from field names during this phase; they are initialized to `unknown`.

### 3. Zarr Extractor (`zarr_v2_metadata_extractor`)
Implementation: [zarr_extractor.py](../extractors/zarr_extractor.py).
* **Hierarchical Exploration**:
  * Designed for directory stores. It scans the directory and prioritizes reading the consolidated `.zmetadata` file. If missing, it crawls the directory for separate `.zgroup`, `.zarray`, and `.zattrs` files.
* **Version Enforcement**:
  * Validates the `zarr_format` field.
  * If `zarr_format == 3` (Zarr v3), it throws a `StructuredExtractionError` with an `abstained` status, as the extractor currently only supports Zarr v2.
* **Coordinate & Dimension Analysis**:
  * Parses `.zarray` configurations to determine `shape`, `chunks`, and `dtype` as physical fields.
  * Resolves dimensions based on Xarray conventions (reading `_ARRAY_DIMENSIONS`).
  * Resolves coordinate systems by checking CF (Climate and Forecast) conventions (inspecting `axis`, `units`, `standard_name`).
  * Determines whether arrays serve as `dimension_coordinate`, `auxiliary_coordinate`, or physical measurements.
* **Metadata-Only Constraints**:
  * The extractor only reads JSON configuration headers; it **does not load chunk data payloads** to maintain high I/O performance. Consequently, missing counts, unique ratios, and value ranges are marked as `unknown` or `abstained`.

---

## Phase 3: Data Profiling & Normalization

After extracting physical fields and generating the baseline evidence trail, the system runs three automated enrichment modules:

### 1. Temporal Semantics Analysis (`analyze_temporal_semantics`)
Implementation: [temporal_semantics.py](../temporal_semantics.py).
* **Multi-Factor Scoring**:
  * Evaluates all fields for temporal characteristics.
  * Scores are computed based on physical types, regex patterns on names (e.g., `timestamp`, `event_time`), and semantic attributes.
  * **Y-M-D Assembly**: If no single datetime column exists, but columns for `year`, `month`, and `day` are present, they are compiled into a virtual datetime candidate.
* **Time Axis Selection**:
  * Fields scoring $\ge 0.7$ are considered qualified candidates.
  * If the top two candidates are within $\le 0.05$ of each other, the analyzer registers an `ambiguous_time_axis_candidates` warning to prevent arbitrary selection.
  * The highest-scoring candidate is selected as the primary **Time Axis**, and its logical type is overridden to `time_axis`.
* **Grid and Frequency Profiling**:
  Analyzes the deltas of the time axis values:
  * **Timezone Detection**: Scans suffixes (like `Z` or `+08:00`). Mixed naive and aware timestamps mark the timezone as `conflicted`. Otherwise, a uniform timezone (like `UTC`) is recorded.
  * **Frequency**: Determines the dominant delta between sorted timestamps (e.g., 60 seconds -> `1 minute`).
  * **Regularity**: Labeled as `regular` if the dominant frequency describes $\ge 95\%$ of intervals.
  * **Missing Intervals**: Computes the expected number of grid points based on frequency and start/end bounds, then subtracts the actual record count.

### 2. Physical Unit Normalization (`normalize_unit_claim`)
Implementation: [unit_normalization.py](../unit_normalization.py).
* Input units (extracted from headers or attributes) are sent to the normalization engine.
* The engine queries `UNIT_ALIASES` to resolve synonyms (e.g., `celsius`, `c`, `Cel` are normalized to `Celsius` with UCUM code `Cel`; `mg/l`, `mg_l` to `milligram_per_liter` with UCUM code `mg/L`).
* Unrecognized units are marked as `unmapped_unit`.
* The `evidence_basis` is categorized by strength: `explicit_metadata` (from HDF5/NetCDF attributes) or `name_pattern` (guessed from column name).

### 3. Dataset Profiling (`build_dataset_profile`)
Implementation: [deterministic_profile.py](../deterministic_profile.py).
* Measures column-level nullability and missing ratios (`missing_ratio`).
* Evaluates key candidate columns (labeled `identifier`) for cardinality:
  * Nulls present ──► `incomplete_identifier`.
  * Unique ratio $\ge 98\%$ ──► `unique_identifier`.
  * Unique ratio between $50\% \sim 98\%$ ──► `group_identifier`.
  * Unique ratio $< 50\%$ ──► `low_cardinality_identifier`.
* Identifiers evaluated as unique or group fields are added to `best_identifier_fields` for downstream relationships.

---

## Phase 4: Evidence-Constrained LLM Semantics

After deterministic parsing and profiling, the system determines whether to enrich unresolved or `unknown` attributes. This semantic layer operates under strict safety constraints.

### 1. Grounding Bundle Generation
Implementation: [semantic_layer.py](../semantic_layer.py).
* The deterministic schema and contextual dataset documentation (such as README files) are compiled into a list of prioritized `GroundingSnippet` objects.
* This bundle is submitted to the LLM alongside standard system rules (`SYSTEM_RULES`).
* **LLM Rules**:
  * The model must not invent physical fields. All assertions must cite a snippet from the README in `supporting_evidence`.
  * If evidence is insufficient, the model must output `unknown`.
  * The response must conform to a strict JSON Schema.

### 2. Validation and Normalization (`validate_annotation_result`)
When the LLM returns its assertions, they are intercepted by a validator:
* Confirms `task_id` matches.
* Checks that all `field_path` entries correspond to valid physical fields in the deterministic schema.
* Verifies that the returned `logical_type` belongs to the eight allowed types.
* Validates that `confidence` falls within $[0.0, 1.0]$.
* Forces an `uncertainty_reason` if `semantic_type` is returned as `unknown`.

### 3. Conservative Merger (`merge_annotation_result`)
Valid assertions are integrated into the schema using these rules:
* **No Evidence Rejection**: If the LLM proposes an enrichment but leaves the `supporting_evidence` list empty, the change is rejected with an `unsupported_annotation_no_evidence` conflict.
* **Compatibility Check**: Prohibits incompatible logical-semantic pairs (e.g., mapping `latitude` to a `measurement` logical type).
* **Deterministic Protection**:
  * If the deterministic parser already extracted explicit metadata:
    * Proposals that match the existing value are accepted.
    * Proposals that disagree are rejected and logged under `conflicts`.
    * **Refinement Override**: If the existing logical type is compatible but generic (e.g., `measurement` -> `coordinate`), and the LLM confidence is $\ge 0.85$, it is merged and recorded under `logical_type_overrides`.
  * The audit report, including all conflicts and overrides, is stored in the metadata for full transparency.

---

## Phase 5: Unified Schema Envelope Projection

Finally, `unified_schema.py` projects the outcome into a standardized format via [build_unified_schema_envelope](../unified_schema.py#L64). The envelope decouples "assertions" (Claims) from "justifications" (Evidence) using a graph structure.

### 1. Envelope Structure
The schema envelope consists of the following top-level keys:
```json
{
  "schema_envelope_version": "1.0.0",
  "identity": {
    "dataset_id": "Dataset Identifier",
    "file_id": "Physical Filename",
    "file_format": "Detected Format",
    "data_modality": "Data Modality (e.g., tabular, multidimensional)",
    "resource_kind": "Resource Kind (file or directory_store)"
  },
  "format_detection": "Format decision records from Phase 1",
  "extractor_capability": "Metadata and capability declaration of the parser",
  "outcome": {
    "status": "Extraction status (success, partial, abstained, failed)",
    "issues": [ "Warnings, truncations, or errors encountered during extraction" ]
  },
  "physical_structure": {
    "fields": [ "Physical field definitions (names, physical types, shapes)" ],
    "groups": [ "Hierarchical containers" ],
    "dimensions": { "Dimensional axis configurations for high-dim data" },
    "format_specific": { "Internal parameters specific to the physical parser" }
  },
  "logical_roles": [ { "field_path": "Path", "logical_type": "Logical Type" } ],
  "semantic_hints": [ { "field_path": "Path", "semantic_type": "Semantic Type" } ],
  "units": [ { "field_path": "Path", "unit": "Raw Unit", "normalization": "UCUM details" } ],
  "temporal_semantics": { "Time axis, timezone, frequency, and missing grid intervals" },
  "claims": [ "Unified list of metadata claims" ],
  "evidence": [ "Deduplicated registry of physical evidence records" ],
  "provenance": {
    "source_file_id": "Original file source",
    "extractor_id": "ID of the deterministic extractor used",
    "extractor_version": "Version of the extractor",
    "determinism_class": "Class of determinism (e.g., strict, strict_metadata_only)",
    "transformation": "deterministic_unified_envelope_projection"
  },
  "conflicts": [ "Audit records of all conflicts during extraction and merging" ],
  "abstentions": [ "Abstention reasons and errors if outcome is abstained" ]
}
```

### 2. Claims & Evidence Binding
The core audit feature of the envelope is the mapping between the `claims` and `evidence` arrays:
* **Global Evidence Registry (`evidence`)**:
  All physical observations gathered during parsing are consolidated into a deduplicated registry and assigned unique IDs:
  ```json
  "evidence": [
    {
      "evidence_id": "e0001",
      "tier": "structural",
      "evidence_type": "csv_header",
      "source": "d:/data/weather.csv",
      "detail": "header='ts_utc'",
      "confidence": 1.0
    },
    {
      "evidence_id": "e0002",
      "tier": "statistical",
      "evidence_type": "sample_rows",
      "source": "d:/data/weather.csv",
      "detail": "sampled_rows=200",
      "confidence": 0.9
    }
  ]
  ```
* **Schema Claims (`claims`)**:
  Every assertion in the schema is normalized into a claim record. Each claim is assigned a `claim_id` and points to its evidence sources via `evidence_refs`:
  ```json
  "claims": [
    {
      "claim_id": "c0001",
      "subject": "ts_utc",
      "property": "physical_type",
      "value": "datetime",
      "state": "declared",
      "reason_code": "extractor_field_claim",
      "evidence_refs": [ "e0001", "e0002" ]
    },
    {
      "claim_id": "c0002",
      "subject": "ts_utc",
      "property": "logical_type",
      "value": "time_axis",
      "state": "supported",
      "reason_code": "extractor_field_property",
      "evidence_refs": [ "e0001", "e0002" ]
    }
  ]
  ```

This architecture ensures that even for massive, complex datasets, every metadata assertion can be traced back to its underlying physical evidence.
