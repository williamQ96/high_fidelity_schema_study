from __future__ import annotations

from .evaluate_phase13_netcdf_cf import write_phase13_artifacts


def main() -> None:
    report = write_phase13_artifacts()
    print(
        "Phase 13 NetCDF/CF experiment built: "
        f"{report['metrics']['case_count']} cases, "
        f"unsupported promotions={report['metrics']['unsupported_promotion_count']}"
    )


if __name__ == "__main__":
    main()
