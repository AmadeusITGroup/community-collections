#!/usr/bin/env python3
"""List available skill evaluations.

Scans both eval layouts (canonical evals/skills/<name>/ and colocated
skills/<name>/evals/) and prints summaries. With --detail, shows
individual test cases for a specific skill.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from eval_paths import iter_eval_dirs, resolve_eval_dir

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "skills"

# Colors (disabled in CI or non-TTY)
if sys.stdout.isatty() and not os.environ.get("CI"):
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    MUTED = "\033[0;90m"
    NC = "\033[0m"
else:
    RED = GREEN = YELLOW = MUTED = NC = ""

SEPARATOR = "━" * 60


def get_skill_metadata_version(skill_name: str) -> str | None:
    """Extract metadata.version from a skill's SKILL.md frontmatter.

    Parses the YAML frontmatter (between ``---`` delimiters) and looks
    for a ``version:`` field under ``metadata:``.  Returns ``None`` if the
    file doesn't exist, has no frontmatter, or lacks a metadata version.
    """
    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_md.exists():
        return None

    text = skill_md.read_text(encoding="utf-8")
    # Frontmatter must start at the very beginning of the file
    if not text.startswith("---"):
        return None

    end = text.find("---", 3)
    if end == -1:
        return None

    frontmatter = text[3:end]

    # Simple line-based parse: find "metadata:" block, then "version:" underneath
    in_metadata = False
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Top-level key: no leading whitespace
        is_top_level = not line.startswith((" ", "\t"))
        if is_top_level:
            if stripped.startswith("metadata:"):
                in_metadata = True
            else:
                in_metadata = False
            continue
        # Indented key inside metadata block
        if in_metadata and stripped.startswith("version:"):
            raw = stripped.split(":", 1)[1].strip()
            # Remove inline comments (outside quotes)
            if raw and raw[0] not in ('"', "'"):
                raw = re.sub(r"\s+#.*$", "", raw).strip()
            value = raw.strip("\"'")
            return value if value else None

    return None


def staleness_label(skill_version: str | None, metadata_version: str | None) -> str:
    """Return a formatted staleness status string."""
    if metadata_version is None:
        return f"{MUTED}? unknown{NC}"
    if skill_version is None:
        return f"{MUTED}? unknown{NC}"
    if skill_version == metadata_version:
        return f"{GREEN}\u2713 current (v{metadata_version}){NC}"
    return (
        f"{YELLOW}\u26a0 stale "
        f"(eval\u2192v{skill_version}, skill\u2192v{metadata_version}){NC}"
    )


def list_all() -> int:
    """List all skills that have evals."""
    eval_dirs = list(iter_eval_dirs(REPO_ROOT))
    if not eval_dirs:
        print(f"{RED}No evals found under {REPO_ROOT}{NC}")
        return 1

    print(SEPARATOR)
    print("Available Skill Evaluations")
    print(SEPARATOR)

    for skill_name, eval_dir in eval_dirs:
        data = json.loads((eval_dir / "evals.json").read_text(encoding="utf-8"))
        skill_version = data.get("skill_version") or data.get("version")
        cases = data.get("evals", [])
        metadata_version = get_skill_metadata_version(skill_name)
        status = staleness_label(skill_version, metadata_version)
        print(f"  {GREEN}\u25cf{NC} {skill_name}  ({len(cases)} test cases)  {status}")

    print(SEPARATOR)
    print(f"Total: {len(eval_dirs)} skill(s)")
    return 0


def show_detail(skill_name: str) -> int:
    """Show test cases for a specific skill."""
    eval_dir = resolve_eval_dir(REPO_ROOT, skill_name)
    if eval_dir is None:
        print(f"{RED}No evals.json found for skill '{skill_name}'{NC}")
        return 1

    data = json.loads((eval_dir / "evals.json").read_text(encoding="utf-8"))
    skill_version = data.get("skill_version") or data.get("version", "unknown")
    cases = data.get("evals", [])
    metadata_version = get_skill_metadata_version(skill_name)
    status = staleness_label(skill_version, metadata_version)

    print(SEPARATOR)
    print(f"Skill: {skill_name}  (v{skill_version})  {status}")
    print(SEPARATOR)

    for case in cases:
        cid = case.get("id", "?")
        name = case.get("name", "unnamed")
        expectations = case.get("expectations", [])
        has_files = bool(case.get("files"))
        files_label = f"{GREEN}yes{NC}" if has_files else f"{YELLOW}no{NC}"
        print(
            f"  [{cid}] {name}\n"
            f"      expectations={len(expectations)}  files={files_label}"
        )

    print(SEPARATOR)
    print(f"Total: {len(cases)} test case(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="List available skill evaluations.")
    parser.add_argument(
        "--detail",
        metavar="SKILL",
        help="Show test cases for a specific skill",
    )
    args = parser.parse_args()

    if args.detail:
        return show_detail(args.detail)
    return list_all()


if __name__ == "__main__":
    raise SystemExit(main())
