from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
EXTERNAL_ROOT = DATA_ROOT / "external"
RETRIEVAL_ROOT = DATA_ROOT / "retrieval" / "external_candidate_pool"
POOL_MANIFEST_PATH = RETRIEVAL_ROOT / "pool_manifest.json"
ARTIFACT_MANIFEST_PATH = RETRIEVAL_ROOT / "artifact_manifest.json"
METADATA_ONLY_PATH = RETRIEVAL_ROOT / "metadata_only.json"
README_ONLY_PATH = RETRIEVAL_ROOT / "readme_only.json"
SCHEMA_ENHANCED_PATH = RETRIEVAL_ROOT / "schema_enhanced.json"
SCHEMA_ENHANCED_DETERMINISTIC_PATH = RETRIEVAL_ROOT / "schema_enhanced_deterministic.json"
SCHEMA_ENHANCED_SEMANTIC_MERGED_PATH = RETRIEVAL_ROOT / "schema_enhanced_semantic_merged.json"
QUERIES_PATH = RETRIEVAL_ROOT / "queries.json"
QRELS_PATH = RETRIEVAL_ROOT / "qrels.json"
SEMANTIC_MERGED_MANIFEST_PATH = DATA_ROOT / "semantic_merged" / "manifest.json"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def strip_html(text: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", text)
    no_entities = unescape(no_tags)
    return re.sub(r"\s+", " ", no_entities).strip()


def candidate_id_from_source_file(source_file: str) -> str:
    return source_file.replace("/", "__").replace(" ", "_")


def load_source_record(source_file: str) -> Dict[str, Any]:
    parts = Path(source_file).parts
    record_dir = EXTERNAL_ROOT / parts[0] / parts[1]
    return load_json(record_dir / "source_record.json")


def load_derived_schema(derived_relative: str) -> Dict[str, Any]:
    return load_json(DATA_ROOT / derived_relative)


def load_semantic_merged_by_source_file() -> Dict[str, str]:
    if not SEMANTIC_MERGED_MANIFEST_PATH.exists():
        return {}
    manifest = load_json(SEMANTIC_MERGED_MANIFEST_PATH)
    merged_by_source = {}
    for item in manifest.get("entries", []):
        if item.get("scope") != "external":
            continue
        merged = load_json(DATA_ROOT / item["merged_file"])
        source_file = merged.get("external_source_file")
        if source_file:
            merged_by_source[source_file] = item["merged_file"]
    return merged_by_source


def source_slice_terms(source_file: str) -> str:
    basename = Path(source_file).name
    terms = []
    for match in re.finditer(r"year[_\-\s]*(\d+)", basename, flags=re.IGNORECASE):
        value = match.group(1)
        terms.extend([f"year{value}", f"year {value}", f"file_slice_year{value}"])
        if value == "1":
            terms.extend(["first year", "first-year", "year one"])
        elif value == "2":
            terms.extend(["second year", "second-year", "year two"])
    for match in re.finditer(r"school[_\-\s]*(\d+)", basename, flags=re.IGNORECASE):
        value = match.group(1)
        terms.extend([f"school{value}", f"school {value}", f"file_slice_school{value}"])
    month_match = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|July|Jul|Aug|Sep|Oct|Nov|Dec)\b", basename, flags=re.IGNORECASE)
    if month_match:
        month = month_match.group(1).lower()
        terms.extend([month, f"file_slice_{month}"])
    return " ".join(terms)


def metadata_document(candidate: Dict[str, Any], source_record: Dict[str, Any]) -> Dict[str, Any]:
    metadata = source_record.get("metadata", {})
    title = metadata.get("title") or source_record.get("title", "")
    keywords = metadata.get("keywords", [])
    creators = [creator.get("name", "") for creator in metadata.get("creators", [])]
    text = " ".join(
        part for part in [
            title,
            " ".join(keywords),
            " ".join(creators),
            metadata.get("publication_date", ""),
            metadata.get("resource_type", {}).get("title", ""),
            metadata.get("license", {}).get("id", ""),
            Path(candidate["source_file"]).name,
        ] if part
    )
    return {
        "candidate_id": candidate_id_from_source_file(candidate["source_file"]),
        "source_file": candidate["source_file"],
        "title": title,
        "text": text,
        "metadata": {
            "doi": source_record.get("doi"),
            "keywords": keywords,
            "creators": creators,
            "publication_date": metadata.get("publication_date"),
            "license": metadata.get("license", {}).get("id"),
        },
    }


def readme_like_document(candidate: Dict[str, Any], source_record: Dict[str, Any]) -> Dict[str, Any]:
    metadata = source_record.get("metadata", {})
    description = strip_html(metadata.get("description", ""))
    notes = metadata.get("notes", "")
    title = metadata.get("title") or source_record.get("title", "")
    text = " ".join(part for part in [title, description, notes] if part).strip()
    return {
        "candidate_id": candidate_id_from_source_file(candidate["source_file"]),
        "source_file": candidate["source_file"],
        "title": title,
        "text": text,
        "metadata": {
            "text_source": "record_description_and_notes",
        },
    }


def schema_enhanced_document(
    candidate: Dict[str, Any],
    source_record: Dict[str, Any],
    derived_schema: Dict[str, Any],
    schema_source: str,
) -> Dict[str, Any]:
    metadata_doc = metadata_document(candidate, source_record)
    readme_doc = readme_like_document(candidate, source_record)

    field_summaries = []
    units = []
    logical_types = []
    semantic_types = []
    field_names = []
    schema_keywords = []
    for field in derived_schema.get("fields", []):
        field_names.append(field["field_name"])
        summary = f"{field['field_path']} {field['physical_type']}"
        if field.get("logical_type") and field["logical_type"] != "unknown":
            logical_types.append(field["logical_type"])
            schema_keywords.append(field["logical_type"])
            summary += f" logical:{field['logical_type']}"
        if field.get("semantic_type") and field["semantic_type"] != "unknown":
            semantic_types.append(field["semantic_type"])
            schema_keywords.append(field["semantic_type"])
            summary += f" semantic:{field['semantic_type']}"
        if field.get("unit"):
            units.append(field["unit"])
            schema_keywords.append(field["unit"])
            summary += f" unit:{field['unit']}"
        field_summaries.append(summary)

    time_series = derived_schema.get("metadata", {}).get("time_series")
    time_text = ""
    if time_series:
        time_axis = time_series.get("time_axis", {})
        time_text = " ".join(
            str(part)
            for part in [
                "time_axis",
                time_axis.get("field"),
                time_axis.get("frequency"),
                time_axis.get("regularity"),
                time_axis.get("missing_intervals"),
            ]
            if part is not None
        )

    # Emphasize file-specific schema terms so closely related files from the same source
    # record become easier to distinguish than they are in plain record descriptions.
    slice_terms = source_slice_terms(candidate["source_file"])
    schema_focus = " ".join(
        part for part in [
            Path(candidate["source_file"]).name,
            slice_terms,
            slice_terms,
            slice_terms,
            slice_terms,
            " ".join(field_names),
            " ".join(field_names),
            " ".join(schema_keywords),
            " ".join(schema_keywords),
            time_text,
        ] if part
    )

    text = " ".join(
        part for part in [
            metadata_doc["text"],
            readme_doc["text"],
            derived_schema.get("file_format", ""),
            derived_schema.get("data_modality", ""),
            f"schema_source {schema_source}",
            schema_focus,
            " ".join(field_summaries),
        ] if part
    )

    return {
        "candidate_id": candidate_id_from_source_file(candidate["source_file"]),
        "source_file": candidate["source_file"],
        "title": metadata_doc["title"],
        "text": text,
        "schema_summary": {
            "field_count": len(derived_schema.get("fields", [])),
            "data_modality": derived_schema.get("data_modality"),
            "logical_types": sorted(set(logical_types)),
            "semantic_types": sorted(set(semantic_types)),
            "units": sorted(set(units)),
            "time_series": time_series,
            "schema_source": schema_source,
        },
    }


def build_queries(target_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    lookup = {item["source_file"]: candidate_id_from_source_file(item["source_file"]) for item in target_entries}
    return [
        {
            "query_id": "hailstorm_tracks_geo_time",
            "text": "Find a CSV dataset with hailstorm tracks, latitude and longitude, timestamps, and storm intensity.",
            "expected_candidate_id": lookup["zenodo/record_15008662/unique_tracks_90.csv"],
        },
        {
            "query_id": "indoor_air_sensor_pollutants",
            "text": "Find school 5 time-series sensor data with PM2.5, NO2, O3, CO2, humidity, temperature, and sensor identifiers.",
            "expected_candidate_id": lookup["zenodo/record_18195710/ensensia_raw_20230728-20251202_school_5.csv"],
        },
        {
            "query_id": "atmospheric_hdf5_station",
            "text": "Find the Jan or January file-slice HDF5 atmospheric station data with ozone, nitrogen oxides, meteorological parameters, and rain variables.",
            "expected_candidate_id": lookup["zenodo/record_3660832/Data 01 Jan 2019.h5"],
        },
        {
            "query_id": "wind_lidar_time_series",
            "text": "Find time-series wind measurements with wind speed, wind direction, and wind shear exponent.",
            "expected_candidate_id": lookup["zenodo/record_5935524/20211108_ZXLidar_Winds.csv"],
        },
        {
            "query_id": "particle_counts_time_series",
            "text": "Find sensor time-series data with per-second particle counts from a field deployment.",
            "expected_candidate_id": lookup["zenodo/record_5935524/20211108_Sensit.csv"],
        },
        {
            "query_id": "tide_water_level_series",
            "text": "Find a time series of still water level or tidal water level measurements.",
            "expected_candidate_id": lookup["zenodo/record_5935524/20211108_Tides.csv"],
        },
        {
            "query_id": "greenland_cod_telemetry_positions",
            "text": "Find the year1 or first-year time-series telemetry data for juvenile Greenland cod with hourly positions, latitude and longitude, cove labels, and transplant or control group information.",
            "expected_candidate_id": lookup["dryad/10.5061_dryad.2f2b3/Season and site fidelity determine home range of dispersing and resident juvenile Greenland cod (Gadus ogac) in a Newfoundland fjord_year1.csv"],
        },
        {
            "query_id": "african_mammal_site_locations",
            "text": "Find a table of African mammal food web site locations with site code, community name, country, latitude, and longitude.",
            "expected_candidate_id": lookup["dryad/10.5061_dryad.zkh1893nh/African_Mammal_FoodWebs_Locations.csv"],
        },
        {
            "query_id": "mammal_functional_traits",
            "text": "Find a species trait table with mammal body mass in grams and binary or categorical feeding-resource traits such as vertebrate, bird, plant, or invertebrate consumption.",
            "expected_candidate_id": lookup["dryad/10.5061_dryad.zkh1893nh/functional_traits.csv"],
        },
        {
            "query_id": "weather_station_meteorology",
            "text": "Find weather station data with dateTime, temperature, relative humidity, rainfall, wind speed, wind gust, wind direction, and barometric pressure.",
            "expected_candidate_id": lookup["dryad/10.5061_dryad.dv41ns266/weatherMQ-FP-20261011.csv"],
        },
    ]


def build_qrels(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    qrels = []
    for query in queries:
        qrels.append(
            {
                "query_id": query["query_id"],
                "candidate_id": query["expected_candidate_id"],
                "relevance_grade": 2,
                "relevance_label": "highly_relevant",
                "query_source": "planted",
                "relevance_reason": "The query was intentionally written to target this candidate in the frozen external retrieval slice.",
            }
        )
    return {
        "qrels_schema": "single_positive_planted_v1",
        "query_count": len(queries),
        "judgment_count": len(qrels),
        "relevance_scale": {
            "0": "not judged or not relevant",
            "1": "partially relevant",
            "2": "highly relevant planted target",
        },
        "limitations": [
            "Current qrels contain one positive planted target per query.",
            "They support controlled offline comparison, not broad real-world dataset-search robustness.",
            "Future qrels should add graded judgments and user- or repository-inspired queries.",
        ],
        "qrels": qrels,
    }


def main() -> None:
    ensure_dir(RETRIEVAL_ROOT)
    pool_manifest = load_json(POOL_MANIFEST_PATH)
    pool_entries = pool_manifest["entries"]
    target_entries = [item for item in pool_entries if item["role"] == "target"]

    metadata_docs = []
    readme_docs = []
    schema_docs = []
    schema_deterministic_docs = []
    schema_semantic_merged_docs = []
    merged_by_source = load_semantic_merged_by_source_file()
    for entry in pool_entries:
        source_record = load_source_record(entry["source_file"])
        derived_schema = load_derived_schema(entry["derived_schema_file"])
        semantic_schema = (
            load_json(DATA_ROOT / merged_by_source[entry["source_file"]])
            if entry["source_file"] in merged_by_source
            else derived_schema
        )
        metadata_docs.append(metadata_document(entry, source_record))
        readme_docs.append(readme_like_document(entry, source_record))
        deterministic_doc = schema_enhanced_document(entry, source_record, derived_schema, "deterministic")
        semantic_doc = schema_enhanced_document(entry, source_record, semantic_schema, "semantic_merged" if entry["source_file"] in merged_by_source else "deterministic_fallback")
        schema_docs.append(deterministic_doc)
        schema_deterministic_docs.append(deterministic_doc)
        schema_semantic_merged_docs.append(semantic_doc)

    queries = build_queries(target_entries)
    qrels = build_qrels(queries)

    METADATA_ONLY_PATH.write_text(json.dumps({"documents": metadata_docs}, indent=2) + "\n", encoding="utf-8")
    README_ONLY_PATH.write_text(json.dumps({"documents": readme_docs}, indent=2) + "\n", encoding="utf-8")
    SCHEMA_ENHANCED_PATH.write_text(json.dumps({"documents": schema_docs}, indent=2) + "\n", encoding="utf-8")
    SCHEMA_ENHANCED_DETERMINISTIC_PATH.write_text(json.dumps({"documents": schema_deterministic_docs}, indent=2) + "\n", encoding="utf-8")
    SCHEMA_ENHANCED_SEMANTIC_MERGED_PATH.write_text(json.dumps({"documents": schema_semantic_merged_docs}, indent=2) + "\n", encoding="utf-8")
    QUERIES_PATH.write_text(json.dumps({"queries": queries}, indent=2) + "\n", encoding="utf-8")
    QRELS_PATH.write_text(json.dumps(qrels, indent=2) + "\n", encoding="utf-8")
    ARTIFACT_MANIFEST_PATH.write_text(
        json.dumps(
            {
                "candidate_count": len(pool_entries),
                "target_count": len(target_entries),
                "artifact_files": {
                    "metadata_only": str(METADATA_ONLY_PATH.relative_to(DATA_ROOT)).replace("\\", "/"),
                    "readme_only": str(README_ONLY_PATH.relative_to(DATA_ROOT)).replace("\\", "/"),
                    "schema_enhanced": str(SCHEMA_ENHANCED_PATH.relative_to(DATA_ROOT)).replace("\\", "/"),
                    "schema_enhanced_deterministic": str(SCHEMA_ENHANCED_DETERMINISTIC_PATH.relative_to(DATA_ROOT)).replace("\\", "/"),
                    "schema_enhanced_semantic_merged": str(SCHEMA_ENHANCED_SEMANTIC_MERGED_PATH.relative_to(DATA_ROOT)).replace("\\", "/"),
                    "queries": str(QUERIES_PATH.relative_to(DATA_ROOT)).replace("\\", "/"),
                    "qrels": str(QRELS_PATH.relative_to(DATA_ROOT)).replace("\\", "/"),
                },
                "notes": [
                    "The readme_only artifact is currently a README-like text baseline derived from source record descriptions and notes, because the imported Zenodo records do not provide standalone README files.",
                    "The schema_enhanced artifact is retained as a backward-compatible deterministic-schema artifact.",
                    "The schema_enhanced_deterministic and schema_enhanced_semantic_merged artifacts provide explicit schema_source comparison modes.",
                    "The schema_enhanced_semantic_merged artifact uses semantic_merged schemas where available and deterministic fallback otherwise.",
                    "Schema-enhanced artifacts include file-slice terms such as year1/year2 and month names to support same-family disambiguation.",
                    "This artifact bundle is built from retrieval-pool entries, which may include distractors that are not promoted benchmark targets.",
                    "The qrels file currently records one highly relevant planted target per query.",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
