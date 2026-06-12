# Phase 15A: Parquet / Arrow Metadata-First Extraction

Date: 2026-06-12

## Purpose

Phase 15A adds a registry-backed Parquet extractor that reads Parquet footer metadata and the embedded Arrow schema without scanning row values. It extends representative deterministic format coverage while preserving explicit evidence, unsupported-promotion discipline, and frozen-artifact isolation.

## Delivered

- Parquet magic/suffix detection routed through the central registry.
- Recursive Arrow schema extraction for primitive, struct, list, and nested fields.
- Arrow type descriptors, nullability, field metadata, schema metadata, and timestamp timezone declarations.
- Explicit mapping between Arrow logical leaf paths and Parquet physical column paths.
- Parquet physical/logical types, converted types, definition levels, and repetition levels.
- Row-group metadata, compression, encodings, sizes, and footer statistics.
- Generic CLI and GUI scratch extraction compatibility.
- Isolated 8-case challenge pack, evaluator, generated artifacts, and tests.

## Controlled Result

| Metric | Result |
| --- | ---: |
| Format detection accuracy | `1.0000` |
| Extractor routing accuracy | `1.0000` |
| Arrow field accuracy | `1.0000` |
| Parquet column accuracy | `1.0000` |
| Row-group accuracy | `1.0000` |
| Compression accuracy | `1.0000` |
| Encoding accuracy | `1.0000` |
| Statistics policy accuracy | `1.0000` |
| Nullability accuracy | `1.0000` |
| Timestamp timezone accuracy | `1.0000` |
| Metadata accuracy | `1.0000` |
| Evidence coverage | `1.0000` |
| Row-value abstention accuracy | `1.0000` |
| Unsupported promotion count | `0` |

The controlled pack covers primitives, nested structs/lists, dictionary encoding, timezone-aware and naive timestamps, required and nullable fields, multiple row groups, absent footer statistics, decimal/binary types, and an empty table.

## Claim Boundaries

- `pyarrow` is required as the current spec-backed Parquet metadata backend.
- The extractor does not call row-reading APIs and reports `row_values_read=0`.
- Min/max, null count, distinct count, and value count are copied only from footer statistics and are not independently validated against row values.
- Arrow logical paths and Parquet physical paths are retained separately because nested-list encodings may differ.
- Dictionary encoding is visible in Parquet column metadata, but an Arrow dictionary logical type may not round-trip through every Parquet producer.
- Timestamp timezone is a declared Arrow type property. Naive timestamps remain timezone `unknown`.
- Semantic roles are not inferred from field names.
- The PyArrow-produced challenge pack is bounded evidence, not broad ecosystem robustness.
- Frozen benchmark artifacts, paper tables, figures, manuscript, and headline metrics remain unchanged.
- Full repository regression suite at completion: `136 passed`.

The Phase 12 post-freeze format-routing case for the intentionally malformed Parquet payload was updated from unsupported-format abstention to registered-extractor `parser_error`. Phase 12 remains at `1.0000` across its declared current-state metrics.

## Next Gate

The next Parquet step should be a small externally sourced or multi-producer compatibility corpus, including non-PyArrow files and malformed/unsupported feature cases. Phase 16 JSON observed-structure work can proceed in parallel once Phase 15A remains green.
