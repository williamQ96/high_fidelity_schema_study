# Phase 16B: Lightweight XML / XSD Structure Extraction

Date: 2026-06-12

## Purpose

Phase 16B completes the initial semi-structured format track with registry-backed, namespace-aware XML observation and declared-only XSD extraction.

## Delivered

- `.xml` and `.xsd` registry routing.
- Bounded element and attribute paths using portable Clark notation for namespaces.
- Observed scalar type sets and repeated sibling paths.
- XSD element/attribute declarations, occurrence bounds, and required attributes.
- Explicit `xsi:type` declared-versus-observed conflicts.
- External schemas and entities are not loaded.
- CLI and GUI scratch compatibility.
- Isolated 5-case challenge pack, evaluator, artifacts, and tests.

## Controlled Result

All declared Phase 16B metrics are `1.0000`, including format/routing, mode, paths, repeated paths, namespaces, XSD declarations, declared-observed conflicts, sampling issues, and evidence coverage. Unsupported promotion count is `0`.

## Claim Boundaries

- Observed XML structure and repeat counts are bounded by `sample_limit`.
- XSD and `xsi:type` declarations remain separate from observations.
- XSD declarations are lightweight structural support, not complete XML Schema validation.
- External schemas, DTDs, and entities are not loaded.
- Semantic roles are not inferred from names.
- The controlled pack is not broad XML ecosystem evidence.
- Frozen benchmark artifacts, paper tables, figures, manuscript, and headline metrics remain unchanged.

## Next Gate

Proceed to the unified schema envelope while retaining legacy schema payloads. Broader XML work should be driven by external compatibility evidence rather than expanding into a full validating XML processor.
