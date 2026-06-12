from __future__ import annotations

import json
from pathlib import Path

import h5py
import numpy as np
from scipy.io import netcdf_file


ROOT = Path(__file__).resolve().parent
CHALLENGE_ROOT = ROOT / "testdata" / "netcdf_cf_phase13"


def _classic(name: str):
    CHALLENGE_ROOT.mkdir(parents=True, exist_ok=True)
    return netcdf_file(str(CHALLENGE_ROOT / name), "w")


def _base_time(handle, values, units="hours since 2026-01-01 00:00:00 UTC", calendar="standard"):
    handle.createDimension("time", len(values))
    time = handle.createVariable("time", "f8", ("time",))
    time[:] = values
    time.standard_name = "time"
    time.long_name = "observation time"
    time.units = units
    time.calendar = calendar
    time.axis = "T"
    return time


def _temperature(handle, dimensions=("time",), values=None, units="K"):
    variable = handle.createVariable("temperature", "f4", dimensions)
    variable[:] = np.asarray(values if values is not None else [280.0, 281.0, 282.0], dtype="f4")
    variable.standard_name = "air_temperature"
    variable.long_name = "air temperature"
    variable.units = units
    return variable


def build_standard_coordinates():
    with _classic("standard_coordinates.nc") as handle:
        handle.Conventions = "CF-1.8"
        _base_time(handle, [0, 1, 2])
        handle.createDimension("lat", 2)
        handle.createDimension("lon", 2)
        lat = handle.createVariable("lat", "f4", ("lat",))
        lat[:] = [10, 20]
        lat.standard_name = "latitude"
        lat.units = "degrees_north"
        lat.axis = "Y"
        lon = handle.createVariable("lon", "f4", ("lon",))
        lon[:] = [100, 110]
        lon.standard_name = "longitude"
        lon.units = "degrees_east"
        lon.axis = "X"
        _temperature(handle, ("time", "lat", "lon"), np.arange(12, dtype="f4").reshape(3, 2, 2))


def build_auxiliary_coordinates():
    with _classic("auxiliary_coordinates.nc") as handle:
        handle.Conventions = "CF-1.8"
        handle.createDimension("obs", 3)
        lat = handle.createVariable("lat", "f4", ("obs",))
        lat[:] = [10, 11, 12]
        lat.standard_name = "latitude"
        lat.units = "degrees_north"
        lon = handle.createVariable("lon", "f4", ("obs",))
        lon[:] = [100, 101, 102]
        lon.standard_name = "longitude"
        lon.units = "degrees_east"
        temp = _temperature(handle, ("obs",), [280, 281, 282])
        temp.coordinates = "lat lon"


def build_days_since():
    with _classic("days_since.nc") as handle:
        handle.Conventions = "CF-1.8"
        _base_time(handle, [0, 1, 2], units="days since 2026-01-01 00:00:00 UTC")
        _temperature(handle)


def build_calendar_360_day():
    with _classic("calendar_360_day.nc") as handle:
        handle.Conventions = "CF-1.8"
        _base_time(handle, [0, 1, 2], units="days since 2000-01-01", calendar="360_day")
        _temperature(handle)


def build_multiple_time_variables():
    with _classic("multiple_time_variables.nc") as handle:
        handle.Conventions = "CF-1.8"
        handle.createDimension("time", 3)
        for name, values in (("time", [0, 1, 2]), ("forecast_time", [0, 1, 2])):
            variable = handle.createVariable(name, "f8", ("time",))
            variable[:] = values
            variable.standard_name = "time"
            variable.units = "hours since 2026-01-01 00:00:00 UTC"
            variable.calendar = "standard"
            variable.axis = "T"
        _temperature(handle)


def build_irregular_sampling():
    with _classic("irregular_sampling.nc") as handle:
        handle.Conventions = "CF-1.8"
        _base_time(handle, [0, 1, 4, 9, 10])
        _temperature(handle, values=[280, 281, 282, 283, 284])


def build_bounds_variable():
    with _classic("bounds_variable.nc") as handle:
        handle.Conventions = "CF-1.8"
        time = _base_time(handle, [0, 1, 2])
        handle.createDimension("nv", 2)
        bounds = handle.createVariable("time_bnds", "f8", ("time", "nv"))
        bounds[:] = [[-0.5, 0.5], [0.5, 1.5], [1.5, 2.5]]
        bounds.units = "hours since 2026-01-01 00:00:00 UTC"
        time.bounds = "time_bnds"
        _temperature(handle)


def build_missing_metadata():
    with _classic("missing_metadata.nc") as handle:
        handle.createDimension("record", 3)
        value = handle.createVariable("mystery", "f4", ("record",))
        value[:] = [1, 2, 3]


def build_name_only_coordinate():
    with _classic("name_only_coordinate.nc") as handle:
        handle.createDimension("record", 3)
        value = handle.createVariable("lat", "f4", ("record",))
        value[:] = [10, 11, 12]


def build_coordinate_conflict():
    with _classic("coordinate_conflict.nc") as handle:
        handle.createDimension("record", 3)
        value = handle.createVariable("position", "f4", ("record",))
        value[:] = [10, 11, 12]
        value.standard_name = "latitude"
        value.axis = "X"


def build_malformed_cf_time():
    with _classic("malformed_cf_time.nc") as handle:
        handle.Conventions = "CF-1.8"
        handle.createDimension("time", 3)
        time = handle.createVariable("time", "f8", ("time",))
        time[:] = [0, 1, 2]
        time.standard_name = "time"
        time.axis = "T"
        time.units = "hours since not-a-date"
        time.calendar = "standard"
        _temperature(handle)


def build_unmapped_unit():
    with _classic("unmapped_unit.nc") as handle:
        handle.Conventions = "CF-1.8"
        handle.createDimension("record", 3)
        value = handle.createVariable("signal", "f4", ("record",))
        value[:] = [1, 2, 3]
        value.long_name = "instrument signal"
        value.units = "furlongs_per_fortnight"


def build_missing_markers():
    with _classic("missing_markers.nc") as handle:
        handle.Conventions = "CF-1.8"
        handle.createDimension("record", 3)
        value = handle.createVariable("temperature", "f4", ("record",))
        value[:] = [280, -9999, 282]
        value.standard_name = "air_temperature"
        value.units = "K"
        value._FillValue = np.float32(-9999)
        value.missing_value = np.float32(-9999)


def build_hdf5_grouped_netcdf():
    path = CHALLENGE_ROOT / "grouped_netcdf4.nc"
    with h5py.File(path, "w") as handle:
        handle.attrs["Conventions"] = "CF-1.8"
        handle.attrs["_NCProperties"] = "version=2"
        group = handle.create_group("observations")
        time = group.create_dataset("time", data=np.asarray([0, 1, 2], dtype="f8"))
        time.attrs["standard_name"] = "time"
        time.attrs["units"] = "hours since 2026-01-01 00:00:00 UTC"
        time.attrs["calendar"] = "standard"
        time.attrs["axis"] = "T"
        time.attrs["_Netcdf4Dimid"] = 0
        time.make_scale("time")
        temperature = group.create_dataset("temperature", data=np.asarray([280, 281, 282], dtype="f4"))
        temperature.attrs["standard_name"] = "air_temperature"
        temperature.attrs["units"] = "K"
        temperature.dims[0].attach_scale(time)


def build_manifest():
    manifest = {
        "experiment_id": "phase13_netcdf_cf",
        "cases": [
            {
                "case_id": "standard_coordinates",
                "file": "standard_coordinates.nc",
                "expected_variables": ["time", "lat", "lon", "temperature"],
                "expected_dimensions": ["time", "lat", "lon"],
                "expected_coordinate_roles": {
                    "time": ["dimension_coordinate", "axis_t", "standard_time"],
                    "lat": ["dimension_coordinate", "axis_y", "standard_latitude", "geospatial_coordinate"],
                    "lon": ["dimension_coordinate", "axis_x", "standard_longitude", "geospatial_coordinate"]
                },
                "expected_time_field": "time",
                "expected_calendar": {"time": ["standard", "supported"]},
                "expected_units": {"temperature": "normalized_ucum"},
                "expect_temporal_abstention": False
            },
            {
                "case_id": "auxiliary_coordinates",
                "file": "auxiliary_coordinates.nc",
                "expected_variables": ["lat", "lon", "temperature"],
                "expected_dimensions": ["obs"],
                "expected_coordinate_roles": {"lat": ["auxiliary_coordinate"], "lon": ["auxiliary_coordinate"]},
                "expected_time_field": None,
                "expected_calendar": {},
                "expected_units": {},
                "expect_temporal_abstention": True
            },
            {
                "case_id": "days_since",
                "file": "days_since.nc",
                "expected_variables": ["time", "temperature"],
                "expected_coordinate_roles": {"time": ["dimension_coordinate", "axis_t", "standard_time"]},
                "expected_time_field": "time",
                "expected_calendar": {"time": ["standard", "supported"]},
                "expected_units": {},
                "expect_temporal_abstention": False
            },
            {
                "case_id": "calendar_360_day",
                "file": "calendar_360_day.nc",
                "expected_variables": ["time", "temperature"],
                "expected_coordinate_roles": {"time": ["dimension_coordinate", "axis_t", "standard_time"]},
                "expected_time_field": None,
                "expected_calendar": {"time": ["360_day", "supported"]},
                "expected_units": {},
                "expect_temporal_abstention": True
            },
            {
                "case_id": "multiple_time_variables",
                "file": "multiple_time_variables.nc",
                "expected_variables": ["time", "forecast_time", "temperature"],
                "expected_coordinate_roles": {"time": ["dimension_coordinate", "axis_t", "standard_time"], "forecast_time": ["axis_t", "standard_time"]},
                "expected_time_field": None,
                "expected_calendar": {"time": ["standard", "supported"], "forecast_time": ["standard", "supported"]},
                "expected_units": {},
                "expect_temporal_abstention": True
            },
            {
                "case_id": "irregular_sampling",
                "file": "irregular_sampling.nc",
                "expected_variables": ["time", "temperature"],
                "expected_coordinate_roles": {"time": ["dimension_coordinate", "axis_t", "standard_time"]},
                "expected_time_field": "time",
                "expected_calendar": {"time": ["standard", "supported"]},
                "expected_time_properties": {"frequency": "mixed", "regularity": "irregular", "missing_intervals": None},
                "expected_units": {},
                "expect_temporal_abstention": False
            },
            {
                "case_id": "bounds_variable",
                "file": "bounds_variable.nc",
                "expected_variables": ["time", "time_bnds", "temperature"],
                "expected_dimensions": ["time", "nv"],
                "expected_coordinate_roles": {"time": ["dimension_coordinate", "axis_t", "standard_time"]},
                "expected_bounds_variables": ["time_bnds"],
                "expected_time_field": "time",
                "expected_calendar": {"time": ["standard", "supported"]},
                "expected_units": {},
                "expect_temporal_abstention": False
            },
            {
                "case_id": "missing_metadata",
                "file": "missing_metadata.nc",
                "expected_variables": ["mystery"],
                "expected_coordinate_roles": {},
                "expected_unknown_fields": ["mystery"],
                "expected_time_field": None,
                "expected_calendar": {},
                "expected_units": {},
                "expect_temporal_abstention": True
            },
            {
                "case_id": "name_only_coordinate",
                "file": "name_only_coordinate.nc",
                "expected_variables": ["lat"],
                "expected_coordinate_roles": {},
                "expected_unknown_fields": ["lat"],
                "expected_time_field": None,
                "expected_calendar": {},
                "expected_units": {},
                "expect_temporal_abstention": True
            },
            {
                "case_id": "coordinate_conflict",
                "file": "coordinate_conflict.nc",
                "expected_variables": ["position"],
                "expected_coordinate_roles": {"position": ["axis_x", "standard_latitude"]},
                "expected_coordinate_claim_states": {"position": "conflicted"},
                "expected_unknown_fields": ["position"],
                "expected_time_field": None,
                "expected_calendar": {},
                "expected_units": {},
                "expect_temporal_abstention": True
            },
            {
                "case_id": "malformed_cf_time",
                "file": "malformed_cf_time.nc",
                "expected_variables": ["time", "temperature"],
                "expected_coordinate_roles": {"time": ["dimension_coordinate", "axis_t", "standard_time"]},
                "expected_time_field": None,
                "expected_calendar": {"time": ["standard", "conflicted"]},
                "expected_units": {},
                "expect_temporal_abstention": True
            },
            {
                "case_id": "unmapped_unit",
                "file": "unmapped_unit.nc",
                "expected_variables": ["signal"],
                "expected_coordinate_roles": {},
                "expected_time_field": None,
                "expected_calendar": {},
                "expected_units": {"signal": "unmapped_unit"},
                "expect_temporal_abstention": True
            },
            {
                "case_id": "missing_markers",
                "file": "missing_markers.nc",
                "expected_variables": ["temperature"],
                "expected_coordinate_roles": {},
                "expected_nullable_fields": ["temperature"],
                "expected_time_field": None,
                "expected_calendar": {},
                "expected_units": {"temperature": "normalized_ucum"},
                "expect_temporal_abstention": True
            },
            {
                "case_id": "grouped_netcdf4",
                "file": "grouped_netcdf4.nc",
                "expected_variables": ["/observations/time", "/observations/temperature"],
                "expected_dimensions": ["time"],
                "expected_groups": ["/observations"],
                "expected_coordinate_roles": {"/observations/time": ["dimension_coordinate", "axis_t", "standard_time"]},
                "expected_time_field": "time",
                "expected_calendar": {"/observations/time": ["standard", "supported"]},
                "expected_units": {"/observations/temperature": "normalized_ucum"},
                "expect_temporal_abstention": False
            }
        ]
    }
    (CHALLENGE_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main():
    build_standard_coordinates()
    build_auxiliary_coordinates()
    build_days_since()
    build_calendar_360_day()
    build_multiple_time_variables()
    build_irregular_sampling()
    build_bounds_variable()
    build_missing_metadata()
    build_name_only_coordinate()
    build_coordinate_conflict()
    build_malformed_cf_time()
    build_unmapped_unit()
    build_missing_markers()
    build_hdf5_grouped_netcdf()
    build_manifest()
    print("Phase 13 NetCDF/CF challenge pack built: 14 cases")


if __name__ == "__main__":
    main()
