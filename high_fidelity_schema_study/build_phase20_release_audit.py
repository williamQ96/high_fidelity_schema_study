from __future__ import annotations

from .release_audit import write_release_readiness_artifacts


def main() -> None:
    report = write_release_readiness_artifacts()
    print(f"Phase 20 release readiness: {'ready' if report['ready'] else 'not ready'}")


if __name__ == "__main__":
    main()
