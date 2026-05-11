from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from high_fidelity_schema_study.semantic_annotate import atomic_write_json, load_json


class SemanticAnnotateManifestTests(unittest.TestCase):
    def test_atomic_write_and_load_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "manifest.json"
            atomic_write_json(path, {"a": 1})
            self.assertEqual(load_json(path), {"a": 1})


if __name__ == "__main__":
    unittest.main()
