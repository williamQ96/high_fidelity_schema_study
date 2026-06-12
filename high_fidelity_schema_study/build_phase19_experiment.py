from __future__ import annotations

from .evaluate_phase19_agent_exports import write_phase19_artifacts


def main() -> None:
    report = write_phase19_artifacts()
    print(f"Phase 19 agent-ready exports built: {report['metrics']['case_count']} bundles")


if __name__ == "__main__":
    main()
