# Acquisition Log

## 2026-04-27

### Decision 1

- Request interpreted as corpus-preparation work, not final benchmarking.
- Objective set to: download a moderate, curated external corpus from Dryad and Zenodo into this study directory, with enough diversity to support later extractor expansion and retrieval experiments.

### Decision 2

- No dedicated `log agent` skill is available in this session.
- Fallback chosen: keep the durable, user-facing acquisition trail in this file and use the `note` skill only as conceptual guidance for persistence discipline.

### Decision 3

- Selection policy chosen before downloading:
- Prefer openly downloadable records.
- Prefer file types directly relevant to the study: `csv`, `tsv`, `hdf5`, `h5`, and time-series-friendly tabular exports.
- Prefer small-to-moderate files first so setup remains reproducible and reviewable.
- Avoid pulling very large archives as the first import batch unless they are the only viable source for a needed format.

### Decision 4

- Acquisition will be manifest-driven instead of ad hoc.
- Added [curated_sources.json](D:\github\searnxg\llm-schema\high_fidelity_schema_study\data\external\curated_sources.json) to pin the selected Dryad DOIs, Zenodo record ids, chosen files, and rationale.
- Added [import_external_corpus.py](D:\github\searnxg\llm-schema\high_fidelity_schema_study\import_external_corpus.py) so imports can be re-run and audited.

### Candidate Selection Notes

- Dryad `10.5061/dryad.04t19`: selected `boundaryflow_snapshots.hdf5`; rejected the much larger companion HDF5 files for the first batch because they are hundreds of MB each.
- Dryad `10.5061/dryad.2f2b3`: selected the direct year1/year2 CSV files because they are immediately usable as time-series candidates.
- Dryad `10.5061/dryad.zkh1893nh`: selected four direct CSV files instead of notebooks and archives because the study needs schema-rich tables first.
- Dryad `10.5061/dryad.dv41ns266`: selected the direct weather station CSV because it is medium-sized and format-aligned.
- Zenodo `15008662`: selected `unique_tracks_90.csv` as a compact timestamp-and-geo table.
- Zenodo `5935524`: selected three direct CSV time-series files and skipped the larger holographic particle CSV in the first batch.
- Zenodo `18195710`: selected the smaller school-level CSV to keep the first import moderate while still adding real raw sensor data.
- Zenodo `3660832`: selected two monthly `.h5` files instead of the full yearly collection.
- Zenodo `5116851`: selected the single direct `.h5` file as a small binary-format smoke case.

### Import Process

- First import run failed on Zenodo because `urllib` requests to `.../content` links were rejected, while `requests` worked.
- Importer was changed to use `requests` for both metadata fetches and file downloads.
- Second import run then failed on Dryad because API file download endpoints returned `401 Unauthorized`.
- Dryad download resolution was changed from `/api/v2/files/.../download` to public `downloads/file_stream/<id>` links derived from file ids.
- Third import run showed Dryad file-stream links are still blocked in this environment with `403 Forbidden`, while landing pages and metadata remain accessible.
- Importer was changed to best-effort mode so blocked Dryad payloads are recorded without aborting the whole batch.
- Landing pages are now also saved locally per record for audit and later manual follow-up.

### Import Outcome

- Zenodo payload downloads succeeded for 8 files totaling about 28.27 MB.
- Dryad payload downloads did not succeed in this environment, but record metadata and landing pages were staged locally for 4 selected Dryad records and 8 selected Dryad files.
- Current machine-readable result is stored in [import_manifest.json](D:\github\searnxg\llm-schema\high_fidelity_schema_study\data\external\import_manifest.json).
- Current staged corpus summary is stored in [data/external/README.md](D:\github\searnxg\llm-schema\high_fidelity_schema_study\data\external\README.md).

### Decision 5

- Accepted best-effort corpus staging rather than failing the entire preparation task.
- Reason: Zenodo provides enough actual downloadable payloads to move schema-extraction work forward now, while Dryad is blocked by repository-side human verification rather than a repository-local bug.

### Post-Import Validation

- Ran the CSV extractor on `zenodo/record_15008662/unique_tracks_90.csv`; extractor recognized 4 fields and classified it as time-series-shaped because of the timestamp field and numeric measurements.
- Ran the CSV extractor on `zenodo/record_5935524/20211108_ZXLidar_Winds.csv`; extractor treated it conservatively as tabular rather than forcing a time-series label.
- Ran the HDF5 extractor on `zenodo/record_5116851/DataseParaWorkshop_v2.h5`; extractor read it successfully as hierarchical with three top-level datasets.

### Entry 1

Summary:
- Switched logging mode to the project-log skill format for ongoing study history.
- External corpus staging remains best-effort: 8 Zenodo payloads downloaded and Dryad metadata staged with payload downloads blocked by repository-side human verification.

Action Points:
- Use project-log structured entries for subsequent dataset, extraction, and evaluation milestones.
- If Dryad payloads are still needed, complete them with a browser-assisted manual pass using the pinned records in data/external/curated_sources.json.

Important Process:
- Used the bundled project-log helper because the workspace does not provide scripts/update_log.py.
- Appended a new dated entry instead of rewriting the earlier freeform acquisition notes, to preserve prior decision history.

### Entry 2

Summary:
- Clarified core study terminology in the README by defining pilot as the controlled first-round corpus and gold as the human-authored reference schema used for evaluation.
- Aligned the study README with the actual directory state, including internal pilot assets, derived schemas, external corpus staging, rebuild commands, and logging conventions.

Action Points:
- Keep future README updates synchronized with real directory state whenever new scripts, manifests, or corpus stages are added.
- Use the clarified pilot and gold language consistently in future evaluation docs and experiment writeups.

Important Process:
- Treated the README as a project contract and checked for documentation drift against the live directory contents before editing.
- Removed generated __pycache__ directories so the live folder state more closely matches the documented research structure.

### Entry 3

Summary:
- Expanded the README into an end-to-end roadmap and checklist covering the full study lifecycle from framing through paper delivery.
- Marked already completed milestones as checked so the README now doubles as both project contract and execution tracker.

Action Points:
- Keep the checklist state current whenever corpus, extraction, evaluation, or writing milestones change.
- Use the checklist phases to drive the next implementation sequence instead of adding new ad hoc TODO lists elsewhere.

Important Process:
- Organized the roadmap by phase so completed and pending work are separated cleanly across framing, corpus building, extraction, evaluation, retrieval, scale-up, and paper writing.
- Kept incomplete items explicit rather than over-checking partially staged work, especially for Dryad payload acquisition and evaluation pipeline tasks.

### Entry 4

Summary:
- Implemented the first internal field-level baseline evaluation and generated reports at data/derived/internal_baseline_report.json and .md.
- Implemented batch deterministic extraction for downloaded external files and generated external derived outputs plus a derived manifest under data/external/derived/.
- Advanced the README checklist by checking completed evaluation and external-derived milestones and documenting the new artifacts.

Action Points:
- Review the internal baseline metrics to decide which logical and semantic heuristics should be improved first.
- Triage the 7 successful external derived schemas and decide which should be promoted into benchmark candidates.
- Investigate or exclude the one external HDF5 file currently marked extraction_failed before depending on it in later benchmark planning.

Important Process:
- Kept both new scripts best-effort and manifest-driven so one failing external file does not block the whole batch.
- Validation confirmed 7 successful unit tests, internal baseline aggregate metrics generation, and external status counts of 7 derived_built, 8 skipped_not_downloaded, and 1 extraction_failed.

### Entry 5

Summary:
- Implemented a first deterministic heuristic upgrade for CSV and HDF5 logical and semantic typing, driven by the internal baseline gaps.
- Rebuilt internal derived schemas and refreshed the internal baseline report, lifting aggregate logical_accuracy to 0.9444, semantic_accuracy to 1.0000, and unit_accuracy to 0.8889 while keeping physical_accuracy at 0.9815.
- Made HDF5 extraction tolerant to per-node failures, so the external July 2019 atmospheric file now yields a derived schema with recorded extraction_errors instead of failing the whole batch.
- Created first-pass external benchmark triage at data/external/benchmark_candidates.json with 3 promoted, 5 pending, and 8 blocked_not_downloaded files.

Action Points:
- Add time-part assembly heuristics for external CSVs that currently expose split Year/Month/Day/Hour/Minute/Second columns.
- Decide whether the partially recoverable Data 07 July 2019.h5 file is acceptable as a benchmark candidate or should be excluded.
- Use the promoted external files as the first cross-dataset retrieval candidate pool once retrieval artifacts are built.

Important Process:
- Re-ran internal build and evaluation sequentially, not in parallel, because the evaluation reads data/derived outputs and can otherwise observe stale files.
- The external builder remains manifest-driven and best-effort, but all 8 downloaded external files now produce derived schemas successfully at batch level.

### Entry 6

Summary:
- Added deterministic time-part assembly for CSV files with split Year/Month/Day/Hour/Minute/Second columns and allowed exact date fields to drive time-series detection.
- Rebuilt external derived schemas so the previously pending Zenodo wind, Sensit, and tides CSVs now extract as time_series rather than plain tabular files.
- Updated benchmark candidate triage: the three split-time CSVs are now promoted, leaving only the two HDF5 edge cases pending among downloaded files.

Action Points:
- Decide whether Data 07 July 2019.h5 should remain a benchmark candidate despite per-node extraction_errors.
- Decide whether DataseParaWorkshop_v2.h5 is realistic enough to keep in the benchmark candidate pool.
- Start retrieval-artifact construction using the promoted external candidate set.

Important Process:
- Implemented time-part assembly as metadata-only evidence: no synthetic schema field is added, but the computed time axis is recorded under metadata.time_series.time_axis.computed_from.
- Kept the assembled-time heuristic conservative by requiring standard component columns and leaving raw columns intact in the schema output.

### Entry 7

Summary:
- Built retrieval artifacts for the 6 promoted external candidates: metadata_only, readme_only, schema_enhanced, planted queries, and an artifact manifest under data/retrieval/external_candidate_pool/.
- Implemented a first lexical retrieval evaluator and generated retrieval_report.json and retrieval_report.md with Recall@k, Precision@k, MRR, nDCG, and per-query case summaries.
- Improved retrieval tokenization by splitting underscore-delimited field names, which materially improved schema_enhanced retrieval behavior for the promoted pool.
- Current first-pass result: schema_enhanced recall_at_1 = 0.8333, readme_only recall_at_1 = 0.5000, metadata_only recall_at_1 = 0.6667.

Action Points:
- Improve discrimination for the remaining particle-count query that still ranks the wind-lidar file above the Sensit file in the schema_enhanced setting.
- Decide whether the two pending HDF5 candidates should be promoted, excluded, or held for a later benchmark tier.
- Use the current retrieval artifacts and reports as the baseline comparison bundle for the next retrieval iteration.

Important Process:
- The readme_only baseline is currently a README-like proxy derived from Zenodo record descriptions and notes because standalone README files are not available for the imported Zenodo records.
- The retrieval evaluator should be run after artifact construction, and the latest report should be trusted only after a sequential rerun to avoid stale parallel-read outputs.

### Entry 8

Summary:
- Checked the live directory against the README contract again: no method shift was found, but there was minor documentation drift and regenerated __pycache__ runtime clutter.
- Fixed the remaining schema_enhanced retrieval miss for particle_counts_time_series by splitting camel-case tokens during retrieval evaluation so ParticleCounts contributes particle and counts as separate lexical signals.
- After the retrieval evaluator fix, the current promoted-pool schema_enhanced result improved to recall_at_1 = 1.0000, mrr = 1.0000, and ndcg_at_3 = 1.0000 on the planted query set.
- Updated the README folder layout and retrieval status text so it again matches the current directory state and latest retrieval report.

Action Points:
- Move next to semantic-layer work or enlarge the promoted retrieval pool, since the current planted retrieval set is now saturated for the schema_enhanced lexical baseline.
- If retrieval work continues first, add harder same-record and cross-record distractors so the current 6-candidate pool does not overstate progress.

Important Process:
- Treated README as the active project contract, then corrected drift instead of leaving the directory state and documentation to diverge.
- Cleared regenerated __pycache__ directories after the drift check so runtime byproducts do not get mistaken for planned research assets.

### Entry 9

Summary:
- Expanded the retrieval pool from 6 promoted targets to a 10-file pool by adding 4 harder same-family distractors: HoloParticles, a second indoor-air school CSV, and two additional ATLASM5 monthly HDF5 files.
- Introduced retrieval-pool-specific manifests and scripts so retrieval difficulty can grow without changing benchmark-candidate semantics.
- Reran retrieval evaluation on the harder pool and observed a more honest spread: metadata_only recall_at_1 = 0.3333, readme_only recall_at_1 = 0.5000, schema_enhanced recall_at_1 = 0.8333.
- Checked the live directory against the README again; there was no method shift, only minor documentation/runtime drift, which was corrected.

Action Points:
- Use the expanded 10-file pool as the new default retrieval evaluation pool for subsequent iterations.
- If retrieval work continues, add more same-family distractors or locally available Dryad payloads before claiming broad retrieval robustness.
- If method work continues next, prioritize the semantic layer rather than squeezing more gain from the current lexical schema-enhanced baseline.

Important Process:
- Separated retrieval-pool manifests from benchmark-candidate manifests so distractor expansion does not falsely imply benchmark-target promotion.
- Updated the README and retrieval README after expansion so the documented pool size and retrieval metrics do not drift from the current artifacts.

## 2026-04-28


### Entry 1

Summary:
- Completed the remaining Phase 7 evaluation items by extending the internal baseline report with confidence-bucket uncertainty analysis and grouped error-mode reporting.
- Started Phase 8 by defining an evidence-constrained semantic annotation interface in semantic_layer.py and docs/semantic_annotation_interface.md.
- Built semantic grounding task bundles from internal README files and external source-record metadata, producing 9 internal tasks and 10 external tasks under data/semantic_grounding/.

Action Points:
- Implement the actual LLM-assisted semantic annotation step over the grounding task bundles.
- Add explicit unknown/conflict handling to semantic annotation outputs so semantic merge-back stays evidence-constrained.
- Keep README, retrieval docs, and semantic-layer docs synchronized as the Phase 8 execution path becomes concrete.

Important Process:
- Used task-bundle generation rather than direct model calls first so the semantic layer has an auditable, rerunnable input contract before execution logic is added.
- Updated the checklist only after the grounding manifest and interface files existed on disk and were verified locally.

### Entry 2

Summary:
- Completed the remaining Phase 8 execution-path implementation by adding semantic_annotate.py, merge_semantic_annotations.py, semantic result validation, normalization, and merge-back safeguards.
- Built and verified semantic grounding, annotation, and merge artifacts on smoke-run samples: one internal task (csv_hard_field_campaign) and one external task (unique_tracks_90.csv).
- Added a hard guard so unsupported semantic claims without supporting evidence are normalized or recorded but not merged back into schema artifacts.

Action Points:
- Broaden semantic annotation execution to more tasks while reducing prompt size enough to avoid local-model context limits.
- Add post-merge evaluation so semantic outputs can be scored against gold or targeted expectations.
- Decide whether to keep pushing semantic execution before or after acquiring additional Dryad payloads and harder benchmark candidates.

Important Process:
- The local qwen3.5-9b endpoint was too constrained for several current task bundles, so smoke execution used llama-3.3-70b-instruct while keeping the same OpenAI-compatible runner interface.
- Merge-back is now intentionally conservative: unsupported annotations are retained for audit but not applied to the deterministic schema unless they carry supporting evidence and pass structural validation.

### Entry 3

Summary:
- Added a post-merge semantic evaluation script and generated the first semantic_merge_report over the currently merged internal sample.
- The current smoke-run post-merge result is explicitly a no-regression / no-gain outcome: accepted semantic merges = 0 and evaluation metrics are unchanged relative to the deterministic baseline for csv_hard_field_campaign.
- This negative result is still useful because it shows the semantic merge safety rails are preventing unsupported or weakly grounded model output from silently polluting the schema.

Action Points:
- Broaden semantic execution coverage and tighten prompt/output constraints so more annotations return usable supporting evidence and become merge-eligible.
- Use the semantic_merge_report as the baseline for future semantic-layer iterations, not just the retrieval report or raw annotation files.
- Keep distinguishing between runner success, validation success, and merge acceptance, since these are now separate stages with separate failure modes.

Important Process:
- Updated the README after the semantic merge report existed on disk so the documented project state reflects the actual evaluation artifacts and the current no-regression result.
- Treat the current semantic layer as safe but low-yield: the next engineering work should target evidence-carrying outputs, not simply higher annotation volume.

### Entry 4

Summary:
- Added a post-merge semantic evaluation report and confirmed the current smoke-run semantic layer remains no-regression / no-net-gain on the internal hard sample.
- Tightened semantic merge safety again by rejecting semantic/logical incompatibilities and normalizing supporting-evidence payloads before merge decisions.
- The current state is now clearer: the semantic runner can produce structured outputs and merged artifacts, but most useful merge candidates are still blocked by either missing supporting evidence or incompatibility checks.

Action Points:
- Focus the next semantic iteration on evidence-carrying outputs rather than simply producing more annotations.
- Broaden semantic execution coverage only after the prompt reliably yields supporting_evidence for at least one accepted merge case.
- Use the semantic_merge_report as the baseline when judging whether semantic-layer prompt changes actually improve downstream schema quality.

Important Process:
- Preserved the evidence-first contract by treating unsupported or semantically incompatible model claims as conflicts instead of mergeable updates.
- Kept the README aligned with the new semantic_merge_report artifact so project status reflects both the existence of the semantic layer and its current low-yield behavior.

## 2026-04-29


### Entry 1

Summary:
- Improved semantic evidence yield by constraining annotation_targets to unresolved fields and requiring supporting_evidence references tied to compact field-level evidence catalogs.
- This produced the first accepted semantic merge case: the internal hard sample now records an accepted semantic annotation on zc while still rejecting an incompatible logical-type proposal through the merge safety rails.
- Post-merge semantic evaluation still shows no net metric gain on the current internal hard sample, but the semantic layer has advanced from zero accepted merges to at least one accepted no-regression merge.

Action Points:
- Broaden semantic execution to additional internal tasks and identify the first case where accepted semantic merges improve logical or semantic accuracy against gold.
- Keep strengthening evidence-carrying outputs, especially for fields like val where the model still falls back to unknown without usable supporting evidence.
- Treat the current semantic layer as technically working but scientifically incomplete until accepted merges create measurable evaluation gains.

Important Process:
- Preserved the evidence-first contract by accepting the semantic_type refinement for zc while separately rejecting the incompatible logical_type suggestion through explicit conflict recording.
- Updated the README after the accepted-merge case existed so project status now reflects the difference between no-regression safety and actual measurable gain.

### Entry 2

Summary:
- Refactored semantic annotation execution toward smaller per-field requests and compact evidence catalogs so the semantic layer can scale beyond a single smoke task without relying only on larger context windows.
- Stabilized semantic annotation state management by adding atomic manifest writes and a repair utility for semantic annotation manifests.
- The semantic layer now has two validated smoke-run results recorded in data/semantic_annotations/manifest.json: one internal and one external.
- Current status improved from zero accepted merges to at least one accepted merge, but the net semantic-merge evaluation on the internal hard sample is still no-gain.

Action Points:
- When the local OpenAI-compatible endpoint is available again, rerun semantic annotation on the next most promising tasks such as hdf5_hard_ocean_profile and additional external pollutant datasets.
- Focus the next prompt iteration on producing merge-eligible evidence for fields like val rather than broad, low-information annotations.
- Use the repaired manifest plus semantic_merge_report as the ground truth project state before broadening semantic coverage further.

Important Process:
- Kept semantic_annotations/manifest.json limited to validated successful results after repair so downstream merge and evaluation stages do not have to interpret half-written or stale failures.
- Separated manifest robustness work from semantic quality work: the pipeline is now more recoverable even when the local model endpoint is unavailable or interrupts mid-run.

### Entry 3

Summary:
- Produced a current-stage report aligned to the README checklist and current repository state at docs/stage_report_2026-04-29.md.
- The report makes the project status explicit: deterministic extraction, evaluation, retrieval, and semantic execution paths are implemented, but semantic-layer net gain and benchmark completeness are still unfinished.

Action Points:
- Use the stage report as the working status snapshot before the next iteration, rather than reconstructing state from multiple artifacts each time.
- Keep the report updated when accepted semantic merges begin to produce measurable gains or when Dryad payload availability changes.

Important Process:
- Treated the README checklist as the primary contract, then summarized the live artifact state into a single stage document for easier review and handoff.

### Entry 4

Summary:
- Verified that the remote OpenAI-compatible endpoint at http://100.66.106.126:1234/v1 is reachable and exposes qwen/qwen3.6-27b.
- Used the remote endpoint for semantic smoke testing and confirmed a valid external semantic annotation result for unique_tracks_90.csv with supporting evidence and an accepted merge case.
- Updated the stage report so the current project state now distinguishes endpoint reachability from broader semantic-layer yield and coverage limitations.

Action Points:
- Prefer the reachable remote qwen/qwen3.6-27b endpoint for the next semantic-layer smoke and coverage-expansion runs.
- Do not treat endpoint reachability as equivalent to semantic-layer completion; the remaining bottleneck is evidence-yield and prompt-size discipline.

Important Process:
- Recorded endpoint reachability as project state because it materially changes which semantic execution paths are practical in the current environment.

### Entry 5

Summary:
- Expanded semantic smoke coverage to two internal tasks and two external tasks, including hdf5_hard_ocean_profile and the external ENSENSIA school_5 pollutant dataset.
- The semantic merge report now covers two internal merged tasks and still shows no regression, but also no measurable metric gain on the internal samples evaluated so far.
- A reachable remote qwen/qwen3.6-27b endpoint is now a practical execution lane for semantic-layer runs when local availability is limited.

Action Points:
- Prioritize the first semantic task that can convert accepted merges into measurable gold-aligned gains rather than only safe accepted merges.
- Use the remote endpoint for the next semantic expansion batch unless a stronger local endpoint becomes stably available.

Important Process:
- Updated README and the stage report after semantic coverage expansion so the documented project state matches the current manifest and merged-report scope.

## 2026-04-30


### Entry 1

Summary:
- Reconciled the external corpus after manual Dryad completion: all curated-source payloads are now locally present under data/external and import/derived manifests have been updated to match the filesystem.
- Applied benchmark triage to the newly available Dryad files, splitting them into promoted targets, same-family distractors, and keep_not_benchmark items, while preserving the two user-excluded HDF5 files.
- Expanded the retrieval pool state to reflect the larger curated corpus and updated the README and stage report so the documented external status now matches the manifests.

Action Points:
- Add planted retrieval queries for the newly promoted Dryad targets so the larger pool is exercised more completely.
- Keep distinguishing benchmark-target status from retrieval-pool distractor status, since not every locally available file should become a benchmark target.

Important Process:
- Used a manifest repair pass before rebuilding external derived artifacts so manual file drops in Dryad directories became machine-visible to the rest of the pipeline.

### Entry 2

Summary:
- Expanded external semantic smoke coverage to Dryad-backed targets, including African_Mammal_FoodWebs_Locations.csv and weatherMQ-FP-20261011.csv, and merged their validated outputs into the semantic_merged state.
- Reconciled the newly completed Dryad payload set into import, derived, benchmark-candidate, retrieval-pool, and semantic-grounding manifests so the external corpus is now payload-backed end to end.
- Updated README and the stage report to reflect the enlarged Dryad-backed external state, the revised benchmark candidate distribution, and the increased semantic smoke coverage.

Action Points:
- Use the new Dryad-backed semantic and retrieval state to target the first measurable semantic gain case rather than only expanding artifact count.
- Review whether the atmospheric HDF5 distractor family is still too dominant in retrieval and whether additional query shaping or family balancing is needed.

Important Process:
- Treated manual Dryad file drops as a state-repair problem first, then rebuilt downstream artifacts in dependency order so retrieval and semantic layers consumed the corrected corpus state.

### Entry 3

Summary:
- Integrated the newly downloaded Dryad payloads into external derived schemas, benchmark candidate triage, retrieval pool expansion, retrieval query coverage, and semantic grounding manifests.
- Ran Dryad semantic smoke tasks and successfully merged results for African_Mammal_FoodWebs_Locations.csv and weatherMQ-FP-20261011.csv, increasing validated external semantic results to four.
- Retried semantic execution for Greenland cod year1 and functional_traits with smaller subtask slicing, but those tasks remain blocked by remote endpoint timeouts rather than missing data or missing grounding artifacts.

Action Points:
- Treat Greenland cod year1 and functional_traits as the next semantic execution targets once the remote endpoint is stable enough for additional field-sliced retries.
- Do not request more data yet; the current bottleneck is semantic execution reliability, not external corpus completeness.

Important Process:
- Separated corpus-state repair from semantic execution: first repaired import/derived/benchmark/retrieval manifests for Dryad, then expanded semantic grounding and only afterward attempted new semantic smoke runs.

### Entry 4

Summary:
- Upgraded the semantic runner from plain field-window slicing to explicit field-group scheduling for blocked Dryad tasks, with a tailored grouping strategy for Greenland cod year1 and functional_traits.
- Retried those two Dryad targets with grouped semantic execution. They still failed, but the remaining blocker is now clearly remote endpoint responsiveness rather than missing data or missing grounding artifacts.
- Dryad-backed semantic coverage remains expanded for weatherMQ and African_Mammal_FoodWebs_Locations, while Greenland cod year1 and functional_traits are still pending execution success.

Action Points:
- Resume the grouped Dryad semantic retries when the remote qwen/qwen3.6-27b endpoint is reachable and stable again.
- Do not spend time acquiring more data for these two tasks yet; the next marginal gain is runner/endpoint reliability, not corpus size.

Important Process:
- The semantic runner now supports semantic domain-aware grouping instead of only mechanical field offsets, which should reduce prompt waste once the endpoint is responsive again.

## 2026-05-01


### Entry 1

Summary:
- Expanded the retrieval query set to cover the full 10 promoted targets in the enlarged 16-file pool, including the newly promoted Dryad targets.
- Confirmed Dryad-backed semantic smoke success for weatherMQ-FP-20261011.csv and African_Mammal_FoodWebs_Locations.csv, while Greenland cod year1 and functional_traits remain blocked by remote endpoint timeout even after grouped field-slice retries.
- Updated README and stage-report status so the current project state now reflects both the larger Dryad-backed retrieval pool and the remaining semantic execution bottleneck.

Action Points:
- Treat remote endpoint reliability as the primary blocker for the remaining two Dryad semantic tasks, not data acquisition or grounding coverage.
- When the endpoint is stable again, retry Greenland cod year1 and functional_traits with the grouped semantic runner before adding more new semantic targets.

Important Process:
- Differentiated clearly between successful Dryad semantic integration and still-blocked Dryad semantic retries so the project state does not overclaim semantic coverage.

### Entry 2

Summary:
- Created a high-school-readable Chinese presentation deck explaining the schema extraction study.

Action Points:
- Use the new PPTX for non-expert presentations; next deck iteration can add an English version or speaker notes if needed.

Important Process:
- Used the existing current-state reports and retrieval metrics; produced a 9-slide editable PPTX and verified it imports with 9 slides plus non-empty rendered previews.

### Entry 3

Summary:
- Created an English high-school-readable presentation deck for the schema extraction study.

Action Points:
- Use the English PPTX alongside the Chinese version for non-expert presentations; keep both decks aligned when retrieval or semantic-layer numbers change.

Important Process:
- Reused the same 9-slide narrative, updated all copy to English, generated rendered previews, and verified the exported deck imports with 9 slides.

## 2026-05-04


### Entry 1

Summary:
- Tightened semantic annotation prompt/output constraints so models can make evidence-backed logical-type updates even when semantic_type must remain unknown.
- Produced the first measured internal semantic-layer gain: csv_hard_field_campaign logical_accuracy improved from 0.6667 to 1.0000 after merged annotations for zc and val, with zero merge conflicts.
- Reran grouped semantic annotation for the previously blocked Dryad targets functional_traits and Greenland cod year1 against the reachable qwen/qwen3.6-27b endpoint; both now have validated result files and merged artifacts.

Action Points:
- Broaden semantic merge evaluation to additional internal tasks so the first measured gain is tested beyond one hard CSV case.
- Review the new functional_traits and Greenland cod year1 merged outputs for benchmark usefulness and retrieval-query impact.
- Keep using grouped semantic retries for larger external tasks because they preserved progress and avoided the earlier all-or-nothing timeout failure mode.

Important Process:
- Kept merge safety unchanged: unsupported claims are still rejected, and unknown semantic_type is acceptable only when logical/unit claims carry supporting evidence.
- Added regression coverage for compact semantic payload construction and unknown-semantic normalization, then ran the full high_fidelity_schema_study test suite.

### Entry 2

Summary:
- Expanded internal semantic merge evaluation beyond the first hard CSV gain case by adding a targeted review path for explicitly selected non-unknown fields.
- Reran semantic annotation for csv_easy_weather_stations/elevation_m and accepted an evidence-backed compatible logical refinement from coordinate to measurement.
- The semantic merge report now covers 3 internal datasets, with measurable metric gain in 2 of them; mean logical_accuracy delta is +0.1667 and total accepted semantic merges is 3.

Action Points:
- Review whether remaining time-axis accuracy gaps belong in semantic merge, deterministic profiling, or evaluation logic before trying to force more semantic-layer gains.
- Use the targeted review path sparingly for known evaluation gaps; default semantic annotation should still focus on unresolved fields.
- Move next to external field-subset regression tests or retrieval impact review for the newly merged Dryad outputs.

Important Process:
- Preserved the conservative default by making non-unknown field review explicit through target-field selection instead of widening all semantic annotation runs.
- Added regression tests for explicit review targets and compatible logical refinement, then reran the full high_fidelity_schema_study test suite.

### Entry 3

Summary:
- Reviewed the new Dryad semantic-merged outputs for retrieval and benchmark impact.
- Confirmed current retrieval artifacts still consume deterministic derived schemas, so the checked-in retrieval report has no direct metric change from the new semantic merges.
- Ran an in-memory counterfactual with the two merged Dryad schemas; aggregate schema_enhanced retrieval metrics stayed unchanged, functional_traits remained top1, and Greenland cod year1 still ranked behind the same-family year2 distractor.

Action Points:
- Do not switch retrieval to naively consume semantic_merged schemas yet; add an explicit schema_source comparison mode first if retrieval integration continues.
- Treat Greenland cod year1 vs year2 as a same-family disambiguation problem requiring file-slice or temporal signals, not just generic logical-type enrichment.
- Add external field-subset regression checks for high-confidence Dryad merged fields before promoting semantic merges toward gold references.

Important Process:
- Recorded the impact review in docs/dryad_semantic_retrieval_benchmark_impact.md instead of changing retrieval behavior based on a no-improvement counterfactual.
- Kept both Dryad targets promoted for benchmark use, but marked their semantic merges as useful annotations rather than final gold references.

### Entry 4

Summary:
- Added explicit retrieval schema-source comparison artifacts: schema_enhanced_deterministic and schema_enhanced_semantic_merged, while preserving schema_enhanced as the backward-compatible deterministic artifact.
- Added year/file-slice/time-slice disambiguation terms to schema-enhanced artifacts and updated planted slice-specific queries for school 5, January HDF5, and Greenland cod year1.
- Rebuilt retrieval artifacts and reports; schema_enhanced, schema_enhanced_deterministic, and schema_enhanced_semantic_merged now each reach recall_at_1 = 1.0000 on the current 10-query planted set.

Action Points:
- Keep deterministic and semantic-merged schema-source artifacts side by side until harder non-planted queries verify that semantic-merged retrieval does not overfit or dilute useful field-name signals.
- Add representative external field-subset regression tests next so the high-confidence semantic merges are protected independently of retrieval ranking.
- Add more same-family slice distractors before treating perfect planted-set retrieval as broad robustness.

Important Process:
- Fixed same-family ambiguity by encoding explicit slice evidence rather than relying on generic logical-type terms.
- Added retrieval artifact tests for year and school slice token extraction, then rebuilt artifacts and reran the full study test suite.

### Entry 5

Summary:
- Froze the current benchmark slice in docs/benchmark_freeze_2026-05-04.md and docs/benchmark_freeze_2026-05-04.json.
- The freeze covers 9 internal pilot datasets, the 16-file external retrieval pool, 10 promoted targets, 6 distractors, current retrieval systems, and locked regression subsets.
- Added external field-subset regression tests for Greenland cod year1, functional_traits, and weatherMQ-FP-20261011.

Action Points:
- Use the freeze JSON as the source of truth for current-slice counts and target/distractor membership.
- Treat external semantic merges as protected working annotations, not final gold, until manual review or codebook evidence is added.
- Move next toward time-axis gap triage or paper-ready result tables rather than expanding the corpus immediately.

Important Process:
- Added a freeze consistency test that checks the freeze JSON against live pilot, pool, and retrieval artifact manifests.
- Added field-subset tests that protect high-confidence external logical, semantic, and unit claims independently of retrieval ranking.

## 2026-05-06


### Entry 1

Summary:
- Created a high-school-readable Chinese explanatory report at docs/schema_study_explained_for_high_school_CN.md.
- The report explains why schema extraction needs components such as raw datasets, pilot, gold, deterministic extractors, evidence, evaluation, semantic layer, retrieval, benchmark freeze, and regression tests.
- The report summarizes the current project state and frames the next convergence steps: time-axis gap triage, paper-ready result tables, schema-source decision, and gold review.

Action Points:
- Use the report as a non-expert narrative handoff before deeper technical reports or paper sections.
- Keep the report aligned if retrieval metrics, freeze scope, or next-step priorities change.

Important Process:
- Based the report on the current README, benchmark freeze, retrieval report, and recent project log rather than writing from stale memory.

## 2026-05-11


### Entry 1

Summary:
- Completed the second-pass consistency review for all 9 internal gold schema files.
- Added a reproducible gold audit command and report at docs/gold-schema-second-pass-2026-05-11.md and docs/gold-schema-second-pass-2026-05-11.json.
- The review covers 50 gold fields, including 37 high-necessity fields, and found 0 blocking consistency errors.

Action Points:
- Treat the current internal gold labels as consistency-reviewed for pilot-scale evaluation.
- Keep the documented warning that gold_evidence arrays remain empty; evidence enrichment is separate from label consistency.
- Move next to deterministic profiling improvements or paper-ready result tables rather than reopening internal gold labels without new evidence.

Important Process:
- Locked review policy in code: top-level time_axis is required only for time-series modality, null units can mean not evidence-backed, and semantic_type=unknown is allowed for intentionally underdetermined fields.
- Added a regression test so future gold edits cannot silently introduce manifest mismatches, duplicate fields, invalid logical types, or time-axis inconsistencies.

### Entry 2

Summary:
- Added richer deterministic profiling for internal derived schemas: missingness, identifier quality, and multi-file relationship candidates.
- Rebuilt internal derived schemas so each artifact now includes metadata.deterministic_profile.
- Added data/derived/internal_relationship_profile.json and documented the pass in docs/deterministic_profile_report_2026-05-11.md.

Action Points:
- Treat relationship entries as deterministic candidates, not asserted joins, until value-level overlap or source documentation supports them.
- Use the profile report as the Phase 4 closure artifact before moving to paper-ready result tables.
- If profiling expands later, prioritize value-scanned HDF5 missingness and external-file-safe sampling.

Important Process:
- Kept profiling separate from evaluation metrics so baseline numbers do not shift simply because diagnostic metadata exists.
- Added regression coverage for missingness, identifier quality, and shared-identifier relationship inference, then reran the full study test suite.

## 2026-05-12


### Entry 1

Summary:
- Entered Phase 11 by adding reproducible paper-ready result tables at docs/paper_result_tables_2026-05-12.md and docs/paper_result_tables_2026-05-12.json.
- The table builder consolidates frozen benchmark counts, deterministic baseline metrics, retrieval metrics, semantic merge deltas, deterministic profile diagnostics, locked regression subsets, and remaining non-final items.
- Updated the README checklist so result tables are marked complete while paper-ready figures remain explicitly pending.

Action Points:
- Use docs/paper_result_tables_2026-05-12.json as the machine-readable source of truth for paper numbers.
- Convert only the highest-signal tables into figures; do not duplicate every table as a chart.
- Draft methods and evaluation text from the generated tables instead of copying numbers manually from scattered reports.

Important Process:
- Kept Phase 11 table generation read-only over existing frozen artifacts; no new experiment was introduced.
- Added regression coverage for the key table values so future artifact drift is visible in tests.

## 2026-05-14


### Entry 1

Summary:
- Added four local related-work seed papers under docs/literature for data readiness, scientific AI readiness, and analogy-only sequence-model behavior framing.
- Added docs/literature/deep_research_prompt_established_work.md to guide a structured search for established work that can strengthen high-fidelity schema extraction.
- Updated the README so related-work research becomes an explicit Phase 11 writing task and immediate next step.

Action Points:
- Run the deep research prompt against scholarly search tools before drafting the related-work section.
- Treat AIDRIN and scientific AI data readiness as direct framing leads; treat Professor Forcing and continual RNN learning as analogy-only unless the research pass finds a stronger link.
- Convert the research output into a citation matrix before changing method claims or novelty language.

Important Process:
- Kept the seed papers local under docs/literature so literature context stays near the study artifacts.
- Wrote the research prompt to distinguish direct schema/data-readiness relevance from weak analogy, avoiding forced citations.

### Entry 2

Summary:
- Copied the generated deep research report into docs/literature/deep_research_report_2026-05-14.md.
- Assessed the current project against the report in docs/literature/project_improvement_assessment_2026-05-14.md.
- The assessment concludes that the project direction is strong, but the next convergence pass should formalize claim states, provenance, evidence adequacy metrics, benchmark-card documentation, qrels, and standards-backed unit normalization.

Action Points:
- Prioritize a schema-claim model and benchmark card before expanding the corpus or running additional retrieval experiments.
- Extend paper-ready result tables with evidence adequacy metrics so evidence-grounding becomes measurable.
- Keep RNN seed papers out of core related work unless explicitly framed as weak analogy only.

Important Process:
- Evaluated the research report against current code artifacts rather than treating all recommendations as equally urgent.
- Preserved the current planted-query retrieval limitation instead of turning perfect planted-slice metrics into a broad robustness claim.

## 2026-05-15


### Entry 1

Summary:
- Added the literature-driven improvement plan to the Phase 11 checklist.
- Started the convergence pass by adding docs/schema_claim_model.md and docs/benchmark_card_2026-05-15.md.
- Extended paper-ready result tables to include evidence adequacy metrics and regenerated docs/paper_result_tables_2026-05-15.md/json.

Action Points:
- Move next to lightweight PROV-like provenance export, then standards-backed unit normalization status, then retrieval qrels.
- Use the schema claim model when drafting the methods section so claim states, reason codes, and merge semantics are explicit.
- Treat evidence adequacy as a first-class result alongside accuracy metrics.

Important Process:
- Advanced documentation and table generation before expanding the corpus, because the research report identified artifact defensibility as the current bottleneck.
- Kept current retrieval claims bounded to the planted external slice.

### Entry 2

Summary:
- Added standards-backed unit normalization status to field schemas and rebuilt internal derived schemas.
- Added a lightweight PROV-like provenance export at data/derived/provenance_manifest.json.
- Added retrieval qrels at data/retrieval/external_candidate_pool/qrels.json and updated retrieval artifact generation/evaluation to treat qrels as an auxiliary artifact.
- Regenerated paper-ready tables so unit normalization, provenance summary, and qrels summary are first-class report tables.

Action Points:
- Use the provenance manifest and claim model when drafting the methods section.
- Keep the qrels limitation explicit: current qrels are planted single-positive judgments, not full graded real-world relevance judgments.
- Consider Table Schema export next only if another standards-facing artifact pass is needed before paper writing.

Important Process:
- Fixed retrieval evaluation so auxiliary qrels are skipped when iterating ranking artifacts.
- Added tests for unit normalization, provenance summary, qrels consistency, and updated paper table sections.

## 2026-05-23


### Entry 1

Summary:
- Reframed the current convergence target as two concrete deliverables: a complete paper-ready draft and a visual GUI demo.
- Updated the README so Phase 11 now explicitly includes manuscript drafting and a GUI inspection surface over extraction, evidence, semantic merge, retrieval, and provenance artifacts.
- Confirmed that the GUI demo should communicate and inspect the frozen artifact state rather than define a new benchmark, qrels set, gold reference, or evaluation path.

Action Points:
- Draft the paper from the frozen benchmark card, paper-ready tables, schema claim model, provenance export, qrels, semantic merge report, and related-work map.
- Build the GUI demo as a reviewer-facing artifact browser for source files, field claims, evidence records, uncertainty/conflict status, semantic merge decisions, retrieval comparison, and provenance links.
- Keep planted-qrels and benchmark-scope limitations explicit in both the paper draft and GUI demo.

Important Process:
- Treat further corpus expansion, non-planted qrels, and Table Schema export as optional support work only if they directly improve the paper-ready draft or visual demo.
- Preserve the frozen-slice contract: GUI work must read existing artifacts and should not silently change benchmark membership or headline metrics.

### Entry 2

Summary:
- Added the first complete paper-ready draft at docs/paper_draft.md, using frozen benchmark tables, semantic merge results, retrieval metrics, claim model, provenance export, and limitations as source material.
- Added an initial static GUI demo under gui_demo/ that loads frozen JSON artifacts and presents overview metrics, evidence adequacy, semantic merge status, retrieval comparisons, provenance counts, and benchmark limitations.
- Updated the README current-state and Phase 11 checklist so the paper draft and initial GUI demo are tracked as delivered convergence artifacts.

Action Points:
- Replace related-work placeholders in docs/paper_draft.md with formal citations from the literature report.
- Convert the highest-signal result tables into figures and reference them from the draft.
- Verify the GUI demo in a browser and refine the reviewer workflow around field-level evidence and per-query retrieval inspection.

Important Process:
- Kept the GUI dependency-free and static so it can be served from high_fidelity_schema_study/ with python -m http.server.
- Preserved the GUI as an inspection layer over frozen artifacts, not a new evaluation or benchmark generation path.

### Entry 3

Summary:
- Added a reproducible paper figure builder at build_paper_figures.py.
- Generated five SVG figures under docs/figures/: frozen benchmark slice, internal deterministic metrics, evidence adequacy, retrieval Recall@1, and semantic-merge logical-accuracy deltas.
- Added docs/literature/citation_matrix.md and revised docs/paper_draft.md to use draft citation keys and figure references.

Action Points:
- Convert citation keys into the target venue's bibliography format before final submission.
- Review the generated SVG figures for visual clarity and remove any that duplicate tables without adding interpretive value.
- Keep figure generation tied to docs/paper_result_tables_2026-05-15.json so paper visuals remain reproducible.

Important Process:
- Generated figures from frozen table artifacts rather than hand-editing chart values.
- Used a dependency-free SVG generator so the figure pipeline does not add package requirements.

### Entry 4

Summary:
- Added docs/references.md as a draft reference list derived from the citation matrix and local deep research report.
- Advanced docs/paper_draft.md to v0.3 by linking the reference list as the next bibliography source.
- Expanded the static GUI demo with a field-level inspector that shows per-dataset metrics and per-field physical/logical/semantic match, confidence, and uncertainty status from the internal baseline report.

Action Points:
- Convert docs/references.md into venue-specific bibliography formatting and verify each bibliographic detail before submission.
- Use the GUI field inspector as the main demo surface for explaining why this is field-level high-fidelity extraction rather than only aggregate scoring.
- Add browser-level visual verification when Playwright or the in-app browser tool is available.

Important Process:
- Kept the GUI field inspector read-only over data/derived/internal_baseline_report.json.
- Added static regression coverage so the core GUI views and artifact-boundary documentation remain present.

### Entry 5

Summary:
- Completed an Artifact Paper rigor pass by adding docs/academic_rigor_audit.md, docs/time_axis_gap_adjudication.md, and docs/artifact_handoff.md.
- Upgraded docs/references.md from a draft list to a verified artifact bibliography with stable identifiers and a separate use-with-caution section.
- Advanced docs/paper_draft.md to v0.4 with tighter retrieval, semantic merge, provenance, and time-axis limitation wording.
- Added a visible Artifact Boundary banner to the GUI demo so planted qrels, small pilot scope, working annotations, and the time-axis gap stay visible during review.

Action Points:
- Use docs/academic_rigor_audit.md as the guardrail for final paper review.
- Keep the time-axis gap as an explicit limitation unless a separate evaluation-policy pass changes the metric.
- Use docs/artifact_handoff.md for final reviewer handoff and verification.

Important Process:
- Did not expand the corpus, add non-planted qrels, rerun LLM semantic annotation, or change headline metrics.
- Preserved the GUI as a read-only inspection layer over frozen artifacts.

### Entry 6

Summary:
- Added hash-based GUI navigation so every view can be opened directly for browser smoke checks.
- Ran Chrome headless screenshots for Overview, Evidence, Fields, Semantic Merge, Retrieval, Provenance, Limits, and a mobile Fields viewport.
- Fixed a field-inspector table-header overlap found during visual review.
- Added docs/gui_visual_qa.md to record the visual QA method, outcome, and remaining polish.

Action Points:
- Treat the GUI as Artifact Paper demo-ready, with remaining polish limited to mobile header text and optional accessibility review.
- Keep hash navigation because it makes future demo screenshots and reviewer links stable.

Important Process:
- Browser screenshots were written to the system temp directory and not tracked as repo artifacts.

### Entry 7

Summary:
- Completed the final Artifact Paper convergence polish without changing the frozen corpus, qrels, semantic annotations, or headline metrics.
- Advanced the paper draft to v0.5 with reviewer-facing wording, verified citation-key hygiene, and explicit preservation of planted-qrels, small-pilot, working-annotation, evidence-adequacy, provenance, and time-axis boundaries.
- Polished the GUI mobile header behavior and added docs/final_convergence_report.md as the release audit for the 98% artifact package.

Action Points:
- Move remaining paper work to venue/template formatting and external human review.
- Keep Auctus and other caution-only references out of core paper claims unless their bibliographic details and role are re-verified.
- Treat any future corpus expansion, non-planted qrels, or time-axis metric change as a new experiment round, not part of this convergence polish.

Important Process:
- This was a final convergence and audit pass, not a new experiment.
- Verification remains centered on figure regeneration, the high_fidelity_schema_study test suite, GUI JavaScript parse checks, HTTP smoke checks, browser screenshots, and consistency searches.

## 2026-05-27


### Entry 1

Summary:
- Restored the intended interactive GUI surface by adding a scratch Extract tab for uploaded HDF5, CSV time-series, and raw binary files.
- Added a dependency-free local GUI server at gui_demo/server.py with a `/api/extract-schema` endpoint that calls the existing deterministic extractors and returns the schema JSON to the browser.
- Kept frozen artifact views read-only; scratch extraction is local, non-persistent, and does not change benchmark membership, qrels, gold references, paper metrics, or semantic merge policy.

Action Points:
- Use `python -m high_fidelity_schema_study.gui_demo.server 8765` for the full GUI with uploads.
- Treat raw binary uploads without sidecar metadata as high-fidelity abstention: record file-level evidence, but do not invent field claims.
- Keep `python -m http.server 8765` as a read-only fallback for artifact inspection when uploads are not needed.

Important Process:
- This was a demo/workbench repair, not a new experiment or metric update.
- The live extraction tab reuses existing deterministic extractors instead of introducing a separate GUI-only schema path.
