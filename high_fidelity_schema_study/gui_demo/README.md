# High-Fidelity Schema GUI Demo

This directory contains two reviewer-facing interfaces for the high-fidelity schema extraction study:

- `research_dashboard.html`: the current research console for the English manuscript,
  A/B/C/D methodology, NDP-50 aggregate execution, backend qualification, human
  workflow, and fail-closed readiness gates;
- `index.html`: the deterministic extraction workbench and legacy artifact inspector.

The research dashboard loads `/api/research-status` at runtime. The server assembles
that response directly from the current content-addressed paper, selection, execution,
qualification, readiness, and human-assignment artifacts. It returns aggregate state
only and never exposes sealed test identities, blind gold, reviewer submissions, model
outputs, or test outcomes.

The main views are an inspection layer over frozen artifacts. They should not change benchmark membership, gold references, qrels, headline metrics, or semantic merge policy.

The Extract view is the default local scratch workbench. It can run an allowlisted portable example, upload one NetCDF/CF, Parquet/Arrow, JSON/JSON Lines, HDF5, CSV time-series, or raw binary file, or select one local Zarr v2 directory store. Scratch extraction returns results to the browser only; it does not write into `data/`, alter the frozen benchmark, or update paper metrics. Parquet extraction reads footer/schema metadata without row values, JSON extraction is sample-bounded, and Zarr scratch intake uploads metadata documents only without chunk payloads.

Scratch extraction is routed through the Phase 12 capability registry. Responses preserve the existing `schema` payload and additionally include `extraction_outcome` with format signals, selected extractor capability, status, and structured issues.

Responses also include the additive `unified_schema_envelope`, which normalizes claims, evidence, provenance, conflicts, and abstentions without replacing the legacy schema. The workbench surfaces format signals, structured issues, claim-state counts, conflicts, and provenance before the raw JSON.

Failed parser or missing-backend outcomes remain visible in the workbench. The
server returns the format decision, selected extractor, reason codes, issues,
and unified envelope even when no schema payload can be produced.

The visual system is documented in [DESIGN.md](DESIGN.md). It uses a compact developer-tool layout with visible semantic states and responsive navigation.

The page includes a visible Artifact Boundary banner covering planted qrels, the small internal pilot, working external semantic annotations, and the known time-axis gap. Runnable controlled examples are documented in [demo_examples/README.md](../demo_examples/README.md).

## Run

For the full demo, including scratch uploads, run from the repository root:

```bash
python -m pip install -r high_fidelity_schema_study/requirements.txt
python -m high_fidelity_schema_study.gui_demo.server 8765
```

For read-only artifact inspection only, this also works from `high_fidelity_schema_study/`:

```bash
python -m http.server 8765
```

Then open:

```text
http://localhost:8765/gui_demo/research_dashboard.html
```

The extraction workbench remains available at
`http://localhost:8765/gui_demo/index.html#extract`.

The page attempts to load these artifact files:

- `docs/paper_result_tables_2026-05-15.json`
- `data/derived/internal_baseline_report.json`
- `data/retrieval/external_candidate_pool/retrieval_report.json`
- `data/semantic_merged/semantic_merge_report.json`
- `data/derived/provenance_manifest.json`
- `data/retrieval/external_candidate_pool/qrels.json`

If artifact loading fails, the page still shows a small embedded fallback summary so the layout remains inspectable.

## Views

Research Console:

- Overview: current defensible claim, research architecture, and paper snapshot.
- Methodology: deterministic pipeline, fixed A/B/C/D variants, paired inference,
  replay control, and blind-gold information separation.
- NDP-50 corpus: 15/10/25 split, selection strata, aggregate development and
  validation extraction coverage, and sealed-test boundary.
- Evidence: diagnostic development metrics and operational backend qualification.
- Readiness gates: structural checks, evidence-completion matrix, and filterable blockers.
- Human workflow: assignment roles, F01-F16 collaborator review, release sequence,
  and information boundaries.

Extraction Workbench:

- Overview: frozen-slice counts, internal baseline metrics, and error modes.
- Evidence: evidence adequacy ratios and source evidence type counts.
- Fields: dataset-level metrics and field-level match/uncertainty inspection from the internal baseline report.
- Semantic Merge: accepted merge and conflict summary.
- Retrieval: Recall@1 comparison and per-query top-1 inspection.
- Provenance: entity, activity, and agent counts from the PROV-like manifest.
- Extract: scratch deterministic schema extraction for NetCDF/CF, Parquet/Arrow metadata, bounded JSON structure, HDF5, CSV time-series, local Zarr v2 directory metadata, and high-fidelity raw-binary abstention.
- Extract result review: visible format decision, issues/conflicts, claim states, provenance, fields, and expandable structured JSON.
