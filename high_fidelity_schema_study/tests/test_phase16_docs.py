from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_readme_records_json_support_and_boundary():
    text = _read("README.md")

    assert "JSON / JSON Lines" in text
    assert "Phase 16A: Conservative JSON Structure Extraction" in text
    assert "Observed structure is sample-bounded" in text
    assert "Phase 16A JSON challenge" in text


def test_phase16a_report_records_declared_observed_boundary():
    text = _read("docs/phase16a_json_structure_report.md")

    assert "Declared-versus-observed type conflicts" in text
    assert "not universal schema truth" in text
    assert "Unsupported promotion count is `0`" in text
    assert "XML/XSD remains deferred" in text


def test_phase16a_docs_and_artifacts_do_not_contain_local_absolute_paths():
    for path in (
        "docs/phase16a_json_structure_report.md",
        "data/experiments/phase16a_json_structure/report.json",
        "data/experiments/phase16a_json_structure/report.md",
    ):
        text = _read(path)
        assert "C:\\Users\\" not in text
        assert "D:\\github\\" not in text
