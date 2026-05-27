from __future__ import annotations

import unittest

from high_fidelity_schema_study.unit_normalization import normalize_unit_claim


class UnitNormalizationTests(unittest.TestCase):
    def test_normalizes_common_units_to_ucum_codes(self) -> None:
        celsius = normalize_unit_claim("Celsius", ["column_name_unit_hint"])
        meter = normalize_unit_claim("meter", ["column_name_unit_hint"])

        self.assertEqual(celsius["status"], "normalized_ucum")
        self.assertEqual(celsius["ucum_code"], "Cel")
        self.assertEqual(celsius["evidence_basis"], "name_pattern")
        self.assertEqual(meter["ucum_code"], "m")

    def test_records_unmapped_explicit_time_reference_units(self) -> None:
        normalized = normalize_unit_claim("hours since 2026-01-01 00:00:00 UTC", ["hdf5_attribute"])

        self.assertEqual(normalized["status"], "unmapped_unit")
        self.assertEqual(normalized["evidence_basis"], "explicit_metadata")
        self.assertIsNone(normalized["ucum_code"])


if __name__ == "__main__":
    unittest.main()
