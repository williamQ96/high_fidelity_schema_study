# NDP-50 development checkpoint

This report is a development-only engineering checkpoint. Validation and test
splits remain unopened, and these rates are not external accuracy estimates.

## Frozen-split integrity

- Development datasets: 15 (exact selection-ID match)
- Validation/test datasets executed: no

## End-to-end coverage

- Dataset level: 7/15 (46.7%)
- Catalog-resource level: 10/37 (27.0%)
- Acquisition conditional on a policy attempt: 76.9%
- Extraction success conditional on an acquired data payload: 100.0%

## Capability and acquisition ledger

- `content_length_exceeds_frozen_limit`: 1
- `provider_control_response`: 2
- `skip_dataset_resource_cap`: 1
- `skip_remote_directory_store`: 2
- `skip_unsupported_format`: 21

## Interpretation

The conditional extraction rate must not be reported alone: most coverage loss
occurs before extraction through unsupported formats, remote directory stores,
resource caps, or byte limits. The dataset- and catalog-resource denominators
above are the primary engineering coverage measures.
