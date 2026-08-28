#!/usr/bin/env python3
"""Sync and validate canonical demo scenario artifact across surfaces (Issue #84).

Usage:
    python scripts/sync_scenario.py          # Regenerate artifacts in frontend/remotion
    python scripts/sync_scenario.py --check  # Fail if generated artifacts are stale
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SCENARIO = REPO_ROOT / "scenario" / "v1" / "demo_scenario.json"
CANONICAL_SCHEMA = REPO_ROOT / "scenario" / "v1" / "scenario.schema.json"

TARGETS = [
    REPO_ROOT / "frontend" / "src" / "scenario" / "demo_scenario.json",
    REPO_ROOT / "remotion" / "src" / "data" / "demo_scenario.json",
]


def load_canonical() -> str:
    if not CANONICAL_SCENARIO.exists():
        print(f"Error: Canonical scenario not found at {CANONICAL_SCENARIO}", file=sys.stderr)
        sys.exit(1)
    with open(CANONICAL_SCENARIO, encoding="utf-8") as f:
        # Validate json syntax
        data = json.load(f)
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def sync_targets(content: str, check_only: bool = False) -> bool:
    all_ok = True
    for target in TARGETS:
        target.parent.mkdir(parents=True, exist_ok=True)
        if check_only:
            if not target.exists():
                print(f"[STALE] Target does not exist: {target.relative_to(REPO_ROOT)}", file=sys.stderr)
                all_ok = False
            else:
                with open(target, encoding="utf-8") as f:
                    existing = f.read()
                if existing != content:
                    print(f"[STALE] Outdated generated scenario at {target.relative_to(REPO_ROOT)}", file=sys.stderr)
                    all_ok = False
        else:
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[SYNC] Synced {target.relative_to(REPO_ROOT)}")

    return all_ok


def main():
    check_mode = "--check" in sys.argv
    content = load_canonical()
    ok = sync_targets(content, check_only=check_mode)
    if check_mode and not ok:
        print("\nGenerated scenario artifacts are stale. Run 'python scripts/sync_scenario.py' to update.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
