from __future__ import annotations

import unittest

from high_fidelity_schema_study.evaluate_internal_baseline import bucket_confidence, categorize_field_failure, safe_ratio


class InternalBaselineEvalTests(unittest.TestCase):
    def test_safe_ratio_handles_zero_denominator(self) -> None:
        self.assertEqual(safe_ratio(0, 0), 0.0)
        self.assertEqual(safe_ratio(1, 4), 0.25)

    def test_bucket_confidence(self) -> None:
        self.assertEqual(bucket_confidence(0.97), "0.95-1.00")
        self.assertEqual(bucket_confidence(0.90), "0.85-0.95")
        self.assertEqual(bucket_confidence(0.80), "0.70-0.85")
        self.assertEqual(bucket_confidence(0.50), "<0.70")

    def test_categorize_field_failure(self) -> None:
        missing = {
            "status": "missing",
            "field_path": "x",
        }
        self.assertEqual(categorize_field_failure(missing), ["missing_field"])

        matched = {
            "status": "matched",
            "field_path": "power_kw",
            "physical_match": True,
            "logical_match": False,
            "semantic_match": False,
            "gold_logical_type": "measurement",
            "derived_logical_type": "unknown",
            "gold_semantic_type": "power",
            "derived_semantic_type": "unknown",
            "gold_unit": "kilowatt",
            "derived_unit": None,
        }
        self.assertEqual(
            categorize_field_failure(matched),
            ["logical_unknown", "semantic_unknown", "unit_mismatch"],
        )


if __name__ == "__main__":
    unittest.main()
