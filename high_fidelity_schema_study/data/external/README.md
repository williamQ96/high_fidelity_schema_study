# External Corpus Staging

This directory contains the first external acquisition batch for the high-fidelity schema extraction study.

## What Is Here

- [curated_sources.json](D:\github\searnxg\llm-schema\high_fidelity_schema_study\data\external\curated_sources.json)
  Selected Dryad and Zenodo records, file targets, and selection rationale.
- [import_manifest.json](D:\github\searnxg\llm-schema\high_fidelity_schema_study\data\external\import_manifest.json)
  Machine-readable result of the latest import run.
- [benchmark_candidates.json](D:\github\searnxg\llm-schema\high_fidelity_schema_study\data\external\benchmark_candidates.json)
  First-pass triage of which staged files are promoted, pending, or blocked for later benchmark use.
- `derived/`
  Deterministic schema outputs for successfully downloaded supported files, plus a derived manifest recording skipped and failed cases.
- `dryad/`
  Per-record metadata snapshots and landing pages. File payload downloads are currently blocked by Dryad's human-verification gate in this environment.
- `zenodo/`
  Per-record metadata snapshots, landing pages, and successfully downloaded files.

## Current Batch Status

- Actual downloaded files: 8
- Actual downloaded size: about 28.27 MB
- External derived schemas successfully built: 8
- External extraction failures currently recorded: 0 batch-blocking failures
- Dryad selected files staged as metadata targets: 8
- Dryad file payload status: blocked by HTTP 403 from `downloads/file_stream/*` in this environment

## Current Zenodo Payloads

- `record_15008662/unique_tracks_90.csv`
- `record_5935524/20211108_ZXLidar_Winds.csv`
- `record_5935524/20211108_Sensit.csv`
- `record_5935524/20211108_Tides.csv`
- `record_18195710/ensensia_raw_20230728-20251202_school_5.csv`
- `record_3660832/Data 01 Jan 2019.h5`
- `record_3660832/Data 07 July 2019.h5`
- `record_5116851/DataseParaWorkshop_v2.h5`

## Current Derived Status

- See [derived/derived_manifest.json](D:\github\searnxg\llm-schema\high_fidelity_schema_study\data\external\derived\derived_manifest.json) for per-file extraction status.
- One downloaded HDF5 file is partially recoverable and now records per-node `extraction_errors` in its derived schema instead of failing the whole batch.
- See [benchmark_candidates.json](D:\github\searnxg\llm-schema\high_fidelity_schema_study\data\external\benchmark_candidates.json) for the current promotion decision on each staged external file.

## Dryad Note

Dryad record metadata and landing pages were successfully fetched, but direct file payload downloads were blocked by Dryad's human-verification gate for programmatic access in this environment. The selected targets are still pinned in `curated_sources.json` and `import_manifest.json`, so a later manual or browser-assisted pass can complete those downloads without repeating source selection.
