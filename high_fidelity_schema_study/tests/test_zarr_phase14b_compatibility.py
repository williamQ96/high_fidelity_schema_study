from __future__ import annotations

from pathlib import Path

from high_fidelity_schema_study.extractors.base import ExtractionRequest
from high_fidelity_schema_study.extractors.registry import extract_path


ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "testdata" / "zarr_phase14b_compatibility"


def _extract(name: str):
    return extract_path(ExtractionRequest(str(CORPUS_ROOT / name)))


def test_root_array_and_structured_dtype_are_compatible():
    root_array = _extract("root_array_numpy_style.zarr")
    records = _extract("structured_dtype_records.zarr")

    assert root_array.status == "success"
    assert root_array.schema is not None
    assert root_array.schema.fields[0].field_path == "/"
    assert root_array.schema.fields[0].field_name == "root_array_numpy_style"

    assert records.status == "success"
    assert records.schema is not None
    analysis = records.schema.metadata["zarr_analysis"]["arrays"][0]
    assert analysis["array_metadata"]["dtype"] == [
        ["timestamp", "<i8"],
        ["quality", "|u1"],
        ["value", "<f4"],
    ]


def test_auxiliary_coordinate_references_are_group_scoped():
    outcome = _extract("nested_instrument_groups.zarr")

    assert outcome.status == "success"
    assert outcome.schema is not None
    analyses = {
        item["field_path"]: item
        for item in outcome.schema.metadata["zarr_analysis"]["arrays"]
    }
    assert "auxiliary_coordinate" in analyses["station_a/qc"]["coordinate_roles"]
    assert analyses["station_b/qc"]["coordinate_role_claim"]["state"] == "unknown"


def test_array_boundary_aware_walk_prunes_slash_chunk_tree():
    outcome = _extract("slash_separator_tree.zarr")

    assert outcome.status == "success"
    assert outcome.schema is not None
    inventory = outcome.schema.metadata["store_inventory"]
    assert inventory["walk_strategy"] == "array_boundary_aware"
    assert inventory["pruned_array_directory_count"] >= 1
    assert inventory["payload_bytes_read"] == 0
    assert outcome.schema.metadata["documents_discovered"] == [".zgroup", "image/.zarray"]


def test_compatibility_gaps_are_explicit_without_unsupported_promotion():
    unresolved = _extract("unresolved_coordinate_reference.zarr")
    dimension_conflict = _extract("dimension_conflict_group.zarr")

    assert unresolved.schema is not None
    unresolved_gaps = unresolved.schema.metadata["zarr_analysis"]["compatibility_gaps"]
    assert {gap["code"] for gap in unresolved_gaps} == {"unresolved_coordinate_reference"}
    assert all(gap["evidence_refs"] for gap in unresolved_gaps)
    assert {field.field_path for field in unresolved.schema.fields} == {"lat", "measurement"}

    assert dimension_conflict.schema is not None
    dimensions = dimension_conflict.schema.metadata["dimensions"]
    assert dimensions["record"]["state"] == "conflicted"
    dimension_gaps = dimension_conflict.schema.metadata["zarr_analysis"]["compatibility_gaps"]
    assert {gap["code"] for gap in dimension_gaps} == {
        "dimension_size_conflict"
    }
    assert all(gap["evidence_refs"] for gap in dimension_gaps)


def test_stale_consolidated_and_malformed_variants_are_structured():
    stale = _extract("stale_consolidated_metadata.zarr")
    malformed = _extract("malformed_only_array.zarr")

    assert stale.status == "partial"
    assert stale.schema is not None
    assert stale.schema.fields[0].shape == [4]
    assert {issue.code for issue in stale.issues} >= {"partial_extraction", "zarr_consolidated_conflict"}

    assert malformed.status == "failed"
    assert malformed.schema is None
    assert malformed.issues[0].code == "zarr_metadata_malformed"
