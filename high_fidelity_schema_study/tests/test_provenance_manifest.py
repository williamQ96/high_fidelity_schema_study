from __future__ import annotations

import json
import unittest
from pathlib import Path

from high_fidelity_schema_study.build_provenance_manifest import build_provenance_manifest


DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


class ProvenanceManifestTests(unittest.TestCase):
    def test_builds_lightweight_prov_summary(self) -> None:
        manifest = build_provenance_manifest()
        summary = manifest["summary"]

        self.assertEqual(manifest["provenance_model"], "lightweight_prov_v1")
        self.assertEqual(summary["dataset_count"], 9)
        self.assertEqual(summary["field_entity_count"], 53)
        self.assertEqual(summary["evidence_entity_count"], 109)
        self.assertEqual(summary["semantic_annotation_result_count"], 9)
        self.assertGreaterEqual(summary["entity_count"], 200)

    def test_checked_in_manifest_links_core_agents_and_relations(self) -> None:
        manifest = json.loads((DATA_ROOT / "derived" / "provenance_manifest.json").read_text(encoding="utf-8"))
        agent_ids = {agent["id"] for agent in manifest["agents"]}
        generated_entities = {
            relation["entity"]
            for relation in manifest["relations"]["wasGeneratedBy"]
        }

        self.assertIn("agent:deterministic_extractors", agent_ids)
        self.assertIn("agent:semantic_merge_policy", agent_ids)
        self.assertIn("derived_schema:csv_easy_weather_stations", generated_entities)
        self.assertIn("report:paper_tables", generated_entities)


if __name__ == "__main__":
    unittest.main()
