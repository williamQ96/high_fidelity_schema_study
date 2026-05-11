# Retrieval Artifacts

This directory stores retrieval-ready assets derived from the current promoted benchmark candidate pool.

## Current Pool

- Source pool: promoted entries from [data/external/benchmark_candidates.json](D:\github\searnxg\llm-schema\high_fidelity_schema_study\data\external\benchmark_candidates.json)
- Current target count: 6
- Current distractor count: 4
- Current total pool size: 10

The harder distractors are pinned in [external_candidate_pool/pool_manifest.json](D:\github\searnxg\llm-schema\high_fidelity_schema_study\data\retrieval\external_candidate_pool\pool_manifest.json) and were chosen to be same-family or same-record neighbors rather than distant random noise.

## Current Artifacts

Artifacts for the promoted external pool live under [external_candidate_pool](D:\github\searnxg\llm-schema\high_fidelity_schema_study\data\retrieval\external_candidate_pool).

- `metadata_only.json`
  Metadata-focused retrieval documents using title, keywords, creators, DOI-related metadata, and file names.
- `readme_only.json`
  README-like text baseline built from source-record descriptions and notes. For the current Zenodo imports, this is a description-only proxy because standalone README files are not present.
- `schema_enhanced.json`
  Metadata plus deterministic schema summaries, semantic labels, units, and time-axis details.
- `queries.json`
  Planted-match retrieval queries for the promoted pool.
- `artifact_manifest.json`
  Manifest describing the artifact files and the assumptions behind them.
- `retrieval_report.json` and `retrieval_report.md`
  First retrieval comparison results over the current promoted pool, including Recall@k, Precision@k, MRR, nDCG, and per-query case summaries.

## Current Result Snapshot

On the current expanded 10-file pool:

- `metadata_only` reaches `recall_at_1 = 0.3333`
- `readme_only` reaches `recall_at_1 = 0.5000`
- `schema_enhanced` reaches `recall_at_1 = 0.8333`

This is a more honest result than the earlier smaller pool because same-family distractors are now present. `schema_enhanced` still leads after expansion, while `metadata_only` drops substantially.

## Next Step

Add semantic-layer signals and, if possible, locally available Dryad payloads to keep increasing distractor difficulty.
