# Artifact Handoff

This is the concise handoff for the Artifact Paper package. The package is a paper draft plus a GUI demo over frozen study artifacts. The demo also includes a scratch extraction tab for local file inspection.

## Primary Artifacts

- Paper draft: `docs/paper_draft.md`
- Academic rigor audit: `docs/academic_rigor_audit.md`
- Verified bibliography: `docs/references.md`
- Citation-role matrix: `docs/literature/citation_matrix.md`
- Time-axis adjudication: `docs/time_axis_gap_adjudication.md`
- Paper figures: `docs/figures/`
- GUI demo: `gui_demo/`
- GUI visual QA: `docs/gui_visual_qa.md`
- Frozen benchmark card: `docs/benchmark_card_2026-05-15.md`
- Generated paper tables: `docs/paper_result_tables_2026-05-15.md`

## Run The GUI Demo

For the full GUI, including upload-based scratch extraction, run from the repository root:

```bash
python -m high_fidelity_schema_study.gui_demo.server 8765
```

For read-only artifact inspection only, this also works from `high_fidelity_schema_study/`:

```bash
python -m http.server 8765
```

Open:

```text
http://localhost:8765/gui_demo/
```

The main GUI views are an inspection layer. They read frozen JSON artifacts and should not change benchmark membership, gold references, qrels, metrics, semantic annotations, or merge policy. The Extract tab is scratch-only: it returns one uploaded file's deterministic schema to the browser and does not write into frozen artifacts.

## Rebuild Report Visuals

From the repository root:

```bash
python -m high_fidelity_schema_study.build_paper_tables
python -m high_fidelity_schema_study.build_paper_figures
```

## Verify

```bash
python -m pytest high_fidelity_schema_study\tests
```

Static GUI JavaScript parse check:

```bash
node -e "const fs=require('fs'); const html=fs.readFileSync('high_fidelity_schema_study/gui_demo/index.html','utf8'); const re=new RegExp('<script>([\\\\s\\\\S]*?)<\\\\/script>','g'); const scripts=[...html.matchAll(re)].map(m=>m[1]); for (const script of scripts) new Function(script); console.log('inline scripts parse ok:', scripts.length);"
```

HTTP smoke:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8765/gui_demo/ | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest -UseBasicParsing http://localhost:8765/docs/paper_result_tables_2026-05-15.json | Select-Object -ExpandProperty StatusCode
```

## Known Limits To Preserve

- The internal pilot is intentionally small.
- External retrieval qrels are planted single-positive judgments.
- External semantic merges are working annotations, not final gold references.
- Time-axis accuracy remains a known non-final gap in the frozen slice.
- Evidence adequacy and provenance establish auditability, not semantic truth.

## Current Convergence Assessment

After the final convergence polish, the Artifact Paper package is approximately `98%` converged. Remaining work is venue-specific formatting and external human review.
