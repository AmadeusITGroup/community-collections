#!/usr/bin/env python3
"""Shared resolution of where a skill's eval definitions live.

Two layouts are supported, searched in this order:

1. **Canonical** — ``evals/skills/<skill_name>/`` at the repository root.
   Mirrors the ``docs/skills/<skill_name>/`` convention: per-primitive
   artifacts are grouped by primitive type under a typed top-level folder.
   This is where the generator writes and where new evals should live.

2. **Colocated fallback** — ``skills/<skill_name>/evals/`` inside the skill
   package. This is the layout used by the ``skill-optimiser`` reference
   skill, kept working so no existing package needs migration.

If *both* exist, the canonical location wins and a warning is emitted so a
half-finished migration leaves an obvious signal rather than silently using
a stale copy.

The eval *workspace* (generated run artifacts) always lives under the
resolved eval directory as ``<eval_dir>/workspace/``; downstream scripts
receive that path directly and never call this module.
"""

from __future__ import annotations

import sys
from pathlib import Path

CANONICAL_REL = "evals/skills"
COLOCATED_REL = "evals"  # under skills/<skill_name>/


def canonical_eval_dir(repo_root: Path, skill_name: str) -> Path:
    """The canonical eval directory (may or may not exist)."""
    return repo_root / "evals" / "skills" / skill_name


def colocated_eval_dir(repo_root: Path, skill_name: str) -> Path:
    """The colocated (in-package) eval directory (may or may not exist)."""
    return repo_root / "skills" / skill_name / "evals"


def resolve_eval_dir(
    repo_root: Path,
    skill_name: str,
    *,
    warn: bool = True,
) -> Path | None:
    """Return the eval directory holding ``evals.json`` for ``skill_name``.

    Resolution order: canonical (``evals/skills/<name>/``) then colocated
    (``skills/<name>/evals/``). Presence is decided by the existence of
    ``evals.json`` inside the candidate, not the directory alone — an empty
    directory must not shadow a populated fallback.

    Returns ``None`` if neither location has an ``evals.json``. When both do,
    the canonical one is returned and a warning is printed to stderr (unless
    ``warn=False``).
    """
    canonical = canonical_eval_dir(repo_root, skill_name)
    colocated = colocated_eval_dir(repo_root, skill_name)

    canonical_has = (canonical / "evals.json").is_file()
    colocated_has = (colocated / "evals.json").is_file()

    if canonical_has and colocated_has and warn:
        print(
            f"warning: evals for '{skill_name}' exist in both the canonical "
            f"location ({canonical}) and the colocated fallback ({colocated}); "
            f"using the canonical one. Remove the colocated copy to silence "
            f"this warning.",
            file=sys.stderr,
        )

    if canonical_has:
        return canonical
    if colocated_has:
        return colocated
    return None


def iter_eval_dirs(repo_root: Path):
    """Yield ``(skill_name, eval_dir)`` for every skill that has evals.

    Scans both layouts. A skill present in both is yielded once, with its
    canonical directory (matching ``resolve_eval_dir`` precedence).
    """
    seen: set[str] = set()

    canonical_root = repo_root / "evals" / "skills"
    if canonical_root.is_dir():
        for path in sorted(canonical_root.glob("*/evals.json")):
            name = path.parent.name
            seen.add(name)
            yield name, path.parent

    skills_root = repo_root / "skills"
    if skills_root.is_dir():
        for path in sorted(skills_root.glob("*/evals/evals.json")):
            name = path.parent.parent.name
            if name in seen:
                continue
            seen.add(name)
            yield name, path.parent
