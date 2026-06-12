# Phase 16A: Conservative JSON Structure Extraction

Date: 2026-06-12

## Purpose

Phase 16A adds registry-backed JSON and JSON Lines extraction with bounded observed-structure claims. It also recognizes JSON Schema documents and keeps declared properties separate from observed examples and conflicts.

## Delivered

- `.json`, `.jsonl`, and `.ndjson` registry routing.
- Bounded path, type-set, null, missing, nested-object, and array-shape observations.
- Heterogeneous array visibility.
- Structured `sampling_insufficient` notes when JSON Lines exceed `sample_limit`.
- JSON Schema declared fields, required/nullability handling, and descriptions.
- Declared-versus-observed type conflicts from JSON Schema `examples`.
- Generic CLI and GUI scratch compatibility.
- Isolated 6-case challenge pack, evaluator, artifacts, and tests.

## Controlled Result

All declared Phase 16A metrics are `1.0000`, including format/routing, mode, paths, missingness, nullability, heterogeneous arrays, declared schema, declared-observed conflicts, sampling issues, and evidence coverage. Unsupported promotion count is `0`.

## Claim Boundaries

- Observed structure is bounded by `sample_limit` and is not universal schema truth.
- JSON documents larger than the bounded parser byte limit abstain rather than being partially guessed.
- Missingness is reported relative to sampled top-level records.
- JSON Schema properties are declared claims, not observed-data claims.
- JSON Schema `examples` are bounded observations and may produce explicit conflicts; they never override declarations.
- Semantic roles are not inferred from names.
- XML/XSD remains deferred to a later Phase 16 subphase.
- Frozen benchmark artifacts, paper tables, figures, manuscript, and headline metrics remain unchanged.
- Full repository regression suite at completion: `148 passed`.

## Next Gate

Add lightweight XML/XSD structure extraction or proceed to the unified schema envelope. A broader JSON compatibility round should include larger JSON Lines inputs, additional JSON Schema constructs, and externally sourced documents before making wider claims.
