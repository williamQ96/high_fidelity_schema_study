from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from .extractors.registry import list_capabilities


def export_capability_registry() -> Dict[str, Any]:
    return {
        "registry_version": "1.0.0",
        "capabilities": [asdict(item) for item in list_capabilities()],
        "policy": {
            "canonical_claims_require_registered_deterministic_extractor": True,
            "agent_can_register_or_promote_claims": False,
        },
    }


def export_agent_bundle(envelope: Dict[str, Any]) -> Dict[str, Any]:
    identity = envelope["identity"]
    field_summaries = [
        {
            "field_path": field.get("field_path"),
            "physical_type": field.get("physical_type"),
            "logical_type": field.get("logical_type"),
            "semantic_type": field.get("semantic_type"),
            "nullable": field.get("nullable"),
        }
        for field in envelope["physical_structure"]["fields"]
    ]
    source_id = f"source:{identity.get('file_id')}"
    envelope_id = f"envelope:{identity.get('dataset_id')}"
    extractor_id = envelope["provenance"].get("extractor_id") or "none"
    return {
        "agent_export_version": "1.0.0",
        "policy": {
            "canonical_mutation_allowed": False,
            "silent_claim_promotion_allowed": False,
            "suggestions_are_noncanonical": True,
            "reruns_require_explicit_request": True,
        },
        "schema_summary": {
            "identity": identity,
            "outcome_status": envelope["outcome"]["status"],
            "field_count": len(field_summaries),
            "claim_count": len(envelope["claims"]),
            "evidence_count": len(envelope["evidence"]),
            "conflict_count": len(envelope["conflicts"]),
            "abstention_count": len(envelope["abstentions"]),
            "fields": field_summaries,
        },
        "claim_records": envelope["claims"],
        "evidence_records": envelope["evidence"],
        "provenance_graph": {
            "entities": [
                {"id": source_id, "type": "source_resource", "file_id": identity.get("file_id")},
                {"id": envelope_id, "type": "unified_schema_envelope", "version": envelope["schema_envelope_version"]},
            ],
            "activities": [
                {
                    "id": "activity:deterministic_extraction",
                    "type": "deterministic_extraction",
                    "used": source_id,
                    "generated": envelope_id,
                },
                {
                    "id": "activity:unified_projection",
                    "type": "deterministic_projection",
                    "generated": envelope_id,
                },
            ],
            "agents": [
                {
                    "id": f"extractor:{extractor_id}",
                    "type": "registered_extractor",
                    "version": envelope["provenance"].get("extractor_version"),
                    "determinism_class": envelope["provenance"].get("determinism_class"),
                }
            ],
        },
        "retrieval_context": {
            "title": identity.get("dataset_id"),
            "format": identity.get("file_format"),
            "field_paths": [field["field_path"] for field in field_summaries],
            "supported_claims": [
                {
                    "subject": claim["subject"],
                    "property": claim["property"],
                    "value": claim["value"],
                    "state": claim["state"],
                }
                for claim in envelope["claims"]
                if claim["state"] in {"observed", "declared", "derived", "supported"}
            ],
            "conflicts": envelope["conflicts"],
            "unsupported_features": envelope["unsupported_features"],
        },
        "requestable_actions": [
            {
                "action": "inspect_evidence",
                "effect": "read_only",
            },
            {
                "action": "suggest_noncanonical_annotation",
                "effect": "suggestion_only",
            },
            {
                "action": "request_explicit_rerun",
                "effect": "requires_user_or_orchestrator_approval",
            },
        ],
    }
