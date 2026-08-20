from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_research_dashboard_contains_current_research_views():
    html = (ROOT / "gui_demo" / "research_dashboard.html").read_text(encoding="utf-8")

    for view in ("overview", "methodology", "ndp50", "evidence", "readiness", "human"):
        assert f'data-view="{view}"' in html
        assert f'data-section="{view}"' in html
    assert "Four frozen architecture variants" in html
    assert "NDP-50 corpus" in html
    assert "Readiness gates" in html
    assert "Swathi · F01–F16" in html
    assert "What this dashboard will never show" in html
    assert "index.html#extract" in html


def test_research_dashboard_loads_live_aggregate_api_and_supports_interaction():
    script = (ROOT / "gui_demo" / "research_dashboard.js").read_text(encoding="utf-8")

    assert 'fetch("/api/research-status"' in script
    assert "renderVariants" in script
    assert "renderNdp50" in script
    assert "renderReadiness" in script
    assert "renderHumanWorkflow" in script
    assert "blocker-filter" in script
    assert "location.hash" in script
    assert "showModal" in script


def test_research_dashboard_is_responsive_and_reduced_motion_safe():
    css = (ROOT / "gui_demo" / "research_dashboard.css").read_text(encoding="utf-8")

    assert "@media (max-width: 860px)" in css
    assert "@media (max-width: 620px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ".view.active" in css
    assert ".gate-matrix" in css
    assert ".split-ring" in css
