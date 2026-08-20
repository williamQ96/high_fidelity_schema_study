# Reviewer Demo Script

## 1. Run Tests

```text
python -m pip install -r high_fidelity_schema_study/requirements-dev.txt
python -m pytest high_fidelity_schema_study/tests -q
```

## 2. Extract Legacy And Unified Output

```text
python -m high_fidelity_schema_study.cli extract --input high_fidelity_schema_study/testdata/parquet_phase15a/primitives.parquet --output-shape both
```

Show that:

- legacy `ExtractionOutcome.schema` is preserved;
- `unified_schema_envelope` contains normalized claims, evidence, provenance, and boundaries;
- Parquet reports `row_values_read=0`.

The same controlled input is available under `high_fidelity_schema_study/demo_examples/arrow_metadata.parquet`.

## 3. Show Bounded Semi-Structured Claims

```text
python -m high_fidelity_schema_study.cli extract --input high_fidelity_schema_study/testdata/json_phase16a/sampled.jsonl --sample-limit 3 --output-shape envelope
python -m high_fidelity_schema_study.cli extract --input high_fidelity_schema_study/testdata/xml_phase16b/xsi_conflict.xml --output-shape envelope
```

Show sample-bounded JSON structure and explicit XML declared-observed conflict handling.

## 4. Run Unified Evaluation

```text
python -m high_fidelity_schema_study.cli evaluate --scope all
```

Show that frozen references, bounded challenges, compatibility, external conformance, and cross-format contracts remain separate and that no aggregate score is produced.

## 5. Export Agent Context

```text
python -m high_fidelity_schema_study.cli agent-export --input high_fidelity_schema_study/testdata/netcdf_cf_phase13/standard_coordinates.nc
```

Show the read-only policy, claim/evidence records, provenance graph, capability context, and bounded actions.

## 6. Run the current research dashboard

```text
python -m high_fidelity_schema_study.gui_demo.server 8765
```

Open `http://localhost:8765/gui_demo/research_dashboard.html`.

Show that the page reads the current repository artifacts through
`/api/research-status`, while returning no sealed test identity, blind gold, reviewer
submission, model output, or test outcome. Walk through:

- the current defensible result and claim boundary;
- the deterministic pipeline and fixed A/B/C/D variants;
- the NDP-50 15/10/25 split and aggregate structural execution;
- development noncomparability and backend operational eligibility;
- the distinction between workflow readiness and completed human evidence;
- the F01-F16 collaborator-review status and ordered release sequence.

## 7. Run the extraction workbench

Open `http://localhost:8765/gui_demo/index.html#extract`.

Run these examples from the visible example list:

- `UTC time series`: deterministic temporal properties and evidence;
- `Opaque binary`: structured abstention with no invented fields;
- `Parquet / Arrow`: metadata-only extraction with `row_values_read=0`;
- `XML conflict`: a declared-observed conflict that remains visible.

Inspect format signals, issues/conflicts, claim-state counts, provenance, fields, and the expandable structured JSON. Scratch extraction does not modify frozen artifacts or paper metrics.

## 8. Run Portable Examples From CLI

```text
python -m high_fidelity_schema_study.cli extract --input high_fidelity_schema_study/demo_examples/utc_series.csv --output-shape both
python -m high_fidelity_schema_study.cli extract --input high_fidelity_schema_study/demo_examples/opaque.bin --output-shape envelope
python -m high_fidelity_schema_study.cli extract --input high_fidelity_schema_study/demo_examples/basic_array.zarr --output-shape both
```

`demo_examples/manifest.json` records repository-relative sources and SHA-256 digests. These controlled examples do not establish broad format compatibility.
