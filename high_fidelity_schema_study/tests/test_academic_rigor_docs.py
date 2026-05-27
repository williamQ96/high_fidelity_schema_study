import re
from pathlib import Path


def read_doc(name: str) -> str:
    return Path("high_fidelity_schema_study/docs", name).read_text(encoding="utf-8")


def test_academic_rigor_audit_contains_required_claim_boundaries():
    text = read_doc("academic_rigor_audit.md")

    assert "Evidence adequacy measures auditability, not truth." in text
    assert "Schema-enhanced artifacts improve Recall@1 on the planted 10-query" in text
    assert "Time-axis evaluation remains the clearest non-final gap." in text
    assert "Disallowed wording" in text


def test_time_axis_gap_adjudication_freezes_current_facts():
    text = read_doc("time_axis_gap_adjudication.md")

    assert "Aggregate `time_axis_accuracy` | `0.6667`" in text
    assert "Time-series family `time_axis_accuracy` | `0.0000`" in text
    assert "Error-mode count for `time_axis_mismatch` | `3`" in text
    assert "Do not force a metric change" in text


def test_references_separate_verified_and_caution_entries():
    text = read_doc("references.md")

    assert "# Verified Artifact Bibliography" in text
    assert "Status: `verified`" in text
    assert "Status: `verification_needed`" in text
    assert "`Auctus`" in text
    assert "`Menick2022VerifiedQuotes`" in text


def test_artifact_handoff_preserves_known_limits_and_commands():
    text = read_doc("artifact_handoff.md")

    assert "python -m http.server 8765" in text
    assert "python -m pytest high_fidelity_schema_study\\tests" in text
    assert "External retrieval qrels are planted single-positive judgments." in text
    assert "Evidence adequacy and provenance establish auditability, not semantic truth." in text
    assert "98%" in text


def test_gui_visual_qa_records_smoke_result():
    text = read_doc("gui_visual_qa.md")

    assert "Status: passed for Artifact Paper demo readiness." in text
    assert "#fields" in text
    assert "table-header overlap" in text
    assert "mobile header status now wraps" in text


def test_paper_draft_uses_only_verified_core_citation_keys():
    paper = read_doc("paper_draft.md")
    references = read_doc("references.md")
    verified_section = references.split("## Use With Caution", maxsplit=1)[0]
    verified_keys = set(re.findall(r"^- `([^`]+)`", verified_section, flags=re.MULTILINE))

    citation_groups = re.findall(
        r"(?<!!)\[([A-Za-z][A-Za-z0-9]+(?:; [A-Za-z][A-Za-z0-9]+)*)\]",
        paper,
    )
    used_keys = {
        key.strip()
        for group in citation_groups
        for key in group.split(";")
    }

    caution_keys = {"Auctus", "AttributedQA"}
    assert caution_keys.isdisjoint(used_keys)
    assert used_keys
    assert used_keys <= verified_keys


def test_final_convergence_report_records_evidence_and_limits():
    text = read_doc("final_convergence_report.md")

    assert "98%" in text
    assert "pytest" in text
    assert "57 passed" in text
    assert "planted single-positive qrels" in text
    assert "time_axis_accuracy = 0.6667" in text
    assert "Evidence adequacy != correctness" in text
