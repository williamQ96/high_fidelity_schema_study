from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple
from urllib.error import HTTPError

from .semantic_annotate import (
    aggregate_field_results,
    compact_task_payload,
    extract_json_object,
    grouped_field_sets,
    looks_like_annotation_result,
    response_json_schema,
)
from .semantic_layer import (
    ALLOWED_LOGICAL_TYPES,
    compatible_logical_types_from_semantic,
    merge_annotation_result,
    normalize_annotation_result,
    validate_annotation_result,
)
from .unit_normalization import normalize_unit_claim


EVALUATED_PROPERTIES: Tuple[str, ...] = (
    "physical_type",
    "logical_type",
    "semantic_type",
    "unit",
)
SEMANTIC_PROPERTIES = {"logical_type", "semantic_type", "unit"}
EMPTY_VALUES = {None, "", "unknown"}


def _canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    field_path: Optional[str]
    source_type: str
    source_name: str
    detail: str
    text: str
    applicable_field_paths: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PropertyClaim:
    claim_id: str
    field_path: str
    property_name: str
    value: Any
    source: str
    evidence_refs: List[str]
    confidence: Optional[float]
    verification_level: str
    verification_status: str
    decision: str
    decision_reason: str

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["property"] = payload.pop("property_name")
        return payload


@dataclass
class ModelTelemetry:
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    failed_calls: int = 0

    def add(self, other: "ModelTelemetry") -> None:
        self.model_calls += other.model_calls
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.latency_ms += other.latency_ms
        self.cost_usd += other.cost_usd
        self.failed_calls += other.failed_calls

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["latency_ms"] = round(self.latency_ms, 3)
        payload["cost_usd"] = round(self.cost_usd, 8)
        return payload


@dataclass
class ModelCompletion:
    data: Dict[str, Any]
    telemetry: ModelTelemetry
    model_info: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    request_hash: str = ""
    response_hash: str = ""

    def to_record(self, purpose: str) -> Dict[str, Any]:
        return {
            "purpose": purpose,
            "request_hash": self.request_hash,
            "response_hash": self.response_hash or _canonical_hash(self.data),
            "raw_text": self.raw_text or json.dumps(self.data, ensure_ascii=False),
            "parsed_response": self.data,
            "telemetry": self.telemetry.to_dict(),
            "model_info": self.model_info,
        }


class ModelBackendError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        telemetry: Optional[ModelTelemetry] = None,
        request_hash: str = "",
        replayed: bool = False,
        raw_text: str = "",
        model_info: Optional[Dict[str, Any]] = None,
        response_hash: str = "",
        response_records: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        super().__init__(message)
        self.telemetry = telemetry or ModelTelemetry(failed_calls=1)
        self.request_hash = request_hash
        self.replayed = replayed
        self.raw_text = raw_text
        self.model_info = model_info or {}
        self.response_hash = response_hash
        self.response_records = response_records or []


class ModelBackend(Protocol):
    def complete(
        self,
        *,
        system_prompt: str,
        payload: Dict[str, Any],
        response_schema: Dict[str, Any],
        purpose: str,
    ) -> ModelCompletion: ...


@dataclass
class ExperimentCase:
    case_id: str
    task_payload: Dict[str, Any]
    gold_schema: Dict[str, Any]
    benchmark_role: str = "development"
    annotation_vocabulary: Optional[Dict[str, Any]] = None
    legacy_result: Optional[Dict[str, Any]] = None
    legacy_replay_required: bool = False

    @property
    def task_id(self) -> str:
        return str(self.task_payload["task"]["task_id"])


@dataclass
class VariantRun:
    variant_id: str
    case_id: str
    task_id: str
    status: str
    claims: List[PropertyClaim]
    evidence_catalog: List[EvidenceItem]
    telemetry: ModelTelemetry = field(default_factory=ModelTelemetry)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    model_info: Dict[str, Any] = field(default_factory=dict)
    architecture: Dict[str, Any] = field(default_factory=dict)
    model_responses: List[Dict[str, Any]] = field(default_factory=list)
    run_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "case_id": self.case_id,
            "task_id": self.task_id,
            "status": self.status,
            "claims": [claim.to_dict() for claim in self.claims],
            "evidence_catalog": [item.to_dict() for item in self.evidence_catalog],
            "telemetry": self.telemetry.to_dict(),
            "issues": self.issues,
            "model_info": self.model_info,
            "architecture": self.architecture,
            "model_responses": self.model_responses,
            "run_latency_ms": round(self.run_latency_ms, 3),
        }


class OpenAICompatibleBackend:
    """Small strict-JSON backend used only by the experimental variants."""

    def __init__(
        self,
        *,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout_seconds: int = 180,
        input_price_per_million: float = 0.0,
        output_price_per_million: float = 0.0,
        seed: int = 0,
        max_tokens: int = 4096,
        registered_backend: Optional[Dict[str, Any]] = None,
        backend_registry_sha256: Optional[str] = None,
    ) -> None:
        self.api_base = api_base or os.getenv(
            "LLM_SCHEMA_API_BASE", "http://127.0.0.1:1234/v1"
        )
        self.model = model or os.getenv("LLM_SCHEMA_MODEL", "")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "lm-studio")
        self.timeout_seconds = timeout_seconds
        self.input_price_per_million = input_price_per_million
        self.output_price_per_million = output_price_per_million
        self.seed = seed
        self.max_tokens = max_tokens
        self.registered_backend = registered_backend
        self.backend_registry_sha256 = backend_registry_sha256
        if not self.model:
            raise ValueError("model is required for OpenAICompatibleBackend")

    def _post_body(
        self,
        body: Dict[str, Any],
        *,
        purpose: str,
        allow_legacy_json_salvage: bool = False,
    ) -> ModelCompletion:
        request_hash = _canonical_hash(body)
        request = urllib.request.Request(
            url=f"{self.api_base.rstrip('/')}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            response_body = exc.read().decode("utf-8", errors="replace")
            raise ModelBackendError(
                f"model request for {purpose} failed with HTTP {exc.code}: {response_body}",
                telemetry=ModelTelemetry(
                    model_calls=1, latency_ms=latency_ms, failed_calls=1
                ),
                request_hash=request_hash,
            ) from exc
        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - started) * 1000
            raise ModelBackendError(
                f"model request for {purpose} failed: {exc}",
                telemetry=ModelTelemetry(
                    model_calls=1, latency_ms=latency_ms, failed_calls=1
                ),
                request_hash=request_hash,
            ) from exc

        latency_ms = (time.perf_counter() - started) * 1000
        parsed: Dict[str, Any] = {}
        raw_text = ""
        input_tokens = 0
        output_tokens = 0
        cost = 0.0
        model_info: Dict[str, Any] = {}
        try:
            parsed = json.loads(raw)
            usage = parsed.get("usage", {})
            input_tokens = int(
                usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0
            )
            output_tokens = int(
                usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0
            )
            cost = (
                input_tokens * self.input_price_per_million / 1_000_000
                + output_tokens * self.output_price_per_million / 1_000_000
            )
            model_info = {
                "provider": "openai_compatible",
                "model": self.model,
                "purpose": purpose,
                "response_id": parsed.get("id"),
                "finish_reason": parsed.get("choices", [{}])[0].get("finish_reason"),
                "decoding": {
                    "temperature": body.get("temperature"),
                    "seed": body.get("seed"),
                    "max_tokens": body.get("max_tokens"),
                    "thinking_enabled": body.get("chat_template_kwargs", {}).get(
                        "enable_thinking"
                    ),
                    "response_format": body.get("response_format", {}).get("type"),
                },
            }
            message = parsed["choices"][0]["message"]
            content = message.get("content") or message.get("reasoning_content") or ""
            if isinstance(content, dict):
                data = content
                raw_text = json.dumps(content, ensure_ascii=False)
            else:
                raw_text = str(content)
                data = (
                    extract_json_object(raw_text)
                    if allow_legacy_json_salvage
                    else json.loads(raw_text)
                )
        except Exception as exc:  # noqa: BLE001
            raise ModelBackendError(
                f"model response for {purpose} was not valid contract JSON: {exc}",
                telemetry=ModelTelemetry(
                    model_calls=1,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                    failed_calls=1,
                ),
                request_hash=request_hash,
                raw_text=raw_text,
                model_info=model_info,
                response_hash=_canonical_hash(raw_text) if raw_text else "",
            ) from exc
        response_hash = _canonical_hash(data)
        return ModelCompletion(
            data=data,
            telemetry=ModelTelemetry(
                model_calls=1,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
            ),
            model_info=model_info,
            raw_text=raw_text,
            request_hash=request_hash,
            response_hash=response_hash,
        )

    def complete(
        self,
        *,
        system_prompt: str,
        payload: Dict[str, Any],
        response_schema: Dict[str, Any],
        purpose: str,
    ) -> ModelCompletion:
        body = {
            "model": self.model,
            "temperature": 0,
            "seed": self.seed,
            "max_tokens": self.max_tokens,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "architecture_experiment_result",
                    "strict": True,
                    "schema": response_schema,
                },
            },
        }
        return self._post_body(body, purpose=purpose)

    def complete_legacy(
        self,
        *,
        payload: Dict[str, Any],
        response_schema: Dict[str, Any],
        purpose: str,
    ) -> ModelCompletion:
        """Reproduce the historical free-JSON-then-schema request behavior for D."""

        cumulative = ModelTelemetry()
        attempt_records: List[Dict[str, Any]] = []
        last_error: Optional[Exception] = None
        for use_json_schema in (False, True):
            body: Dict[str, Any] = {
                "model": self.model,
                "temperature": 0.2,
                "max_tokens": 1000,
                "chat_template_kwargs": {"enable_thinking": False},
                "messages": [
                    {"role": "system", "content": LEGACY_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Produce a semantic annotation result for this task.\n"
                            'Bad output example: {"task": {...}}\n'
                            "Good output example: "
                            '{"task_id":"...","annotations":[{"field_path":"...","semantic_type":"unknown","logical_type":null,"unit":null,"description":null,"supporting_evidence":[],"confidence":0.0,"uncertainty_reason":"..."}],"conflicts":[...],"notes":[...]}\n\n'
                            + json.dumps(payload, indent=2)
                        ),
                    },
                ],
            }
            if use_json_schema:
                body["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "semantic_annotation_result",
                        "schema": response_schema,
                    },
                }
            attempt_purpose = f"{purpose}:json_schema={str(use_json_schema).lower()}"
            try:
                completion = self._post_body(
                    body,
                    purpose=attempt_purpose,
                    allow_legacy_json_salvage=True,
                )
                cumulative.add(completion.telemetry)
                attempt_records.append(completion.to_record(attempt_purpose))
                if looks_like_annotation_result(completion.data):
                    completion.telemetry = cumulative
                    completion.model_info = {
                        **completion.model_info,
                        "legacy_request_policy": "free_json_then_json_schema",
                        "attempts": attempt_records,
                    }
                    return completion
                cumulative.failed_calls += 1
                attempt_records[-1]["telemetry"]["failed_calls"] = 1
                attempt_records[-1]["contract_error"] = (
                    "JSON did not match the annotation-result shape"
                )
                last_error = RuntimeError(
                    "model returned JSON but not the required annotation-result shape"
                )
            except ModelBackendError as exc:
                cumulative.add(exc.telemetry)
                attempt_records.append(
                    {
                        "purpose": attempt_purpose,
                        "request_hash": exc.request_hash,
                        "error": str(exc),
                        "telemetry": exc.telemetry.to_dict(),
                        "raw_text": exc.raw_text,
                        "model_info": exc.model_info,
                    }
                )
                last_error = exc
        raise ModelBackendError(
            f"legacy semantic annotation request failed: {last_error}",
            telemetry=cumulative,
            request_hash=_canonical_hash(payload),
            response_records=attempt_records,
        )


class MemoizingBackend:
    """Reuses identical B/C reasoner responses so the verifier is the only changed variable."""

    def __init__(self, backend: ModelBackend) -> None:
        self.backend = backend
        self._cache: Dict[str, ModelCompletion] = {}
        self._failure_cache: Dict[str, Dict[str, Any]] = {}
        self.physical_model_calls = 0
        self.physical_backend_invocations = 0
        self.cache_hits = 0
        self.failure_cache_hits = 0

    def complete(
        self,
        *,
        system_prompt: str,
        payload: Dict[str, Any],
        response_schema: Dict[str, Any],
        purpose: str,
    ) -> ModelCompletion:
        cacheable = purpose.startswith("dataset_reasoner:")
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "system_prompt": system_prompt,
                    "payload": payload,
                    "response_schema": response_schema,
                    "purpose": purpose,
                },
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        if cacheable and fingerprint in self._cache:
            self.cache_hits += 1
            cached = self._cache[fingerprint]
            return ModelCompletion(
                data=json.loads(json.dumps(cached.data)),
                telemetry=ModelTelemetry(),
                model_info={
                    **cached.model_info,
                    "shared_reasoner_replay": True,
                    "replay_source_telemetry": cached.telemetry.to_dict(),
                },
                raw_text=cached.raw_text,
                request_hash=cached.request_hash or fingerprint,
                response_hash=cached.response_hash or _canonical_hash(cached.data),
            )
        if cacheable and fingerprint in self._failure_cache:
            self.failure_cache_hits += 1
            failure = self._failure_cache[fingerprint]
            raise ModelBackendError(
                f"replayed upstream model failure: {failure['message']}",
                telemetry=ModelTelemetry(),
                request_hash=fingerprint,
                replayed=True,
                raw_text=str(failure.get("raw_text", "")),
                model_info={
                    **failure.get("model_info", {}),
                    "shared_reasoner_replay": True,
                    "replay_source_telemetry": failure.get("telemetry", {}),
                },
                response_hash=str(failure.get("response_hash", "")),
                response_records=json.loads(
                    json.dumps(failure.get("response_records", []))
                ),
            )
        self.physical_backend_invocations += 1
        try:
            completion = self.backend.complete(
                system_prompt=system_prompt,
                payload=payload,
                response_schema=response_schema,
                purpose=purpose,
            )
        except ModelBackendError as exc:
            self.physical_model_calls += exc.telemetry.model_calls
            if cacheable:
                self._failure_cache[fingerprint] = {
                    "message": str(exc),
                    "telemetry": exc.telemetry.to_dict(),
                    "raw_text": exc.raw_text,
                    "model_info": exc.model_info,
                    "response_hash": exc.response_hash
                    or (_canonical_hash(exc.raw_text) if exc.raw_text else ""),
                    "response_records": exc.response_records,
                }
            raise
        except Exception as exc:  # noqa: BLE001
            telemetry = ModelTelemetry(model_calls=1, failed_calls=1)
            self.physical_model_calls += 1
            if cacheable:
                self._failure_cache[fingerprint] = {"message": str(exc)}
            raise ModelBackendError(
                str(exc), telemetry=telemetry, request_hash=fingerprint
            ) from exc
        self.physical_model_calls += completion.telemetry.model_calls
        completion.request_hash = completion.request_hash or fingerprint
        completion.response_hash = completion.response_hash or _canonical_hash(
            completion.data
        )
        if cacheable:
            self._cache[fingerprint] = completion
        return completion

    def complete_legacy(
        self,
        *,
        payload: Dict[str, Any],
        response_schema: Dict[str, Any],
        purpose: str,
    ) -> ModelCompletion:
        self.physical_backend_invocations += 1
        legacy_method = getattr(self.backend, "complete_legacy", None)
        try:
            if legacy_method is not None:
                completion = legacy_method(
                    payload=payload,
                    response_schema=response_schema,
                    purpose=purpose,
                )
            else:
                completion = self.backend.complete(
                    system_prompt=LEGACY_SYSTEM_PROMPT,
                    payload=payload,
                    response_schema=response_schema,
                    purpose=purpose,
                )
        except ModelBackendError as exc:
            self.physical_model_calls += exc.telemetry.model_calls
            raise
        except Exception as exc:  # noqa: BLE001
            self.physical_model_calls += 1
            raise ModelBackendError(
                str(exc), telemetry=ModelTelemetry(model_calls=1, failed_calls=1)
            ) from exc
        self.physical_model_calls += completion.telemetry.model_calls
        completion.response_hash = completion.response_hash or _canonical_hash(
            completion.data
        )
        return completion


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_present(value: Any) -> bool:
    return value not in EMPTY_VALUES


def _claim_id(
    prefix: str, field_path: str, property_name: str, ordinal: int = 0
) -> str:
    safe_path = field_path.replace(" ", "_").replace("/", "~")
    return f"{prefix}:{safe_path}:{property_name}:{ordinal}"


def _mentions_field(text: str, field_name: Any, field_path: Any) -> bool:
    for raw_token in (field_name, field_path):
        token = str(raw_token or "").strip()
        if token and re.search(
            rf"(?<![\w]){re.escape(token)}(?![\w])", text, flags=re.IGNORECASE
        ):
            return True
    return False


def build_evidence_catalog(task_payload: Dict[str, Any]) -> List[EvidenceItem]:
    task = task_payload["task"]
    fields = task["deterministic_schema"].get("fields", [])
    catalog: List[EvidenceItem] = []
    for field_schema in fields:
        field_path = str(field_schema["field_path"])
        for index, evidence in enumerate(
            field_schema.get("source_evidence", []), start=1
        ):
            detail = str(evidence.get("detail", ""))
            catalog.append(
                EvidenceItem(
                    evidence_id=f"{field_path}::F{index}",
                    field_path=field_path,
                    source_type=str(evidence.get("evidence_type", "parser_evidence")),
                    source_name=str(evidence.get("source", "")),
                    detail=detail,
                    text=detail,
                    applicable_field_paths=(field_path,),
                )
            )
    for index, snippet in enumerate(task.get("grounding_snippets", []), start=1):
        snippet_text = str(snippet.get("text", ""))
        applicable_paths = tuple(
            str(item["field_path"])
            for item in fields
            if _mentions_field(snippet_text, item.get("field_name"), item["field_path"])
        )
        catalog.append(
            EvidenceItem(
                evidence_id=f"S{index}",
                field_path=None,
                source_type=str(snippet.get("source_type", "grounding_snippet")),
                source_name=str(snippet.get("source_name", "")),
                detail=str(snippet.get("detail", "")),
                text=snippet_text,
                applicable_field_paths=applicable_paths,
            )
        )
    return catalog


def build_observation_payload(
    task_payload: Dict[str, Any],
    annotation_vocabulary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    task = task_payload["task"]
    catalog = build_evidence_catalog(task_payload)
    evidence_by_field: Dict[str, List[str]] = {}
    for item in catalog:
        if item.field_path is not None:
            evidence_by_field.setdefault(item.field_path, []).append(item.evidence_id)

    fields: List[Dict[str, Any]] = []
    targets: List[Dict[str, Any]] = []
    for field_schema in task["deterministic_schema"].get("fields", []):
        field_path = str(field_schema["field_path"])
        fields.append(
            {
                "field_path": field_path,
                "field_name": field_schema.get("field_name"),
                "physical_type": field_schema.get("physical_type"),
                "logical_type": field_schema.get("logical_type"),
                "semantic_type": field_schema.get("semantic_type"),
                "unit": field_schema.get("unit"),
                "shape": field_schema.get("shape"),
                "description": field_schema.get("description"),
                "example_values": field_schema.get("example_values", []),
                "value_range": field_schema.get("value_range"),
                "uncertainty_reason": field_schema.get("uncertainty_reason"),
                "evidence_refs": evidence_by_field.get(field_path, []),
            }
        )
        unresolved = [
            property_name
            for property_name in ("logical_type", "semantic_type")
            if not _is_present(field_schema.get(property_name))
        ]
        if unresolved:
            targets.append(
                {
                    "field_path": field_path,
                    "unresolved_properties": unresolved,
                    "allowed_properties": unresolved + ["unit"],
                }
            )

    payload = {
        "task_id": task["task_id"],
        "dataset_id": task["dataset_id"],
        "file_format": task["file_format"],
        "data_modality": task["data_modality"],
        "allowed_logical_types": sorted(ALLOWED_LOGICAL_TYPES),
        "fields": fields,
        "targets": targets,
        "evidence_catalog": [item.to_dict() for item in catalog],
        "instructions": task.get("instructions", []),
    }
    if annotation_vocabulary is not None:
        payload["allowed_semantic_types"] = list(
            annotation_vocabulary.get("semantic_types", [])
        )
        payload["allowed_units"] = list(annotation_vocabulary.get("units", []))
        payload["unit_aliases"] = dict(annotation_vocabulary.get("unit_aliases", {}))
        payload["unit_patterns"] = list(annotation_vocabulary.get("unit_patterns", []))
    return payload


def deterministic_claims(task_payload: Dict[str, Any]) -> List[PropertyClaim]:
    task = task_payload["task"]
    evidence_by_field: Dict[str, List[str]] = {}
    for item in build_evidence_catalog(task_payload):
        if item.field_path is not None:
            evidence_by_field.setdefault(item.field_path, []).append(item.evidence_id)
    claims: List[PropertyClaim] = []
    for field_schema in task["deterministic_schema"].get("fields", []):
        field_path = str(field_schema["field_path"])
        evidence_refs = evidence_by_field.get(field_path, [])
        source_types = {
            str(item.get("evidence_type", ""))
            for item in field_schema.get("source_evidence", [])
        }
        for property_name in EVALUATED_PROPERTIES:
            value = field_schema.get(property_name)
            present = _is_present(value)
            if property_name == "physical_type":
                level = "deterministically_verified"
                verification_status = "verified"
            elif property_name == "unit" and any(
                token in evidence_type
                for evidence_type in source_types
                for token in ("attribute", "declared", "xsd", "schema")
            ):
                level = "deterministically_verified"
                verification_status = "verified"
            elif evidence_refs:
                level = "evidence_grounded"
                verification_status = "supported"
            else:
                level = "unverified"
                verification_status = "not_checked"
            claims.append(
                PropertyClaim(
                    claim_id=_claim_id("A", field_path, property_name),
                    field_path=field_path,
                    property_name=property_name,
                    value=value,
                    source="deterministic_baseline",
                    evidence_refs=list(evidence_refs),
                    confidence=float(field_schema.get("confidence", 1.0)),
                    verification_level=level,
                    verification_status=verification_status,
                    decision="accepted" if present else "abstained",
                    decision_reason="deterministic output"
                    if present
                    else "deterministic output is unknown or not applicable",
                )
            )
    return claims


def dataset_reasoner_response_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "task_id": {"type": "string"},
            "claims": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "field_path": {"type": "string"},
                        "property": {
                            "type": "string",
                            "enum": sorted(SEMANTIC_PROPERTIES),
                        },
                        "value": {"type": ["string", "number", "boolean", "null"]},
                        "evidence_refs": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "uncertainty_reason": {"type": ["string", "null"]},
                    },
                    "required": [
                        "field_path",
                        "property",
                        "value",
                        "evidence_refs",
                        "confidence",
                        "uncertainty_reason",
                    ],
                },
            },
            "notes": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["task_id", "claims", "notes"],
    }


DATASET_REASONER_SYSTEM_PROMPT = """You are the single dataset-level semantic reasoner in an architecture experiment.
Use the complete observation payload jointly. Emit property-level candidate claims only for fields and properties listed in targets.
Never create fields or physical_type claims. Cite only exact evidence_id values from evidence_catalog.
For logical_type claims, value must be one of the exact strings in allowed_logical_types.
When allowed_semantic_types or allowed_units are present, use their exact canonical strings. Normalize listed unit_aliases before emitting a unit; use no claim rather than inventing an out-of-vocabulary value.
Evidence citation is not truth verification. Prefer no claim over an unsupported claim. Return strict JSON matching the schema."""


LEGACY_SYSTEM_PROMPT = """You are an evidence-constrained semantic schema annotator. Return strict JSON only. Do not include markdown, reasoning trace, or commentary outside the JSON object. Use the provided task_id exactly. Only use logical_type values from the allowed_logical_types list. The top-level JSON object must contain exactly these keys: task_id, annotations, conflicts, notes. Do not echo the input task object. Only annotate fields listed in annotation_targets. For any non-unknown semantic_type, logical_type override, or unit claim, include at least one supporting_evidence item. Each supporting_evidence item must be an evidence id from the field's available_evidence list, such as F1 or S1. Treat logical_type and semantic_type as separate decisions: if evidence supports a logical role such as measurement, identifier, coordinate, label, or attribute but does not support a precise semantic_type, set logical_type and keep semantic_type as unknown. Use semantic_logical_hint when it is present and evidence does not contradict it; for example a postal zone code is an identifier, not a label. Field descriptions like 'numeric observations with non-detect markers' support logical_type measurement even when the physical_type must remain string and semantic_type remains unknown. If evidence is insufficient, keep semantic_type as unknown and explain uncertainty_reason."""


def parse_reasoner_claims(
    response: Dict[str, Any],
    observation_payload: Dict[str, Any],
    *,
    source: str,
) -> Tuple[List[PropertyClaim], List[Dict[str, Any]]]:
    issues: List[Dict[str, Any]] = []
    claims: List[PropertyClaim] = []
    if not isinstance(response, dict):
        return [], [
            {"code": "invalid_top_level", "detail": "response is not an object"}
        ]
    expected_keys = {"task_id", "claims", "notes"}
    if set(response) != expected_keys:
        issues.append(
            {
                "code": "invalid_top_level_keys",
                "missing": sorted(expected_keys - set(response)),
                "unexpected": sorted(set(response) - expected_keys),
            }
        )
    if response.get("task_id") != observation_payload["task_id"]:
        issues.append(
            {"code": "task_id_mismatch", "detail": str(response.get("task_id"))}
        )
    if not isinstance(response.get("claims"), list):
        issues.append({"code": "invalid_claims_container"})
    if not isinstance(response.get("notes"), list) or any(
        not isinstance(note, str) for note in response.get("notes", [])
    ):
        issues.append({"code": "invalid_notes_container"})
    if issues:
        return [], issues
    target_map = {
        item["field_path"]: set(item["allowed_properties"])
        for item in observation_payload["targets"]
    }
    seen: set[Tuple[str, str]] = set()
    for ordinal, item in enumerate(response.get("claims", []), start=1):
        if not isinstance(item, dict):
            issues.append(
                {
                    "code": "invalid_claim_shape",
                    "detail": f"claim {ordinal} is not an object",
                }
            )
            continue
        required_claim_keys = {
            "field_path",
            "property",
            "value",
            "evidence_refs",
            "confidence",
            "uncertainty_reason",
        }
        if set(item) != required_claim_keys:
            issues.append(
                {
                    "code": "invalid_claim_keys",
                    "claim_index": ordinal,
                    "missing": sorted(required_claim_keys - set(item)),
                    "unexpected": sorted(set(item) - required_claim_keys),
                }
            )
            continue
        field_path = item.get("field_path")
        property_name = item.get("property")
        key = (str(field_path), str(property_name))
        if field_path not in target_map:
            issues.append({"code": "out_of_scope_field", "field_path": field_path})
            continue
        if (
            property_name not in target_map[field_path]
            or property_name not in SEMANTIC_PROPERTIES
        ):
            issues.append(
                {
                    "code": "out_of_scope_property",
                    "field_path": field_path,
                    "property": property_name,
                }
            )
            continue
        if key in seen:
            issues.append(
                {
                    "code": "duplicate_claim",
                    "field_path": field_path,
                    "property": property_name,
                }
            )
            continue
        seen.add(key)
        confidence = item.get("confidence")
        if (
            not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0 <= float(confidence) <= 1
        ):
            issues.append(
                {
                    "code": "invalid_confidence",
                    "field_path": field_path,
                    "property": property_name,
                }
            )
            continue
        refs = item.get("evidence_refs")
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
            issues.append(
                {
                    "code": "invalid_evidence_refs",
                    "field_path": field_path,
                    "property": property_name,
                }
            )
            continue
        value = item.get("value")
        if property_name == "logical_type" and value not in ALLOWED_LOGICAL_TYPES:
            issues.append(
                {
                    "code": "invalid_logical_type",
                    "field_path": field_path,
                    "value": value,
                }
            )
            continue
        if value in EMPTY_VALUES and not item.get("uncertainty_reason"):
            issues.append(
                {
                    "code": "abstention_without_reason",
                    "field_path": field_path,
                    "property": property_name,
                }
            )
            continue
        present = _is_present(value)
        claims.append(
            PropertyClaim(
                claim_id=_claim_id(
                    source, str(field_path), str(property_name), ordinal
                ),
                field_path=str(field_path),
                property_name=str(property_name),
                value=value,
                source=source,
                evidence_refs=list(refs),
                confidence=float(confidence),
                verification_level="unverified",
                verification_status="not_checked",
                decision="accepted" if present else "abstained",
                decision_reason="reasoner candidate; no independent verification"
                if present
                else "reasoner abstained",
            )
        )
    return claims, issues


def _verify_claim(
    claim: PropertyClaim,
    catalog: Sequence[EvidenceItem],
    baseline: Sequence[PropertyClaim],
) -> PropertyClaim:
    if claim.decision != "accepted" or not _is_present(claim.value):
        claim.verification_level = "unverified"
        claim.verification_status = "not_checked"
        claim.decision = "abstained"
        claim.decision_reason = "reasoner abstention cannot be promoted by verification"
        return claim
    evidence_by_id = {item.evidence_id: item for item in catalog}
    if not claim.evidence_refs:
        claim.verification_level = "unverified"
        claim.verification_status = "unsupported"
        claim.decision = "abstained"
        claim.decision_reason = "no evidence references"
        return claim
    invalid_refs = [ref for ref in claim.evidence_refs if ref not in evidence_by_id]
    cross_field_refs = [
        ref
        for ref in claim.evidence_refs
        if ref in evidence_by_id
        and claim.field_path not in evidence_by_id[ref].applicable_field_paths
    ]
    if invalid_refs or cross_field_refs:
        claim.verification_level = "unverified"
        claim.verification_status = "unsupported"
        claim.decision = "abstained"
        claim.decision_reason = (
            f"invalid evidence refs={invalid_refs}; cross-field refs={cross_field_refs}"
        )
        return claim

    existing = next(
        (
            item
            for item in baseline
            if item.field_path == claim.field_path
            and item.property_name == claim.property_name
            and item.decision == "accepted"
        ),
        None,
    )
    existing_comparison_value = (
        normalize_unit_claim(str(existing.value), [])["canonical_unit"]
        if existing is not None and claim.property_name == "unit"
        else existing.value
        if existing is not None
        else None
    )
    claim_comparison_value = (
        normalize_unit_claim(str(claim.value), [])["canonical_unit"]
        if claim.property_name == "unit"
        else claim.value
    )
    if existing is not None and existing_comparison_value != claim_comparison_value:
        claim.verification_level = "deterministic_conflict_check"
        claim.verification_status = "contradicted"
        claim.decision = "rejected"
        claim.decision_reason = (
            f"contradicts accepted deterministic value {existing.value!r}"
        )
        return claim
    if existing is not None and existing_comparison_value == claim_comparison_value:
        claim.verification_level = "deterministically_verified"
        claim.verification_status = "verified"
        claim.decision = "accepted"
        claim.decision_reason = (
            "matches accepted deterministic claim and cites valid evidence"
        )
        return claim

    claim.verification_level = "evidence_grounded"
    claim.verification_status = "supported"
    claim.decision = "accepted"
    claim.decision_reason = "evidence references exist and are field-relevant; semantic entailment is not machine-verified"
    return claim


def _verify_claims(
    claims: Sequence[PropertyClaim],
    catalog: Sequence[EvidenceItem],
    baseline: Sequence[PropertyClaim],
) -> List[PropertyClaim]:
    verified = [_verify_claim(claim, catalog, baseline) for claim in claims]
    by_field: Dict[str, Dict[str, PropertyClaim]] = {}
    for claim in verified:
        if claim.decision == "accepted":
            by_field.setdefault(claim.field_path, {})[claim.property_name] = claim
    for field_claims in by_field.values():
        semantic = field_claims.get("semantic_type")
        logical = field_claims.get("logical_type")
        if semantic is None or logical is None:
            continue
        compatible = compatible_logical_types_from_semantic(str(semantic.value))
        if compatible and logical.value not in compatible:
            for claim in (semantic, logical):
                claim.verification_level = "deterministic_cross_claim_check"
                claim.verification_status = "conflicted"
                claim.decision = "abstained"
                claim.decision_reason = f"mutually incompatible semantic/logical claims; expected logical type in {sorted(compatible)}"
    return verified


def _exception_telemetry(exc: Exception) -> ModelTelemetry:
    telemetry = getattr(exc, "telemetry", None)
    if isinstance(telemetry, ModelTelemetry):
        return telemetry
    return ModelTelemetry(failed_calls=1)


def _error_response_records(exc: Exception, purpose: str) -> List[Dict[str, Any]]:
    preserved_records = getattr(exc, "response_records", None)
    if isinstance(preserved_records, list) and preserved_records:
        return json.loads(json.dumps(preserved_records))
    raw_text = str(getattr(exc, "raw_text", ""))
    if not raw_text:
        return []
    return [
        {
            "purpose": purpose,
            "request_hash": str(getattr(exc, "request_hash", "")),
            "response_hash": str(getattr(exc, "response_hash", ""))
            or _canonical_hash(raw_text),
            "raw_text": raw_text,
            "parsed_response": None,
            "telemetry": _exception_telemetry(exc).to_dict(),
            "model_info": getattr(exc, "model_info", {}),
            "error": str(exc),
        }
    ]


class ArchitectureVariant(Protocol):
    variant_id: str

    def run(
        self, case: ExperimentCase, backend: Optional[ModelBackend] = None
    ) -> VariantRun: ...


class DeterministicOnlyVariant:
    variant_id = "A"

    def run(
        self, case: ExperimentCase, backend: Optional[ModelBackend] = None
    ) -> VariantRun:
        return VariantRun(
            variant_id=self.variant_id,
            case_id=case.case_id,
            task_id=case.task_id,
            status="ok",
            claims=deterministic_claims(case.task_payload),
            evidence_catalog=build_evidence_catalog(case.task_payload),
            architecture={
                "deterministic": True,
                "dataset_reasoner_calls": 0,
                "verifier": "none",
            },
        )


class DatasetReasonerVariant:
    variant_id = "B"

    def _run_reasoner(
        self,
        case: ExperimentCase,
        backend: Optional[ModelBackend],
    ) -> Tuple[List[PropertyClaim], List[Dict[str, Any]], Optional[ModelCompletion]]:
        observation_payload = build_observation_payload(
            case.task_payload, case.annotation_vocabulary
        )
        if not observation_payload["targets"]:
            return [], [], None
        if backend is None:
            raise RuntimeError(
                f"variant {self.variant_id} requires a model backend for {case.case_id}"
            )
        completion = backend.complete(
            system_prompt=DATASET_REASONER_SYSTEM_PROMPT,
            payload=observation_payload,
            response_schema=dataset_reasoner_response_schema(),
            purpose=f"dataset_reasoner:{case.task_id}",
        )
        expected_calls = 0 if self.variant_id == "C" else 1
        if completion.telemetry.model_calls != expected_calls:
            raise ModelBackendError(
                f"variant {self.variant_id} expected {expected_calls} semantic generation calls but observed {completion.telemetry.model_calls}",
                telemetry=completion.telemetry,
                request_hash=completion.request_hash,
            )
        if self.variant_id == "C" and not completion.model_info.get(
            "shared_reasoner_replay"
        ):
            raise ModelBackendError(
                "variant C did not receive a replayed B response",
                telemetry=completion.telemetry,
                request_hash=completion.request_hash,
            )
        claims, issues = parse_reasoner_claims(
            completion.data,
            observation_payload,
            source="dataset_reasoner",
        )
        return claims, issues, completion

    def run(
        self, case: ExperimentCase, backend: Optional[ModelBackend] = None
    ) -> VariantRun:
        baseline = deterministic_claims(case.task_payload)
        catalog = build_evidence_catalog(case.task_payload)
        try:
            model_claims, issues, completion = self._run_reasoner(case, backend)
        except Exception as exc:  # noqa: BLE001
            return VariantRun(
                variant_id=self.variant_id,
                case_id=case.case_id,
                task_id=case.task_id,
                status="partial",
                claims=baseline,
                evidence_catalog=catalog,
                telemetry=_exception_telemetry(exc),
                model_responses=_error_response_records(
                    exc, f"dataset_reasoner:{case.task_id}"
                ),
                issues=[
                    {
                        "code": "dataset_reasoner_failed",
                        "detail": str(exc),
                        "request_hash": getattr(exc, "request_hash", ""),
                        "replayed_failure": bool(getattr(exc, "replayed", False)),
                    }
                ],
                architecture={
                    "deterministic": True,
                    "dataset_reasoner_max_calls": 1,
                    "verifier": "none",
                },
            )
        telemetry = completion.telemetry if completion is not None else ModelTelemetry()
        model_info = completion.model_info if completion is not None else {}
        model_responses = (
            [completion.to_record(f"dataset_reasoner:{case.task_id}")]
            if completion is not None
            else []
        )
        if issues:
            return VariantRun(
                variant_id=self.variant_id,
                case_id=case.case_id,
                task_id=case.task_id,
                status="partial",
                claims=baseline,
                evidence_catalog=catalog,
                telemetry=telemetry,
                issues=issues,
                model_info=model_info,
                model_responses=model_responses,
                architecture={
                    "deterministic": True,
                    "dataset_reasoner_max_calls": 1,
                    "verifier": "none",
                },
            )
        return VariantRun(
            variant_id=self.variant_id,
            case_id=case.case_id,
            task_id=case.task_id,
            status="ok",
            claims=baseline + model_claims,
            evidence_catalog=catalog,
            telemetry=telemetry,
            issues=issues,
            model_info=model_info,
            model_responses=model_responses,
            architecture={
                "deterministic": True,
                "dataset_reasoner_max_calls": 1,
                "verifier": "none",
            },
        )


class DatasetReasonerWithVerifierVariant(DatasetReasonerVariant):
    variant_id = "C"

    def run(
        self, case: ExperimentCase, backend: Optional[ModelBackend] = None
    ) -> VariantRun:
        baseline = deterministic_claims(case.task_payload)
        catalog = build_evidence_catalog(case.task_payload)
        try:
            model_claims, issues, completion = self._run_reasoner(case, backend)
        except Exception as exc:  # noqa: BLE001
            return VariantRun(
                variant_id=self.variant_id,
                case_id=case.case_id,
                task_id=case.task_id,
                status="partial",
                claims=baseline,
                evidence_catalog=catalog,
                telemetry=_exception_telemetry(exc),
                model_responses=_error_response_records(
                    exc, f"dataset_reasoner:{case.task_id}"
                ),
                issues=[
                    {
                        "code": "dataset_reasoner_failed",
                        "detail": str(exc),
                        "request_hash": getattr(exc, "request_hash", ""),
                        "replayed_failure": bool(getattr(exc, "replayed", False)),
                    }
                ],
                architecture={
                    "deterministic": True,
                    "dataset_reasoner_max_calls": 1,
                    "semantic_generation_calls": 0,
                    "reused_response_hash": str(
                        getattr(exc, "response_hash", "")
                    )
                    or (
                        _canonical_hash(str(getattr(exc, "raw_text", "")))
                        if getattr(exc, "raw_text", "")
                        else None
                    ),
                    "verifier": "deterministic_evidence_reference_and_conflict_checks",
                },
            )
        telemetry = completion.telemetry if completion is not None else ModelTelemetry()
        model_info = completion.model_info if completion is not None else {}
        model_responses = (
            [completion.to_record(f"dataset_reasoner:{case.task_id}")]
            if completion is not None
            else []
        )
        if issues:
            return VariantRun(
                variant_id=self.variant_id,
                case_id=case.case_id,
                task_id=case.task_id,
                status="partial",
                claims=baseline,
                evidence_catalog=catalog,
                telemetry=telemetry,
                issues=issues,
                model_info=model_info,
                model_responses=model_responses,
                architecture={
                    "deterministic": True,
                    "dataset_reasoner_max_calls": 1,
                    "semantic_generation_calls": 0,
                    "reused_response_hash": completion.response_hash
                    if completion is not None
                    else None,
                    "verifier": "deterministic_evidence_reference_and_conflict_checks",
                },
            )
        verified_claims = _verify_claims(model_claims, catalog, baseline)
        return VariantRun(
            variant_id=self.variant_id,
            case_id=case.case_id,
            task_id=case.task_id,
            status="ok",
            claims=baseline + verified_claims,
            evidence_catalog=catalog,
            telemetry=telemetry,
            issues=issues,
            model_info=model_info,
            model_responses=model_responses,
            architecture={
                "deterministic": True,
                "dataset_reasoner_max_calls": 1,
                "semantic_generation_calls": 0,
                "reused_response_hash": completion.response_hash
                if completion is not None
                else None,
                "verifier": "deterministic_evidence_reference_and_conflict_checks",
                "verification_independence": "failure-mode independent from the model; no second-model truth claim",
            },
        )


def _legacy_refs_to_global(
    field_path: str, refs: Iterable[str], task_payload: Dict[str, Any]
) -> List[str]:
    task = task_payload["task"]
    field = next(
        item
        for item in task["deterministic_schema"].get("fields", [])
        if item["field_path"] == field_path
    )
    matching_snippets: List[int] = []
    for index, snippet in enumerate(task.get("grounding_snippets", []), start=1):
        if _mentions_field(
            str(snippet.get("text", "")), field.get("field_name"), field_path
        ):
            matching_snippets.append(index)
    converted: List[str] = []
    for ref in refs:
        if ref.startswith("F") and ref[1:].isdigit():
            converted.append(f"{field_path}::{ref}")
        elif ref.startswith("S") and ref[1:].isdigit():
            local_index = int(ref[1:]) - 1
            converted.append(
                f"S{matching_snippets[local_index]}"
                if local_index < len(matching_snippets)
                else ref
            )
        else:
            converted.append(ref)
    return converted


class LegacyPerFieldVariant:
    variant_id = "D"

    def _live_result(
        self,
        case: ExperimentCase,
        backend: Optional[ModelBackend],
    ) -> Tuple[Dict[str, Any], ModelTelemetry, Dict[str, Any], List[Dict[str, Any]]]:
        if backend is None:
            raise RuntimeError(
                f"variant {self.variant_id} requires a model backend for {case.case_id}"
            )
        compact = compact_task_payload(case.task_payload)
        target_fields = compact["task"]["annotation_targets"]
        path_groups = grouped_field_sets(case.task_id, target_fields)
        raw_results: List[Dict[str, Any]] = []
        response_records: List[Dict[str, Any]] = []
        telemetry = ModelTelemetry()
        model_info: Dict[str, Any] = {}
        for group_index, paths in enumerate(path_groups):
            field_payload = compact_task_payload(case.task_payload, paths)
            legacy_method = getattr(backend, "complete_legacy", None)
            purpose = f"legacy_per_field:{case.task_id}:{group_index}"
            try:
                if legacy_method is not None:
                    completion = legacy_method(
                        payload=field_payload,
                        response_schema=response_json_schema(),
                        purpose=purpose,
                    )
                else:
                    completion = backend.complete(
                        system_prompt=LEGACY_SYSTEM_PROMPT,
                        payload=field_payload,
                        response_schema=response_json_schema(),
                        purpose=purpose,
                    )
            except Exception as exc:  # noqa: BLE001
                telemetry.add(_exception_telemetry(exc))
                response_records.extend(_error_response_records(exc, purpose))
                raise ModelBackendError(
                    str(exc),
                    telemetry=telemetry,
                    request_hash=str(getattr(exc, "request_hash", "")),
                    response_records=response_records,
                ) from exc
            telemetry.add(completion.telemetry)
            model_info = completion.model_info
            raw_results.append(completion.data)
            response_records.append(
                completion.to_record(f"legacy_per_field:{case.task_id}:{group_index}")
            )
        raw_result = aggregate_field_results(case.task_id, raw_results)
        normalized = normalize_annotation_result(raw_result, case.task_payload)
        return normalized, telemetry, model_info, response_records

    def run(
        self, case: ExperimentCase, backend: Optional[ModelBackend] = None
    ) -> VariantRun:
        baseline = deterministic_claims(case.task_payload)
        catalog = build_evidence_catalog(case.task_payload)
        issues: List[Dict[str, Any]] = []
        if case.legacy_result is not None:
            result = case.legacy_result.get("result", case.legacy_result)
            telemetry = ModelTelemetry()
            model_info = case.legacy_result.get("model_info", {})
            model_responses = [
                {
                    "purpose": f"legacy_replay:{case.task_id}",
                    "request_hash": "",
                    "response_hash": _canonical_hash(result),
                    "raw_text": json.dumps(result, ensure_ascii=False),
                    "parsed_response": result,
                    "telemetry": telemetry.to_dict(),
                    "model_info": {**model_info, "historical_replay": True},
                }
            ]
            issues.append(
                {
                    "code": "legacy_replay_telemetry_unavailable",
                    "detail": "historical replay does not contain reliable call/token/latency telemetry",
                }
            )
        elif case.legacy_replay_required:
            return VariantRun(
                variant_id=self.variant_id,
                case_id=case.case_id,
                task_id=case.task_id,
                status="failed",
                claims=baseline,
                evidence_catalog=catalog,
                issues=[
                    {
                        "code": "legacy_replay_missing",
                        "detail": "replay mode was requested but this case has no historical result artifact",
                    }
                ],
                architecture={
                    "deterministic": True,
                    "reasoner": "legacy replay unavailable",
                    "verifier": "not run",
                },
            )
        else:
            try:
                result, telemetry, model_info, model_responses = self._live_result(
                    case, backend
                )
            except Exception as exc:  # noqa: BLE001
                return VariantRun(
                    variant_id=self.variant_id,
                    case_id=case.case_id,
                    task_id=case.task_id,
                    status="partial",
                    claims=baseline,
                    evidence_catalog=catalog,
                    telemetry=_exception_telemetry(exc),
                    model_responses=_error_response_records(
                        exc, f"legacy_per_field:{case.task_id}"
                    ),
                    issues=[
                        {
                            "code": "legacy_reasoner_failed",
                            "detail": str(exc),
                            "request_hash": getattr(exc, "request_hash", ""),
                        }
                    ],
                    architecture={
                        "deterministic": True,
                        "reasoner": "legacy per-field/manual-group scheduler",
                        "verifier": "legacy shape validation and merge",
                    },
                )

        validation_errors = validate_annotation_result(result, case.task_payload)
        issues.extend(
            {"code": "legacy_validation_error", "detail": error}
            for error in validation_errors
        )
        deterministic_schema = case.task_payload["task"]["deterministic_schema"]
        merged = merge_annotation_result(deterministic_schema, result, model_info)
        merged_fields = {item["field_path"]: item for item in merged.get("fields", [])}
        model_claims: List[PropertyClaim] = []
        for annotation_index, annotation in enumerate(
            result.get("annotations", []), start=1
        ):
            field_path = str(annotation.get("field_path"))
            if field_path not in merged_fields:
                continue
            refs = _legacy_refs_to_global(
                field_path, annotation.get("supporting_evidence", []), case.task_payload
            )
            for property_name in SEMANTIC_PROPERTIES:
                value = annotation.get(property_name)
                if not _is_present(value):
                    continue
                accepted = (
                    bool(annotation.get("supporting_evidence"))
                    and merged_fields[field_path].get(property_name) == value
                )
                model_claims.append(
                    PropertyClaim(
                        claim_id=_claim_id(
                            "D", field_path, property_name, annotation_index
                        ),
                        field_path=field_path,
                        property_name=property_name,
                        value=value,
                        source="legacy_per_field_reasoner",
                        evidence_refs=refs,
                        confidence=float(annotation.get("confidence", 0.0)),
                        verification_level="unverified",
                        verification_status="not_checked",
                        decision="accepted" if accepted else "rejected",
                        decision_reason=(
                            "legacy merge accepted a non-empty evidence string"
                            if accepted
                            else "legacy merge rejected or conflicted with deterministic output"
                        ),
                    )
                )
        return VariantRun(
            variant_id=self.variant_id,
            case_id=case.case_id,
            task_id=case.task_id,
            status="partial" if validation_errors else "ok",
            claims=baseline + model_claims,
            evidence_catalog=catalog,
            telemetry=telemetry,
            issues=issues,
            model_info=model_info,
            model_responses=model_responses,
            architecture={
                "deterministic": True,
                "reasoner": "legacy per-field/manual-group scheduler",
                "verifier": "legacy shape validation and merge",
                "known_boundary": "non-empty evidence strings are not referentially validated",
            },
        )


VARIANTS: Dict[str, ArchitectureVariant] = {
    "A": DeterministicOnlyVariant(),
    "B": DatasetReasonerVariant(),
    "C": DatasetReasonerWithVerifierVariant(),
    "D": LegacyPerFieldVariant(),
}


def run_variant(
    variant_id: str,
    case: ExperimentCase,
    backend: Optional[ModelBackend] = None,
) -> VariantRun:
    normalized = variant_id.upper()
    if normalized not in VARIANTS:
        raise ValueError(f"unknown architecture variant: {variant_id}")
    return VARIANTS[normalized].run(case, backend)
