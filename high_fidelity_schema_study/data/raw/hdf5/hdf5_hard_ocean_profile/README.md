# hdf5_hard_ocean_profile

Deeply nested ocean-profile hierarchy with repeated casts and partial field metadata.

- `/campaign/run_01/cast_000*/depth_m` is the vertical coordinate
- `/campaign/run_01/cast_000*/temp` stores seawater temperature
- only one cast includes an explicit temperature unit attribute
- salinity is named structurally but not fully attributed
