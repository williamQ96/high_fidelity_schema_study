from high_fidelity_schema_study.release_audit import (
    ABSOLUTE_PATH_RE,
    REPOSITORY_REQUIRED_PATHS,
    REQUIRED_PATHS,
    audit_release_readiness,
)


def test_release_readiness_checks_pass():
    report = audit_release_readiness()

    assert report["ready"] is True
    assert all(report["checks"].values())
    assert "requirements.txt" in REQUIRED_PATHS
    assert "requirements-dev.txt" in REQUIRED_PATHS
    assert "docs/phase20_companion_engineering_appendix.md" in REQUIRED_PATHS
    assert ".gitattributes" in REPOSITORY_REQUIRED_PATHS
    assert ".github/workflows/ci.yml" in REPOSITORY_REQUIRED_PATHS
    assert "data/experiments/phase20_release_readiness/report.json" not in REQUIRED_PATHS


def test_absolute_path_detection_covers_windows_and_unix_homes():
    assert ABSOLUTE_PATH_RE.search(r"D:\github\example\report.json")
    assert ABSOLUTE_PATH_RE.search("C:/Users/example/report.json")
    assert ABSOLUTE_PATH_RE.search("/Users/example/report.json")
    assert ABSOLUTE_PATH_RE.search("/home/example/report.json")
    assert ABSOLUTE_PATH_RE.search("https://example.org/report.json") is None
