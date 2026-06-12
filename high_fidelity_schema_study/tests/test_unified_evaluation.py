from __future__ import annotations

import json
import sys

from high_fidelity_schema_study import cli
from high_fidelity_schema_study.unified_evaluation import evaluate_all_tracks


def test_unified_evaluation_keeps_track_categories_separate():
    report = evaluate_all_tracks()

    assert report["track_count"] == 11
    assert report["aggregate_score"] is None
    assert report["category_summary"] == {
        "bounded_challenge": 6,
        "compatibility": 1,
        "cross_format_contract": 1,
        "external_conformance": 1,
        "frozen_artifact_paper": 2,
    }
    frozen = [track for track in report["tracks"] if track["category"] == "frozen_artifact_paper"]
    assert all(track["status"] == "reference_only_not_rerun" for track in frozen)


def test_unified_evaluation_extension_scope_excludes_frozen_references():
    report = evaluate_all_tracks(include_frozen_references=False)

    assert report["track_count"] == 9
    assert "frozen_artifact_paper" not in report["category_summary"]
    assert all(track["status"] == "evaluated" for track in report["tracks"])


def test_unified_evaluation_cli(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["schema-study", "evaluate", "--scope", "extensions"])

    cli.main()
    payload = json.loads(capsys.readouterr().out)

    assert payload["track_count"] == 9
    assert payload["aggregate_score"] is None
