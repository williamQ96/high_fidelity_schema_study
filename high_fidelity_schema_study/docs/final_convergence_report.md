# Final Convergence Report

Date: 2026-05-23

Target: Artifact Paper final polish, citation hygiene, demo polish, and release audit.

## Completion Summary

- Paper draft advanced to `v0.5` with artifact-ready wording and no new experimental claims.
- References were normalized into an ASCII-safe verified artifact bibliography.
- Paper citation keys are constrained to verified core references; `Auctus` remains in `Use With Caution` and is not used for a core paper claim.
- GUI mobile header status now wraps on narrow screens while preserving direct hash navigation for `#overview`, `#evidence`, `#fields`, `#semantic`, `#retrieval`, `#provenance`, and `#limits`.
- Artifact handoff, README checklist, GUI QA notes, and project log were updated to reflect final convergence polish rather than new experimentation.

## Verification Evidence

- `python -m high_fidelity_schema_study.build_paper_figures`: passed; rebuilt 5 SVG figures in `docs/figures/`.
- `python -m pytest high_fidelity_schema_study\tests`: passed; the prior Artifact Paper baseline was `57 passed`, and the final hygiene-expanded suite is `60 passed`.
- GUI inline JavaScript parse check from `docs/artifact_handoff.md`: passed with `inline scripts parse ok: 1`.
- HTTP smoke: passed with status `200` for `http://localhost:8765/gui_demo/` and `http://localhost:8765/docs/paper_result_tables_2026-05-15.json`.
- Chrome headless visual check: passed screenshot generation for desktop `#overview`, `#evidence`, `#fields`, `#semantic`, `#retrieval`, `#provenance`, and `#limits`, plus mobile `#overview` and `#fields`.
- Consistency search: passed for `docs/paper_draft.md`, `docs/references.md`, and `gui_demo` with no matches for stale TODOs, overclaim phrases, old convergence/version text, or encoding artifacts.

## Current Limits

- Internal corpus remains a 9-dataset pilot for method validation and failure analysis.
- External retrieval uses planted single-positive qrels over the frozen 16-file pool.
- External semantic merges are working annotations, not final gold references.
- Time-axis evaluation remains explicit: `time_axis_accuracy = 0.6667`, time-series family `time_axis_accuracy = 0.0000`, and `time_axis_mismatch = 3`.
- Evidence adequacy != correctness; provenance improves auditability but does not guarantee truth.

## Overclaim Prohibitions

- Do not claim broad robustness for open-ended dataset search.
- Do not claim the pilot corpus represents all scientific data formats or domains.
- Do not claim semantic merge is generally beneficial beyond the selected internal tasks.
- Do not claim planted qrels are equivalent to user-centered or graded relevance judgments.
- Do not claim provenance or evidence adequacy proves semantic correctness.

## Convergence Assessment

Current Artifact Paper convergence: `98%`.

Remaining 2% is venue/template-specific formatting and external human review by a reviewer, mentor, or collaborator.
