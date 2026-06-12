from __future__ import annotations

import json
from pathlib import Path

from high_fidelity_schema_study.extractors.base import ExtractionRequest
from high_fidelity_schema_study.extractors.registry import extract_path


ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "testdata" / "zarr_phase14c_external"
METADATA_NAMES = {".zgroup", ".zarray", ".zattrs", ".zmetadata", "manifest.json", "README.md"}


def _extract(name: str):
    return extract_path(ExtractionRequest(str(CORPUS_ROOT / name)))


def test_phase14c_corpus_is_metadata_only_and_source_documented():
    manifest = json.loads((CORPUS_ROOT / "manifest.json").read_text(encoding="utf-8"))
    non_metadata = [
        path.relative_to(CORPUS_ROOT).as_posix()
        for path in CORPUS_ROOT.rglob("*")
        if path.is_file() and path.name not in METADATA_NAMES
    ]

    assert non_metadata == []
    assert len(manifest["cases"]) == 12
    assert manifest["generation_environment"]["zarr"] == "2.18.7"
    official = [case for case in manifest["cases"] if case["source"]["source_kind"] == "external_public_sdist"]
    assert len(official) == 2
    assert all(case["source"]["license"] == "MIT" for case in official)
    assert all(case["source"]["source_sha256"] for case in official)


def test_official_public_fixture_subset_and_orphan_are_structured():
    fixture = _extract("official_zarr_python_fixture_subset.zarr")
    orphan = _extract("official_zarr_python_utf8attrs_orphan.zarr")

    assert fixture.status == "success"
    assert fixture.schema is not None
    assert len(fixture.schema.fields) == 10
    assert {group["path"] for group in fixture.schema.groups} == {"/", "0"}
    assert orphan.status == "abstained"
    assert orphan.issues[0].code == "zarr_metadata_missing"


def test_library_produced_structured_and_xarray_metadata_are_supported():
    structured = _extract("zarr_library_structured_records.zarr")
    xarray = _extract("xarray_library_consolidated.zarr")

    assert structured.status == "success"
    assert structured.schema is not None
    structured_metadata = structured.schema.metadata["zarr_analysis"]["arrays"][0]["array_metadata"]
    assert structured_metadata["dtype"] == [["timestamp", "<i8"], ["quality", "|u1"], ["value", "<f4"]]

    assert xarray.status == "success"
    assert xarray.schema is not None
    analyses = {item["field_path"]: item for item in xarray.schema.metadata["zarr_analysis"]["arrays"]}
    assert analyses["temperature"]["dimensions"] == ["time", "latitude", "longitude"]
    assert "dimension_coordinate" in analyses["time"]["coordinate_roles"]


def test_library_derived_edge_cases_remain_explicit():
    dangling = _extract("xarray_library_dangling_coordinate.zarr")
    malformed = _extract("zarr_library_malformed_optional_attrs.zarr")

    assert dangling.status == "success"
    assert dangling.schema is not None
    gaps = dangling.schema.metadata["zarr_analysis"]["compatibility_gaps"]
    assert {gap["code"] for gap in gaps} == {"unresolved_coordinate_reference"}
    assert all(gap["evidence_refs"] for gap in gaps)

    assert malformed.status == "partial"
    assert malformed.schema is not None
    assert {issue.code for issue in malformed.issues} >= {"partial_extraction", "zarr_metadata_malformed"}
