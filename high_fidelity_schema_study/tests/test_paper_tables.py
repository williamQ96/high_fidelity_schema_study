from __future__ import annotations

import unittest

from high_fidelity_schema_study.build_paper_tables import build_paper_tables, render_markdown


class PaperTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = build_paper_tables()
        self.tables = self.report["tables"]

    def test_benchmark_slice_counts_are_frozen(self) -> None:
        values = {row["measure"]: row["value"] for row in self.tables["benchmark_slice"]}

        self.assertEqual(values["Internal pilot datasets"], 9)
        self.assertEqual(values["External retrieval candidate files"], 16)
        self.assertEqual(values["Promoted external target files"], 10)
        self.assertEqual(values["External distractor files"], 6)
        self.assertEqual(values["Locked external field-subset regression groups"], 3)

    def test_schema_enhanced_retrieval_metrics_are_reported(self) -> None:
        retrieval_rows = {
            row["system"]: row
            for row in self.tables["retrieval_metrics"]
        }

        semantic_merged = retrieval_rows["schema_enhanced_semantic_merged"]
        self.assertEqual(semantic_merged["schema_source"], "semantic-merged schema")
        self.assertEqual(semantic_merged["query_count"], 10)
        self.assertEqual(semantic_merged["recall_at_1"], 1.0)
        self.assertEqual(semantic_merged["mrr"], 1.0)

    def test_semantic_merge_gain_is_locked(self) -> None:
        aggregate = self.tables["semantic_merge_aggregate"][0]
        dataset_rows = {
            row["dataset_id"]: row
            for row in self.tables["semantic_merge_dataset_delta"]
        }

        self.assertEqual(aggregate["dataset_count"], 3)
        self.assertEqual(aggregate["improved_dataset_count"], 2)
        self.assertEqual(aggregate["accepted_for_merge_count"], 3)
        self.assertEqual(dataset_rows["csv_hard_field_campaign"]["logical_accuracy_delta"], 0.3333)
        self.assertEqual(dataset_rows["csv_easy_weather_stations"]["logical_accuracy_delta"], 0.1667)

    def test_deterministic_profile_summary_is_reported(self) -> None:
        summary_values = {
            row["metric"]: row["value"]
            for row in self.tables["deterministic_profile_summary"]
        }
        relationship_counts = {
            row["relationship_type"]: row["count"]
            for row in self.tables["deterministic_profile_relationships"]
        }

        self.assertEqual(summary_values["Internal datasets with deterministic profile"], 9)
        self.assertEqual(summary_values["Derived fields profiled"], 53)
        self.assertEqual(summary_values["Cross-file relationship candidates"], 22)
        self.assertEqual(relationship_counts["shared_identifier_semantic"], 6)
        self.assertEqual(relationship_counts["shared_measurement_semantic"], 6)
        self.assertEqual(relationship_counts["shared_time_axis_semantic"], 6)

    def test_markdown_contains_paper_claims(self) -> None:
        markdown = render_markdown(self.report)

        self.assertIn("## Table 5. External Retrieval Metrics", markdown)
        self.assertIn("Schema-enhanced retrieval reaches Recall@1 = 1.0000", markdown)


if __name__ == "__main__":
    unittest.main()
