from __future__ import annotations

from .evaluate_phase14c_zarr_external import write_phase14c_artifacts


def main() -> None:
    report = write_phase14c_artifacts(enable_cross_parser=True)
    print(
        "Phase 14C external/library conformance experiment built: "
        f"{report['metrics']['case_count']} cases, "
        f"differences={report['metrics']['conformance_difference_count']}, "
        f"true bugs={report['metrics']['true_bug_count']}"
    )


if __name__ == "__main__":
    main()
