from __future__ import annotations

import argparse
import json
from pathlib import Path

from .extractors.csv_extractor import extract_csv_schema
from .extractors.hdf5_extractor import extract_hdf5_schema


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

    parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
