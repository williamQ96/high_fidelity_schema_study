from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from types import ModuleType
from typing import Any, Dict, Iterable, Mapping


DECLARATION_SCHEMA_VERSION = (
    "ndp50-execution-implementation-declaration/v1"
)
RECEIPT_SCHEMA_VERSION = (
    "ndp50-execution-implementation-qualification/v1"
)
REPLAY_SCHEMA_VERSION = (
    "ndp50-execution-implementation-qualification-replay/v1"
)
PROBE_SUITE_VERSION = "ndp50-execution-synthetic-conformance/v3"
IMPLEMENTATION_SLOTS = (
    "cost_accounting",
    "demonstration_ranker",
    "response_cache",
    "response_parser",
    "row_sampler",
    "runner",
    "scorer",
    "serializer",
)
ENTRYPOINT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class NDPExecutionQualificationError(ValueError):
    pass


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _study_relative(path: Path, study_root: Path) -> str:
    try:
        return path.resolve().relative_to(study_root.resolve()).as_posix()
    except ValueError as exc:
        raise NDPExecutionQualificationError(
            f"artifact must be inside the study root: {path}"
        ) from exc


def _binding(path: Path, study_root: Path) -> Dict[str, str]:
    if not path.is_file():
        raise NDPExecutionQualificationError(
            f"artifact does not exist: {path}"
        )
    return {
        "file": _study_relative(path, study_root),
        "sha256": _sha256_file(path),
    }


def _bound_path(
    ref: Any,
    *,
    study_root: Path,
    label: str,
) -> Path:
    if not isinstance(ref, dict):
        raise NDPExecutionQualificationError(f"{label} binding is missing")
    value = ref.get("file")
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise NDPExecutionQualificationError(
            f"{label} must use a study-relative file"
        )
    root = study_root.resolve()
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise NDPExecutionQualificationError(
            f"{label} escapes the study root"
        ) from exc
    if not path.is_file():
        raise NDPExecutionQualificationError(f"{label} does not exist")
    if _sha256_file(path) != ref.get("sha256"):
        raise NDPExecutionQualificationError(f"{label} hash mismatch")
    return path


def interface_version(slot: str) -> str:
    if slot not in IMPLEMENTATION_SLOTS:
        raise NDPExecutionQualificationError(
            f"unsupported implementation slot: {slot}"
        )
    version = (
        "v2"
        if slot in {"response_parser", "runner", "scorer"}
        else "v1"
    )
    return f"ndp50-execution-{slot.replace('_', '-')}/{version}"


_PROBE_REQUESTS: Dict[str, list[Dict[str, Any]]] = {
    "runner": [
        {
            "probe_suite_version": PROBE_SUITE_VERSION,
            "probe_id": "runner_registered_matrix",
            "case_ids": ["synthetic-case-b", "synthetic-case-a"],
            "arm_ids": ["arm-2", "arm-1"],
            "case_order_policy": "case_id_ascending",
            "arm_order_policy": "registered",
        },
        {
            "probe_suite_version": PROBE_SUITE_VERSION,
            "probe_id": "runner_actual_schedule_contract",
            "interface_version": "ndp50-execution-runner/v2",
            "operation": "plan_registered_execution",
            "case_ids": [
                "synthetic-case-c",
                "synthetic-case-a",
                "synthetic-case-b",
            ],
            "case_order_policy": "fixed_seed_hash_rank",
            "case_order_seed": 99173,
            "arm_interleaving_policy": (
                "case_major_seeded_cyclic_execution_blocks"
            ),
            "arm_order_seed": 37,
            "execution_blocks": [
                ["zero", "replay"],
                ["deterministic"],
                ["one-shot"],
                ["sensitivity-a"],
                ["sensitivity-b"],
            ],
        },
    ],
    "response_cache": [
        {
            "probe_suite_version": PROBE_SUITE_VERSION,
            "probe_id": "cache_byte_identity",
            "requests": [
                {"cache_key": "a", "response_hex": "7b2261223a317d"},
                {"cache_key": "a", "response_hex": "7b2261223a317d"},
                {"cache_key": "b", "response_hex": "7b2262223a327d"},
            ],
        }
    ],
    "serializer": [
        {
            "probe_suite_version": PROBE_SUITE_VERSION,
            "probe_id": "serializer_canonical_utf8",
            "payload": {
                "z": None,
                "a": ["α", 2, True],
                "nested": {"b": 2, "a": 1},
            },
        }
    ],
    "row_sampler": [
        {
            "probe_suite_version": PROBE_SUITE_VERSION,
            "probe_id": "row_sampler_head",
            "sampler_id": "head",
            "row_count": 2,
            "seed": None,
            "rows": [
                {"row_id": "r3", "value": 3},
                {"row_id": "r1", "value": 1},
                {"row_id": "r2", "value": 2},
            ],
        },
        {
            "probe_suite_version": PROBE_SUITE_VERSION,
            "probe_id": "row_sampler_fixed_seed",
            "sampler_id": "fixed_seed_hash_rank",
            "row_count": 2,
            "seed": 1729,
            "rows": [
                {"row_id": "r3", "value": 3},
                {"row_id": "r1", "value": 1},
                {"row_id": "r2", "value": 2},
            ],
        },
    ],
    "demonstration_ranker": [
        {
            "probe_suite_version": PROBE_SUITE_VERSION,
            "probe_id": "ranker_development_only",
            "top_k": 2,
            "candidates": [
                {
                    "case_id": "dev-b",
                    "split": "development",
                    "similarity": 0.8,
                },
                {
                    "case_id": "validation-leak",
                    "split": "validation",
                    "similarity": 1.0,
                },
                {
                    "case_id": "dev-a",
                    "split": "development",
                    "similarity": 0.8,
                },
                {
                    "case_id": "dev-c",
                    "split": "development",
                    "similarity": 0.5,
                },
            ],
        }
    ],
    "response_parser": [
        {
            "probe_suite_version": PROBE_SUITE_VERSION,
            "probe_id": "parser_valid_and_malformed",
            "responses": [
                {"response_id": "valid", "text": "{\"answer\":\"x\"}"},
                {"response_id": "malformed", "text": "{\"answer\":"},
            ],
        },
        {
            "probe_suite_version": PROBE_SUITE_VERSION,
            "probe_id": "parser_actual_response_contract",
            "interface_version": "ndp50-execution-response-parser/v2",
            "operation": "parse_registered_response",
            "case_id": "synthetic-case",
            "dataset_id": "synthetic-dataset",
            "arm_id": "synthetic-arm",
            "response_text": (
                "{\"slots\":[{\"slot_id\":\"s1\","
                "\"prediction_state\":\"accepted_known\","
                "\"prediction_value\":\"x\",\"verified\":true,"
                "\"support_valid\":true,"
                "\"evidence_reference_valid\":true}]}"
            ),
        },
    ],
    "scorer": [
        {
            "probe_suite_version": PROBE_SUITE_VERSION,
            "probe_id": "scorer_denominator_and_abstention",
            "slots": [
                {
                    "slot_id": "s1",
                    "gold_state": "applicable_known",
                    "gold_value": "x",
                    "prediction_state": "accepted_known",
                    "prediction_value": "x",
                    "verified": True,
                },
                {
                    "slot_id": "s2",
                    "gold_state": "applicable_known",
                    "gold_value": "y",
                    "prediction_state": "accepted_known",
                    "prediction_value": "z",
                    "verified": False,
                },
                {
                    "slot_id": "s3",
                    "gold_state": "applicable_known",
                    "gold_value": "q",
                    "prediction_state": "explicit_oov_or_abstention",
                    "prediction_value": None,
                    "verified": False,
                },
            ],
        },
        {
            "probe_suite_version": PROBE_SUITE_VERSION,
            "probe_id": "scorer_actual_case_contract",
            "interface_version": "ndp50-execution-scorer/v2",
            "operation": "score_registered_case",
            "case_id": "synthetic-case",
            "dataset_id": "synthetic-dataset",
            "arm_id": "synthetic-arm",
            "record_status": "completed",
            "gold": {
                "slots": [
                    {
                        "slot_id": "s1",
                        "label_id": "semantic_type",
                        "gold_state": "applicable_known",
                        "gold_value": "temperature",
                    },
                    {
                        "slot_id": "s2",
                        "label_id": "semantic_type",
                        "gold_state": "applicable_known",
                        "gold_value": "humidity",
                    },
                    {
                        "slot_id": "s3",
                        "label_id": "unit",
                        "gold_state": "applicable_unknown_or_oov",
                        "gold_value": None,
                    },
                ]
            },
            "prediction": {
                "slots": [
                    {
                        "slot_id": "s1",
                        "prediction_state": "accepted_known",
                        "prediction_value": "temperature",
                        "verified": True,
                        "support_valid": True,
                        "evidence_reference_valid": True,
                    },
                    {
                        "slot_id": "s2",
                        "prediction_state": "explicit_oov_or_abstention",
                        "prediction_value": None,
                        "verified": False,
                        "support_valid": False,
                        "evidence_reference_valid": False,
                    },
                    {
                        "slot_id": "s3",
                        "prediction_state": "explicit_oov_or_abstention",
                        "prediction_value": None,
                        "verified": False,
                        "support_valid": False,
                        "evidence_reference_valid": False,
                    },
                ]
            },
        }
    ],
    "cost_accounting": [
        {
            "probe_suite_version": PROBE_SUITE_VERSION,
            "probe_id": "cost_frozen_schedule",
            "usage": {
                "physical_calls": 2,
                "input_tokens": 1500,
                "output_tokens": 250,
            },
            "rates": {
                "per_call": 0.01,
                "input_per_1000_tokens": 0.002,
                "output_per_1000_tokens": 0.004,
            },
        }
    ],
}


def qualification_probe_requests(slot: str) -> list[Dict[str, Any]]:
    if slot not in _PROBE_REQUESTS:
        raise NDPExecutionQualificationError(
            f"unsupported implementation slot: {slot}"
        )
    return deepcopy(_PROBE_REQUESTS[slot])


def reference_registered_execution_schedule(
    request: Mapping[str, Any],
) -> Dict[str, Any]:
    case_ids = request.get("case_ids")
    blocks = request.get("execution_blocks")
    if (
        request.get("interface_version") != interface_version("runner")
        or request.get("operation") != "plan_registered_execution"
        or request.get("case_order_policy")
        not in {"case_id_ascending", "fixed_seed_hash_rank"}
        or request.get("arm_interleaving_policy")
        != "case_major_seeded_cyclic_execution_blocks"
        or not isinstance(case_ids, list)
        or not case_ids
        or any(not str(value).strip() for value in case_ids)
        or len(set(str(value) for value in case_ids)) != len(case_ids)
        or not isinstance(blocks, list)
        or not blocks
        or any(not isinstance(block, list) or not block for block in blocks)
    ):
        raise NDPExecutionQualificationError(
            "registered execution scheduling request is invalid"
        )
    normalized_blocks = [
        [str(value) for value in block] for block in blocks
    ]
    arm_ids = [
        arm_id for block in normalized_blocks for arm_id in block
    ]
    if (
        any(not arm_id.strip() for arm_id in arm_ids)
        or len(set(arm_ids)) != len(arm_ids)
    ):
        raise NDPExecutionQualificationError(
            "registered execution blocks must contain unique arm IDs"
        )
    case_policy = str(request["case_order_policy"])
    case_seed = request.get("case_order_seed")
    if case_policy == "case_id_ascending":
        if case_seed is not None:
            raise NDPExecutionQualificationError(
                "ascending case order cannot declare a seed"
            )
        ordered_cases = sorted(str(value) for value in case_ids)
    else:
        if not isinstance(case_seed, int) or isinstance(case_seed, bool):
            raise NDPExecutionQualificationError(
                "hash-ranked case order requires an integer seed"
            )
        ordered_cases = sorted(
            (str(value) for value in case_ids),
            key=lambda case_id: (
                hashlib.sha256(
                    f"{case_seed}:{case_id}".encode("utf-8")
                ).hexdigest(),
                case_id,
            ),
        )
    arm_order_seed = request.get("arm_order_seed")
    if not isinstance(arm_order_seed, int) or isinstance(
        arm_order_seed, bool
    ):
        raise NDPExecutionQualificationError(
            "cyclic execution blocks require an integer arm-order seed"
        )
    schedule = []
    execution_sequence = 0
    block_count = len(normalized_blocks)
    for case_position, case_id in enumerate(ordered_cases):
        offset = (case_position + arm_order_seed) % block_count
        rotated = (
            normalized_blocks[offset:] + normalized_blocks[:offset]
        )
        for block in rotated:
            for arm_id in block:
                execution_sequence += 1
                schedule.append(
                    {
                        "execution_sequence": execution_sequence,
                        "case_id": case_id,
                        "arm_id": arm_id,
                    }
                )
    return {
        "case_order": ordered_cases,
        "execution_blocks": normalized_blocks,
        "schedule": schedule,
        "record_count": len(schedule),
    }


def reference_registered_response_parse(
    request: Mapping[str, Any],
) -> Dict[str, Any]:
    if (
        request.get("interface_version")
        != interface_version("response_parser")
        or request.get("operation") != "parse_registered_response"
        or not all(
            str(request.get(key) or "").strip()
            for key in ("case_id", "dataset_id", "arm_id")
        )
        or not isinstance(request.get("response_text"), str)
    ):
        raise NDPExecutionQualificationError(
            "registered response parsing request is invalid"
        )
    try:
        parsed = json.loads(request["response_text"])
    except json.JSONDecodeError:
        return {
            "parse_status": "rejected",
            "error_code": "invalid_json",
            "slots": [],
        }
    if not isinstance(parsed, dict) or not isinstance(
        parsed.get("slots"), list
    ):
        return {
            "parse_status": "rejected",
            "error_code": "invalid_response_shape",
            "slots": [],
        }
    return {
        "parse_status": "parsed",
        "slots": parsed["slots"],
    }


def reference_registered_case_score(
    request: Mapping[str, Any],
) -> Dict[str, Any]:
    if (
        request.get("interface_version") != interface_version("scorer")
        or request.get("operation") != "score_registered_case"
        or not all(
            str(request.get(key) or "").strip()
            for key in ("case_id", "dataset_id", "arm_id")
        )
        or request.get("record_status")
        not in {"completed", "structured_abstention", "execution_failure"}
    ):
        raise NDPExecutionQualificationError(
            "registered case scoring request is invalid"
        )
    gold = request.get("gold")
    prediction = request.get("prediction")
    if not isinstance(gold, dict) or not isinstance(prediction, dict):
        raise NDPExecutionQualificationError(
            "registered case scoring inputs are missing"
        )
    gold_slots = gold.get("slots")
    prediction_slots = prediction.get("slots")
    if not isinstance(gold_slots, list) or not isinstance(
        prediction_slots, list
    ):
        raise NDPExecutionQualificationError(
            "registered case scoring slots are missing"
        )
    gold_by_id: Dict[str, Mapping[str, Any]] = {}
    for item in gold_slots:
        if not isinstance(item, dict):
            raise NDPExecutionQualificationError("gold slot is malformed")
        slot_id = str(item.get("slot_id") or "")
        if (
            not slot_id
            or slot_id in gold_by_id
            or not str(item.get("label_id") or "")
            or item.get("gold_state")
            not in {
                "applicable_known",
                "applicable_unknown_or_oov",
                "not_applicable",
            }
            or (
                item.get("gold_state") == "applicable_known"
                and item.get("gold_value") is None
            )
        ):
            raise NDPExecutionQualificationError("gold slot is invalid")
        gold_by_id[slot_id] = item
    prediction_by_id: Dict[str, Mapping[str, Any]] = {}
    for item in prediction_slots:
        if not isinstance(item, dict):
            raise NDPExecutionQualificationError(
                "prediction slot is malformed"
            )
        slot_id = str(item.get("slot_id") or "")
        if (
            not slot_id
            or slot_id in prediction_by_id
            or item.get("prediction_state")
            not in {
                "accepted_known",
                "explicit_oov_or_abstention",
                "missing_due_to_execution_failure",
            }
            or any(
                not isinstance(item.get(key), bool)
                for key in (
                    "verified",
                    "support_valid",
                    "evidence_reference_valid",
                )
            )
            or (
                item.get("prediction_state") == "accepted_known"
                and item.get("prediction_value") is None
            )
            or (
                item.get("prediction_state") != "accepted_known"
                and item.get("prediction_value") is not None
            )
        ):
            raise NDPExecutionQualificationError(
                "prediction slot is invalid"
            )
        prediction_by_id[slot_id] = item
    if set(prediction_by_id) != set(gold_by_id):
        raise NDPExecutionQualificationError(
            "gold and prediction slot identities differ"
        )
    if request["record_status"] in {
        "structured_abstention",
        "execution_failure",
    } and any(
        item["prediction_state"] == "accepted_known"
        for item in prediction_by_id.values()
    ):
        raise NDPExecutionQualificationError(
            "failure or abstention cannot accept claims"
        )
    known = [
        item
        for item in gold_slots
        if item["gold_state"] == "applicable_known"
    ]
    unknown_count = sum(
        item["gold_state"] == "applicable_unknown_or_oov"
        for item in gold_slots
    )
    correct = 0
    accepted = 0
    incorrect = 0
    unsupported = 0
    evidence_valid = 0
    verified_correct = 0
    confusion: Dict[str, Dict[str, int]] = {}
    for gold_item in known:
        prediction_item = prediction_by_id[str(gold_item["slot_id"])]
        label_id = str(gold_item["label_id"])
        counts = confusion.setdefault(
            label_id, {"tp": 0, "fp": 0, "fn": 0}
        )
        is_accepted = (
            prediction_item["prediction_state"] == "accepted_known"
        )
        is_correct = (
            is_accepted
            and prediction_item["prediction_value"]
            == gold_item["gold_value"]
        )
        if is_accepted:
            accepted += 1
            unsupported += int(not prediction_item["support_valid"])
            evidence_valid += int(
                prediction_item["evidence_reference_valid"]
            )
        if is_correct:
            correct += 1
            counts["tp"] += 1
            verified_correct += int(prediction_item["verified"])
        else:
            counts["fn"] += 1
            if is_accepted:
                incorrect += 1
                counts["fp"] += 1
    return {
        "applicable_known_slot_count": len(known),
        "applicable_unknown_or_oov_slot_count": unknown_count,
        "correct_accepted_claim_count": correct,
        "accepted_known_claim_count": accepted,
        "incorrect_accepted_known_claim_count": incorrect,
        "unsupported_accepted_claim_count": unsupported,
        "valid_evidence_reference_claim_count": evidence_valid,
        "verified_correct_accepted_claim_count": verified_correct,
        "label_confusion_counts": [
            {
                "label_id": label_id,
                **counts,
                "gold_support": counts["tp"] + counts["fn"],
                "prediction_support": counts["tp"] + counts["fp"],
            }
            for label_id, counts in sorted(confusion.items())
        ],
    }


def reference_probe_response(request: Mapping[str, Any]) -> Dict[str, Any]:
    if request.get("operation") == "plan_registered_execution":
        return reference_registered_execution_schedule(request)
    if request.get("operation") == "parse_registered_response":
        return reference_registered_response_parse(request)
    if request.get("operation") == "score_registered_case":
        return reference_registered_case_score(request)
    probe_id = request.get("probe_id")
    if request.get("probe_suite_version") != PROBE_SUITE_VERSION:
        raise NDPExecutionQualificationError("probe suite version mismatch")
    if probe_id == "runner_registered_matrix":
        case_ids = sorted(str(value) for value in request["case_ids"])
        arm_ids = [str(value) for value in request["arm_ids"]]
        return {
            "records": [
                {"case_id": case_id, "arm_id": arm_id}
                for case_id in case_ids
                for arm_id in arm_ids
            ],
            "record_count": len(case_ids) * len(arm_ids),
        }
    if probe_id == "cache_byte_identity":
        cache: Dict[str, str] = {}
        records = []
        physical_calls = 0
        for item in request["requests"]:
            key = str(item["cache_key"])
            hit = key in cache
            if not hit:
                cache[key] = str(item["response_hex"])
                physical_calls += 1
            records.append(
                {
                    "cache_key": key,
                    "cache_hit": hit,
                    "response_hex": cache[key],
                }
            )
        return {
            "records": records,
            "physical_calls": physical_calls,
            "byte_identity_preserved": True,
        }
    if probe_id == "serializer_canonical_utf8":
        text = json.dumps(
            request["payload"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        encoded = text.encode("utf-8")
        return {
            "utf8_hex": encoded.hex(),
            "sha256": hashlib.sha256(encoded).hexdigest(),
        }
    if probe_id in {"row_sampler_head", "row_sampler_fixed_seed"}:
        rows = list(request["rows"])
        count = int(request["row_count"])
        if request["sampler_id"] == "head":
            selected = rows[:count]
        else:
            seed = int(request["seed"])
            selected = sorted(
                rows,
                key=lambda row: (
                    hashlib.sha256(
                        f"{seed}:{row['row_id']}".encode("utf-8")
                    ).hexdigest(),
                    str(row["row_id"]),
                ),
            )[:count]
        return {
            "selected_row_ids": [str(row["row_id"]) for row in selected],
            "input_row_count": len(rows),
            "input_mutated": False,
        }
    if probe_id == "ranker_development_only":
        ranked = sorted(
            (
                item
                for item in request["candidates"]
                if item["split"] == "development"
            ),
            key=lambda item: (
                -float(item["similarity"]),
                str(item["case_id"]),
            ),
        )
        selected = ranked[: int(request["top_k"])]
        return {
            "selected_case_ids": [
                str(item["case_id"]) for item in selected
            ],
            "nondevelopment_selected": False,
        }
    if probe_id == "parser_valid_and_malformed":
        records = []
        for item in request["responses"]:
            try:
                parsed = json.loads(str(item["text"]))
            except json.JSONDecodeError:
                records.append(
                    {
                        "response_id": item["response_id"],
                        "status": "rejected",
                        "error_code": "invalid_json",
                    }
                )
            else:
                records.append(
                    {
                        "response_id": item["response_id"],
                        "status": "parsed",
                        "payload": parsed,
                    }
                )
        return {"records": records}
    if probe_id == "scorer_denominator_and_abstention":
        slots = list(request["slots"])
        applicable = [
            item
            for item in slots
            if item["gold_state"] == "applicable_known"
        ]
        accepted = [
            item
            for item in applicable
            if item["prediction_state"] == "accepted_known"
        ]
        correct = [
            item
            for item in accepted
            if item["prediction_value"] == item["gold_value"]
        ]
        verified_correct = [
            item for item in correct if item["verified"] is True
        ]
        incorrect = [
            item
            for item in accepted
            if item["prediction_value"] != item["gold_value"]
        ]
        return {
            "registered_applicable_known_slots": len(applicable),
            "accepted_known_claims": len(accepted),
            "correct_accepted_claims": len(correct),
            "verified_correct_claims": len(verified_correct),
            "abstained_or_oov_slots": len(applicable) - len(accepted),
            "correct_accepted_applicable_claim_rate": (
                len(correct) / len(applicable)
            ),
            "verified_coverage": (
                len(verified_correct) / len(applicable)
            ),
            "selective_risk": len(incorrect) / len(accepted),
        }
    if probe_id == "cost_frozen_schedule":
        usage = request["usage"]
        rates = request["rates"]
        cost = (
            int(usage["physical_calls"]) * float(rates["per_call"])
            + int(usage["input_tokens"])
            / 1000
            * float(rates["input_per_1000_tokens"])
            + int(usage["output_tokens"])
            / 1000
            * float(rates["output_per_1000_tokens"])
        )
        return {
            "cost": round(cost, 12),
            "currency": "frozen_schedule_units",
            "cached_calls_charged": False,
        }
    raise NDPExecutionQualificationError(
        f"unknown qualification probe: {probe_id}"
    )


def _load_module(path: Path) -> ModuleType:
    module_name = (
        "_ndp50_execution_component_"
        + hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
    )
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise NDPExecutionQualificationError(
            f"cannot load Python implementation: {path}"
        )
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def _validate_declaration(
    declaration: Mapping[str, Any],
    *,
    study_root: Path,
) -> Dict[str, tuple[Path, str]]:
    if declaration.get("schema_version") != DECLARATION_SCHEMA_VERSION:
        raise NDPExecutionQualificationError(
            "unexpected implementation declaration schema"
        )
    if declaration.get("status") != "complete_pending_qualification":
        raise NDPExecutionQualificationError(
            "implementation declaration status is incomplete"
        )
    if declaration.get("synthetic_probes_only") is not True:
        raise NDPExecutionQualificationError(
            "qualification must use synthetic probes only"
        )
    if declaration.get("development_validation_or_test_data_used") is not False:
        raise NDPExecutionQualificationError(
            "qualification cannot use development, validation, or test data"
        )
    if declaration.get("completion_attestation") is not True:
        raise NDPExecutionQualificationError(
            "implementation declaration completion is not attested"
        )
    implementations = declaration.get("implementations")
    if not isinstance(implementations, dict) or set(implementations) != set(
        IMPLEMENTATION_SLOTS
    ):
        raise NDPExecutionQualificationError(
            "implementation declaration must cover every required slot"
        )
    validated: Dict[str, tuple[Path, str]] = {}
    for slot in IMPLEMENTATION_SLOTS:
        item = implementations[slot]
        if not isinstance(item, dict) or set(item) != {
            "artifact",
            "entrypoint",
            "interface_version",
        }:
            raise NDPExecutionQualificationError(
                f"{slot} implementation declaration is malformed"
            )
        if item.get("interface_version") != interface_version(slot):
            raise NDPExecutionQualificationError(
                f"{slot} interface version mismatch"
            )
        entrypoint = item.get("entrypoint")
        if not isinstance(entrypoint, str) or not ENTRYPOINT_RE.fullmatch(
            entrypoint
        ):
            raise NDPExecutionQualificationError(
                f"{slot} entrypoint is invalid"
            )
        path = _bound_path(
            item.get("artifact"),
            study_root=study_root,
            label=f"{slot} implementation artifact",
        )
        if path.suffix.casefold() != ".py":
            raise NDPExecutionQualificationError(
                f"{slot} implementation must be a Python source file"
            )
        validated[slot] = (path, entrypoint)
    return validated


def build_qualification_receipt(
    *,
    declaration_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    declaration = _load_json(declaration_path)
    validated = _validate_declaration(
        declaration,
        study_root=study_root,
    )
    modules: Dict[Path, ModuleType] = {}
    slot_results: Dict[str, Any] = {}
    suite_material: Dict[str, Any] = {}
    for slot in IMPLEMENTATION_SLOTS:
        path, entrypoint = validated[slot]
        if path not in modules:
            modules[path] = _load_module(path)
        module = modules[path]
        function = getattr(module, entrypoint, None)
        if not callable(function):
            raise NDPExecutionQualificationError(
                f"{slot} entrypoint is not callable"
            )
        requests = qualification_probe_requests(slot)
        output_hashes = []
        for request in requests:
            expected = reference_probe_response(request)
            try:
                observed = function(deepcopy(request))
            except Exception as exc:  # noqa: BLE001
                raise NDPExecutionQualificationError(
                    f"{slot} probe {request['probe_id']} raised: {exc}"
                ) from exc
            if observed != expected:
                raise NDPExecutionQualificationError(
                    f"{slot} probe {request['probe_id']} output mismatch"
                )
            output_hashes.append(_canonical_sha256(observed))
        suite_material[slot] = {
            "requests": requests,
            "expected_outputs": [
                reference_probe_response(request) for request in requests
            ],
        }
        item = declaration["implementations"][slot]
        slot_results[slot] = {
            "artifact": item["artifact"],
            "entrypoint": entrypoint,
            "interface_version": item["interface_version"],
            "probe_count": len(requests),
            "probe_ids": [request["probe_id"] for request in requests],
            "output_sha256": output_hashes,
            "all_passed": True,
        }
    implementation = Path(__file__).resolve()
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": "passed",
        "synthetic_probes_only": True,
        "development_validation_or_test_data_used": False,
        "declaration": _binding(declaration_path, study_root),
        "probe_suite": {
            "version": PROBE_SUITE_VERSION,
            "canonical_sha256": _canonical_sha256(suite_material),
            "implementation": {
                "file": implementation.name,
                "sha256": _sha256_file(implementation),
            },
        },
        "qualified_slot_count": len(slot_results),
        "slots": slot_results,
    }


def verify_qualification_receipt(
    receipt: Mapping[str, Any],
    *,
    declaration_path: Path,
    study_root: Path,
) -> Dict[str, Any]:
    try:
        expected = build_qualification_receipt(
            declaration_path=declaration_path,
            study_root=study_root,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "schema_version": REPLAY_SCHEMA_VERSION,
            "status": "failed",
            "detail": str(exc),
            "differing_top_level_keys": [],
        }
    differing = sorted(
        key
        for key in set(expected) | set(receipt)
        if receipt.get(key) != expected.get(key)
    )
    return {
        "schema_version": REPLAY_SCHEMA_VERSION,
        "status": "passed" if not differing else "failed",
        "detail": None,
        "differing_top_level_keys": differing,
    }


def load_qualified_entrypoint(
    execution_freeze: Mapping[str, Any],
    *,
    slot: str,
    study_root: Path,
) -> Any:
    if slot not in IMPLEMENTATION_SLOTS:
        raise NDPExecutionQualificationError(
            f"unsupported implementation slot: {slot}"
        )
    config = execution_freeze.get("config")
    if not isinstance(config, dict):
        raise NDPExecutionQualificationError(
            "execution freeze config is missing"
        )
    qualification = config.get("execution_qualification")
    if not isinstance(qualification, dict):
        raise NDPExecutionQualificationError(
            "execution qualification binding is missing"
        )
    declaration_path = _bound_path(
        qualification.get("declaration"),
        study_root=study_root,
        label="execution implementation declaration",
    )
    receipt_path = _bound_path(
        qualification.get("receipt"),
        study_root=study_root,
        label="execution implementation qualification receipt",
    )
    declaration = _load_json(declaration_path)
    receipt = _load_json(receipt_path)
    replay = verify_qualification_receipt(
        receipt,
        declaration_path=declaration_path,
        study_root=study_root,
    )
    if replay.get("status") != "passed":
        raise NDPExecutionQualificationError(
            "execution implementation qualification does not replay"
        )
    if config.get("execution_implementations") != declaration.get(
        "implementations"
    ):
        raise NDPExecutionQualificationError(
            "execution freeze and qualification declaration differ"
        )
    path, entrypoint = _validate_declaration(
        declaration, study_root=study_root
    )[slot]
    function = getattr(_load_module(path), entrypoint, None)
    if not callable(function):
        raise NDPExecutionQualificationError(
            f"{slot} entrypoint is not callable"
        )
    return function


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Qualify frozen NDP-50 execution component entrypoints with "
            "synthetic deterministic conformance probes."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--declaration", type=Path, required=True)
    prepare.add_argument("--study-root", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--receipt", type=Path, required=True)
    verify.add_argument("--declaration", type=Path, required=True)
    verify.add_argument("--study-root", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        receipt = build_qualification_receipt(
            declaration_path=args.declaration,
            study_root=args.study_root,
        )
        _write_json(args.output, receipt)
        print(
            json.dumps(
                {
                    "status": receipt["status"],
                    "qualified_slot_count": receipt[
                        "qualified_slot_count"
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    receipt = _load_json(args.receipt)
    result = verify_qualification_receipt(
        receipt,
        declaration_path=args.declaration,
        study_root=args.study_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
