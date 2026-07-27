from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping


DESIGN_SCHEMA_VERSION = "ndp50-cpa-design/v1"
SCREEN_SCHEMA_VERSION = "ndp50-cpa-applicability-screen/v1"
PRIMARY_OUTCOME_ID = (
    "correct_accepted_applicable_claim_rate_gain_per_dataset"
)
PRIMARY_CONTRASTS = [
    {
        "contrast_id": "deterministic-vs-zero",
        "arm_a": "deterministic_only",
        "arm_b": "zero_shot_dataset_level",
    },
    {
        "contrast_id": "zero-vs-verified",
        "arm_a": "zero_shot_dataset_level",
        "arm_b": (
            "zero_shot_byte_identical_response_plus_"
            "deterministic_verification"
        ),
    },
]

_METRIC_CONTRACT = {
    "scoring_unit": "field_path_x_evaluated_property_slot",
    "evaluated_properties": [
        "physical_type",
        "logical_type",
        "semantic_type",
        "unit",
    ],
    "scoring_population": (
        "resource_cases_approved_applicable_by_frozen_CPA_consensus"
    ),
    "canonicalization": (
        "frozen_vocabulary_canonical_values_and_predeclared_aliases_only"
    ),
    "exact_match_required_after_canonicalization": True,
    "gold_states": [
        "applicable_known",
        "applicable_unknown_or_oov",
        "not_applicable",
    ],
    "prediction_states": [
        "accepted_known",
        "explicit_oov_or_abstention",
        "missing_due_to_execution_failure",
    ],
    "definitions": {
        "micro_f1": (
            "micro_averaged_label_value_F1_over_applicable_known_slots"
        ),
        "macro_f1": (
            "unweighted_mean_of_defined_per_label_F1_values_with_gold_support"
        ),
        "per_label_f1": (
            "label_value_F1_with_gold_support_prediction_support_and_counts"
        ),
        "out_of_vocabulary_rate": (
            "applicable_unknown_or_oov_gold_slots_divided_by_all_applicable_gold_slots"
        ),
        "verified_coverage": (
            "exactly_correct_accepted_claims_passing_frozen_verification_divided_by_applicable_known_gold_slots"
        ),
        "selective_risk": (
            "incorrect_accepted_known_claims_divided_by_all_accepted_known_claims"
        ),
        "unsupported_claim_rate": (
            "accepted_known_claims_without_valid_approved_support_divided_by_all_accepted_known_claims"
        ),
        "evidence_reference_validity": (
            "accepted_known_claims_with_resolvable_allowed_evidence_references_divided_by_all_accepted_known_claims"
        ),
        "calls": "physical_backend_calls_excluding_cache_replay",
        "tokens": "backend_reported_or_frozen_tokenizer_input_plus_output_tokens",
        "latency": "wall_clock_seconds_per_physical_backend_call",
        "cost": "frozen_price_schedule_applied_to_recorded_token_and_call_usage",
    },
    "undefined_denominator_policy": (
        "emit_null_with_explicit_zero_denominator_and_never_impute_zero"
    ),
    "required_support_counts": True,
}

_ANALYSIS_CONTRACT = {
    "primary_unit": "dataset",
    "resource_cases_clustered_within_dataset": True,
    "primary_outcome_id": PRIMARY_OUTCOME_ID,
    "primary_outcome_definition": (
        "Within each dataset and arm, divide exactly correct accepted claims "
        "for gold-applicable-known slots by all gold-applicable-known slots, "
        "then form the paired arm_b_minus_arm_a difference."
    ),
    "dataset_aggregation": (
        "pool_registered_slots_within_dataset_then_compute_one_dataset_score"
    ),
    "effect_direction": "arm_b_minus_arm_a",
    "primary_contrasts": PRIMARY_CONTRASTS,
    "primary_contrasts_require_holm_adjustment": True,
    "familywise_alpha": 0.05,
    "primary_test": {
        "method": (
            "two_sided_paired_sign_flip_on_dataset_level_mean_difference"
        ),
        "exact_max_nonzero_pairs": 24,
        "monte_carlo_repetitions_above_exact_max": 1_000_000,
        "monte_carlo_seed_text": "ndp50-cpa-sign-flip-v1",
        "monte_carlo_p_value_correction": "plus_one_numerator_and_denominator",
        "zero_difference_policy": (
            "retain_in_total_pair_count_exclude_from_effective_sign_patterns"
        ),
    },
    "multiplicity": {
        "method": "holm_step_down",
        "family": "two_co_primary_contrasts",
        "decision_basis": "holm_adjusted_two_sided_p_values",
    },
    "dataset_bootstrap_repetitions": 10000,
    "bootstrap_seed_text": "ndp50-cpa-dataset-bootstrap-v1",
    "confidence_interval": {
        "level": 0.95,
        "method": "fixed_seed_nonparametric_dataset_bootstrap_percentile",
        "estimand": "mean_dataset_level_paired_difference",
    },
    "missingness_policy": {
        "frozen_CPA_inapplicable_cases": (
            "exclude_from_CPA_estimand_but_report_by_reason"
        ),
        "missing_or_invalid_gold": "block_execution_before_model_calls",
        "transport_timeout_or_parser_failure": (
            "retain_registered_slot_in_denominator_as_no_correct_accepted_claim"
        ),
        "explicit_abstention_or_oov": (
            "retain_registered_slot_in_denominator_as_no_correct_accepted_claim"
        ),
        "no_accepted_claims_selective_risk": (
            "null_with_zero_denominator_not_zero_risk"
        ),
        "pairwise_dataset_comparability": (
            "require_both_registered_arms_and_report_every_exclusion"
        ),
        "post_outcome_case_deletion": False,
    },
}


def registered_metric_contract() -> Dict[str, Any]:
    return deepcopy(_METRIC_CONTRACT)


def registered_analysis_contract() -> Dict[str, Any]:
    return deepcopy(_ANALYSIS_CONTRACT)


class NDPCPADesignError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_cpa_design(
    opportunity_manifest_path: Path,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    manifest = _load_json(opportunity_manifest_path)
    if manifest.get("schema_version") != (
        "ndp50-semantic-opportunity-manifest/v1"
    ):
        raise NDPCPADesignError("unexpected opportunity manifest schema")
    cases = [
        item
        for item in manifest["cases"]
        if item["cpa_applicability_status"]
        == "requires_manual_relation_and_subject_assessment"
    ]
    if any(item["split"] == "test" for item in cases):
        raise NDPCPADesignError("CPA design must not contain test cases")
    case_ids = [item["case_id"] for item in cases]
    if len(case_ids) != len(set(case_ids)):
        raise NDPCPADesignError("duplicate CPA case IDs")
    split_counts = Counter(item["split"] for item in cases)
    manifest_binding = {
        "file": opportunity_manifest_path.name,
        "sha256": _sha256_file(opportunity_manifest_path),
    }
    screening_cases = [
        {
            "case_id": item["case_id"],
            "dataset_id": item["dataset_id"],
            "resource_id": item["resource_id"],
            "split": item["split"],
            "field_paths": item["field_paths"],
            "relational_table_applicable": None,
            "single_subject_column_supported": None,
            "subject_column_field_path": None,
            "property_annotation_applicable": None,
            "rationale": None,
            "evidence_refs": [],
        }
        for item in cases
    ]
    screen = {
        "schema_version": SCREEN_SCHEMA_VERSION,
        "protocol_version": "ndp50-external-validation-protocol/v1",
        "annotation_stage": "independent_pre_model_screen",
        "annotator_id": "replace-with-pseudonymous-non-developer-id",
        "annotator_role": "replace-with-qualified-annotator-role",
        "qualification_summary": None,
        "conflict_of_interest_declared": None,
        "submission_id": "replace-with-stable-unique-id",
        "developer_participation": False,
        "model_outputs_visible": False,
        "opportunity_manifest": manifest_binding,
        "instructions": [
            "Judge applicability before any CPA prompt or model output is exposed.",
            "A case is CPA-applicable only when it is a relational table, one subject column is supported, and target property annotation is meaningful.",
            "Ambiguous subject columns remain in the general semantic study but are not silently forced into the CPA denominator.",
            "Every non-null decision requires a rationale and locatable approved evidence.",
        ],
        "cases": screening_cases,
    }
    design = {
        "schema_version": DESIGN_SCHEMA_VERSION,
        "protocol_version": "ndp50-external-validation-protocol/v1",
        "status": "draft_blocked_on_independent_applicability_and_prompt_freeze",
        "created_at": _utc_now(),
        "literature_basis": {
            "title": "Column Property Annotation using Large Language Models",
            "doi": "10.1007/978-3-031-78952-6_6",
            "adaptation_boundary": (
                "CPA is a tabular sub-study and is not treated as equivalent "
                "to general scientific schema extraction."
            ),
        },
        "opportunity_manifest": manifest_binding,
        "candidate_counts": {
            "resource_cases": len(cases),
            "dataset_clusters": len({item["dataset_id"] for item in cases}),
            "split_case_counts": dict(sorted(split_counts.items())),
        },
        "applicability_contract": {
            "required_independent_annotators": 2,
            "required_role_coverage": [
                "one_domain_or_scientific_metadata_curator",
                "one_annotation_methodologist",
            ],
            "qualification_and_conflict_declaration_required": True,
            "screen_template_schema": SCREEN_SCHEMA_VERSION,
            "consensus_only_after_both_submission_hashes_freeze": True,
            "model_outputs_visible_during_screening": False,
            "applicable_if_all": [
                "relational_table_applicable",
                "single_subject_column_supported",
                "property_annotation_applicable",
            ],
            "ambiguous_subject_policy": "exclude_from_CPA_only; retain_in_general_semantic_study",
            "primary_analysis_cluster": "dataset_id",
        },
        "planned_arms": [
            "deterministic_only",
            "zero_shot_dataset_level",
            "zero_shot_byte_identical_response_plus_deterministic_verification",
            "one_shot_development_similarity_selected",
            "five_shot_development_similarity_selected",
        ],
        "demonstration_policy": {
            "source_split": "development_only",
            "selection": "frozen_similarity_ranking",
            "validation_or_test_as_demonstration": False,
            "fine_tuning": "not_in_primary_pilot; requires separate registration",
        },
        "row_sampling_sensitivity": [
            "head",
            "fixed_seed_stratified",
            "fixed_seed_adaptive",
        ],
        "metrics": [
            "micro_f1",
            "macro_f1",
            "per_label_f1",
            "out_of_vocabulary_rate",
            "prompt_sensitivity",
            "cross_domain_transfer",
            "verified_coverage",
            "selective_risk",
            "unsupported_claim_rate",
            "evidence_reference_validity",
            "calls",
            "tokens",
            "latency",
            "cost",
        ],
        "metric_contract": registered_metric_contract(),
        "analysis": registered_analysis_contract(),
        "freeze_blockers": [
            "two independent applicability screens and consensus are absent",
            "target property vocabulary is not frozen",
            "prompt texts and serialization are not frozen",
            "similarity model/ranking and demonstrations are not frozen",
            "semantic backend registry is not frozen",
            "independent gold is absent",
        ],
    }
    return design, screen


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the draft NDP-50 CPA design and neutral screen."
    )
    parser.add_argument("--opportunity-manifest", type=Path, required=True)
    parser.add_argument("--design-output", type=Path, required=True)
    parser.add_argument("--screen-output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    design, screen = build_cpa_design(args.opportunity_manifest)
    _write_json(args.design_output, design)
    _write_json(args.screen_output, screen)
    print(json.dumps(design["candidate_counts"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
