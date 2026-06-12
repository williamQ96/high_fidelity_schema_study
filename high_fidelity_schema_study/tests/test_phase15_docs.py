from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_readme_records_parquet_support_and_boundary():
    text = _read("README.md")

    assert "Parquet / Arrow" in text
    assert "Phase 15A: Parquet / Arrow Metadata-First Extraction" in text
    assert "row values are not read" in text
    assert "Phase 15A Parquet/Arrow challenge" in text


def test_phase15a_report_records_metadata_first_result():
    text = _read("docs/phase15a_parquet_arrow_report.md")

    assert "Recursive Arrow schema extraction" in text
    assert "Arrow logical paths and Parquet physical paths" in text
    assert "Row-value abstention accuracy" in text
    assert "Unsupported promotion count" in text
    assert "bounded evidence, not broad ecosystem robustness" in text


def test_phase15a_docs_do_not_contain_local_absolute_paths():
    for path in (
        "docs/phase15a_parquet_arrow_report.md",
        "data/experiments/phase15a_parquet_arrow/report.json",
        "data/experiments/phase15a_parquet_arrow/report.md",
    ):
        text = _read(path)
        assert "C:\\Users\\" not in text
        assert "D:\\github\\" not in text
