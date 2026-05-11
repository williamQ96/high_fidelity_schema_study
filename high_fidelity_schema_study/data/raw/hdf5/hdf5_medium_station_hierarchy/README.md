# hdf5_medium_station_hierarchy

Nested per-station hierarchy with partial metadata.

- `/weather/timestamp` is the shared hourly time axis
- each station group stores `temp` and `pressure`
- `station_002/pressure` intentionally lacks unit metadata
