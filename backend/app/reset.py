"""CLI utility to reset demo state back to baseline (Issue #34, SPEC §2.2 / §13 Phase 4).

Usage:
    python -m app.reset
"""

from app.seed import reset_demo_state


def main() -> None:
    summary = reset_demo_state()
    print(f"✓ {summary['message']}")
    print(f"  Scene: {summary['scene_id']}")
    print(f"  Incident: {summary['incident_id']}")


if __name__ == "__main__":
    main()
