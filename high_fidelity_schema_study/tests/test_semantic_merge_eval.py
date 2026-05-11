from __future__ import annotations

import unittest

from high_fidelity_schema_study.evaluate_semantic_merge import safe_ratio


class SemanticMergeEvalTests(unittest.TestCase):
    def test_safe_ratio_handles_zero(self) -> None:
        self.assertEqual(safe_ratio(0, 0), 0.0)
        self.assertEqual(safe_ratio(3, 4), 0.75)


if __name__ == "__main__":
    unittest.main()
