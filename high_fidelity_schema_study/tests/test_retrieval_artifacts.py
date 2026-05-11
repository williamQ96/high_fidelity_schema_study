from __future__ import annotations

import unittest

from high_fidelity_schema_study.build_retrieval_artifacts import source_slice_terms
from high_fidelity_schema_study.evaluate_retrieval_artifacts import evaluate_artifact


class RetrievalArtifactTests(unittest.TestCase):
    def test_source_slice_terms_extracts_year_slice(self) -> None:
        terms = source_slice_terms("dryad/example/fjord_year1.csv")

        self.assertIn("year1", terms)
        self.assertIn("first-year", terms)
        self.assertIn("file_slice_year1", terms)

    def test_source_slice_terms_extracts_school_slice(self) -> None:
        terms = source_slice_terms("zenodo/example/sensor_school_5.csv")

        self.assertIn("school5", terms)
        self.assertIn("school 5", terms)
        self.assertIn("file_slice_school5", terms)

    def test_evaluate_artifact_handles_schema_source_variants(self) -> None:
        documents = [
            {
                "candidate_id": "year1.csv",
                "title": "year1",
                "text": "greenland cod telemetry file_slice_year1 first-year coordinate",
            },
            {
                "candidate_id": "year2.csv",
                "title": "year2",
                "text": "greenland cod telemetry file_slice_year2 second-year coordinate",
            },
        ]
        queries = [
            {
                "query_id": "year1_query",
                "text": "greenland cod first-year telemetry",
                "expected_candidate_id": "year1.csv",
            }
        ]

        result = evaluate_artifact("schema_enhanced_semantic_merged", documents, queries)

        self.assertEqual(result["artifact_name"], "schema_enhanced_semantic_merged")
        self.assertTrue(result["queries"][0]["top_1_correct"])


if __name__ == "__main__":
    unittest.main()
