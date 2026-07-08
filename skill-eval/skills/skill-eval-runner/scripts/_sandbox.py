"""Per-variant sandbox staging + repo-tree escape detection for the eval runner.

Shared by ``prepare_workspace.py`` (stages sandboxes, snapshots the git baseline)
and ``finalize_metrics.py`` (the post-run escape guard); kept in its own module so
finalize does not have to import prepare's CLI to reach ``git_dirty_paths``.

`stage_sandbox` creates a private `<variant>/sandbox/` directory — the executor's
writable repository root — and stages the eval's declared input files into it.
The skill reads its staged inputs there AND writes every file
it produces there — a declared input it edits, a path the skill computes itself
(e.g. `evals/skills/<name>/evals.json`), or a brand-new file — without touching
the shared `evals/<skill>/files/` tree, the real repository, or the concurrent
A/B variant. `git_dirty_paths` reports what the working tree has changed so the
runner can detect a skill that escaped its sandbox and wrote into the real tree.
Stdlib-only; `subprocess` shells out to the system `git` (not a third-party dep).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def stage_sandbox(
    evals_dir: Path,
    variant_dir: Path,
    declared_files: list[str],
) -> list[str]:
    """Create <variant_dir>/sandbox/ and stage the eval's declared inputs into it.

    The sandbox is the skill's writable repository root for this run. It is
    ALWAYS created — even when the eval declares no input files — so a skill that
    only PRODUCES output still has somewhere to write. Declared inputs are copied
    in, preserving their relative path under the sandbox.

    Args:
        evals_dir: evals/<skill_name>/ — the root the declared paths are relative to.
        variant_dir: eval-<id>-<name>/<variant>/ for this run.
        declared_files: the eval's `files` list, e.g. ["files/sample.log"].

    Returns:
        Paths to the staged COPIES, relative to variant_dir
        (e.g. ["sandbox/files/sample.log"]). Empty list when declared_files is
        empty — but the sandbox/ directory is still created.

    Raises:
        FileNotFoundError: a declared file does not exist under evals_dir.
    """
    sandbox_root = variant_dir / "sandbox"
    sandbox_root.mkdir(parents=True, exist_ok=True)

    resolved: list[str] = []
    for rel in declared_files:
        src = evals_dir / rel
        if not src.exists():
            raise FileNotFoundError(f"declared eval input not found: {src}")
        dst = sandbox_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        resolved.append(f"sandbox/{rel}")
    return resolved


def git_dirty_paths(anchor: Path) -> set[str]:
    """Repo-root-relative paths git reports as changed/untracked at `anchor`.

    Runs `git -C <anchor> status --porcelain -z` and returns the set of paths.
    git omits ignored files, and `evals/skills/**/workspace/` (which contains
    every per-variant `sandbox/`) is gitignored, so a correct run — one that
    writes only inside its sandbox — contributes nothing here. Returns an empty
    set when `anchor` is not inside a git work tree or git is unavailable, so a
    caller can treat "cannot check" as "nothing to report" instead of crashing.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(anchor), "status", "--porcelain", "-z"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return set()
    if proc.returncode != 0:
        return set()

    # Parse the NUL-separated porcelain stream. A normal entry is
    # "XY <path>", so the path is entry[3:]. A rename/copy entry ("R" or "C"
    # in either status column) is followed by its ORIGINAL path as the next
    # NUL-separated token with no status prefix; consume that token as-is so
    # it is recorded as a real path instead of being sliced like a prefixed one.
    tokens = proc.stdout.split("\0")
    paths: set[str] = set()
    i = 0
    while i < len(tokens):
        entry = tokens[i]
        if not entry:
            i += 1
            continue
        status = entry[:2]
        paths.add(entry[3:] if len(entry) > 3 else entry)
        if "R" in status or "C" in status:
            i += 1
            if i < len(tokens) and tokens[i]:
                paths.add(tokens[i])
        i += 1
    return paths
