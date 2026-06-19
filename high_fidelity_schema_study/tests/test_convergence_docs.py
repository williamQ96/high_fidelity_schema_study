from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_convergence_docs_record_release_boundaries():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    report = (ROOT / "docs" / "phase20_convergence_report.md").read_text(encoding="utf-8")
    demo = (ROOT / "docs" / "demo_script.md").read_text(encoding="utf-8")

    assert "Phases 18-20: Evaluation, Agent Exports, And Convergence" in readme
    assert "aggregate score is `null`" in readme
    assert "181 passed" in report
    assert "agents cannot silently promote canonical claims" in report
    assert "agent-export" in demo
    assert "evaluate --scope all" in demo
