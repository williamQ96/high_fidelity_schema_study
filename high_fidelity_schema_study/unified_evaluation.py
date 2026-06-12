from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict

from .evaluate_phase12 import evaluate_phase12
from .evaluate_phase13_netcdf_cf import evaluate_phase13
from .evaluate_phase14a_zarr import evaluate_phase14a
from .evaluate_phase14b_zarr_compatibility import evaluate_phase14b
from .evaluate_phase14c_zarr_external import evaluate_phase14c
from .evaluate_phase15a_parquet_arrow import evaluate_phase15a
from .evaluate_phase16a_json import evaluate_phase16a
from .evaluate_phase16b_xml import evaluate_phase16b
from .evaluate_phase17_unified_envelope import evaluate_phase17


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "experiments" / "phase18_unified_evaluation"
TRACKS: list[tuple[str, str, Callable[[], Dict[str, Any]]]] = [
    ("phase12_deterministic_substrate", "bounded_challenge", evaluate_phase12),
    ("phase13_netcdf_cf", "bounded_challenge", evaluate_phase13),
    ("phase14a_zarr", "bounded_challenge", evaluate_phase14a),
    ("phase14b_zarr_compatibility", "compatibility", evaluate_phase14b),
    ("phase14c_zarr_external_conformance", "external_conformance", lambda: evaluate_phase14c(enable_cross_parser=False)),
    ("phase15a_parquet_arrow", "bounded_challenge", evaluate_phase15a),
    ("phase16a_json_structure", "bounded_challenge", evaluate_phase16a),
    ("phase16b_xml_xsd_structure", "bounded_challenge", evaluate_phase16b),
    ("phase17_unified_schema_envelope", "cross_format_contract", evaluate_phase17),
]


def _load_frozen_references() -> list[Dict[str, Any]]:
    internal_path = ROOT / "data" / "derived" / "internal_baseline_report.json"
    retrieval_path = ROOT / "data" / "retrieval" / "external_candidate_pool" / "retrieval_report.json"
    internal = json.loads(internal_path.read_text(encoding="utf-8"))
    retrieval = json.loads(retrieval_path.read_text(encoding="utf-8"))
    return [
        {
            "track_id": "frozen_internal_baseline",
            "category": "frozen_artifact_paper",
            "source": "data/derived/internal_baseline_report.json",
            "metrics": internal["aggregate"]["metrics"],
            "status": "reference_only_not_rerun",
        },
        {
            "track_id": "frozen_retrieval_slice",
            "category": "frozen_artifact_paper",
            "source": "data/retrieval/external_candidate_pool/retrieval_report.json",
            "metrics": {
                item["artifact_name"]: item["metrics"]
                for item in retrieval["artifacts"]
            },
            "status": "reference_only_not_rerun",
        },
    ]


def evaluate_all_tracks(*, include_frozen_references: bool = True) -> Dict[str, Any]:
    tracks: list[Dict[str, Any]] = _load_frozen_references() if include_frozen_references else []
    for track_id, category, evaluator in TRACKS:
        report = evaluator()
        tracks.append(
            {
                "track_id": track_id,
                "category": category,
                "metrics": report["metrics"],
                "status": "evaluated",
                "claim_boundary": report.get("claim_boundary")
                or report.get("corpus_claim_boundary")
                or report.get("notes", []),
            }
        )
    categories: Dict[str, int] = {}
    for track in tracks:
        categories[track["category"]] = categories.get(track["category"], 0) + 1
    return {
        "experiment_id": "phase18_unified_evaluation",
        "track_count": len(tracks),
        "category_summary": dict(sorted(categories.items())),
        "tracks": tracks,
        "aggregate_score": None,
        "notes": [
            "No cross-track aggregate score is computed because track scopes and claim boundaries differ.",
            "Frozen Artifact Paper metrics are referenced only and are not rerun or rewritten.",
            "Bounded challenge, compatibility, external-conformance, and cross-format-contract tracks remain separate.",
        ],
    }


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Phase 18 Unified Evaluation",
        "",
        "Common entrypoint with explicit track-category separation and no cross-track aggregate score.",
        "",
        "| Track | Category | Status |",
        "| --- | --- | --- |",
    ]
    for track in report["tracks"]:
        lines.append(f"| {track['track_id']} | {track['category']} | {track['status']} |")
    lines.extend(["", "## Category Summary", ""])
    lines.extend(f"- `{key}`: {value}" for key, value in report["category_summary"].items())
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


def write_unified_evaluation_artifacts(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    report = report or evaluate_all_tracks()
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output_root / "report.md").write_text(_markdown(report), encoding="utf-8")
    return report
