# High-Fidelity Schema GUI Demo

This directory contains the reviewer-facing demo for the high-fidelity schema extraction study.

The main views are an inspection layer over frozen artifacts. They should not change benchmark membership, gold references, qrels, headline metrics, or semantic merge policy.

The Extract view is a local scratch workbench. It can upload one HDF5 file, CSV time-series file, or raw binary payload and run the deterministic-first extraction path for inspection. Scratch extraction returns JSON to the browser only; it does not write into `data/`, alter the frozen benchmark, or update paper metrics.

The page includes a visible Artifact Boundary banner covering planted qrels, the small internal pilot, working external semantic annotations, and the known time-axis gap.

## Run

For the full demo, including scratch uploads, run from the repository root:

```bash
python -m high_fidelity_schema_study.gui_demo.server 8765
```

For read-only artifact inspection only, this also works from `high_fidelity_schema_study/`:

```bash
python -m http.server 8765
```

Then open:

```text
http://localhost:8765/gui_demo/
```

The page attempts to load these artifact files:

- `docs/paper_result_tables_2026-05-15.json`
- `data/derived/internal_baseline_report.json`
- `data/retrieval/external_candidate_pool/retrieval_report.json`
- `data/semantic_merged/semantic_merge_report.json`
- `data/derived/provenance_manifest.json`
- `data/retrieval/external_candidate_pool/qrels.json`

If artifact loading fails, the page still shows a small embedded fallback summary so the layout remains inspectable.

## Views

- Overview: frozen-slice counts, internal baseline metrics, and error modes.
- Evidence: evidence adequacy ratios and source evidence type counts.
- Fields: dataset-level metrics and field-level match/uncertainty inspection from the internal baseline report.
- Semantic Merge: accepted merge and conflict summary.
- Retrieval: Recall@1 comparison and per-query top-1 inspection.
- Provenance: entity, activity, and agent counts from the PROV-like manifest.
- Extract: scratch deterministic schema extraction for HDF5, CSV time-series, and high-fidelity raw-binary abstention.
