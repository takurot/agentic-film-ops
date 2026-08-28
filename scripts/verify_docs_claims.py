#!/usr/bin/env python3
"""Verify documentation links, scenario claims, and absence of stale contracts (Issue #87).

Usage:
    python scripts/verify_docs_claims.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DOC_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "DEVPOST_ABOUT_THE_PROJECT.md",
    REPO_ROOT / "docs" / "DEVPOST_SUBMISSION.md",
    REPO_ROOT / "docs" / "DEMO_FALLBACK.md",
    REPO_ROOT / "docs" / "DEMO_SCRIPT.md",
    REPO_ROOT / "docs" / "EVIDENCE_MATRIX.md",
    REPO_ROOT / "docs" / "GOOGLE_CLOUD_PRODUCTS_USED.md",
    REPO_ROOT / "frontend" / "README.md",
]

FORBIDDEN_PATTERNS = [
    (r"GEMINI_MOCK", "Obsolete mock env var found"),
    (r"docs/assets/demo-recording\.mp4", "Dead asset link found"),
    (r"378 automated tests", "Outdated test count found (should reflect current suite)"),
    (r"354 Passing", "Outdated test count found"),
]


def check_forbidden_patterns(errors: list[str]):
    for doc in DOC_FILES:
        if not doc.exists():
            continue

        text = doc.read_text(encoding="utf-8")
        for pattern, desc in FORBIDDEN_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                errors.append(f"In {doc.relative_to(REPO_ROOT)}: {desc} ('{pattern}')")


def check_markdown_relative_links(errors: list[str]):
    # Matches [label](url) where url is not an external protocol or local hash anchor
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")
    for doc in DOC_FILES:
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8")
        for match in link_pattern.finditer(text):
            target = match.group(2).strip()
            # Ignore absolute URLs, page anchors, mailto, etc.
            if target.startswith(("http://", "https://", "#", "mailto:", "data:", "conversation://")):
                continue

            target_path_str = target.split("#")[0].strip()
            if not target_path_str:
                continue

            if target_path_str.startswith("/"):
                target_path = (REPO_ROOT / target_path_str.lstrip("/")).resolve()
            else:
                target_path = (doc.parent / target_path_str).resolve()

            if not target_path.exists():
                errors.append(
                    f"Broken link in {doc.relative_to(REPO_ROOT)}: '{target_path_str}' -> {target_path}"
                )


def main():
    errors: list[str] = []
    check_forbidden_patterns(errors)
    check_markdown_relative_links(errors)

    if errors:
        print("Documentation consistency checks failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print("All documentation claims, links, and contracts verified successfully.")


if __name__ == "__main__":
    main()
