# NDP-50 development structural checkpoint

This report measures structural acquisition/extraction coverage. It is not
a semantic accuracy estimate and must not be merged with controlled fixtures.

## Frozen-split integrity

- Development datasets: 15 (exact frozen selection-ID match)

## End-to-end coverage

- Dataset level: 7/15 (46.7%)
- Dataset bootstrap 95% interval: 20.0% to 73.3%
- Catalog-resource level: 10/37 (27.0%)
- Acquisition conditional on a policy attempt: 76.9%
- Extraction success conditional on an acquired data payload: 100.0%
- Macro mean of per-dataset resource coverage: 35.6%

## Resource-count skew

- Min / median / max resources per dataset: 1 / 1 / 9
- Largest dataset share of all catalog resources: 24.3%

## Capability and acquisition ledger

- `content_length_exceeds_frozen_limit`: 2
- `provider_control_response`: 1
- `skip_dataset_resource_cap`: 1
- `skip_remote_store_locator_incomplete`: 2
- `skip_unsupported_format`: 21

## Dataset outcome classes

- `attempted_but_not_acquired`: 1
- `no_policy_attempt`: 7
- `schema_extracted`: 7

## Selection-stratum results

- `archive`: 1/2 datasets with schema; 3/11 resources
- `documentation_or_text`: 0/1 datasets with schema; 0/1 resources
- `geospatial_or_image`: 0/2 datasets with schema; 0/6 resources
- `other_or_unknown`: 0/2 datasets with schema; 0/7 resources
- `supported_hierarchical`: 0/2 datasets with schema; 0/2 resources
- `supported_semistructured`: 3/3 datasets with schema; 3/4 resources
- `supported_tabular`: 3/3 datasets with schema; 4/6 resources

## Interpretation

The conditional extraction rate must not be reported alone: most coverage loss
occurs before extraction through unsupported formats, remote directory stores,
resource caps, or byte limits. The dataset- and catalog-resource denominators
above are the primary engineering coverage measures.
