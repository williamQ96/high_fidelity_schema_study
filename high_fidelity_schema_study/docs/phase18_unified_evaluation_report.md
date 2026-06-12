# Phase 18: Unified Evaluation Harness

Date: 2026-06-12

Phase 18 adds one common evaluation entrypoint:

```text
python -m high_fidelity_schema_study.cli evaluate --scope all
python -m high_fidelity_schema_study.cli evaluate --scope extensions
```

The generated report covers 11 tracks when frozen references are included:

- 2 frozen Artifact Paper reference tracks;
- 6 bounded challenge tracks;
- 1 compatibility track;
- 1 external-conformance track;
- 1 cross-format contract track.

`aggregate_score` is deliberately `null`. Frozen, bounded, compatibility, external, and cross-format evidence have different scopes and must not be collapsed into one score. Frozen metrics are referenced only and are not rerun or rewritten.

Generated artifacts live under `data/experiments/phase18_unified_evaluation/`.
