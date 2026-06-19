from __future__ import annotations

import argparse
import json
from pathlib import Path

from .extractors.base import ExtractionRequest
from .extractors.csv_extractor import extract_csv_schema
from .extractors.hdf5_extractor import extract_hdf5_schema
from .extractors.registry import extract_path
from .unified_schema import build_unified_schema_envelope


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic-first scaffold for high-fidelity schema extraction studies."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("show-layout", help="Print the intended study directory layout.")

    csv_parser = subparsers.add_parser("extract-csv", help="Extract a conservative schema from a CSV file.")
    csv_parser.add_argument("--input", required=True, help="Path to the CSV file.")
    csv_parser.add_argument("--output", help="Optional JSON output path.")
    csv_parser.add_argument("--sample-limit", type=int, default=200, help="Maximum rows to sample.")

    hdf5_parser = subparsers.add_parser("extract-hdf5", help="Extract HDF5 hierarchy and field schema.")
    hdf5_parser.add_argument("--input", required=True, help="Path to the HDF5 file.")
    hdf5_parser.add_argument("--output", help="Optional JSON output path.")

    extract_parser = subparsers.add_parser("extract", help="Detect a format and run a registered deterministic extractor.")
    extract_parser.add_argument("--input", required=True, help="Path to the input file or supported directory store.")
    extract_parser.add_argument("--format", default="auto", help="Optional format hint; defaults to auto detection.")
    extract_parser.add_argument("--sample-limit", type=int, default=200, help="Maximum rows to sample for tabular profiling.")
    extract_parser.add_argument("--output", help="Optional JSON output path.")
    extract_parser.add_argument(
        "--output-shape",
        choices=["legacy", "envelope", "both"],
        default="legacy",
        help="Select the legacy outcome, unified envelope, or both.",
    )
    evaluate_parser = subparsers.add_parser("evaluate", help="Run the unified post-freeze evaluation entrypoint.")
    evaluate_parser.add_argument(
        "--scope",
        choices=["extensions", "all"],
        default="all",
        help="Include only post-freeze extension tracks or include frozen reference metrics.",
    )
    evaluate_parser.add_argument("--output", help="Optional JSON output path.")
    agent_parser = subparsers.add_parser("agent-export", help="Export a read-only agent context bundle.")
    agent_parser.add_argument("--input", required=True, help="Path to the input resource.")
    agent_parser.add_argument("--format", default="auto", help="Optional format hint.")
    agent_parser.add_argument("--sample-limit", type=int, default=200)
    agent_parser.add_argument("--output", help="Optional JSON output path.")

    return parser


def handle_show_layout() -> None:
    print(
        "\n".join(
            [
                "high_fidelity_schema_study/",
                "  README.md",
                "  study_manifest.json",
                "  cli.py",
                "  models.py",
                "  extractors/",
                "  docs/",
                "  templates/",
                "  data/",
                "  tests/",
            ]
        )
    )


def write_or_print(payload: dict, output_path: str | None) -> None:
    text = json.dumps(payload, indent=2)
    if output_path:
        Path(output_path).write_text(text + "\n", encoding="utf-8")
        return
    print(text)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "show-layout":
        handle_show_layout()
        return

    if args.command == "extract-csv":
        result = extract_csv_schema(args.input, sample_limit=args.sample_limit)
        write_or_print(result.to_dict(), args.output)
        return

    if args.command == "extract-hdf5":
        result = extract_hdf5_schema(args.input)
        write_or_print(result.to_dict(), args.output)
        return

    if args.command == "extract":
        outcome = extract_path(
            ExtractionRequest(
                path=args.input,
                format_hint=args.format,
                sample_limit=max(1, args.sample_limit),
            )
        )
        legacy = outcome.to_dict()
        envelope = build_unified_schema_envelope(legacy)
        payload = (
            legacy
            if args.output_shape == "legacy"
            else envelope
            if args.output_shape == "envelope"
            else {"extraction_outcome": legacy, "unified_schema_envelope": envelope}
        )
        write_or_print(payload, args.output)
        return

    if args.command == "evaluate":
        from .unified_evaluation import evaluate_all_tracks

        write_or_print(
            evaluate_all_tracks(include_frozen_references=args.scope == "all"),
            args.output,
        )
        return

    if args.command == "agent-export":
        from .agent_exports import export_agent_bundle

        outcome = extract_path(
            ExtractionRequest(args.input, format_hint=args.format, sample_limit=max(1, args.sample_limit))
        )
        write_or_print(export_agent_bundle(build_unified_schema_envelope(outcome)), args.output)
        return

    parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
