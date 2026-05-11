# Pilot Corpus Plan

Start small and interpretable.

## 3 x 3 Pilot Matrix

| Modality | Easy | Medium | Hard |
| --- | --- | --- | --- |
| CSV | clean headers and explicit units | partial metadata and mixed types | ambiguous identifiers and overloaded strings |
| HDF5 | clear hierarchy and useful attributes | partial attributes and nested groups | sparse metadata and repeated structural patterns |
| Time-series | regular timestamps and clear measurements | mild missingness and multiple entities | irregular cadence, timezone ambiguity, mixed measurement names |

## Selection Criteria

- open-access scientific datasets
- at least one intentionally planted relevant retrieval match per query set
- enough documentation to create a human reference schema
- heterogeneity in metadata quality

## Gold Annotation Requirements

Each dataset should have a compact human reference schema with:

- physical type
- logical type
- semantic type
- unit
- necessity level
- gold evidence location when available

## Retrieval Query Shape

Seed the pilot with queries such as:

- find hourly temperature readings from weather stations
- find HDF5 data containing pressure and velocity measurements
- find time-series data with missing intervals and sensor identifiers
- find CSV data with latitude, longitude, and precipitation in millimeters
