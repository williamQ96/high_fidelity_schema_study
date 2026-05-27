from pathlib import Path

from high_fidelity_schema_study.build_paper_figures import build_figures, write_index


def test_build_paper_figures_outputs_svg_and_index():
    figures = build_figures()
    write_index(figures)

    figure_root = Path("high_fidelity_schema_study/docs/figures")
    expected_files = {
        "figure_1_benchmark_slice.svg",
        "figure_2_internal_baseline_accuracy.svg",
        "figure_3_evidence_adequacy.svg",
        "figure_4_retrieval_metrics.svg",
        "figure_5_semantic_merge_delta.svg",
    }

    assert {figure["file"] for figure in figures} == expected_files
    for filename in expected_files:
        text = (figure_root / filename).read_text(encoding="utf-8")
        assert text.startswith("<svg")
        assert "docs/paper_result_tables_2026-05-15.json" in text

    index = (figure_root / "README.md").read_text(encoding="utf-8")
    assert "These SVG figures are generated" in index
    assert "figure_4_retrieval_metrics.svg" in index
