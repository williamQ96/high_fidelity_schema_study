from __future__ import annotations

from .evaluate_phase12 import write_phase12_artifacts


def main() -> None:
    report = write_phase12_artifacts()
    print(
        "Phase 12 experiment built: "
        f"{report['metrics']['case_count']} cases, "
        f"unsupported promotions={report['metrics']['unsupported_promotion_count']}"
    )


if __name__ == "__main__":
    main()
