from __future__ import annotations

from .evaluate_phase16a_json import write_phase16a_artifacts


def main() -> None:
    report = write_phase16a_artifacts()
    print(
        "Phase 16A JSON experiment built: "
        f"{report['metrics']['case_count']} cases, "
        f"unsupported promotions={report['metrics']['unsupported_promotion_count']}"
    )


if __name__ == "__main__":
    main()
