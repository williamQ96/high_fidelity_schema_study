# Data Layout

This directory now contains a reproducible 9-dataset pilot corpus for the high-fidelity schema extraction study.

## Structure

- `raw/csv/` contains three tabular CSV pilot datasets
- `raw/time_series/` contains three time-series CSV pilot datasets
- `raw/hdf5/` contains three hierarchical HDF5 pilot datasets
- `gold/` contains one gold schema JSON per dataset
- `derived/` is reserved for deterministic extractor outputs
- `retrieval/` is reserved for retrieval indices and query artifacts
- `pilot_corpus_manifest.json` is the corpus index

All files in `raw/` are deliberately small and human-readable so the study can start with interpretable field-level evaluation before scaling.
