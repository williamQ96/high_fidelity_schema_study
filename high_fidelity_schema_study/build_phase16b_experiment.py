from __future__ import annotations

from .evaluate_phase16b_xml import write_phase16b_artifacts


def main() -> None:
    report = write_phase16b_artifacts()
    print(
        "Phase 16B XML/XSD experiment built: "
        f"{report['metrics']['case_count']} cases, "
        f"unsupported promotions={report['metrics']['unsupported_promotion_count']}"
    )


if __name__ == "__main__":
    main()
