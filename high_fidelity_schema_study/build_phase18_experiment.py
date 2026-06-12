from __future__ import annotations

from .unified_evaluation import write_unified_evaluation_artifacts


def main() -> None:
    report = write_unified_evaluation_artifacts()
    print(f"Phase 18 unified evaluation built: {report['track_count']} tracks")


if __name__ == "__main__":
    main()
