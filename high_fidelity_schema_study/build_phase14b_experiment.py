from __future__ import annotations

from .evaluate_phase14b_zarr_compatibility import write_phase14b_artifacts


def main() -> None:
    report = write_phase14b_artifacts()
    print(
        "Phase 14B Zarr compatibility experiment built: "
        f"{report['metrics']['case_count']} cases, "
        f"true bugs={report['metrics']['true_bug_count']}, "
        f"unsupported promotions={report['metrics']['unsupported_promotion_count']}"
    )


if __name__ == "__main__":
    main()
