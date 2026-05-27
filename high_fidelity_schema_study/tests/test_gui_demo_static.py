from pathlib import Path


def test_gui_demo_contains_core_inspection_views():
    html = Path("high_fidelity_schema_study/gui_demo/index.html").read_text(encoding="utf-8")

    assert 'data-view="overview"' in html
    assert 'data-view="evidence"' in html
    assert 'data-view="fields"' in html
    assert 'data-view="semantic"' in html
    assert 'data-view="retrieval"' in html
    assert 'data-view="provenance"' in html
    assert 'data-view="extract"' in html
    assert "renderFields(data)" in html
    assert "setupExtractor()" in html
    assert "/api/extract-schema" in html
    assert "field_results" in html
    assert "Artifact Boundary" in html
    assert "time-axis gap" in html
    assert "location.hash" in html
    assert "history.replaceState" in html


def test_gui_demo_documents_artifact_boundary():
    readme = Path("high_fidelity_schema_study/gui_demo/README.md").read_text(encoding="utf-8")

    assert "inspection layer over frozen artifacts" in readme
    assert "scratch workbench" in readme
    assert "Artifact Boundary banner" in readme
    assert "Fields:" in readme
    assert "Extract:" in readme
    assert "python -m high_fidelity_schema_study.gui_demo.server 8765" in readme
    assert "python -m http.server 8765" in readme


def test_gui_demo_mobile_status_wraps_in_css():
    html = Path("high_fidelity_schema_study/gui_demo/index.html").read_text(encoding="utf-8")

    assert "@media (max-width: 860px)" in html
    assert ".status" in html
    assert "white-space: normal" in html
