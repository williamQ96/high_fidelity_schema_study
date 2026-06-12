from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CHALLENGE_ROOT = ROOT / "testdata" / "json_phase16a"


def _write_json(name: str, payload) -> None:
    CHALLENGE_ROOT.mkdir(parents=True, exist_ok=True)
    (CHALLENGE_ROOT / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_cases() -> None:
    _write_json(
        "single_object.json",
        {"id": 1, "name": "alpha", "active": True, "metadata": {"source": "sensor", "quality": 3}},
    )
    _write_json(
        "records_missing_null.json",
        [
            {"id": 1, "value": 10.5, "label": "a"},
            {"id": 2, "value": None},
            {"id": 3, "label": "c"},
        ],
    )
    _write_json(
        "heterogeneous_arrays.json",
        [
            {"id": 1, "items": [1, 2, 3]},
            {"id": 2, "items": ["x", {"nested": True}, None]},
        ],
    )
    _write_json(
        "nested_records.json",
        [
            {"station": {"id": "A", "location": {"lat": 10.0, "lon": 20.0}}, "values": [{"v": 1}, {"v": 2}]},
            {"station": {"id": "B", "location": {"lat": 11.0}}, "values": []},
        ],
    )
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.invalid/measurement.schema.json",
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"type": "integer", "description": "Declared identifier"},
            "value": {"type": ["number", "null"]},
            "context": {
                "type": "object",
                "required": ["source"],
                "properties": {"source": {"type": "string"}},
            },
        },
        "examples": [
            {"id": 1, "value": 12.5, "context": {"source": "sensor"}},
            {"id": 2, "value": "not-a-number", "context": {"source": "manual"}},
        ],
    }
    _write_json("declared_schema.json", schema)
    lines = [{"id": index, "kind": "even" if index % 2 == 0 else "odd"} for index in range(6)]
    (CHALLENGE_ROOT / "sampled.jsonl").write_text(
        "".join(json.dumps(item) + "\n" for item in lines),
        encoding="utf-8",
    )


def build_manifest() -> None:
    manifest = {
        "experiment_id": "phase16a_json_structure",
        "claim_boundary": "Controlled JSON challenge pack; observed structures are sample-bounded and not universal schema truth.",
        "cases": [
            {
                "case_id": "single_object",
                "file": "single_object.json",
                "expected_mode": "bounded_observed_structure",
                "expected_paths": ["$.id", "$.name", "$.active", "$.metadata", "$.metadata.source", "$.metadata.quality"],
            },
            {
                "case_id": "records_missing_null",
                "file": "records_missing_null.json",
                "expected_mode": "bounded_observed_structure",
                "expected_paths": ["$.id", "$.value", "$.label"],
                "expected_missing": {"$.value": 1, "$.label": 1},
                "expected_nullable": ["$.value", "$.label"],
            },
            {
                "case_id": "heterogeneous_arrays",
                "file": "heterogeneous_arrays.json",
                "expected_mode": "bounded_observed_structure",
                "expected_paths": ["$.id", "$.items", "$.items[]", "$.items[].nested"],
                "expected_heterogeneous_arrays": ["$.items"],
            },
            {
                "case_id": "nested_records",
                "file": "nested_records.json",
                "expected_mode": "bounded_observed_structure",
                "expected_paths": ["$.station.location.lat", "$.station.location.lon", "$.values", "$.values[]", "$.values[].v"],
                "expected_missing": {"$.station.location.lon": 1, "$.values[].v": 1},
            },
            {
                "case_id": "declared_schema",
                "file": "declared_schema.json",
                "expected_mode": "declared_json_schema",
                "expected_paths": ["$.id", "$.value", "$.context", "$.context.source"],
                "expected_declared_required": {"$.id": True, "$.value": False, "$.context.source": True},
                "expected_conflict_count": 1,
            },
            {
                "case_id": "sampled_json_lines",
                "file": "sampled.jsonl",
                "sample_limit": 3,
                "expected_mode": "bounded_observed_structure",
                "expected_paths": ["$.id", "$.kind"],
                "expected_sampling_issue": True,
            },
        ],
    }
    (CHALLENGE_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    build_cases()
    build_manifest()
    print("Phase 16A JSON challenge pack built: 6 cases")


if __name__ == "__main__":
    main()
