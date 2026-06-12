from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .agent_exports import export_agent_bundle, export_capability_registry
from .evaluate_phase17_unified_envelope import evaluate_phase17


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = ROOT / "data" / "experiments" / "phase19_agent_ready_exports"


def _ratio(hit: int, total: int) -> float:
    return round(hit / total, 4) if total else 0.0


def evaluate_phase19() -> Dict[str, Any]:
    phase17 = evaluate_phase17()
    bundles = []
    counters = {key: [0, 0] for key in ("policy", "claims", "evidence", "provenance", "context", "actions")}
    for case in phase17["cases"]:
        bundle = export_agent_bundle(case["envelope"])
        evidence_ids = {item["evidence_id"] for item in bundle["evidence_records"]}
        accepted_claims = [
            claim
            for claim in bundle["claim_records"]
            if claim["state"] in {"observed", "declared", "derived", "supported"}
        ]

        def check(name: str, value: bool) -> bool:
            counters[name][0] += int(value)
            counters[name][1] += 1
            return value

        checks = {
            "policy": check(
                "policy",
                bundle["policy"]["canonical_mutation_allowed"] is False
                and bundle["policy"]["silent_claim_promotion_allowed"] is False,
            ),
            "claims": check("claims", bundle["claim_records"] == case["envelope"]["claims"]),
            "evidence": check(
                "evidence",
                all(
                    claim.get("evidence_refs")
                    and all(ref in evidence_ids for ref in claim["evidence_refs"])
                    for claim in accepted_claims
                ),
            ),
            "provenance": check(
                "provenance",
                bool(bundle["provenance_graph"]["entities"])
                and bool(bundle["provenance_graph"]["activities"])
                and bool(bundle["provenance_graph"]["agents"]),
            ),
            "context": check(
                "context",
                bundle["retrieval_context"]["format"] == case["envelope"]["identity"]["file_format"],
            ),
            "actions": check(
                "actions",
                all(item["effect"] != "canonical_mutation" for item in bundle["requestable_actions"]),
            ),
        }
        bundles.append({"case_id": case["case_id"], "checks": checks, "bundle": bundle})
    registry = export_capability_registry()
    return {
        "experiment_id": "phase19_agent_ready_exports",
        "metrics": {
            "case_count": len(bundles),
            "policy_guard_accuracy": _ratio(*counters["policy"]),
            "claim_fidelity": _ratio(*counters["claims"]),
            "evidence_integrity": _ratio(*counters["evidence"]),
            "provenance_completeness": _ratio(*counters["provenance"]),
            "retrieval_context_accuracy": _ratio(*counters["context"]),
            "bounded_action_accuracy": _ratio(*counters["actions"]),
            "capability_count": len(registry["capabilities"]),
        },
        "capability_registry": registry,
        "bundles": bundles,
        "notes": [
            "Agent exports are read-only projections and noncanonical context artifacts.",
            "Agents may inspect, suggest, or request reruns but cannot silently promote canonical claims.",
        ],
    }


def _markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Phase 19 Agent-Ready Exports",
        "",
        "Read-only deterministic exports for future bounded agents.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in report["metrics"].items():
        lines.append(f"| {key} | {value:.4f} |" if isinstance(value, float) else f"| {key} | {value} |")
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines) + "\n"


def write_phase19_artifacts(
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    report = report or evaluate_phase19()
    bundles_root = output_root / "bundles"
    bundles_root.mkdir(parents=True, exist_ok=True)
    for item in report["bundles"]:
        (bundles_root / f"{item['case_id']}.json").write_text(
            json.dumps(item["bundle"], indent=2) + "\n", encoding="utf-8"
        )
    (output_root / "capability_registry.json").write_text(
        json.dumps(report["capability_registry"], indent=2) + "\n", encoding="utf-8"
    )
    summary = {key: value for key, value in report.items() if key != "bundles"}
    summary["bundles"] = [
        {"case_id": item["case_id"], "checks": item["checks"]}
        for item in report["bundles"]
    ]
    (output_root / "report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output_root / "report.md").write_text(_markdown(report), encoding="utf-8")
    return report
