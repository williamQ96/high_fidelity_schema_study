from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Any, Dict


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parent
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "experiments" / "phase20_release_readiness"
ABSOLUTE_PATH_RE = re.compile(
    r"(?<![A-Za-z])(?:[A-Za-z]:[\\/](?:Users|github)[\\/]|/(?:Users|home)/)",
    flags=re.IGNORECASE,
)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
LINK_AUDIT_PATHS = [
    "README.md",
    "log.md",
    "gui_demo/README.md",
    "demo_examples/README.md",
    "docs/demo_script.md",
    "docs/evaluation_plan.md",
    "docs/project_log.md",
    "docs/phase15a_parquet_arrow_report.md",
    "docs/phase16a_json_structure_report.md",
    "docs/phase16b_xml_xsd_report.md",
    "docs/phase17_unified_schema_envelope_report.md",
    "docs/phase18_unified_evaluation_report.md",
    "docs/phase19_agent_ready_exports_report.md",
    "docs/phase20_convergence_report.md",
    "docs/phase20_companion_engineering_appendix.md",
    "demo_examples/manifest.json",
    "demo_examples/README.md",
    "gui_demo/DESIGN.md",
]
REQUIRED_PATHS = [
    "README.md",
    "requirements.txt",
    "requirements-dev.txt",
    "docs/demo_script.md",
    "docs/evaluation_plan.md",
    "docs/project_log.md",
    "docs/phase15a_parquet_arrow_report.md",
    "docs/phase16a_json_structure_report.md",
    "docs/phase16b_xml_xsd_report.md",
    "docs/phase17_unified_schema_envelope_report.md",
    "docs/phase18_unified_evaluation_report.md",
    "docs/phase19_agent_ready_exports_report.md",
    "docs/phase20_convergence_report.md",
    "docs/phase20_companion_engineering_appendix.md",
    "data/experiments/phase17_unified_schema_envelope/report.json",
    "data/experiments/phase18_unified_evaluation/report.json",
    "data/experiments/phase19_agent_ready_exports/report.json",
]
REPOSITORY_REQUIRED_PATHS = [
    ".gitattributes",
    ".github/workflows/ci.yml",
]
FROZEN_PATHS = [
    "data/derived",
    "data/retrieval",
    "data/semantic_merged",
    "docs/paper_draft.md",
    "docs/paper_result_tables_2026-05-15.md",
    "docs/paper_result_tables_2026-05-15.json",
    "docs/figures",
    "docs/benchmark_freeze_2026-05-04.md",
    "docs/benchmark_freeze_2026-05-04.json",
]


def _readable_text_files(root: Path) -> list[Path]:
    return [
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".txt"}
    ]


def _broken_local_links(path: Path) -> list[str]:
    broken = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for target in MARKDOWN_LINK_RE.findall(text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        path_text = target.split("#", 1)[0].strip("<>")
        if not path_text:
            continue
        candidates = [path.parent / path_text, ROOT / path_text]
        if not any(candidate.exists() for candidate in candidates):
            broken.append(f"{path.relative_to(ROOT).as_posix()} -> {target}")
    return broken


def _absolute_path_matches(roots: list[Path]) -> list[str]:
    matches = []
    for root in roots:
        paths = [root] if root.is_file() else _readable_text_files(root)
        for path in paths:
            text = path.read_text(encoding="utf-8", errors="replace")
            if ABSOLUTE_PATH_RE.search(text):
                matches.append(path.relative_to(ROOT).as_posix())
    return sorted(set(matches))


def audit_release_readiness() -> Dict[str, Any]:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    missing.extend(
        path for path in REPOSITORY_REQUIRED_PATHS
        if not (REPOSITORY_ROOT / path).exists()
    )
    broken_links = []
    for relative_path in LINK_AUDIT_PATHS:
        path = ROOT / relative_path
        if path.exists():
            broken_links.extend(_broken_local_links(path))

    generated_absolute_matches = _absolute_path_matches([ROOT / "data" / "experiments"])
    documentation_absolute_matches = _absolute_path_matches(
        [
            ROOT / "README.md",
            ROOT / "log.md",
            ROOT / "docs",
            ROOT / "gui_demo" / "README.md",
            ROOT / "gui_demo" / "DESIGN.md",
            ROOT / "demo_examples",
        ]
    )

    completed = subprocess.run(
        ["git", "diff", "--name-only", "--", *FROZEN_PATHS],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    frozen_diffs = [line for line in completed.stdout.splitlines() if line.strip()]
    checks = {
        "required_paths_complete": not missing,
        "major_documentation_local_links_resolve": not broken_links,
        "generated_artifacts_have_no_local_absolute_paths": not generated_absolute_matches,
        "documentation_has_no_local_absolute_paths": not documentation_absolute_matches,
        "frozen_artifact_paths_unchanged": not frozen_diffs,
    }
    return {
        "experiment_id": "phase20_release_readiness",
        "ready": all(checks.values()),
        "checks": checks,
        "details": {
            "missing_required_paths": missing,
            "broken_local_links": broken_links,
            "generated_absolute_path_matches": generated_absolute_matches,
            "documentation_absolute_path_matches": documentation_absolute_matches,
            "frozen_path_diffs": frozen_diffs,
        },
        "boundaries": [
            "Release readiness does not expand bounded challenge claims into broad ecosystem robustness.",
            "The audit does not modify frozen artifacts.",
        ],
    }


def write_release_readiness_artifacts(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    report = report or audit_release_readiness()
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Phase 20 Release Readiness",
        "",
        f"Ready: `{'yes' if report['ready'] else 'no'}`",
        "",
        "| Check | Result |",
        "| --- | --- |",
    ]
    lines.extend(f"| {key} | {'pass' if value else 'fail'} |" for key, value in report["checks"].items())
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {item}" for item in report["boundaries"])
    (output_root / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
