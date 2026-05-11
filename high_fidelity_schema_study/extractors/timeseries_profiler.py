from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from ..models import FieldSchema


DATETIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
)


def is_strong_time_field_name(field_name: str) -> bool:
    lowered = field_name.lower()
    return any(
        token in lowered
        for token in ("timestamp", "event_time", "datetime", "time_", "_time", "ts_", "_ts")
    ) or lowered in {"time", "timestamp", "event_time", "ts", "ts_utc", "date"}


def parse_datetime(value: str) -> Optional[datetime]:
    text = value.strip()
    if not text:
        return None
    normalized = text[:-1] if text.endswith("Z") else text
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    return None


def looks_like_datetime_series(values: Iterable[str]) -> bool:
    non_empty = [value for value in values if value.strip()]
    if not non_empty:
        return False
    parsed = [parse_datetime(value) for value in non_empty]
    return all(item is not None for item in parsed)


def infer_frequency(deltas_seconds: List[int]) -> str:
    if not deltas_seconds:
        return "unknown"
    dominant_delta, count = Counter(deltas_seconds).most_common(1)[0]
    dominance = count / len(deltas_seconds)
    if dominance < 0.75:
        return "mixed"
    mapping = {
        1: "1 second",
        60: "1 minute",
        300: "5 minutes",
        360: "6 minutes",
        600: "10 minutes",
        1200: "20 minutes",
        900: "15 minutes",
        1800: "30 minutes",
        3600: "1 hour",
        86400: "1 day",
    }
    return mapping.get(dominant_delta, f"{dominant_delta} seconds")


def _measurement_candidates(fields: List[FieldSchema], excluded_names: set[str]) -> List[str]:
    candidates = []
    for field in fields:
        if field.field_name in excluded_names:
            continue
        if field.physical_type not in {"int", "float"}:
            continue
        if field.logical_type in {"identifier", "coordinate"}:
            continue
        candidates.append(field.field_name)
    return candidates


def _infer_time_axis_properties(parsed_values: List[datetime]) -> Dict[str, object]:
    frequency = "unknown"
    regularity = "unknown"
    missing_intervals = None
    if len(parsed_values) >= 3:
        ordered = sorted(parsed_values)
        deltas = [
            int((current - previous).total_seconds())
            for previous, current in zip(ordered, ordered[1:])
            if current >= previous
        ]
        frequency = infer_frequency(deltas)
        if deltas and frequency not in {"unknown", "mixed"}:
            dominant_delta, count = Counter(deltas).most_common(1)[0]
            dominance = count / len(deltas)
            if dominance >= 0.95:
                regularity = "regular"
            elif dominance >= 0.75:
                regularity = "mostly_regular"
            else:
                regularity = "irregular"
            target_delta = Counter(deltas).most_common(1)[0][0]
            expected_steps = int((ordered[-1] - ordered[0]).total_seconds() / target_delta) + 1
            missing_intervals = max(expected_steps - len(ordered), 0)
        else:
            regularity = "irregular"

    return {
        "type": "datetime",
        "frequency": frequency,
        "regularity": regularity,
        "missing_intervals": missing_intervals,
    }


def _assembled_datetime_series(column_samples: Dict[str, List[str]]) -> tuple[Optional[List[str]], List[datetime]]:
    key_map = {key.lower(): key for key in column_samples}
    required = ["year", "month", "day"]
    if any(part not in key_map for part in required):
        return None, []

    ordered_parts = [key_map["year"], key_map["month"], key_map["day"]]
    optional_parts = [part for part in ["hour", "minute", "second"] if part in key_map]
    ordered_parts.extend(key_map[part] for part in optional_parts)

    row_count = len(column_samples[key_map["year"]])
    parsed_values: List[datetime] = []
    for idx in range(row_count):
        try:
            year = int(column_samples[key_map["year"]][idx])
            month = int(column_samples[key_map["month"]][idx])
            day = int(column_samples[key_map["day"]][idx])
            hour = int(column_samples[key_map["hour"]][idx]) if "hour" in key_map else 0
            minute = int(column_samples[key_map["minute"]][idx]) if "minute" in key_map else 0
            second = int(column_samples[key_map["second"]][idx]) if "second" in key_map else 0
            parsed_values.append(datetime(year, month, day, hour, minute, second))
        except (ValueError, IndexError):
            return None, []

    return ordered_parts, parsed_values


def infer_time_series_metadata(
    column_samples: Dict[str, List[str]],
    fields: List[FieldSchema],
) -> Dict[str, object]:
    time_candidates = []
    field_by_name = {field.field_name: field for field in fields}
    for field in fields:
        samples = column_samples.get(field.field_name, [])
        if field.physical_type == "datetime" or looks_like_datetime_series(samples):
            time_candidates.append(field.field_name)

    if not time_candidates:
        assembled_parts, assembled_values = _assembled_datetime_series(column_samples)
        if not assembled_parts:
            return {}

        measurement_candidates = _measurement_candidates(fields, set(assembled_parts))
        if not measurement_candidates:
            return {}

        identifier_candidates = [
            field.field_name
            for field in fields
            if field.semantic_type.endswith("_identifier") or field.logical_type == "identifier"
        ]

        return {
            "time_axis": {
                "field": "computed_from_parts",
                "computed_from": assembled_parts,
                **_infer_time_axis_properties(assembled_values),
            },
            "series_identifier": identifier_candidates[0] if identifier_candidates else None,
            "measurements": measurement_candidates,
        }

    time_field = time_candidates[0]
    measurement_candidates = _measurement_candidates(fields, {time_field})
    if not measurement_candidates:
        return {}
    if not is_strong_time_field_name(time_field):
        return {}

    parsed_values = [parse_datetime(value) for value in column_samples.get(time_field, [])]
    parsed_values = [value for value in parsed_values if value is not None]

    field_by_name[time_field].logical_type = "time_axis"
    if field_by_name[time_field].semantic_type == "unknown":
        field_by_name[time_field].semantic_type = "observation_time"

    identifier_candidates = [
        field.field_name
        for field in fields
        if field.semantic_type == "identifier" or field.logical_type == "identifier"
    ]

    return {
        "time_axis": {
            "field": time_field,
            **_infer_time_axis_properties(parsed_values),
        },
        "series_identifier": identifier_candidates[0] if identifier_candidates else None,
        "measurements": measurement_candidates,
    }
