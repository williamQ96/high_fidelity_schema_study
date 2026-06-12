from __future__ import annotations

from .evaluate_phase15a_parquet_arrow import write_phase15a_artifacts


def main() -> None:
    report = write_phase15a_artifacts()
    print(
        "Phase 15A Parquet/Arrow experiment built: "
        f"{report['metrics']['case_count']} cases, "
        f"unsupported promotions={report['metrics']['unsupported_promotion_count']}"
    )


if __name__ == "__main__":
    main()
