# Runnable Demo Examples

This directory contains small, portable inputs for reviewer demos. They are controlled examples, not evidence of broad ecosystem compatibility.

Run any file or directory through the generic CLI:

```text
python -m high_fidelity_schema_study.cli extract --input high_fidelity_schema_study/demo_examples/utc_series.csv --output-shape both
python -m high_fidelity_schema_study.cli extract --input high_fidelity_schema_study/demo_examples/opaque.bin --output-shape envelope
python -m high_fidelity_schema_study.cli extract --input high_fidelity_schema_study/demo_examples/basic_array.zarr --output-shape both
```

Run the GUI server and use the example buttons in the Extract workbench:

```text
python -m high_fidelity_schema_study.gui_demo.server 8765
```

The examples cover CSV temporal semantics, raw-binary abstention, NetCDF/CF, HDF5, Zarr v2 metadata, Parquet/Arrow metadata, bounded JSON structure, and an XML declared-observed conflict. Parquet examples do not read row values and the Zarr example contains metadata documents only.

`manifest.json` records each example's repository-relative source and SHA-256 digest. These are repository-generated controlled fixtures or internal pilot data; no external or sensitive data is included.
