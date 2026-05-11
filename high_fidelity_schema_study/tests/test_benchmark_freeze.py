from __future__ import annotations

import json
import unittest
from pathlib import Path


DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
DOCS_ROOT = Path(__file__).resolve().parents[1] / "docs"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


class BenchmarkFreezeTests(unittest.TestCase):
    def test_freeze_matches_current_manifests(self) -> None:
        freeze = load_json(DOCS_ROOT / "benchmark_freeze_2026-05-04.json")
        pilot_manifest = load_json(DATA_ROOT / "pilot_corpus_manifest.json")
        pool_manifest = load_json(DATA_ROOT / "retrieval" / "external_candidate_pool" / "pool_manifest.json")
        artifact_manifest = load_json(DATA_ROOT / "retrieval" / "external_candidate_pool" / "artifact_manifest.json")

        self.assertEqual(freeze["internal_pilot"]["dataset_count"], len(pilot_manifest["datasets"]))
        self.assertEqual(
            sorted(freeze["internal_pilot"]["datasets"]),
            sorted(entry["dataset_id"] for entry in pilot_manifest["datasets"]),
        )

        pool_entries = pool_manifest["entries"]
        targets = [entry["source_file"] for entry in pool_entries if entry["role"] == "target"]
        distractors = [entry["source_file"] for entry in pool_entries if entry["role"] == "distractor"]
        self.assertEqual(freeze["external_retrieval_pool"]["entry_count"], len(pool_entries))
        self.assertEqual(freeze["external_retrieval_pool"]["target_count"], len(targets))
        self.assertEqual(freeze["external_retrieval_pool"]["distractor_count"], len(distractors))
        self.assertEqual(sorted(freeze["external_retrieval_pool"]["targets"]), sorted(targets))
        self.assertEqual(sorted(freeze["external_retrieval_pool"]["distractors"]), sorted(distractors))

        for system_name in freeze["retrieval_protocol"]["systems"]:
            self.assertIn(system_name, artifact_manifest["artifact_files"])


if __name__ == "__main__":
    unittest.main()
