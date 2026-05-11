from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np

from high_fidelity_schema_study.extractors.hdf5_extractor import extract_hdf5_schema


class Hdf5ExtractorTests(unittest.TestCase):
    def test_normalizes_string_dtype_and_preserves_units(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "sample.h5"
            with h5py.File(file_path, "w") as handle:
                station_dtype = h5py.string_dtype(encoding="utf-8")
                station = handle.create_dataset(
                    "station_id",
                    data=np.array(["ST001", "ST002"], dtype=object),
                    dtype=station_dtype,
                )
                station.attrs["long_name"] = "station identifier"
                temp = handle.create_dataset("temperature", data=np.array([12.5, 13.1], dtype=np.float32))
                temp.attrs["unit"] = "C"

            schema = extract_hdf5_schema(str(file_path))

        fields = {field.field_path: field for field in schema.fields}
        self.assertEqual(schema.file_format, "hdf5")
        self.assertEqual(fields["/station_id"].physical_type, "string")
        self.assertEqual(fields["/temperature"].physical_type, "float32")
        self.assertEqual(fields["/temperature"].unit, "C")


if __name__ == "__main__":
    unittest.main()
