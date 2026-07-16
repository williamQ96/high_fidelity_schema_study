# From File Input to Unified Schema Envelope Output

This document describes the current File In -> Schema Out pipeline. The goal is not to guess a schema with an LLM. The goal is to produce the strongest schema supported by file structure, explicit metadata, deterministic validators, and recorded evidence.

## Design Principles

- **Deterministic first**: format-specific parsers establish physical structure before logical or semantic interpretation.
- **Evidence first**: fields and important claims point back to headers, sample rows, file attributes, format metadata, or validator output.
- **No unsupported completion**: weak evidence, format conflict, unsupported resources, or missing parsers result in `unknown`, `conflicted`, `partial`, `failed`, or `abstained` outcomes.
- **Frozen paper separation**: the Artifact Paper benchmark and headline metrics are not silently rewritten by post-freeze Phases 12-20.

```text
Raw file / directory store
  -> format detection and routing
  -> extractor capability registry
  -> registered deterministic extractor
  -> temporal / unit / profile validators
  -> structured ExtractionOutcome
  -> unified schema envelope
```

## 1. Intake And Format Detection

The entrypoint is `extract_path(ExtractionRequest(...))`. The system first validates whether the input is a regular file or directory store, then collects format signals:

- magic bytes for HDF5, Parquet, classic NetCDF, ZIP containers, and related strong signatures;
- directory signals for Zarr v2 metadata files such as `.zgroup`, `.zarray`, and `.zmetadata`;
- explicit format hints when they do not conflict with stronger signatures;
- suffix and conservative text probes for CSV/TSV, JSON/JSONL, XML, and similar text formats.

The decision priority is:

```text
magic/container signature > compatible explicit hint > suffix/text probe
```

Strong signal conflicts produce structured abstention instead of guessed fields.

## 2. Deterministic Structural Extraction

Each registered extractor is selected through the capability registry and returns a structured outcome.

### CSV

The CSV extractor reads headers and samples up to `sample_limit` rows. It records:

- `field_name` and `field_path`;
- conservative physical type;
- nullable, missing count, unique ratio, and value range;
- source evidence such as `csv_header` and `sample_rows`;
- bounded temporal analysis;
- guarded logical, semantic, and unit hints.

CSV semantic inference is intentionally conservative:

- clear coordinate names such as `lat` and `longitude` may map to coordinate semantics;
- temperature becomes `air_temperature` only with explicit environmental/weather context;
- explicit GPU temperature names such as `gpu_*temp*` map to `gpu_temperature`;
- generic `temp` remains `unknown`;
- `_c`, `_f`, and `_k` are temperature units only for temperature-like fields, so `input_dim_c` is treated as channel count and gets no Celsius unit claim.

### Other Registered Formats

- HDF5 traverses groups and datasets and preserves paths, dtypes, shapes, and explicit attributes.
- NetCDF/CF extracts dimensions, variables, coordinate attributes, calendars, units, and missing markers.
- Zarr v2 reads local directory-store metadata only; it does not read chunk payloads or claim remote-store, Zarr v3, or full Xarray reconstruction.
- Parquet/Arrow reads footer metadata and embedded Arrow schema without reading row values.
- JSON/JSON Lines reports bounded observed paths and separates declared JSON Schema from observed examples.
- XML/XSD performs lightweight namespace-aware structure extraction and does not act as a full validating XML processor.

## 3. Temporal, Unit, And Profile Validators

After physical extraction, shared validators add auditable claims:

- temporal semantics: candidates, canonical-axis selection, timezone, frequency, regularity, missing intervals, and ambiguity/conflict issues;
- unit normalization: evidence-backed unit claims with UCUM-like normalization or `unmapped_unit`;
- deterministic profile: missingness, identifier quality, and relationship candidates.

Validators enrich the evidence graph. They do not create unsupported physical fields.

## 4. Constrained Semantic Layer

Older semantic annotation experiments are downstream of deterministic extraction:

- they cannot create physical fields;
- they cannot overwrite explicit metadata with weaker evidence;
- non-`unknown` claims must cite supporting evidence;
- conflicts are recorded rather than silently resolved.

The system is therefore an agent-ready deterministic schema substrate, not an autonomous data agent.

## 5. Unified Schema Envelope

`extract_unified()` projects legacy outcomes into an additive envelope:

- identity;
- format detection;
- extractor capability;
- outcome issues;
- physical structure;
- logical roles;
- semantic hints;
- units;
- temporal semantics;
- claims;
- evidence;
- provenance;
- conflicts, abstentions, and unsupported features.

The envelope is a deterministic projection over existing claims. It does not promote new semantic truth and does not replace the legacy schema.

## Phase 20 Boundary

Phase 20 is a release-readiness convergence pass:

- current full regression suite: `183 passed`;
- release-readiness audit: `ready=true`;
- frozen Artifact Paper artifacts remain unchanged;
- Phases 12-20 are companion engineering evidence, not replacement paper metrics.

See `docs/phase20_companion_engineering_appendix.md` for the post-freeze engineering appendix.
