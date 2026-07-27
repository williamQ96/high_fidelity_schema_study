# NDP-50 validation structural checkpoint

This report measures structural acquisition/extraction coverage. It is not
a semantic accuracy estimate and must not be merged with controlled fixtures.

## Frozen-split integrity

- Validation datasets: 10 (exact frozen selection-ID match)

## End-to-end coverage

- Dataset level: 5/10 (50.0%)
- Dataset bootstrap 95% interval: 20.0% to 80.0%
- Catalog-resource level: 6/5054 (0.1%)
- Acquisition conditional on a policy attempt: 70.0%
- Extraction success conditional on an acquired data payload: 85.7%
- Macro mean of per-dataset resource coverage: 44.0%

## Resource-count skew

- Min / median / max resources per dataset: 1 / 2 / 4933
- Largest dataset share of all catalog resources: 97.6%

## Capability and acquisition ledger

- `content_length_exceeds_frozen_limit`: 3
- `skip_remote_store_locator_incomplete`: 1
- `skip_unsupported_format`: 5043
- `unknown_no_signature`: 1

## Dataset outcome classes

- `attempted_but_not_acquired`: 2
- `no_policy_attempt`: 3
- `schema_extracted`: 5

## Selection-stratum results

- `archive`: 1/1 datasets with schema; 2/5 resources
- `documentation_or_text`: 0/1 datasets with schema; 0/3 resources
- `geospatial_or_image`: 0/2 datasets with schema; 0/5035 resources
- `other_or_unknown`: 0/1 datasets with schema; 0/6 resources
- `supported_hierarchical`: 0/1 datasets with schema; 0/1 resources
- `supported_semistructured`: 2/2 datasets with schema; 2/2 resources
- `supported_tabular`: 2/2 datasets with schema; 2/2 resources

## Interpretation

The conditional extraction rate must not be reported alone: most coverage loss
occurs before extraction through unsupported formats, remote directory stores,
resource caps, or byte limits. The dataset- and catalog-resource denominators
above are the primary engineering coverage measures.
