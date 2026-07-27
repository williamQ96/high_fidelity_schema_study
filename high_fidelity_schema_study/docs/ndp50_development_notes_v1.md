# NDP-50 development checkpoint and protocol amendment

Date: 2026-07-26

This is a historical development-only record. It documents observations and general fixes
made after inspecting the 15-case development split. It does not report
validation/test performance and does not alter the frozen Artifact Paper.
The later structural result is reported separately in
`docs/ndp50_structural_validation_report_v1.md`.

## Frozen corpus state

- NDP catalog count: 5,823 dataset records across 75 organizations.
- Candidate-frame SHA-256:
  `96dd37f89cbc34a5deb219acb636a8b643ba141bf07f62f70508fd090d91822f`.
- Deterministic selection: 50 datasets plus 17 ordered reserves.
- Split: 15 development, 10 validation, 25 test.
- The executed development IDs exactly match the frozen development split.
- Validation and test details have not been fetched or executed.

The initial proposal to take a random detailed CKAN sample was rejected before
freezing the 50: 110/120 records came from one organization and the sample
expanded to 25,783 resources. The implemented frame uses the complete
lightweight catalog, format strata, and an organization cap.

## Development results

The 15 development datasets exposed 37 catalog resources. The frozen bounded
policy attempted 13. Ten data payloads were acquired and all ten completed
deterministic extraction. This conditional 100% must not be reported alone:

- dataset end-to-end coverage: 7/15 (46.7%);
- catalog-resource end-to-end coverage: 10/37 (27.0%);
- acquisition success conditional on an attempt: 10/13 (76.9%);
- extraction success conditional on acquired data: 10/10 (100%).

The reproducible summary and resource-level failure ledger are under
`data/experiments/ndp50_v1/reports/development_v4/`.

## Oversights found and resolved

1. **Catalog pagination wording.** The protocol incorrectly required one response
   for the complete frame. NDP requires six contiguous pages at the current
   count. The protocol now requires individually hashed contiguous pages whose
   combined unique IDs exactly equal the catalog count.
2. **Repeated temporal coordinates.** A spatial prediction CSV repeats one
   timestamp across many observations. The cadence profiler treated the dominant
   zero-second delta as a divisor. The general fix now abstains from cadence and
   missing-interval claims when the dominant delta is zero; a regression test
   covers this case.
3. **HTTP success is not payload success.** Two ArcGIS downloads returned HTTP
   200 JSON control documents with `Pending`/`ExportingData` status. The
   acquisition gate now recognizes bounded provider status/error payloads and
   prevents them from being extracted as datasets.
4. **Rerun contamination.** Prior downloaded payloads and derived schemas could
   survive a later failed attempt. Each attempted resource now clears only its
   exact generated destination and schema before reacquisition.
5. **Misleading denominator.** A conditional parser success rate hides catalog
   compatibility loss. The report builder separately freezes dataset,
   catalog-resource, attempted-resource, and acquired-payload denominators.
6. **Mutable external payloads.** ArcGIS resources changed between status
   documents and generated files during development. Reports therefore retain
   retrieval time, final URL, byte count, content type, and SHA-256. Raw payloads
   are reproducible external data and are excluded from version control.
7. **CSV field identity.** Semantic-packet construction found a development CSV
   with a blank first header. The CSV extractor now assigns stable unique paths
   to blank and duplicate headers while preserving raw header text and column
   index as evidence. Controlled tests cover blank, duplicate, and row-value
   alignment, and development was rebuilt before the current opportunity
   manifest.

## Remaining capability debt before validation

- Twenty-one development resources use formats without a registered file
  extractor under the current policy, including geospatial/image, archive, and
  documentation-oriented resources.
- Two remote Zarr resources cannot be processed because their catalog metadata
  does not uniquely locate a store with discoverable Zarr markers.
- External resource state is mutable: across development captures, one or two
  resources exceeded the 25 MiB limit while an ArcGIS export could remain
  pending after the frozen retry limit.
- One eligible resource was excluded by the stable three-resource-per-dataset
  cap.
- Five successful extractions emitted `sampling_insufficient`; this is an
  explicit bounded-evidence warning, not parser failure.
- Provider export polling is frozen at three attempts with a fixed 10-second
  interval; all responses and transferred bytes remain recorded.
- The current run has no independent semantic gold, so it supports compatibility
  and capability discovery only, not semantic accuracy claims.

Any new transport, archive, or format support must be implemented from
development evidence, covered by general regression fixtures, and frozen before
validation. Validation may accept or reject a general change but may not motivate
dataset-specific rules.

## Incorporation of Korini and Bizer

The column-property-annotation paper
[Column Property Annotation using Large Language Models](https://dl.acm.org/doi/10.1007/978-3-031-78952-6_6)
is incorporated as a bounded tabular sub-study, not as a substitute for general
schema extraction.

The study adopts its useful experimental dimensions: zero-shot versus one/five
shot prompting, similarity-selected examples, prompt formulation sensitivity,
row-sampling sensitivity, explicit target vocabulary, per-label and macro/micro
metrics, and out-of-vocabulary handling. It adds controls needed here:
development-only demonstration selection, frozen subject-column applicability,
byte-identical B/C semantic-response replay, evidence validity, unsupported-claim
rates, selective risk, and dataset-level analysis.

CPA is evaluated only when a relational target and subject column are
well-defined. Hierarchical, array, geospatial, documentation, and file-level
schema questions remain outside the CPA denominator. Fine-tuning is optional and
cannot use validation/test cases.

## Freeze-boundary correction

A post-validation audit found that the live preflight helper's implementation
path list had been expanded to include later semantic-preparation modules.
Those modules did not participate in structural acquisition or extraction and
were not part of the 19-file implementation manifest recorded in the valid
structural freeze. Keeping them in the live list would make an unrelated
semantic edit appear to alter the historical structural execution boundary.

The implementation list is therefore scoped again to the structural runner,
reporting, preflight, models, temporal logic, unified schema, and registered
extractors. Semantic and CPA workflows bind their own implementation hashes.
The historical freeze and passed preflight report were not regenerated or
rewritten; this correction changes only the live boundary definition and is
covered by a regression test.
