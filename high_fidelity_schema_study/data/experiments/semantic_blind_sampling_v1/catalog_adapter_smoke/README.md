# Catalog adapter infrastructure smoke

Status: passed; infrastructure evidence only

On 2026-07-16 UTC, the fixed `zenodo_dryad_catalog_snapshot/v1` adapter captured
and replayed one two-record page from each official repository API:

- Zenodo: two dataset records expanded to three file resources;
- Dryad: two dataset records, including their version/files responses, expanded
  to four file resources.

The live responses exercised file identity, dataset grouping, URL, size, provider
checksum, license, scientific-family metadata, and suffix-based format
normalization. The observed supported-resource count was zero for this Zenodo page
and one CSV for this Dryad page. That observation is not an architecture result
and must not be used to tune a query after inspecting A/B/C/D outputs.

These snapshots are not the blind candidate frame, not a sampling-design
registration, not gold, and not evidence of corpus representativeness. Their only
purpose is to demonstrate that the frozen adapter matches the live API contracts.
