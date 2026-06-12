from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_readme_describes_current_substrate_and_boundaries():
    text = _read("README.md")

    assert "registry-backed, evidence-grounded substrate" in text
    assert "not** an autonomous data agent" in text
    assert "## Architecture" in text
    assert "## Supported Formats" in text
    assert "## Post-Freeze Development" in text
    assert "## Current Results Snapshot" in text
    assert "## Bounded Limitations" in text
    assert "Phase 14: Zarr / Xarray-Compatible Scientific Array Extraction" in text
    assert "Recognized-but-unregistered formats" in text
    assert "Phase 14A: Zarr Directory-Store Intake" in text
    assert "Phase 14B: Zarr Compatibility Validation" in text
    assert "Phase 14C: External And Library Zarr Conformance" in text
    assert "chunk payloads, remote stores, Zarr v3" in text


def test_project_log_records_required_milestones_and_recommendation():
    text = _read("docs/project_log.md")

    assert "Deep Research Recommendation" in text
    assert "Phase 12 Deterministic Substrate" in text
    assert "Phase 13 NetCDF/CF Extension" in text
    assert "Phase 14 Recommendation" in text
    assert "Phase 14A Zarr Directory-Store Intake" in text
    assert "Phase 14B Zarr Compatibility Validation" in text
    assert "Phase 14C External And Library Zarr Conformance" in text
    assert "Do not turn the project into an autonomous, LLM-first data agent." in text


def test_phase14_plan_preserves_deterministic_first_gates():
    text = _read("docs/phase14_zarr_plan.md")

    assert text.startswith("# Phase 14: Zarr / Xarray-Compatible Scientific Array Extraction")
    for token in (".zgroup", ".zarray", ".zattrs", "dtype", "shape", "chunks", "compressor", "fill value"):
        assert token in text
    assert "Zarr v2 first" in text
    assert "semantic inference to create arrays, dimensions, coordinates, or physical fields" in text
    assert "Unsupported promotion count is `0`." in text
    assert "Generated artifacts contain no local absolute paths." in text
    assert "Frozen benchmark artifacts, paper result tables, figures, manuscript" in text
    assert "Status: Phase 14A, Phase 14B, and Phase 14C implemented." in text


def test_phase14a_report_records_bounded_result():
    text = _read("docs/phase14a_zarr_report.md")

    assert "local directory-store Zarr v2 metadata" in text
    assert "14-case" in text
    assert "Unsupported promotion count: `0`" in text
    assert "Chunk payloads" in text
    assert "Remote stores" in text
    assert "Zarr v3" in text


def test_phase14b_report_records_classified_compatibility_result():
    text = _read("docs/phase14b_zarr_compatibility_report.md")

    assert "17-case local compatibility corpus" in text
    assert "realistic compatibility corpus, not a downloaded representative ecosystem sample" in text
    assert "Supported and correctly extracted" in text
    assert "Unsupported features" in text
    assert "Malformed-store failures" in text
    assert "unsupported promotion count: `0`" in text
    assert "true bug count after fixes: `0`" in text


def test_phase14c_report_records_external_conformance_boundaries():
    text = _read("docs/phase14c_zarr_external_conformance_report.md")

    assert "metadata-only 12-case corpus" in text
    assert "Optional Cross-Parser Evidence" in text
    assert "Unexplained differences" in text
    assert "not a representative sample of the Zarr ecosystem" in text
    assert "True bug count" in text


def test_new_architecture_docs_do_not_contain_local_absolute_paths():
    for relative_path in (
        "README.md",
        "docs/project_log.md",
        "docs/phase14_zarr_plan.md",
        "docs/phase14a_zarr_report.md",
        "docs/phase14b_zarr_compatibility_report.md",
        "docs/phase14c_zarr_external_conformance_report.md",
    ):
        text = _read(relative_path)
        assert "C:\\Users\\" not in text
        assert "D:\\github\\" not in text
