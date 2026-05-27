from __future__ import annotations

import json
import unittest
from pathlib import Path


RETRIEVAL_ROOT = Path(__file__).resolve().parents[1] / "data" / "retrieval" / "external_candidate_pool"


class RetrievalQrelsTests(unittest.TestCase):
    def test_qrels_match_frozen_queries(self) -> None:
        queries = json.loads((RETRIEVAL_ROOT / "queries.json").read_text(encoding="utf-8"))["queries"]
        qrels = json.loads((RETRIEVAL_ROOT / "qrels.json").read_text(encoding="utf-8"))

        expected_by_query = {
            query["query_id"]: query["expected_candidate_id"]
            for query in queries
        }
        judged_by_query = {
            item["query_id"]: item
            for item in qrels["qrels"]
        }

        self.assertEqual(qrels["qrels_schema"], "single_positive_planted_v1")
        self.assertEqual(qrels["query_count"], len(queries))
        self.assertEqual(qrels["judgment_count"], len(queries))
        self.assertEqual(set(judged_by_query), set(expected_by_query))
        for query_id, expected_candidate_id in expected_by_query.items():
            judgment = judged_by_query[query_id]
            self.assertEqual(judgment["candidate_id"], expected_candidate_id)
            self.assertEqual(judgment["relevance_grade"], 2)
            self.assertEqual(judgment["query_source"], "planted")

    def test_artifact_manifest_lists_qrels_as_auxiliary_artifact(self) -> None:
        manifest = json.loads((RETRIEVAL_ROOT / "artifact_manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["artifact_files"]["qrels"], "retrieval/external_candidate_pool/qrels.json")


if __name__ == "__main__":
    unittest.main()
