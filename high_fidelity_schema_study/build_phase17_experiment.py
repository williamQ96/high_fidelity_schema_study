from __future__ import annotations

from .evaluate_phase17_unified_envelope import write_phase17_artifacts


def main() -> None:
    report = write_phase17_artifacts()
    print(f"Phase 17 unified envelope experiment built: {report['metrics']['case_count']} cases")


if __name__ == "__main__":
    main()
