from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional

from ..models import DatasetSchema, EvidenceRecord, FieldSchema
from .timeseries_profiler import infer_time_series_metadata, parse_datetime


def _looks_like_int(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if text.startswith(("+", "-")):
        text = text[1:]
    return text.isdigit()


def _has_leading_zero(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    signless = text[1:] if text.startswith(("+", "-")) else text
    return len(signless) > 1 and signless.startswith("0") and signless.isdigit()


def _looks_like_float(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    try:
        float(text)
    except ValueError:
        return False
    return any(char in text for char in ".eE")


def _semantic_type_from_name(column_name: str, fieldnames: List[str]) -> str:
    lowered = column_name.lower()
    fieldname_set = {name.lower() for name in fieldnames}

    exact_mapping = {
        "station_id": "station_identifier",
        "station_name": "station_name",
        "sample_id": "sample_identifier",
        "sensor_id": "sensor_identifier",
        "buoy_id": "buoy_identifier",
        "site_code": "site_identifier",
        "collection_date": "collection_date",
        "ts_utc": "observation_time",
        "event_time": "observation_time",
        "dt_obs": "observation_time",
        "power_kw": "power",
        "voltage_v": "voltage",
        "status": "operational_status",
        "ph": "acidity_ph",
        "do_mg_l": "dissolved_oxygen",
        "turbidity_ntu": "turbidity",
        "notes": "free_text_note",
        "qc_flag": "quality_flag",
        "flag": "quality_flag",
        "rec": "record_identifier",
        "zc": "postal_zone_code",
        "device": "device_identifier",
        "salinity_psu": "salinity",
    }
    if lowered in exact_mapping:
        return exact_mapping[lowered]
    if lowered.endswith("_id") or lowered == "id" or "identifier" in lowered:
        return lowered.removesuffix("_id") + "_identifier" if lowered.endswith("_id") and lowered != "id" else "identifier"
    if "timestamp" in lowered or lowered.startswith("time") or lowered.endswith("date") or lowered in {"ts_utc", "dt_obs", "event_time"}:
        return "observation_time"
    if lowered in {"lat", "latitude", "latitude_deg"}:
        return "latitude"
    if lowered in {"lon", "longitude", "longitude_deg"}:
        return "longitude"
    if lowered in {"lat", "latitude", "lon", "longitude"}:
        return "coordinate"
    if "elevation" in lowered:
        return "elevation"
    if "precip" in lowered:
        return "precipitation"
    if "humidity" in lowered:
        return "relative_humidity"
    if "pressure" in lowered:
        return "surface_pressure"
    if "wind_speed" in lowered:
        return "wind_speed"
    if "temp" in lowered or lowered == "temperature":
        aquatic_context = any(token in fieldname_set for token in {"salinity_psu", "buoy_id"}) or "water" in lowered
        return "water_temperature" if aquatic_context else "air_temperature"
    if any(token in lowered for token in ("value", "val")):
        return "unknown"
    return "unknown"


def _unit_from_name(column_name: str) -> Optional[str]:
    lowered = column_name.lower()
    suffix_mapping = {
        "_c": "Celsius",
        "_f": "Fahrenheit",
        "_k": "Kelvin",
        "_mm": "millimeter",
        "_m": "meter",
        "_kg": "kilogram",
        "_deg": "degree",
        "_pct": "percent",
        "_kw": "kilowatt",
        "_v": "volt",
        "_ntu": "NTU",
        "_psu": "PSU",
        "_mg_l": "milligram_per_liter",
        "_m_s": "meter_per_second",
    }
    for suffix, unit in suffix_mapping.items():
        if lowered.endswith(suffix):
            return unit
    return None


def _logical_type_from_field(fieldname: str, physical_type: str, semantic_type: str) -> str:
    lowered = fieldname.lower()
    if semantic_type.endswith("_identifier") or semantic_type == "identifier":
        return "identifier"
    if semantic_type in {"latitude", "longitude", "elevation", "depth"}:
        return "coordinate"
    if semantic_type in {
        "precipitation",
        "relative_humidity",
        "surface_pressure",
        "wind_speed",
        "air_temperature",
        "water_temperature",
        "power",
        "voltage",
        "acidity_ph",
        "dissolved_oxygen",
        "turbidity",
        "salinity",
    }:
        return "measurement"
    if semantic_type in {"station_name", "operational_status", "quality_flag", "free_text_note"}:
        return "label"
    if semantic_type in {"collection_date", "observation_time"}:
        return "attribute"
    if "flag" in lowered or "status" in lowered or "note" in lowered or lowered.endswith("_name"):
        return "label"
    if physical_type in {"int", "float"} and any(token in lowered for token in ("temp", "precip", "pressure", "power", "voltage", "humidity", "wind", "rain", "ph", "turbidity")):
        return "measurement"
    return "unknown"


def _conservative_physical_type(values: List[str]) -> str:
    non_empty = [value for value in values if value.strip()]
    if not non_empty:
        return "string"
    if any(_has_leading_zero(value) for value in non_empty):
        return "string"
    if all(parse_datetime(value) is not None for value in non_empty):
        return "datetime"
    if all(_looks_like_int(value) for value in non_empty):
        return "int"
    if all(_looks_like_int(value) or _looks_like_float(value) for value in non_empty):
        return "float"
    return "string"


def _value_range(physical_type: str, values: List[str]) -> Optional[List[float]]:
    if physical_type not in {"int", "float"}:
        return None
    numeric_values = [float(value) for value in values if value.strip()]
    if not numeric_values:
        return None
    return [min(numeric_values), max(numeric_values)]


def extract_csv_schema(path: str, sample_limit: int = 200) -> DatasetSchema:
    csv_path = Path(path)
    with csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV file has no header row: {csv_path}")
        fieldnames = list(reader.fieldnames)
        column_samples: Dict[str, List[str]] = {fieldname: [] for fieldname in fieldnames}
        sampled_rows = 0
        for row in reader:
            if sampled_rows >= sample_limit:
                break
            sampled_rows += 1
            for fieldname in fieldnames:
                column_samples[fieldname].append((row.get(fieldname) or "").strip())

    fields: List[FieldSchema] = []
    for fieldname in fieldnames:
        samples = column_samples[fieldname]
        physical_type = _conservative_physical_type(samples)
        semantic_type = _semantic_type_from_name(fieldname, fieldnames)
        logical_type = _logical_type_from_field(fieldname, physical_type, semantic_type)
        unit = _unit_from_name(fieldname)
        nullable = any(not value.strip() for value in samples)
        non_empty = [value for value in samples if value.strip()]
        unique_ratio = round(len(set(non_empty)) / len(non_empty), 4) if non_empty else None
        evidence = [
            EvidenceRecord(
                tier="structural",
                evidence_type="csv_header",
                source=str(csv_path),
                detail=f"header='{fieldname}'",
                confidence=1.0,
            ),
            EvidenceRecord(
                tier="statistical",
                evidence_type="sample_rows",
                source=str(csv_path),
                detail=f"sampled_rows={sampled_rows}",
                confidence=0.9,
            ),
        ]
        if unit is not None:
            evidence.append(
                EvidenceRecord(
                    tier="structural",
                    evidence_type="column_name_unit_hint",
                    source=fieldname,
                    detail=f"inferred unit from column suffix: {unit}",
                    confidence=0.82,
                )
            )
        if semantic_type == "identifier" and physical_type == "string":
            evidence.append(
                EvidenceRecord(
                    tier="structural",
                    evidence_type="identifier_name_pattern",
                    source=fieldname,
                    detail="column name suggests identifier semantics",
                    confidence=0.9,
                )
            )

        field = FieldSchema(
            field_name=fieldname,
            field_path=fieldname,
            physical_type=physical_type,
            logical_type=logical_type,
            semantic_type=semantic_type,
            nullable=nullable,
            unique_ratio=unique_ratio,
            unit=unit,
            example_values=list(dict.fromkeys(non_empty[:3])),
            missing_count=sum(1 for value in samples if not value.strip()),
            value_range=_value_range(physical_type, samples),
            source_evidence=evidence,
            confidence=1.0 if physical_type in {"datetime", "int", "float"} else 0.9,
            uncertainty_reason=(
                "conservative fallback to string to avoid over-claiming"
                if physical_type == "string" and non_empty
                else None
            ),
            extraction_method="csv_conservative_profiler",
        )
        fields.append(field)

    dataset_schema = DatasetSchema(
        dataset_id=csv_path.stem,
        file_id=csv_path.name,
        file_format="csv",
        data_modality="tabular",
        fields=fields,
        metadata={
            "sampled_rows": sampled_rows,
            "column_count": len(fieldnames),
        },
    )

    time_series_metadata = infer_time_series_metadata(column_samples, fields)
    if time_series_metadata:
        dataset_schema.data_modality = "time_series"
        dataset_schema.metadata["time_series"] = time_series_metadata

    return dataset_schema
