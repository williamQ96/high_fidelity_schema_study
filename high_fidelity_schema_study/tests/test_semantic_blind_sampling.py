from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest
import high_fidelity_schema_study.semantic_catalog_acquisition as catalog_adapter

from high_fidelity_schema_study.semantic_blind_sampling import (
    BlindSamplingError,
    build_blind_selection,
    build_known_nonblind_registry,
    canonical_source_identity,
    preflight_sampling_design,
    sha256_file,
    validate_acquisition_log,
    validate_blind_selection,
    validate_candidate_frame,
    validate_known_nonblind_registry,
)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def task_payload(candidate_id: str) -> dict:
    return {
        "task": {
            "task_id": f"blind-candidate::{candidate_id}",
            "dataset_id": candidate_id,
            "file_format": "csv",
            "data_modality": "tabular",
            "deterministic_schema": {
                "fields": [
                    {
                        "field_name": "temperature",
                        "field_path": "temperature",
                        "physical_type": "float",
                        "logical_type": "unknown",
                        "semantic_type": "unknown",
                        "unit": None,
                        "confidence": 0.8,
                        "source_evidence": [
                            {
                                "evidence_type": "csv_header",
                                "source": f"{candidate_id}.csv",
                                "detail": "header='temperature'",
                            }
                        ],
                    }
                ],
                "metadata": {},
            },
            "grounding_snippets": [
                {
                    "source_type": "approved_documentation",
                    "source_name": "README.md",
                    "detail": "variables:temperature",
                    "text": "temperature is a measured environmental variable",
                    "priority": 1,
                }
            ],
            "instructions": [],
        }
    }


def build_fixture(tmp_path: Path) -> dict[str, Path]:
    known_path = tmp_path / "known.json"
    frame_path = tmp_path / "frame.json"
    acquisition_path = tmp_path / "acquisition.json"
    power_path = tmp_path / "power.json"
    design_path = tmp_path / "design.json"
    receipt_path = tmp_path / "receipt.json"
    output_path = tmp_path / "selection.json"
    adapter_path = Path(catalog_adapter.__file__).resolve()
    snapshot_paths = {
        "zenodo": tmp_path / "zenodo-catalog.json",
        "dryad": tmp_path / "dryad-catalog.json",
    }
    construction_path = tmp_path / "known-construction.json"
    known_task_path = tmp_path / "known-task.json"
    write_json(construction_path, {"scope": "fixture known resources"})
    write_json(known_task_path, {"task_id": "known-task"})
    known_task_sha256 = sha256_file(known_task_path)
    known_source_identity = canonical_source_identity(
        "zenodo", "record_known", "known-resource.csv"
    )
    write_json(
        known_path,
        {
            "schema_version": "semantic-known-nonblind-resources/v1",
            "status": "frozen_before_candidate_frame",
            "source_identity_algorithm": "canonical_source_tuple_sha256/v1",
            "frozen_at": "2026-07-16T00:00:00Z",
            "construction_sources": [
                {
                    "file": construction_path.name,
                    "sha256": sha256_file(construction_path),
                }
            ],
            "generator": {
                "file": construction_path.name,
                "sha256": sha256_file(construction_path),
            },
            "coverage": {
                "total_record_count": 1,
                "resource_hash_available_count": 0,
                "source_identity_count": 1,
            },
            "source_identities": [known_source_identity],
            "task_sha256s": [known_task_sha256],
            "resource_sha256s": [],
            "records": [
                {
                    "source_identity": known_source_identity,
                    "source_repository": "zenodo",
                    "source_record_id": "record_known",
                    "source_resource_id": "known-resource.csv",
                    "task": {
                        "file": known_task_path.name,
                        "sha256": known_task_sha256,
                    },
                    "resource_available_at_freeze": False,
                    "resource": None,
                    "resource_absence_reason": "not retained in fixture",
                }
            ],
        },
    )
    specs = [
        {
            "candidate_id": "candidate-a",
            "dataset_group_id": "zenodo::concept::201",
            "repository": "zenodo",
            "source_record_id": "record_101",
            "source_resource_id": "candidate-a.csv",
            "family": "atmosphere",
            "file_format": "csv",
        },
        {
            "candidate_id": "candidate-b",
            "dataset_group_id": "dryad::10.5061_dryad.fixtureb",
            "repository": "dryad",
            "source_record_id": "10.5061_dryad.fixtureb",
            "source_resource_id": "candidate-b.csv",
            "family": "ocean",
            "file_format": "csv",
        },
        {
            "candidate_id": "candidate-c",
            "dataset_group_id": "dryad::10.5061_dryad.fixturec",
            "repository": "dryad",
            "source_record_id": "10.5061_dryad.fixturec",
            "source_resource_id": "candidate-c.h5",
            "family": "climate",
            "file_format": "hdf5",
        },
        {
            "candidate_id": "candidate-d",
            "dataset_group_id": "zenodo::concept::204",
            "repository": "zenodo",
            "source_record_id": "record_104",
            "source_resource_id": "candidate-d.h5",
            "family": "hydrology",
            "file_format": "hdf5",
        },
    ]
    candidates = []
    acquisition_records = []
    resources_by_candidate: dict[str, Path] = {}
    for spec in specs:
        candidate_id = spec["candidate_id"]
        group_id = spec["dataset_group_id"]
        repository = spec["repository"]
        source_record_id = spec["source_record_id"]
        source_resource_id = spec["source_resource_id"]
        family = spec["family"]
        stratum = spec["file_format"]
        resource_path = tmp_path / source_resource_id
        resources_by_candidate[candidate_id] = resource_path
        task_path = tmp_path / f"{candidate_id}.task.json"
        source_path = tmp_path / f"{candidate_id}.source.json"
        resource_path.write_text(f"resource:{candidate_id}\n", encoding="utf-8")
        write_json(task_path, task_payload(candidate_id))
        write_json(source_path, {"candidate_id": candidate_id, "sources": []})
        candidates.append(
            {
                "candidate_id": candidate_id,
                "dataset_group_id": group_id,
                "source_identity": canonical_source_identity(
                    repository, source_record_id, source_resource_id
                ),
                "source_repository": repository,
                "source_record_id": source_record_id,
                "source_resource_id": source_resource_id,
                "source_url": (
                    f"https://zenodo.org/api/records/{source_record_id.removeprefix('record_')}/files/{source_resource_id}/content"
                    if repository == "zenodo"
                    else f"https://datadryad.org/api/v2/files/{candidate_id}/download"
                ),
                "acquired_at": "2026-07-16T00:00:00Z",
                "scientific_family": family,
                "file_format": stratum,
                "selection_stratum": stratum,
                "license": "CC-BY-4.0",
                "resource": {
                    "file": resource_path.name,
                    "sha256": sha256_file(resource_path),
                },
                "task": {
                    "file": task_path.name,
                    "sha256": sha256_file(task_path),
                },
                "source_bundle": {
                    "file": source_path.name,
                    "sha256": sha256_file(source_path),
                },
                "semantic_opportunity_target_count": 1,
                "eligibility": {
                    "eligible": True,
                    "reasons": [],
                    "criterion_results": {
                        "supported_local_format": True,
                        "known_nonblind_overlap": False,
                    },
                },
            }
        )
        acquisition_records.append(
            {
                "candidate_id": candidate_id,
                "dataset_group_id": group_id,
                "source_identity": canonical_source_identity(
                    repository, source_record_id, source_resource_id
                ),
                "source_repository": repository,
                "source_record_id": source_record_id,
                "source_resource_id": source_resource_id,
                "source_url": (
                    f"https://zenodo.org/api/records/{source_record_id.removeprefix('record_')}/files/{source_resource_id}/content"
                    if repository == "zenodo"
                    else f"https://datadryad.org/api/v2/files/{candidate_id}/download"
                ),
                "source_size_bytes": resource_path.stat().st_size,
                "provider_checksum": (
                    f"md5:{hashlib.md5(resource_path.read_bytes()).hexdigest()}"
                    if repository == "zenodo"
                    else f"sha-256:{sha256_file(resource_path)}"
                ),
                "discovered_at": "2026-07-16T00:00:00Z",
                "scientific_family": family,
                "file_format": stratum,
                "selection_stratum": stratum,
                "license": "CC-BY-4.0",
                "catalog_snapshot_id": f"snapshot::{repository}",
                "criterion_results": {
                    "supported_fixture_resource": True,
                    "oversize_resource": False,
                },
                "eligible_for_acquisition": True,
                "reasons": [],
                "acquisition_status": "acquired",
                "acquired_at": "2026-07-16T00:00:00Z",
                "resource": {
                    "file": resource_path.name,
                    "sha256": sha256_file(resource_path),
                },
                "failure": None,
            }
        )
    zenodo_specs = [spec for spec in specs if spec["repository"] == "zenodo"]
    dryad_specs = [spec for spec in specs if spec["repository"] == "dryad"]
    write_json(
        snapshot_paths["zenodo"],
        {
            "schema_version": "semantic-catalog-snapshot/v1",
            "adapter_id": catalog_adapter.ADAPTER_ID,
            "source_repository": "zenodo",
            "page_ordinal": 1,
            "request_url": "https://zenodo.org/api/records?page=1",
            "retrieved_at": "2026-07-16T00:00:00Z",
            "raw_catalog_response": {
                "hits": {
                    "hits": [
                        {
                            "id": spec["source_record_id"].removeprefix("record_"),
                            "conceptrecid": spec["dataset_group_id"].split("::")[-1],
                            "metadata": {
                                "rights": [{"id": "CC-BY-4.0"}],
                                "subjects": [{"subject": spec["family"]}],
                            },
                            "files": [
                                {
                                    "key": spec["source_resource_id"],
                                    "size": resources_by_candidate[spec["candidate_id"]]
                                    .stat()
                                    .st_size,
                                    "checksum": f"md5:{hashlib.md5(resources_by_candidate[spec['candidate_id']].read_bytes()).hexdigest()}",
                                    "links": {
                                        "self": f"https://zenodo.org/api/records/{spec['source_record_id'].removeprefix('record_')}/files/{spec['source_resource_id']}/content"
                                    },
                                }
                            ],
                        }
                        for spec in zenodo_specs
                    ]
                }
            },
        },
    )
    write_json(
        snapshot_paths["dryad"],
        {
            "schema_version": "semantic-catalog-snapshot/v1",
            "adapter_id": catalog_adapter.ADAPTER_ID,
            "source_repository": "dryad",
            "page_ordinal": 1,
            "request_url": "https://datadryad.org/api/v2/search?page=1",
            "retrieved_at": "2026-07-16T00:00:00Z",
            "raw_catalog_response": {
                "_embedded": {
                    "stash:datasets": [
                        {
                            "identifier": f"doi:{spec['source_record_id'].replace('_', '/', 1)}",
                            "license": "CC-BY-4.0",
                            "fieldOfScience": spec["family"],
                        }
                        for spec in dryad_specs
                    ]
                }
            },
            "dataset_expansions": [
                {
                    "identifier": f"doi:{spec['source_record_id'].replace('_', '/', 1)}",
                    "files_response": {
                        "_embedded": {
                            "stash:files": [
                                {
                                    "path": spec["source_resource_id"],
                                    "size": resources_by_candidate[spec["candidate_id"]]
                                    .stat()
                                    .st_size,
                                    "digest": sha256_file(
                                        resources_by_candidate[spec["candidate_id"]]
                                    ),
                                    "digestType": "sha-256",
                                    "_links": {
                                        "stash:download": {
                                            "href": f"/api/v2/files/{spec['candidate_id']}/download"
                                        }
                                    },
                                }
                            ]
                        }
                    },
                }
                for spec in dryad_specs
            ],
        },
    )
    repositories = ["zenodo", "dryad"]
    write_json(
        acquisition_path,
        {
            "schema_version": "semantic-blind-acquisition-log/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "frozen_before_candidate_frame",
            "frozen_at": "2026-07-16T00:00:00Z",
            "construction_boundary": {
                "model_outputs_consulted": False,
                "architecture_results_consulted": False,
                "gold_labels_created": False,
            },
            "enumeration": {
                "adapter": {
                    "adapter_id": catalog_adapter.ADAPTER_ID,
                    "implementation": {
                        "file": str(adapter_path),
                        "sha256": sha256_file(adapter_path),
                    },
                },
                "retrieval_cutoff": "2026-07-16T00:00:00Z",
                "source_repositories": repositories,
                "catalog_snapshots": [
                    {
                        "snapshot_id": f"snapshot::{repository}",
                        "source_repository": repository,
                        "page_ordinal": 1,
                        "request_url": (
                            "https://zenodo.org/api/records?page=1"
                            if repository == "zenodo"
                            else "https://datadryad.org/api/v2/search?page=1"
                        ),
                        "retrieved_at": "2026-07-16T00:00:00Z",
                        "returned_dataset_record_count": 2,
                        "enumerated_resource_count": 2,
                        "response": {
                            "file": snapshot_paths[repository].name,
                            "sha256": sha256_file(snapshot_paths[repository]),
                        },
                    }
                    for repository in repositories
                ],
                "repository_boundaries": [
                    {
                        "source_repository": repository,
                        "last_page_ordinal": 1,
                        "termination_reason": "frozen_page_cap_reached",
                    }
                    for repository in repositories
                ],
            },
            "acquisition_criteria": {
                "inclusion": [
                    {
                        "criterion_id": "supported_fixture_resource",
                        "description": "resource is supported by the fixture",
                        "assessment_method": "deterministic fixture check",
                    }
                ],
                "exclusion": [
                    {
                        "criterion_id": "oversize_resource",
                        "description": "resource exceeds the fixture size cap",
                        "assessment_method": "deterministic byte-size check",
                    }
                ],
            },
            "counts": {
                "enumerated_resource_count": 4,
                "eligible_for_acquisition_count": 4,
                "acquired_count": 4,
                "download_failed_count": 0,
                "excluded_before_download_count": 0,
            },
            "records": acquisition_records,
        },
    )
    write_json(
        frame_path,
        {
            "schema_version": "semantic-blind-candidate-frame/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "frozen_before_selection",
            "frozen_at": "2026-07-16T00:00:00Z",
            "construction_boundary": {
                "model_outputs_consulted": False,
                "architecture_results_consulted": False,
                "gold_labels_created": False,
                "eligibility_decided_before_selection": True,
            },
            "frame_definition": {
                "source_identity_algorithm": "canonical_source_tuple_sha256/v1",
                "scope_statement": "All eligible records in the frozen test catalog.",
                "candidate_unit": "one local scientific data resource",
                "enumeration_method": "enumerate every record in the fixture catalog",
                "retrieval_cutoff": "2026-07-16T00:00:00Z",
                "source_repositories": ["zenodo", "dryad"],
                "inclusion_criteria": [
                    {
                        "criterion_id": "supported_local_format",
                        "description": "resource has a supported local format",
                        "assessment_method": "deterministic suffix and parser check",
                    }
                ],
                "exclusion_criteria": [
                    {
                        "criterion_id": "known_nonblind_overlap",
                        "description": "resource hash or source identity is known non-blind",
                        "assessment_method": "deterministic hash or identity membership",
                    }
                ],
            },
            "known_nonblind_resources": {
                "file": known_path.name,
                "sha256": sha256_file(known_path),
            },
            "acquisition_log": {
                "file": acquisition_path.name,
                "sha256": sha256_file(acquisition_path),
            },
            "candidates": candidates,
        },
    )
    write_json(
        power_path,
        {
            "schema_version": "semantic-power-analysis/v2",
            "status": "frozen",
            "assumptions": {
                "required_dataset_count": 2,
                "required_semantic_opportunity_case_count": 2,
            },
        },
    )
    write_json(
        design_path,
        {
            "schema_version": "semantic-blind-sampling-design/v1",
            "protocol_version": "semantic-architecture-protocol/v1",
            "status": "frozen_before_selection",
            "design_id": "blind-sampling-round-1",
            "candidate_frame": {
                "file": frame_path.name,
                "sha256": sha256_file(frame_path),
            },
            "power_analysis": {
                "file": power_path.name,
                "sha256": sha256_file(power_path),
            },
            "selection_algorithm": "stratum_ordered_sha256_priority_with_frozen_caps/v1",
            "selection_seed": "registered-test-seed",
            "seed_provenance": {
                "method": "externally registered literal",
                "source": "test append-only registry",
                "committed_before_selection": True,
            },
            "required_dataset_count": 2,
            "required_semantic_opportunity_case_count": 2,
            "stratum_quotas": {"csv": 1, "hdf5": 1},
            "minimum_scientific_family_count": 2,
            "maximum_cases_per_dataset_group": 1,
            "maximum_cases_per_source_repository": 1,
        },
    )
    write_json(
        receipt_path,
        {
            "schema_version": "semantic-sampling-registration-receipt/v1",
            "design_sha256": sha256_file(design_path),
            "registered_at": "2026-07-16T01:00:00Z",
            "registry": "test-append-only-registry",
            "registration_identifier": "sampling-fixture-1",
            "frozen_before_selection": True,
            "selection_not_executed_at_registration": True,
        },
    )
    return {
        "known": known_path,
        "acquisition": acquisition_path,
        "frame": frame_path,
        "power": power_path,
        "design": design_path,
        "receipt": receipt_path,
        "selection": output_path,
    }


def test_sampling_design_preflight_requires_no_gold_or_model_output(
    tmp_path: Path,
) -> None:
    paths = build_fixture(tmp_path)

    report = preflight_sampling_design(paths["design"])

    assert report["status"] == "ready_for_external_registration"
    assert report["eligible_candidate_count"] == 4
    assert report["not_a_registration_receipt"] is True


def test_acquisition_log_rejects_catalog_page_gap(tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    acquisition = json.loads(paths["acquisition"].read_text(encoding="utf-8"))
    acquisition["enumeration"]["catalog_snapshots"][0]["page_ordinal"] = 2
    acquisition["enumeration"]["repository_boundaries"][0]["last_page_ordinal"] = 2
    response_record = acquisition["enumeration"]["catalog_snapshots"][0]["response"]
    response_path = tmp_path / response_record["file"]
    response = json.loads(response_path.read_text(encoding="utf-8"))
    response["page_ordinal"] = 2
    write_json(response_path, response)
    response_record["sha256"] = sha256_file(response_path)
    write_json(paths["acquisition"], acquisition)

    with pytest.raises(BlindSamplingError, match="complete and contiguous"):
        validate_acquisition_log(paths["acquisition"])


def test_acquisition_eligibility_is_mechanically_derived(tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    acquisition = json.loads(paths["acquisition"].read_text(encoding="utf-8"))
    acquisition["records"][0]["criterion_results"]["supported_fixture_resource"] = False
    write_json(paths["acquisition"], acquisition)

    with pytest.raises(BlindSamplingError, match="mechanically derived"):
        validate_acquisition_log(paths["acquisition"])


def test_acquisition_log_cannot_omit_file_exposed_by_catalog(tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    acquisition = json.loads(paths["acquisition"].read_text(encoding="utf-8"))
    acquisition["records"] = acquisition["records"][1:]
    acquisition["counts"]["enumerated_resource_count"] = 3
    acquisition["counts"]["eligible_for_acquisition_count"] = 3
    acquisition["counts"]["acquired_count"] = 3
    write_json(paths["acquisition"], acquisition)

    with pytest.raises(BlindSamplingError, match="resource count is not reproducible"):
        validate_acquisition_log(paths["acquisition"])


def test_acquired_bytes_must_match_provider_checksum(tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    acquisition = json.loads(paths["acquisition"].read_text(encoding="utf-8"))
    record = acquisition["records"][0]
    resource_path = tmp_path / record["resource"]["file"]
    resource_path.write_text("tampered bytes\n", encoding="utf-8")
    record["resource"]["sha256"] = sha256_file(resource_path)
    write_json(paths["acquisition"], acquisition)

    with pytest.raises(BlindSamplingError, match="provider checksum mismatch"):
        validate_acquisition_log(paths["acquisition"])


def test_candidate_frame_cannot_omit_acquired_record(tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    frame = json.loads(paths["frame"].read_text(encoding="utf-8"))
    frame["candidates"] = frame["candidates"][1:]
    write_json(paths["frame"], frame)

    with pytest.raises(BlindSamplingError, match="cover every acquired record"):
        validate_candidate_frame(paths["frame"])


def test_recorded_download_failure_does_not_become_candidate(tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    acquisition = json.loads(paths["acquisition"].read_text(encoding="utf-8"))
    failed = acquisition["records"][0]
    failed["acquisition_status"] = "download_failed"
    failed["acquired_at"] = None
    failed["resource"] = None
    failed["failure"] = "fixture transport failure"
    acquisition["counts"]["acquired_count"] = 3
    acquisition["counts"]["download_failed_count"] = 1
    write_json(paths["acquisition"], acquisition)
    frame = json.loads(paths["frame"].read_text(encoding="utf-8"))
    frame["acquisition_log"]["sha256"] = sha256_file(paths["acquisition"])
    frame["candidates"] = frame["candidates"][1:]
    write_json(paths["frame"], frame)

    validated = validate_candidate_frame(paths["frame"])

    assert len(validated["candidates"]) == 3


def test_known_registry_builder_preserves_missing_external_bytes_as_identity(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    internal_task = data_root / "tasks" / "internal.json"
    external_task = data_root / "tasks" / "external.json"
    internal_resource = data_root / "raw" / "internal.csv"
    manifest_path = data_root / "manifest.json"
    output_path = tmp_path / "known.json"
    internal_resource.parent.mkdir(parents=True)
    internal_task.parent.mkdir(parents=True)
    internal_resource.write_text("temperature\n1\n", encoding="utf-8")
    write_json(
        internal_task,
        {
            "task": {
                "deterministic_schema": {
                    "metadata": {"study_source_file": "raw/internal.csv"}
                }
            }
        },
    )
    write_json(
        external_task,
        {
            "task": {
                "deterministic_schema": {
                    "metadata": {"external_source_file": "zenodo/record-1/missing.csv"}
                }
            }
        },
    )
    write_json(
        manifest_path,
        {
            "internal_task_count": 1,
            "external_task_count": 1,
            "internal_tasks": [
                {
                    "task_id": "internal::one",
                    "dataset_id": "one",
                    "task_file": "tasks/internal.json",
                }
            ],
            "external_tasks": [
                {
                    "task_id": "external::zenodo::record-1::missing.csv",
                    "source_file": "zenodo/record-1/missing.csv",
                    "role": "target",
                    "task_file": "tasks/external.json",
                }
            ],
        },
    )

    payload = build_known_nonblind_registry(
        grounding_manifest_path=manifest_path,
        data_root=data_root,
        frozen_at="2026-07-16T00:00:00Z",
        output_path=output_path,
    )
    write_json(output_path, payload)

    assert payload["coverage"]["total_record_count"] == 2
    assert payload["coverage"]["resource_hash_available_count"] == 1
    external = next(
        record
        for record in payload["records"]
        if record["source_namespace"] == "external"
    )
    assert external["resource"] is None
    assert external["source_identity"] == canonical_source_identity(
        "zenodo", "record-1", "missing.csv"
    )
    assert validate_known_nonblind_registry(output_path)["status"] == "ready"


def test_selection_is_deterministic_and_self_validating(tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    first = build_blind_selection(
        design_path=paths["design"],
        receipt_path=paths["receipt"],
        output_path=paths["selection"],
    )
    second = build_blind_selection(
        design_path=paths["design"],
        receipt_path=paths["receipt"],
        output_path=paths["selection"],
    )
    write_json(paths["selection"], first)

    assert first == second
    assert first["selected_dataset_count"] == 2
    assert first["selected_semantic_opportunity_case_count"] == 2
    assert validate_blind_selection(paths["selection"])["status"] == "ready"


def test_receipt_must_bind_exact_sampling_design(tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    receipt = json.loads(paths["receipt"].read_text(encoding="utf-8"))
    receipt["design_sha256"] = "0" * 64
    write_json(paths["receipt"], receipt)

    with pytest.raises(BlindSamplingError, match="does not bind"):
        build_blind_selection(
            design_path=paths["design"],
            receipt_path=paths["receipt"],
            output_path=paths["selection"],
        )


def test_known_nonblind_resource_cannot_remain_eligible(tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    frame = json.loads(paths["frame"].read_text(encoding="utf-8"))
    overlap = frame["candidates"][0]["resource"]["sha256"]
    known = json.loads(paths["known"].read_text(encoding="utf-8"))
    known["records"][0]["resource_available_at_freeze"] = True
    known["records"][0]["resource"] = frame["candidates"][0]["resource"]
    known["records"][0]["resource_absence_reason"] = None
    known["resource_sha256s"] = [overlap]
    known["coverage"]["resource_hash_available_count"] = 1
    write_json(paths["known"], known)
    frame["known_nonblind_resources"]["sha256"] = sha256_file(paths["known"])
    write_json(paths["frame"], frame)

    with pytest.raises(BlindSamplingError, match="not reproducible"):
        validate_candidate_frame(paths["frame"])


def test_known_nonblind_source_identity_cannot_evade_missing_resource_hash(
    tmp_path: Path,
) -> None:
    paths = build_fixture(tmp_path)
    frame = json.loads(paths["frame"].read_text(encoding="utf-8"))
    known = json.loads(paths["known"].read_text(encoding="utf-8"))
    candidate = frame["candidates"][0]
    known_record = known["records"][0]
    for key in (
        "source_identity",
        "source_repository",
        "source_record_id",
        "source_resource_id",
    ):
        known_record[key] = candidate[key]
    known["source_identities"] = [candidate["source_identity"]]
    write_json(paths["known"], known)
    frame["known_nonblind_resources"]["sha256"] = sha256_file(paths["known"])
    write_json(paths["frame"], frame)

    with pytest.raises(BlindSamplingError, match="not reproducible"):
        validate_candidate_frame(paths["frame"])


def test_outcome_only_task_key_blocks_candidate_frame(tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    frame = json.loads(paths["frame"].read_text(encoding="utf-8"))
    task_path = tmp_path / frame["candidates"][0]["task"]["file"]
    task = json.loads(task_path.read_text(encoding="utf-8"))
    task["gold_schema"] = {"secret": True}
    write_json(task_path, task)
    frame["candidates"][0]["task"]["sha256"] = sha256_file(task_path)
    write_json(paths["frame"], frame)

    with pytest.raises(BlindSamplingError, match="outcome-only keys"):
        validate_candidate_frame(paths["frame"])


def test_candidate_eligibility_must_be_derived_from_frozen_criteria(
    tmp_path: Path,
) -> None:
    paths = build_fixture(tmp_path)
    frame = json.loads(paths["frame"].read_text(encoding="utf-8"))
    candidate = frame["candidates"][0]
    candidate["eligibility"]["criterion_results"]["supported_local_format"] = False
    write_json(paths["frame"], frame)

    with pytest.raises(BlindSamplingError, match="mechanically derived"):
        validate_candidate_frame(paths["frame"])


def test_tampered_selection_fails_recalculation(tmp_path: Path) -> None:
    paths = build_fixture(tmp_path)
    selection = build_blind_selection(
        design_path=paths["design"],
        receipt_path=paths["receipt"],
        output_path=paths["selection"],
    )
    selection["selected_cases"][0]["scientific_family"] = "tampered"
    write_json(paths["selection"], selection)

    validation = validate_blind_selection(paths["selection"])

    assert validation["status"] == "blocked"
    assert validation["errors"][0]["code"] == "blind_selection_invalid"
