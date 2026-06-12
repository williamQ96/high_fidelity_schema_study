from __future__ import annotations

from .evaluate_phase14a_zarr import write_phase14a_artifacts


def main() -> None:
    report = write_phase14a_artifacts()
    print(
        "Phase 14A Zarr experiment built: "
        f"{report['metrics']['case_count']} cases, "
        f"unsupported promotions={report['metrics']['unsupported_promotion_count']}"
    )


if __name__ == "__main__":
    main()
