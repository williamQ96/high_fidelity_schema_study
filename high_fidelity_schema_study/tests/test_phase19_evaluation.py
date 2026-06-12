from high_fidelity_schema_study.evaluate_phase19_agent_exports import evaluate_phase19


def test_phase19_metrics_are_complete():
    metrics = evaluate_phase19()["metrics"]

    assert metrics["case_count"] == 8
    assert metrics["capability_count"] == 7
    for key, value in metrics.items():
        if key.endswith("_accuracy") or key in {"claim_fidelity", "evidence_integrity", "provenance_completeness"}:
            assert value == 1.0, key
