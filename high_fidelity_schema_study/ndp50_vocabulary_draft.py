from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, Mapping

from .semantic_gold_workflow import validate_vocabulary


SCHEMA_VERSION = "semantic-annotation-vocabulary/v1"


class NDPVocabularyDraftError(ValueError):
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


def _field_tokens(field_path: str) -> list[str]:
    return [
        token
        for token in re.split(r"[^a-z0-9]+", field_path.casefold())
        if len(token) >= 2 and not token.isdigit()
    ]


def build_vocabulary_draft(
    *,
    packet_manifest_path: Path,
    base_vocabulary_path: Path,
) -> Dict[str, Any]:
    packet_manifest = _load_json(packet_manifest_path)
    if packet_manifest.get("schema_version") != "ndp50-semantic-packet-pack/v1":
        raise NDPVocabularyDraftError("unexpected packet manifest schema")
    base = _load_json(base_vocabulary_path)
    if validate_vocabulary(base)["status"] != "ready":
        raise NDPVocabularyDraftError("base vocabulary must be frozen and valid")

    physical_types = set(base["physical_types"])
    field_token_counts: Counter[str] = Counter()
    field_paths = []
    for item in packet_manifest["cases"]:
        packet_path = (
            packet_manifest_path.parent / item["packet_file"]
        ).resolve()
        if _sha256_file(packet_path) != item["packet_sha256"]:
            raise NDPVocabularyDraftError(
                f"packet hash mismatch for {item['case_id']}"
            )
        packet = _load_json(packet_path)
        for field in packet["field_inventory"]:
            physical_type = field.get("physical_type")
            if physical_type:
                physical_types.add(str(physical_type))
            field_path = str(field["field_path"])
            field_paths.append(
                {
                    "case_id": item["case_id"],
                    "split": item["split"],
                    "field_path": field_path,
                }
            )
            field_token_counts.update(_field_tokens(field_path))

    draft = {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": "semantic-architecture-protocol/v1",
        "status": "draft",
        "research_evidence_status": "ndp50_pre_model_human_curation_required",
        "vocabulary_version": "ndp50-draft-v1",
        "created_at": _utc_now(),
        "construction_basis": (
            "Starts from the pre-NDP frozen calibration vocabulary. Only "
            "deterministically observed physical types are added automatically. "
            "No logical, semantic, or unit label is inferred from field names."
        ),
        "base_vocabulary": {
            "file": base_vocabulary_path.name,
            "sha256": _sha256_file(base_vocabulary_path),
        },
        "packet_manifest": {
            "file": packet_manifest_path.name,
            "sha256": _sha256_file(packet_manifest_path),
        },
        "physical_types": sorted(physical_types),
        "logical_types": list(base["logical_types"]),
        "semantic_types": list(base["semantic_types"]),
        "units": list(base["units"]),
        "unit_aliases": dict(base["unit_aliases"]),
        "unit_patterns": list(base["unit_patterns"]),
        "unknown_representation": None,
        "extension_policy": (
            "Human curators may add corpus-supported terms before annotation "
            "using approved source documentation only. Every addition requires "
            "a rationale and source selector. After freeze, unresolved or OOV "
            "applicable values use null; no label is invented during scoring."
        ),
        "field_lexicon_for_human_review": {
            "field_occurrence_count": len(field_paths),
            "unique_field_path_count": len(
                {(item["case_id"], item["field_path"]) for item in field_paths}
            ),
            "token_counts": [
                {"token": token, "count": count}
                for token, count in sorted(
                    field_token_counts.items(), key=lambda item: (-item[1], item[0])
                )
            ],
            "field_paths": sorted(
                field_paths, key=lambda item: (item["case_id"], item["field_path"])
            ),
            "warning": (
                "Tokens are discovery aids, not candidate semantic labels and "
                "must not be promoted without approved evidence."
            ),
        },
        "freeze_blockers": [
            "domain curator review has not occurred",
            "NDP documentation-backed additions and rationales are absent",
            "out-of-vocabulary policy has not been independently approved",
            "two independent annotators have not confirmed usability",
        ],
    }
    if validate_vocabulary(draft)["status"] != "blocked":
        raise NDPVocabularyDraftError(
            "draft vocabulary must fail the frozen-vocabulary readiness gate"
        )
    return draft


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a conservative non-frozen NDP-50 vocabulary draft."
    )
    parser.add_argument("--packet-manifest", type=Path, required=True)
    parser.add_argument("--base-vocabulary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    draft = build_vocabulary_draft(
        packet_manifest_path=args.packet_manifest,
        base_vocabulary_path=args.base_vocabulary,
    )
    _write_json(args.output, draft)
    print(
        json.dumps(
            {
                "status": draft["status"],
                "physical_type_count": len(draft["physical_types"]),
                "semantic_type_count": len(draft["semantic_types"]),
                "field_token_count": len(
                    draft["field_lexicon_for_human_review"]["token_counts"]
                ),
                "freeze_blocker_count": len(draft["freeze_blockers"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
