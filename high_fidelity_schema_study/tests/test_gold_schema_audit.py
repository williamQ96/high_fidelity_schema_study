import unittest

from high_fidelity_schema_study.audit_gold_schemas import audit_gold_schemas


class GoldSchemaAuditTests(unittest.TestCase):
    def test_internal_gold_schemas_pass_second_pass_consistency_audit(self) -> None:
        report = audit_gold_schemas()

        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["dataset_count"], 9)
        self.assertEqual(report["field_count"], 50)
        self.assertEqual(report["finding_counts"].get("error", 0), 0)


if __name__ == "__main__":
    unittest.main()
