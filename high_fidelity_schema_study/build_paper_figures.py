from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


ROOT = Path(__file__).resolve().parent
DOCS_ROOT = ROOT / "docs"
FIGURES_ROOT = DOCS_ROOT / "figures"
TABLES_PATH = DOCS_ROOT / "paper_result_tables_2026-05-15.json"
INDEX_PATH = FIGURES_ROOT / "README.md"


FIGURE_SPECS = [
    {
        "file": "figure_1_benchmark_slice.svg",
        "title": "Figure 1. Frozen benchmark slice",
        "table": "benchmark_slice",
        "label": "measure",
        "value": "value",
        "note": "Counts from the frozen benchmark contract.",
    },
    {
        "file": "figure_2_internal_baseline_accuracy.svg",
        "title": "Figure 2. Internal deterministic extraction metrics",
        "table": "internal_baseline_aggregate",
        "label": "metric",
        "value": "value",
        "include": [
            "physical_completeness",
            "physical_accuracy",
            "logical_accuracy",
            "semantic_accuracy",
            "unit_accuracy",
            "time_axis_accuracy",
        ],
        "max_value": 1.0,
        "note": "Accuracy and completeness metrics over the 9-dataset internal pilot.",
    },
    {
        "file": "figure_3_evidence_adequacy.svg",
        "title": "Figure 3. Evidence adequacy ratios",
        "table": "evidence_adequacy_summary",
        "label": "metric",
        "value": "value",
        "include": [
            "Derived fields with source evidence",
            "Derived fields with confidence",
            "Unit claims with unit evidence",
            "Accepted semantic merges with support",
            "Unsupported accepted semantic merges",
        ],
        "max_value": 1.0,
        "note": "Evidence coverage is measured separately from label correctness.",
    },
    {
        "file": "figure_4_retrieval_metrics.svg",
        "title": "Figure 4. Retrieval metrics by artifact",
        "table": "retrieval_metrics",
        "label": "system",
        "value": "recall_at_1",
        "max_value": 1.0,
        "note": "Recall@1 over planted single-positive qrels in the 16-file external pool.",
    },
    {
        "file": "figure_5_semantic_merge_delta.svg",
        "title": "Figure 5. Semantic merge logical-accuracy delta",
        "table": "semantic_merge_dataset_delta",
        "label": "dataset_id",
        "value": "logical_accuracy_delta",
        "max_value": 0.35,
        "note": "Positive values indicate evidence-backed logical-label improvements after semantic merge.",
    },
]


def load_tables() -> Dict[str, Any]:
    return json.loads(TABLES_PATH.read_text(encoding="utf-8"))["tables"]


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def filtered_rows(rows: Sequence[Dict[str, Any]], label_key: str, include: Iterable[str] | None) -> List[Dict[str, Any]]:
    if include is None:
        return list(rows)
    wanted = list(include)
    lookup = {str(row[label_key]): row for row in rows}
    return [lookup[label] for label in wanted if label in lookup]


def short_label(label: str) -> str:
    replacements = {
        "External retrieval candidate files": "external candidates",
        "Promoted external target files": "external targets",
        "External distractor files": "distractors",
        "Internal pilot datasets": "internal pilot",
        "Current retrieval systems": "retrieval systems",
        "Locked external field-subset regression groups": "locked regressions",
        "Derived fields with source evidence": "fields with evidence",
        "Derived fields with confidence": "fields with confidence",
        "Unit claims with unit evidence": "unit claims with evidence",
        "Accepted semantic merges with support": "accepted merges supported",
        "Unsupported accepted semantic merges": "unsupported accepted merges",
        "schema_enhanced_deterministic": "schema deterministic",
        "schema_enhanced_semantic_merged": "schema semantic merged",
    }
    return replacements.get(label, label)


def make_bar_svg(
    title: str,
    rows: Sequence[Dict[str, Any]],
    label_key: str,
    value_key: str,
    max_value: float | None,
    note: str,
) -> str:
    width = 920
    left = 260
    right = 120
    top = 74
    row_h = 38
    bar_h = 18
    chart_w = width - left - right
    height = top + row_h * len(rows) + 70
    values = [float(row[value_key]) for row in rows]
    scale_max = max_value if max_value is not None else max(values or [1.0])
    if scale_max <= 0:
        scale_max = 1.0

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        "<style>",
        ".title{font:700 22px Arial,Helvetica,sans-serif;fill:#18201c}",
        ".note{font:13px Arial,Helvetica,sans-serif;fill:#5f6b63}",
        ".label{font:13px Arial,Helvetica,sans-serif;fill:#2f3b34}",
        ".value{font:13px Arial,Helvetica,sans-serif;fill:#18201c}",
        ".track{fill:#e8ece7}",
        ".bar{fill:#1f7a5a}",
        ".zero{stroke:#9a3f35;stroke-width:2}",
        "</style>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="24" y="34" class="title">{escape(title)}</text>',
        f'<text x="24" y="56" class="note">{escape(note)}</text>',
    ]

    for idx, row in enumerate(rows):
        y = top + idx * row_h
        label = short_label(str(row[label_key]))
        value = float(row[value_key])
        bar_w = max(0.0, min(chart_w, chart_w * value / scale_max))
        parts.extend(
            [
                f'<text x="24" y="{y + 15}" class="label">{escape(label)}</text>',
                f'<rect x="{left}" y="{y}" width="{chart_w}" height="{bar_h}" rx="4" class="track"/>',
                f'<rect x="{left}" y="{y}" width="{bar_w:.2f}" height="{bar_h}" rx="4" class="bar"/>',
                f'<text x="{left + chart_w + 16}" y="{y + 15}" class="value">{escape(fmt(row[value_key]))}</text>',
            ]
        )
        if value == 0:
            parts.append(f'<line x1="{left}" y1="{y - 2}" x2="{left}" y2="{y + bar_h + 2}" class="zero"/>')

    parts.extend(
        [
            f'<text x="24" y="{height - 24}" class="note">Source: docs/paper_result_tables_2026-05-15.json</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


def build_figures() -> List[Dict[str, str]]:
    tables = load_tables()
    FIGURES_ROOT.mkdir(parents=True, exist_ok=True)
    built = []
    for spec in FIGURE_SPECS:
        rows = filtered_rows(
            tables[spec["table"]],
            spec["label"],
            spec.get("include"),
        )
        svg = make_bar_svg(
            title=spec["title"],
            rows=rows,
            label_key=spec["label"],
            value_key=spec["value"],
            max_value=spec.get("max_value"),
            note=spec["note"],
        )
        path = FIGURES_ROOT / spec["file"]
        path.write_text(svg, encoding="utf-8")
        built.append(
            {
                "title": spec["title"],
                "file": spec["file"],
                "note": spec["note"],
            }
        )
    return built


def write_index(figures: Sequence[Dict[str, str]]) -> None:
    lines = [
        "# Paper Figures",
        "",
        "These SVG figures are generated from `docs/paper_result_tables_2026-05-15.json` by `python -m high_fidelity_schema_study.build_paper_figures`.",
        "",
        "They are paper-facing summaries, not new experiment outputs.",
        "",
    ]
    for figure in figures:
        lines.extend(
            [
                f"## {figure['title']}",
                "",
                f"![{figure['title']}]({figure['file']})",
                "",
                figure["note"],
                "",
            ]
        )
    INDEX_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    figures = build_figures()
    write_index(figures)
    print(f"Built {len(figures)} figures in {FIGURES_ROOT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
