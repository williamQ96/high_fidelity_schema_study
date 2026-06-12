from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parent
CHALLENGE_ROOT = ROOT / "testdata" / "parquet_phase15a"


def _write(name: str, table: pa.Table, **kwargs) -> None:
    CHALLENGE_ROOT.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, CHALLENGE_ROOT / name, version="2.6", **kwargs)


def build_primitives() -> None:
    schema = pa.schema(
        [
            pa.field("id", pa.int64(), nullable=False, metadata={b"role": b"identifier"}),
            pa.field("value", pa.float32()),
            pa.field("label", pa.string()),
            pa.field("active", pa.bool_()),
        ],
        metadata={b"dataset": b"phase15a_primitives"},
    )
    table = pa.Table.from_arrays(
        [
            pa.array([1, 2, 3, 4], type=pa.int64()),
            pa.array([1.5, 2.5, None, 4.5], type=pa.float32()),
            pa.array(["a", "b", "b", None], type=pa.string()),
            pa.array([True, False, True, True], type=pa.bool_()),
        ],
        schema=schema,
    )
    _write("primitives.parquet", table, compression="snappy", row_group_size=2)


def build_nested() -> None:
    profile_type = pa.struct(
        [
            pa.field("age", pa.int32()),
            pa.field("tags", pa.list_(pa.field("element", pa.string(), nullable=False))),
        ]
    )
    table = pa.table(
        {
            "entity_id": pa.array([1, 2], type=pa.int64()),
            "profile": pa.array(
                [{"age": 30, "tags": ["alpha", "beta"]}, {"age": None, "tags": []}],
                type=profile_type,
            ),
            "scores": pa.array([[1.0, 2.0], None], type=pa.list_(pa.float64())),
        }
    )
    _write("nested_struct_list.parquet", table, compression="gzip")


def build_timestamps() -> None:
    utc = pa.array(
        [
            datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
        ],
        type=pa.timestamp("ms", tz="UTC"),
    )
    naive = pa.array(
        [
            datetime(2026, 1, 1, 0, 0),
            datetime(2026, 1, 1, 1, 0),
        ],
        type=pa.timestamp("us"),
    )
    _write("timestamps.parquet", pa.table({"event_time": utc, "local_time": naive}), compression="zstd")


def build_dictionary() -> None:
    dictionary = pa.array(["red", "blue", "red", "green"]).dictionary_encode()
    _write("dictionary.parquet", pa.table({"category": dictionary}), use_dictionary=True)


def build_required_nullable() -> None:
    schema = pa.schema(
        [
            pa.field("required_id", pa.int32(), nullable=False),
            pa.field("optional_value", pa.int32(), nullable=True),
        ]
    )
    table = pa.Table.from_arrays(
        [pa.array([1, 2, 3]), pa.array([10, None, 30])],
        schema=schema,
    )
    _write("required_nullable.parquet", table)


def build_no_statistics() -> None:
    table = pa.table({"value": pa.array([5, 4, 3, 2, 1], type=pa.int64())})
    _write("no_statistics.parquet", table, write_statistics=False)


def build_decimal_binary() -> None:
    table = pa.table(
        {
            "amount": pa.array([Decimal("12.34"), Decimal("56.78")], type=pa.decimal128(10, 2)),
            "payload": pa.array([b"\x00\xff", b"ok"], type=pa.binary()),
        }
    )
    _write("decimal_binary.parquet", table, compression=None)


def build_empty() -> None:
    schema = pa.schema([pa.field("id", pa.int64()), pa.field("name", pa.string())])
    _write("empty.parquet", pa.Table.from_batches([], schema=schema))


def build_manifest() -> None:
    manifest = {
        "experiment_id": "phase15a_parquet_arrow",
        "claim_boundary": (
            "Controlled PyArrow-produced Parquet challenge pack; validates metadata-first extraction "
            "and does not establish broad Parquet ecosystem robustness."
        ),
        "generation": {
            "library": "pyarrow",
            "version": pa.__version__,
            "method": "create_phase15a_parquet_challenge.py",
        },
        "cases": [
            {
                "case_id": "primitives",
                "file": "primitives.parquet",
                "expected_fields": ["id", "value", "label", "active"],
                "expected_columns": ["id", "value", "label", "active"],
                "expected_row_groups": 2,
                "expected_compression": ["SNAPPY"],
                "expected_metadata_keys": ["dataset"],
                "expected_field_metadata": {"id": ["role"]},
            },
            {
                "case_id": "nested_struct_list",
                "file": "nested_struct_list.parquet",
                "expected_fields": [
                    "entity_id",
                    "profile",
                    "profile.age",
                    "profile.tags",
                    "profile.tags.element",
                    "scores",
                    "scores.element",
                ],
                "expected_columns": ["entity_id", "profile.age", "profile.tags.list.element", "scores.list.element"],
                "expected_row_groups": 1,
                "expected_compression": ["GZIP"],
            },
            {
                "case_id": "timestamps",
                "file": "timestamps.parquet",
                "expected_fields": ["event_time", "local_time"],
                "expected_columns": ["event_time", "local_time"],
                "expected_row_groups": 1,
                "expected_compression": ["ZSTD"],
                "expected_timezones": {"event_time": "UTC", "local_time": "unknown"},
            },
            {
                "case_id": "dictionary",
                "file": "dictionary.parquet",
                "expected_fields": ["category"],
                "expected_columns": ["category"],
                "expected_row_groups": 1,
                "expected_encodings": ["RLE_DICTIONARY"],
            },
            {
                "case_id": "required_nullable",
                "file": "required_nullable.parquet",
                "expected_fields": ["required_id", "optional_value"],
                "expected_columns": ["required_id", "optional_value"],
                "expected_row_groups": 1,
                "expected_nullability": {"required_id": False, "optional_value": True},
            },
            {
                "case_id": "no_statistics",
                "file": "no_statistics.parquet",
                "expected_fields": ["value"],
                "expected_columns": ["value"],
                "expected_row_groups": 1,
                "expected_statistics_state": "unknown",
            },
            {
                "case_id": "decimal_binary",
                "file": "decimal_binary.parquet",
                "expected_fields": ["amount", "payload"],
                "expected_columns": ["amount", "payload"],
                "expected_row_groups": 1,
                "expected_compression": ["UNCOMPRESSED"],
            },
            {
                "case_id": "empty",
                "file": "empty.parquet",
                "expected_fields": ["id", "name"],
                "expected_columns": ["id", "name"],
                "expected_row_groups": 1,
            },
        ],
    }
    (CHALLENGE_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    build_primitives()
    build_nested()
    build_timestamps()
    build_dictionary()
    build_required_nullable()
    build_no_statistics()
    build_decimal_binary()
    build_empty()
    build_manifest()
    print(f"Phase 15A Parquet challenge pack built: {len(json.loads((CHALLENGE_ROOT / 'manifest.json').read_text())['cases'])} cases")


if __name__ == "__main__":
    main()
