from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from high_fidelity_schema_study.repair_external_import_manifest import find_local_file


class RepairExternalImportManifestTests(unittest.TestCase):
    def test_find_local_file_handles_plus_encoded_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            directory = Path(tmp_dir)
            encoded = directory / "Season+and+site+fidelity+determine+home+range.csv"
            encoded.write_text("x", encoding="utf-8")
            found = find_local_file(directory, "Season and site fidelity determine home range.csv")
            self.assertEqual(found, encoded)


if __name__ == "__main__":
    unittest.main()
